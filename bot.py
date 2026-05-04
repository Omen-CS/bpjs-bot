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
# GET ALL IDX STOCKS - FALLBACK LIST
# =========================
def get_all_idx_stocks():
    """Coba ambil dari CSV, kalau gagal pake fallback list"""
    
    # Fallback list - saham IDX populer + mid-cap
    fallback_stocks = [
        "AALI", "ADRO", "ASII", "ASRI", "ASSA", "AUTO", "BBCA", "BBKP", "BBRI", "BBTN",
        "BCAP", "BCIC", "BDMN", "BENJ", "BIMP", "BKSL", "BMAS", "BMTR", "BNBA", "BNGA",
        "BNLI", "BPPT", "BRAU", "BRPT", "BSDE", "BTEL", "BULL", "BUMI", "CAKK", "CASS",
        "CENT", "CITA", "CMNP", "CMPP", "CMTX", "CNKO", "CNMA", "CPIN", "CTRA", "CTRS",
        "DADA", "DART", "DBIT", "DBRK", "DCII", "DEHP", "DEWA", "DEXA", "DFAM", "DGIK",
        "DGIN", "DHPP", "DIDI", "DISK", "DIVA", "DKFT", "DPLM", "DSSA",
        "DUTI", "DVLA", "DWGL", "ECII", "ECIP", "EDDY", "EKAD", "ELKO", "ELSA", "ELTY",
        "EMTK", "ENRG", "ENSO", "ENVY", "EPMT", "EPRO", "ERAA", "ERTX", "ESIP", "ESSA",
        "ESSM", "ESTL", "ETIC", "EULN", "EVAN", "EXCL", "EXIM", "EXIT", "EXTB", "FAPA",
        "FASW", "FBNS", "FBSL", "FCAP", "FCED", "FERI", "FIRE", "FISH", "FITT", "FKLI",
        "FLMA", "FLOW", "FLSP", "FMII", "FMPI", "FNSH", "FOOD", "FORE", "FPNI", "FRED",
        "FRIP", "FRSH", "FUEL", "FUJI", "GAIL", "GAIN", "GAMC", "GAMI", "GBLA", "GBRO",
        "GBTS", "GCAP", "GDYR", "GEMA", "GEND", "GENI", "GENM", "GERY", "GEST", "GFDU",
        "GFLD", "GGRM", "GHON", "GHPP", "GIAA", "GIDA", "GIGA", "GIKK", "GILM", "GINN",
        "GIPS", "GIPT", "GIRD", "GIRF", "GMCC", "GMTD", "GMTN", "GNAP", "GNFI", "GNSA",
        "GNSI", "GNSR", "GNUT", "GOLD", "GOLF", "GONE", "GOOD", "GORO", "GOWN", "GPRA",
        "GPSO", "GRAI", "GRAN", "GRHA", "GRIM", "GRNQ", "GRSI", "GRYA", "GSMF",
        "GTBO", "GTMA", "GTSI", "GTSM", "GTTS", "GUHA", "GUID", "GUNA", "GUNP", "GUST",
        "HAKA", "HAKT", "HALF", "HALO", "HALT", "HAMA", "HAMR", "HAND", "HANG", "HAPI",
        "INAF", "INAI", "INAP", "INCA", "INCF", "INCO", "INDF", "INDI", "INDX", "INDY",
        "INET", "INFA", "INFO", "INGA", "INGF", "INGH", "INGI", "INGP", "INGR", "INGS",
        "JPFA", "JRPT", "KAEF", "KAIR", "KKGI", "KLBF", "KMTR", "KOBX", "KOIN", "LPKR",
        "LPPF", "LSIP", "LTCM", "LTLN", "MAIN", "MAPC", "MAPA", "MAPB", "MAPS", "MARA",
        "MARK", "MAUN", "MAYA", "MBSS", "MCAS", "MCOL", "MCPP", "MCSM", "MDKA", "MDLN",
        "MDRN", "MEDC", "MEDH", "MEKA", "MELI", "MERK", "MFIN", "MGRO", "MIFA", "MIFX",
        "MIKA", "MIKB", "MIKC", "MIKD", "MIKE", "MIKI", "MIKJ", "MIKK", "MIKL", "MIKM",
        "MIKN", "MIKO", "MIKP", "MIKS", "MIKT", "MIKU", "MIKV", "MIKW", "MIKX", "MIKY",
        "MIKZ", "MINA", "MINB", "MINC", "MIND", "MINE", "MINF", "MING", "MINH", "MINI",
        "MINJ", "MINK", "MINL", "MINM", "MINN", "MINO", "MINP", "MINS", "MINT", "MINU",
        "MINV", "MINW", "MINX", "MINY", "MINZ", "MIPA", "MIPB", "MIPC", "MIPD", "MIPE",
        "MIPF", "MIPG", "MIPH", "MIPI", "MIPJ", "MIPK", "MIPL", "MIPM", "MIPN", "MIPO",
        "MIPP", "MIPS", "MIPT", "MIPU", "MIPV", "MIPW", "MIPX", "MIPY", "MIPZ", "MIRB",
        "MITA", "MITB", "MITC", "MITD", "MITE", "MITF", "MITG", "MITH", "MITI", "MITJ",
        "MITK", "MITL", "MITM", "MITN", "MITO", "MITP", "MITS", "MITT", "MITU", "MITV",
        "MITW", "MITX", "MITY", "MITZ", "MKPI", "MKWS", "MLPL", "MMLP", "MNEG", "MNIK",
        "MNSE", "MOIL", "MOLI", "MONK", "MONS", "MOPC", "MOPI", "MORO", "MORR", "MOST",
        "MOTB", "MOTI", "MOTO", "MOTP", "MOTS", "MOTT", "MOTU", "MOTV", "MOTW", "MOTX",
        "MOTY", "MOTZ", "MOVE", "MOWS", "MOXC", "MOXD", "MOXA", "MOXB", "MOXI", "MOXP",
        "MOXX", "MOYE", "MOYO", "MOYP", "MOYS", "MOYT", "MOYU", "MOYV", "MOYW", "MOYX",
        "MOYY", "MOYZ", "MPRO", "MRAT", "MRLN", "MRNA", "MRNY", "MROR", "MRSA", "MRSD",
        "MRSE", "MRSF", "MRSG", "MRSH", "MRSI", "MRSJ", "MRSK", "MRSL", "MRSM", "MRSN",
        "MRSO", "MRSP", "MRSS", "MRST", "MRSU", "MRSV", "MRSW", "MRSX", "MRSY", "MRSZ",
        "MTDL", "MTEM", "MTFB", "MTFP", "MTLC", "MTLA", "MTLN", "MTLP", "MTLS", "MTLT",
        "MTLU", "MTLV", "MTLW", "MTLX", "MTLY", "MTLZ", "MTOM", "MTPS", "MTTR", "MTSM",
    ]
    
    # Try to get dari CSV
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
        print(f"✗ CSV gagal ({str(e)[:30]}), pake fallback {len(fallback_stocks)} stocks")
        return fallback_stocks

