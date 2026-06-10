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
        page.wait_for_timeout(2000)

        # "+" per JavaScript ausloesen (umgeht aria-hidden / nicht-klickbar)
        page.evaluate("""() => {
            const plus = document.querySelector('a.btn-plus');
            if (plus) plus.click();
        }""")
        page.wait_for_timeout(3000)

        # auf Kacheln warten; wenn sie ausbleiben -> Diagnose ausgeben
        try:
            page.wait_for_selector(".timeslot-calendar__day", state="attached", timeout=30000)
        except Exception:
            print("DIAGNOSE: keine Kacheln gefunden.")
            print("  Plus-Button im HTML:", page.locator("a.btn-plus").count())
            print("  Kalender-Container:", page.locator(".timeslot-calendar").count())
            html = page.content()
            print("  'Kusama' im HTML:", "Kusama" in html)
            print("  'timeslot-calendar' im HTML:", "timeslot-calendar" in html)
            b.close()
            return False

        for _ in range(3):
            header = page.locator(".timeslot-calendar__header h3").inner_text()
            if ZIELMONAT in header:
                break
            clicked = page.evaluate("""() => {
                const el = document.querySelector('a.timeslot-calendar__month--next');
                if (!el || el.hasAttribute('disabled')) return false;
                el.click();
                return true;
            }""")
            if not clicked:
                break
            page.wait_for_timeout(2000)

        header = page.locator(".timeslot-calendar__header h3").inner_text()
        frei = page.locator(
            ".timeslot-calendar__content .timeslot-calendar__day"
            ":not(.timeslot-calendar__day--disabled)"
        ).count()
        print(f"DIAGNOSE: Monat='{header}', freie Tage={frei}")
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
