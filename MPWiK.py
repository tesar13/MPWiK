# MPWiK.py – wersja 2025/2026 – działa na każdej publicznej stronie FB
import os
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests

# === KONFIGURACJA ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8457272120:AAG4b8uvOG2gb20raSlFP52OikwQ-5L1sT8")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1233434142")

# ←←← TU ZMIENIAJ URL (tylko ta jedna linijka!) ←←←
FB_URL = "https://www.facebook.com/ZiemiaChrzanowska"
#FB_URL = "https://www.facebook.com/inna.strona.do.testow"   # odkomentuj do testów

# === Telegram ===
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text[:4090],       # Telegram max 4096 znaków
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass


# === Selenium – maksymalne ukrycie przed detekcją FB ===
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
})

posts_found = []

try:
    print("Otwieram stronę:", FB_URL)
    driver.get(FB_URL)
    time.sleep(8)

    # Czekamy aż się załaduje cokolwiek z postami
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//div[@data-ad-comet-preview='message'] | //span[contains(text(),'godzin')] | //span[contains(text(),'wczoraj')]"))
    )

    # Scrollujemy – bardzo ważne!
    print("Scrolluję w dół…")
    for _ in range(12):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.5)

    # Najnowszy działający selektor 2025/2026
    post_blocks = driver.find_elements(By.XPATH, 
        "//div[contains(@class,'x1yztbdb')]//div[@data-ad-comet-preview='message']//span/..")

    print(f"Znaleziono {len(post_blocks)} potencjalnych bloków z tekstem")

    today = datetime.today().date()

    for block in post_blocks:
        try:
            text = block.text.strip()
            if len(text) < 30:          # za krótkie – pomijamy
                continue

            # Szukamy elementu z datą w okolicy tego bloku
            parent = block.find_element(By.XPATH, "./ancestor::div[30]")  # szeroki zakres
            time_elem = parent.find_elements(By.XPATH, ".//abbr | .//span[contains(text(),'godzin')] | .//span[contains(text(),'wczoraj')] | .//span[contains(text(),'dzień')] | .//span[contains(text(),'minut')]")

            if not time_elem:
                continue
            date_str = time_elem[0].text.lower()

            # Parsowanie względnej daty
            if any(x in date_str for x in ["min", "godz", "właśnie"]):
                post_date = today
            elif "wczoraj" in date_str or "1 dzie" in date_str:
                post_date = today - timedelta(days=1)
            elif "2 dni" in date_str:
                post_date = today - timedelta(days=2)
            elif "3 dni" in date_str:
                post_date = today - timedelta(days=3)
            else:
                continue  # starsze niż 3 dni

            # Odfiltruj duplikaty i reklamy
            if text not in [p[1] for p in posts_found] and "został" not in text.lower()[:30]:
                posts_found.append((post_date, text))
                print(f"ZNALEZIONO POST z {post_date}: {text[:100]}…")

        except Exception as e:
            continue

finally:
    driver.quit()

# Sortuj od najnowszego i wyślij
posts_found.sort(reverse=True)

if not posts_found:
    send_telegram("MPWiK scraper się wykonał – brak nowych postów z ostatnich 3 dni")
else:
    for date, text in posts_found:
        msg = f"<b>MPWiK Mysłowice – {date.strftime('%d.%m.%Y')}</b>\n\n{text}"
        send_telegram(msg)
        time.sleep(1.5)   # anty-flood Telegram

