import time
import requests
from datetime import datetime

TELEGRAM_TOKEN = "8727573455:AAGwyHHTDMLtCSc3Cfxo_hAU7BGSInU_A0k"
CHAT_ID = "285441898"

def send_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Помилка відправки у Telegram: {e}")

def fetch_mexc():
    url = "https://contract.mexc.com/api/v1/contract/ticker"
    r = requests.get(url).json()
    return {item["symbol"]: float(item.get("lastPrice", 0)) for item in r.get("data", [])}

def fetch_gate():
    url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
    r = requests.get(url).json()
    return {item["contract"]: float(item.get("last", 0)) for item in r}

# --- читаємо список пар ---
with open(r"C:\Users\Vit\qwer\mg.txt", "r", encoding="utf-8") as f:
    pairs = [line.strip() for line in f.readlines()]

# --- видаляємо небажані інструменти ---
exclude = {
    "MEXC:HK50USDT.P/GATE:HK50USDT.P",
    "MEXC:RTXUSDT.P/GATE:RTXUSDT.P",
    "MEXC:FUNUSDT.P/GATE:FUNUSDT.P",
    "MEXC:ALLUSDT.P/GATE:ALLUSDT.P"
}
pairs = [p for p in pairs if p not in exclude]

print("Завантажені інструменти:")
for p in pairs:
    print(p)

# --- зберігаємо останні High/Low для антиспаму ---
last_high = {}
last_low = {}

while True:
    try:
        mexc_prices = fetch_mexc()
        gate_prices = fetch_gate()

        for p in pairs:
            try:
                left, right = p.split("/")
                ex1, sym1 = left.split(":")
                ex2, sym2 = right.split(":")

                base1 = sym1.replace("USDT.P", "_USDT")
                base2 = sym2.replace("USDT.P", "_USDT")

                price1 = mexc_prices.get(base1) if ex1 == "MEXC" else gate_prices.get(base1)
                price2 = mexc_prices.get(base2) if ex2 == "MEXC" else gate_prices.get(base2)

                if not price1 or not price2:
                    print(f"⚠️ Дані відсутні для {p}")
                    continue

                ratio = round(price1 / price2, 4)
                deviation = round((ratio - 1) * 100, 2)  # D% від 1
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(f"{p} → {ratio} ({deviation}%)")

                msg = None
                # --- Умови алерту ---
                if ratio >= 1.03:
                    # новий High
                    if p not in last_high or ratio > last_high[p]:
                        msg = f"🚨 АЛЕРТ! {p} → {ratio} ({deviation}%) вище +3% | {now}"
                        last_high[p] = ratio
                elif ratio <= 0.97:
                    # новий Low
                    if p not in last_low or ratio < last_low[p]:
                        msg = f"🚨 АЛЕРТ! {p} → {ratio} ({deviation}%) нижче -3% | {now}"
                        last_low[p] = ratio

                # --- Виділення сильних алертів (>10%) ---
                if msg and abs(deviation) >= 10:
                    msg = msg.replace("🚨 АЛЕРТ!", "🔥 СИЛЬНИЙ АЛЕРТ!")

                if msg:
                    print(msg)
                    send_alert(msg)

                # --- Обнулення антиспаму при поверненні в зону 0.99–1.01 ---
                if 0.99 <= ratio <= 1.01:
                    last_high[p] = None
                    last_low[p] = None

            except Exception as e:
                print(f"Помилка для {p}: {e}")

    except Exception as e:
        print(f"Помилка отримання даних: {e}")

    time.sleep(10)