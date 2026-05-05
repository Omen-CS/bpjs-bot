import requests
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import time as datetime_time
import os
import time
import json

# =========================
# GLOBAL STATE
# =========================
BOT_ACTIVE = True
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# =========================
# GET ALL IDX STOCKS - FALLBACK LIST
# =========================
def get_all_idx_stocks():
    """Coba ambil dari CSV, kalau gagal pake fallback list"""
    
    fallback_stocks = [
        "BBRI", "BBCA", "TLKM", "ASII", "UNVR", "INDF", "GGRM", "HMSP", "JSMR", "LPKR",
        "PGAS", "PTBA", "SMGR", "TINS", "WIKA", "ADRO", "BMTR", "BRPT", "CTRA", "EXCL",
    ]
    
    try:
        url = "https://www.idx.co.id/Portals/0/StaticData/ListedCompanies/StockCode/StockCode.csv"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        df = pd.read_csv(res.text)
        symbols = df['Kode Saham'].dropna().tolist()
        result = [s.strip() for s in symbols if isinstance(s, str)]
        print(f"✓ Got {len(result)} stocks from IDX CSV")
        return result
    except Exception as e:
        print(f"✗ CSV gagal, pake fallback")
        return fallback_stocks

# =========================
# GET DATA FROM ALPHA VANTAGE
# =========================
def get_stock_data_av(symbol):
    """Get data dari Alpha Vantage dengan logging detail"""
    if not ALPHA_VANTAGE_KEY:
        print(f"  ⚠️ API KEY NOT SET!")
        return None
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": f"{symbol}.JK",
            "apikey": ALPHA_VANTAGE_KEY,
            "outputsize": "compact"
        }
        
        print(f"  → API call: {symbol}.JK...", end=" ", flush=True)
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        # LOG RESPONSE
        if "Error Message" in data:
            print(f"❌ ERROR: {data['Error Message']}")
            return None
        
        if "Note" in data:
            print(f"⚠️ NOTE: {data['Note'][:50]}")
            return None
        
        if "information" in data:
            print(f"⚠️ INFO: {data['information'][:50]}")
            return None
        
        if "Time Series (Daily)" not in data:
            print(f"❌ NO TIME SERIES - Keys: {list(data.keys())}")
            return None
        
        ts = data["Time Series (Daily)"]
        print(f"✅ Got {len(ts)} days", end=" ")
        
        dates = sorted(ts.keys())[-30:]
        
        prices = []
        volumes = []
        highs = []
        
        for date in dates:
            prices.append(float(ts[date]["4. close"]))
            volumes.append(float(ts[date]["5. volume"]))
            highs.append(float(ts[date]["2. high"]))
        
        print(f"| Latest: {prices[-1]:.0f}")
        
        return {
            "prices": prices,
            "volumes": volumes,
            "highs": highs,
            "dates": dates
        }
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)[:60]}")
        return None

# =========================
# SCAN LOGIC
# =========================
def scan_market(limit=None):
    stocks = get_all_idx_stocks()
    if limit:
        stocks = stocks[:limit]
    
    results = []
    
    print(f"\n{'='*70}")
    print(f"🔍 SCANNING {len(stocks)} STOCKS | API Key: {ALPHA_VANTAGE_KEY[:10]}...")
    print(f"{'='*70}\n")

    for idx, symbol in enumerate(stocks):
        try:
            print(f"[{idx+1}/{len(stocks)}] {symbol}...", end=" ", flush=True)
            
            data = get_stock_data_av(symbol)
            
            if not data or len(data["prices"]) < 5:
                continue
            
            prices = data["prices"]
            volumes = data["volumes"]
            highs = data["highs"]
            
            latest_price = prices[-1]
            prev_price = prices[-2]
            current_volume = volumes[-1]
            current_high = highs[-1]
            
            change_pct = ((latest_price - prev_price) / prev_price) * 100
            
            ma20 = sum(prices[-20:]) / min(20, len(prices))
            vol_ma20 = sum(volumes[-20:]) / min(20, len(volumes))
            
            close_position = latest_price / current_high if current_high > 0 else 0
            
            # SCORING
            score = 0
            
            if current_volume > vol_ma20 * 0.8:
                score += 1
            
            if close_position >= 0.7:
                score += 1
            
            if latest_price > ma20 * 0.95:
                score += 1
            
            if change_pct > 0:
                score += 1
            
            if 1 <= change_pct <= 5:
                score += 1
            
            if score < 1:
                continue
            
            label = "🔥 STRONG" if score >= 4 else "⚡ WATCH"
            
            results.append({
                "symbol": symbol,
                "score": score,
                "change": round(change_pct, 2),
                "price": round(latest_price, 2),
                "volume_ratio": round(current_volume / vol_ma20, 2),
                "label": label
            })
            
            time.sleep(0.1)
        
        except Exception as e:
            print(f"ERROR: {str(e)[:40]}")
            continue
    
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    print(f"\n{'='*70}")
    print(f"📊 TOTAL RESULTS: {len(results)} stocks")
    print(f"{'='*70}\n")
    
    message = "📊 BPJS ALL MARKET\n"
    message += f"🕐 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if len(results) == 0:
        message += "❌ Ga ada saham valid hari ini"
    else:
        for r in results[:10]:
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
    await update.message.reply_text("⏳ Scan dimulai...\n⏱️ Tunggu 2-3 menit")
    result = scan_market()
    await update.message.reply_text(result)

async def test_sample(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Test 2 saham...\n⏱️ Check console untuk detail")
    result = scan_market(limit=2)
    await update.message.reply_text(result)

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Debug mode...\n⏱️ Check console")
    result = scan_market(limit=3)
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
        await context.bot.send_message(chat_id=chat_id, text="🤖 Auto scan jam 9 pagi mulai...")
        result = scan_market()
        await context.bot.send_message(chat_id=chat_id, text=result)
    except Exception as e:
        print(f"Error: {e}")

# =========================
# MAIN
# =========================
def main():
    TOKEN = os.getenv("TOKEN")
    
    if not TOKEN:
        print("❌ TOKEN not found!")
        return
    
    print(f"API KEY: {ALPHA_VANTAGE_KEY[:15]}..." if ALPHA_VANTAGE_KEY else "❌ NO API KEY")
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("scan", scan_now))
    app.add_handler(CommandHandler("test_sample", test_sample))
    app.add_handler(CommandHandler("debug", debug))
    
    # Schedule jam 9 pagi WIB (UTC+7)
    app.job_queue.run_daily(auto_scan, time=datetime_time(hour=2, minute=0))  # 2 UTC = 9 WIB
    
    print("🔥 BOT JALAN - Detailed logging ON")
    app.run_polling()

if __name__ == "__main__":
    main()
