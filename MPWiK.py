import os
import time
from datetime import datetime, date, timedelta
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import requests

# === KONFIGURACJA ===
TELEGRAM_BOT_TOKEN = "8457272120:AAG4b8uvOG2gb20raSlFP52OikwQ-5L1sT8"
CHAT_ID = "1233434142"

FB_URL = "https://www.facebook.com/ZiemiaChrzanowska"


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text[:4090],
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception:
        pass


def parse_relative_date(text: str) -> Optional[date]:
    """
    Parsuje tekst typu '10 godz.', 'wczoraj', '2 dni' itp.
    Zwraca obiekt date lub None jeśli nie uda się sparsować (starsze niż 3 dni).
    """
    text = text.lower()
    today = datetime.today().date()

    if any(x in text for x in ["min", "sek", "godz", "właśnie"]):
        return today
    if "wczoraj" in text or "1 dzień" in text or "1 dzień temu" in text:
        return today - timedelta(days=1)
    if "2 dni" in text or "2 dni temu" in text:
        return today - timedelta(days=2)
    if "3 dni" in text or "3 dni temu" in text:
        return today - timedelta(days=3)

    return None


# === Selenium setup ===
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
})

posts = []

try:
    driver.get(FB_URL)
    time.sleep(6)

    # scroll
    for _ in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # każdy post Facebooka
    containers = driver.find_elements(
        By.XPATH,
        "//div[@role='article']"
    )

    for post in containers:
        try:
            # 1) wyszukujemy element z datą posta (klasy FB mogą się zmieniać; ten selektor działa w 2025)
            time_el = post.find_elements(
                By.XPATH,
                ".//span[contains(@class,'x1e558r4') or contains(text(),'godz') or contains(text(),'wczoraj') or contains(text(),'min')]"
            )
            if not time_el:
                continue
            date_raw = time_el[0].text.strip()

            parsed_date = parse_relative_date(date_raw)
            if parsed_date is None:
                continue  # post starszy niż 3 dni → pomijamy

            # 2) tekst posta
            text_el = post.find_elements(By.XPATH, ".//div[@data-ad-comet-preview='message']")
            if not text_el:
                # próbujemy alternatywnie złapać tekst posta
                text_el = post.find_elements(By.XPATH, ".//div[contains(@class,'x1yztbdb')]")
                if not text_el:
                    continue
            text_content = text_el[0].text.strip()

            if len(text_content) < 20:
                continue

            posts.append((parsed_date, text_content))

        except Exception:
            continue

finally:
    driver.quit()


# Sort — najnowsze pierwsze
posts.sort(key=lambda x: x[0], reverse=True)

if not posts:
    send_telegram("Brak nowych postów z ostatnich 3 dni.")
else:
    for date_val, text in posts:
        msg = f"<b>MPWiK Mysłowice – {date_val.strftime('%d.%m.%Y')}</b>\n\n{text}"
        send_telegram(msg)
        time.sleep(1)