# =========================
# SCAN LOGIC
# =========================
def scan_market(limit=None):
    stocks = get_all_idx_stocks()
    if limit:
        stocks = stocks[:limit]
    
    results = []
    
    print(f"\n{'='*60}")
    print(f"🔍 SCANNING {len(stocks)} STOCKS")
    print(f"{'='*60}\n")

    for idx, symbol in enumerate(stocks):
        try:
            print(f"[{idx+1}/{len(stocks)}] {symbol}...", end=" ", flush=True)
            
            # Get data dengan .JK suffix
            ticker_str = f"{symbol}.JK"
            data = yf.download(ticker_str, period="30d", interval="1d", progress=False, timeout=10)

            if len(data) < 5:
                print(f"❌ Tidak cukup data")
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
                print(f"❌ Invalid")
                continue

            close_position = current_price / high

            # ADJUSTED SCORING - LEBIH LENIENT
            score = 0
            
            # Base score: jika volume bagus
            if volume > vol_ma20 * 0.8:  # Kurang dari 1.5x
                score += 1
            
            # Score: Closing position >= 70% (turun dari 80%)
            if close_position >= 0.7:
                score += 1
            
            # Score: Close > MA20 (more lenient)
            if current_price > ma20 * 0.95:  # 95% of MA20
                score += 1
            
            # Score: Positive change (any positive)
            if change_pct > 0:
                score += 1
            
            # Bonus: Strong change 1-5%
            if 1 <= change_pct <= 5:
                score += 1

            if score < 1:  # Kurang dari 1 skip
                print(f"❌ (score {score})")
                continue

            label = "🔥 STRONG" if score >= 4 else "⚡ WATCH"

            results.append({
                "symbol": symbol,
                "score": score,
                "change": round(change_pct, 2),
                "price": round(current_price, 2),
                "volume_ratio": round(volume / vol_ma20, 2),
                "label": label
            })
            
            print(f"✅ (score {score})")

            time.sleep(0.2)

        except Exception as e:
            print(f"❌ {str(e)[:30]}")
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
    await update.message.reply_text("⏳ Scan dimulai...\n⏱️ Tunggu 2-3 menit untuk semua saham")
    result = scan_market()
    await update.message.reply_text(result)

async def test_sample(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Test 5 saham...\n⏱️ Tunggu sebentar")
    result = scan_market(limit=5)
    await update.message.reply_text(result)

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Debug mode: Checking data...\n⏱️ Tunggu 1-2 menit")
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
        await context.bot.send_message(chat_id=chat_id, text="🤖 Auto scan mulai...\n⏱️ Tunggu hasil")
        result = scan_market()
        await context.bot.send_message(chat_id=chat_id, text=result)
        await context.bot.send_message(chat_id=chat_id, text="✅ Scan selesai")
    except Exception as e:
        print(f"Error in auto_scan: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)[:100]}")

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
    app.add_handler(CommandHandler("test_sample", test_sample))
    app.add_handler(CommandHandler("debug", debug))

    # schedule jam 9 pagi
    app.job_queue.run_daily(auto_scan, time=datetime_time(hour=9, minute=0))

    print("BOT JALAN 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
