import os, sys
from playwright.sync_api import sync_playwright
import requests

NTFY = os.environ["NTFY_URL"]
SHOP = "https://shop.museum-ludwig.de/webshop/webticket/timeslot"
ZIELMONAT = "Juli"   # spaeter ggf. "August" usw.

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

def ziel_verfuegbar():
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(
            user_agent=UA,
            locale="de-DE",
            viewport={"width": 1280, "height": 900},
        )
        # webdriver-Flag verstecken
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = ctx.new_page()
        page.goto(SHOP, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        # Cookie-Banner bestaetigen, falls da
        for sel in ['button:has-text("Verstanden")', 'text=Verstanden']:
            try:
                page.click(sel, timeout=5000)
                break
            except Exception:
                pass
        page.wait_for_timeout(2000)

        # Diagnose: kam die echte Seite an?
        cal = page.locator(".timeslot-calendar").count()
        if cal == 0:
            print("DIAGNOSE: Seite weiterhin ohne Kalender.")
            print("  TITEL:", page.title())
            print("  h1/h2:", page.locator("h1, h2").all_inner_texts())
            print("  body-Anfang:", page.locator("body").inner_text()[:300])
            b.close()
            return False

        page.wait_for_selector(".timeslot-calendar__day", state="attached", timeout=20000)

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
