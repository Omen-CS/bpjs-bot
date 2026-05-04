import requests
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import time as datetime_time
import os
import time
import yfinance as yf

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
        result = [s.strip() for s in symbols if isinstance(s, str)][:15]
        print(f"✓ Got {len(result)} stocks from IDX")
        return result
    except Exception as e:
        print(f"✗ Error getting IDX stocks: {e}")
        return ["BBRI", "BBCA", "TLKM", "ASII", "UNVR", "INDF", "GGRM"]

# =========================
# SCAN LOGIC
# =========================
def scan_market():
    stocks = get_all_idx_stocks()
    results = []
    
    print(f"\n{'='*60}")
    print(f"🔍 SCANNING {len(stocks)} STOCKS")
    print(f"{'='*60}\n")

    for idx, symbol in enumerate(stocks):
        try:
            print(f"[{idx+1}/{len(stocks)}] {symbol}...", end=" ")
            
            # Get data dengan .JK suffix
            ticker_str = f"{symbol}.JK"
            data = yf.download(ticker_str, period="30d", interval="1d", progress=False, timeout=10)

            if len(data) < 5:
                print(f"❌ Tidak cukup data ({len(data)} days)")
                continue

            latest = data.iloc[-1]
            prev = data.iloc[-2]

            change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
            current_price = latest['Close']
            volume = latest['Volume']
            high = latest['High']
            
            ma20 = data['Close'].rolling(20).mean().iloc[-1]
            vol_ma20 = data['Volume'].rolling(20).mean().iloc[-1]

            if high == 0 or current_price == 0:
                print(f"❌ Invalid price")
                continue

            close_position = current_price / high

            # SIMPLE SCORING
            score = 0
            
            # Score: Change 1-4%
            if 1 <= change_pct <= 4:
                score += 2
            elif change_pct > 5:
                score -= 2
            
            # Score: Close > MA20
            if current_price > ma20:
                score += 1
            
            # Score: Volume > 1.5x avg
            if volume > vol_ma20 * 1.5:
                score += 1
            
            # Score: Closing position >= 80%
            if close_position >= 0.8:
                score += 2

            print(f"change={change_pct:.2f}% price={current_price:.0f} vol_ratio={volume/vol_ma20:.2f}x close_pos={close_position:.2f} → score={score}", end="")

            if score < 0:
                print(f" ❌ (negative score)")
                continue

            label = "🔥 STRONG" if score >= 6 else "⚡ WATCH"

            results.append({
                "symbol": symbol,
                "score": score,
                "change": round(change_pct, 2),
                "price": round(current_price, 2),
                "volume_ratio": round(volume / vol_ma20, 2),
                "label": label
            })
            
            print(f" ✅ ADDED")

            time.sleep(0.5)

        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            continue

    results = sorted(results, key=lambda x: x['score'], reverse=True)

    print(f"\n{'='*60}")
    print(f"📊 TOTAL RESULTS: {len(results)} stocks")
    print(f"{'='*60}\n")

    message = "📊 BPJS ALL MARKET\n"
    message += f"🕐 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        for r in results[:7]:
            message += f"{r['label']} {r['symbol']}\n"
            message += f"Rp {r['price']} | {r['change']:+.2f}% | Vol {r['volume_ratio']:.2f}x\n\n"

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
    await update.message.reply_text("⏳ Scan dimulai...\n⏱️ Tunggu 1-2 menit")
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
