import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# ================== KONFIGURACJA ==================
TELEGRAM_BOT_TOKEN = "8457272120:AAG4b8uvOG2gb20raSlFP52OikwQ-5L1sT8"
CHAT_ID = "1233434142"  
FB_URL = "https://www.facebook.com/mpwik.myslowice"

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Błąd wysyłania do Telegrama:", e)


def scroll_and_load_all_posts(driver, max_scrolls=15):
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)


def parse_relative_date(text):
    text = text.lower().strip()
    today = datetime.today().date()
    
    if "właśnie" in text or "minut" in text or "godzin" in text and "1" in text:
        return today
    elif "wczoraj" in text:
        return today - timedelta(days=1)
    elif "2 dni temu" in text:
        return today - timedelta(days=2)
    elif "3 dni temu" in text:
        return today - timedelta(days=3)
    else:
        return None


def get_recent_posts():
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
    
    try:
        driver.get(FB_URL)
        print("Ładowanie strony...")
        time.sleep(8)

        # Czekamy aż się załaduje przynajmniej jeden post
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'MPWiK') or contains(text(), 'awaria') or contains(text(), 'wod') or contains(text(), 'przerwa')]"))
        )

        print("Scrolluję w poszukiwaniu nowych postów...")
        scroll_and_load_all_posts(driver, max_scrolls=20)

        # Nowy, niezawodny selektor 2024/2025
        post_elements = driver.find_elements(By.XPATH, 
            "//div[@data-ad-comet-preview='message']//div//span/..//span/..")
        
        found_posts = []

        for el in post_elements:
            try:
                full_text = el.text
                if len(full_text) < 20:  # za krótkie to raczej nie post
                    continue

                # Szukamy daty w pobliżu (najbliższy element z datą)
                parent = el.find_element(By.XPATH, "./ancestor::div[descendant::abbr]")
                abbr = parent.find_element(By.TAG_NAME, "abbr")
                date_text = abbr.text if abbr else ""

                post_date = parse_relative_date(date_text)
                if not post_date:
                    continue

                days_ago = (datetime.today().date() - post_date).days
                if 0 <= days_ago <= 2:  # ostatnie 3 dni (włącznie z dzisiaj)
                    clean_text = full_text.strip()
                    if clean_text not in [p[1] for p in found_posts]:  # unikamy duplikatów
                        found_posts.append((post_date, clean_text))
                        print(f"Znaleziono post z {post_date}: {clean_text[:100]}...")
            except Exception:
                continue

        # Sortujemy od najnowszego
        found_posts.sort(reverse=True)
        return found_posts

    except Exception as e:
        send_telegram(f"⚠️ Błąd scrapera MPWiK: {e}")
        print("Błąd:", e)
    finally:
        driver.quit()

    return []


if __name__ == "__main__":
    print(f"Start sprawdzania o {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    posts = get_recent_posts()

    if not posts:
        print("Nie znaleziono żadnych nowych postów z ostatnich 3 dni.")
    else:
        for date, text in posts:
            message = f"<b>MPWiK Myslowice – {date.strftime('%d.%m.%Y')}</b>\n\n{text}"
            send_telegram(message)
            time.sleep(1)  # na wszelki wypadek anty-flood
