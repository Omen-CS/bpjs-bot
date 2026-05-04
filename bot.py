import yfinance as yf
import pandas as pd
import requests
from io import StringIO
from telegram import Bot
import os
import time

# =========================
# AMBIL LIST SAHAM IDX
# =========================
def get_all_idx_stocks():
    url = "https://www.idx.co.id/Portals/0/StaticData/ListedCompanies/StockCode/StockCode.csv"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(StringIO(res.text))
        symbols = df['Kode Saham'].dropna().tolist()
        return [f"{s}.JK" for s in symbols if isinstance(s, str)]
    except Exception as e:
        print("Gagal ambil IDX:", e)
        return ["BBRI.JK", "BBCA.JK", "TLKM.JK"]  # fallback

# =========================
# MAIN
# =========================
def main():
    TOKEN = os.getenv("8664485004:AAGwuuhlBw3ddkUIpM13OyO9bInJb7OORmQ")
    CHAT_ID = os.getenv("6214324961")

    if not TOKEN or not CHAT_ID:
        print("TOKEN / CHAT_ID belum diset")
        return

    bot = Bot(token=TOKEN)

    # 🔥 NOTIF BOT HIDUP
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Bot aktif & mulai scan...")
    except Exception as e:
        print("Gagal kirim status awal:", e)

    stocks = get_all_idx_stocks()
    print(f"Scan {len(stocks)} saham...")

    results = []

    for symbol in stocks:
        try:
            data = yf.download(symbol, period="30d", interval="1d", progress=False)

            if len(data) < 20:
                continue

            latest = data.iloc[-1]
            prev = data.iloc[-2]

            change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
            ma20 = data['Close'].rolling(20).mean().iloc[-1]
            vol_ma20 = data['Volume'].rolling(20).mean().iloc[-1]

            volume = latest['Volume']
            value = latest['Close'] * volume

            high = latest['High']
            close = latest['Close']

            if high == 0:
                continue

            close_position = close / high

            # =========================
            # SCORING
            # =========================
            score = 0

            if 1 <= change_pct <= 4:
                score += 2
            elif change_pct > 5:
                score -= 2

            if close > ma20:
                score += 1

            if volume > vol_ma20 * 2:
                score += 2
            elif volume > vol_ma20 * 1.5:
                score += 1

            if value > 3_000_000:
                score += 1

            if close_position >= 0.8:
                score += 2

            # FILTER KETAT
            if score < 4:
                continue

            label = "🔥 STRONG" if score >= 6 else "⚡ WATCH"

            results.append({
                "symbol": symbol,
                "score": score,
                "change": round(change_pct, 2),
                "volume_ratio": round(volume / vol_ma20, 2),
                "label": label
            })

            time.sleep(0.3)  # anti limit

        except Exception:
            continue

    # =========================
    # SORT
    # =========================
    results = sorted(results, key=lambda x: x['score'], reverse=True)

    # =========================
    # FORMAT MESSAGE
    # =========================
    message = "📊 BPJS ALL MARKET\n\n"

    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        for r in results[:7]:
            message += f"{r['label']} {r['symbol']}\n"
            message += f"Score: {r['score']} | {r['change']}% | Vol {r['volume_ratio']}x\n\n"

    # =========================
    # KIRIM HASIL
    # =========================
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print("Gagal kirim hasil:", e)

    # 🔥 NOTIF SELESAI
    try:
        bot.send_message(chat_id=CHAT_ID, text="✅ Scan selesai")
    except Exception as e:
        print("Gagal kirim status akhir:", e)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()
