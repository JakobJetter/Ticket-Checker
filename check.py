import os, sys
from playwright.sync_api import sync_playwright
import requests

NTFY = os.environ["NTFY_URL"]
SHOP = "https://shop.museum-ludwig.de/webshop/webticket/timeslot"
ZIELMONAT = "Juli"   # spaeter ggf. "August" usw.

def finde_kalender_frame(page):
    # den Frame finden, der den Kalender tatsaechlich enthaelt
    for fr in page.frames:
        try:
            if fr.locator(".timeslot-calendar").count() > 0:
                return fr
        except Exception:
            pass
    return None

def ziel_verfuegbar():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(SHOP, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)  # AJAX/Frame laden lassen

        fr = finde_kalender_frame(page)
        if fr is None:
            print("DIAGNOSE: Kalender-Frame nicht gefunden.")
            print("  Anzahl Frames:", len(page.frames))
            for i, f in enumerate(page.frames):
                print(f"  Frame {i}: {f.url}")
            b.close()
            return False

        # "+" im richtigen Frame ausloesen, damit der Kalender aktiv wird
        fr.evaluate("""() => {
            const plus = document.querySelector('a.btn-plus');
            if (plus) plus.click();
        }""")
        page.wait_for_timeout(3000)

        try:
            fr.wait_for_selector(".timeslot-calendar__day", state="attached", timeout=30000)
        except Exception:
            print("DIAGNOSE: Frame da, aber keine Kacheln.")
            print("  Plus im Frame:", fr.locator("a.btn-plus").count())
            b.close()
            return False

        for _ in range(3):
            header = fr.locator(".timeslot-calendar__header h3").inner_text()
            if ZIELMONAT in header:
                break
            clicked = fr.evaluate("""() => {
                const el = document.querySelector('a.timeslot-calendar__month--next');
                if (!el || el.hasAttribute('disabled')) return false;
                el.click();
                return true;
            }""")
            if not clicked:
                break
            page.wait_for_timeout(2000)

        header = fr.locator(".timeslot-calendar__header h3").inner_text()
        frei = fr.locator(
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
