import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import requests

# ================= KONFIGURACJA =================
TELEGRAM_BOT_TOKEN = "8457272120:AAG4b8uvOG2gb20raSlFP52OikwQ-5L1sT8"
CHAT_ID = "1233434142"
FB_URL = "https://www.facebook.com/mpwik.myslowice"
LAST_POST_FILE = "last_post.txt"          # musi być w repo i commitowany

# ================= Telegram =================
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text[:4000],
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=payload, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print("Błąd wysyłki →", e)


# ================= Last post =================
def load_last_post_hash():
    if not os.path.exists(LAST_POST_FILE):
        return ""
    with open(LAST_POST_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_last_post_hash(text):
    with open(LAST_POST_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip())


# ================= Selenium =================
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.page_load_strategy = 'eager'   # szybsze ładowanie

driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
})

try:
    print("Otwieram:", FB_URL)
    driver.get(FB_URL)

    wait = WebDriverWait(driver, 20)

    # Czekamy na jakikolwiek artykuł / post
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']")))

    # Scroll × 5–8 (wystarczająco na 3–5 najnowszych postów)
    for _ in range(7):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.2)

    # Bierzemy pierwszy (najnowszy) post
    post = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']")))

    # Rozwijamy wszystkie "Wyświetl więcej" / "See more" w obrębie posta
    try:
        see_more_buttons = post.find_elements(By.XPATH, ".//div[@role='button'][contains(., 'więcej') or contains(., 'more') or contains(@aria-label, 'more')]")
        for btn in see_more_buttons:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.4)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.8)
            except:
                pass
    except:
        pass

    # Najbardziej odporne sposoby na wyciągnięcie treści (2026)
    text = ""

    candidates = [
        # stary sposób (już rzadko działa)
        (By.XPATH, ".//div[@data-ad-comet-preview='message']"),
        # częsty w 2025/26 – div z dir="auto" i dużą ilością span
        (By.XPATH, ".//div[@dir='auto' and .//span]"),
        # bardzo szeroki – dowolny div z długim tekstem w poście
        (By.XPATH, ".//div[contains(@class, 'x1iorvi4') or contains(@class, 'x1lliihq')]//div[@dir='auto']"),
        # tekst z aria-label lub role
        (By.CSS_SELECTOR, "div[role='article'] div[dir='auto']"),
    ]

    for by, val in candidates:
        try:
            els = post.find_elements(by, val)
            for el in els:
                t = el.text.strip()
                if len(t) > 40:  # odrzucamy nagłówki, daty itp.
                    text += t + "\n\n"
            if text.strip():
                break
        except:
            continue

    text = text.strip()
    if not text:
        text = "[Nie udało się wyciągnąć czytelnej treści posta]"

    print("Wyciągnięty tekst:\n", text[:300], "..." if len(text) > 300 else "")

finally:
    driver.quit()


# ================= Logika wysyłki =================
last_hash = load_last_post_hash()
current_hash = text[:800]   # pierwsze 800 znaków jako "hash" (wystarczająco)

if last_hash == current_hash:
    print("Ten sam post → pomijam")
else:
    print("Nowy / zmieniony post → wysyłka")
    msg = f"<b>Nowy post MPWiK Mysłowice</b>  •  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{text}"
    send_telegram(msg)
    save_last_post_hash(current_hash)
