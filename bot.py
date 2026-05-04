import requests
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import time as datetime_time
import os
import time
import asyncio
import json

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
        return [s.strip() for s in symbols if isinstance(s, str)][:20]  # Limit 20 for testing
    except Exception as e:
        print(f"Error getting IDX stocks: {e}")
        return ["BBRI", "BBCA", "TLKM", "ASII", "UNVR"]

# =========================
# GET DATA FROM STOCKBIT
# =========================
def get_stockbit_data(symbol):
    """Ambil data dari Stockbit API - menggunakan endpoint yang berbeda"""
    try:
        # Try endpoint 1: /api/v2/stock/{symbol}
        url = f"https://api.stockbit.com/v2/stocks/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG {symbol}: {json.dumps(data, indent=2)[:200]}")
            return data
        else:
            print(f"Error {symbol}: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error fetching {symbol} from Stockbit: {e}")
        return None

# =========================
# ALTERNATIVE: YahooFinance dengan Fallback
# =========================
def get_stock_data_fallback(symbol):
    """Fallback ke Yahoo Finance jika Stockbit gagal"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.JK")
        hist = ticker.history(period="5d")
        
        if len(hist) < 2:
            return None
            
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        
        change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
        current_price = latest['Close']
        volume = latest['Volume']
        
        return {
            "change": round(change_pct, 2),
            "price": round(current_price, 2),
            "volume": volume
        }
    except Exception as e:
        print(f"Fallback error for {symbol}: {e}")
        return None

# =========================
# SCAN LOGIC
# =========================
def scan_market():
    stocks = get_all_idx_stocks()
    results = []
    
    print(f"\n🔍 Scanning {len(stocks)} stocks...\n")

    for idx, symbol in enumerate(stocks):
        try:
            print(f"[{idx+1}/{len(stocks)}] Checking {symbol}...")
            
            # Try Stockbit first
            data = get_stockbit_data(symbol)
            
            # Fallback to Yahoo Finance
            if not data:
                print(f"  → Fallback to Yahoo Finance for {symbol}")
                data = get_stock_data_fallback(symbol)
            
            if not data:
                print(f"  → Skipped (no data)")
                continue

            # Extract data
            change_pct = data.get('change', 0)
            current_price = data.get('price', 0)
            
            if current_price == 0:
                continue

            score = 0

            # Score calculation
            if 1 <= change_pct <= 4:
                score += 2
            elif change_pct > 5:
                score -= 2
            
            if change_pct > 0:
                score += 1

            if current_price > 1000:
                score += 1

            if score < 0:
                continue

            label = "🔥 STRONG" if score >= 5 else "⚡ WATCH"

            results.append({
                "symbol": symbol,
                "score": score,
                "change": change_pct,
                "price": current_price,
                "label": label
            })
            
            print(f"  ✓ Added to results (score: {score})")

            time.sleep(0.2)

        except Exception as e:
            print(f"  ✗ Error scanning {symbol}: {e}")
            continue

    results = sorted(results, key=lambda x: x['score'], reverse=True)

    message = "📊 BPJS ALL MARKET\n"
    message += f"Waktu: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        message += f"✅ Found {len(results)} valid stocks\n\n"
        for r in results[:7]:
            message += f"{r['label']} {r['symbol']}\n"
            message += f"Rp {r['price']} | {r['change']:+.2f}%\n\n"

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
    await update.message.reply_text("⏳ Scan dimulai...\n(Silahkan tunggu 30-60 detik)")
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
