import os
import time
import re
import requests
import psycopg2
import threading
import telebot
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ARABIC_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
}

def format_arabic_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        day = dt.day
        month = ARABIC_MONTHS[dt.month]
        hour = dt.hour
        
        period = "صباحاً" if hour < 12 else "مساءً"
        hour_12 = hour % 12
        if hour_12 == 0:
            hour_12 = 12
            
        if dt.minute > 0:
            return f"{day} {month} الساعة {hour_12}:{dt.minute:02d} {period}"
        else:
            return f"{day} {month} الساعة {hour_12} {period}"
    except Exception:
        return date_str

def normalize_arabic(text):
    if not text: return ""
    text = re.sub(r'[أإآ]', 'ا', text)
    text = text.replace('ى', 'ي')
    text = text.replace('ة', 'ه')
    return text

def clean_team_name(name):
    if not name: return ""
    # Arabic cleaning
    name = re.sub(r'^(نادي|النادي|نادى|النادى)\s+', '', name)
    
    # تنظيف "للألعاب الرياضية" ومتغيراتها بالكامل أولاً لمنع بقاء حروف زائدة
    name = re.sub(r'\s+للألعاب\s+الرياضي[ةهىي]', '', name)
    name = re.sub(r'\s+للألعاب[ةهية]*', '', name)
    name = re.sub(r'\s+للالعاب\s+الرياضي[ةهىي]', '', name)
    name = re.sub(r'\s+للالعاب[ةهية]*', '', name)
    
    # تنظيف الكلمات الرياضية الأخرى
    name = name.replace(" الرياضية", "").replace(" الرياضيه", "")
    name = name.replace(" الرياضي", "").replace(" الرياضى", "")
    name = name.replace(" للرياضة", "").replace(" للرياضه", "")
    name = name.replace(" رياضي", "").replace(" رياضى", "")
    
    # English cleaning
    name = re.sub(r'\s+(SC|FC|Club)$', '', name, flags=re.IGNORECASE)
    return name.strip()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PUBLIC_CHAT_ID = os.getenv("PUBLIC_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

# التحقق من وجود المتغيرات الأساسية قبل بدء البوت
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ خطأ: لم يتم العثور على متغير البيئة TELEGRAM_BOT_TOKEN. يرجى التأكد من ضبطه في ملف .env أو في إعدادات البيئة (Environment Variables) للمستضيف.")
if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ خطأ: لم يتم العثور على متغير البيئة TELEGRAM_CHAT_ID. يرجى التأكد من ضبطه في ملف .env أو في إعدادات البيئة للمستضيف.")
if not DATABASE_URL:
    raise ValueError("❌ خطأ: لم يتم العثور على متغير البيئة DATABASE_URL. يرجى التأكد من ضبطه في ملف .env أو في إعدادات البيئة للمستضيف.")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

API_URL       = "https://tazkarti.com/data/matches-list-json.json"
QUEUE_API_URL = "https://tazkarti.com/data/fanQueuesMatch-list-json.json"
SEATS_API_URL = "https://tazkarti.com/data/TicketPrice-AvailableSeats-{match_id}.json"
MATCHES_URL   = "https://tazkarti.com/#/matches"
CHECK_INTERVAL_SECONDS = 2

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
]

PROXY_URL = os.getenv("PROXY_URL")

def get_random_headers():
    ua = random.choice(USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://tazkarti.com/",
        "Origin": "https://tazkarti.com",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

session = requests.Session()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}

STATUS_OPEN   = 1
STATUS_CLOSED = 2
# Status 3 = مباراة جارية أو انتهت، نتجاهلها تماماً

EGYPTIAN_LEAGUE_TEAMS = [
    "الأهلي", "الزمالك", "الإسماعيلي", "المصري",
    "الاتحاد", "غزل المحلة", "بلدية المحلة", "منتخب مصر",
    "Al Ahly", "Zamalek", "ISMAILY", "Ismaily", "Al Masry",
    "Alithad", "Ittihad", "Ghazl Elmahala", "Baladiyat", "Egypt"
]

TEAM_COLORS = {
    "الأهلي": "🔴", "Al Ahly": "🔴",
    "الزمالك": "⚪", "Zamalek": "⚪",
    "الإسماعيلي": "🟡", "ISMAILY": "🟡", "Ismaily": "🟡",
    "المصري": "🟢", "Al Masry": "🟢",
    "الاتحاد": "🟢", "Alithad": "🟢", "Ittihad": "🟢",
    "غزل المحلة": "🔵", "Ghazl Elmahala": "🔵",
    "بلدية المحلة": "🟠", "Baladiyat": "🟠",
    "مصر": "🔴", "Egypt": "🔴"
}

