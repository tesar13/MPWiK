import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import requests

# == KONFIGURACJA ==
TELEGRAM_BOT_TOKEN = "8457272120:AAG4b8uvOG2gb20raSlFP52OikwQ-5L1sT8"
CHAT_ID = "1233434142"

FB_URL = "https://www.facebook.com/mpwik.myslowice"
LAST_POST_FILE = "last_post.txt"   # plik w repo — musi być commitowany!


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


def load_last_post():
    if not os.path.exists(LAST_POST_FILE):
        return None
    with open(LAST_POST_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_last_post(text):
    with open(LAST_POST_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip())


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

try:
    driver.get(FB_URL)
    time.sleep(6)

    # Scroll dla pewności
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # Pobieramy *pierwszy* post na stronie
    post = driver.find_element(
        By.XPATH,
        "(//div[@role='article'])[1]"
    )

    # 1) Klikamy w „See more / Wyświetl więcej” jeśli jest
    try:
        see_more = post.find_element(By.XPATH, ".//div[@role='button' and contains(., 'See')]")
        driver.execute_script("arguments[0].click();", see_more)
        time.sleep(0.5)
    except:
        pass

    # 2) Pobieramy pełną treść
    text_el = post.find_element(
        By.XPATH,
        ".//div[@data-ad-comet-preview='message']"
    )

    text = text_el.text.strip()

finally:
    driver.quit()

# == porównujemy z ostatnio wysłanym ==
last = load_last_post()

if last == text:
    print("Brak nowych postów – nie wysyłam nic.")
else:
    print("Nowy post wykryty – wysyłam do Telegrama.")
    msg = f"<b>MPWiK – najnowszy post</b>\n\n{text}"
    send_telegram(msg)
    save_last_post(text)
