import yfinance as yf
import pandas as pd
import requests
from io import StringIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import time
from datetime import time
import asyncio

# =========================
# GLOBAL STATE
# =========================
BOT_ACTIVE = True

# =========================
# AMBIL SAHAM IDX
# =========================
def get_all_idx_stocks():
    url = "https://www.idx.co.id/Portals/0/StaticData/ListedCompanies/StockCode/StockCode.csv"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(StringIO(res.text))
        symbols = df['Kode Saham'].dropna().tolist()
        return [f"{s}.JK" for s in symbols if isinstance(s, str)]
    except:
        return ["BBRI.JK", "BBCA.JK", "TLKM.JK"]

# =========================
# SCAN LOGIC
# =========================
def scan_market():
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

            time.sleep(0.2)

        except:
            continue

    results = sorted(results, key=lambda x: x['score'], reverse=True)

    message = "📊 BPJS ALL MARKET\n\n"

    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        for r in results[:7]:
            message += f"{r['label']} {r['symbol']}\n"
            message += f"{r['change']}% | Vol {r['volume_ratio']}x\n\n"

    return message

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_ACTIVE
    BOT_ACTIVE = True
    await update.message.reply_text("🟢 BOT AKTIF")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_ACTIVE
    BOT_ACTIVE = False
    await update.message.reply_text("🔴 BOT DIMATIKAN")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = "AKTIF 🟢" if BOT_ACTIVE else "MATI 🔴"
    await update.message.reply_text(f"Status bot: {state}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 BOT NYALA NORMAL")

async def scan_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Scan dimulai...")
    result = scan_market()
    await update.message.reply_text(result)

# =========================
# AUTO SCAN (09:00)
# =========================
async def auto_scan(context: ContextTypes.DEFAULT_TYPE):
    global BOT_ACTIVE

    if not BOT_ACTIVE:
        return

    chat_id = os.getenv("CHAT_ID")

    await context.bot.send_message(chat_id=chat_id, text="🤖 Auto scan mulai...")
    result = scan_market()
    await context.bot.send_message(chat_id=chat_id, text=result)
    await context.bot.send_message(chat_id=chat_id, text="✅ Scan selesai")

# =========================
# MAIN
# =========================
def main():
    TOKEN = os.getenv("TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("scan", scan_now))

    # schedule jam 9 pagi
    app.job_queue.run_daily(auto_scan, time=time(hour=9, minute=0))

    print("BOT JALAN 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