# ==========================================
# 💾 Neon PostgreSQL
# ==========================================
def get_db():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ خطأ في DB: {e}")
        return None

def init_db():
    conn = get_db()
    if conn:
        c = conn.cursor()
        try:
            # جدول حالة الحجز والطابور لكل مباراة
            c.execute('''
                CREATE TABLE IF NOT EXISTS match_status_tracker (
                    match_id      BIGINT PRIMARY KEY,
                    last_status   INTEGER NOT NULL,
                    last_is_queue BOOLEAN NOT NULL DEFAULT FALSE,
                    team1_ar      TEXT,
                    team2_ar      TEXT,
                    stadium       TEXT,
                    kick_off      TEXT,
                    gates_open    TEXT
                )
            ''')
            # جدول تتبع حالة sold_out لكل درجة في كل مباراة
            c.execute('''
                CREATE TABLE IF NOT EXISTS category_soldout_tracker (
                    match_id      BIGINT NOT NULL,
                    category_id   BIGINT NOT NULL,
                    category_name TEXT,
                    price         NUMERIC,
                    last_soldout  BOOLEAN NOT NULL DEFAULT FALSE,
                    PRIMARY KEY (match_id, category_id)
                )
            ''')
            # جدول الإشعارات المؤجلة لإرسالها للقناة العامة بعد 10 دقائق
            c.execute('''
                CREATE TABLE IF NOT EXISTS delayed_notifications (
                    id             SERIAL PRIMARY KEY,
                    message_text   TEXT NOT NULL,
                    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    sent           BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        finally:
            c.close()
            conn.close()

MATCH_STATE_CACHE = {}
CATEGORY_SOLDOUT_CACHE = {}
OPEN_MATCHES_CACHE = {}

def load_state_from_db():
    global MATCH_STATE_CACHE, CATEGORY_SOLDOUT_CACHE, OPEN_MATCHES_CACHE
    conn = get_db()
    if conn:
        try:
            c = conn.cursor()
            c.execute("SELECT match_id, last_status, last_is_queue FROM match_status_tracker")
            for row in c.fetchall():
                MATCH_STATE_CACHE[row[0]] = (row[1], row[2])
                
            c.execute("SELECT match_id, category_id, last_soldout FROM category_soldout_tracker")
            for row in c.fetchall():
                CATEGORY_SOLDOUT_CACHE[(row[0], row[1])] = row[2]
                
            c.execute("SELECT match_id, team1_ar, team2_ar, stadium, kick_off FROM match_status_tracker WHERE last_status = 1")
            for row in c.fetchall():
                OPEN_MATCHES_CACHE[row[0]] = (row[1], row[2], row[3], row[4])
                
            c.close()
            print("✅ تم تحميل الحالة السابقة من قاعدة البيانات للذاكرة (Cache).")
        except Exception as e:
            print(f"⚠️ خطأ أثناء تحميل الكاش: {e}")
        finally:
            conn.close()

def get_last_state(match_id):
    """يرجع (last_status, last_is_queue) أو None لو مباراة جديدة"""
    return MATCH_STATE_CACHE.get(match_id, None)

def upsert_state(match_id, status, is_queue, t1, t2, stadium, kick_off, gates_open):
    MATCH_STATE_CACHE[match_id] = (status, is_queue)
    if status == 1:
        OPEN_MATCHES_CACHE[match_id] = (t1, t2, stadium, kick_off)
    elif match_id in OPEN_MATCHES_CACHE:
        del OPEN_MATCHES_CACHE[match_id]

    conn = get_db()
    if conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO match_status_tracker
                (match_id, last_status, last_is_queue, team1_ar, team2_ar, stadium, kick_off, gates_open)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO UPDATE SET
                last_status   = EXCLUDED.last_status,
                last_is_queue = EXCLUDED.last_is_queue
        ''', (match_id, status, is_queue, t1, t2, stadium, kick_off, gates_open))
        conn.commit()
        c.close()
        conn.close()

def get_last_soldout(match_id, category_id):
    """يرجع آخر حالة soldOut لدرجة معينة، أو None لو جديدة"""
    return CATEGORY_SOLDOUT_CACHE.get((match_id, category_id), None)

