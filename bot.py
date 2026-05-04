import yfinance as yf
import pandas as pd
import requests
from telegram import Bot
import os

def get_all_idx_stocks():
    url = "https://www.idx.co.id/Portals/0/StaticData/ListedCompanies/StockCode/StockCode.csv"
    df = pd.read_csv(url)
    symbols = df['Kode Saham'].tolist()
    return [f"{s}.JK" for s in symbols if isinstance(s, str)]

def main():
    TOKEN = os.getenv("TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")

    bot = Bot(token=TOKEN)

    stocks = get_all_idx_stocks()
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

        except:
            continue

    results = sorted(results, key=lambda x: x['score'], reverse=True)

    message = "📊 BPJS ALL MARKET\n\n"

    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        for r in results[:7]:
            message += f"{r['label']} {r['symbol']}\n"
            message += f"Score: {r['score']} | {r['change']}% | Vol {r['volume_ratio']}x\n\n"

    bot.send_message(chat_id=CHAT_ID, text=message)

if __name__ == "__main__":
    main()