import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

TELEGRAM_BOT_TOKEN = "8457272120:AAG4b8uvOG2gb20raSlFP52OikwQ-5L1sT8"
CHAT_ID = "1233434142"

FB_URL = "https://www.facebook.com/mpwik.myslowice/?locale=pl_PL"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=payload)


def get_today_posts():
    response = requests.get(FB_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(FB_URL)

    time.sleep(5)

    posts = []

    articles = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')

    for art in articles:
        try:
            text_block = art.text
            spans = art.find_elements(By.TAG_NAME, "span")
            detected_date = None
            for s in spans:
                if any(m in s.text for m in ["2023", "2024", "2025", "2026"]):
                    detected_date = s.text.strip()
                    break
            if not detected_date:
                continue
            try:
                post_date = datetime.strptime(detected_date, "%d.%m.%Y")
            except:
                continue
            if post_date.date() == datetime.today().date():
                posts.append((detected_date, text_block))
            else:
                break
        except Exception:
            continue

    driver.quit()

    return posts


if __name__ == "__main__":
    posts_today = get_today_posts()

    for _, text in posts_today:
        send_telegram_message(text)
