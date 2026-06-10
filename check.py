import os, sys
from playwright.sync_api import sync_playwright
import requests

NTFY = os.environ["NTFY_URL"]
SHOP = "https://shop.museum-ludwig.de/webshop/webticket/timeslot"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.goto(SHOP, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4000)

    print("TITEL:", page.title())
    print("URL nach Laden:", page.url)
    print("h1/h2:", page.locator("h1, h2").all_inner_texts())
    print("calendar-Elemente:", page.locator(".timeslot-calendar").count())
    print("day-Elemente:", page.locator(".timeslot-calendar__day").count())
    print("btn-plus:", page.locator("a.btn-plus").count())
    body = page.locator("body").inner_text()
    print("----- BODY-TEXT (Anfang) -----")
    print(body[:1500])
    b.close()