def upsert_soldout(match_id, category_id, category_name, price, soldout):
    CATEGORY_SOLDOUT_CACHE[(match_id, category_id)] = soldout
    conn = get_db()
    if conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO category_soldout_tracker
                (match_id, category_id, category_name, price, last_soldout)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (match_id, category_id) DO UPDATE SET last_soldout = EXCLUDED.last_soldout
        ''', (match_id, category_id, category_name, price, soldout))
        conn.commit()
        c.close()
        conn.close()

# ==========================================
# 📡 جلب بيانات الطابور
# ==========================================
def get_queue_match_ids():
    """يرجع set من match_ids التي عندها طابور حالياً في الـ API المخصص للطوابير"""
    try:
        ts = int(time.time() * 1000)
        r = session.get(f"{QUEUE_API_URL}?_={ts}", headers=get_random_headers(), timeout=10)
        r.raise_for_status()
        data = r.json()
        return {item["matchId"] for item in data}
    except Exception as e:
        print(f"⚠️ تعذر جلب بيانات الطابور: {e}")
        return set()

# ==========================================
# 📤 إرسال إشعار
# ==========================================
def send_delayed_notification_fallback(msg):
    try:
        bot.send_message(PUBLIC_CHAT_ID, msg)
        print("✅ تم إرسال الإشعار المؤجل (الاحتياطي في الذاكرة) للقناة العامة.")
    except Exception as e:
        print(f"❌ خطأ في إرسال الإشعار المؤجل (الاحتياطي في الذاكرة) للقناة العامة: {e}")

def send_notification(msg):
    print(msg)
    sent_private = False
    try:
        # إرسال فوري للقناة الخاصة فقط (مش العامة!)
        bot.send_message(TELEGRAM_CHAT_ID, msg)
        sent_private = True
        print(f"✅ تم الإرسال للقناة الخاصة: {TELEGRAM_CHAT_ID}")
    except Exception as e:
        print(f"❌ خطأ في الإرسال للقناة الخاصة: {e}")

    # جدولة الإرسال للقناة العامة بعد 10 دقائق (بس لو القناة العامة مختلفة عن الخاصة)
    if sent_private and PUBLIC_CHAT_ID and str(PUBLIC_CHAT_ID) != str(TELEGRAM_CHAT_ID):
        conn = None
        try:
            conn = get_db()
            if conn:
                c = conn.cursor()
                try:
                    # حماية من التكرار: لو نفس الرسالة موجودة ولسه ما اتبعتتش، ما نضيفهاش تاني
                    c.execute('''
                        SELECT COUNT(*) FROM delayed_notifications
                        WHERE message_text = %s AND sent = FALSE
                    ''', (msg,))
                    existing = c.fetchone()[0]
                    if existing > 0:
                        print("⚠️ الإشعار موجود بالفعل في قائمة الانتظار، تم تجاهل التكرار.")
                    else:
                        c.execute('''
                            INSERT INTO delayed_notifications (message_text, scheduled_time)
                            VALUES (%s, NOW() + INTERVAL '10 minutes')
                        ''', (msg,))
                        conn.commit()
                        print(f"✅ تم جدولة الإشعار للقناة العامة ({PUBLIC_CHAT_ID}) بعد 10 دقائق.")
                finally:
                    c.close()
            else:
                # Fallback to threading.Timer in memory
                print("⚠️ تعذر الاتصال بـ DB لجدولة الإشعار. استخدام المؤقت المحلي الاحتياطي.")
                t = threading.Timer(600.0, send_delayed_notification_fallback, args=[msg])
                t.daemon = True
                t.start()
        except Exception as db_err:
            print(f"❌ خطأ في جدولة الإشعار في قاعدة البيانات: {db_err}")
            # Fallback to threading.Timer in memory
            t = threading.Timer(600.0, send_delayed_notification_fallback, args=[msg])
            t.daemon = True
            t.start()
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    elif sent_private and (not PUBLIC_CHAT_ID or str(PUBLIC_CHAT_ID) == str(TELEGRAM_CHAT_ID)):
        print("⚠️ القناة العامة هي نفس القناة الخاصة أو غير مُعرّفة، تم تخطي الجدولة.")

    return sent_private

def cleanup_stale_notifications():
    """حذف الإشعارات القديمة جداً (أكتر من 20 دقيقة من وقت الجدولة) عند بدء التشغيل"""
    conn = None
    try:
        conn = get_db()
        if conn:
            c = conn.cursor()
            try:
                # حذف الإشعارات اللي فات وقتها بأكتر من 20 دقيقة (يعني قديمة ومش منطقي نبعتها)
                c.execute('''
                    DELETE FROM delayed_notifications 
                    WHERE sent = FALSE AND scheduled_time < NOW() - INTERVAL '20 minutes'
                    RETURNING id
                ''')
                deleted = c.fetchall()
                if deleted:
                    print(f"🗑️ تم حذف {len(deleted)} إشعار(ات) قديمة من قائمة الانتظار عند بدء التشغيل.")
                conn.commit()
            finally:
                c.close()
    except Exception as e:
        print(f"⚠️ خطأ في تنظيف الإشعارات القديمة: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def process_delayed_notifications():
    print("⏳ بدأ معالج الإشعارات المؤجلة...")
    # تنظيف أي إشعارات قديمة متبقية من تشغيل سابق
    cleanup_stale_notifications()
    
    while True:
        conn = None
        try:
            conn = get_db()
            if conn:
                c = conn.cursor()
                try:
                    # جلب الإشعارات التي حان وقت إرسالها ولم تُرسل بعد
                    # بس بنتجاهل اللي فات وقتها بأكتر من 20 دقيقة (حماية إضافية)
                    c.execute('''
                        SELECT id, message_text, scheduled_time
                        FROM delayed_notifications 
                        WHERE scheduled_time <= NOW() 
                          AND sent = FALSE
                          AND scheduled_time > NOW() - INTERVAL '20 minutes'
                        ORDER BY scheduled_time ASC
                    ''')
                    pending = c.fetchall()
                    
                    if pending:
                        print(f"📬 تم العثور على {len(pending)} إشعار(ات) مؤجلة جاهزة للإرسال.")
                    
                    for row in pending:
                        msg_id, msg_text, sched_time = row
                        print(f"🕒 إرسال الإشعار المؤجل #{msg_id} (مجدول: {sched_time}) للقناة العامة {PUBLIC_CHAT_ID}...")
                        try:
                            bot.send_message(PUBLIC_CHAT_ID, msg_text)
                            # حذف الإشعار بعد إرساله بنجاح
                            c.execute('DELETE FROM delayed_notifications WHERE id = %s', (msg_id,))
                            conn.commit()
                            print(f"✅ تم إرسال وحذف الإشعار المؤجل #{msg_id} بنجاح.")
                        except Exception as e:
                            print(f"❌ خطأ في إرسال الإشعار المؤجل #{msg_id}: {e}")
                            # لو فشل الإرسال، نحذفه برضو عشان مايتكررش للأبد
                            c.execute('DELETE FROM delayed_notifications WHERE id = %s', (msg_id,))
                            conn.commit()
                            print(f"🗑️ تم حذف الإشعار #{msg_id} الفاشل لمنع التكرار.")
                    
                    # تنظيف دوري: حذف أي إشعارات قديمة جداً لسه موجودة
                    c.execute('''
                        DELETE FROM delayed_notifications 
                        WHERE scheduled_time < NOW() - INTERVAL '20 minutes'
                    ''')
                    if c.rowcount > 0:
                        conn.commit()
                        print(f"🗑️ تنظيف دوري: حذف {c.rowcount} إشعار(ات) قديمة.")
                        
                finally:
                    c.close()
        except Exception as e:
            print(f"❌ خطأ في معالج الإشعارات المؤجلة: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        
        # فحص كل 30 ثانية (بدل 10 عشان نقلل الضغط على الـ DB)
        time.sleep(30)

# ==========================================
# 🤖 أوامر تليجرام
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
        "🤖 أنا بوت تذاكر الدوري المصري!\n"
        "أراقب موقع تذكرتي كل 60 ثانية ⏱️\n\n"
        "أُرسل إشعار عند:\n"
        "🟢 فتح الحجز\n"
        "🔴 إغلاق الحجز\n"
        "🚶 بدء طابور الجماهير\n"
        "🚀 توقف الطابور والدخول المباشر!\n\n"
        "الأوامر:\n"
        "/status - حالة البوت\n"
        "/matches - المباريات المتاحة الآن"
    )

@bot.message_handler(commands=['status'])
def send_status(message):
    bot.reply_to(message, "✅ البوت يعمل ويراقب التذاكر.")

@bot.message_handler(commands=['matches'])
def send_current_matches(message):
    bot.reply_to(message, "⏳ جاري الفحص...")
    try:
        ts = int(time.time() * 1000)
        r = session.get(f"{API_URL}?_={ts}", headers=get_random_headers(), timeout=15)
        r.raise_for_status()
        matches = r.json()
        queue_ids = get_queue_match_ids()
        found = False

        for match in matches:
            if match.get("matchStatus") == STATUS_OPEN:
                t1 = match.get("teamNameAr1") or match.get("teamName1", "")
                t2 = match.get("teamNameAr2") or match.get("teamName2", "")
                t1_en = match.get("teamName1", "")
                t2_en = match.get("teamName2", "")

                if is_popular_team(t2) and not is_popular_team(t1):
                    t1, t2 = t2, t1
                    t1_en, t2_en = t2_en, t1_en
                    
                t1_clean = clean_team_name(t1)
                t2_clean = clean_team_name(t2)
                
                stadium = match.get("stadiumNameAr") or match.get("stadiumName", "")
                kick_off = (match.get("kickOffTime") or "").replace("T", " ")
                kick_off_ar = format_arabic_date(kick_off)
                max_t = match.get("maxTicketsPerUser", "")
                mid = match.get("matchId")
                has_queue = mid in queue_ids or match.get("isUsedQueue", False)

                is_target = is_popular_team(t1) or is_popular_team(t2) or is_popular_team(t1_en) or is_popular_team(t2_en)

                if is_target:
                    found = True
                    queue_note = "🚶‍♂️ في طابور دلوقتي!" if has_queue else "✅ حجز مباشر بدون طابور!"
                    bot.send_message(message.chat.id,
                        f"🏆 {t1_clean} 🆚 {t2_clean}\n\n"
                        f"🏟️ الاستاد: {stadium}\n\n"
                        f"📅 الماتش: {kick_off_ar}\n\n"
                        f"{queue_note}\n\n"
                        f"🔗 {MATCHES_URL}"
                    )

        if not found:
            bot.send_message(message.chat.id, "❌ لا توجد مباريات مفتوحة حالياً.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

# ==========================================
# 🎫 جلب تفاصيل الدرجات ومتابعة sold_out
# ==========================================
def get_categories(match_id):
    """يجلب قائمة الدرجات من API المقاعد"""
    try:
        ts = int(time.time() * 1000)
        url = SEATS_API_URL.format(match_id=match_id)
        r = session.get(f"{url}?_={ts}", headers=get_random_headers(), timeout=10)
        if r.status_code != 200:
            return []
        return r.json().get("data", [])
    except Exception as e:
        print(f"⚠️ تعذر جلب بيانات الدرجات: {e}")
        return []

def is_popular_team(team_name):
    if not team_name: return False
    cleaned = normalize_arabic(clean_team_name(team_name).lower())

    # 1. منع الفرق اللي فيها كلمات "بنك" أو "bank" عشان دي مش فرق جماهيرية (زي البنك الأهلي)
    if "بنك" in cleaned or "bank" in cleaned:
        return False

    # 2. فحص منتخب مصر
    if "egypt" in cleaned or "منتخب مصر" in cleaned or "المنتخب المصري" in cleaned or cleaned == "مصر":
        return True

    # 3. التأكد إن اسم الفريق فيه اسم من الفرق الجماهيرية المحددة
    # بنجرب الاسم كامل + الاسم بدون "ال" التعريف عشان نتعرف على (اهلى) و (زمالك) وغيرها
    for p in EGYPTIAN_LEAGUE_TEAMS:
        p_norm = normalize_arabic(p.lower())
        if p_norm in cleaned:
            return True
        # لو الاسم بيبدأ بـ "ال"، نجرب بدونها (الاهلي → اهلي)
        if p_norm.startswith("ال") and p_norm[2:] in cleaned:
            return True
    return False

def is_category_targeted(cat_name, t1, t2, t1_en, t2_en):
    if not cat_name: return True
    cat_lower = cat_name.lower()
    
    # 1. Extract text between parentheses to catch explicitly assigned non-popular teams
    match = re.search(r'\((.*?)\)', cat_name)
    if match:
        team_in_parentheses = match.group(1).strip()
        if is_popular_team(team_in_parentheses):
            return True
        else:
            return False
            
    # 2. هل الدرجة مخصصة صراحة لفريق جماهيري؟
    if is_popular_team(cat_name):
        return True
            
    # 3. لو مش مخصصة لفريق جماهيري، هل هي مخصصة للفريق المنافس (غير الجماهيري)؟
    non_popular_teams = []
    for t in [t1, t2, t1_en, t2_en]:
        if t and not is_popular_team(t):
            clean_t = clean_team_name(t).lower()
            if clean_t:
                non_popular_teams.append(clean_t)
            
    for np_team in non_popular_teams:
        if np_team and np_team in cat_lower:
            return False # مخصصة صراحة للفريق غير الجماهيري، إذن نتجاهلها
            
    # 4. لو مش مكتوب عليها اسم أي فريق (زي المقصورة الرئيسية)، نعرضها عادي
    return True

def check_soldout_changes(match_id, t1, t2, t1_clean, t2_clean, t1_en, t2_en, circles, categories, tour_label="", notify_new_available=False):
    """
    يفحص تغيرات sold_out لكل درجة:
    - لو تحولت ل True  → تذاكر الدرجة دي خلصت!
    - لو تحولت ل False → تذاكر الدرجة دي فتحت تاني!
    """
    if not categories:
        return

    for cat in categories:
        cat_name = cat.get("categoryNameAr") or cat.get("categoryName", "")
        if not is_category_targeted(cat_name, t1, t2, t1_en, t2_en):
            continue

        cat_id   = cat.get("categoryId")
        price    = cat.get("price", 0)
        curr_soldout = cat.get("soldOut", False)

        last_soldout = get_last_soldout(match_id, cat_id)

        if last_soldout is None:
            # أول مرة نشوف الدرجة دي
            if not curr_soldout and notify_new_available:
                # درجة جديدة اتضافت وهي متاحة (الماتش كان متتبع قبل كده)
                send_notification(
                    f"فتح الحجز\n"
                    f"{cat_name}\n"
                    f"{t1_clean} ضد {t2_clean}\n"
                    f"{tour_label}\n\n"
                    f"{MATCHES_URL}"
                )
            # لو نفذت من أول ما اتضافت → بس سجل بدون إشعار (الإشعار الأساسي كفاية)
        elif last_soldout is False and curr_soldout:
            # كانت متاحة وخلصت
            send_notification(
                f"نفذت التذاكر\n"
                f"{cat_name}\n"
                f"{t1_clean} ضد {t2_clean}"
            )
        elif last_soldout is True and not curr_soldout:
            # كانت خلصت وفتحت تاني
            send_notification(
                f"إعادة فتح الحجز\n"
                f"{cat_name}\n"
                f"{t1_clean} ضد {t2_clean}\n"
                f"{tour_label}\n\n"
                f"{MATCHES_URL}"
            )

        # تحديث قاعدة البيانات فقط في حالة التغيير
        if last_soldout != curr_soldout:
            upsert_soldout(match_id, cat_id, cat_name, price, curr_soldout)

def get_seats_section(match_id, t1, t2, t1_en, t2_en, categories):
    """يرجع نص ملخص الدرجات (مفتوحة / خلصت) للإشعار"""
    if not categories:
        return ""
    lines = []
    for cat in categories:
        name     = cat.get("categoryNameAr") or cat.get("categoryName", "")
        if not is_category_targeted(name, t1, t2, t1_en, t2_en):
            continue

        price    = cat.get("price", 0)
        sold_out = cat.get("soldOut", False)
        if sold_out:
            lines.append(f"  ❌ {name} ({price} ج.م) - نفذت")
        else:
            lines.append(f"  ✅ {name} ({price} ج.م) - متاحة")
    return "\n🎫 الدرجات المتاحة:\n" + "\n\n".join(lines) + "\n"


def start_telegram_polling():
    print("🤖 مستقبل الأوامر يعمل...")
    bot.infinity_polling()

# ==========================================
# 🔍 الفحص الدوري الرئيسي
# ==========================================
def check_tickets_via_api():
    try:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] جاري الفحص...")

        ts = int(time.time() * 1000)
        r = session.get(f"{API_URL}?_={ts}", headers=get_random_headers(), timeout=15)
        r.raise_for_status()
        matches = r.json()

        api_match_ids = [m.get("matchId") for m in matches]

        # جلب المباريات المفتوحة من الكاش
        open_db_matches = [(k, v[0], v[1], v[2], v[3]) for k, v in OPEN_MATCHES_CACHE.items()]

        # جلب بيانات الطوابير من الـ API
        queue_ids = get_queue_match_ids()

        for match in matches:
            match_id   = match.get("matchId")
            curr_status = match.get("matchStatus")
            curr_is_queue = (match_id in queue_ids) or match.get("isUsedQueue", False)

            last_state = get_last_state(match_id)
            last_status = last_state[0] if last_state else None

            # إذا كان هناك طابور، فالمباراة تعتبر مفتوحة حتى لو لم تتحدث الحالة رسمياً بعد
            if curr_is_queue and curr_status != STATUS_OPEN:
                curr_status = STATUS_OPEN

            # تجاهل المباريات الجارية أو المنتهية (status 3)
            # لكن لو كانت مفتوحة قبل كدا، هنعتبرها "قفلت" عشان نبعت إشعار
            if curr_status not in (STATUS_OPEN, STATUS_CLOSED):
                if last_status == STATUS_OPEN:
                    curr_status = STATUS_CLOSED
                else:
                    continue

            t1         = match.get("teamNameAr1") or match.get("teamName1", "")
            t2         = match.get("teamNameAr2") or match.get("teamName2", "")
            t1_en      = match.get("teamName1", "")
            t2_en      = match.get("teamName2", "")

            if is_popular_team(t2) and not is_popular_team(t1):
                t1, t2 = t2, t1
                t1_en, t2_en = t2_en, t1_en
                
            t1_clean = clean_team_name(t1)
            t2_clean = clean_team_name(t2)
            
            stadium    = match.get("stadiumNameAr") or match.get("stadiumName", "")
            kick_off   = (match.get("kickOffTime") or "").replace("T", " ")
            gates_open = (match.get("gatesOpenTime") or "").replace("T", " ")
            
            kick_off_ar = format_arabic_date(kick_off)
            gates_open_ar = format_arabic_date(gates_open)

            # تصفية الفرق المستهدفة
            found_colors = []
            is_target = False
            for t_name in [t1, t2, t1_en, t2_en]:
                if is_popular_team(t_name):
                    is_target = True
                    # جلب اللون الخاص بالفريق
                    cleaned_t = normalize_arabic(clean_team_name(t_name).lower())
                    for color_team, color_val in TEAM_COLORS.items():
                        if normalize_arabic(color_team.lower()) in cleaned_t:
                            if color_val not in found_colors:
                                found_colors.append(color_val)
                                break

            if not is_target:
                continue

            circles = "".join(found_colors) or "🟢"

            # تحديد التسمية المستخدمة في الإشعار (فريق واحد ولا فريقين)
            is_p1 = is_popular_team(t1) or is_popular_team(t1_en)
            is_p2 = is_popular_team(t2) or is_popular_team(t2_en)
            
            if is_p1 and is_p2:
                teams_label = f"لنادي {t1_clean} و {t2_clean}"
                match_label = f"مباراة {t1_clean} و {t2_clean}"
            else:
                teams_label = f"لنادي {t1_clean}"
                match_label = f"مباراة {t1_clean}"

            # =============================================
            # استخراج الحالة السابقة
            last_is_queue = last_state[1] if last_state else None

            # استخراج بيانات البطولة والدور
            tournament_data = match.get("tournament") or {}
            tour_name = tournament_data.get("nameAr") or ""
            round_name = match.get("roundNameAr") or ""
            tour_label = f"{tour_name} - {round_name}" if round_name else tour_name

            # =============================================
            # 🔔 منطق الإشعارات
            # =============================================

            # جلب قسم الدرجات للمباريات المفتوحة
            categories = []
            if curr_status == STATUS_OPEN:
                categories = get_categories(match_id)
            
            # 1. مباراة جديدة مفتوحة
            if last_state is None and curr_status == STATUS_OPEN:
                success = send_notification(
                    f"فتح الحجز\n"
                    f"{t1_clean} ضد {t2_clean}\n"
                    f"{tour_label}\n\n"
                    f"{MATCHES_URL}"
                )
                if success:
                    upsert_state(match_id, curr_status, curr_is_queue, t1, t2, stadium, kick_off, gates_open)

            # 2. مباراة جديدة مغلقة
            elif last_state is None and curr_status == STATUS_CLOSED:
                success = send_notification(
                    f"إغلاق الحجز\n"
                    f"{t1_clean} ضد {t2_clean}\n"
                    f"{tour_label}"
                )
                if success:
                    upsert_state(match_id, curr_status, curr_is_queue, t1, t2, stadium, kick_off, gates_open)

            # 3. الحجز كان مغلق وفتح
            elif last_status == STATUS_CLOSED and curr_status == STATUS_OPEN:
                success = send_notification(
                    f"إعادة فتح الحجز\n"
                    f"{t1_clean} ضد {t2_clean}\n"
                    f"{tour_label}\n\n"
                    f"{MATCHES_URL}"
                )
                if success:
                    upsert_state(match_id, curr_status, curr_is_queue, t1, t2, stadium, kick_off, gates_open)

            # 4. الحجز كان مفتوح واتقفل
            elif last_status == STATUS_OPEN and curr_status == STATUS_CLOSED:
                success = send_notification(
                    f"إغلاق الحجز\n"
                    f"{t1_clean} ضد {t2_clean}\n"
                    f"{tour_label}"
                )
                if success:
                    upsert_state(match_id, curr_status, curr_is_queue, t1, t2, stadium, kick_off, gates_open)

            # ⭐ 5. الطابور وقف أو بدأ
            elif (last_status == STATUS_OPEN and curr_status == STATUS_OPEN
                  and last_is_queue != curr_is_queue):
                status_text = "دخول مباشر بدون طابور" if not curr_is_queue else "بدأ طابور الانتظار"
                success = send_notification(
                    f"{status_text}\n"
                    f"{t1_clean} ضد {t2_clean}\n\n"
                    f"{MATCHES_URL}"
                )
                if success:
                    upsert_state(match_id, curr_status, curr_is_queue, t1, t2, stadium, kick_off, gates_open)

            else:
                print(f"  ✅ لا تغيير: {t1_clean} ضد {t2_clean} | status={curr_status} | queue={curr_is_queue}")

            # ⭐ فحص تغيرات sold_out لكل درجة (للمباريات المفتوحة فقط)
            if curr_status == STATUS_OPEN:
                # notify_new_available = True بس لو الماتش كان مفتوح قبل كده
                # (مش أول مرة يشوفه، ومش بعد إغلاق وفتح)
                notify_new = (
                    last_state is not None
                    and last_state[0] == STATUS_OPEN
                    and curr_status == STATUS_OPEN
                )
                check_soldout_changes(match_id, t1, t2, t1_clean, t2_clean, t1_en, t2_en, circles, categories, tour_label, notify_new)

            # تحديث قاعدة البيانات فقط عند تغير الحالة (لو مفيش إشعار اتبعت فوق)
            # ملحوظة: لو اتبعت إشعار فوق، الـ upsert_state تمت فعلياً، بس بنأكد هنا لو في حالة تانية
            state_changed = (last_state is None) or (last_state[0] != curr_status) or (last_state[1] != curr_is_queue)
            
            # بنحدث الحالة في الذاكرة والكاش حتى لو الإشعار فشل، عشان نمنع التكرار المزعج في الـ Logs 
            # لكن في الكود اللي فوق، مش بنحدث الـ DB غير لو الإرسال نجح (للحالات المهمة)
            if state_changed and last_state is not None: 
                 # تحديث للحالات اللي مش بتبعت إشعارات (زي المباريات غير الهامة لو وجدت)
                 upsert_state(match_id, curr_status, curr_is_queue, t1, t2, stadium, kick_off, gates_open)

        # فحص المباريات التي اختفت من الموقع (كانت مفتوحة واختفت)
        for db_match in open_db_matches:
            db_m_id, db_t1, db_t2, db_stadium, db_kickoff = db_match
            if db_m_id not in api_match_ids:
                # تصفية الفرق لمعرفة الألوان
                found_colors = []
                for db_t in [db_t1, db_t2]:
                    if is_popular_team(db_t):
                        cleaned_db_t = normalize_arabic(clean_team_name(db_t).lower())
                        for color_team, color_val in TEAM_COLORS.items():
                            if normalize_arabic(color_team.lower()) in cleaned_db_t:
                                if color_val not in found_colors:
                                    found_colors.append(color_val)
                                    break
                circles = "".join(found_colors) or "🟢"

                db_t1_clean = clean_team_name(db_t1)
                db_t2_clean = clean_team_name(db_t2)
                db_kickoff_ar = format_arabic_date(db_kickoff)
                
                # إعداد التسمية الصحيحة للمباراة المختفية
                match_label_closed = f"مباراة {db_t1_clean} و {db_t2_clean}" if is_popular_team(db_t2) else f"مباراة {db_t1_clean}"

                send_notification(
                    f"🛑 إغلاق الحجز 🛑\n\n"
                    f"{db_t1_clean} 🆚 {db_t2_clean}\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                upsert_state(db_m_id, STATUS_CLOSED, False, db_t1, db_t2, db_stadium, db_kickoff, "")

        print(f"✅ انتهى الفحص.")

    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    print("🚀 Super Bot يعمل الآن!")
    print("اضغط Ctrl+C للإيقاف.")

    init_db()
    load_state_from_db()

    polling_thread = threading.Thread(target=start_telegram_polling, daemon=True)
    polling_thread.start()

    delayed_thread = threading.Thread(target=process_delayed_notifications, daemon=True)
    delayed_thread.start()

    try:
        while True:
            check_tickets_via_api()
            # Add random jitter between 0.5 and 1.5 seconds to the interval
            jitter = random.uniform(0.5, 1.5)
            time.sleep(CHECK_INTERVAL_SECONDS + jitter)
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت. وداعاً!")
