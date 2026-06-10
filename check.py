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

        # Cookie-Banner bestaetigen ("Verstanden") -> erst dann erscheint der Kalender
        try:
            page.get_by_role("button", name="Verstanden").click(timeout=8000)
        except Exception:
            try:
                page.get_by_text("Verstanden", exact=True).click(timeout=8000)
            except Exception:
                print("DIAGNOSE: 'Verstanden' nicht gefunden/klickbar")
        page.wait_for_timeout(3000)

        # jetzt sollte der Kalender da sein
        try:
            page.wait_for_selector(".timeslot-calendar__day", state="attached", timeout=30000)
        except Exception:
            print("DIAGNOSE: nach Cookie-Klick immer noch keine Kacheln.")
            print("  calendar:", page.locator(".timeslot-calendar").count())
            print("  btn-plus:", page.locator("a.btn-plus").count())
            print("  h1/h2:", page.locator("h1, h2").all_inner_texts())
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
