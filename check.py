import os, sys
from playwright.sync_api import sync_playwright
import requests

NTFY = os.environ["NTFY_URL"]
SHOP = "https://shop.museum-ludwig.de/webshop/webticket/timeslot"
ZIELMONAT = "Juli"   # spaeter ggf. "August" usw.

def ziel_verfuegbar():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(SHOP, wait_until="networkidle", timeout=60000)
        # Kartenauswahl aktivieren, damit der Kalender ueberhaupt erscheint
        page.locator("a.btn-plus").first.click()
        page.wait_for_timeout(2000)
        # auf einen tatsaechlichen Tag warten
        page.wait_for_selector(".timeslot-calendar__day", timeout=30000)
        # bis zu 3x auf "naechster Monat" klicken, bis Zielmonat im Header steht
        for _ in range(3):
            header = page.locator(".timeslot-calendar__header h3").inner_text()
            if ZIELMONAT in header:
                break
            nxt = page.locator("a.timeslot-calendar__month--next")
            if nxt.get_attribute("disabled") is not None:
                break
            nxt.click()
            page.wait_for_timeout(1500)
        header = page.locator(".timeslot-calendar__header h3").inner_text()
        # buchbare Tage = Kacheln OHNE die Klasse --disabled
        frei = page.locator(
            ".timeslot-calendar__content .timeslot-calendar__day"
            ":not(.timeslot-calendar__day--disabled)"
        ).count()
        b.close()
        return (ZIELMONAT in header) and (frei > 0)

try:
    if ziel_verfuegbar():
        requests.post(
            NTFY,
            data=f"Kusama {ZIELMONAT}-Tickets verfuegbar! {SHOP}".encode("utf-8"),
            headers={"Title": "Museum Ludwig", "Priority": "urgent", "Tags": "tada"},
        )
        print("Tickets gefunden -> benachrichtigt")
    else:
        print("noch keine Tickets")
except Exception as e:
    print("Fehler:", e)
    sys.exit(0)
