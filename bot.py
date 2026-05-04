import requests
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import time as datetime_time
import os
import time
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
        df = pd.read_csv(res.text)
        symbols = df['Kode Saham'].dropna().tolist()
        return [s.strip() for s in symbols if isinstance(s, str)]
    except Exception as e:
        print(f"Error getting IDX stocks: {e}")
        return ["BBRI", "BBCA", "TLKM"]

# =========================
# GET DATA FROM STOCKBIT
# =========================
def get_stockbit_data(symbol):
    """Ambil data dari Stockbit API"""
    try:
        url = f"https://stockbit.com/api/v2/stock/{symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching {symbol} from Stockbit: {e}")
        return None

def get_stockbit_technical(symbol):
    """Ambil data technical dari Stockbit"""
    try:
        url = f"https://stockbit.com/api/v2/stock/{symbol}/technical"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching technical {symbol}: {e}")
        return None

# =========================
# SCAN LOGIC (STOCKBIT)
# =========================
def scan_market():
    stocks = get_all_idx_stocks()
    results = []

    for symbol in stocks:
        try:
            # Get basic data
            data = get_stockbit_data(symbol)
            if not data:
                continue

            # Get technical data
            tech = get_stockbit_technical(symbol)

            # Extract data
            price = data.get('price', {})
            change_pct = price.get('change', 0)
            current_price = price.get('current', 0)
            
            if current_price == 0:
                continue

            volume = data.get('volume', 0)
            market_cap = data.get('market_cap', 0)

            # Get technical indicators
            ma20 = None
            rsi = None
            if tech:
                indicators = tech.get('indicators', {})
                ma20 = indicators.get('ma20')
                rsi = indicators.get('rsi')

            score = 0

            # Score calculation
            if 1 <= change_pct <= 4:
                score += 2
            elif change_pct > 5:
                score -= 2

            if ma20 and current_price > ma20:
                score += 1

            if volume > 0:
                score += 1

            if market_cap > 3_000_000_000:  # 3 miliar
                score += 1

            if rsi and 40 <= rsi <= 70:
                score += 2

            if score < 0:
                continue

            label = "🔥 STRONG" if score >= 6 else "⚡ WATCH"

            results.append({
                "symbol": symbol,
                "score": score,
                "change": round(change_pct, 2),
                "price": round(current_price, 2),
                "label": label
            })

            time.sleep(0.3)

        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            continue

    results = sorted(results, key=lambda x: x['score'], reverse=True)

    message = "📊 BPJS ALL MARKET\n"
    message += f"Waktu: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        for r in results[:7]:
            message += f"{r['label']} {r['symbol']}\n"
            message += f"Rp {r['price']} | {r['change']}%\n\n"

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

    try:
        await context.bot.send_message(chat_id=chat_id, text="🤖 Auto scan mulai...")
        result = scan_market()
        await context.bot.send_message(chat_id=chat_id, text=result)
        await context.bot.send_message(chat_id=chat_id, text="✅ Scan selesai")
    except Exception as e:
        print(f"Error in auto_scan: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")

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
    app.job_queue.run_daily(auto_scan, time=datetime_time(hour=9, minute=0))

    print("BOT JALAN 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
