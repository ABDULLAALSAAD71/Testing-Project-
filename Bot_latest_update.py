import requests
import time
import json
import os
import sys
import fcntl

# ─── SINGLE INSTANCE LOCK ──────────────────────────────────────────────────────
# Prevents 2 copies of the bot running at the same time (causes duplicate OTPs)
_LOCKFILE_PATH = "/tmp/exe_next_bot.lock"
_lockfile = open(_LOCKFILE_PATH, "w")
try:
    fcntl.flock(_lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    _lockfile.write(str(os.getpid()))
    _lockfile.flush()
except IOError:
    print("❌ Another instance of the bot is already running! Exiting.")
    print(f"   (Lock file: {_LOCKFILE_PATH})")
    sys.exit(1)
# ───────────────────────────────────────────────────────────────────────────────

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import threading
import random
import re
import html
import pyotp
from collections import Counter 
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import datetime 
from urllib.parse import urljoin
from dotenv import load_dotenv
try:
    import pytz
    DHAKA_TZ = pytz.timezone("Asia/Dhaka")
except ImportError:
    DHAKA_TZ = None

def dhaka_now():
    """Returns current datetime in Asia/Dhaka (BDT UTC+6)."""
    if DHAKA_TZ:
        return datetime.now(DHAKA_TZ)
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=6)))

def bdt_str(fmt="%d %b %Y • %H:%M BDT"):
    """Formatted Dhaka time string."""
    return dhaka_now().strftime(fmt)

load_dotenv()


# ==========================================
# Configuration (Token & Owner ID)
# ========================================
TOKEN = "8663307697:AAGS0wD9_bCWs470RfYBC09hD1VMrrKES6I"       #YOUR BOT TOKEN HERE
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
FILE_URL = f"https://api.telegram.org/file/bot{TOKEN}/"

OWNER_ID = 8709830500
BOT_USERNAME = "@Fast_Otpservice_Bot"
WEB_APP_URL = ""  # 🌟 Set your Mini App URL here after hosting (e.g. https://yoursite.com/miniapp.html)
DB_FILE = "bot_data.json"

# 🤖 Groq AI API Key — FREE at console.groq.com

# ==========================================
# Premium Emoji Database
# ==========================================
PEM = {
    "ok": '<tg-emoji emoji-id="6069055635566108204">✅</tg-emoji>',
    "no": '<tg-emoji emoji-id="5420130255174145507">❌</tg-emoji>',
    "warn": '<tg-emoji emoji-id="6143434414614389370">⚠️</tg-emoji>',
    "admin": '<tg-emoji emoji-id="5353032893096567467">📊</tg-emoji>',
    "user": '<tg-emoji emoji-id="5372926953978341366">👤</tg-emoji>',
    "file": '<tg-emoji emoji-id="6143176592022576839">📁</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5352597830089347330">🚀</tg-emoji>',
    "graph": '<tg-emoji emoji-id="5352877703043258544">📊</tg-emoji>',
    "money": '<tg-emoji emoji-id="6233077820965264756">💸</tg-emoji>',
    "gift": '<tg-emoji emoji-id="6142995125359354101">🎁</tg-emoji>',
    "msg": '<tg-emoji emoji-id="6066735296664315449">💬</tg-emoji>',
    "gear": '<tg-emoji emoji-id="6142958910195116114">⚙️</tg-emoji>',
    "link": '<tg-emoji emoji-id="6145657476801896402">🔗</tg-emoji>',
    "trash": '<tg-emoji emoji-id="5422557736330106570">🗑</tg-emoji>',
    "upload": '<tg-emoji emoji-id="5353001161878182134">📤</tg-emoji>',
    "world": '<tg-emoji emoji-id="5336972142066047577">🌐</tg-emoji>',
    "lock": '<tg-emoji emoji-id="5353022963132174959">🔐</tg-emoji>',
    "phone": '<tg-emoji emoji-id="5337132498965010628">📱</tg-emoji>',
    "num": '<tg-emoji emoji-id="5352862640592949843">🔢</tg-emoji>',
    "pin": '<tg-emoji emoji-id="5352922460897452503">📍</tg-emoji>',
    "star": '<tg-emoji emoji-id="5352552689983067014">✨</tg-emoji>',
    "hi": '<tg-emoji emoji-id="5353027129250453493">👋</tg-emoji>'
}

GLOBAL_BODY_EMOJIS = {
    "➖": "6143093578894680789", "🚫": "6142927346480456059", "😒": "6142920298439124074",
    "🖥": "6145444502258589013", "🌐": "6145349587776314020", "🌟": "6145503867296554876",
    "🕓": "6142942305851548665", "⌛": "6143329557282824869", "💬": "6066735296664315449",
    "🔐": "6233077820965264756", "🍏": "5406809207947142040", "❔": "5336850036145823599",
    "⚠️": "6142927346480456059", "🔥": "6142995125359354101", "💸": "6233077820965264756",
    "🥚": "5348390922507817684", "👨‍⚖": "6143209100630039695", "🐁": "5348494358205207761",
    "🧻": "5348486915026884464", "⚗": "5346311574221000149", "🛴": "5348075478634766440",
    "📊": "6145303502777228507", "🔢": "5352862640592949843", "👤": "6145563872284648156",
    "📁": "6143176592022576839", "🚀": "6145349587776314020", "💎": "6143129076799380935",
    "📍": "5352922460897452503", "👋": "5353027129250453493", "✅": "6143279228856048178",
    "1️⃣": "6143346861706059342", "2️⃣": "6142918189610181872", "3️⃣": "6142934424586559136",
    "4️⃣": "6143294664968512411", "5️⃣": "6145165677276700326", "6️⃣": "6143066091103986007",
    "7️⃣": "6143345835208877733", "8️⃣": "6143417247630106782", "9️⃣": "6143119043755778021",
    "🔤": "6143040299825373710", "📣": "5352980533150259581", "📤": "6069162146460082700",
    "✨": "5352552689983067014", "🔹": "5352638632278660622", "🎙": "6145276843915222012",
    "💴": "5352985330628730418", "📅": "6145310353250066053", "📴": "5352974971167611327",
    "✏️": "5395444784611480792", "📱": "5406809207947142040", "🔗": "6145657476801896402",
    "❌": "6142996229165949390", "⚙️": "6142958910195116114", "🫂": "6143250963676274738",
    "➕": "6143317110467600972", "🗑": "5422557736330106570", "🎁": "6142995125359354101",
    "➤": "5420618897898381296", "🏢": "5420156334215565595", "💳": "6143358196124753543",
    "📝": "6145591450269654844", "🛡": "6143295970638569929", "🤝": "5192805934073685937",
    "💰": "6143207206549463932", "👀": "6143257698184996220", "🕹": "5193100774988617665",
    "🟢": "6142955577300491632", "🧪": "5190781475468915802", "🎨": "5190751148704833975",
    "📂": "5257969839313526622", "🌍": "6145349587776314020", "📌": "5318986077455795572",
    "📢": "5789428375261023681", "🆔": "6143035536706643370", "📈": "6233409641548619154",
    "🔔": "6145597725216875059", "🏦": "6142985947014243059", "🧾": "6145591450269654844",
    "👨‍⚖️": "6143209100630039695", "🔍": "6143338142922449331",
    "🔑": "5197288647275071607"
}

DEFAULT_CUSTOM_MESSAGES = {
    "start": {"text": "╔══════════════╗\n       📊. EXE NEXT NUMBER ☠️ \n╚══════════════╝\n🚀 Welcome to Number & OTP Service\n━━━━━━━━━━━━\n✅ Choose an option below\nto continue using the bot.\n━━━━━━━━━━━━\n💎 Premium OTP Service", "buttons": []},
    "get_number": {"text": f"{PEM['pin']} Select a service:", "buttons": []},
    "select_country": {"text": f"📌 Select a country for {{service}}:", "buttons": []}, 
    "search_number": {"text": "╔═══════════╗\n     🔍 <b>SEARCH NUMBER</b>\n╚═══════════╝\n✅ Enter 3 to 9 digits  \nto search for a number.\n━━━━━━━━━━━━━\n📝 Example:\n➥ 880\n➥ 9227373\n━━━━━━━━━━━━━\n🔍 Fast Number Lookup System", "buttons": []},
    "traffic": {"text": f"{PEM['graph']} <b>Traffic Overview</b>\n\n{PEM['ok']} Available Numbers: {{avail}}\n{PEM['rocket']} Assigned Numbers: {{assigned}}", "buttons": []},
    "refer": {"text": f"➖➖➖➖➖➖➖\n« {PEM['gift']} REFER & EARN »\n➖➖➖➖➖➖➖\n{PEM['link']} YOUR LINK:\n<code>{{ref_link}}</code>\n➖➖➖➖➖➖➖\n{PEM['user']} TOTAL REFERS: <b>{{total_ref}}</b>\n➖➖➖➖➖➖➖\n{PEM['money']} PER REFER: <b>{{ref_reward}} TK</b>\n➖➖➖➖➖➖➖", "buttons": []},
    "withdrawal": {"text": "➖➖➖➖➖➖➖\n《 😒 WITHDRAWAL 》\n➖➖➖➖➖➖➖\n👋 Total Otp: {total_otp}\n➖➖➖➖➖➖➖\n🫂 Total Reffer :{total_ref}\n➖➖➖➖➖➖➖\n📅 BALANCE: {bal}৳\n➖➖➖➖➖➖➖\n🔐 MINIMUM: {min_w} ৳\n➖➖➖➖➖➖➖\nSELECT METHOD:", "buttons": []},
    "support": {"text": f"{PEM['msg']} Contact us for any help:", "buttons": []}
}

# ==========================================
# Firebase Setup (Railway Compatible)
# ==========================================
firebase_credentials_json = r"""
{
  "type": "service_account",
  "project_id": "test-390b5",
  "private_key_id": "63831876952c9a68e73f77f17a6575b7cff9a243",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDEC7LZFemNio6f\nu57XmaAZiMJSEWl9oOyDKRspuYABkB5tPK74o1BsTQWJ8AaER/z3CZzPYQbk7nLC\nX5GqJZQkWErE/x/onlSKWqyw99gmxxsQAFCOkZbinPJyeaivmV9QwVYpC4ayf7D2\ne1MmcfNjb3etmeqB1U0BoDUgYTA0m1f5X6HCYEE8oJEj3c1/6JwUooZF3biIULrK\nAMAxOzr5+tI6xbvfH2/6kqqwNJs8d5T2guDrpWVDMPatX22guRwC1twsd9Kn4P2Q\nhIos6MLWR6V+UWyy1kJbBbA0TSNKFccXs0eqw79jMoyzMBc3w89HWk9xAuxL7KgE\nabeEXjS1AgMBAAECggEAAL5VhgiDbD0WdzOGaQ4vL/sOy8k+7+Z84gvprkcCuueD\nvsDbQQUNie/412fOiigSR+QbziKgP4WnQWaMefcUVmKV4aSmx5nK2KZjYl2FiOGR\nhIYzDdR0P09nP57NZ7LmHdKmnHSC6s8cb8oj8a3tURnzTVVtAm85kHK90krjVqQX\n7lzNbTIf4kdtWbMmxKcadswlgIMRpXM6XHdNORSIRw/4kIQrjIE6byV4XQn2h1yH\nJjX3k+lOXDeEGaT+PiH5c5N+/FQUP4/iBa03K3WIdKufc7dxIl2B+JlQ0nlbzmjm\nB5Ip1OBYEE3MFyE1hymi9M1CO5grYvpNsGeDuIl++QKBgQDukJdhVYea/p8SvdNW\n7Xt0r2OkG7AaywTECCP+x1w1Rcz/eKyRMQ7daU9dOAQgZGdb+NAN9hKfiz51lB4K\n40ZcPn/ilwUo3Bwen17crohwTiD7vrhiiGULPdtqkfwaA+XPZ9pEq9H5GBijNoCq\ntQWC2NtOFDcpThvKmdWBtSIFgwKBgQDSX5l2vFZR7dBvkSiBoqn9jIFuUIrmzXAd\nRpxHqxs8bhId6frC/Er4bodpmQAMHQO2E5VEAlVxME2Q8e0K3666zIpFPCV5qYzu\nMKsUXCF8pUjOwmwnlCa1mX+zx2W4zHvr94+nqP5KNtT288MotcrpGdC2suanl4Kl\n0RZsEKZ/ZwKBgCq9MrGYXhPxe9Qit+MB5rUv2r0CzNjv+Cmaf8BcPPO6TpCSMPBO\nBqi5/iLoLy0Sb8X1XGiz5gA5NPZhk8RFlUxfUg/pGF6KmGsQCDGm/wCHrrcLIwNc\nBiYubcm4355Vhm1S4LKeyZ5Dp95NnF140sTvTtK9Imi++pGgX7S+G5s7AoGAWl4m\nlhKhIeB+QO6h783oJ7pLfw+qGyr0lh7W0xJ1SKgfsCnqRggKTF1uXbYThyCPj48p\n92TpPw34w+KoaJtde3CRlNwZXQGwQEE3vC83U0vM0sRBoV7KogemC5wD3jY4pUxa\nsTKuyUJ0iQB9POeamjc0qMaAvk0fGguPDiy42NECgYBjlceLhiw6FTKOn5jjLal6\nfsxIpvnxy/Bh9dpjVWWwnJ8r3Z5yWYT8g/PTVBHLlkq2zlpsGD/MnulJud9wprLe\n5UVcFmfo69Mmj50hkVqyBS0B+bfcLBRS2WBCcoASCy/80AYXCqM1FUE25Ckwn8kv\nZ0odGZZ6e9zgXubJJ45CMw==\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@test-390b5.iam.gserviceaccount.com",
  "client_id": "101826010793472532014",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40test-390b5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""

try:
    cred_dict = json.loads(firebase_credentials_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Connected! (Full Sync Enabled)")
except Exception as e:
    print(f"❌ Firebase Error: {e}")
    db = None

bot_settings = {
    "admins": [OWNER_ID],
    "panels": [], 
    "fw_groups": [], 
    "otp_link": "https://t.me/fast_otpgroup",
    "withdraw_on": True,
    "min_withdraw": 30.0,
    "otp_reward": 0.1,
    "refer_reward": 0.0,
    "cooldown": 10,
    "num_req": 3,
    "num_share": 1, 
    "support_link": "https://t.me/Aaribzayen",
    "w_methods": ["bKash", "Nagad"],
    "w_group": "", 
    
    "fj_on": False,
    "fj_channels": [], 
    "nexa_keys": [], 
    "voltx_keys": [],
    "stex_keys": [],
    "search_countries": [],
    "nexa_services": {},
    "voltx_services": {},
    "stex_services": {},
    "premium_flags": {
        "1": {"char": "🇺🇸", "iso": "US", "name": "United States", "id": "5913463998522592692"},
        "880": {"char": "🇧🇩", "iso": "BD", "name": "Bangladesh", "id": "5911365056594973179"},
        "91": {"char": "🇮🇳", "iso": "IN", "name": "India", "id": "5913754823643107921"},
        "92": {"char": "🇵🇰", "iso": "PK", "name": "Pakistan", "id": "5913705895375672082"},
        "44": {"char": "🇬🇧", "iso": "GB", "name": "United Kingdom", "id": "5913443365499703513"}
    },
    "premium_apps": {
        "FACEBOOK": {"char": "🚫", "id": "5334807341109908955", "name": "Facebook"},
        "WHATSAPP": {"char": "🚫", "id": "5334759662677957452", "name": "WhatsApp"}
    },
    "custom_messages": DEFAULT_CUSTOM_MESSAGES.copy(),

    # 🌟 Referral Commission: referrer gets a % cut whenever their referral earns an OTP reward
    "referral_commission": 10.0,   # in percent (10.0 = 10%) — adjustable from Prime Control

    # 🌟 Auto Traffic Broadcast: posts "which range/country is hot right now" into forward groups
    "auto_traffic_on": True,
    "auto_traffic_interval": 20,   # minutes (suggested range 15-30)

    # 🌟 Zero-Cost Global Aggregates (Local Only — updated incrementally, never scanned from DB)
    "global_balance_pool": 0.0,    # Sum of every user's current withdrawable balance
    "global_total_earned": 0.0,    # Lifetime sum of every reward/credit ever paid out
    "global_total_otps": 0,        # Lifetime total OTPs delivered to users
    "last_reset_date": "",         # Tracks last "today_otps" daily reset (YYYY-MM-DD)

    # 🌟 Smart Number Expiry: auto-expire assigned numbers after N minutes
    "number_expiry_minutes": 10,   # 0 = disabled

    # 🌟 Low Stock Alert threshold
    "low_stock_threshold": 50,

    # 🌟 Maintenance Mode
    "maintenance_mode": False,

    # 🌟 Visible Services — empty = show all, add names to restrict
    "visible_services": [],

    # 🌟 Streak Bonus
    "streak_bonus": 0.0,  # Free bonus disabled

    # 🌟 Auto Welcome Onboarding
    "onboarding_on": True,         # Send step-by-step guide to new users
}

FS_KEYS = [
    "admins", "panels", "fw_groups", "otp_link", "withdraw_on", 
    "min_withdraw", "otp_reward", "refer_reward", "cooldown", 
    "num_req", "num_share", "support_link", "w_methods", "w_group", "nexa_keys", "voltx_keys", "stex_keys", "search_countries", "nexa_services", "voltx_services", "stex_services",
    "fj_on", "fj_channels", "referral_commission", "auto_traffic_on", "auto_traffic_interval",
    "number_expiry_minutes", "onboarding_on"
]

number_batches = {}
used_numbers_list = []
nexa_assigned_numbers = {} 
voltx_assigned_numbers = {}
stex_assigned_numbers = {}
NEXA_BASE_URL = "http://nexaotpservice.com"
VOLTX_BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
STEX_BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api"

def _make_stex_session(verify_ssl=True):
    """Create a requests Session with retry logic for STEX/VOLTX API calls."""
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.verify = verify_ssl
    return s

def stex_get(url, headers=None, timeout=15):
    """GET with 3 retries + SSL fallback for api.2oo9.cloud endpoints."""
    for verify in (True, False):
        try:
            res = _make_stex_session(verify_ssl=verify).get(url, headers=headers or {}, timeout=timeout)
            return res
        except requests.exceptions.SSLError:
            if not verify:
                raise
            continue
        except Exception:
            raise

def stex_post(url, json_data=None, headers=None, timeout=15):
    """POST with 3 retries + SSL fallback for api.2oo9.cloud endpoints."""
    for verify in (True, False):
        try:
            res = _make_stex_session(verify_ssl=verify).post(url, json=json_data or {}, headers=headers or {}, timeout=timeout)
            return res
        except requests.exceptions.SSLError:
            if not verify:
                raise
            continue
        except Exception:
            raise

total_uploaded_stats = 0
total_assigned_stats = 0
processed_otps = set()
_commissioned_numbers = set()  # tracks number+inviter pairs already commissioned
_rewarded_numbers = set()      # tracks number+owner pairs already rewarded (1 reward per number)

# ─── LOCAL BALANCE STORE (balances.json) ───────────────────────────────────────
# Primary balance storage — fast local file, Firebase synced every 5 min
_BALANCES_FILE = "balances.json"

def _load_balances():
    try:
        if os.path.exists(_BALANCES_FILE):
            with open(_BALANCES_FILE, "r") as f:
                return json.load(f)
    except: pass
    return {}

def _save_balances():
    try:
        with open(_BALANCES_FILE, "w") as f:
            json.dump(_local_balances, f)
    except Exception as e:
        print(f"[BALANCE] Save error: {e}")

_local_balances = _load_balances()  # {str(user_id): float}

def _get_local_balance(user_id):
    return float(_local_balances.get(str(user_id), 0.0))

def _set_local_balance(user_id, amount):
    _local_balances[str(user_id)] = round(float(amount), 4)
    _save_balances()

def _firebase_balance_sync_thread():
    """Sync local balances → Firebase every 5 minutes (not on every OTP)."""
    while True:
        time.sleep(300)  # 5 minutes
        if not db: continue
        try:
            items = list(_local_balances.items())
            for i in range(0, len(items), 450):
                chunk = items[i:i+450]
                try:
                    batch = db.batch()
                    for uid, bal in chunk:
                        ref = db.collection("users").document(str(uid))
                        batch.set(ref, {"balance": bal}, merge=True)
                    batch.commit()
                except Exception as e:
                    print(f"[BALANCE SYNC] batch error: {e}")
        except Exception as e:
            print(f"[BALANCE SYNC] error: {e}")
# ───────────────────────────────────────────────────────────────────────────────

recent_traffic = []          # 🌟 "GROUP" traffic: unique OTPs actually forwarded to the group (post-dedup)
panel_otp_log = []           # 🌟 "PANEL" traffic: every raw OTP item seen from panels (incl. duplicates)
user_banned_cache = {}
full_msg_cache = {}

def get_service_emoji_id(app_full_name):
    """প্রিমিয়াম অ্যাপের emoji_id বের করে, না পেলে default lock icon দেয়"""
    service_key = app_full_name.upper().strip()
    apps = bot_settings.get("premium_apps", {})
    for app_name, data in apps.items():
        if app_name == service_key or app_name in service_key or service_key in app_name:
            eid = data.get("id")
            if eid:
                return eid
    return "5353022963132174959"  # default 🔐 premium icon


def build_inbox_keyboard(otp, app_full_name, reward=0.0, owner_id=None, number=None):
    """
    Inbox keyboard builder — OTP বাটনে service premium emoji icon থাকবে।
    """
    service_emoji_id = get_service_emoji_id(app_full_name)
    kb = [[{
        "text": f"{otp}",
        "icon_custom_emoji_id": service_emoji_id,
        "copy_text": {"text": otp},
        "style": "success"
    }]]
    if reward > 0 and owner_id:
        # 🌟 Same number থেকে একবারই reward — duplicate reward block
        reward_key = f"{owner_id}_{str(number).replace('+','').strip()}" if number else None
        already_rewarded = reward_key and reward_key in _rewarded_numbers
        if not already_rewarded:
            if reward_key:
                _rewarded_numbers.add(reward_key)
                if len(_rewarded_numbers) > 10000:
                    _rewarded_numbers.clear()
            update_balance(owner_id, reward)
            pay_referral_commission(owner_id, reward, number=number)
            kb.append([{
                "text": f"Added {reward} tk",
                "icon_custom_emoji_id": "5420396762189831222",
                "callback_data": "ignore",
                "style": "primary"
            }])
    return kb


def build_otp_messages(prem_app_html, app_full_name, prem_flag_html, display_num, masked, lang, otp, msg_text):
    """
    Group forward format — matches inbox format exactly:
    ✅ OTP Received!
    ━━━━━━━━━━━━━━━
    📲 Service: INSTAGRAM
    🌍 Country: Bangladesh
    📱 Number: +880『𝐄𝐗𝐄』123
    🔑 OTP: 682107
    🗣 Language: Bengali
    📩 Full Message: { msg }
    ━━━━━━━━━━━━━━━
    ⚠️ Use within 15 minutes!
    🕐 22 Jun 2026 • 03:39 BDT
    🔔
    """
    flag_char, flag_iso, _ = get_flag_info_from_num(display_num)
    country_name = get_country_full_name(flag_iso)

    # Language code → full name
    lang_map = {
        "#EN": "English", "#BN": "Bengali", "#AR": "Arabic",
        "#HI": "Hindi", "#RU": "Russian", "#TR": "Turkish",
        "#FR": "French", "#DE": "German", "#ES": "Spanish",
        "#PT": "Portuguese", "#ZH": "Chinese", "#JA": "Japanese",
        "#KO": "Korean", "#VI": "Vietnamese", "#TH": "Thai",
        "#FA": "Persian", "#UR": "Urdu", "#PA": "Punjabi",
        "#GU": "Gujarati", "#TA": "Tamil", "#TE": "Telugu",
        "#KN": "Kannada", "#ML": "Malayalam", "#IT": "Italian",
        "#PL": "Polish", "#NL": "Dutch", "#UK": "Ukrainian",
        "#RO": "Romanian", "#HU": "Hungarian", "#CS": "Czech",
        "#SK": "Slovak", "#BG": "Bulgarian", "#HR": "Croatian",
        "#SR": "Serbian", "#SL": "Slovenian", "#LT": "Lithuanian",
        "#LV": "Latvian", "#ET": "Estonian", "#FI": "Finnish",
        "#SV": "Swedish", "#NO": "Norwegian", "#DA": "Danish",
        "#EL": "Greek", "#HE": "Hebrew", "#ID": "Indonesian",
        "#MS": "Malay", "#SW": "Swahili", "#AM": "Amharic",
    }
    lang_name = lang_map.get(lang.upper(), lang.replace("#", ""))

    # Full message line
    full_msg_line = ""
    if msg_text and msg_text != otp:
        full_msg_line = f"\n📩 <b>Full Message:</b>\n<blockquote>{html.escape(msg_text)}</blockquote>"

    # Group forward — plain HTML (no tg-emoji) so it works in all groups
    combined = (
        f"✅ <b>OTP Received!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📲 <b>Service:</b> {app_full_name.upper()}\n"
        f"{flag_char} <b>Country:</b> {country_name}\n"
        f"📱 <b>Number:</b> <code>{masked}</code>\n"
        f"🔑 <b>OTP:</b> <code>{otp}</code>\n"
        f"🗣 <b>Language:</b> {lang_name}"
        + full_msg_line +
        f"\n━━━━━━━━━━━━━━━\n"
        f"⚠️ Use within 15 minutes!\n"
        f"🕐 {bdt_str()}\n"
        f"🔔"
    )

    # Service emoji id for OTP copy button
    service_key = app_full_name.upper().strip()
    apps = bot_settings.get("premium_apps", {})
    service_emoji_id = None
    for app_name, data in apps.items():
        if app_name == service_key or app_name in service_key or service_key in app_name:
            service_emoji_id = data.get("id")
            break

    green_btn = {"text": f"📋 {otp}", "copy_text": {"text": otp}, "style": "success"}
    if service_emoji_id:
        green_btn["icon_custom_emoji_id"] = service_emoji_id

    return combined, "", green_btn, None


def build_inbox_otp_message(prem_app_html, app_full_name, prem_flag_html,
                             display_num, masked, lang, otp, msg_text):
    """
    User inbox OTP format:
    ✅ OTP Received!
    ━━━━━━━━━━━━━━━
    📲 Service: INSTAGRAM
    🌍 Country: Bangladesh
    📱 Number: +880『𝐄𝐗𝐄』123
    🔑 OTP: 682107
    🗣 Language: Bengali
    📩 Full Message: { msg }
    ━━━━━━━━━━━━━━━
    ⚠️ Use within 15 minutes!
    🕐 22 Jun 2026 • 03:39 BDT
    🔔
    """
    flag_char, flag_iso, _ = get_flag_info_from_num(display_num)
    country_name = get_country_full_name(flag_iso)

    # Language code → full name
    lang_map = {
        "#EN": "English", "#BN": "Bengali", "#AR": "Arabic",
        "#HI": "Hindi", "#RU": "Russian", "#TR": "Turkish",
        "#FR": "French", "#DE": "German", "#ES": "Spanish",
        "#PT": "Portuguese", "#ZH": "Chinese", "#JA": "Japanese",
        "#KO": "Korean", "#VI": "Vietnamese", "#TH": "Thai",
        "#FA": "Persian", "#UR": "Urdu", "#PA": "Punjabi",
        "#GU": "Gujarati", "#TA": "Tamil", "#TE": "Telugu",
        "#KN": "Kannada", "#ML": "Malayalam", "#IT": "Italian",
        "#PL": "Polish", "#NL": "Dutch", "#UK": "Ukrainian",
        "#RO": "Romanian", "#HU": "Hungarian", "#CS": "Czech",
        "#SK": "Slovak", "#BG": "Bulgarian", "#HR": "Croatian",
        "#SR": "Serbian", "#SL": "Slovenian", "#LT": "Lithuanian",
        "#LV": "Latvian", "#ET": "Estonian", "#FI": "Finnish",
        "#SV": "Swedish", "#NO": "Norwegian", "#DA": "Danish",
        "#EL": "Greek", "#HE": "Hebrew", "#ID": "Indonesian",
        "#MS": "Malay", "#SW": "Swahili", "#AM": "Amharic",
    }
    lang_name = lang_map.get(lang.upper(), lang.replace("#", ""))

    # Full message line
    full_msg_line = ""
    if msg_text and msg_text != otp:
        full_msg_line = f"\n📩 <b>Full Message:</b>\n<blockquote>{html.escape(msg_text)}</blockquote>"

    return render_body_text(
        f"╔═══════════════╗\n"
        f"║  ✅  <b>OTP RECEIVED</b>  ✅  ║\n"
        f"╚═══════════════╝\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{prem_app_html} <b>Service:</b> {app_full_name.upper()}\n"
        f"{prem_flag_html} <b>Country:</b> {country_name}\n"
        f"📱 <b>Number:</b> <code>{masked}</code>\n"
        f"🔑 <b>OTP:</b> <code>{otp}</code>\n"
        f"🗣 <b>Language:</b> {lang_name}"
        + full_msg_line +
        f"\n━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>Use within 15 minutes!</b>\n"
        f"🕐 {bdt_str()}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔔 <i>Tap the button below to copy your OTP</i>"
    )


def send_inbox_otp(owner_id, prem_app_html, app_full_name, prem_flag_html, display_num, lang, otp, reward=0.0, msg_text=""):
    """🌟 Sends OTP to user inbox with new detailed format."""
    masked = mask_number(display_num)
    inbox_msg = build_inbox_otp_message(
        prem_app_html, app_full_name, prem_flag_html,
        display_num, masked, lang, otp, msg_text
    )
    kb = build_inbox_keyboard(otp, app_full_name, reward, owner_id, number=display_num)
    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": kb})

    # Resolve waiting status
    resolve_waiting_status(owner_id, otp)
    # Record history
    record_user_otp_history(owner_id, app_full_name, display_num, otp)
    # Streak
    streak, milestone = update_streak(owner_id)
    if milestone:
        send_message(owner_id, render_body_text(
            f"🔥 <b>{streak} Day Streak!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Amazing! {streak} days in a row! 💪"
        ))
    elif streak in [3, 5]:
        send_message(owner_id, render_body_text(
            f"{streak_badge(streak)} <b>Streak: {streak} days!</b>\n"
            f"🎯 {7 - (streak % 7)} more days to 7-day milestone!"
        ))


def send_to_forward_groups(prem_app_html, app_full_name, prem_flag_html, display_num, masked, lang, otp, unique_id, msg_text, iso):
    combined, _, green_btn, _ = build_otp_messages(
        prem_app_html, app_full_name, prem_flag_html, display_num, masked, lang, otp, msg_text
    )
    kb = [[green_btn]]

    sent_msgs = []  # [(chat_id, message_id)]
    for fw in bot_settings.get("fw_groups", []):
        cid = fw["chat_id"]
        btn_row = []
        for btn in fw.get("buttons", []):
            # Clean URL — strip any accidental prefix before https:// or http://
            raw_url = btn["url"]
            for proto in ("https://", "http://", "tg://"):
                if proto in raw_url:
                    raw_url = proto + raw_url.split(proto, 1)[1]
                    break
            b_obj = {"text": btn["text"], "url": raw_url, "style": "primary"}
            if "icon_custom_emoji_id" in btn:
                b_obj["icon_custom_emoji_id"] = btn["icon_custom_emoji_id"]
            btn_row.append(b_obj)
        if btn_row:
            kb.append(btn_row)
        res = send_message(cid, combined, reply_markup={"inline_keyboard": kb})
        if not res or not res.get("result"):
            err = res.get("description", "Unknown error") if res else "No response"
            print(f"[FW GROUP ERROR] chat_id={cid} | {err}")
        if res and res.get("result"):
            sent_msgs.append((cid, res["result"]["message_id"]))

    # 🌟 Hook: log OTP sent for success rate tracker
    log_otp_sent(otp, display_num)
    # 🌟 Hook: low stock check
    check_low_stock_and_alert()

    # 🌟 OTP Expiry Warning — 2 min later edit message
    if sent_msgs:
        def _expiry_edit(msgs, orig_text):
            time.sleep(900)  # 15 minutes
            expired_txt = orig_text + render_body_text(
                f"\n\n⚠️ <b>This OTP may be expired</b>\n🕐 {bdt_str('%H:%M BDT')}"
            )
            for (cid, mid) in msgs:
                try:
                    api_call("editMessageText", {
                        "chat_id": cid, "message_id": mid,
                        "text": expired_txt, "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    })
                except: pass
        threading.Thread(target=_expiry_edit, args=(sent_msgs, combined), daemon=True).start()


# Active HTTP sessions for Auto Captcha Panels
panel_sessions = {}

# 🌟 sAjaxSource (AJAX/DataTable) এবং Fallback HTML Parser Helper Function
def fetch_cpt_panel_cdrs(p, session, check_url):
    res = session.get(check_url, timeout=15)
    html_text = res.text
    
    # সেশন শেষ হয়েছে বা লগইন পেজে রিডাইরেক্ট করেছে কি না তা চেক করা
    if "login" in html_text.lower() or "signin" in html_text.lower() or any(x in html_text for x in ["Sign in to your account", "Please sign in", "Welcome back!"]):
        raise Exception("Session expired")
        
    soup = BeautifulSoup(html_text, 'html.parser')
    s_ajax_source = ""
    for script in soup.find_all("script"):
        script_text = script.string or ""
        match = re.search(r'sAjaxSource":\s*"([^"]+)"', script_text)
        if match:
            s_ajax_source = match.group(1)
            break
            
    results = []
    
    n_col_name = p.get("num_col_name", "number").lower()
    m_col_name = p.get("msg_col_name", "message").lower()
    n_idx = int(p.get("num_col_idx", 1)) - 1 if p.get("num_col_idx") else 1
    m_idx = int(p.get("msg_col_idx", 2)) - 1 if p.get("msg_col_idx") else 2

    # ৫.১ যদি sAjaxSource AJAX লিংক পাওয়া যায়
    if s_ajax_source:
        baseUrl = p.get("login_url", "").split("/client")[0].split("/login")[0].strip()
        if not baseUrl.startswith("http"):
            baseUrl = "http://" + baseUrl
            
        full_ajax_url = ""
        if s_ajax_source.startswith("http"):
            full_ajax_url = s_ajax_source
        elif s_ajax_source.startswith("/"):
            full_ajax_url = f"{baseUrl}{s_ajax_source}"
        else:
            last_slash_idx = check_url.rfind("/")
            current_dir = check_url[:last_slash_idx]
            full_ajax_url = f"{current_dir}/{s_ajax_source}"

        if "iDisplayLength" not in full_ajax_url:
            query_params = "sEcho=1&iColumns=7&iDisplayStart=0&iDisplayLength=250&sSearch=&iSortingCols=1&iSortCol_0=0&sSortDir_0=desc"
            divider = "&" if "?" in full_ajax_url else "?"
            full_ajax_url += f"{divider}{query_params}"

        ajax_headers = {
            "Referer": check_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        
        ajax_res = session.get(full_ajax_url, headers=ajax_headers, timeout=15)
        data_dict = ajax_res.json()
        rows = data_dict.get("aaData", [])
        for row_val in rows:
            if not isinstance(row_val, list):
                continue
                
            if len(row_val) < max(n_idx, m_idx) + 1:
                continue
                
            num_val = row_val[n_idx] if (0 <= n_idx < len(row_val)) else row_val[2]
            msg_val = row_val[m_idx] if (0 <= m_idx < len(row_val)) else row_val[4]
            
            clean_num = re.sub(r'\D', '', str(num_val))
            if clean_num and 5 <= len(clean_num) <= 18:
                otp = extract_otp_code(msg_val)
                if otp and len(msg_val) > 4:
                    results.append({"number": clean_num, "message": msg_val, "otp": otp})
                    
    else:
        # ৫.২ ডাইরেক্ট HTML টেবিল থেকে রিড করার ব্যাকআপ লজিক
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if not rows: continue
            
            final_n_idx = n_idx
            final_m_idx = m_idx
            
            header_cells = rows[0].find_all(['th', 'td'])
            for i, cell in enumerate(header_cells):
                c_text = cell.get_text(strip=True).lower()
                if n_col_name in c_text: final_n_idx = i
                if m_col_name in c_text: final_m_idx = i

            for row in rows:
                cols = row.find_all(['td', 'th'])
                if all(c.name == 'th' for c in cols): continue
                
                if len(cols) > max(final_n_idx, final_m_idx):
                    num_text = cols[final_n_idx].get_text(separator=" ", strip=True)
                    msg_text = cols[final_m_idx].get_text(separator=" ", strip=True)
                    
                    clean_num = re.sub(r'\D', '', num_text)
                    if clean_num and 5 <= len(clean_num) <= 18:
                        otp = extract_otp_code(msg_text)
                        if otp and len(msg_text) > 4:
                            results.append({"number": clean_num, "message": msg_text, "otp": otp})
                            
    return results, html_text

# Track active number sessions to expire them automatically
user_active_sessions = {}

def load_db():
    global bot_settings, number_batches, used_numbers_list, total_uploaded_stats, total_assigned_stats, recent_traffic, panel_otp_log
    if db:
        try:
            doc = db.collection('settings').document('bot_config').get()
            if doc.exists:
                fs_data = doc.to_dict()
                for k in FS_KEYS:
                    if k in fs_data:
                        bot_settings[k] = fs_data[k]
                print("✅ Config Loaded from Firestore!")
            else:
                fs_data = {k: bot_settings[k] for k in FS_KEYS}
                db.collection('settings').document('bot_config').set(fs_data)
                print("✅ Firestore Config Initialized!")
        except Exception as e:
            print(f"❌ Error loading from Firestore: {e}")

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f:
                raw = f.read()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as je:
                print(f"⚠️ Local DB corrupted ({je}) — attempting recovery...")
                # Backup corrupted file
                backup_path = DB_FILE + ".corrupted"
                with open(backup_path, "w", encoding='utf-8') as bf:
                    bf.write(raw)
                print(f"📦 Corrupted DB backed up to {backup_path}")
                # Try partial recovery — find last valid JSON
                data = {}
                # Try truncating at error position
                try:
                    clean = raw[:je.pos].rstrip().rstrip(',').rstrip()
                    # Try to close any open structures
                    open_braces = clean.count('{') - clean.count('}')
                    open_brackets = clean.count('[') - clean.count(']')
                    clean += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
                    data = json.loads(clean)
                    print("✅ Partial recovery successful!")
                except:
                    print("⚠️ Recovery failed — starting with empty local DB")
                    data = {}

            saved_settings = data.get("bot_settings", {})
            for key, val in saved_settings.items():
                if key not in FS_KEYS:
                    if key == "custom_messages":
                        for m_key, m_val in val.items():
                            bot_settings["custom_messages"][m_key] = m_val
                    else:
                        bot_settings[key] = val

            for m_key, m_val in DEFAULT_CUSTOM_MESSAGES.items():
                if m_key not in bot_settings["custom_messages"]:
                    bot_settings["custom_messages"][m_key] = m_val

            number_batches.update(data.get("number_batches", {}))
            used_numbers_list.extend(data.get("used_numbers_list", []))
            global total_uploaded_stats, total_assigned_stats
            total_uploaded_stats = data.get("total_uploaded_stats", 0)
            total_assigned_stats = data.get("total_assigned_stats", 0)
            recent_traffic.extend(data.get("recent_traffic", []))
            panel_otp_log.extend(data.get("panel_otp_log", []))
            nexa_assigned_numbers.update(data.get("nexa_assigned_numbers", {}))
            voltx_assigned_numbers.update(data.get("voltx_assigned_numbers", {}))
            stex_assigned_numbers.update(data.get("stex_assigned_numbers", {}))
            print("✅ Local Stock/UI DB Loaded Successfully!")
        except Exception as e:
            print(f"❌ Error loading local DB: {e}")

def save_local_db():
    local_data = {
        "bot_settings": {k: v for k, v in bot_settings.items() if k not in FS_KEYS},
        "number_batches": number_batches,
        "used_numbers_list": used_numbers_list[-500:],  # keep last 500 only
        "total_uploaded_stats": total_uploaded_stats,
        "total_assigned_stats": total_assigned_stats,
        "recent_traffic": recent_traffic[-200:],        # keep last 200
        "panel_otp_log": panel_otp_log[-200:],
        "nexa_assigned_numbers": nexa_assigned_numbers,
        "voltx_assigned_numbers": voltx_assigned_numbers,
        "stex_assigned_numbers": stex_assigned_numbers
    }
    try:
        # 🌟 Atomic write — write to temp file first, then rename
        # Prevents corruption if process crashes during write
        tmp_file = DB_FILE + ".tmp"
        with open(tmp_file, "w", encoding='utf-8') as f:
            json.dump(local_data, f, indent=2, ensure_ascii=False)
        # Validate before replacing
        with open(tmp_file, "r", encoding='utf-8') as f:
            json.load(f)  # will raise if invalid
        os.replace(tmp_file, DB_FILE)
    except Exception as e:
        try: os.remove(tmp_file)
        except: pass

def _sync_fs():
    if not db: return
    fs_data = {k: bot_settings[k] for k in FS_KEYS if k in bot_settings}
    try:
        db.collection('settings').document('bot_config').set(fs_data)
    except: pass

def save_db():
    save_local_db()
    # 🌟 Firestore Save Threading: মেইন বটকে স্লো না করার জন্য ব্যাকগ্রাউন্ডে সেভ হবে
    threading.Thread(target=_sync_fs, daemon=True).start()

load_db()



user_states = {}
temp_data = {}
user_cooldowns = {}
pending_withdrawals = {}

# ==========================================
# Telegram API & Helpers
# ==========================================
tg_session = requests.Session() # 🌟 Keep-Alive Connection (Makes bot 10x faster)

def api_call(method, payload=None):
    url = f"{BASE_URL}/{method}"
    try:
        # 🌟 Added timeout to prevent hanging!
        res = tg_session.post(url, json=payload, timeout=15)
        return res.json()
    except Exception as e:
        return {}

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("sendMessage", payload)

def send_photo(chat_id, photo_url_or_file_id, caption="", reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "photo": photo_url_or_file_id, "caption": caption, "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("sendPhoto", payload)

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("editMessageText", payload)

def delete_message(chat_id, message_id):
    return api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def answer_callback(callback_id, text="", show_alert=False):
    api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text, "show_alert": show_alert})

def send_document(chat_id, filename, text_content):
    url = f"{BASE_URL}/sendDocument"
    files = {'document': (filename, text_content)}
    data = {'chat_id': chat_id}
    try: requests.post(url, data=data, files=files)
    except: pass

# 🌟 Local User List to completely remove Firebase Read Costs!
all_known_users = set()

def sync_users_list():
    global all_known_users
    try:
        if os.path.exists("users_list.json"):
            with open("users_list.json", "r") as f:
                all_known_users = set(json.load(f))
        if not all_known_users and db:
            for doc in db.collection('users').select([]).stream():
                all_known_users.add(doc.id)
            with open("users_list.json", "w") as f:
                json.dump(list(all_known_users), f)
    except: pass

threading.Thread(target=sync_users_list, daemon=True).start()

def _save_users_list():
    try:
        with open("users_list.json", "w") as f:
            json.dump(list(all_known_users), f)
    except: pass

def register_user_local(uid):
    uid_str = str(uid)
    if uid_str not in all_known_users:
        all_known_users.add(uid_str)
        # 🌟 Non-blocking background save (Prevents lag)
        threading.Thread(target=_save_users_list, daemon=True).start()

def do_daily_reset():
    """
    1) Sends top OTP leaderboard to admin
    2) Resets today_otps for ALL users (Firebase + cache)
    3) Clears traffic logs
    Called at BDT midnight automatically, or manually by admin.
    """
    global recent_traffic, panel_otp_log
    today_str = dhaka_now().strftime("%Y-%m-%d")

    # ── STEP 1: Build & send TOP OTP leaderboard BEFORE resetting ──────────────
    try:
        # Collect from cache + Firebase
        otp_scores = {}
        for uid, udata in user_cache.items():
            t = udata.get("today_otps", 0)
            if t > 0:
                otp_scores[uid] = t

        if db and not otp_scores:
            # Fallback — fetch from Firebase if cache is empty
            docs = db.collection("users").order_by("today_otps", direction="DESCENDING").limit(20).stream()
            for doc in docs:
                d = doc.to_dict()
                if d.get("today_otps", 0) > 0:
                    otp_scores[int(doc.id)] = d["today_otps"]

        if otp_scores:
            sorted_lb = sorted(otp_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            lb_lines = ""
            medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
            for rank, (uid, count) in enumerate(sorted_lb):
                udata = user_cache.get(uid, {})
                name = udata.get("first_name", f"User {uid}")
                lb_lines += f"{medals[rank]} <b>{name}</b> — {count} OTPs\n"

            lb_summary = (
                f"🏆 <b>DAILY OTP LEADERBOARD</b>\n"
                f"📅 {today_str}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{lb_lines}"
                f"━━━━━━━━━━━━━━━\n"
                f"🔄 Leaderboard resets to 0 now!"
            )
            admins = bot_settings.get("admins", [OWNER_ID])
            for admin_id in admins[:3]:
                try: send_message(admin_id, lb_summary)
                except: pass
    except Exception as e:
        print(f"[LEADERBOARD] Error building summary: {e}")

    # ── STEP 2: Reset today_otps in Firebase (ALL users, not just known) ───────
    if db:
        try:
            all_docs = db.collection("users").stream()
            uid_list = [doc.id for doc in all_docs]
            for i in range(0, len(uid_list), 450):
                chunk = uid_list[i:i+450]
                try:
                    batch = db.batch()
                    for uid in chunk:
                        batch.set(db.collection("users").document(uid), {"today_otps": 0}, merge=True)
                    batch.commit()
                except: pass
        except: pass

    # ── STEP 3: Reset today_otps in local cache ─────────────────────────────────
    for uid_cached in list(user_cache.keys()):
        user_cache[uid_cached]["today_otps"] = 0

    # ── STEP 4: Clear traffic logs ──────────────────────────────────────────────
    recent_traffic = []
    panel_otp_log  = []

    bot_settings["last_reset_date"] = today_str
    save_db()

    send_message(OWNER_ID,
        f"🔄 <b>Daily Reset Complete!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Leaderboard: Sent & Reset to 0\n"
        f"✅ Today OTPs: Reset\n"
        f"✅ Country Traffic: Cleared\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )


def daily_reset_thread():
    """🌟 Runs daily reset at BDT midnight (00:00 Asia/Dhaka) + sends leaderboard summary to admin."""
    _notified_date = None
    while True:
        try:
            now = dhaka_now()
            today_str = now.strftime("%Y-%m-%d")
            # Only reset once per day
            if bot_settings.get("last_reset_date") != today_str:
                do_daily_reset()
                # 🌟 Send leaderboard summary to admin at midnight
                if _notified_date != today_str:
                    _notified_date = today_str
                    try:
                        admins = bot_settings.get("admins", [])
                        if admins:
                            lb_msg = (
                                f"🏆 <b>DAILY LEADERBOARD RESET</b>\n"
                                f"━━━━━━━━━━━━━━━\n"
                                f"🕛 BDT Midnight — Auto Reset Done!\n"
                                f"📅 Date: {today_str}\n"
                                f"👥 Users: {len(user_cache)}\n"
                                f"📊 OTPs Today: {bot_settings.get('global_total_otps', 0)}\n"
                                f"💰 Balance Pool: {round(bot_settings.get('global_balance_pool', 0), 2)} ৳\n"
                                f"━━━━━━━━━━━━━━━\n"
                                f"🔄 Leaderboard refreshed!"
                            )
                            for admin_id in admins[:3]:  # max 3 admins
                                try: send_message(admin_id, lb_msg)
                                except: pass
                    except: pass
        except: pass
        time.sleep(300)  # Check every 5 min

def build_auto_traffic_broadcast_text(sample_size=10):
    """🌟 Last 5 min traffic analysis — all services breakdown + top country + BDT time."""
    now = time.time()
    five_min_ago = now - 300  # last 5 minutes

    # Primary: last 5 min data
    five_min_sample = [t for t in recent_traffic if t.get("time", 0) >= five_min_ago]

    # Fallback: last N OTPs if 5min data is sparse
    if len(five_min_sample) < 3:
        sample = recent_traffic[-sample_size:] if recent_traffic else []
        time_label = f"Last {len(sample)} OTPs"
    else:
        sample = five_min_sample
        time_label = "Last 5 Minutes"

    if not sample:
        return None

    country_counter = Counter()
    range_counter   = Counter()
    service_counter = Counter()
    for t in sample:
        country_counter[t.get("iso", "XX")] += 1
        num = t.get("number", "")
        if num: range_counter[get_number_range(num)] += 1
        service_counter[t.get("service", "Unknown")] += 1

    top_iso, top_iso_cnt   = country_counter.most_common(1)[0]
    top_range, top_range_cnt = (range_counter.most_common(1)[0] if range_counter else ("N/A", 0))

    # Country name + premium flag html
    c_name = top_iso
    for code, fdata in bot_settings.get("premium_flags", {}).items():
        if fdata.get("iso") == top_iso:
            c_name = fdata.get("name", top_iso)
            break
    flag_html = get_flag_info_html(top_iso)

    n = len(sample)

    # 🌟 All active services — bar chart style
    all_srv_lines = ""
    for srv, cnt in service_counter.most_common():
        _, srv_html = get_service_info_html(srv)
        pct = int(cnt / n * 100) if n else 0
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        crown = " 👑" if cnt == service_counter.most_common(1)[0][1] else ""
        all_srv_lines += f"  {srv_html} <b>{srv}</b>{crown}\n  <code>{bar}</code> {cnt}/{n} ({pct}%)\n"

    # 🌟 1h success rate inline
    with _otp_success_lock:
        hr_cut = now - 3600
        hr_sample = [e for e in otp_success_log if e["sent_time"] >= hr_cut]
    if hr_sample:
        used_hr = sum(1 for e in hr_sample if e["used"])
        rate_pct = used_hr * 100 // len(hr_sample)
        rate_line = f"📈 Success Rate (1h): <b>{used_hr}/{len(hr_sample)} ({rate_pct}%)</b>\n"
    else:
        rate_line = ""

    # OTP speed (avg time between OTPs in sample)
    if len(sample) >= 2:
        times = sorted(t.get("time", 0) for t in sample)
        gaps = [times[i+1]-times[i] for i in range(len(times)-1)]
        avg_gap = sum(gaps) / len(gaps)
        if avg_gap < 30:   speed_tag = "⚡ Very Fast"
        elif avg_gap < 90: speed_tag = "🟡 Normal"
        else:              speed_tag = "🔴 Slow"
        speed_line = f"🚀 OTP Speed: <b>{speed_tag}</b> (~{int(avg_gap)}s/OTP)\n"
    else:
        speed_line = ""

    txt = (
        f"╔═══════════════╗\n"
        f"║ 🔥 <b>LIVE TRAFFIC UPDATE</b>\n"
        f"╚═══════════════╝\n\n"
        f"📊 Analysis: <b>{time_label}</b> — {n} OTPs\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{flag_html} 🏆 Top Country: <b>{c_name} ({top_iso})</b> — {top_iso_cnt}/{n}\n"
        f"🔢 Active Range: <code>{top_range}</code> — {top_range_cnt}/{n}\n"
        f"{speed_line}"
        f"━━━━━━━━━━━━━━━\n"
        f"📱 <b>Services Breakdown:</b>\n{all_srv_lines}"
        f"━━━━━━━━━━━━━━━\n"
        f"{rate_line}"
        f"🕐 {bdt_str()}"
    )
    return render_body_text(txt)

def auto_traffic_broadcast_thread():
    """🌟 Every `auto_traffic_interval` minutes, analyzes the last 10 OTPs and posts which
    range/country is currently hottest into every forward group AND all user inboxes.
    Auto-disables 20 minutes after bot start."""
    last_broadcast = 0
    _bot_start_time = time.time()
    _AUTO_OFF_AFTER = 20 * 60  # 20 minutes
    while True:
        try:
            time.sleep(60)
            # 🌟 Auto-off after 20 minutes
            if time.time() - _bot_start_time >= _AUTO_OFF_AFTER:
                if bot_settings.get("auto_traffic_on", True):
                    bot_settings["auto_traffic_on"] = False
                    save_db()
                continue
            if not bot_settings.get("auto_traffic_on", True):
                continue
            interval_sec = max(int(bot_settings.get("auto_traffic_interval", 20)), 1) * 60
            if time.time() - last_broadcast < interval_sec:
                continue

            msg_txt = build_auto_traffic_broadcast_text(10)
            if not msg_txt:
                continue
            last_broadcast = time.time()

            # Send to forward groups
            for fg in bot_settings.get("fw_groups", []):
                try: send_message(fg["chat_id"], msg_txt)
                except: pass

            # 🌟 Also send to all user inboxes (broadcast)
            def _inbox_broadcast():
                b_session = requests.Session()
                url = f"{BASE_URL}/sendMessage"
                for user_id in list(all_known_users):
                    try:
                        payload = {"chat_id": user_id, "text": msg_txt, "parse_mode": "HTML", "disable_web_page_preview": True}
                        b_session.post(url, json=payload, timeout=5)
                    except: pass
                    time.sleep(0.04)  # ~25 msg/sec safe rate
            threading.Thread(target=_inbox_broadcast, daemon=True).start()

        except: pass

def broadcast_copymessage(from_chat_id, msg_id):
    success = 0
    failed = 0
    users = list(all_known_users)
    
    # 🌟 Dedicated Connection Pool for Broadcast (Fixes Port Exhaustion & Network Lag)
    b_session = requests.Session()
    url = f"{BASE_URL}/copyMessage"
    
    for user_id in users:
        payload = {"chat_id": user_id, "from_chat_id": from_chat_id, "message_id": msg_id}
        try:
            res = b_session.post(url, json=payload, timeout=5).json()
            if res.get("ok"): success += 1
            else: failed += 1
        except:
            failed += 1
        time.sleep(0.035) # Safe speed (28 msgs/sec) to prevent Telegram Ban
        
    send_message(from_chat_id, render_body_text(f"📢 <b>Broadcast Completed!</b>\n✅ Success: {success}\n❌ Failed: {failed}\n👥 Total Sent: {len(users)}"))


# ==========================================
# 🌟 OTP SUCCESS RATE TRACKER
# ==========================================
otp_success_log = []   # {"otp": str, "sent_time": float, "used": bool}
_otp_success_lock = threading.Lock()

def log_otp_sent(otp, number):
    """Call when OTP is forwarded to group — marks as 'sent'."""
    with _otp_success_lock:
        otp_success_log.append({"otp": otp, "number": number, "sent_time": time.time(), "used": False})
        # keep only last 1000
        if len(otp_success_log) > 1000:
            del otp_success_log[:len(otp_success_log) - 1000]

def mark_otp_used(otp):
    """Call when user copies/uses OTP — marks as 'used'."""
    with _otp_success_lock:
        for entry in reversed(otp_success_log):
            if entry["otp"] == otp and not entry["used"]:
                entry["used"] = True
                break

def get_success_rate_text():
    """Returns success rate summary text."""
    with _otp_success_lock:
        cutoff = time.time() - 86400  # last 24h
        recent = [e for e in otp_success_log if e["sent_time"] >= cutoff]
    if not recent:
        return "📈 <b>OTP Success Rate</b>\n<i>No data in last 24h</i>"
    total = len(recent)
    used  = sum(1 for e in recent if e["used"])
    rate  = (used / total * 100) if total else 0
    bar_used = int(rate / 10)
    bar = "🟩" * bar_used + "⬜" * (10 - bar_used)
    return (
        f"📈 <b>OTP Success Rate (24h)</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{bar} <b>{rate:.1f}%</b>\n"
        f"✅ Used: <b>{used}</b>  |  📨 Sent: <b>{total}</b>  |  ❌ Expired: <b>{total - used}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )


# ==========================================
# 🌟 LOW STOCK ALERT
# ==========================================
_last_low_stock_alert = {}  # service_key → last alert timestamp

def check_low_stock_and_alert():
    """Check number_batches stock — alert admin if any service < threshold."""
    threshold = int(bot_settings.get("low_stock_threshold", 50))
    now = time.time()
    for key, nums in number_batches.items():
        remaining = len(nums) if isinstance(nums, list) else 0
        if remaining < threshold:
            last_alert = _last_low_stock_alert.get(key, 0)
            if now - last_alert > 1800:  # max 1 alert per 30 min per service
                _last_low_stock_alert[key] = now
                txt = render_body_text(
                    f"⚠️ <b>Low Stock Alert!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📦 Service: <b>{key}</b>\n"
                    f"🔢 Remaining Numbers: <b>{remaining}</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🕐 {bdt_str()}"
                )
                try:
                    send_message(OWNER_ID, txt)
                except: pass


# ==========================================
# 🌟 NUMBER REUSE PROTECTION
# ==========================================
_used_numbers_24h = {}  # number → first_use_timestamp

def is_number_reused(number):
    """Returns True if this number was already assigned in last 24h."""
    clean = str(number).replace("+", "").replace(" ", "")
    cutoff = time.time() - 86400
    # purge old entries
    expired = [n for n, t in _used_numbers_24h.items() if t < cutoff]
    for n in expired:
        del _used_numbers_24h[n]
    if clean in _used_numbers_24h:
        return True
    _used_numbers_24h[clean] = time.time()
    return False


# ==========================================
# 🌟 PANEL HEALTH MONITOR
# ==========================================
_panel_last_seen = {}    # panel_name → last success timestamp
_panel_down_alerted = {} # panel_name → last down-alert timestamp

def record_panel_success(panel_name):
    _panel_last_seen[panel_name] = time.time()
    _panel_down_alerted.pop(panel_name, None)  # reset alert on recovery

def check_panel_health():
    """Alert admin if a panel hasn't responded in 10 min."""
    now = time.time()
    for p in bot_settings.get("panels", []):
        name = p.get("name", "Unknown")
        if p.get("status") != "ON":
            continue
        last = _panel_last_seen.get(name, now)  # new panels get grace period
        if now - last > 600:  # 10 min silent
            last_alert = _panel_down_alerted.get(name, 0)
            if now - last_alert > 1800:  # alert max every 30 min
                _panel_down_alerted[name] = now
                txt = render_body_text(
                    f"🔴 <b>Panel Down Alert!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🖥 Panel: <b>{name}</b>\n"
                    f"⏱ Silent for: <b>{int((now - last) / 60)} min</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🕐 {bdt_str()}"
                )
                try:
                    send_message(OWNER_ID, txt)
                except: pass

def panel_health_thread():
    """Runs every 5 min — checks all ON panels for silence."""
    while True:
        try:
            time.sleep(300)
            check_panel_health()
        except: pass


# ==========================================
# 🌟 USER OTP HISTORY
# ==========================================
user_otp_history = {}  # user_id → [ {service, number, otp, time_str}, ... ] max 10

def record_user_otp_history(user_id, service, number, otp):
    """Store last 10 OTPs per user."""
    entry = {
        "service": service,
        "number": number,
        "otp": otp,
        "time": bdt_str("%d %b %H:%M BDT")
    }
    hist = user_otp_history.setdefault(str(user_id), [])
    hist.append(entry)
    if len(hist) > 10:
        del hist[:len(hist) - 10]

def build_user_history_text(user_id):
    """Builds /history message for a user."""
    hist = user_otp_history.get(str(user_id), [])
    if not hist:
        return render_body_text("📜 <b>Your OTP History</b>\n\n<i>No OTPs received yet.</i>")
    lines = [render_body_text("📜 <b>Your Last OTPs</b>\n━━━━━━━━━━━━━━━")]
    for i, e in enumerate(reversed(hist), 1):
        lines.append(render_body_text(
            f"<b>{i}.</b> {e['service']}\n"
            f"   📱 <code>{e['number']}</code>\n"
            f"   🔑 <code>{e['otp']}</code>\n"
            f"   🕐 {e['time']}"
        ))
    return "\n".join(lines)


def generate_emoji_txt(mode):
    """
    Generate downloadable TXT content for premium flags or apps.
    mode = "flags" → premium_flags
    mode = "apps"  → premium_apps
    Returns bytes or None.
    """
    if mode == "flags":
        data = bot_settings.get("premium_flags", {})
        if not data:
            return None
        lines = []
        for code, info in data.items():
            char = info.get("char", "")
            iso  = info.get("iso", "")
            name = info.get("name", "")
            eid  = info.get("id", "")
            lines.append(f'({code})({iso}){char} {name} {{"emoji": "{char}", "id": "{eid}"}}')
        return "\n".join(lines).encode("utf-8")
    elif mode == "apps":
        data = bot_settings.get("premium_apps", {})
        if not data:
            return None
        lines = []
        for key, info in data.items():
            char = info.get("char", "")
            name = info.get("name", key.title())
            eid  = info.get("id", "")
            lines.append(f'{char} {name} {{"emoji": "{char}", "id": "{eid}"}}')
        return "\n".join(lines).encode("utf-8")
    return None



# ==========================================
# 🌟 MAINTENANCE MODE
# ==========================================
# bot_settings["maintenance_mode"] = False by default

def is_maintenance(user_id):
    """Returns True if maintenance is ON and user is not admin."""
    return bot_settings.get("maintenance_mode", False) and not is_admin(user_id)

def maintenance_msg():
    return render_body_text(
        "🔧 <b>Bot Under Maintenance</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "We'll be back shortly.\n"
        "Please wait a few minutes.\n"
        "━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )


# ==========================================
# 🌟 STREAK SYSTEM
# ==========================================
def update_streak(user_id):
    """
    Call once per day when user receives an OTP.
    Updates streak_days and streak_last_date.
    Returns (new_streak, milestone_hit).
    No balance bonus — just streak tracking and milestone notification.
    """
    u = get_user(user_id)
    today = dhaka_now().strftime("%Y-%m-%d")
    last  = u.get("streak_last_date", "")
    streak = int(u.get("streak_days", 0))

    import datetime as _dt
    yesterday = (dhaka_now() - _dt.timedelta(days=1)).strftime("%Y-%m-%d")

    if last == today:
        return streak, False   # already counted today
    elif last == yesterday:
        streak += 1            # consecutive day
    else:
        streak = 1             # reset

    milestone = (streak > 0 and streak % 7 == 0)

    # save
    if user_id in user_cache:
        user_cache[user_id]["streak_days"]      = streak
        user_cache[user_id]["streak_last_date"] = today
    if db:
        try:
            db.collection("users").document(str(user_id)).set(
                {"streak_days": streak, "streak_last_date": today}, merge=True
            )
        except: pass

    return streak, milestone


def streak_badge(streak):
    if streak >= 30: return "🏆"
    if streak >= 14: return "💎"
    if streak >= 7:  return "🔥"
    if streak >= 3:  return "⭐"
    return "📅"


# ==========================================
# 🌟 VIP BADGE
# ==========================================
def get_vip_label(total_otps):
    if total_otps >= 200: return "👑 LEGEND"
    if total_otps >= 100: return "💎 ELITE"
    if total_otps >= 50:  return "⭐ VIP"
    return ""


# ==========================================
# 🌟 OTP WAITING STATUS — live message
# ==========================================
# {user_id: {"msg_id": int, "chat_id": int, "number": str, "service": str, "expire_ts": float}}
otp_waiting_status = {}

def send_waiting_status(chat_id, number, service, expire_ts):
    """Sends a 'Waiting for OTP...' message and stores msg_id for later edit."""
    masked = mask_number(number)
    exp_min = int(bot_settings.get("number_expiry_minutes", 10))
    txt = render_body_text(
        f"⏳ <b>Waiting for OTP...</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📱 Number: <code>{masked}</code>\n"
        f"📲 Service: <b>{service}</b>\n"
        f"⏰ Session: <b>{exp_min} min</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )
    res = send_message(chat_id, txt)
    if res and res.get("result"):
        otp_waiting_status[chat_id] = {
            "msg_id": res["result"]["message_id"],
            "chat_id": chat_id,
            "number": number,
            "service": service,
            "expire_ts": expire_ts
        }

def resolve_waiting_status(chat_id, otp):
    """Edit the waiting message to show OTP received."""
    entry = otp_waiting_status.pop(chat_id, None)
    if not entry: return
    txt = render_body_text(
        f"✅ <b>OTP Received!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📲 Service: <b>{entry['service']}</b>\n"
        f"🔑 OTP: <code>{otp}</code>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚠️ Use within 15 minutes!\n"
        f"🕐 {bdt_str()}"
    )
    try:
        api_call("editMessageText", {
            "chat_id": chat_id,
            "message_id": entry["msg_id"],
            "text": txt,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        })
    except: pass


# ==========================================
# 🌟 /status COMMAND
# ==========================================
def build_status_text(chat_id):
    u = get_user(chat_id)
    bal   = u.get("balance", 0.0)
    total = u.get("total_otps", 0)
    today = u.get("today_otps", 0)
    refs  = u.get("total_refers", 0)
    streak = int(u.get("streak_days", 0))
    min_w  = float(bot_settings.get("min_withdraw", 30.0))
    vip    = get_vip_label(total)
    badge  = streak_badge(streak)

    # Active session
    session = user_active_sessions.get(chat_id)
    if session:
        nums = session.get("nums", [])
        num_str = f"<code>{nums[0]}</code>" if nums else "—"
        exp_ts  = number_expiry_tracker.get(chat_id, 0)
        rem_sec = max(0, int(exp_ts - time.time()))
        rem_str = f"{rem_sec // 60}:{rem_sec % 60:02d} min" if rem_sec > 0 else "Expired"
        session_line = (
            f"📱 Active Number: {num_str}\n"
            f"⏰ Expires in: <b>{rem_str}</b>\n"
        )
    else:
        session_line = "📱 No active session\n"

    # withdraw progress bar
    prog = min(int((bal / min_w) * 10), 10)
    bar  = "█" * prog + "░" * (10 - prog)
    pct  = min(int((bal / min_w) * 100), 100)

    return render_body_text(
        f"{'👑 ' + vip if vip else '👤'} <b>Your Status</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{session_line}"
        f"━━━━━━━━━━━━━━━\n"
        f"📨 OTPs Today: <b>{today}</b>  |  Total: <b>{total}</b>\n"
        f"👥 Referrals: <b>{refs}</b>\n"
        f"{badge} Streak: <b>{streak} days</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Balance: <b>{bal:.2f} ৳</b>\n"
        f"<code>{bar}</code> {pct}% to withdraw\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )


# ==========================================
# 🌟 WITHDRAW PROGRESS BAR (standalone)
# ==========================================
def build_withdraw_progress(chat_id):
    u     = get_user(chat_id)
    bal   = u.get("balance", 0.0)
    min_w = float(bot_settings.get("min_withdraw", 30.0))
    prog  = min(int((bal / min_w) * 10), 10)
    bar   = "█" * prog + "░" * (10 - prog)
    pct   = min(int((bal / min_w) * 100), 100)
    needed = max(0.0, min_w - bal)
    return (
        f"💰 Balance: <b>{bal:.2f} ৳</b>\n"
        f"🎯 Min Withdraw: <b>{min_w:.0f} ৳</b>\n"
        f"<code>[{bar}]</code> <b>{pct}%</b>\n"
        + (f"⚠️ Need <b>{needed:.2f} ৳</b> more" if needed > 0 else "✅ <b>Ready to withdraw!</b>")
    )


# ==========================================
# 🌟 ADMIN: LIVE STATS
# ==========================================
def build_live_stats_text():
    now_t = time.time()
    five_ago = now_t - 300
    active_users = len(user_active_sessions)
    total_users  = len(all_known_users)
    today_otps   = sum(user_cache[uid].get("today_otps", 0) for uid in user_cache)
    total_otps   = bot_settings.get("global_total_otps", 0)
    total_paid   = bot_settings.get("global_total_earned", 0.0)
    panels_on    = len([p for p in bot_settings.get("panels", []) if p.get("status") == "ON"])
    panels_total = len(bot_settings.get("panels", []))
    recent_5 = len([t for t in recent_traffic if t.get("time", 0) >= five_ago])

    if recent_traffic:
        srv_cnt = Counter(t.get("service", "?") for t in recent_traffic[-20:])
        top_srv = srv_cnt.most_common(1)[0][0] if srv_cnt else "—"
        _, top_srv_html = get_service_info_html(top_srv)
    else:
        top_srv_html = "—"

    maintenance = "🔴 ON" if bot_settings.get("maintenance_mode") else "🟢 OFF"

    return render_body_text(
        f"╔══════════════════╗\n"
        f"║ 📊 <b>LIVE BOT STATS</b>\n"
        f"╚══════════════════╝\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"🟢 Active Sessions: <b>{active_users}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📨 Today's OTPs: <b>{today_otps}</b>\n"
        f"🚀 All-Time OTPs: <b>{total_otps}</b>\n"
        f"⚡ Last 5 Min: <b>{recent_5} OTPs</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💸 Total Paid Out: <b>{total_paid:.2f} ৳</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🖥 Panels ON: <b>{panels_on}/{panels_total}</b>\n"
        f"🔥 Hot Service: {top_srv_html}\n"
        f"🔧 Maintenance: {maintenance}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )


# ==========================================
# 🌟 ADMIN: USER SEARCH / MANAGER
# ==========================================
def build_user_profile_text(target_uid):
    u      = get_user(int(target_uid))
    bal    = u.get("balance", 0.0)
    total  = u.get("total_otps", 0)
    today  = u.get("today_otps", 0)
    refs   = u.get("total_refers", 0)
    earned = u.get("total_earned", 0.0)
    banned = u.get("banned", False)
    streak = int(u.get("streak_days", 0))
    vip    = get_vip_label(total)

    # OTP history stats
    otp_hist   = user_otp_history.get(str(target_uid), [])
    num_hist   = user_number_history.get(str(target_uid), [])
    total_nums = len(num_hist)
    total_hist = len(otp_hist)

    # Service breakdown from OTP history
    srv_count = Counter(e.get("service","?").upper() for e in otp_hist)
    srv_lines = ""
    for srv, cnt in srv_count.most_common(5):
        apps_db  = bot_settings.get("premium_apps", {})
        emoji_id = "5352694861990501856"
        for app_key, app_data in apps_db.items():
            if srv == app_key or srv in app_key or app_key in srv:
                emoji_id = app_data.get("id", emoji_id)
                break
        srv_lines += f'  <tg-emoji emoji-id="{emoji_id}">{srv[:2]}</tg-emoji> {srv}: {cnt}\n'

    # Last 3 assigned numbers
    num_lines = ""
    for e in reversed(num_hist[-3:]):
        num_lines += f"  📱 <code>{mask_number(e['number'])}</code> — {e['service']} ({e['time']})\n"

    return render_body_text(
        f"👤 <b>User Profile</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{target_uid}</code>\n"
        f"{'🚫 BANNED' if banned else '✅ Active'} {vip}\n"
        f"🔥 Streak: <b>{streak} days</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Balance: <b>{bal:.2f} ৳</b>\n"
        f"💵 Total Earned: <b>{earned:.2f} ৳</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📨 OTPs: <b>{total}</b> (Today: {today})\n"
        f"📱 Numbers Assigned: <b>{total_nums}</b>\n"
        f"👥 Referrals: <b>{refs}</b>\n"
        + (f"━━━━━━━━━━━━━━━\n📊 <b>OTP by Service:</b>\n{srv_lines}" if srv_lines else "") +
        (f"━━━━━━━━━━━━━━━\n📱 <b>Last Numbers:</b>\n{num_lines}" if num_lines else "") +
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )

def user_manager_keyboard(target_uid, banned):
    return {"inline_keyboard": [
        [{"text": "🚫 Ban" if not banned else "✅ Unban", "callback_data": f"um_toggle_ban_{target_uid}", "style": "danger" if not banned else "success"},
         {"text": "💰 Add Balance", "callback_data": f"um_add_bal_{target_uid}", "style": "primary"}],
        [{"text": "📜 OTP History", "callback_data": f"um_history_{target_uid}", "style": "primary"},
         {"text": "🔄 Reset Balance", "callback_data": f"um_reset_bal_{target_uid}", "style": "danger"}],
        [{"text": "◀️ Back", "callback_data": "user_management", "style": "danger"}]
    ]}


# ==========================================
# 🌟 ADMIN: TOP USERS LEADERBOARD
# ==========================================
def build_leaderboard_text():
    if not user_cache:
        return render_body_text("📊 <b>Leaderboard</b>\n\n<i>No data yet.</i>")
    sorted_users = sorted(user_cache.items(), key=lambda x: x[1].get("total_otps", 0), reverse=True)[:10]
    lines = ""
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, (uid, u) in enumerate(sorted_users):
        total = u.get("total_otps", 0)
        bal   = u.get("balance", 0.0)
        vip   = get_vip_label(total)
        lines += f"{medals[i]} <code>{uid}</code> {vip}\n   📨 {total} OTPs | 💰 {bal:.1f} ৳\n"
    return render_body_text(
        f"🏆 <b>Top Users Leaderboard</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{lines}"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )


# ==========================================
# 🌟 ADMIN: COUNTRY-WISE TRAFFIC
# ==========================================
def build_country_traffic_text():
    """User-facing live traffic — country full name + premium emoji + service breakdown."""
    now = time.time()
    sample = [t for t in recent_traffic if now - t.get("time", 0) <= 3600]
    if not sample:
        sample = recent_traffic[-30:]
    if not sample:
        return render_body_text(
            "🌍 <b>Live Traffic</b>\n\n"
            "<i>No traffic data yet.\nCheck back in a few minutes.</i>"
        )

    country_counter = Counter(t.get("iso", "XX") for t in sample)
    service_counter = Counter(t.get("service", "?").upper() for t in sample)
    total = len(sample)

    # Country breakdown
    country_lines = ""
    for iso, cnt in country_counter.most_common(10):
        flag_html = get_flag_info_html(iso)
        c_name    = get_country_full_name(iso)
        pct       = int(cnt / total * 100)
        filled    = int(pct / 10)
        bar       = "█" * filled + "░" * (10 - filled)
        crown     = " 👑" if cnt == country_counter.most_common(1)[0][1] else ""
        country_lines += f"{flag_html} <b>{c_name}</b>{crown}\n  <code>{bar}</code> {cnt} OTPs ({pct}%)\n\n"

    # Service breakdown
    apps_db = bot_settings.get("premium_apps", {})
    service_lines = ""
    for srv, cnt in service_counter.most_common(5):
        emoji_id = "5352694861990501856"
        for app_key, app_data in apps_db.items():
            if srv == app_key or srv in app_key or app_key in srv:
                emoji_id = app_data.get("id", emoji_id)
                break
        pct      = int(cnt / total * 100)
        srv_html = f'<tg-emoji emoji-id="{emoji_id}">{srv[:2]}</tg-emoji>'
        service_lines += f"{srv_html} <b>{srv}</b> — {cnt} OTPs ({pct}%)\n"

    return render_body_text(
        f"🌍 <b>Live Traffic</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 Last <b>{total}</b> OTPs (1h)\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Countries:</b>\n{country_lines}"
        f"━━━━━━━━━━━━━━━\n"
        f"📱 <b>Services:</b>\n{service_lines}"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )



# ==========================================
# 🌟 CUSTOM REWARD PER SERVICE
# ==========================================
def get_service_reward(service_name):
    """
    Returns reward for a specific service.
    Checks bot_settings["service_rewards"] first, then falls back to global otp_reward.
    service_rewards = {"INSTAGRAM": 0.50, "WHATSAPP": 0.30, ...}
    """
    rewards = bot_settings.get("service_rewards", {})
    key = service_name.upper().strip()
    if key in rewards:
        return float(rewards[key])
    return float(bot_settings.get("otp_reward", 0.1))


# ==========================================
# 🌟 ERROR LOG — Silent admin alert
# ==========================================
_error_log = []   # [{time, source, error}]
_error_lock = threading.Lock()

def log_error(source, error_msg):
    """Log an error and silently notify admin."""
    now_str = bdt_str("%d %b %H:%M BDT")
    entry = {"time": now_str, "source": source, "error": str(error_msg)[:300]}
    with _error_lock:
        _error_log.append(entry)
        if len(_error_log) > 200:
            del _error_log[:len(_error_log) - 200]
    # Silent notify admin
    try:
        txt = render_body_text(
            f"🔴 <b>Error Log</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 Source: <code>{source}</code>\n"
            f"❌ Error: <code>{str(error_msg)[:250]}</code>\n"
            f"🕐 {now_str}"
        )
        send_message(OWNER_ID, txt)
    except: pass

def build_error_log_text(last_n=10):
    with _error_lock:
        recent = list(_error_log[-last_n:])
    if not recent:
        return render_body_text("📋 <b>Error Log</b>\n\n<i>No errors logged yet.</i>")
    lines = ""
    for e in reversed(recent):
        lines += f"📍 <code>{e['source']}</code>\n❌ <code>{e['error'][:120]}</code>\n🕐 {e['time']}\n\n"
    return render_body_text(
        f"📋 <b>Error Log (Last {len(recent)})</b>\n"
        f"━━━━━━━━━━━━━━━\n{lines}"
        f"━━━━━━━━━━━━━━━\n🕐 {bdt_str()}"
    )


# ==========================================
# 🌟 AUTO BACKUP — Daily at midnight BDT
# ==========================================
def do_backup():
    """Backup bot_settings to Firebase and notify admin."""
    try:
        backup_key = f"backup_{dhaka_now().strftime('%Y%m%d_%H%M')}"
        if db:
            db.collection("backups").document(backup_key).set({
                "data": json.dumps(bot_settings),
                "time": bdt_str(),
                "lines": len(json.dumps(bot_settings))
            })
        size_kb = len(json.dumps(bot_settings)) // 1024
        send_message(OWNER_ID, render_body_text(
            f"✅ <b>Auto Backup Complete!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 Key: <code>{backup_key}</code>\n"
            f"📦 Size: <b>{size_kb} KB</b>\n"
            f"☁️ Saved to Firebase\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕐 {bdt_str()}"
        ))
    except Exception as e:
        log_error("auto_backup", e)

def auto_backup_thread():
    """Runs daily at midnight BDT."""
    while True:
        try:
            now = dhaka_now()
            # Sleep until next midnight BDT
            import datetime as _dt
            tomorrow = (now + _dt.timedelta(days=1)).replace(
                hour=0, minute=0, second=5, microsecond=0)
            wait_sec = (tomorrow - now).total_seconds()
            time.sleep(max(wait_sec, 60))
            do_backup()
        except Exception as e:
            log_error("auto_backup_thread", e)
            time.sleep(3600)


# ==========================================
# 🌟 USER NUMBER HISTORY
# ==========================================
# {user_id: [ {number, service, time_str}, ... ]} max 5
user_number_history = {}

def record_user_number(user_id, number, service):
    """Store last 5 assigned numbers per user."""
    entry = {
        "number": number,
        "service": service.upper(),
        "time": bdt_str("%d %b %H:%M BDT")
    }
    hist = user_number_history.setdefault(str(user_id), [])
    # Avoid duplicate consecutive entry
    if hist and hist[-1]["number"] == number:
        return
    hist.append(entry)
    if len(hist) > 5:
        del hist[:len(hist) - 5]

def build_number_history_text(user_id):
    hist = user_number_history.get(str(user_id), [])
    if not hist:
        return render_body_text(
            "📱 <b>Your Number History</b>\n\n"
            "<i>No numbers assigned yet.</i>"
        )
    lines = ""
    medals = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
    for i, e in enumerate(reversed(hist)):
        masked = mask_number(e["number"])
        lines += (
            f"{medals[i]} <b>{e['service']}</b>\n"
            f"   📱 <code>{masked}</code>\n"
            f"   🕐 {e['time']}\n"
        )
    return render_body_text(
        f"📱 <b>Your Last Numbers</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{lines}"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {bdt_str()}"
    )



# ==========================================
def render_body_text(text):
    if not text: return str(text)
    parts = re.split(r'(<tg-emoji.*?</tg-emoji>)', str(text))
    for i in range(len(parts)):
        if not parts[i].startswith('<tg-emoji'):
            for normal_emj, prem_id in GLOBAL_BODY_EMOJIS.items():
                if normal_emj in parts[i]:
                    parts[i] = parts[i].replace(normal_emj, f'<tg-emoji emoji-id="{prem_id}">{normal_emj}</tg-emoji>')
    return "".join(parts)

def extract_premium_html(msg):
    text = msg.get("text", msg.get("caption", ""))
    entities = msg.get("entities", msg.get("caption_entities", []))
    if not entities: return text
    try:
        b_text = text.encode('utf-16-le')
        c_entities = [e for e in entities if e.get("type") == "custom_emoji"]
        c_entities.sort(key=lambda x: x["offset"], reverse=True)
        for ent in c_entities:
            offset = ent["offset"] * 2
            length = ent["length"] * 2
            eid = ent["custom_emoji_id"]
            emoji_char = b_text[offset:offset+length].decode('utf-16-le')
            html_tag = f'<tg-emoji emoji-id="{eid}">{emoji_char}</tg-emoji>'
            replacement = html_tag.encode('utf-16-le')
            b_text = b_text[:offset] + replacement + b_text[offset+length:]
        return b_text.decode('utf-16-le')
    except Exception as e:
        return text 

def get_flag_info_from_num(num):
    clean = num.replace("+", "").replace(" ", "")
    sorted_codes = sorted(bot_settings.get("premium_flags", {}).keys(), key=len, reverse=True)
    for code in sorted_codes:
        if clean.startswith(code):
            data = bot_settings["premium_flags"][code]
            return data["char"], data.get("iso", "XX"), data.get("id")
    return "🌍", "XX", None

def get_flag_and_code(num):
    char, iso, _ = get_flag_info_from_num(num)
    return char, iso

def get_country_full_name(iso_or_num):
    """Returns full country name from ISO code or phone number."""
    # Try ISO first
    iso = iso_or_num.upper().strip() if len(iso_or_num) <= 3 else None
    if not iso:
        _, iso, _ = get_flag_info_from_num(iso_or_num)
    for code, data in bot_settings.get("premium_flags", {}).items():
        if data.get("iso") == iso:
            return data.get("name", iso)
    return iso or "Unknown"

def get_flag_info_html(num_or_iso):
    """Returns premium <tg-emoji> HTML for flag. Works with ISO code or phone number."""
    flags = bot_settings.get("premium_flags", {})
    # ISO code (2 letters)
    if len(str(num_or_iso)) == 2:
        iso = str(num_or_iso).upper()
        for code, data in flags.items():
            if data.get("iso") == iso:
                eid  = data.get("id")
                char = data.get("char", "🌍")
                if eid: return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
                return char
        return "🌍"
    # Phone number
    char, _, eid = get_flag_info_from_num(str(num_or_iso))
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
    return char

def mask_number(num):
    clean = num.replace("+", "").replace(" ", "")
    if len(clean) > 6: return f"{clean[:3]} 『𝐄𝐗𝐄』 {clean[-3:]}"
    elif len(clean) > 2: return f"{clean[:1]} 『𝐄𝐗𝐄』 {clean[-1:]}"
    return clean

# ==========================================
# 🌟 ADVANCED SERVICE & LANGUAGE DETECTION
# ==========================================

SERVICE_SMS_KEYWORDS = {
    # 🟢 Social Media & Chat (Added Arabic Keywords)
    "whatsapp": ["whatsapp", "wap", "w/a", "whatsapp business", "wa.me", "wa code", "واتساب", "واتساپ", "واٹس ایپ", "व्हाट्सएप", "वाट्सएप", "वॉट्सऐप", "व्हाट्सप्प", "হোয়াটসঅ্যাপ", "হোটসঅ্যাপ", "ватсап", "уотсап", "вотсап", "ватс апп", "వాట్సాప్", "വാട്‌സ്ആപ്പ്", "வாட்ஸ்அப்", "ವಾಟ್ಸಾಪ್", "વોટ્સએપ", "ਵਟਸਐਪ", "ହ୍ଵାଟସ୍ ଆପ୍", "වට්ස්ඇප්", "วอตส์แอปป์", "วอทส์แอพ", "ဝက်စ်အက်ပ်", "វ៉តសាប់", "ວອດແອັບ", "ワッツアップ", "왓츠앱", "whatsapp的", "whatsapp验证码", "וואטסאפ", "γουάτσαπ", "ዋትስአፕ", "ვოთსאფი", "վոթսափ"],
    "facebook": ["facebook", "fb", "meta", "fbook", "fb code", "facebook code", "فيسبوك", "فيس بوك"],
    "instagram": ["instagram", "insta", "ig", "ig code", "instagram code", "انستغرام", "انستقرام"],
    "telegram": ["telegram", "tg", "tele", "telegram code", "tg code", "t.me", "تيليجرام", "تليجرام"],
    "tiktok": ["tiktok", "tik tok", "tikvideo", "tiktok code", "tik code", "تيك توك"],
    "snapchat": ["snapchat", "snap", "snap code", "سناب شات"],
    "twitter": ["twitter", "x.com", "x code", "twitter code", "تويتر"],
    "discord": ["discord", "discord code", "ديسكورد"],
    "viber": ["viber", "viber code", "فايبر"],
    "line": ["line", "line code", "line verification", "لاين"],
    "wechat": ["wechat", "we chat", "wechat code", "وي تشات"],
    "signal": ["signal", "signal code", "سيجنال"],
    "linkedin": ["linkedin", "linked in", "لينكد إن"],
    "imo": ["imo", "imo code", "imo verification", "ايمو"],
    "kakaotalk": ["kakao", "kakaotalk", "كاكاو"],
    "qq": ["qq", "tencent qq"],
    "vk": ["vk", "vkontakte"],

    # 🔵 Tech & Mail
    "google": ["google", "gmail", "youtube", "g-", "google voice", "جوجل", "غوغل"],
    "microsoft": ["microsoft", "ms", "outlook", "live.com", "hotmail"],
    "apple": ["apple", "icloud", "itunes", "apple id"],
    "yahoo": ["yahoo", "yahoo code", "ymail"],
    "protonmail": ["proton", "protonmail"],
    
    # 💰 Crypto & Trading
    "binance": ["binance", "bnb", "binances"],
    "coinbase": ["coinbase"],
    "okx": ["okx", "okex"],
    "kucoin": ["kucoin"],
    "bybit": ["bybit"],
    "huobi": ["huobi", "htx"],
    "mexc": ["mexc"],
    "trustwallet": ["trust wallet", "trustwallet"],

    # 💳 Finance & Wallets
    "bkash": ["bkash", "b-kash", "bkash code"],
    "nagad": ["nagad", "nagad code"],
    "rocket": ["rocket", "dutch bangla"],
    "upay": ["upay", "upay code"],
    "paypal": ["paypal", "pay pal"],
    "paytm": ["paytm"],
    "cashapp": ["cash app", "cashapp"],
    "wise": ["wise", "transferwise"],

    # 🛒 E-commerce & Delivery
    "amazon": ["amazon", "amzn", "amazon code"],
    "ebay": ["ebay"],
    "aliexpress": ["aliexpress", "ali express"],
    "alibaba": ["alibaba"],
    "daraz": ["daraz", "daraz code"],
    "foodpanda": ["foodpanda", "food panda"],
    "uber": ["uber", "uber code", "uber verification", "uber eats"],
    "pathao": ["pathao", "pathao ride"],

    # 🎮 Gaming & Entertainment
    "netflix": ["netflix", "netflix code"],
    "spotify": ["spotify", "spotify code"],
    "steam": ["steam", "steam guard"],
    "epicgames": ["epic games", "epicgames"],
    "roblox": ["roblox", "roblox code"],
    "riotgames": ["riot", "riot games", "valorant", "league of legends"],
    "garena": ["garena", "free fire", "freefire"],
    "playstation": ["playstation", "psn"],

    # 🎲 Betting & Casino
    "1xbet": ["1xbet", "1x bet"],
    "melbet": ["melbet", "melbet code"],
    "linebet": ["linebet"],
    "bet365": ["bet365"],
    "megapari": ["megapari"],

    # ❤️ Dating
    "tinder": ["tinder", "tinder code"],
    "bumble": ["bumble"],
    "badoo": ["badoo"]
}

def detect_service(text):
    text_lower = str(text).lower()
    # ১. আগে longer/exact keyword দিয়ে match করো (false positive এড়াতে)
    # প্রতিটা service এর keywords longest first sort করে check করো
    best_match = None
    best_len = 0
    for service_key, keywords in SERVICE_SMS_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower and len(kw) > best_len:
                best_match = service_key.upper()
                best_len = len(kw)
    return best_match

def get_service_info_html(service_text, msg_text=""):
    s = str(service_text).upper().strip()
    m = str(msg_text).lower().strip()
    apps = bot_settings.get("premium_apps", {})
    
    detected_service = s
    if m:
        for service_key, keywords in SERVICE_SMS_KEYWORDS.items():
            for kw in keywords:
                if kw in m:
                    detected_service = service_key.upper()
                    break
            if detected_service != s: break

    clean_s = re.sub(r'[^\w\s]', '', detected_service).strip()
    
    for app_name, data in apps.items():
        if app_name == detected_service or app_name == clean_s or app_name in detected_service or detected_service in app_name:
            full_name = data.get("name", app_name.title())
            char = data.get("char", "📱")
            eid = data.get("id")
            if eid: return full_name, f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
            return full_name, char
            
    if len(detected_service) > 20:
        return "Message", "💬"
        
    return detected_service.title(), "📱"

def detect_language(text):
    if not text: return "#EN"
    text_str = str(text)

    # ১. Unicode Block দিয়ে নিখুঁত বর্ণমালা শনাক্তকরণ (100% Accurate for scripts)
    if any('\u0600' <= c <= '\u06ff' for c in text_str): return "#AR" # Arabic / Persian / Urdu
    if any('\u0980' <= c <= '\u09ff' for c in text_str): return "#BN" # Bengali
    if any('\u0900' <= c <= '\u097f' for c in text_str): return "#HI" # Hindi / Marathi / Nepali
    if any('\u0a00' <= c <= '\u0a7f' for c in text_str): return "#PA" # Punjabi (Gurmukhi)
    if any('\u0a80' <= c <= '\u0aff' for c in text_str): return "#GU" # Gujarati
    if any('\u0b00' <= c <= '\u0b7f' for c in text_str): return "#OR" # Odia
    if any('\u0b80' <= c <= '\u0bff' for c in text_str): return "#TA" # Tamil
    if any('\u0c00' <= c <= '\u0c7f' for c in text_str): return "#TE" # Telugu
    if any('\u0c80' <= c <= '\u0cff' for c in text_str): return "#KN" # Kannada
    if any('\u0d00' <= c <= '\u0d7f' for c in text_str): return "#ML" # Malayalam
    if any('\u0d80' <= c <= '\u0dff' for c in text_str): return "#SI" # Sinhala
    if any('\u0e00' <= c <= '\u0e7f' for c in text_str): return "#TH" # Thai
    if any('\u0e80' <= c <= '\u0eff' for c in text_str): return "#LO" # Lao
    if any('\u0f00' <= c <= '\u0fff' for c in text_str): return "#BO" # Tibetan
    if any('\u1000' <= c <= '\u109f' for c in text_str): return "#MY" # Burmese (Myanmar)
    if any('\u1200' <= c <= '\u137f' for c in text_str): return "#AM" # Amharic (Ethiopic)
    if any('\u1780' <= c <= '\u17ff' for c in text_str): return "#KM" # Khmer
    if any('\u10a0' <= c <= '\u10ff' for c in text_str): return "#KA" # Georgian
    if any('\u0530' <= c <= '\u058f' for c in text_str): return "#HY" # Armenian
    if any('\u0590' <= c <= '\u05ff' for c in text_str): return "#HE" # Hebrew
    if any('\u0370' <= c <= '\u03ff' for c in text_str): return "#EL" # Greek
    if any('\u0400' <= c <= '\u04ff' for c in text_str): return "#RU" # Russian / Ukrainian (Cyrillic)
    if any('\u4e00' <= c <= '\u9fff' for c in text_str): return "#ZH" # Chinese
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text_str): return "#JA" # Japanese
    if any('\uac00' <= c <= '\ud7af' for c in text_str): return "#KO" # Korean

    # ২. OTP Keyword দিয়ে ভাষা শনাক্তকরণ (Latin script languages)
    text_lower = text_str.lower()
    
    # Asian / Pacific
    if any(w in text_lower for w in ["kode verifikasi", "jangan bagikan", "rahasia"]): return "#ID" # Indonesian
    if any(w in text_lower for w in ["kod pengesahan", "jangan kongsi"]): return "#MS" # Malay
    if any(w in text_lower for w in ["mã của bạn", "không chia sẻ", "mã xác minh"]): return "#VN" # Vietnamese
    if any(w in text_lower for w in ["ang iyong code", "huwag ibahagi"]): return "#TL" # Tagalog / Filipino
    
    # European / Americas
    if any(w in text_lower for w in ["código", "tu código", "verificación", "no compartas"]): return "#ES" # Spanish
    if any(w in text_lower for w in ["seu código", "código de verificação", "não compartilhe"]): return "#PT" # Portuguese
    if any(w in text_lower for w in ["code secret", "ne partagez pas", "votre code"]): return "#FR" # French
    if any(w in text_lower for w in ["dein code", "bestätigungscode", "nicht teilen"]): return "#DE" # German
    if any(w in text_lower for w in ["il tuo codice", "codice di verifica", "non condividere"]): return "#IT" # Italian
    if any(w in text_lower for w in ["twój kod", "nie udostępniaj", "kod weryfikacyjny"]): return "#PL" # Polish
    if any(w in text_lower for w in ["doğrulama kodu", "paylaşmayın", "onay kodu"]): return "#TR" # Turkish
    if any(w in text_lower for w in ["jouw code", "verificatiecode", "niet delen"]): return "#NL" # Dutch
    if any(w in text_lower for w in ["din kod", "verifieringskod", "dela inte"]): return "#SV" # Swedish
    if any(w in text_lower for w in ["bekræftelseskode", "del ikke"]): return "#DA" # Danish
    if any(w in text_lower for w in ["bekreftelseskode", "ikke del"]): return "#NO" # Norwegian
    if any(w in text_lower for w in ["vahvistuskoodi", "älä jaa"]): return "#FI" # Finnish
    if any(w in text_lower for w in ["váš kód", "ověřovací kód", "nesdílejte"]): return "#CS" # Czech
    if any(w in text_lower for w in ["overovací kód", "nezdieľajte"]): return "#SK" # Slovak
    if any(w in text_lower for w in ["ellenőrző kód", "ne oszd meg"]): return "#HU" # Hungarian
    if any(w in text_lower for w in ["codul tău", "codul de verificare", "nu partaja"]): return "#RO" # Romanian
    if any(w in text_lower for w in ["kontrolni kod", "kod za potvrdu", "ne delite"]): return "#HR" # Croatian/Serbian
    if any(w in text_lower for w in ["код за потвърждение", "не споделяйте"]): return "#BG" # Bulgarian
    if any(w in text_lower for w in ["ваш код", "код підтвердження"]): return "#UK" # Ukrainian
    
    # African
    if any(w in text_lower for w in ["msimbo wako", "usishiriki"]): return "#SW" # Swahili
    if any(w in text_lower for w in ["verifikasiekode", "moenie deel nie"]): return "#AF" # Afrikaans
    
    # ৩. উপরের কোনোটি না মিললে ডিফল্ট
    return "#EN"

def parse_chat_id(text):
    text = text.strip()
    if text.startswith("-100") or (text.startswith("-") and text[1:].isdigit()):
        return text
    if "t.me/" in text:
        parts = text.split("/")
        username = parts[-1]
        if username: return "@" + username if not username.startswith("@") else username
    if text.startswith("@"):
        return text
    return "@" + text

def is_admin(user_id):
    return user_id in bot_settings["admins"] or user_id == OWNER_ID

def check_force_join(user_id):
    if not bot_settings["fj_on"] or not bot_settings["fj_channels"]: return True
    if is_admin(user_id): return True
    for ch in bot_settings["fj_channels"]:
        try:
            res = api_call("getChatMember", {"chat_id": ch, "user_id": user_id})
            if not res.get("ok"):
                continue  # API error হলে এই channel skip করো, block করো না
            status = res["result"]["status"]
            if status in ["left", "kicked"]:
                return False
        except:
            continue  # Exception হলেও block করবে না
    return True

def send_force_join_msg(chat_id):
    kb = []
    for ch in bot_settings["fj_channels"]:
        url = f"https://t.me/{ch.replace('@', '')}" if ch.startswith("@") else ch
        kb.append([{"text": f"Join Channel", "icon_custom_emoji_id": "5789428375261023681", "url": url, "style": "primary"}])
    kb.append([{"text": "Check Joined", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "check_fj", "style": "success"}])
    send_message(chat_id, render_body_text(f"{PEM['warn']} <b>Please join our channels to use the bot!</b>"), reply_markup={"inline_keyboard": kb})

def is_user_banned(user_id):
    if is_admin(user_id): return False
    if user_id in user_banned_cache and time.time() - user_banned_cache[user_id]['time'] < 60:
        return user_banned_cache[user_id]['banned']
    # user_cache থেকে আগে check (Firestore read বাঁচায়)
    if user_id in user_cache:
        banned = user_cache[user_id].get("banned", False)
        user_banned_cache[user_id] = {'banned': banned, 'time': time.time()}
        return banned
    banned = False
    if db:
        try:
            doc = db.collection('users').document(str(user_id)).get()
            if doc.exists:
                data = doc.to_dict()
                banned = data.get("banned", False)
                user_cache[user_id] = data  # cache এ রাখো
        except: pass
    user_banned_cache[user_id] = {'banned': banned, 'time': time.time()}
    return banned

# ==========================================
# Captcha Auto Login & Parsing Core
# ==========================================
def extract_otp_code(text):
    clean_text = re.sub(r'[\u200B-\u200D\uFEFF]', '', str(text))

    # 1. Multi-part OTPs (e.g. 123-456 or 809-761)
    multi_part = re.search(r'(\d{3}[-\s]+\d{3})|(\d{2}[-\s]+\d{2}[-\s]+\d{2})', clean_text)
    if multi_part:
        # হাইফেন (-) থাকলে সেটা রেখে দিবে, কিন্তু স্পেস থাকলে মুছে একসাথে করে দিবে
        return multi_part.group(0).replace(" ", "")

    # 2. Keyword-based extraction
    otp_keywords = ['code', 'is', 'otp', 'pin', 'verification', 'auth', 'কোড', 'رمز', 'your code']
    keywords_pattern = '|'.join(otp_keywords)
    keyword_match = re.search(rf'(?:{keywords_pattern})\s*(?:is|:|-|=)?\s*([a-z0-9]{{4,10}})', clean_text, re.I)
    if keyword_match and keyword_match.group(1).isdigit():
        return keyword_match.group(1)
        
    keyword_match_rev = re.search(rf'([a-z0-9]{{4,10}})\s*(?:is your|is the|কোড)', clean_text, re.I)
    if keyword_match_rev and keyword_match_rev.group(1).isdigit():
        return keyword_match_rev.group(1)

    # 3. Google OTP
    g_match = re.search(r'G-(\d{6})', clean_text, re.IGNORECASE)
    if g_match: return g_match.group(1)

    # 4. Digit sequences fallback
    digit_matches = re.findall(r'(?<!\d)\d{4,8}(?!\d)', clean_text)
    if digit_matches: return digit_matches[0]

    return None

def parse_panel_response(response_text, p_config=None):
    results = []
    p_type = p_config.get("type", "API Panel") if p_config else "API Panel"
    
    n_col_name = p_config.get("num_col_name", "number").lower() if p_config else "number"
    m_col_name = p_config.get("msg_col_name", "message").lower() if p_config else "message"
    n_idx = int(p_config.get("num_col_idx", 1)) - 1 if p_config and p_config.get("num_col_idx") else 1
    m_idx = int(p_config.get("msg_col_idx", 2)) - 1 if p_config and p_config.get("msg_col_idx") else 2

    if p_type == "Auto Captcha Panel":
        try:
            soup = BeautifulSoup(response_text, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if not rows: continue
                
                # 🌟 Option 1 + Smart HTML Detection: কলামের নাম ও ব্যবহারকারীর দেওয়া সিরিয়াল দিয়ে সঠিক পজিশন বের করা
                final_n_idx = n_idx
                final_m_idx = m_idx
                
                # প্রথম রো (Header) চেক করে কলামের আসল সিরিয়াল মিলিয়ে নেওয়া
                header_cells = rows[0].find_all(['th', 'td'])
                for i, cell in enumerate(header_cells):
                    c_text = cell.get_text(strip=True).lower()
                    if n_col_name in c_text: final_n_idx = i
                    if m_col_name in c_text: final_m_idx = i

                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    
                    # হেডার রো (যেখানে সব th থাকে) সেগুলো থেকে ডাটা নিবে না
                    if all(c.name == 'th' for c in cols): continue
                    
                    if len(cols) > max(final_n_idx, final_m_idx):
                        # HTML টেবিল থেকে টেক্সট বের করা
                        num_text = cols[final_n_idx].get_text(separator=" ", strip=True)
                        msg_text = cols[final_m_idx].get_text(separator=" ", strip=True)
                        
                        clean_num = re.sub(r'\D', '', num_text)
                        
                        # নাম্বারটা আসলেই ৫-১৮ ডিজিটের কিনা তা নিশ্চিত করা (যাতে উল্টাপাল্টা টেক্সট না আসে)
                        if clean_num and 5 <= len(clean_num) <= 18:
                            otp = extract_otp_code(msg_text)
                            if otp and len(msg_text) > 4:
                                results.append({"number": clean_num, "message": msg_text, "otp": otp})
        except Exception as e:
            pass
    else:
        try:
            data = json.loads(response_text)
            temp_results = []
            
            def process_item(item):
                pot_nums_list = []
                pot_msg = None
                values = []
                
                if isinstance(item, dict):
                    # ১. প্রথমে পরিচিত JSON Key (যেমন: num, phone, sms) দিয়ে খোঁজার চেষ্টা
                    lower_keys = {str(k).lower(): v for k, v in item.items()}
                    for k in ["number", "num", "phone", "msisdn", "sender"]:
                        if k in lower_keys:
                            clean_val = re.sub(r'\D', '', str(lower_keys[k]))
                            if 5 <= len(clean_val) <= 18:
                                if clean_val not in pot_nums_list: pot_nums_list.append(clean_val)
                    for k in ["message", "msg", "sms", "content", "text"]:
                        if k in lower_keys:
                            val = str(lower_keys[k])
                            if len(val) > 4:
                                pot_msg = val
                                break
                    values = list(item.values())
                elif isinstance(item, list):
                    values = item

                # ২. যদি Key দিয়ে না পাওয়া যায়, তবে Smart Blind Scan (সব ভ্যালু চেক করবে)
                for v in values:
                    if isinstance(v, (dict, list)) or v is None: continue
                    v_str = str(v).strip()
                    
                    # Number Detection: 7 থেকে 18 ডিজিট
                    clean_v = re.sub(r'\D', '', v_str)
                    if 7 <= len(clean_v) <= 18 and not re.search(r'[a-zA-Z]', v_str):
                        # Date/Time/IP এড়ানোর লজিক
                        if not re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', v_str) and not re.search(r'\d{2}:\d{2}:\d{2}', v_str) and "." not in v_str:
                            if clean_v not in pot_nums_list:
                                pot_nums_list.append(clean_v)
                    
                    # Message Detection: 5 অক্ষরের বেশি এবং শুধু সংখ্যা নয়
                    if len(v_str) > 4 and not v_str.isdigit():
                        if extract_otp_code(v_str):
                            if pot_msg is None or len(v_str) > len(pot_msg):
                                pot_msg = v_str
                                
                # 🌟 ৩. Multiple Numbers Logic (User Priority > Second Number > First Number)
                pot_num = None
                if pot_nums_list:
                    matched_user_num = None
                    for n in pot_nums_list:
                        # চেক করবে ইউজারের অ্যাসাইন করা নাম্বারের তালিকায় এই নাম্বারটি আছে কি না
                        if n in nexa_assigned_numbers or any(n in str(key) for key in nexa_assigned_numbers.keys()):
                            matched_user_num = n
                            break
                    
                    if matched_user_num:
                        pot_num = matched_user_num
                    elif len(pot_nums_list) >= 2:
                        pot_num = pot_nums_list[1] # ইউজারের কাছে না থাকলে সরাসরি দ্বিতীয় নাম্বারটি নেবে
                    else:
                        pot_num = pot_nums_list[0]
                            
                if pot_num and pot_msg:
                    otp = extract_otp_code(pot_msg)
                    if otp:
                        temp_results.append({"number": pot_num, "message": pot_msg, "otp": otp})
                        
            def traverse_json(node):
                if isinstance(node, list):
                    if len(node) > 0 and not isinstance(node[0], (dict, list)):
                        # It's a flat list representing one record
                        process_item(node)
                    for child in node:
                        if isinstance(child, (dict, list)):
                            traverse_json(child)
                elif isinstance(node, dict):
                    process_item(node)
                    for val in node.values():
                        if isinstance(val, (dict, list)):
                            traverse_json(val)

            traverse_json(data)
            
            # Remove duplicates
            seen = set()
            for r in temp_results:
                uid = f"{r['number']}_{r['otp']}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(r)
        except: pass
        
    return results

# 🌟 Advanced Automated Background Captcha Solver 🌟
def attempt_auto_login(p, idx):
    login_url = p.get("login_url", "").strip()
    if not login_url.startswith("http"):
        login_url = "http://" + login_url
        
    if not login_url.lower().endswith('/login') and not login_url.lower().endswith('.php'):
        login_url = f"{login_url.rstrip('/')}/login"
        
    session = _make_stex_session(verify_ssl=True)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    
    try:
        res = session.get(login_url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        all_text = res.text
        
        # 1. SOLVE CAPTCHA (Exact bot 3.py logic)
        captcha_match = re.search(r'(\d+\s*[\+\-\*]\s*\d+)\s*[=\?:]', all_text)
        if not captcha_match:
            captcha_match = re.search(r'what is\s*(\d+\s*[\+\-\*]\s*\d+)', all_text, re.I)
        if not captcha_match:
            elements = soup.find_all(["label", "div", "span", "p", "strong"])
            for el in elements:
                txt = el.get_text(separator=" ", strip=True)
                if any(op in txt for op in ["+", "-", "*"]):
                    m = re.search(r'(\d+\s*[\+\-\*]\s*\d+)', txt)
                    if m:
                        captcha_match = m
                        break
                        
        captcha_text = captcha_match.group(1) if captcha_match else None
        answer = "0"
        m2 = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', captcha_text)
        if m2:
            a, op, b = int(m2.group(1)), m2.group(2), int(m2.group(3))
            if op == '+': answer = str(a + b)
            elif op == '-': answer = str(a - b)
            elif op == '*': answer = str(a * b)

        # 2. FIND FORM
        form = soup.find("form")
        if not form:
            p["login_status"] = "❌ No login form found"
            return False
            
        action = form.get("action")
        from urllib.parse import urljoin
        post_url = urljoin(login_url, action) if action else login_url

        form_data = {}
        for hidden in form.find_all("input", type="hidden"):
            name = hidden.get("name")
            if name: form_data[name] = hidden.get("value") or ""
        
        user_input = form.find("input", {"name": re.compile(r"user|email|id", re.I)}) or \
                     form.find("input", {"type": "text", "placeholder": re.compile(r"user|email", re.I)}) or \
                     form.find("input", {"type": "text"})
                     
        pass_input = form.find("input", {"name": re.compile(r"pass", re.I)}) or \
                     form.find("input", {"type": "password"})
                     
        captcha_input = form.find("input", {"placeholder": re.compile(r"answer|ans|code|verification|value|captcha", re.I)}) or \
                        form.find("input", {"name": re.compile(r"ans|captcha|ver|code", re.I)})
        
        user_field = user_input.get("name") if user_input else "username"
        pass_field = pass_input.get("name") if pass_input else "password"
        captcha_field = captcha_input.get("name") if captcha_input else "answer"

        form_data[user_field] = p.get("username", "")
        form_data[pass_field] = p.get("password", "")
        if captcha_field and captcha_text:
            form_data[captcha_field] = answer

        # 3. SUBMIT
        login_req = session.post(post_url, data=form_data, allow_redirects=True, timeout=15)
        
        # 4. VERIFY (Exact bot 3.py check logic)
        msg_link = p.get("msg_link", "").strip()
        if not msg_link.startswith("http") and msg_link != "":
            msg_link = "http://" + msg_link
            
        check_url = msg_link if msg_link else f"{login_url.split('/login')[0]}/client/SMSCDRStats"
        
        check_res = session.get(check_url, timeout=10)
        
        if 'logout' in login_req.text.lower() or 'logout' in check_res.text.lower() or 'sms reports' in check_res.text.lower() or 'dashboard' in check_res.text.lower() or 'cdrs' in check_res.text.lower():
            panel_sessions[idx] = session
            p["login_status"] = "✅ Active & Fetching"
            return True
        else:
            # এখানে ফেইল হলে অংক কী পেয়েছিল তা দেখা যাবে
            p["login_status"] = f"❌ Login Failed (Math: {captcha_text or 'No captcha'} = {answer})"
            return False
            
    except Exception as e:
        p["login_status"] = f"❌ Error: {str(e)[:20]}"
        
    return False

def panel_monitor_thread():
    global processed_otps, recent_traffic, panel_sessions, panel_otp_log
    while True:
        try:
            for idx, p in enumerate(bot_settings.get("panels", [])):
                if p.get("status") == "ON":
                    
                    if p.get("type") == "Auto Captcha Panel":
                        sess = panel_sessions.get(idx)
                        
                        if not sess:
                            now = time.time()
                            if now - p.get("last_login_attempt", 0) < 30: 
                                continue 
                            p["last_login_attempt"] = now
                            
                            success = attempt_auto_login(p, idx)
                            save_db() # Save login status text to show in settings
                            if not success:
                                continue 
                            sess = panel_sessions.get(idx)
                            
                        try:
                            # 🌟 auto sessions with sAjaxSource and Fallback HTML Parser
                            parsed_data, res_text = fetch_cpt_panel_cdrs(p, sess, p["msg_link"])
                            p["login_status"] = "✅ Active & Fetching"
                        except Exception as e:
                            p["login_status"] = "❌ Session Expired (Retrying...)"
                            del panel_sessions[idx]
                            save_db()
                            continue

                    elif p.get("api_url") or p.get("full_api_url"): 
                        full_url = p.get("full_api_url", "").strip()
                        url = p.get("api_url", "").strip()
                        token = p.get("token", "").strip()
                        if not full_url and not url: continue
                        
                        urls_to_try = []
                        if full_url:
                            urls_to_try.append(full_url)
                        else:
                            if "{token}" in url or "{key}" in url:
                                urls_to_try.append(url.replace("{token}", token).replace("{key}", token))
                            elif "token=" in url or "key=" in url:
                                urls_to_try.append(url)
                            else:
                                sep = '&' if '?' in url else '?'
                                urls_to_try.append(f"{url}{sep}token={token}")
                                urls_to_try.append(f"{url}{sep}key={token}&start=0")
                                urls_to_try.append(f"{url}{sep}key={token}")
                            
                        parsed_data = []
                        # 🌟 Browser Bypass (403 Forbidden Fix)
                        base_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                        
                        # Stex/Voltx: mauthapi header দিয়ে call করতে হয়
                        is_stex_panel = "2oo9.cloud" in (full_url or url) and "tness" in (full_url or url)
                        is_voltx_panel = "2oo9.cloud" in (full_url or url) and "tnevs" in (full_url or url)
                        
                        if is_stex_panel or is_voltx_panel:
                            # token: panel token field অথবা stex_keys/voltx_keys list থেকে নাও
                            auth_token = token
                            if not auth_token:
                                key_list = bot_settings.get("stex_keys" if is_stex_panel else "voltx_keys", [])
                                if key_list:
                                    auth_token = key_list[0]
                            if not auth_token:
                                continue
                            stex_panel_url = full_url or f"https://api.2oo9.cloud/MXS47FLFX0U/{'tness' if is_stex_panel else 'tnevs'}/@public/api/success-otp"
                            stex_panel_headers = {**base_headers, "mauthapi": auth_token}
                            try:
                                res = stex_get(stex_panel_url, headers=stex_panel_headers)
                                resp_json = res.json()
                                if resp_json.get("meta", {}).get("code") == 200:
                                    for item in resp_json.get("data", {}).get("otps", []):
                                        num = re.sub(r'\D', '', str(item.get("number", "")))
                                        msg_text = str(item.get("message", ""))
                                        otp = extract_otp_code(msg_text)
                                        if num and msg_text and otp:
                                            parsed_data.append({"number": num, "message": msg_text, "otp": otp})
                            except: pass
                        else:
                            for try_url in urls_to_try:
                                try:
                                    res = stex_get(try_url, headers=base_headers)
                                    parsed_data = parse_panel_response(res.text, p)
                                    if parsed_data:
                                        if not full_url and try_url != url and token:
                                            p["api_url"] = try_url.replace(token, "{token}")
                                            save_db()
                                        break
                                except: continue
                        if not parsed_data: continue
                    else:
                        continue
                    
                    if p.get("type") != "Auto Captcha Panel":
                        limit = p.get("records", 0)
                        if limit > 0: parsed_data = parsed_data[:limit]
                        
                    for item in parsed_data:
                        num = item["number"]
                        otp = item["otp"]
                        msg_text = item["message"]
                        unique_id = f"{num}_{otp}"

                        # 🌟 Log EVERY raw item the panel returned (incl. duplicates) for Panel vs Group analysis
                        pg_now = time.time()
                        panel_otp_log = [t for t in panel_otp_log if pg_now - t.get("time", 0) <= 3600]
                        panel_otp_log.append({"number": num, "time": pg_now})
                        
                        if unique_id not in processed_otps:
                            processed_otps.add(unique_id)
                            if len(processed_otps) > 5000: processed_otps = set(list(processed_otps)[-2000:])
                                 
                            char, iso = get_flag_and_code(num)
                            app_full_name, prem_app_html = get_service_info_html(p.get("name", "Panel"), msg_text)
                            current_time = time.time()
                            
                            recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                            recent_traffic.append({
                                "service": app_full_name,
                                "iso": iso,
                                "flag": char,
                                "number": num,
                                "time": current_time
                            })
                            # 🌟 শুধু লোকাল ফাইলে সেভ করবে, Firestore এ অহেতুক Write করবে না!
                                 
                            display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                            masked = mask_number(display_num)
                            lang = detect_language(msg_text)
                            
                            print(f"[FW DEBUG] Forwarding OTP={otp} num={display_num} to {len(bot_settings.get(chr(102)+chr(119)+chr(95)+chr(103)+chr(114)+chr(111)+chr(117)+chr(112)+chr(115), []))} groups")
                            send_to_forward_groups(prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, masked, lang, otp, unique_id, msg_text, iso)
                            save_local_db()  # moved after forward

                            
                            owners = []
                            clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                            
                            # 🌟 ALGORITHM FIX: সরাসরি Active Sessions থেকে মালিক খোঁজা 
                            # (কারণ Local Stock থেকে নাম্বার Assign হওয়ার সাথে সাথে ডিলিট হয়ে যায়)
                            for uid, session_data in user_active_sessions.items():
                                for act_num in session_data.get("nums", []):
                                    act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                    if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                        owners.append(uid)
                                        break
                                        
                            # ব্যাকআপ হিসেবে Nexa-তে চেক করা 
                            if not owners:
                                for nexa_n, n_owner in nexa_assigned_numbers.items():
                                    clean_nexa = str(nexa_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                    if clean_nexa == clean_api_num or (len(clean_nexa) >= 8 and clean_nexa.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_nexa[-8:])):
                                        owners.append(n_owner)
                                        
                            owners = list(set(owners)) 
                            for owner_id in owners:
                                reward = get_service_reward(app_full_name)
                                send_inbox_otp(owner_id, prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, lang, otp, reward, msg_text)
                                increment_user_otp(owner_id, number=display_num)
        except Exception as e:
            try:
                send_message(OWNER_ID, f"⚠️ <b>Panel Monitor Error:</b>\n<code>{html.escape(str(e))}</code>")
            except: pass
        time.sleep(5) 

# ==========================================
# Firebase User Management
# ==========================================
# 🌟 Local User Cache: বারবার Firestore থেকে Read করা বন্ধ করবে!
user_cache = {}

def get_user(user_id):
    if user_id in user_cache:
        # Always use local balance as source of truth
        user_cache[user_id]["balance"] = _get_local_balance(user_id)
        return user_cache[user_id]
    if not db:
        bal = _get_local_balance(user_id)
        return {"user_id": user_id, "balance": bal, "total_refers": 0, "total_otps": 0, "today_otps": 0, "total_earned": bal}
    
    doc_ref = db.collection('users').document(str(user_id))
    doc = doc_ref.get()
    if doc.exists: 
        data = doc.to_dict()
        if "total_otps" not in data: data["total_otps"] = 0
        if "today_otps" not in data: data["today_otps"] = 0
        if "total_earned" not in data: data["total_earned"] = data.get("balance", 0.0)
        if "banned" not in data: data["banned"] = False
        if "verified" not in data: data["verified"] = False
        # Override balance with local file (most up-to-date)
        data["balance"] = _get_local_balance(user_id) or data.get("balance", 0.0)
        # Seed local balance if not set yet
        if str(user_id) not in _local_balances:
            _set_local_balance(user_id, data["balance"])
        user_cache[user_id] = data
        return data
    else:
        bal = _get_local_balance(user_id)
        new_user = {"user_id": user_id, "balance": bal, "total_refers": 0, "total_otps": 0, "today_otps": 0, "total_earned": bal, "banned": False, "verified": False}
        doc_ref.set(new_user)
        user_cache[user_id] = new_user
        return new_user

def update_balance(user_id, amount):
    amount = float(amount)
    uid_str = str(user_id)

    # 1. Update local cache
    if user_id in user_cache:
        user_cache[user_id]["balance"] = user_cache[user_id].get("balance", 0.0) + amount
        if amount > 0:
            user_cache[user_id]["total_earned"] = user_cache[user_id].get("total_earned", 0.0) + amount

    # 2. Update balances.json (primary storage — no Firebase call here)
    current = _get_local_balance(user_id)
    _set_local_balance(user_id, current + amount)

    # 3. Update global aggregates (local only)
    bot_settings["global_balance_pool"] = bot_settings.get("global_balance_pool", 0.0) + amount
    if amount > 0:
        bot_settings["global_total_earned"] = bot_settings.get("global_total_earned", 0.0) + amount
    # Firebase sync happens in background every 5 min via _firebase_balance_sync_thread

def increment_user_otp(owner_id, number=None):
    """🌟 Bumps total_otps, today_otps, and global_total_otps.
    If number is given, only counts once per unique number (blocks duplicates)."""
    # 🌟 Same number — count একবারই হবে
    if number:
        count_key = f"cnt_{owner_id}_{str(number).replace('+','').strip()}"
        if count_key in _rewarded_numbers:
            return  # already counted for this number
        _rewarded_numbers.add(count_key)

    if owner_id in user_cache:
        user_cache[owner_id]["total_otps"] = user_cache[owner_id].get("total_otps", 0) + 1
        user_cache[owner_id]["today_otps"] = user_cache[owner_id].get("today_otps", 0) + 1
    bot_settings["global_total_otps"] = bot_settings.get("global_total_otps", 0) + 1
    if not db: return
    try:
        db.collection('users').document(str(owner_id)).set({
            "total_otps": firestore.Increment(1),
            "today_otps": firestore.Increment(1)
        }, merge=True)
    except: pass

def pay_referral_commission(owner_id, reward, number=None):
    """Referrer gets commission when their referral earns OTP reward.
    number param ensures only 1 commission per unique number."""
    try:
        if reward <= 0: return
        rate = float(bot_settings.get("referral_commission", 0.0)) / 100.0
        if rate <= 0: return

        u_data = get_user(owner_id)
        inviter = u_data.get("referred_by")
        if not inviter: return
        inviter = int(inviter) if str(inviter).isdigit() else inviter
        if inviter == owner_id: return

        # 🌟 Same number থেকে একবারই commission — duplicate block
        if number:
            num_clean = str(number).replace("+", "").strip()
            commission_key = f"{inviter}_{num_clean}"
            if commission_key in _commissioned_numbers:
                return  # already paid for this number
            _commissioned_numbers.add(commission_key)
            if len(_commissioned_numbers) > 10000:
                # keep set small
                _commissioned_numbers.clear()

        commission = round(reward * rate, 4)
        if commission <= 0: return

        update_balance(inviter, commission)
        send_message(inviter, render_body_text(
            f"{PEM['money']} <b>Referral Commission!</b>\n"
            f"➖➖➖➖➖➖➖\n"
            f"You earned <b>{commission} ৳</b> ({bot_settings.get('referral_commission', 0)}%) commission\n"
            f"from your referral's OTP reward.\n"
            f"➖➖➖➖➖➖➖"
        ))
    except: pass

def add_referral(inviter_id, new_user_id):
    if not db.collection('users').document(str(new_user_id)).get().exists:
        get_user(new_user_id) 
        reward = bot_settings.get("refer_reward", 0.2)
        update_balance(inviter_id, reward)
        db.collection('users').document(str(inviter_id)).update({"total_refers": firestore.Increment(1)})
        
        # আপনার দেওয়া নতুন ডিজাইন
        ref_msg = (
            f"{PEM['gift']} <b>New Referral !</b>\n"
            f"------------------\n"
            f"🔥 <b>You Received {reward} TK</b>\n"
            f"------------------\n"
            f"{PEM['user']} <b>From User ID:</b> <code>{new_user_id}</code>"
        )
        send_message(inviter_id, render_body_text(ref_msg))

# ==========================================
# UI Keyboards & Menu Builders
# ==========================================
def get_cancel_kb():
    return {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_state", "style": "danger"}]]}


def handle_webapp_data(chat_id, web_app_data):
    """Handle data sent from Mini App via Telegram.WebApp.sendData()"""
    import json as _json
    try:
        data = _json.loads(web_app_data)
        action = data.get("action", "")
        uid = data.get("user_id") or chat_id

        if action == "get_stex_console":
            stex_keys = bot_settings.get("stex_keys", [])
            if not stex_keys:
                send_message(chat_id, _json.dumps({"type":"stex_console","data":[]}))
                return
            try:
                res = stex_get(f"{STEX_BASE_URL}/console", headers={"mauthapi": stex_keys[0]})
                if res.status_code == 200:
                    hits = res.json().get("data", {}).get("hits", [])
                    send_message(chat_id, _json.dumps({"type": "stex_console", "data": hits}))
                    send_message(chat_id, _json.dumps({"type": "stex_api_key", "key": stex_keys[0]}))
            except Exception as e:
                print(f"[WEBAPP] STEX console error: {e}")

        elif action == "get_console":
            recent = panel_otp_log[-50:][::-1]
            send_message(chat_id, _json.dumps({"type": "console_data", "data": recent}))

        elif action == "get_withdraw_history":
            if db:
                try:
                    ws = db.collection("withdrawals").where("user_id", "==", str(uid)).order_by("timestamp", direction="DESCENDING").limit(20).stream()
                    history = [{"method": w.to_dict().get("method",""), "amount": w.to_dict().get("amount",0), "status": w.to_dict().get("status","pending"), "date": str(w.to_dict().get("timestamp",""))[:10]} for w in ws]
                    send_message(chat_id, _json.dumps({"type": "withdraw_history", "data": history}))
                except: pass

        elif action == "withdraw":
            method = data.get("method","")
            number = data.get("number","")
            amount = float(data.get("amount", 0))
            u = get_user(chat_id)
            bal = _get_local_balance(chat_id)
            min_w = float(bot_settings.get("min_withdraw", 30))
            if bal < amount:
                send_message(chat_id, f"❌ Insufficient balance! Your balance: ৳{bal:.2f}")
            elif amount < min_w:
                send_message(chat_id, f"❌ Minimum withdrawal: ৳{min_w}")
            else:
                import uuid as _uuid
                req_id = _uuid.uuid4().hex[:10].upper()
                pending_withdrawals[req_id] = {"user_id": chat_id, "amount": amount, "method": method, "number": number, "full_name": u.get("first_name","User")}
                wb = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"wapp_{req_id}", "style": "success"}, {"text": "❌ REJECT", "callback_data": f"wrej_{req_id}", "style": "danger"}]]}
                admin_msg = f"🎙 <b>NEW WITHDRAWAL (Mini App)</b>\n\n👤 <a href='tg://user?id={chat_id}'>{u.get('first_name','User')}</a>\n💳 {amount} TK | {method}\n🍏 <tg-spoiler>{number}</tg-spoiler>\n🧾 <code>{req_id}</code>"
                for adm in bot_settings.get("admins", [OWNER_ID]):
                    try: send_message(adm, admin_msg, reply_markup=wb)
                    except: pass
                send_message(chat_id, f"✅ Withdrawal submitted!\n🧾 ID: {req_id}\n💰 ৳{amount}")

    except Exception as e:
        print(f"[WEBAPP] Error: {e}")

def main_menu(user_id):
    kb = [
        [
            {"text": "GET NUMBER", "icon_custom_emoji_id": "5406809207947142040", "style": "primary"},
            {"text": "2FA ONLINE", "icon_custom_emoji_id": "5267421176841398765", "style": "success"}
        ],
        [
            {"text": "Refer", "icon_custom_emoji_id": "5372926953978341366", "style": "danger"},
            {"text": "WITHDRAWAL", "icon_custom_emoji_id": "5352585194295564660", "style": "danger"}
        ],
        [
            {"text": "SUPPORT", "icon_custom_emoji_id": "5420145051336485498", "style": "primary"}
        ]
    ]
    if is_admin(user_id):
        kb.append([{"text": "Admin Panel", "icon_custom_emoji_id": "6068714447659080664", "style": "danger"}])
    return {"keyboard": kb, "resize_keyboard": True}

def main_menu_inline(user_id):
    """Inline keyboard with Mini App open button (if URL set)."""
    btns = []
    if WEB_APP_URL:
        btns.append([{"text": "🚀 Open EXE NEXT App", "web_app": {"url": WEB_APP_URL}}])
    return {"inline_keyboard": btns} if btns else None

def get_admin_text():
    users_count = len(all_known_users) # 🌟 Zero Cost User Count!
    total_files = len(number_batches)
    available_nums = sum(len(b["numbers"]) for b in number_batches.values())

    txt = f"""
{PEM['admin']} <b>ADMIN CONTROL PANEL</b> {PEM['admin']}
━━━━━━━━━━━━━━━━━━

{PEM['graph']} <b>DATABASE OVERVIEW</b>
— — — — — — — — — —
{PEM['user']} Users      » {users_count}
{PEM['file']} Files      » {total_files}
{PEM['num']} Numbers    » {total_uploaded_stats}
{PEM['ok']} Assigned   » {total_assigned_stats}
{PEM['rocket']} Available  » {available_nums}

{PEM['graph']} <b>STOCK LEVEL</b>
— — — — — — — — — —
[██████░░░░░░░░░] {available_nums} free
"""
    return render_body_text(txt)

def admin_panel_keyboard():
    return {"inline_keyboard": [
        [{"text": "📊 Live Dashboard", "icon_custom_emoji_id": "5352877703043258544", "callback_data": "live_dashboard", "style": "success"},
         {"text": "🌡 Activity Heatmap", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "activity_heatmap", "style": "primary"}],
        [{"text": "LEADER BOARD SYSTEM", "icon_custom_emoji_id": "5353032893096567467", "callback_data": "lb_main", "style": "success"}],
        [{"text": "⬆️ Upload Number", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "upload_num", "style": "primary"},
         {"text": "🗑 Delete files", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "delete_files", "style": "danger"}],
        [{"text": "Broadcast", "icon_custom_emoji_id": "5789428375261023681", "callback_data": "broadcast_msg", "style": "success"},
         {"text": "System", "icon_custom_emoji_id": "5420155432272438703", "callback_data": "system_settings", "style": "primary"}],
        [{"text": "Used number", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "show_used", "style": "success"},
         {"text": "Unused number", "icon_custom_emoji_id": "5352597830089347330", "callback_data": "show_unused", "style": "success"}],
        [{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]
    ]}

def system_settings_keyboard():
    return {"inline_keyboard": [
        [{"text": "Nexa Control", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "nexa_control", "style": "success"},
         {"text": "Voltx Control", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "voltx_control", "style": "primary"}],
        [{"text": "Stex Control", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "stex_control", "style": "danger"}],
        [{"text": "Force Join System", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "manage_fj", "style": "primary"},
         {"text": "Admin Management", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "manage_admins", "style": "danger"}],
        [{"text": "OTP Group", "icon_custom_emoji_id": "5190447043545438788", "callback_data": "manage_otp_groups", "style": "danger"},
         {"text": "User Management", "icon_custom_emoji_id": "5193063022226086560", "callback_data": "user_management", "style": "primary"}], 
        [{"text": "Panel MANAGEMENT", "icon_custom_emoji_id": "5336879280578138635", "callback_data": "manage_panels", "style": "danger"},
         {"text": "Subscription", "icon_custom_emoji_id": "5190899075968441286", "callback_data": "dummy_alert", "style": "success"}],
        [{"text": "PRIME Control", "icon_custom_emoji_id": "5193100774988617665", "callback_data": "prime_control", "style": "primary"},
         {"text": "Premium Emoji", "icon_custom_emoji_id": "5352552689983067014", "callback_data": "manage_emojis", "style": "success"}],
        [{"text": "📊 Live Stats", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "admin_live_stats", "style": "success"},
         {"text": "🏆 Leaderboard", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "admin_leaderboard", "style": "primary"}],
        [{"text": "🔍 User Search", "icon_custom_emoji_id": "5193063022226086560", "callback_data": "admin_user_search", "style": "success"},
         {"text": "📋 Error Log", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "admin_error_log", "style": "danger"}],
        [{"text": "📱 Visible Services", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "manage_visible_services", "style": "primary"},
         {"text": "💰 Service Rewards", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "manage_service_rewards", "style": "success"}],
        [{"text": "Menu Design", "icon_custom_emoji_id": "5190751148704833975", "callback_data": "menu_design_list", "style": "primary"},
         {"text": "Test", "icon_custom_emoji_id": "5190781475468915802", "callback_data": "test_message_flow", "style": "primary"}], 
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
    ]}

def get_user_management_text():
    # 🌟 Fast & Free User Management Stats!
    total = len(all_known_users)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"""➖➖➖➖➖➖➖➖
《 👋 USER VIEW 》
➖➖➖➖➖➖➖➖
📊 LIVE STATISTICS:
➖➖➖➖➖➖➖➖
🫂 TOTAL USERS: {total}
✅ VERIFIED USERS: (Hidden to save DB Cost)
🚫 BANNED USERS: (Hidden to save DB Cost)
➖➖➖➖➖➖➖➖
⌛ UPDATED: {now_str}"""
    return render_body_text(txt)

def user_management_keyboard():
    return {"inline_keyboard": [
        [{"text": "Manage Balance", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "um_manage_balance", "style": "primary"},
         {"text": "Ban/Unban User", "icon_custom_emoji_id": "5334807341109908955", "callback_data": "um_ban_unban", "style": "danger"}],
        [{"text": "User Profile", "icon_custom_emoji_id": "5352861489541714456", "callback_data": "um_user_profile", "style": "success"}],
        [{"text": "💰 Balance Overview (All)", "icon_custom_emoji_id": "6233077820965264756", "callback_data": "um_balance_overview", "style": "success"}],
        [{"text": "👥 All Users List", "icon_custom_emoji_id": "5193063022226086560", "callback_data": "au_page_0", "style": "primary"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def get_balance_overview_text():
    """🌟 Zero-Read summary: pulled entirely from the incrementally-updated global aggregates."""
    pool = bot_settings.get("global_balance_pool", 0.0)
    earned = bot_settings.get("global_total_earned", 0.0)
    otps = bot_settings.get("global_total_otps", 0)
    users = len(all_known_users)
    avg_bal = (pool / users) if users else 0.0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"""➖➖➖➖➖➖➖➖
《 {PEM['money']} BALANCE OVERVIEW 》
➖➖➖➖➖➖➖➖
{PEM['user']} Total Users: <b>{users}</b>
{PEM['money']} Current Balance Pool (Withdrawable Now): <b>{pool:.2f} ৳</b>
{PEM['gift']} Lifetime Total Rewards Paid: <b>{earned:.2f} ৳</b>
{PEM['msg']} Lifetime Total OTPs Delivered: <b>{otps}</b>
{PEM['graph']} Avg. Balance / User: <b>{avg_bal:.2f} ৳</b>
➖➖➖➖➖➖➖➖
⌛ UPDATED: {now_str}"""
    return render_body_text(txt)

def build_all_users_list_ui(page=0):
    """🌟 Paginates over the free local all_known_users set, then batch-fetches just that
    page's user docs from Firestore — full per-user detail with minimal read cost."""
    PAGE_SIZE = 8
    sorted_uids = sorted(all_known_users, key=lambda x: int(x) if x.isdigit() else 0)
    total = len(sorted_uids)
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = max(0, min(page, total_pages - 1))
    page_uids = sorted_uids[page * PAGE_SIZE: page * PAGE_SIZE + PAGE_SIZE]

    rows_txt = ""
    if not page_uids:
        rows_txt = "<i>No users found.</i>\n"
    elif db:
        try:
            refs = [db.collection('users').document(uid) for uid in page_uids]
            docs = db.get_all(refs)
            for doc in docs:
                uid = doc.id
                d = doc.to_dict() if doc.exists else {}
                rows_txt += (
                    f"┌ {PEM['user']} <a href='tg://user?id={uid}'>{uid}</a>\n"
                    f"├ Total OTP: <b>{d.get('total_otps', 0)}</b> | Today: <b>{d.get('today_otps', 0)}</b>\n"
                    f"└ Total Reward: <b>{d.get('total_earned', 0.0):.2f}৳</b> | Current: <b>{d.get('balance', 0.0):.2f}৳</b>\n"
                    f"➖➖➖➖➖➖➖➖\n"
                )
        except Exception as e:
            rows_txt = f"<i>Error loading users: {html.escape(str(e))}</i>\n"
    else:
        rows_txt = "<i>Database not connected.</i>\n"

    txt = (f"➖➖➖➖➖➖➖➖\n《 👥 <b>ALL USERS</b> 》\n➖➖➖➖➖➖➖➖\n"
           f"Total Users: <b>{total}</b> | Page {page+1}/{total_pages}\n"
           f"➖➖➖➖➖➖➖➖\n{rows_txt}")
    txt = render_body_text(txt)

    kb = []
    nav = []
    if page > 0:
        nav.append({"text": "◀ Prev", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"au_page_{page-1}", "style": "primary"})
    if page < total_pages - 1:
        nav.append({"text": "Next ▶", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"au_page_{page+1}", "style": "primary"})
    if nav: kb.append(nav)
    kb.append([{"text": "Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": f"au_page_{page}", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "user_management", "style": "danger"}])

    return txt, {"inline_keyboard": kb}

def menu_design_list_keyboard():
    return {"inline_keyboard": [
        [{"text": "Edit /start Menu", "icon_custom_emoji_id": "5395444784611480792", "callback_data": "md_edit_start", "style": "primary"}],
        [{"text": "Edit GET NUMBER", "icon_custom_emoji_id": "5406809207947142040", "callback_data": "md_edit_get_number", "style": "success"},
        
        {"text": "Edit Select Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "md_edit_select_country", "style": "primary"}],
        
         [{"text": "Edit Refer", "icon_custom_emoji_id": "5372926953978341366", "callback_data": "md_edit_refer", "style": "primary"}],
        [{"text": "Edit WITHDRAWAL", "icon_custom_emoji_id": "5352585194295564660", "callback_data": "md_edit_withdrawal", "style": "danger"},
         {"text": "Edit SUPPORT", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "md_edit_support", "style": "danger"}],
        [{"text": "Reset Defaults", "icon_custom_emoji_id": "5192812028632274956", "callback_data": "md_reset_defaults", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def menu_edit_options_keyboard(menu_key):
    return {"inline_keyboard": [
        [{"text": "Edit Body (Text)", "icon_custom_emoji_id": "5395444784611480792", "callback_data": f"md_text_{menu_key}", "style": "primary"}],
        [{"text": "Edit Inline Buttons", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"md_btns_{menu_key}", "style": "success"}],
        [{"text": "Back to Menus", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "menu_design_list", "style": "danger"}]
    ]}

def menu_buttons_list_keyboard(menu_key):
    kb = []
    btns = bot_settings["custom_messages"].get(menu_key, {}).get("buttons", [])
    for idx, btn in enumerate(btns):
        kb.append([{"text": f"Del: {btn['text']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"md_delbtn_{menu_key}_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Inline Button", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"md_addbtn_{menu_key}", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_edit_{menu_key}", "style": "primary"}])
    return {"inline_keyboard": kb}

def emoji_settings_keyboard():
    flag_count = len(bot_settings.get("premium_flags", {}))
    app_count  = len(bot_settings.get("premium_apps", {}))
    return {"inline_keyboard": [
        [{"text": f"⬆️ Upload Flags TXT ({flag_count} loaded)", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "up_flags_txt", "style": "primary"},
         {"text": "⬇️ Download Flags", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_flags_txt", "style": "success"}],
        [{"text": f"⬆️ Upload Services TXT ({app_count} loaded)", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "up_apps_txt", "style": "primary"},
         {"text": "⬇️ Download Services", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_apps_txt", "style": "success"}],
        [{"text": "🗑 Delete All Flags", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "del_all_flags", "style": "danger"},
         {"text": "🗑 Delete All Services", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "del_all_apps", "style": "danger"}],
        [{"text": "➕ Add Single Emoji", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_single_emoji", "style": "success"}],
        [{"text": "◀️ Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
    ]}

def fj_settings_keyboard():
    status_text = 'ON' if bot_settings['fj_on'] else 'OFF'
    status_icon = "5352694861990501856" if bot_settings['fj_on'] else "5318840353510408444"
    kb = [[{"text": f"STATUS: {status_text}", "icon_custom_emoji_id": status_icon, "callback_data": "toggle_fj", "style": "primary"}]]
    for idx, ch in enumerate(bot_settings["fj_channels"]):
        kb.append([{"text": f"Delete: {ch}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_fj_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Channel", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_fj", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
    return {"inline_keyboard": kb}

def admin_settings_keyboard():
    kb = []
    for idx, adm in enumerate(bot_settings["admins"]):
        text_btn = f"Owner: {adm}" if adm == OWNER_ID else f"Delete: {adm}"
        icon_id = "5353032893096567467" if adm == OWNER_ID else "5420130255174145507"
        cb_data = "ignore" if adm == OWNER_ID else f"del_adm_{idx}"
        kb.append([{"text": text_btn, "icon_custom_emoji_id": icon_id, "callback_data": cb_data, "style": "danger" if adm != OWNER_ID else "primary"}])
    kb.append([{"text": "Add Admin", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_adm", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
    return {"inline_keyboard": kb}

def otp_groups_list_keyboard():
    kb = [[{"text": "Edit OTP Button Link", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "edit_otp_link", "style": "primary"}]]
    for idx, fg in enumerate(bot_settings["fw_groups"]):
        kb.append([{"text": f"Group: {fg['chat_id']}", "icon_custom_emoji_id": "5193063022226086560", "callback_data": f"manage_fw_{idx}", "style": "primary"}])
    kb.append([{"text": "Add Forward Group", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_fw", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}])
    return {"inline_keyboard": kb}

def nexa_control_keyboard():
    return {"inline_keyboard": [
        [{"text": "Add Nexa Key", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_nexa_key", "style": "success"},
         {"text": "View/Del Keys", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "view_nexa_keys", "style": "danger"}],
        [{"text": "Manage Nexa Services", "icon_custom_emoji_id": "5192739271886282680", "callback_data": "manage_nexa_srv", "style": "success"}],
        [{"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "nexa_search_country", "style": "primary"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def stex_control_keyboard():
    return {"inline_keyboard": [
        [{"text": "Add Stex Key", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_stex_key", "style": "success"},
         {"text": "View/Del Keys", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "view_stex_keys", "style": "danger"}],
        [{"text": "Manage Stex Services", "icon_custom_emoji_id": "5192739271886282680", "callback_data": "manage_stex_srv", "style": "success"}],
        [{"text": "📡 Live Ranges", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "stex_live_ranges", "style": "primary"},
         {"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "stex_search_country", "style": "primary"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}


def voltx_control_keyboard():
    return {"inline_keyboard": [
        [{"text": "Add Voltx Key", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_voltx_key", "style": "success"},
         {"text": "View/Del Keys", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "view_voltx_keys", "style": "danger"}],
        [{"text": "Manage Voltx Services", "icon_custom_emoji_id": "5192739271886282680", "callback_data": "manage_voltx_srv", "style": "success"}],
        [{"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "voltx_search_country", "style": "primary"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def specific_fw_group_keyboard(idx):
    group = bot_settings["fw_groups"][idx]
    kb = []
    for b_idx, btn in enumerate(group.get("buttons", [])):
        kb.append([{"text": f"Del: {btn['text']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_fwbtn_{idx}_{b_idx}", "style": "danger"}])
    
    kb.append([{"text": "🧪 Test Group", "icon_custom_emoji_id": "5190781475468915802", "callback_data": f"test_fw_{idx}", "style": "success"}])
    kb.append([{"text": "Add Inline Button", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"add_fwbtn_{idx}", "style": "success"}])
    kb.append([{"text": "Delete Entire Group", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"del_fw_{idx}", "style": "danger"}])
    kb.append([{"text": "Back to Groups", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "primary"}])
    return {"inline_keyboard": kb}

def prime_control_keyboard():
    w_status = "ON" if bot_settings["withdraw_on"] else "OFF"
    sup_status = "ON" if bot_settings.get("support_link") else "OFF"
    grp_status = "ON" if bot_settings.get("w_group") else "OFF"
    auto_status = "ON" if bot_settings.get("auto_traffic_on", True) else "OFF"
    return {"inline_keyboard": [
        [{"text": f"WITHDRAW: {w_status}", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "prime_toggle_w", "style": "primary"}],
        [{"text": f"MIN WITHDRAW: {bot_settings['min_withdraw']}", "icon_custom_emoji_id": "5352877703043258544", "callback_data": "prime_min_w", "style": "success"},
         {"text": f"OTP REWARD: {bot_settings['otp_reward']}", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "prime_otp_r", "style": "primary"}],
        [{"text": f"REFER REWARD: {bot_settings['refer_reward']}", "icon_custom_emoji_id": "5372926953978341366", "callback_data": "prime_ref_r", "style": "success"},
         {"text": f"COOLDOWN: {bot_settings['cooldown']}s", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "prime_cool", "style": "primary"}],
        [{"text": f"NUM/REQ: {bot_settings['num_req']}", "icon_custom_emoji_id": "5337132498965010628", "callback_data": "prime_num_req", "style": "success"},
         {"text": f"NUM/SHARE: {bot_settings['num_share']}", "icon_custom_emoji_id": "5352862640592949843", "callback_data": "prime_num_share", "style": "primary"}],
        [{"text": f"🤝 REF COMMISSION: {bot_settings.get('referral_commission', 0)}%", "icon_custom_emoji_id": "6233077820965264756", "callback_data": "prime_ref_comm", "style": "success"}],
        [{"text": f"📊 AUTO TRAFFIC: {auto_status}", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "prime_toggle_auto", "style": "primary"},
         {"text": f"INTERVAL: {bot_settings.get('auto_traffic_interval', 20)}min", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "prime_auto_int", "style": "success"}],
        [{"text": f"⏰ NUM EXPIRY: {bot_settings.get('number_expiry_minutes', 10)}min", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "prime_num_expiry", "style": "primary"},
         {"text": f"🎓 ONBOARDING: {'ON' if bot_settings.get('onboarding_on', True) else 'OFF'}", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "prime_toggle_onboard", "style": "success"}],
        [{"text": f"SUPPORT LINK: {sup_status}", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "prime_sup_link", "style": "success"},
         {"text": "W. METHODS", "icon_custom_emoji_id": "5190899075968441286", "callback_data": "manage_w_methods", "style": "primary"}],
        [{"text": f"W. GROUP: {grp_status}", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "prime_w_group", "style": "success"},
         {"text": f"💰 SERVICE REWARDS ({len(bot_settings.get('service_rewards', {}))})", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "manage_service_rewards", "style": "primary"}],
        [{"text": "BACK", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
    ]}

def w_methods_keyboard():
    kb = []
    for idx, m in enumerate(bot_settings["w_methods"]):
        kb.append([{"text": f"Delete: {m}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_wm_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Method", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_wm", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "prime_control", "style": "primary"}])
    return {"inline_keyboard": kb}

def typed_panels_list_keyboard(p_type):
    kb = []
    for idx, p in enumerate(bot_settings["panels"]):
        if p.get("type", "API Panel") != p_type: continue
        action_text = f"Turn OFF {p['name']}" if p['status'] == 'ON' else f"Turn ON {p['name']}"
        action_icon = "5318840353510408444" if p['status'] == 'ON' else "5192812028632274956"
        icon_id = "5420155432272438703" 
        kb.append([
            {"text": action_text, "icon_custom_emoji_id": action_icon, "callback_data": f"tog_pnl_{idx}", "style": "danger" if p['status'] == 'ON' else "success"},
            {"text": f"{p['name']}", "icon_custom_emoji_id": icon_id, "callback_data": f"conf_pnl_{idx}", "style": "primary"}
        ])
    add_cb = "add_api_panel" if p_type == "API Panel" else "add_cpt_panel"
    kb.append([{"text": "Add New Provider", "icon_custom_emoji_id": "5420323438508155202", "callback_data": add_cb, "style": "success"}])
    kb.append([{"text": "Delete Provider", "icon_custom_emoji_id": "5336944168944047463", "callback_data": f"list_del_{'api' if p_type=='API Panel' else 'cpt'}", "style": "danger"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_panels", "style": "primary"}])
    return {"inline_keyboard": kb}

def panel_config_keyboard(idx):
    p = bot_settings["panels"][idx]
    
    kb = []
    action_text = "Turn OFF" if p['status'] == 'ON' else "Turn ON"
    action_icon = "5318840353510408444" if p['status'] == 'ON' else "5192812028632274956"
    kb.append([{"text": action_text, "icon_custom_emoji_id": action_icon, "callback_data": f"tog_pnl_{idx}", "style": "danger" if p['status'] == 'ON' else "success"}])
    
    if p["type"] != "Auto Captcha Panel":
        rec_count_text = "All (Unlimited)" if p.get('records', 0) == 0 else str(p.get('records'))
        kb.append([{"text": "Set API URL", "icon_custom_emoji_id": "5420517437885943844", "callback_data": f"set_p_api_{idx}", "style": "primary"}])
        kb.append([{"text": "Set Token", "icon_custom_emoji_id": "5353022963132174959", "callback_data": f"set_p_tok_{idx}", "style": "primary"}])
        kb.append([{"text": "🌐 Full API (URL+Token)", "icon_custom_emoji_id": "5420517437885943844", "callback_data": f"set_p_fapi_{idx}", "style": "primary"}])
        kb.append([{"text": f"Set Records Count: {rec_count_text}", "icon_custom_emoji_id": "5192739271886282680", "callback_data": f"set_p_rec_{idx}", "style": "primary"}])
        
    kb.append([{"text": "Test Connection", "icon_custom_emoji_id": "5352694861990501856", "callback_data": f"test_p_conn_{idx}", "style": "success"}])
        
    back_data = "manage_api_panels" if p.get("type", "API Panel") == "API Panel" else "manage_cpt_panels"
    kb.append([{"text": "Back to Providers", "icon_custom_emoji_id": "5267490665117275176", "callback_data": back_data, "style": "danger"}])
    return {"inline_keyboard": kb}

def get_number_range(num):
    """🌟 Resolves a phone number to its configured prefix/range (e.g. for Nexa services),
    falling back to the first 7 digits. Shared by the range-explorer and traffic-analysis screens."""
    num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
    known_ranges = set()
    for s_name, c_dict in bot_settings.get("nexa_services", {}).items():
        for c_name, r_list in c_dict.items():
            for r in r_list:
                known_ranges.add(r)
    for r in sorted(known_ranges, key=len, reverse=True):
        if num.startswith(r):
            return r
    return num[:7] if len(num) >= 7 else num

def build_traffic_ui():
    global recent_traffic
    current_time = time.time()
    recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
    
    stats = {}
    for t in recent_traffic:
        srv = t.get("service", "Unknown")
        iso = t.get("iso", "XX")
        flag = t.get("flag", "🌍")
        
        if srv not in stats:
            stats[srv] = {}
        if iso not in stats[srv]:
            stats[srv][iso] = {"count": 0, "flag": flag}
        stats[srv][iso]["count"] += 1
        
    txt = "╔═════════════════╗\n║  📈 <b>NETWORK TRAFFIC</b>\n╚═════════════════╝\n\n"
    
    kb = []
    if not stats:
        txt += "<i>No recent traffic found in the last hour...</i>\n"
    else:
        srv_totals = []
        for srv, countries in stats.items():
            total = sum(c["count"] for c in countries.values())
            srv_totals.append((srv, total, countries))
        
        srv_totals.sort(key=lambda x: x[1], reverse=True)
        
        for srv, total, countries in srv_totals:
            app_full_name, prem_app_html = get_service_info_html(srv)
            txt += f"[ {prem_app_html} <b>{app_full_name}</b> ]\n│\n"
            
            c_list = sorted(countries.items(), key=lambda x: x[1]["count"], reverse=True)
            c_list = c_list[:7] 
            
            for i, (iso, c_data) in enumerate(c_list):
                prem_flag_html = get_flag_info_html(iso)
                count = c_data["count"]
                
                c_name = iso
                for code, fdata in bot_settings.get("premium_flags", {}).items():
                    if fdata.get("iso") == iso:
                        c_name = fdata.get("name", iso)
                        break
                        
                txt += f"├ {prem_flag_html} <b>{c_name} ({iso})</b>\n"
                txt += f"│ ╰ Success: {count}\n"
                if i < len(c_list) - 1:
                    txt += "│\n"
            txt += "\n"
        
        # 🌟 FIX: [:3] লিমিট তুলে দেওয়া হলো, এখন যতো সার্ভিস থাকবে সবগুলোর বাটন নিচে শো করবে!
        for srv, _, _ in srv_totals: 
            safe_srv = srv[:20] 
            # বাটনে সুন্দরভাবে ফুল নাম দেখানোর জন্য
            app_full_name, _ = get_service_info_html(safe_srv, safe_srv)
            kb.append([{"text": f"Explore {app_full_name} Range", "icon_custom_emoji_id": "5190645917711114179", "callback_data": f"exp_rng_{safe_srv}", "style": "success"}])
            
    txt = render_body_text(txt)
    kb.append([{"text": "📊 Panel vs Group Analysis", "icon_custom_emoji_id": "5352877703043258544", "callback_data": "pg_traffic_0", "style": "success"}])
    kb.append([{"text": "Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "refresh_traffic", "style": "primary"}])
    kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
    
    return txt, {"inline_keyboard": kb}

def build_panel_group_traffic_ui(page=0):
    """🌟 Compares raw panel volume (every OTP item the panel returns, incl. duplicates) against
    actual group traffic (unique OTPs successfully forwarded), broken down by number range, so it's
    clear which ranges deliver the most genuine, non-duplicate traffic."""
    global recent_traffic, panel_otp_log
    current_time = time.time()
    recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
    panel_otp_log = [t for t in panel_otp_log if current_time - t.get("time", 0) <= 3600]

    panel_total = len(panel_otp_log)
    group_total = len(recent_traffic)
    dupe_total = max(panel_total - group_total, 0)
    delivery_rate = (group_total / panel_total * 100) if panel_total else 0.0

    panel_by_range = Counter(get_number_range(t.get("number", "")) for t in panel_otp_log if t.get("number"))
    group_by_range = Counter(get_number_range(t.get("number", "")) for t in recent_traffic if t.get("number"))

    all_ranges = set(panel_by_range) | set(group_by_range)
    rows = []
    for r in all_ranges:
        p_cnt = panel_by_range.get(r, 0)
        g_cnt = group_by_range.get(r, 0)
        rate = (g_cnt / p_cnt * 100) if p_cnt else (100.0 if g_cnt else 0.0)
        rows.append((r, p_cnt, g_cnt, rate))

    # 🌟 "Good traffic" = high actual delivered volume (g_cnt), tie-broken by delivery rate
    rows.sort(key=lambda x: (x[2], x[3]), reverse=True)

    PAGE_SIZE = 10
    total_rows = len(rows)
    total_pages = max((total_rows + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * PAGE_SIZE: page * PAGE_SIZE + PAGE_SIZE]

    txt = (f"╔═══════════════════╗\n║ 📊 <b>PANEL vs GROUP TRAFFIC</b>\n╚═══════════════════╝\n\n"
           f"{PEM['rocket']} Panel OTP (raw, incl. duplicates): <b>{panel_total}</b>\n"
           f"{PEM['ok']} Group OTP (unique, forwarded): <b>{group_total}</b>\n"
           f"{PEM['warn']} Duplicate/Dropped: <b>{dupe_total}</b>\n"
           f"{PEM['graph']} Overall Delivery Rate: <b>{delivery_rate:.1f}%</b>\n"
           f"━━━━━━━━━━━━━━━\n")

    if not rows:
        txt += "<i>No traffic recorded in the last hour...</i>\n"
    else:
        txt += "<b>RANGE BREAKDOWN (best traffic first)</b>\n"
        for i, (r, p_cnt, g_cnt, rate) in enumerate(page_rows):
            tag = " 🏆" if (page == 0 and i == 0 and g_cnt > 0) else ""
            txt += f"├ <code>{r}</code>{tag}\n│ ╰ Panel: {p_cnt} → Group: {g_cnt} ({rate:.0f}%)\n"
        txt += f"━━━━━━━━━━━━━━━\nPage {page+1}/{total_pages}\n"

    txt = render_body_text(txt)

    kb = []
    nav = []
    if page > 0:
        nav.append({"text": "◀ Prev", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"pg_traffic_{page-1}", "style": "primary"})
    if page < total_pages - 1:
        nav.append({"text": "Next ▶", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"pg_traffic_{page+1}", "style": "primary"})
    if nav: kb.append(nav)
    kb.append([{"text": "Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": f"pg_traffic_{page}", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "refresh_traffic", "style": "danger"}])

    return txt, {"inline_keyboard": kb}

# ==========================================
# Message Handler
# ==========================================
def handle_message(msg):
    global total_uploaded_stats
    chat_id = msg["chat"]["id"]
    chat_type = msg["chat"].get("type", "private")
    
    if chat_type != "private":
        return
        
    text = msg.get("text", "")
    register_user_local(chat_id) # 🌟 Save User locally for Free Broadcasts!

    # 🌟 Handle Mini App data
    web_app_data = msg.get("web_app_data", {}).get("data", "")
    if web_app_data:
        handle_webapp_data(chat_id, web_app_data)
        return

    if is_user_banned(chat_id):
        send_message(chat_id, render_body_text("🚫 <b>You are banned from using this bot!</b>\nIf you think this is a mistake, please contact support."))
        return
    
    # --- REFERRAL FIX: Save inviter BEFORE Force Join ---
    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            inviter = int(parts[1])
            if inviter != chat_id:
                if db:
                    doc = db.collection('users').document(str(chat_id)).get()
                    existing = doc.to_dict() if doc.exists else {}
                    # Set refer only once — if not already referred by anyone
                    if not existing.get("referred_by"):
                        get_user(chat_id)
                        db.collection('users').document(str(chat_id)).update({"referred_by": inviter, "ref_paid": False})
                        
    if not check_force_join(chat_id):
        send_force_join_msg(chat_id)
        return
        
    MAIN_MENU_CMDS = ["GET NUMBER", "Refer", "WITHDRAWAL", "SUPPORT", "Admin Panel", "2FA ONLINE"]
    
    is_main_cmd = False
    if text in MAIN_MENU_CMDS or text.startswith("/start"):
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        is_main_cmd = True
    
    if chat_id in user_states and not is_main_cmd:
        state = user_states[chat_id]
        
        # 🌟 Auto Captcha Panel Setup Flow 
        if state == "wait_for_cpanel_url" and text:
            temp_data[chat_id]["p_data"]["login_url"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_user"
            send_message(chat_id, render_body_text("2️⃣ <b>Username</b>\n➡️ Panel এর Username দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_user" and text:
            temp_data[chat_id]["p_data"]["username"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_pass"
            send_message(chat_id, render_body_text("3️⃣ <b>Password</b>\n➡️ Panel এর Password দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_pass" and text:
            temp_data[chat_id]["p_data"]["password"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_msg_link"
            send_message(chat_id, render_body_text("4️⃣ <b>Message Link</b>\n➡️ যেখান থেকে SMS/OTP ডাটা (JSON) আসবে সেই Link দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_link" and text:
            temp_data[chat_id]["p_data"]["msg_link"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_num_col_name"
            send_message(chat_id, render_body_text("5️⃣ <b>Number Column Name</b>\n➡️ Data তে Number column এর নাম কী? (যেমন: number, phone):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_num_col_name" and text:
            temp_data[chat_id]["p_data"]["num_col_name"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_num_col_idx"
            send_message(chat_id, render_body_text("6️⃣ <b>Number Column Serial</b>\n➡️ Number Column এর Serial Number কত? (যেমন: 3, 5):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_num_col_idx" and text:
            if text.isdigit():
                temp_data[chat_id]["p_data"]["num_col_idx"] = int(text)
                user_states[chat_id] = "wait_for_cpanel_msg_col_name"
                send_message(chat_id, render_body_text("7️⃣ <b>Message Column Name</b>\n➡️ Message/OTP column এর নাম কী? (যেমন: message, sms):"), reply_markup=get_cancel_kb())
            else:
                 send_message(chat_id, render_body_text("❌ Please enter a valid number serial!"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_col_name" and text:
            temp_data[chat_id]["p_data"]["msg_col_name"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_msg_col_idx"
            send_message(chat_id, render_body_text("8️⃣ <b>Message Column Serial</b>\n➡️ Message Column এর Serial Number কত? (যেমন: 5, 7):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_col_idx" and text:
            if text.isdigit():
                temp_data[chat_id]["p_data"]["msg_col_idx"] = int(text)
                temp_data[chat_id]["p_data"]["login_status"] = "⏳ Pending Auto-Login..."
                
                # Save the panel configuration
                bot_settings["panels"].append(temp_data[chat_id]["p_data"])
                save_db()
                
                send_message(chat_id, render_body_text(f"{PEM['ok']} <b>Auto Captcha Panel Added Successfully!</b>\nবট এখন থেকে নিজেই ব্যাকগ্রাউন্ডে ক্যাপচা সলভ করে লগিন করে নিবে।"), reply_markup=main_menu(chat_id))
                
                msg_id = temp_data[chat_id]["msg_id"]
                handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_cpt_panels", "id": "internal"})
                
                del user_states[chat_id]
                del temp_data[chat_id]
            else:
                 send_message(chat_id, render_body_text("❌ Please enter a valid number serial!"), reply_markup=get_cancel_kb())
            return

        # --- User Management Flows ---
        elif state == "wait_for_um_bal_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID! Please send a numeric User ID."), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            if db:
                doc = db.collection('users').document(str(target_uid)).get()
                if not doc.exists:
                    send_message(chat_id, render_body_text("❌ User not found in database!"), reply_markup=get_cancel_kb())
                    return
                current_bal = doc.to_dict().get('balance', 0.0)
                temp_data[chat_id]["target_uid"] = target_uid
                user_states[chat_id] = "wait_for_um_bal_amt"
                send_message(chat_id, render_body_text(f"✅ User found!\n💰 Current Balance: {current_bal} ৳\n\n📝 Send the amount to ADD (e.g. 50) or REMOVE (e.g. -50):"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_um_bal_amt" and text:
            try:
                amt = float(text.strip())
                target_uid = temp_data[chat_id]["target_uid"]
                update_balance(target_uid, amt)
                send_message(chat_id, render_body_text(f"{PEM['ok']} Balance updated successfully for {target_uid}!"), reply_markup=main_menu(chat_id))
                send_message(target_uid, render_body_text(f"🔔 Your balance has been adjusted by <b>{amt} ৳</b> by an Admin."))
                del user_states[chat_id]
                del temp_data[chat_id]
            except ValueError:
                send_message(chat_id, render_body_text("❌ Invalid amount! Please send a number."), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_um_ban_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID!"), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            if db:
                doc_ref = db.collection('users').document(str(target_uid))
                doc = doc_ref.get()
                if not doc.exists:
                    send_message(chat_id, render_body_text("❌ User not found in database!"), reply_markup=get_cancel_kb())
                    return
                current_status = doc.to_dict().get("banned", False)
                new_status = not current_status
                doc_ref.update({"banned": new_status})
                
                user_banned_cache[target_uid] = {'banned': new_status, 'time': time.time()}
                
                status_text = "BANNED 🚫" if new_status else "UNBANNED ✅"
                send_message(chat_id, render_body_text(f"✅ User {target_uid} has been {status_text}!"), reply_markup=main_menu(chat_id))
                del user_states[chat_id]
                del temp_data[chat_id]
            return

        elif state == "wait_for_um_prof_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID!"), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            if db:
                doc = db.collection('users').document(str(target_uid)).get()
                if not doc.exists:
                    send_message(chat_id, render_body_text("❌ User not found in database!"), reply_markup=get_cancel_kb())
                    return
                data = doc.to_dict()
                is_verified = True if data.get('total_otps', 0) > 0 else data.get('verified', False)
                prof_text = f"""➖➖➖➖➖➖➖➖
👤 <b>USER PROFILE</b>
➖➖➖➖➖➖➖➖
🆔 ID: <code>{target_uid}</code>
💰 Current Balance: {data.get('balance', 0.0)} ৳
🎁 Total Rewards (Lifetime): {data.get('total_earned', 0.0)} ৳
🤝 Total Refers: {data.get('total_refers', 0)}
🔐 Total OTPs: {data.get('total_otps', 0)}
📅 Today's OTPs: {data.get('today_otps', 0)}
✅ Verified: {is_verified}
🚫 Banned: {data.get('banned', False)}
➖➖➖➖➖➖➖➖"""
                kb = {"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "user_management", "style": "primary"}]]}
                send_message(chat_id, render_body_text(prof_text), reply_markup=kb)
                del user_states[chat_id]
                del temp_data[chat_id]
            return

        # --- Menu Design Flow ---
        elif state == "wait_for_menu_text" and text:
            try:
                menu_key = temp_data[chat_id]["menu_key"]
                formatted_html_text = extract_premium_html(msg)
                
                bot_settings["custom_messages"][menu_key]["text"] = formatted_html_text
                save_db()
                
                delete_message(chat_id, msg["message_id"])
                
                preview_text = render_body_text(formatted_html_text)
                success_text = f"{PEM['ok']} <b>Message Body Updated successfully!</b>\n\n🎨 <b>Editing: {menu_key.upper()}</b>\n\nPreview of current Text:\n{preview_text}"
                edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(success_text), reply_markup=menu_edit_options_keyboard(menu_key))
            except Exception as e:
                send_message(chat_id, f"❌ Error saving text: {e}")
            finally:
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            return
            
        elif state == "wait_for_menu_btn" and text:
            try:
                menu_key = temp_data[chat_id]["menu_key"]
                if "-" in text:
                    parts = text.split("-", 1)
                    btn_text = parts[0].strip()
                    btn_url = parts[1].strip()
                    
                    emoji_id = None
                    emoji_char = ""
                    for ent in msg.get("entities", []):
                        if ent.get("type") == "custom_emoji":
                            emoji_id = ent.get("custom_emoji_id")
                            offset = ent.get("offset", 0)
                            length = ent.get("length", 0)
                            b_text = text.encode('utf-16-le')
                            emoji_char = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                            break
                            
                    if emoji_char:
                        btn_text = btn_text.replace(emoji_char, "").strip()
                        
                    btn_data = {"text": btn_text, "url": btn_url, "style": "primary"}
                    if emoji_id:
                        btn_data["icon_custom_emoji_id"] = emoji_id
                        
                    bot_settings["custom_messages"][menu_key]["buttons"].append(btn_data)
                    save_db()
                    delete_message(chat_id, msg["message_id"])
                    edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"{PEM['gear']} <b>Edit Inline Buttons: {menu_key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(menu_key))
                else:
                    send_message(chat_id, render_body_text(f"{PEM['no']} Invalid format. Use <code>Button Text - https://link.com</code>"))
            except Exception as e:
                 pass
            finally:
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            return

        elif state == "wait_for_test_service" and text:
            temp_data[chat_id]["service"] = text.strip()
            user_states[chat_id] = "wait_for_test_number"
            send_message(chat_id, render_body_text("📝 Send the Number (e.g. +8801712345678):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_number" and text:
            temp_data[chat_id]["number"] = text.strip()
            user_states[chat_id] = "wait_for_test_otp"
            send_message(chat_id, render_body_text("📝 Send the OTP (e.g. 556677):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_otp" and text:
            temp_data[chat_id]["otp"] = text.strip()
            user_states[chat_id] = "wait_for_test_lang"
            send_message(chat_id, render_body_text("📝 Send the Language (e.g. EN, AR):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_lang" and text:
            lang = text.strip().upper()
            if not lang.startswith("#"):
                lang = "#" + lang
                
            srv = temp_data[chat_id]["service"]
            num = temp_data[chat_id]["number"]
            otp = temp_data[chat_id]["otp"]
            
            masked = mask_number(num)
            prem_flag_html = get_flag_info_html(num)
            char, iso = get_flag_and_code(num)
            app_full_name, prem_app_html = get_service_info_html(srv)
            
            msg_text = render_body_text(f"╔═══════════════╗\n║ {prem_app_html} {prem_flag_html} {masked} {lang}\n╚═══════════════╝")
            
            for fw in bot_settings["fw_groups"]:
                kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                for btn in fw.get("buttons", []):
                    b_obj = {"text": btn["text"], "url": btn["url"], "style": "primary"}
                    if "icon_custom_emoji_id" in btn: b_obj["icon_custom_emoji_id"] = btn["icon_custom_emoji_id"]
                    kb.append([b_obj])
                send_message(fw["chat_id"], msg_text, reply_markup={"inline_keyboard": kb})
                
            send_message(chat_id, render_body_text(f"{PEM['ok']} Test message formatted and sent to all Forward Groups!"), reply_markup=main_menu(chat_id))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_emoji_extract":
            entities = msg.get("entities", [])
            custom_emoji_id = None
            emoji_text = ""
            for ent in entities:
                if ent.get("type") == "custom_emoji":
                    custom_emoji_id = ent.get("custom_emoji_id")
                    offset = ent.get("offset", 0)
                    length = ent.get("length", 0)
                    b_text = msg.get("text", "").encode('utf-16-le')
                    emoji_text = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                    break
            
            if custom_emoji_id:
                temp_data[chat_id] = {"id": custom_emoji_id, "char": emoji_text}
                user_states[chat_id] = "wait_for_emoji_details"
                send_message(chat_id, render_body_text(f"{PEM['ok']} Emoji ID পাওয়া গেছে: <code>{custom_emoji_id}</code>\n\n📌 এখন এটি সেভ করার জন্য টাইপ এবং নাম লিখুন।\n\n<b>ফরমেট:</b>\n`FLAG | 880 | BD | Bangladesh`\nঅথবা\n`APP | WhatsApp`"), reply_markup=get_cancel_kb())
            else:
                send_message(chat_id, render_body_text(f"{PEM['no']} কোনো Premium Emoji পাওয়া যায়নি! দয়া করে Custom Emoji সেন্ড করুন।"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_emoji_details" and text:
            parts = [p.strip() for p in text.split("|")]
            mode = parts[0].upper()
            eid = temp_data[chat_id]["id"]
            char = temp_data[chat_id]["char"]
            
            if mode == "FLAG" and len(parts) == 4:
                code, iso, name = parts[1], parts[2], parts[3]
                bot_settings["premium_flags"][code] = {"char": char, "iso": iso.upper(), "name": name, "id": eid}
                save_db()
                send_message(chat_id, render_body_text(f"{PEM['ok']} Flag Emoji সেভ হয়েছে!\nCode: {code} | Name: {name}"), reply_markup=emoji_settings_keyboard())
            elif mode == "APP" and len(parts) == 2:
                name = parts[1]
                bot_settings["premium_apps"][name.upper()] = {"char": char, "id": eid, "name": name.title()}
                save_db()
                send_message(chat_id, render_body_text(f"{PEM['ok']} App Emoji সেভ হয়েছে!\nName: {name}"), reply_markup=emoji_settings_keyboard())
            else:
                send_message(chat_id, render_body_text(f"{PEM['no']} ফরম্যাট ভুল!\n\nসঠিক ফরম্যাট:\n`FLAG | 880 | BD | Bangladesh`\n`APP | WhatsApp`"))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state in ["wait_for_flag_txt", "wait_for_app_txt"] and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text(f"{PEM['no']} Please upload a .txt file only."))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            content = requests.get(f"{FILE_URL}{file_path}").text

            mode = "flags" if state == "wait_for_flag_txt" else "apps"
            count = 0
            errors = 0

            if mode == "flags":
                # Format: (dialcode)(ISO)emoji Name {"emoji": "x", "id": "xxx"}
                for line in content.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    json_match = re.search(r'(\{[^{}]+\})', line)
                    if not json_match:
                        continue
                    try:
                        jdata = json.loads(json_match.group(1))
                        char = jdata.get("emoji", "").strip()
                        eid  = jdata.get("id", "").strip()
                        if not char or not eid:
                            errors += 1
                            continue
                        prefix_str = line[:json_match.start()].strip()
                        # Parse (dialcode) and (ISO) from prefix
                        codes = re.findall(r'\((\d+|\?)\)', prefix_str)
                        isos  = re.findall(r'\(([A-Z]{2})\)', prefix_str)
                        if not codes or not isos:
                            errors += 1
                            continue
                        code = codes[0]
                        if code == "?":
                            continue  # skip unknown dial codes
                        iso  = isos[0].upper()
                        # Extract name: remove (dialcode), (ISO), emoji char from prefix
                        name = re.sub(r'\(\d+\)', '', prefix_str)
                        name = re.sub(r'\([A-Z]{2}\)', '', name)
                        name = name.replace(char, '').strip()
                        if not name:
                            errors += 1
                            continue
                        bot_settings["premium_flags"][code] = {
                            "char": char, "iso": iso, "name": name, "id": eid
                        }
                        count += 1
                    except Exception:
                        errors += 1
                        continue
            else:
                # Format: emoji Name {"emoji": "x", "id": "xxx"}
                for line in content.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    json_match = re.search(r'(\{[^{}]+\})', line)
                    if not json_match:
                        continue
                    try:
                        jdata = json.loads(json_match.group(1))
                        char = jdata.get("emoji", "").strip()
                        eid  = jdata.get("id", "").strip()
                        if not char or not eid:
                            errors += 1
                            continue
                        name_part = line[:json_match.start()].strip()
                        # Remove emoji chars from start to get name
                        name = name_part
                        # Strip all leading non-ASCII or emoji characters
                        name = re.sub(r'^[\s\U00010000-\U0010FFFF\u2600-\u27BF\u2300-\u23FF\uFE00-\uFE0F]+', '', name).strip()
                        # Also try removing the char directly
                        for c in char:
                            name = name.replace(c, '').strip()
                        name = name.strip()
                        if not name:
                            errors += 1
                            continue
                        bot_settings["premium_apps"][name.upper()] = {
                            "char": char, "id": eid, "name": name
                        }
                        count += 1
                    except Exception:
                        errors += 1
                        continue

            save_db()
            result_msg = (
                f"{PEM['ok']} <b>Emoji Upload Complete!</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✅ Loaded: <b>{count}</b>\n"
                f"❌ Skipped: <b>{errors}</b>\n"
                f"📦 Type: <b>{'Flags' if mode == 'flags' else 'Services'}</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🕐 {bdt_str()}"
            )
            send_message(chat_id, render_body_text(result_msg), reply_markup=emoji_settings_keyboard())
            del user_states[chat_id]
            return

        elif state == "wait_for_broadcast":
            msg_id = msg["message_id"]
            send_message(chat_id, render_body_text(f"{PEM['ok']} Broadcast started..."))
            threading.Thread(target=broadcast_copymessage, args=(chat_id, msg_id)).start()
            del user_states[chat_id]
            return

        elif state == "wait_service_reward_name" and text:
            svc_name = text.strip().upper()
            temp_data[chat_id]["service_name"] = svc_name
            user_states[chat_id] = "wait_service_reward_amount"
            send_message(chat_id, render_body_text(
                f"💰 Enter reward amount for <b>{svc_name}</b> (e.g. 0.50):"
            ), reply_markup=get_cancel_kb())
            return

        elif state == "wait_service_reward_amount" and text:
            try:
                amount = float(text.strip())
                svc_name = temp_data[chat_id].get("service_name", "")
                if not bot_settings.get("service_rewards"):
                    bot_settings["service_rewards"] = {}
                bot_settings["service_rewards"][svc_name] = amount
                save_db()
                send_message(chat_id, render_body_text(
                    f"✅ <b>Reward Set!</b>\n"
                    f"📱 {svc_name}: <b>{amount:.2f} ৳</b> per OTP"
                ))
            except ValueError:
                send_message(chat_id, render_body_text(f"{PEM['no']} Invalid amount! Enter a number like 0.50"))
            del user_states[chat_id]
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_for_bulk_txt" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text(f"{PEM['no']} Please upload a .txt file only."))
                return
            # Parse SERVICE+COUNTRY from filename
            fname = doc["file_name"].replace(".txt", "")
            if "+" in fname:
                parts = fname.split("+", 1)
                auto_service = parts[0].upper().strip()
                auto_country = parts[1].upper().strip()
            else:
                auto_service = None
                auto_country = None

            file_id   = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_content = requests.get(f"{FILE_URL}{file_path}").text

            raw_lines = [l.strip() for l in file_content.splitlines() if l.strip()]
            # Max 50 numbers
            if len(raw_lines) > 50:
                raw_lines = raw_lines[:50]

            clean_nums = []
            for num in raw_lines:
                if not num.startswith("+"): num = "+" + num
                clean_nums.append(num)

            if not clean_nums:
                send_message(chat_id, render_body_text(f"{PEM['no']} No valid numbers found in file!"))
                del user_states[chat_id]
                return

            temp_data[chat_id] = {
                "numbers": clean_nums,
                "filename": doc["file_name"],
                "auto_service": auto_service,
                "auto_country": auto_country
            }

            if auto_service and auto_country:
                # Auto-detected from filename — confirm directly
                send_message(chat_id, render_body_text(
                    f"📦 <b>Bulk Upload Preview</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📲 Service: <b>{auto_service}</b>\n"
                    f"🌍 Country: <b>{auto_country}</b>\n"
                    f"📱 Numbers: <b>{len(clean_nums)}</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"Confirm upload?"
                ), reply_markup={"inline_keyboard": [
                    [{"text": "✅ Confirm", "callback_data": "bulk_confirm_auto", "style": "success"},
                     {"text": "❌ Cancel", "callback_data": "back_to_admin", "style": "danger"}]
                ]})
                user_states[chat_id] = "wait_bulk_confirm_auto"
            else:
                user_states[chat_id] = "wait_for_service"
                send_message(chat_id, render_body_text(
                    f"{PEM['ok']} <b>{len(clean_nums)} numbers</b> loaded.\n\n"
                    f"📌 Enter the service name (e.g., WHATSAPP):"
                ), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_user_search" and text:
            target_id = text.strip()
            if not target_id.lstrip("-").isdigit():
                send_message(chat_id, render_body_text(f"{PEM['no']} Invalid User ID. Please send numbers only."))
                return
            u = get_user(int(target_id))
            banned = u.get("banned", False)
            send_message(chat_id, build_user_profile_text(target_id),
                         reply_markup=user_manager_keyboard(target_id, banned))
            del user_states[chat_id]
            return

        elif state.startswith("wait_admin_add_bal_") and text:
            target_id = state.replace("wait_admin_add_bal_", "")
            try:
                amount = float(text.strip())
                update_balance(int(target_id), amount)
                send_message(chat_id, render_body_text(
                    f"✅ Added <b>{amount:.2f} ৳</b> to user <code>{target_id}</code>"
                ))
                u = get_user(int(target_id))
                send_message(chat_id, build_user_profile_text(target_id),
                             reply_markup=user_manager_keyboard(target_id, u.get("banned", False)))
            except ValueError:
                send_message(chat_id, render_body_text(f"{PEM['no']} Invalid amount. Please enter a number (e.g. 10.5)"))
            del user_states[chat_id]
            return

        elif state == "wait_for_txt" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text(f"{PEM['no']} Please upload a .txt file only."))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_content = requests.get(f"{FILE_URL}{file_path}").text
            
            temp_data[chat_id] = {"numbers": file_content.splitlines(), "filename": doc["file_name"]}
            user_states[chat_id] = "wait_for_service"
            send_message(chat_id, render_body_text(f"{PEM['ok']} File received.\n\n📌 Enter the service name (e.g., WHATSAPP):"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_service" and text:
            temp_data[chat_id]["service"] = text.upper()
            user_states[chat_id] = "wait_for_country"
            send_message(chat_id, render_body_text(f"{PEM['ok']} Service set.\n\n🌍 Enter the country name (e.g., YEMEN):"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_bulk_confirm_auto":
            # This is handled via callback — ignore text input
            pass

        elif state == "wait_for_country" and text:
            country = text.upper()
            service = temp_data[chat_id]["service"]
            raw_numbers = temp_data[chat_id]["numbers"]
            
            clean_nums = []
            for num in raw_numbers:
                num = num.strip()
                if num:
                    if not num.startswith('+'): num = '+' + num
                    clean_nums.append(num)
            
            batch_id = str(uuid.uuid4())[:8]
            number_batches[batch_id] = {"filename": temp_data[chat_id]["filename"], "service": service, "country": country, "numbers": [{"num": n, "shares": 0, "used_by": []} for n in clean_nums]}
            total_uploaded_stats += len(clean_nums)
            save_db()
            
            app_full_name, prem_app_html = get_service_info_html(service)
            prem_flag_html = get_flag_info_html(clean_nums[0]) if clean_nums else f"{PEM['world']} "
            
            broadcast_txt = f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n      《 𝗡𝗘𝗪 𝗡𝗨𝗠𝗕𝗘𝗥𝗦 𝗔𝗗𝗗𝗘𝗗 》\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n{prem_flag_html} {country} {prem_app_html} {service}\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n📤 Total Added: <b>{len(clean_nums)}</b>\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n𝗡𝗼𝘁𝗲 : 𝗧𝗿𝗮𝗳𝗳𝗶𝗰 𝗶𝘀 𝘃𝗲𝗿𝘆 𝗚𝗼𝗼𝗱 𝗦𝘁𝗮𝗿𝘁 𝗪𝗼𝗿𝗸 𝗡𝗼𝘄\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖\nUse /start to get your numbers!"
            broadcast_txt = render_body_text(broadcast_txt)
            
            send_message(chat_id, render_body_text(f"{PEM['ok']} Numbers added to local stock! Starting broadcast..."))
            
            def simple_broadcast(txt):
                b_session = requests.Session()
                url = f"{BASE_URL}/sendMessage"
                for u_id in list(all_known_users):
                    try:
                        b_session.post(url, json={"chat_id": u_id, "text": txt, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=5)
                    except: pass
                    time.sleep(0.035)
            threading.Thread(target=simple_broadcast, args=(broadcast_txt,)).start()
            
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_nexa_key" and text:
            bot_settings["nexa_keys"].append(text.strip())
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"✅ Nexa API Key Added! Total Keys: {len(bot_settings.get('nexa_keys', []))}"), reply_markup=nexa_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_voltx_key" and text:
            bot_settings["voltx_keys"].append(text.strip())
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"✅ Voltx API Key Added! Total Keys: {len(bot_settings.get('voltx_keys', []))}"), reply_markup=voltx_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_sc" and text:
            code = text.strip().replace("+", "")
            if "search_countries" not in bot_settings: bot_settings["search_countries"] = []
            bot_settings["search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            kb = []
            for idx, c in enumerate(bot_settings.get("search_countries", [])):
                kb.append([{"text": f"❌ Delete {c}", "callback_data": f"del_sc_{idx}", "style": "danger"}])
            kb.append([{"text": "➕ Add Country Code", "callback_data": "add_search_country", "style": "success"}])
            kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "nexa_control", "style": "primary"}])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🌍 <b>Allowed Search Countries:</b>\nOnly these country codes will be allowed in Search Number."), reply_markup={"inline_keyboard": kb})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_vsc" and text:
            code = text.strip().replace("+", "")
            if "voltx_search_countries" not in bot_settings: bot_settings["voltx_search_countries"] = []
            bot_settings["voltx_search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "voltx_search_country", "id": "internal"})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_nx_srv_name" and text:
            srv = text.strip().upper()
            if "nexa_services" not in bot_settings: bot_settings["nexa_services"] = {}
            if srv not in bot_settings["nexa_services"]: bot_settings["nexa_services"][srv] = {}
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "manage_nexa_srv", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_nx_cnt_name" and text:
            cnt = text.strip()
            srv = temp_data[chat_id]["srv"]
            if cnt not in bot_settings["nexa_services"][srv]: bot_settings["nexa_services"][srv][cnt] = []
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"nx_srv_{srv}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_nx_addr" and text:
            srv, cnt = temp_data[chat_id]["srv"], temp_data[chat_id]["cnt"]
            new_range = text.strip().replace("+", "")
            
            if new_range not in bot_settings["nexa_services"][srv][cnt]:
                bot_settings["nexa_services"][srv][cnt].append(new_range)
                
                if "search_countries" not in bot_settings:
                    bot_settings["search_countries"] = []
                if new_range not in bot_settings["search_countries"]:
                    bot_settings["search_countries"].append(new_range)
                    
                save_db()
                
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"nx_cnt_{srv}_{cnt}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_vx_srv_name" and text:
            srv = text.strip().upper()
            if "voltx_services" not in bot_settings: bot_settings["voltx_services"] = {}
            if srv not in bot_settings["voltx_services"]: bot_settings["voltx_services"][srv] = {}
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "manage_voltx_srv", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_vx_cnt_name" and text:
            cnt = text.strip()
            srv = temp_data[chat_id]["srv"]
            if cnt not in bot_settings["voltx_services"][srv]: bot_settings["voltx_services"][srv][cnt] = []
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"vx_srv_{srv}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_vx_addr" and text:
            srv, cnt = temp_data[chat_id]["srv"], temp_data[chat_id]["cnt"]
            new_range = text.strip().replace("+", "")
            
            if new_range not in bot_settings["voltx_services"][srv][cnt]:
                bot_settings["voltx_services"][srv][cnt].append(new_range)
                
                if "voltx_search_countries" not in bot_settings:
                    bot_settings["voltx_search_countries"] = []
                if new_range not in bot_settings["voltx_search_countries"]:
                    bot_settings["voltx_search_countries"].append(new_range)
                    
                save_db()
                
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"vx_cnt_{srv}_{cnt}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_for_add_stex_key" and text:
            bot_settings["stex_keys"].append(text.strip())
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"✅ Stex API Key Added! Total Keys: {len(bot_settings.get('stex_keys', []))}"), reply_markup=stex_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_ssc" and text:
            code = text.strip().replace("+", "")
            if "stex_search_countries" not in bot_settings: bot_settings["stex_search_countries"] = []
            bot_settings["stex_search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "stex_search_country", "id": "internal"})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_sx_srv_name" and text:
            srv = text.strip().upper()
            if "stex_services" not in bot_settings: bot_settings["stex_services"] = {}
            if srv not in bot_settings["stex_services"]: bot_settings["stex_services"][srv] = {}
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "manage_stex_srv", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_sx_cnt_name" and text:
            cnt = text.strip()
            srv = temp_data[chat_id]["srv"]
            if cnt not in bot_settings["stex_services"][srv]: bot_settings["stex_services"][srv][cnt] = []
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"sx_srv_{srv}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_sx_addr" and text:
            srv, cnt = temp_data[chat_id]["srv"], temp_data[chat_id]["cnt"]
            new_range = text.strip().replace("+", "")
            if new_range not in bot_settings["stex_services"][srv][cnt]:
                bot_settings["stex_services"][srv][cnt].append(new_range)
                if "stex_search_countries" not in bot_settings:
                    bot_settings["stex_search_countries"] = []
                if new_range not in bot_settings["stex_search_countries"]:
                    bot_settings["stex_search_countries"].append(new_range)
                save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"sx_cnt_{srv}_{cnt}", "id": "internal"})
            del user_states[chat_id]
            return


        elif state == "wait_for_add_wm" and text:
            bot_settings["w_methods"].append(text.strip())
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("💳 <b>WITHDRAWAL METHODS</b>\n\nManage your withdrawal methods below:"), reply_markup=w_methods_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fj" and text:
            bot_settings["fj_channels"].append(parse_chat_id(text))
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🔗 <b>FORCE JOIN SYSTEM</b>\nManage channels below:\n<i>(Note: For private links, use numeric IDs like -100...)</i>"), reply_markup=fj_settings_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_add_adm" and text:
            if text.isdigit():
                bot_settings["admins"].append(int(text))
                save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("👥 <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"), reply_markup=admin_settings_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fw_id" and text:
            bot_settings["fw_groups"].append({"chat_id": text.strip(), "buttons": []})
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_add_fw_btn" and text:
            fw_idx = temp_data[chat_id]["fw_idx"]
            if "-" in text:
                parts = text.split("-", 1)
                btn_text = parts[0].strip()
                btn_url = parts[1].strip()
                
                emoji_id = None
                emoji_char = ""
                for ent in msg.get("entities", []):
                    if ent.get("type") == "custom_emoji":
                        emoji_id = ent.get("custom_emoji_id")
                        offset = ent.get("offset", 0)
                        length = ent.get("length", 0)
                        b_text = text.encode('utf-16-le')
                        emoji_char = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                        break
                
                if emoji_char:
                    btn_text = btn_text.replace(emoji_char, "").strip()
                    
                btn_data = {"text": btn_text, "url": btn_url}
                if emoji_id:
                    btn_data["icon_custom_emoji_id"] = emoji_id
                    
                bot_settings["fw_groups"][fw_idx]["buttons"].append(btn_data)
                save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"🛡 <b>Manage Group:</b> {bot_settings['fw_groups'][fw_idx]['chat_id']}"), reply_markup=specific_fw_group_keyboard(fw_idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_otp_link" and text:
            bot_settings["otp_link"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_panel_name" and text:
            p_name = text.strip()
            t_key = temp_data[chat_id].get("add_type", "api")
            msg_id = temp_data[chat_id]["msg_id"]
            delete_message(chat_id, msg["message_id"])
            
            if t_key == "logc":
                user_states[chat_id] = "wait_for_cpanel_url"
                temp_data[chat_id] = {"msg_id": msg_id, "p_data": {
                    "name": p_name, "type": "Auto Captcha Panel", "status": "ON", "records": 0, "login_status": "⏳ Pending First Login"
                }}
                edit_message(chat_id, msg_id, render_body_text("1️⃣ <b>Login URL</b>\n➡️ Panel এর Login Link দিন:"), reply_markup=get_cancel_kb())
                return
            else:
                bot_settings["panels"].append({
                    "name": p_name, "type": "API Panel", "status": "OFF", "api_url": "", "token": "", "records": 0
                })
                save_db()
                handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_api_panels", "id": "internal"})
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
                return

        elif state == "wait_for_p_api" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["api_url"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_tok" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["token"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_fapi" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["full_api_url"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Full API URL:</b> <code>{p.get('full_api_url', 'None')}</code>"
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_rec" and text:
            if text.isdigit():
                idx = temp_data[chat_id]["p_idx"]
                bot_settings["panels"][idx]["records"] = int(text)
                save_db()
                delete_message(chat_id, msg["message_id"])
                p = bot_settings["panels"][idx]
                
                ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
                edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            else:
                send_message(chat_id, render_body_text("❌ Please enter a valid number! Try again."), reply_markup=get_cancel_kb())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "set_prime":
            msg_id = temp_data[chat_id]["msg_id"]
            key = temp_data[chat_id]["key"]
            try:
                if key in ["min_withdraw", "otp_reward", "refer_reward", "referral_commission"]: bot_settings[key] = float(text)
                elif key in ["cooldown", "num_req", "num_share", "auto_traffic_interval"]: bot_settings[key] = int(text)
                else: bot_settings[key] = text
                save_db()
                delete_message(chat_id, msg["message_id"])
                edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>"), reply_markup=prime_control_keyboard())
            except:
                delete_message(chat_id, msg["message_id"])
                edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>\n\n❌ Invalid value!"), reply_markup=prime_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_search" and text:
            query = text.strip().replace("+", "")
            if not query.isdigit() or len(query) < 3 or len(query) > 9:
                send_message(chat_id, render_body_text("❌ Please enter a valid 3 to 9 digit number!"))
                return
                
            wait_msg = send_message(chat_id, render_body_text("⌛ <i>Processing... Finding Number...</i>"))
            wait_msg_id = wait_msg.get("result", {}).get("message_id")
            
            # 🌟 ১. প্রথমে Local থেকে নাম্বার খুঁজবে (যে কোনো দেশের জন্য)
            found_indices = []
            for b_id, b_data in number_batches.items():
                for idx, n_obj in enumerate(b_data["numbers"]):
                    if n_obj["num"].replace("+", "").startswith(query) and chat_id not in n_obj.get("used_by", []):
                        found_indices.append((b_id, idx))
            
            fetched_nums = []
            if not found_indices:
                # 🌟 ২. যদি Local এ না পায়, তখন চেক করবে Voltx বা Nexa থেকে আনা যাবে কি না
                nexa_allowed = bot_settings.get("search_countries", [])
                voltx_allowed = bot_settings.get("voltx_search_countries", [])
                
                # ফিক্স: অ্যাডমিন প্যানেলে দেশ এড না থাকলে অটোমেটিক Block করে দেবে
                is_nexa_allowed = any(query.startswith(c) for c in nexa_allowed) if nexa_allowed else False
                is_voltx_allowed = any(query.startswith(c) for c in voltx_allowed) if voltx_allowed else False
                
                if not is_nexa_allowed and not is_voltx_allowed:
                    if wait_msg_id: delete_message(chat_id, wait_msg_id)
                    send_message(chat_id, render_body_text("❌ This country code is not allowed!"), reply_markup=main_menu(chat_id))
                    del user_states[chat_id]
                    return
                    
                if wait_msg_id: edit_message(chat_id, wait_msg_id, render_body_text("⌛ <i>Processing... Finding Number via API...</i>"))
                
                is_voltx_used = False
                req_count = bot_settings.get("num_req", 1)
                
                # 🌟 প্রথমে Voltx চেক করবে
                if is_voltx_allowed:
                    voltx_keys = bot_settings.get("voltx_keys", [])
                    for _ in range(req_count):
                        if len(fetched_nums) >= req_count: break
                        for api_key in voltx_keys:
                            try:
                                headers = {"mauthapi": api_key}
                                res = stex_post(f"{VOLTX_BASE_URL}/getnum", json_data={"rid": query}, headers=headers)
                                resp_data = res.json()
                                if resp_data.get("meta", {}).get("code") == 200 and resp_data.get("data"):
                                    num_str = str(resp_data["data"].get("no_plus_number", "")).replace("+", "")
                                    if not num_str: num_str = str(resp_data["data"].get("national_number", ""))
                                    fetched_nums.append(num_str)
                                    voltx_assigned_numbers[num_str] = chat_id 
                                    is_voltx_used = True
                                    global total_assigned_stats
                                    total_assigned_stats += 1
                                    break # শুধু api_key লুপ ব্রেক করবে, যাতে পরের নাম্বার আনতে পারে
                            except: continue

                # 🌟 Voltx এ না পেলে বা আরও নাম্বার লাগলে Nexa তে চেক করবে
                if len(fetched_nums) < req_count and is_nexa_allowed:
                    nexa_keys = bot_settings.get("nexa_keys", [])
                    t_len = 12
                    if query.startswith("880"): t_len = 13
                    elif query.startswith("1") and len(query) < 12: t_len = 11
                    
                    search_range = query + ("X" * (t_len - len(query))) if len(query) < t_len else query
                    
                    for _ in range(req_count - len(fetched_nums)): # বাকি নাম্বারগুলো আনবে
                        for api_key in nexa_keys:
                            try:
                                headers = {"X-API-Key": api_key}
                                res = requests.post(f"{NEXA_BASE_URL}/api/v1/numbers/get", json={"range": search_range, "format": "normal"}, headers=headers, timeout=10)
                                data = res.json()
                                if data.get("success") and data.get("number"):
                                    num_str = str(data["number"]).replace("+", "")
                                    number_id = data.get("number_id")
                                    fetched_nums.append(num_str)
                                    nexa_assigned_numbers[num_str] = chat_id 
                                    total_assigned_stats += 1
                                    if number_id:
                                        threading.Thread(target=poll_otp_with_status, args=(number_id, num_str, chat_id, api_key), daemon=True).start()
                                    break # শুধু api_key লুপ ব্রেক করবে
                            except: continue
                        
                if not fetched_nums:
                    if wait_msg_id: delete_message(chat_id, wait_msg_id)
                    send_message(chat_id, render_body_text("❌ Number out of stock!"), reply_markup=main_menu(chat_id))
                    del user_states[chat_id]
                    return
                save_db()
            else:
                random.shuffle(found_indices)
                for b_id, idx in found_indices:
                    if len(fetched_nums) >= bot_settings.get("num_req", 1): break
                    n_obj = number_batches[b_id]["numbers"][idx]
                    num_str = n_obj["num"]
                    
                    fetched_nums.append(num_str)
                    
                    n_obj["shares"] += 1
                    n_obj["used_by"].append(chat_id)
                    total_assigned_stats += 1
                    
                    if n_obj["shares"] >= bot_settings.get("num_share", 1):
                        n_obj["to_remove"] = True
                        used_numbers_list.append(num_str)
                
                for b_id in number_batches:
                    number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
                save_db()
                
            if wait_msg_id: edit_message(chat_id, wait_msg_id, render_body_text("✅ Number Found!"))
            kb = []
            flags_db = bot_settings.get("premium_flags", {})
            for num in fetched_nums:
                _, iso = get_flag_and_code(num)
                display_num = f"+{num}" if not num.startswith("+") else num
                
                emoji_id = "5780471598922337683" # Default Flag
                for flag_code, flag_data in flags_db.items():
                    if iso == flag_data.get("iso"):
                        if "id" in flag_data: emoji_id = flag_data["id"]
                        break
                kb.append([{"text": f"{display_num}", "icon_custom_emoji_id": emoji_id, "copy_text": {"text": display_num}, "style": "primary"}])
                
            vtx_ext = "_vtx" if 'is_voltx_used' in locals() and is_voltx_used else ""
            kb.append([{"text": "Change Number", "icon_custom_emoji_id": "6233525120334306978", "callback_data": f"c_n_s_{query}{vtx_ext}", "style": "danger"},
                       {"text": "OTP Group", "icon_custom_emoji_id": "6233384966961502838", "url": bot_settings["otp_link"], "style": "primary"}])
            
            c_btns = bot_settings["custom_messages"].get("search_number", {}).get("buttons", [])
            for c_b in c_btns: 
                b_copy = c_b.copy()
                if "style" not in b_copy: b_copy["style"] = "primary"
                kb.append([b_copy])
            
            kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
            
            if wait_msg_id:
                edit_message(chat_id, wait_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
                user_active_sessions[chat_id] = {"msg_id": wait_msg_id, "nums": fetched_nums}
            else:
                msg_res = send_message(chat_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
                if msg_res and "result" in msg_res:
                    user_active_sessions[chat_id] = {"msg_id": msg_res["result"]["message_id"], "nums": fetched_nums}
            return
            
        elif state == "wait_for_withdraw_amount" and text:
            msg_id_to_edit = temp_data[chat_id].get("msg_id")
            try:
                amount = float(text.strip())
                bal = temp_data[chat_id]["balance"]
                min_w = bot_settings['min_withdraw']
                
                if amount < min_w:
                    if msg_id_to_edit: edit_message(chat_id, msg_id_to_edit, render_body_text(f"❌ Minimum withdrawal is {min_w} ৳!\n💰 Balance: {bal} ৳\n\n📝 Enter again:"), reply_markup=get_cancel_kb())
                    return
                if amount > bal:
                    if msg_id_to_edit: edit_message(chat_id, msg_id_to_edit, render_body_text(f"❌ You don't have enough balance!\n💰 Balance: {bal} ৳\n\n📝 Enter again:"), reply_markup=get_cancel_kb())
                    return
                    
                temp_data[chat_id]["amount"] = amount
                user_states[chat_id] = "wait_for_withdraw_number"
                if msg_id_to_edit:
                    edit_message(chat_id, msg_id_to_edit, render_body_text(f"✅ Amount: {amount} ৳\n\n📱 Now send your <b>{temp_data[chat_id]['method']}</b> account number:"), reply_markup=get_cancel_kb())
            except ValueError:
                if msg_id_to_edit: edit_message(chat_id, msg_id_to_edit, render_body_text("❌ Invalid amount!\n\n📝 Please send a valid number:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_2fa_key" and text:
            msg_id_to_edit = temp_data.get(chat_id, {}).get("msg_id")
            delete_message(chat_id, msg.get("message_id")) # ইউজারের মেসেজ ডিলিট

            if not msg_id_to_edit:
                send_message(chat_id, render_body_text("❌ Error: Message not found. Try again."))
                del user_states[chat_id]
                return

            try:
                secret = text.strip().replace(" ", "")
                totp = pyotp.TOTP(secret)
                code = totp.now()
                remaining_time = 30 - (int(time.time()) % 30)
                
                success_txt = (
                    f"━━━━━━━━━━━━━━━\n"
                    f"《 🔐 <b>2FA CODE</b> 》\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🔐 <b>CODE:</b> <code>{code}</code>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🕓 <b>EXPIRES IN:</b> {remaining_time}s\n"
                    f"━━━━━━━━━━━━━━━"
                )
                kb = [[{"text": f"Click to copy {code}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": code}, "style": "success"}],
                      [{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"ref_2fa_{secret}", "style": "primary"},
                       {"text": "New Code", "icon_custom_emoji_id": "5352552689983067014", "callback_data": "gen_2fa", "style": "danger"}],
                      [{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]]
                
                edit_message(chat_id, msg_id_to_edit, render_body_text(success_txt), reply_markup={"inline_keyboard": kb})
                del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            except Exception:
                error_txt = "━━━━━━━━━━━━━━━\n《 🔑 <b>ENTER 2FA KEY</b> 》\n━━━━━━━━━━━━━━━\n📝 <b>SEND YOUR 2FA SECRET KEY</b>\n━━━━━━━━━━━━━━━\n❌ <b>Invalid Secret Key! Try again.</b>\n━━━━━━━━━━━━━━━"
                cancel_kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_2fa", "style": "danger"}]]}
                edit_message(chat_id, msg_id_to_edit, render_body_text(error_txt), reply_markup=cancel_kb)
            return

        elif state == "wait_for_withdraw_number":
            msg_id_to_edit = temp_data[chat_id].get("msg_id")
            
            method = temp_data[chat_id]["method"]
            amount = temp_data[chat_id]["amount"]
            number = text
            req_id = f"W_{str(uuid.uuid4())[:6].upper()}"
            
            first_name = msg.get("from", {}).get("first_name", "User")
            last_name = msg.get("from", {}).get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            
            update_balance(chat_id, -amount)
            pending_withdrawals[req_id] = {"user_id": chat_id, "amount": amount, "method": method, "number": number, "full_name": full_name}
            
            # Save to Firestore for History
            if db:
                try:
                    db.collection('withdrawals').document(req_id).set({
                        "user_id": str(chat_id),
                        "amount": amount,
                        "method": method,
                        "status": "pending",
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })
                except: pass
                
            # Admin withdrawal notification — always send to admins + w_group if set
            admin_msg = (
                f"🎙 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
                f"👤 <b>USER:</b> <a href='tg://user?id={chat_id}'>{full_name}</a> (<code>{chat_id}</code>)\n"
                f"💳 <b>AMOUNT:</b> {amount} TK\n"
                f"🏦 <b>METHOD:</b> {method}\n"
                f"🍏 <b>NUMBER:</b> <tg-spoiler>{number}</tg-spoiler>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🧾 <b>REQ ID:</b> <code>{req_id}</code>"
            )
            wb = {"inline_keyboard": [[
                {"text": "✅ APPROVE", "callback_data": f"wapp_{req_id}", "style": "success"},
                {"text": "❌ REJECT",  "callback_data": f"wrej_{req_id}", "style": "danger"}
            ]]}
            if bot_settings.get("w_group"):
                send_message(bot_settings["w_group"], admin_msg, reply_markup=wb)
            for adm in bot_settings.get("admins", []):
                try: send_message(adm, admin_msg, reply_markup=wb)
                except: pass
            kb = {"inline_keyboard": [[{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]]}
            success_text = (
                f"✅ Your withdrawal request has been submitted!\n\n"
                f"🧾 <b>Req ID:</b> <code>{req_id}</code>\n"
                f"💰 <b>Amount:</b> {amount} ৳\n"
                f"🏦 <b>Method:</b> {method}\n"
                f"📱 <b>Number:</b> <tg-spoiler>{number}</tg-spoiler>"
            )
            
            if msg_id_to_edit:
                edit_message(chat_id, msg_id_to_edit, render_body_text(success_text), reply_markup=kb)
            else:
                send_message(chat_id, render_body_text(success_text), reply_markup=kb)
                
            del user_states[chat_id]
            del temp_data[chat_id]
            return

    # --- Regular Commands ---
    if text in ["/help", "/commands"]:
        is_adm = is_admin(chat_id)
        user_cmds = render_body_text(
            f"📋 <b>Available Commands</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>User Commands:</b>\n"
            f"/start — Main menu\n"
            f"/status — Your balance, session & stats\n"
            f"/history — Last 10 OTPs received\n"
            f"/numbers — Last 5 assigned numbers\n"
            f"/traffic — Live country OTP traffic\n"
            f"/help — Show this command list\n"
            + (
            f"━━━━━━━━━━━━━━━\n"
            f"👑 <b>Admin Commands:</b>\n"
            f"/success — OTP success rate (24h)\n"
            f"/maintenance on — Enable maintenance mode\n"
            f"/maintenance off — Disable maintenance mode\n"
            f"/reset — Manual daily reset\n"
            f"/clearbalance — Clear all user balances\n"
            f"/stats — Live bot stats\n"
            if is_adm else ""
            ) +
            f"━━━━━━━━━━━━━━━\n"
            f"🕐 {bdt_str()}"
        )
        send_message(chat_id, user_cmds)
        return

    if text == "/history":
        send_message(chat_id, build_user_history_text(chat_id))
        return

    if text == "/numbers":
        send_message(chat_id, build_number_history_text(chat_id))
        return

    if text == "/traffic":
        send_message(chat_id, build_country_traffic_text())
        return

    if text == "/status":
        send_message(chat_id, build_status_text(chat_id))
        return

    if text == "/success" and str(chat_id) == str(OWNER_ID):
        send_message(chat_id, render_body_text(get_success_rate_text()))
        return

    if text == "/stats" and is_admin(chat_id):
        send_message(chat_id, build_live_stats_text())
        return

    if text == "/reset" and is_admin(chat_id):
        send_message(chat_id, render_body_text(
            f"🔄 <b>Manual Daily Reset</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"• Reset all Today OTPs → 0\n"
            f"• Clear country traffic\n"
            f"• Clear OTP log\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Confirm with /resetconfirm"
        ))
        return

    if text == "/resetconfirm" and is_admin(chat_id):
        threading.Thread(target=do_daily_reset, daemon=True).start()
        send_message(chat_id, render_body_text(f"✅ <b>Daily reset started!</b>\n🕐 {bdt_str()}"))
        return

    if text == "/clearbalance" and is_admin(chat_id):
        send_message(chat_id, render_body_text(
            f"⚠️ <b>Clear ALL Balances?</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Sets every user's balance to 0৳.\n"
            f"Cannot be undone!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Confirm with /clearbalanceconfirm"
        ))
        return

    if text == "/clearbalanceconfirm" and is_admin(chat_id):
        for uid in list(user_cache.keys()):
            user_cache[uid]["balance"] = 0.0
        if db:
            def _clr():
                uids = list(all_known_users)
                for i in range(0, len(uids), 450):
                    chunk = uids[i:i+450]
                    try:
                        batch = db.batch()
                        for uid in chunk:
                            batch.set(db.collection('users').document(uid), {"balance": 0.0}, merge=True)
                        batch.commit()
                    except: pass
                send_message(chat_id, render_body_text(
                    f"✅ <b>All Balances Cleared!</b>\n"
                    f"👥 {len(all_known_users)} users affected\n"
                    f"🕐 {bdt_str()}"
                ))
            threading.Thread(target=_clr, daemon=True).start()
        else:
            send_message(chat_id, render_body_text(f"✅ <b>Cache balances cleared!</b>\n🕐 {bdt_str()}"))
        return

    if text in ["/maintenance on", "/maintenance off"] and is_admin(chat_id):
        bot_settings["maintenance_mode"] = (text == "/maintenance on")
        save_db()
        state = "🔴 ON" if bot_settings["maintenance_mode"] else "🟢 OFF"
        send_message(chat_id, render_body_text(f"🔧 <b>Maintenance Mode: {state}</b>\n🕐 {bdt_str()}"))
        return

    # 🌟 Maintenance Mode block for regular users
    if is_maintenance(chat_id):
        send_message(chat_id, maintenance_msg())
        return

    if text.startswith("/start"):
        u_data_check = get_user(chat_id)
        is_new_user = u_data_check.get("total_otps", 0) == 0 and u_data_check.get("total_refers", 0) == 0
        
        # --- PROCESS PENDING REFERRAL ---
        if db:
            doc = db.collection('users').document(str(chat_id)).get()
            if doc.exists:
                u_data = doc.to_dict()
                if u_data.get("referred_by") and not u_data.get("ref_paid"):
                    inviter = u_data["referred_by"]
                    db.collection('users').document(str(chat_id)).update({"ref_paid": True})
                    reward = bot_settings.get("refer_reward", 0.2)
                    update_balance(inviter, reward)
                    db.collection('users').document(str(inviter)).update({"total_refers": firestore.Increment(1)})
                    # Update local cache too
                    if inviter in user_cache:
                        user_cache[inviter]["total_refers"] = user_cache[inviter].get("total_refers", 0) + 1
                    ref_msg = (
                        f"{PEM['gift']} <b>New Referral !</b>\n"
                        f"------------------\n"
                        f"🔥 <b>You Received {reward} TK</b>\n"
                        f"------------------\n"
                        f"{PEM['user']} <b>From User ID:</b> <code>{chat_id}</code>"
                    )
                    send_message(inviter, render_body_text(ref_msg))
                    
        c_msg = bot_settings["custom_messages"].get("start", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['hi']} Welcome!"))
        kb = []
        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        
        # Add Mini App open button if URL is configured
        app_btn = main_menu_inline(chat_id)
        if kb:
            send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})
            send_message(chat_id, render_body_text(f"{PEM['gear']} Navigation Menu:"), reply_markup=main_menu(chat_id))
        else:
            send_message(chat_id, txt, reply_markup=main_menu(chat_id))
        if app_btn:
            send_message(chat_id, "📱 <b>Open the App for better experience:</b>", reply_markup=app_btn)

        # 🌟 Auto Onboarding for new users
        if is_new_user:
            threading.Thread(target=send_onboarding, args=(chat_id,), daemon=True).start()
            
    elif text == "TRAFFIC":
        txt, markup = build_traffic_ui()
        send_message(chat_id, txt, reply_markup=markup)
        
    elif text == "Refer":
        u_data = get_user(chat_id)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"
        c_msg = bot_settings["custom_messages"].get("refer", {})
        
        raw_txt = c_msg.get("text", f"{PEM['gift']} Refer").replace("{ref_link}", ref_link).replace("{total_ref}", str(u_data.get('total_refers', 0))).replace("{ref_reward}", str(bot_settings['refer_reward']))
        txt = render_body_text(raw_txt)
        
        kb = [[{"text": "COPY LINK", "icon_custom_emoji_id": "5192739271886282680", "copy_text": {"text": ref_link}, "style": "success"}]]
        for b in c_msg.get("buttons", []): 
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        kb.append([{"text": "CLOSE", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif text == "WITHDRAWAL":
        if not bot_settings["withdraw_on"]:
            send_message(chat_id, render_body_text(f"{PEM['no']} Withdrawals are currently disabled."))
            return
        
        u_data = get_user(chat_id)
        bal = u_data.get('balance', 0.0)
        
        c_msg = bot_settings["custom_messages"].get("withdrawal", {})
        raw_txt = c_msg.get("text", "Withdrawal").replace("{bal}", str(bal)).replace("{total_otp}", str(u_data.get('total_otps', 0))).replace("{total_ref}", str(u_data.get('total_refers', 0))).replace("{min_w}", str(bot_settings['min_withdraw']))
        txt = render_body_text(raw_txt)
        
        kb = []
        for m in bot_settings["w_methods"]:
            kb.append([{"text": m.strip(), "icon_custom_emoji_id": "5190899075968441286", "callback_data": f"sel_wm_{m.strip()}", "style": "primary"}])
        
        for b in c_msg.get("buttons", []): 
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        kb.append([{"text": "Cancel", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif text == "Admin Panel" and is_admin(chat_id):
        send_message(chat_id, get_admin_text(), reply_markup=admin_panel_keyboard())

    elif text == "GET NUMBER":
        local_srvs = set([b["service"] for b in number_batches.values() if b["numbers"]])
        nexa_srvs  = set(bot_settings.get("nexa_services",  {}).keys())
        voltx_srvs = set(bot_settings.get("voltx_services", {}).keys())
        stex_srvs  = set(bot_settings.get("stex_services",  {}).keys())
        all_services = local_srvs.union(nexa_srvs).union(voltx_srvs).union(stex_srvs)

        # 🌟 Filter by visible_services (admin controlled)
        visible = bot_settings.get("visible_services", [])
        if visible:
            all_services = {s for s in all_services if s.upper() in [v.upper() for v in visible]}

        if not all_services:
            send_message(chat_id, render_body_text(f"{PEM['no']} No services available right now!"))
        else:
            c_msg = bot_settings["custom_messages"].get("get_number", {})
            txt   = render_body_text(c_msg.get("text", f"{PEM['pin']} Select Service"))

            apps_db = bot_settings.get("premium_apps", {})

            # 🌟 Traffic count per service (last 1h) for ranking
            now_t = time.time()
            srv_traffic = Counter(
                t.get("service", "").upper() for t in recent_traffic
                if now_t - t.get("time", 0) <= 3600
            )

            # Sort services: high traffic first
            sorted_srvs = sorted(all_services, key=lambda s: srv_traffic.get(s.upper(), 0), reverse=True)

            kb = []
            for s in sorted_srvs:
                s_up = s.upper()
                emoji_id = "5352694861990501856"
                for app_key, app_data in apps_db.items():
                    if s_up == app_key or s_up in app_key or app_key in s_up:
                        if "id" in app_data:
                            emoji_id = app_data["id"]
                            break
                traffic_cnt = srv_traffic.get(s_up, 0)
                if traffic_cnt >= 5:   badge = " 🔥"
                elif traffic_cnt >= 2: badge = " ⚡"
                elif traffic_cnt >= 1: badge = " ✅"
                else:                  badge = ""
                kb.append([{"text": f"{s}{badge}", "icon_custom_emoji_id": emoji_id,
                            "callback_data": f"g_s_{s}", "style": "primary"}])

            for b in c_msg.get("buttons", []):
                b_copy = b.copy()
                if "style" not in b_copy: b_copy["style"] = "primary"
                kb.append([b_copy])
            kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507",
                        "callback_data": "close_msg", "style": "danger"}])
            send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif text == "Search Number":
        user_states[chat_id] = "wait_for_search"
        c_msg = bot_settings["custom_messages"].get("search_number", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['num']} Search Number"))
        kb = [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_state", "style": "danger"}]]
        for b in c_msg.get("buttons", []): 
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif text == "2FA ONLINE" or text == "🔐 2FA ONLINE":
        txt = "━━━━━━━━━━━━━━━\n《 🔐 <b>2FA ONLINE</b> 》\n━━━━━━━━━━━━━━━\n<i>Generate your 2FA security code instantly using your secret key.</i>\n━━━━━━━━━━━━━━━"
        kb = [[{"text": "Generate 2fa code", "icon_custom_emoji_id": "5353022963132174959", "callback_data": "gen_2fa", "style": "success"}],
              [{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]]
        send_message(chat_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif text == "SUPPORT":
        c_msg = bot_settings["custom_messages"].get("support", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['msg']} Support"))
        if not txt.strip(): txt = render_body_text(f"{PEM['msg']} Support")
        kb = []
        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
            
        sup_link = bot_settings.get("support_link", "")
        if sup_link:
            kb.insert(0, [{"text": "Contact Support", "icon_custom_emoji_id": "5337302974806922068", "url": sup_link, "style": "success"}])
            
        kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb} if kb else None)

def expire_previous_number(chat_id):
    if chat_id in user_active_sessions:
        prev_data = user_active_sessions[chat_id]
        prev_msg_id = prev_data["msg_id"]
        nums = prev_data["nums"]
        
        # সব panel থেকে remove করা যাতে ইনবক্সে আর মেসেজ না যায়
        for num in nums:
            if num in nexa_assigned_numbers:
                del nexa_assigned_numbers[num]
            if num in voltx_assigned_numbers:
                del voltx_assigned_numbers[num]
            if num in stex_assigned_numbers:
                del stex_assigned_numbers[num]
        save_db()
        
        # আগের মেসেজ ইডিট করে Expired বাটন বসানো
        kb = [[{"text": "Number Expired", "icon_custom_emoji_id": "5336997731481193790", "callback_data": "ignore", "style": "danger"}]]
        try:
            edit_message(chat_id, prev_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
        except:
            pass
        del user_active_sessions[chat_id]

# ==========================================
# Callback Query Handler
# ==========================================
def handle_callback(call):
    global total_assigned_stats
    chat_id = call["message"]["chat"]["id"]
    chat_type = call["message"]["chat"].get("type", "private")
    data = call.get("data", "")

    # 🌟 Button Loading Fix: বাটন চাপার সাথে সাথেই টেলিগ্রামকে Response দিয়ে দেওয়া, যাতে বাটন আটকে না থাকে!
    if not data.startswith("test_p_conn_") and not data.startswith("c_n_") and not data.startswith("g_c_"):
        try: threading.Thread(target=answer_callback, args=(call["id"],)).start()
        except: pass

    if chat_type != "private" and not (data.startswith("wapp_") or data.startswith("wrej_")):
        return

    msg_id = call["message"]["message_id"]

    if chat_type == "private":
        if is_user_banned(chat_id):
            answer_callback(call["id"], "🚫 You are banned from using this bot!", show_alert=True)
            return

        if not check_force_join(chat_id) and data != "check_fj":
            send_force_join_msg(chat_id)
            return



    if data == "check_fj":
        if check_force_join(chat_id):
            delete_message(chat_id, msg_id)
            send_message(chat_id, render_body_text(f"{PEM['ok']} Thanks for joining! You can now use the bot."), reply_markup=main_menu(chat_id))
            
            # --- PROCESS PENDING REFERRAL ---
            if db:
                doc = db.collection('users').document(str(chat_id)).get()
                if doc.exists:
                    u_data = doc.to_dict()
                    if u_data.get("referred_by") and not u_data.get("ref_paid"):
                        inviter = u_data["referred_by"]
                        db.collection('users').document(str(chat_id)).update({"ref_paid": True})
                        reward = bot_settings.get("refer_reward", 0.2)
                        update_balance(inviter, reward)
                        db.collection('users').document(str(inviter)).update({"total_refers": firestore.Increment(1)})
                        ref_msg = (
                            f"{PEM['gift']} <b>New Referral !</b>\n"
                            f"------------------\n"
                            f"🔥 <b>You Received {reward} TK</b>\n"
                            f"------------------\n"
                            f"{PEM['user']} <b>From User ID:</b> <code>{chat_id}</code>"
                        )
                        send_message(inviter, render_body_text(ref_msg))
        else:
            answer_callback(call["id"], "❌ You haven't joined all channels yet!", show_alert=True)
        return

    elif data.startswith("s_msg_"):
        uid = data.replace("s_msg_", "")
        msg = full_msg_cache.get(uid, "Message expired or not found.")
        answer_callback(call["id"], f"Full Message:\n{msg}", show_alert=True)
        return

    if data == "close_msg":
        delete_message(chat_id, msg_id)
        
    elif data == "cancel_state":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        delete_message(chat_id, msg_id)

    elif data == "cancel_2fa":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        txt = "━━━━━━━━━━━━━━━\n《 🔐 <b>2FA ONLINE</b> 》\n━━━━━━━━━━━━━━━\n<i>Generate your 2FA security code instantly using your secret key.</i>\n━━━━━━━━━━━━━━━"
        kb = [[{"text": "Generate 2fa code", "icon_custom_emoji_id": "5353022963132174959", "callback_data": "gen_2fa", "style": "success"}],
              [{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data == "gen_2fa":
        user_states[chat_id] = "wait_for_2fa_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        txt = "━━━━━━━━━━━━━━━\n《 🔑 <b>ENTER 2FA KEY</b> 》\n━━━━━━━━━━━━━━━\n📝 <b>SEND YOUR 2FA SECRET KEY</b>\n━━━━━━━━━━━━━━━"
        kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_2fa", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup=kb)
        answer_callback(call["id"])

    elif data.startswith("ref_2fa_"):
        secret = data.replace("ref_2fa_", "")
        try:
            totp = pyotp.TOTP(secret)
            code = totp.now()
            remaining_time = 30 - (int(time.time()) % 30)
            
            success_txt = (
                f"━━━━━━━━━━━━━━━\n"
                f"《 🔐 <b>2FA CODE</b> 》\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔐 <b>CODE:</b> <code>{code}</code>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🕓 <b>EXPIRES IN:</b> {remaining_time}s\n"
                f"━━━━━━━━━━━━━━━"
            )
            kb = [[{"text": f"Click to copy {code}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": code}, "style": "success"}],
                  [{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"ref_2fa_{secret}", "style": "primary"},
                   {"text": "New Code", "icon_custom_emoji_id": "5352552689983067014", "callback_data": "gen_2fa", "style": "danger"}],
                  [{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]]
            
            edit_message(chat_id, msg_id, render_body_text(success_txt), reply_markup={"inline_keyboard": kb})
        except:
            answer_callback(call["id"], "❌ Error refreshing code!", show_alert=True)

    elif data == "cancel_prime_edit":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>"), reply_markup=prime_control_keyboard())
        
    elif data == "dummy_alert":
        answer_callback(call["id"], "This feature will be added later!", show_alert=True)
        
    elif data == "refresh_traffic":
        txt, markup = build_traffic_ui()
        edit_message(chat_id, msg_id, txt, reply_markup=markup)
        answer_callback(call["id"], "✅ Traffic Refreshed!", show_alert=False)

    elif data.startswith("pg_traffic_"):
        try: page = int(data.replace("pg_traffic_", ""))
        except ValueError: page = 0
        txt, markup = build_panel_group_traffic_ui(page)
        edit_message(chat_id, msg_id, txt, reply_markup=markup)
        answer_callback(call["id"])

    elif data.startswith("exp_rng_"):
        srv_query = data.replace("exp_rng_", "")
        
        country_stats = {}
        current_time = time.time()
        for t in recent_traffic:
            if current_time - t.get("time", 0) <= 3600:
                if t.get("service", "").startswith(srv_query):
                    iso = t.get("iso", "XX")
                    flag = t.get("flag", "🌍")
                    if iso not in country_stats:
                        country_stats[iso] = {"count": 0, "flag": flag}
                    country_stats[iso]["count"] += 1
        
        if not country_stats:
            answer_callback(call["id"], "❌ No recent traffic found for this service!", show_alert=True)
            return
            
        kb = []
        for iso, c_data in sorted(country_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            count = c_data["count"]
            c_name = iso
            emoji_id = "5780471598922337683"
            for code, fdata in bot_settings.get("premium_flags", {}).items():
                if fdata.get("iso") == iso:
                    c_name = fdata.get("name", iso)
                    if "id" in fdata: emoji_id = fdata["id"]
                    break
            
            btn_text = f"{c_name} ({iso}) - {count} OTP"
            kb.append([{"text": btn_text, "icon_custom_emoji_id": emoji_id, "callback_data": f"exp_c_{srv_query}_{iso}", "style": "primary"}])
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "refresh_traffic", "style": "danger"}])
        
        app_full_name, prem_app_html = get_service_info_html(srv_query)
        edit_message(chat_id, msg_id, render_body_text(f"📊 <b>Explore Service: {prem_app_html} {app_full_name}</b>\n\nSelect a country to view available ranges:"), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data.startswith("exp_c_"):
        parts = data.split("_")
        srv_query = parts[2]
        iso_query = parts[3]
        
        nums = []
        current_time = time.time()
        for t in recent_traffic:
            if current_time - t.get("time", 0) <= 3600:
                if t.get("service", "").startswith(srv_query) and t.get("iso") == iso_query:
                    num = t.get("number", "").replace("+", "").strip()
                    if num: nums.append(num)
        
        if not nums:
            answer_callback(call["id"], "❌ No recent numbers found for this country!", show_alert=True)
            return
            
        # শুধুমাত্র Nexa Services থেকে রেঞ্জ নিবো (Search Countries নিবো না, কারণ ওগুলোতে শুধু দেশের কোড থাকে)
        known_ranges = set()
        for s_name, c_dict in bot_settings.get("nexa_services", {}).items():
            for c_name, r_list in c_dict.items():
                for r in r_list:
                    known_ranges.add(r)
                    
        sorted_known = sorted(list(known_ranges), key=len, reverse=True)
        
        r_counts = Counter()
        for num in nums:
            matched = False
            for r in sorted_known:
                if num.startswith(r):
                    r_counts[r] += 1
                    matched = True
                    break
            if not matched:
                if len(num) >= 7:
                    r_counts[num[:7]] += 1
                else:
                    r_counts[num] += 1
                    
        r_list = r_counts.most_common(12)
        
        kb = []
        for r, count in r_list:
            # এক লাইনে একটা করে বাটন
            kb.append([{"text": f"{r} ({count})", "icon_custom_emoji_id": "5352862640592949843", "copy_text": {"text": r}, "style": "primary"}])
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"exp_rng_{srv_query}", "style": "danger"}])
        
        app_full_name, prem_app_html = get_service_info_html(srv_query)
        prem_flag_html = get_flag_info_html(iso_query)
        
        edit_message(chat_id, msg_id, render_body_text(f"📊 <b>Ranges for {prem_app_html} {app_full_name} - {prem_flag_html} {iso_query}</b>\n\nClick on any range to copy it."), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    # --- User Management Flows Integration ---
    elif data == "user_management":
        edit_message(chat_id, msg_id, get_user_management_text(), reply_markup=user_management_keyboard())

    elif data == "um_manage_balance":
        user_states[chat_id] = "wait_for_um_bal_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to Manage Balance:"), reply_markup=get_cancel_kb())
        
    elif data == "um_ban_unban":
        user_states[chat_id] = "wait_for_um_ban_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to Ban or Unban:"), reply_markup=get_cancel_kb())

    elif data == "um_user_profile":
        user_states[chat_id] = "wait_for_um_prof_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to View Profile:"), reply_markup=get_cancel_kb())

    elif data == "um_balance_overview":
        kb = {"inline_keyboard": [
            [{"text": "Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "um_balance_overview", "style": "success"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "user_management", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, get_balance_overview_text(), reply_markup=kb)
        answer_callback(call["id"])

    elif data.startswith("au_page_"):
        try: page = int(data.replace("au_page_", ""))
        except ValueError: page = 0
        edit_message(chat_id, msg_id, render_body_text("⌛ <i>Loading Users...</i>"))
        txt, markup = build_all_users_list_ui(page)
        edit_message(chat_id, msg_id, txt, reply_markup=markup)
        answer_callback(call["id"])

    # --- Menu Design Integration ---
    elif data == "menu_design_list":
        edit_message(chat_id, msg_id, render_body_text(f"🎨 <b>Menu Design Editor</b>\n\nSelect a menu block to edit its Body Text and Inline Buttons. You can use Premium Emojis too!"), reply_markup=menu_design_list_keyboard())

    elif data == "md_reset_defaults":
        bot_settings["custom_messages"] = DEFAULT_CUSTOM_MESSAGES.copy()
        save_db()
        answer_callback(call["id"], "✅ Resetted to Premium Defaults!", show_alert=True)

    elif data.startswith("md_edit_"):
        answer_callback(call["id"])
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        key = data.replace("md_edit_", "")
        cm_text = render_body_text(bot_settings["custom_messages"].get(key, {}).get("text", "..."))
        try:
            edit_message(chat_id, msg_id, render_body_text(f"🎨 <b>Editing: {key.upper()}</b>\n\nPreview of current Text:\n{cm_text}"), reply_markup=menu_edit_options_keyboard(key))
        except: pass

    elif data.startswith("md_text_"):
        key = data.replace("md_text_", "")
        user_states[chat_id] = "wait_for_menu_text"
        temp_data[chat_id] = {"msg_id": msg_id, "menu_key": key}
        edit_message(chat_id, msg_id, render_body_text(f"📝 <b>Edit Body: {key.upper()}</b>\n\nSend the new text. You can use Premium Emojis directly here.\n(Use standard HTML like <b>bold</b>, <i>italic</i> for formatting)"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_edit_{key}", "style": "danger"}]]})

    elif data.startswith("md_btns_"):
        answer_callback(call["id"]) 
        if chat_id in user_states: del user_states[chat_id] 
        if chat_id in temp_data: del temp_data[chat_id]
        key = data.replace("md_btns_", "")
        try:
            edit_message(chat_id, msg_id, render_body_text(f"⚙️ <b>Edit Inline Buttons: {key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(key))
        except: pass

    elif data.startswith("md_addbtn_"):
        key = data.replace("md_addbtn_", "")
        user_states[chat_id] = "wait_for_menu_btn"
        temp_data[chat_id] = {"msg_id": msg_id, "menu_key": key}
        edit_message(chat_id, msg_id, render_body_text(f"➕ <b>Add Button: {key.upper()}</b>\n\nSend custom button in this format:\n<code>Button Text - https://link.com</code>\n\n<i>(Only normal Emojis supported here!)</i>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_btns_{key}", "style": "danger"}]]})

    elif data.startswith("md_delbtn_"):
        parts = data.split("_")
        key = parts[2]
        b_idx = int(parts[3])
        if b_idx < len(bot_settings["custom_messages"][key]["buttons"]):
            del bot_settings["custom_messages"][key]["buttons"][b_idx]
            save_db()
            answer_callback(call["id"], "✅ Button Deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"⚙️ <b>Edit Inline Buttons: {key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(key))

    elif data.startswith("sel_wm_"):
        method = data.replace("sel_wm_", "")
        bal = get_user(chat_id).get('balance', 0.0)
        min_w = bot_settings['min_withdraw']
        
        if bal < min_w:
            answer_callback(call["id"], f"❌ আপনার ব্যালেন্স অপর্যাপ্ত! মিনিমাম {min_w} ৳ প্রয়োজন।", show_alert=True)
            return
            
        temp_data[chat_id] = {"method": method, "balance": bal, "msg_id": msg_id}
        user_states[chat_id] = "wait_for_withdraw_amount"
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['ok']} Method: {method}\n💰 Available Balance: {bal} ৳\n\n📝 Enter the amount you want to withdraw (Min: {min_w} ৳):"), reply_markup=get_cancel_kb())
        answer_callback(call["id"])

    elif data == "test_message_flow":
        user_states[chat_id] = "wait_for_test_service"
        temp_data[chat_id] = {}
        edit_message(chat_id, msg_id, render_body_text("🧪 <b>Test Mode</b>\n\n📝 Send the Service Name (e.g., IG):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]]})

    elif data == "manage_emojis":
        flag_count = len(bot_settings.get("premium_flags", {}))
        app_count  = len(bot_settings.get("premium_apps", {}))
        edit_message(chat_id, msg_id, render_body_text(
            f"{PEM['star']} <b>Premium Emoji Management</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏳 Flags Loaded: <b>{flag_count}</b>\n"
            f"📱 Services Loaded: <b>{app_count}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Upload your TXT files below.\n"
            f"📌 Flag TXT format:\n"
            f"<code>(dialcode)(ISO)emoji Name {{\"emoji\":\"x\",\"id\":\"xxx\"}}</code>\n"
            f"📌 Service TXT format:\n"
            f"<code>emoji Name {{\"emoji\":\"x\",\"id\":\"xxx\"}}</code>"
        ), reply_markup=emoji_settings_keyboard())

    elif data == "up_flags_txt":
        user_states[chat_id] = "wait_for_flag_txt"
        edit_message(chat_id, msg_id, render_body_text("📂 Please upload the <b>Flag Emojis</b> <code>.txt</code> file."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_emojis", "style": "danger"}]]})

    elif data == "up_apps_txt":
        user_states[chat_id] = "wait_for_app_txt"
        edit_message(chat_id, msg_id, render_body_text("📂 Please upload the <b>Service Apps</b> <code>.txt</code> file."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_emojis", "style": "danger"}]]})

    elif data == "add_single_emoji":
        user_states[chat_id] = "wait_for_emoji_extract"
        edit_message(chat_id, msg_id, render_body_text("📝 যেকোনো একটি Premium Emoji সেন্ড করুন (যেমন: 🇧🇩 বা 🚫):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_emojis", "style": "danger"}]]})

    elif data == "dl_flags_txt":
        content = generate_emoji_txt("flags")
        if content:
            send_document(chat_id, "Flag_Emojis.txt", content)
            answer_callback(call["id"], "✅ Downloaded!")
        else:
            answer_callback(call["id"], "❌ No Flag Emojis found!", show_alert=True)

    elif data == "dl_apps_txt":
        content = generate_emoji_txt("apps")
        if content:
            send_document(chat_id, "Service_Apps.txt", content)
            answer_callback(call["id"], "✅ Downloaded!")
        else:
            answer_callback(call["id"], "❌ No App Emojis found!", show_alert=True)

    elif data == "del_all_flags":
        bot_settings["premium_flags"] = {}
        save_db()
        answer_callback(call["id"], "✅ All Premium Flags Deleted Successfully!", show_alert=True)

    elif data == "del_all_apps":
        bot_settings["premium_apps"] = {}
        save_db()
        answer_callback(call["id"], "✅ All Premium Services Deleted Successfully!", show_alert=True)

    elif data == "broadcast_msg":
        user_states[chat_id] = "wait_for_broadcast"
        edit_message(chat_id, msg_id, render_body_text("📢 <b>Broadcast Mode</b>\n\nSend the message you want to broadcast (Text, Photo, Video, File etc)."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]})

    elif data == "admin_clear_all_balance":
        edit_message(chat_id, msg_id, render_body_text(
            f"⚠️ <b>Clear ALL User Balances?</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"This will set <b>every user's balance to 0৳</b>.\n"
            f"This action CANNOT be undone!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Are you sure?"
        ), reply_markup={"inline_keyboard": [
            [{"text": "✅ YES — Clear All Balances", "callback_data": "admin_confirm_clear_balance", "style": "danger"}],
            [{"text": "❌ Cancel", "callback_data": "admin_live_stats", "style": "success"}]
        ]})

    elif data == "admin_confirm_clear_balance":
        # 1. Clear local cache
        for uid in list(user_cache.keys()):
            user_cache[uid]["balance"] = 0.0

        # 2. Clear Firebase — fetch ALL users from Firestore, not just all_known_users
        if db:
            def _clear_fb():
                try:
                    # Fetch every user doc from Firestore
                    all_docs = db.collection("users").stream()
                    uid_list = [doc.id for doc in all_docs]
                    count = 0
                    for i in range(0, len(uid_list), 450):
                        chunk = uid_list[i:i+450]
                        try:
                            batch = db.batch()
                            for uid in chunk:
                                ref = db.collection("users").document(uid)
                                batch.update(ref, {"balance": 0.0})
                                # Clear local file + cache
                                _local_balances[str(uid)] = 0.0
                                if uid in user_cache:
                                    user_cache[uid]["balance"] = 0.0
                            batch.commit()
                            _save_balances()  # save balances.json
                            count += len(chunk)
                        except Exception as e:
                            print(f"[CLEAR BALANCE] batch error: {e}")
                    # Reset global pool too
                    bot_settings["global_balance_pool"] = 0.0
                    save_db()
                    send_message(chat_id,
                        f"✅ <b>All Balances Cleared!</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"👥 Users affected: <b>{count}</b>\n"
                        f"💰 All balances set to: <b>0৳</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"🕐 {bdt_str()}"
                    )
                except Exception as e:
                    send_message(chat_id, f"❌ Error clearing balances: {e}")
            threading.Thread(target=_clear_fb, daemon=True).start()
        else:
            # No Firebase — clear local only
            _local_balances.clear()
            _save_balances()
            bot_settings["global_balance_pool"] = 0.0
            save_db()
            send_message(chat_id, "✅ All balances cleared (local only — Firebase not connected).")
        answer_callback(call["id"], "✅ Clearing all balances...", show_alert=True)

    elif data == "admin_manual_reset":
        edit_message(chat_id, msg_id, render_body_text(
            f"🔄 <b>Manual Daily Reset</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"This will:\n"
            f"• Reset all Today OTPs → 0\n"
            f"• Clear country traffic stats\n"
            f"• Clear OTP log\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Confirm?"
        ), reply_markup={"inline_keyboard": [
            [{"text": "✅ YES — Reset Now", "callback_data": "admin_confirm_manual_reset", "style": "danger"}],
            [{"text": "❌ Cancel", "callback_data": "admin_live_stats", "style": "success"}]
        ]})

    elif data == "admin_confirm_manual_reset":
        threading.Thread(target=do_daily_reset, daemon=True).start()
        answer_callback(call["id"], "✅ Daily reset started!", show_alert=True)
        edit_message(chat_id, msg_id, render_body_text(f"🔄 <b>Reset in progress...</b>\n🕐 {bdt_str()}"), reply_markup={"inline_keyboard": [[{"text": "◀️ Back", "callback_data": "admin_live_stats", "style": "danger"}]]})
    elif data == "admin_reset_user_balance":
        # Ask for user ID
        user_pending_actions[chat_id] = {"action": "reset_user_balance"}
        edit_message(chat_id, msg_id,
            f"💰 <b>Reset Specific User Balance</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Send the <b>User ID</b> of the user whose balance you want to reset to 0.\n"
            f"(e.g. <code>123456789</code>)",
            reply_markup={"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_live_stats", "style": "danger"}]]}
        )


    elif data == "admin_live_stats":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "callback_data": "admin_live_stats", "style": "success"}],
            [{"text": f"{'🔴 Maintenance ON' if bot_settings.get('maintenance_mode') else '🟢 Maintenance OFF'}",
              "callback_data": "admin_toggle_maintenance", "style": "danger" if not bot_settings.get("maintenance_mode") else "success"}],
            [{"text": "🔄 Manual Daily Reset", "callback_data": "admin_manual_reset", "style": "primary"},
             {"text": "💰 Clear All Balances", "callback_data": "admin_clear_all_balance", "style": "danger"}],
            [{"text": "◀️ Back", "callback_data": "system_settings", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, build_live_stats_text(), reply_markup=kb)

    elif data == "admin_toggle_maintenance":
        bot_settings["maintenance_mode"] = not bot_settings.get("maintenance_mode", False)
        save_db()
        state = "🔴 ON" if bot_settings["maintenance_mode"] else "🟢 OFF"
        answer_callback(call["id"], f"Maintenance Mode: {state}", show_alert=True)
        handle_callback({"message": call["message"], "data": "admin_live_stats", "id": call["id"]})

    elif data == "admin_leaderboard":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "callback_data": "admin_leaderboard", "style": "success"},
             {"text": "◀️ Back", "callback_data": "system_settings", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, build_leaderboard_text(), reply_markup=kb)

    elif data == "admin_error_log":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "callback_data": "admin_error_log", "style": "success"},
             {"text": "🗑 Clear Log", "callback_data": "admin_clear_error_log", "style": "danger"}],
            [{"text": "◀️ Back", "callback_data": "system_settings", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, build_error_log_text(), reply_markup=kb)

    elif data == "admin_clear_error_log":
        with _error_lock:
            _error_log.clear()
        answer_callback(call["id"], "✅ Error log cleared!", show_alert=True)
        handle_callback({"message": call["message"], "data": "admin_error_log", "id": call["id"]})

    elif data == "admin_country_traffic":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "callback_data": "admin_country_traffic", "style": "success"},
             {"text": "◀️ Back", "callback_data": "system_settings", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, build_country_traffic_text(), reply_markup=kb)

    elif data == "admin_user_search":
        user_states[chat_id] = "wait_for_user_search"
        edit_message(chat_id, msg_id, render_body_text(
            f"🔍 <b>User Search</b>\n\n"
            f"Send the User ID to look up:"
        ), reply_markup={"inline_keyboard": [[{"text": "◀️ Cancel", "callback_data": "system_settings", "style": "danger"}]]})

    elif data.startswith("um_toggle_ban_"):
        target = data.split("um_toggle_ban_")[1]
        u = get_user(int(target))
        new_ban = not u.get("banned", False)
        if db:
            try: db.collection("users").document(target).set({"banned": new_ban}, merge=True)
            except: pass
        if target in user_cache: user_cache[target]["banned"] = new_ban
        answer_callback(call["id"], f"{'🚫 Banned' if new_ban else '✅ Unbanned'} user {target}", show_alert=True)
        edit_message(chat_id, msg_id, build_user_profile_text(target),
                     reply_markup=user_manager_keyboard(target, new_ban))

    elif data.startswith("um_reset_bal_"):
        target = data.split("um_reset_bal_")[1]
        if db:
            try: db.collection("users").document(target).set({"balance": 0.0}, merge=True)
            except: pass
        if target in user_cache: user_cache[target]["balance"] = 0.0
        answer_callback(call["id"], f"✅ Balance reset for {target}", show_alert=True)
        u = get_user(int(target))
        edit_message(chat_id, msg_id, build_user_profile_text(target),
                     reply_markup=user_manager_keyboard(target, u.get("banned", False)))

    elif data.startswith("um_add_bal_"):
        target = data.split("um_add_bal_")[1]
        user_states[chat_id] = f"wait_admin_add_bal_{target}"
        edit_message(chat_id, msg_id, render_body_text(
            f"💰 Add Balance to <code>{target}</code>\n\nEnter amount (e.g. 10.5):"
        ), reply_markup={"inline_keyboard": [[{"text": "◀️ Cancel", "callback_data": "system_settings", "style": "danger"}]]})

    elif data.startswith("um_history_"):
        target = data.split("um_history_")[1]
        hist_txt = build_user_history_text(int(target))
        edit_message(chat_id, msg_id, hist_txt,
                     reply_markup={"inline_keyboard": [[{"text": "◀️ Back", "callback_data": f"um_profile_{target}", "style": "danger"}]]})

    elif data.startswith("um_profile_"):
        target = data.split("um_profile_")[1]
        u = get_user(int(target))
        edit_message(chat_id, msg_id, build_user_profile_text(target),
                     reply_markup=user_manager_keyboard(target, u.get("banned", False)))

    # ==========================================
    # 🌟 BULK NUMBER UPLOAD — max 50, text file output
    # ==========================================
    elif data == "bulk_upload_num":
        edit_message(chat_id, msg_id, render_body_text(
            f"📦 <b>Bulk Number Upload</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Upload a <b>.txt</b> file with numbers.\n\n"
            f"📌 File name format:\n"
            f"<code>WHATSAPP+BD.txt</code>\n"
            f"<i>(SERVICE+COUNTRY.txt)</i>\n\n"
            f"📌 File content format:\n"
            f"<code>+8801XXXXXXXX\n+8801XXXXXXXX\n...</code>\n\n"
            f"⚠️ Max <b>50 numbers</b> per file.\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕐 {bdt_str()}"
        ), reply_markup={"inline_keyboard": [
            [{"text": "◀️ Cancel", "callback_data": "back_to_admin", "style": "danger"}]
        ]})
        user_states[chat_id] = "wait_for_bulk_txt"

    elif data == "bulk_confirm_auto":
        td = temp_data.get(chat_id, {})
        clean_nums   = td.get("numbers", [])
        auto_service = td.get("auto_service", "UNKNOWN")
        auto_country = td.get("auto_country", "UNKNOWN")
        fname        = td.get("filename", f"{auto_service}+{auto_country}.txt")
        if not clean_nums:
            answer_callback(call["id"], "❌ No number data found!", show_alert=True)
            del user_states[chat_id]
            return

        batch_id = str(uuid.uuid4())[:8]
        number_batches[batch_id] = {
            "filename": fname,
            "service": auto_service,
            "country": auto_country,
            "numbers": [{"num": n, "shares": 0, "used_by": []} for n in clean_nums]
        }
        global total_uploaded_stats
        total_uploaded_stats += len(clean_nums)
        save_db()

        # Generate downloadable TXT of uploaded numbers
        txt_content = "\n".join(clean_nums).encode("utf-8")
        send_document(chat_id, fname, txt_content)

        app_full_name, prem_app_html = get_service_info_html(auto_service)
        prem_flag_html = get_flag_info_html(clean_nums[0]) if clean_nums else ""

        broadcast_txt = render_body_text(
            f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"      《 𝗡𝗘𝗪 𝗡𝗨𝗠𝗕𝗘𝗥𝗦 𝗔𝗗𝗗𝗘𝗗 》\n"
            f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"{prem_flag_html} {auto_country} {prem_app_html} {auto_service}\n"
            f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"📤 Total Added: <b>{len(clean_nums)}</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"Use /start to get your numbers!\n"
            f"🕐 {bdt_str()}"
        )

        edit_message(chat_id, msg_id, render_body_text(
            f"✅ <b>Bulk Upload Done!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📲 Service: <b>{auto_service}</b>\n"
            f"🌍 Country: <b>{auto_country}</b>\n"
            f"📱 Numbers: <b>{len(clean_nums)}</b>\n"
            f"🆔 Batch ID: <code>{batch_id}</code>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Broadcasting to all users...\n"
            f"🕐 {bdt_str()}"
        ), reply_markup={"inline_keyboard": [[{"text": "◀️ Back", "callback_data": "back_to_admin", "style": "danger"}]]})

        def simple_broadcast(txt):
            b_session = requests.Session()
            url = f"{BASE_URL}/sendMessage"
            for u_id in list(all_known_users):
                try:
                    b_session.post(url, json={"chat_id": u_id, "text": txt, "parse_mode": "HTML",
                                              "disable_web_page_preview": True}, timeout=5)
                except: pass
                time.sleep(0.035)
        threading.Thread(target=simple_broadcast, args=(broadcast_txt,), daemon=True).start()

        temp_data.pop(chat_id, None)
        user_states.pop(chat_id, None)

    elif data == "dl_batch_numbers":
        # Download all current batch numbers as txt
        if not number_batches:
            answer_callback(call["id"], "❌ No number batches found!", show_alert=True)
            return
        kb = []
        for b_id, b_data in number_batches.items():
            kb.append([{"text": f"⬇️ {b_data['filename']} ({len(b_data['numbers'])})",
                        "callback_data": f"dl_batch_{b_id}", "style": "success"}])
        kb.append([{"text": "◀️ Back", "callback_data": "back_to_admin", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text("📂 <b>Download Number Batches</b>\n\nSelect a batch:"),
                     reply_markup={"inline_keyboard": kb})

    elif data.startswith("dl_batch_"):
        b_id = data.split("dl_batch_")[1]
        if b_id in number_batches:
            b = number_batches[b_id]
            lines = [n["num"] for n in b["numbers"]]
            content = "\n".join(lines).encode("utf-8")
            fname = b.get("filename", f"{b['service']}+{b['country']}.txt")
            send_document(chat_id, fname, content)
            answer_callback(call["id"], f"✅ Downloaded {len(lines)} numbers!")
        else:
            answer_callback(call["id"], "❌ Batch not found!", show_alert=True)

    elif data == "upload_num":
        user_states[chat_id] = "wait_for_txt"
        edit_message(chat_id, msg_id, render_body_text(
            f"📂 <b>Upload Numbers</b>\n\n"
            f"Upload a <b>.txt</b> file.\n\n"
            f"📌 Filename format: <code>SERVICE+COUNTRY.txt</code>\n"
            f"📌 Content:\n<code>+8801XXXXXXXXX\n+8801XXXXXXXXX</code>"
        ), reply_markup={"inline_keyboard": [[{"text": "◀️ Back", "callback_data": "back_to_admin", "style": "danger"}]]})

    elif data == "delete_files":
        kb = []
        for b_id, b_data in number_batches.items():
            kb.append([{"text": f"{b_data['filename']} ({len(b_data['numbers'])})", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"del_b_{b_id}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "primary"}])
        txt = "🗑 Select a file to delete:" if len(kb) > 1 else f"{PEM['no']} No files found."
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_b_"):
        b_id = data.split("del_b_")[1]
        if b_id in number_batches:
            del number_batches[b_id]
            save_db()
            answer_callback(call["id"], "✅ File deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "delete_files", "id": call["id"]})

    elif data == "show_used":
        kb = {"inline_keyboard": [[{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_used", "style": "primary"}], [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['ok']} <b>Total Used Numbers:</b> {len(used_numbers_list)}"), reply_markup=kb)

    elif data == "show_unused":
        unused_count = sum(len(b["numbers"]) for b in number_batches.values())
        kb = {"inline_keyboard": [[{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_unused", "style": "primary"}], [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['rocket']} <b>Total Unused Numbers:</b> {unused_count}"), reply_markup=kb)

    elif data == "dl_used":
        if not used_numbers_list:
            answer_callback(call["id"], "❌ No used numbers found!", show_alert=True)
            return
        content = "\n".join(used_numbers_list).encode('utf-8')
        send_document(chat_id, "used_numbers.txt", content)
        answer_callback(call["id"])

    elif data == "dl_unused":
        unused_list = [n["num"] for b in number_batches.values() for n in b["numbers"]]
        if not unused_list:
            answer_callback(call["id"], "❌ No unused numbers found!", show_alert=True)
            return
        content = "\n".join(unused_list).encode('utf-8')
        send_document(chat_id, "unused_numbers.txt", content)
        answer_callback(call["id"])

    elif data == "lb_main":
        txt = f"━━━━━━━━━━━━━━━\n《 {PEM['admin']} <b>LEADER BOARD MENU</b> 》\n━━━━━━━━━━━━━━━\n<i>Select a category to view the top performers or history.</i>\n━━━━━━━━━━━━━━━"
        kb = [
            [{"text": "Top Referrers", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "lb_top_refs", "style": "primary"}],
            [{"text": "Top OTP Receivers", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "lb_top_otps", "style": "primary"}],
            [{"text": "Withdrawal History", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "lb_w_history", "style": "success"}],
            [{"text": "Back to Admin", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("lb_"):
        sub = data.replace("lb_", "")
        edit_message(chat_id, msg_id, render_body_text("⌛ <i>Fetching Data...</i>"))
        
        num_map = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", "0": "0️⃣"}
        def get_p_num(n): return "".join([num_map.get(c, c) for c in str(n)])
        
        try:
            if sub == "top_refs":
                title, field, limit, icon = "TOP 5 REFERRERS", "total_refers", 5, PEM.get('user', '👥')
                users = db.collection('users').order_by(field, direction="DESCENDING").limit(limit).stream()
                res_txt = ""
                count = 1
                for u in users:
                    d = u.to_dict()
                    if d.get(field, 0) > 0:
                        p = "└" if count == limit else "├"
                        res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={u.id}'>{u.id}</a> ➔ <b>{d.get(field,0)}</b>\n"
                        count += 1
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "top_otps":
                title, field, limit, icon = "TOP 5 OTP RECEIVERS", "total_otps", 5, PEM.get('msg', '📩')
                users = db.collection('users').order_by(field, direction="DESCENDING").limit(limit).stream()
                res_txt = ""
                count = 1
                for u in users:
                    d = u.to_dict()
                    if d.get(field, 0) > 0:
                        p = "└" if count == limit else "├"
                        res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={u.id}'>{u.id}</a> ➔ <b>{d.get(field,0)}</b>\n"
                        count += 1
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "w_history":
                title, limit, icon = "LAST 10 WITHDRAWALS", 10, PEM.get('money', '💸')
                ws = db.collection('withdrawals').order_by('timestamp', direction="DESCENDING").limit(limit).stream()
                res_txt = ""
                count = 1
                for w in ws:
                    d = w.to_dict()
                    s = str(d.get('status','Pending')).lower()
                    stat_icon = PEM.get('ok','✅') if s in ["approved","success"] else PEM.get('no','❌') if s=="rejected" else "⏳"
                    uid = d.get('user_id','User')
                    p = "└" if count == limit else "├"
                    res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={uid}'>{uid}</a> ➔ <b>{d.get('amount',0)}৳</b> {stat_icon}\n"
                    count += 1
                if not res_txt: res_txt = "└ <i>No history found.</i>\n"

            final_msg = f"━━━━━━━━━━━━━━━\n{icon} <b>{title}</b>\n━━━━━━━━━━━━━━━\n{res_txt}━━━━━━━━━━━━━━━"
            kb = [[{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": data, "style": "success"}, {"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]
            edit_message(chat_id, msg_id, render_body_text(final_msg), reply_markup={"inline_keyboard": kb})

        except Exception as e:
            edit_message(chat_id, msg_id, render_body_text(f"❌ Error: {e}"), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]})

    elif data == "lb_main":
        txt = f"━━━━━━━━━━━━━━━\n《 {PEM['admin']} <b>LEADER BOARD MENU</b> 》\n━━━━━━━━━━━━━━━\n<i>Select a category to view the top performers or history.</i>\n━━━━━━━━━━━━━━━"
        kb = [
            [{"text": "Top Referrers", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "lb_top_refs", "style": "primary"}],
            [{"text": "Top OTP Receivers", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "lb_top_otps", "style": "primary"}],
            [{"text": "Withdrawal History", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "lb_w_history", "style": "success"}],
            [{"text": "Back to Admin", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("lb_"):
        sub = data.replace("lb_", "")
        edit_message(chat_id, msg_id, render_body_text("⌛ <i>Fetching Data...</i>"))
        
        num_map = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", "0": "0️⃣"}
        def get_p_num(n): return "".join([num_map.get(c, c) for c in str(n)])
        
        try:
            if sub == "top_refs":
                title, field, limit, icon = "TOP 5 REFERRERS", "total_refers", 5, PEM.get('user', '👥')
                users = db.collection('users').order_by(field, direction="DESCENDING").limit(limit).stream()
                res_txt = ""
                count = 1
                for u in users:
                    d = u.to_dict()
                    if d.get(field, 0) > 0:
                        p = "└" if count == limit else "├"
                        res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={u.id}'>{u.id}</a> ➔ <b>{d.get(field,0)}</b>\n"
                        count += 1
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "top_otps":
                title, field, limit, icon = "TOP 5 OTP RECEIVERS", "total_otps", 5, PEM.get('msg', '📩')
                users = db.collection('users').order_by(field, direction="DESCENDING").limit(limit).stream()
                res_txt = ""
                count = 1
                for u in users:
                    d = u.to_dict()
                    if d.get(field, 0) > 0:
                        p = "└" if count == limit else "├"
                        res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={u.id}'>{u.id}</a> ➔ <b>{d.get(field,0)}</b>\n"
                        count += 1
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "w_history":
                title, limit, icon = "LAST 10 WITHDRAWALS", 10, PEM.get('money', '💸')
                ws = db.collection('withdrawals').order_by('timestamp', direction="DESCENDING").limit(limit).stream()
                res_txt = ""
                count = 1
                for w in ws:
                    d = w.to_dict()
                    s = str(d.get('status','Pending')).lower()
                    stat_icon = PEM.get('ok','✅') if s in ["approved","success"] else PEM.get('no','❌') if s=="rejected" else "⏳"
                    uid = d.get('user_id','User')
                    p = "└" if count == limit else "├"
                    res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={uid}'>{uid}</a> ➔ <b>{d.get('amount',0)}৳</b> {stat_icon}\n"
                    count += 1
                if not res_txt: res_txt = "└ <i>No history found.</i>\n"

            final_msg = f"━━━━━━━━━━━━━━━\n{icon} <b>{title}</b>\n━━━━━━━━━━━━━━━\n{res_txt}━━━━━━━━━━━━━━━"
            kb = [[{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": data, "style": "success"}, {"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]
            edit_message(chat_id, msg_id, render_body_text(final_msg), reply_markup={"inline_keyboard": kb})

        except Exception as e:
            edit_message(chat_id, msg_id, render_body_text(f"❌ Error: {e}"), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]})

    elif data == "back_to_admin":
        if chat_id in user_states: del user_states[chat_id]
        edit_message(chat_id, msg_id, get_admin_text(), reply_markup=admin_panel_keyboard())

    elif data == "live_dashboard":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "live_dashboard", "style": "success"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, build_live_dashboard(), reply_markup=kb)

    elif data == "activity_heatmap":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "activity_heatmap", "style": "success"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, build_activity_heatmap(), reply_markup=kb)
        
    elif data == "system_settings":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['gear']} <b>System Settings</b>\nManage advanced bot configurations below:"), reply_markup=system_settings_keyboard())

    elif data == "nexa_control":
        edit_message(chat_id, msg_id, render_body_text(f"🌐 <b>Nexa Control Panel</b>\n\nTotal API Keys: {len(bot_settings.get('nexa_keys', []))}\nManage your Nexa API Keys below:"), reply_markup=nexa_control_keyboard())

    elif data == "add_nexa_key":
        user_states[chat_id] = "wait_for_add_nexa_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new Nexa API Key (e.g. nxa_...):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "nexa_control", "style": "danger"}]]})

    elif data == "view_nexa_keys":
        kb = []
        for idx, key in enumerate(bot_settings.get("nexa_keys", [])):
            safe_name = key[:10] + "..." if len(key)>10 else key
            kb.append([{"text": f"Delete {safe_name}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_nxa_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "nexa_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🗑 <b>Select Nexa Key to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_nxa_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("nexa_keys", [])):
            del bot_settings["nexa_keys"][idx]
            save_db()
            answer_callback(call["id"], "✅ Nexa Key Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "view_nexa_keys", "id": call["id"]})

    elif data == "nexa_search_country":
        kb = []
        for idx, c in enumerate(bot_settings.get("search_countries", [])):
            kb.append([{"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_sc_{idx}", "style": "danger"}])
        kb.append([{"text": "Add Country Code", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_search_country", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "nexa_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🌍 <b>Allowed Search Countries:</b>\nOnly these country codes will be allowed in Search Number."), reply_markup={"inline_keyboard": kb})

    elif data == "add_search_country":
        user_states[chat_id] = "wait_for_add_sc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Country Code (e.g. 880 or 92):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "nexa_search_country", "style": "danger"}]]})

    elif data.startswith("del_sc_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("search_countries", [])):
            del bot_settings["search_countries"][idx]
            save_db()
            answer_callback(call["id"], "✅ Country Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "nexa_search_country", "id": call["id"]})

    elif data == "manage_nexa_srv":
        kb = []
        srvs = bot_settings.get("nexa_services", {})
        apps_db = bot_settings.get("premium_apps", {})
        for srv in srvs:
            emoji_id = "5257969839313526622"
            for app_key, app_data in apps_db.items():
                if srv.upper() == app_key or srv.upper() in app_key or app_key in srv.upper():
                    if "id" in app_data:
                        emoji_id = app_data["id"]
                        break
            kb.append([{"text": f"{srv}", "icon_custom_emoji_id": emoji_id, "callback_data": f"nx_srv_{srv}", "style": "primary"}])
        kb.append([{"text": "Add New Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "nx_add_srv", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "nexa_control", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text("📦 <b>Nexa Services Manager</b>\nManage your API-based dynamic services below:"), reply_markup={"inline_keyboard": kb})

    elif data == "nx_add_srv":
        user_states[chat_id] = "wait_nx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter Service Name (e.g. TELEGRAM):"), reply_markup=get_cancel_kb())

    elif data.startswith("nx_srv_"):
        srv = data.replace("nx_srv_", "")
        kb = []
        countries = bot_settings["nexa_services"].get(srv, {})
        flags_db = bot_settings.get("premium_flags", {})
        for c in countries:
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                iso = flag_data.get("iso", "").upper()
                name = flag_data.get("name", "").upper()
                if c.upper() == iso or c.upper() == name or c.upper() in name or name in c.upper():
                    if "id" in flag_data:
                        emoji_id = flag_data["id"]
                        break
            kb.append([{"text": f"{c} ({len(countries[c])} Ranges)", "icon_custom_emoji_id": emoji_id, "callback_data": f"nx_cnt_{srv}_{c}", "style": "primary"}])
        kb.append([{"text": "Add Country", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"nx_add_cnt_{srv}", "style": "success"}])
        kb.append([{"text": "Delete Service", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"nx_del_srv_{srv}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_nexa_srv", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📂 <b>Service: {srv}</b>\nManage countries for this service:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("nx_add_cnt_"):
        srv = data.replace("nx_add_cnt_", "")
        user_states[chat_id] = "wait_nx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv}
        edit_message(chat_id, msg_id, render_body_text(f"🌍 Enter Country Name for <b>{srv}</b> (e.g. BD, INDIA):"), reply_markup=get_cancel_kb())

    elif data.startswith("nx_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        ranges = bot_settings["nexa_services"][srv].get(cnt, [])
        
        kb = []
        row = []
        for r in ranges:
            row.append({"text": f"Delete {r}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"nx_dr_{srv}_{cnt}_{r}", "style": "danger"})
            if len(row) == 2:
                kb.append(row)
                row = []
        if row: kb.append(row)
        
        kb.append([{"text": "Add Range", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"nx_addr_{srv}_{cnt}", "style": "success"}])
        kb.append([{"text": "Delete Entire Country", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"nx_del_cnt_{srv}_{cnt}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"nx_srv_{srv}", "style": "primary"}])
        
        txt = f"📍 <b>Service: {srv} | Country: {cnt}</b>\n\n<b>Total Ranges:</b> {len(ranges)}\n<i>Click on a range below to delete it, or add a new one.</i>"
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("nx_addr_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        user_states[chat_id] = "wait_nx_addr"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv, "cnt": cnt}
        edit_message(chat_id, msg_id, render_body_text(f"📝 Send the new Range for <b>{cnt}</b> (e.g. 88017):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"nx_cnt_{srv}_{cnt}", "style": "danger"}]]})

    elif data.startswith("nx_dr_"):
        parts = data.split("_")
        srv, cnt, rng = parts[2], parts[3], parts[4]
        if rng in bot_settings["nexa_services"].get(srv, {}).get(cnt, []):
            bot_settings["nexa_services"][srv][cnt].remove(rng)
            save_db()
            answer_callback(call["id"], f"✅ Range {rng} deleted!", show_alert=True)
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"nx_cnt_{srv}_{cnt}", "id": call["id"]})

    elif data.startswith("nx_del_srv_"):
        srv = data.replace("nx_del_srv_", "")
        if srv in bot_settings["nexa_services"]: del bot_settings["nexa_services"][srv]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_nexa_srv", "id": call["id"]})

    elif data.startswith("nx_del_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[3], parts[4]
        if cnt in bot_settings["nexa_services"].get(srv, {}): del bot_settings["nexa_services"][srv][cnt]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"nx_srv_{srv}", "id": call["id"]})

    elif data == "voltx_control":
        edit_message(chat_id, msg_id, render_body_text(f"⚡ <b>Voltx Control Panel</b>\n\nTotal API Keys: {len(bot_settings.get('voltx_keys', []))}\nManage your Voltx API Keys below:"), reply_markup=voltx_control_keyboard())

    elif data == "add_voltx_key":
        user_states[chat_id] = "wait_for_add_voltx_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new Voltx API Key:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "danger"}]]})

    elif data == "view_voltx_keys":
        kb = []
        for idx, key in enumerate(bot_settings.get("voltx_keys", [])):
            safe_name = key[:10] + "..." if len(key)>10 else key
            kb.append([{"text": f"Delete {safe_name}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_vtx_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🗑 <b>Select Voltx Key to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_vtx_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("voltx_keys", [])):
            del bot_settings["voltx_keys"][idx]
            save_db()
            answer_callback(call["id"], "✅ Voltx Key Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "view_voltx_keys", "id": call["id"]})

    elif data == "voltx_search_country":
        kb = []
        for idx, c in enumerate(bot_settings.get("voltx_search_countries", [])):
            kb.append([{"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_vsc_{idx}", "style": "danger"}])
        kb.append([{"text": "Add Country Code", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_voltx_search_country", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🌍 <b>Voltx Allowed Ranges:</b>\nOnly these ranges/codes will be allowed in Voltx Search Number."), reply_markup={"inline_keyboard": kb})

    elif data == "add_voltx_search_country":
        user_states[chat_id] = "wait_for_add_vsc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Voltx Range Code (e.g. 26134):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_search_country", "style": "danger"}]]})

    elif data.startswith("del_vsc_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("voltx_search_countries", [])):
            del bot_settings["voltx_search_countries"][idx]
            save_db()
            answer_callback(call["id"], "✅ Voltx Range Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "voltx_search_country", "id": call["id"]})

    elif data == "manage_voltx_srv":
        kb = []
        srvs = bot_settings.get("voltx_services", {})
        apps_db = bot_settings.get("premium_apps", {})
        for srv in srvs:
            emoji_id = "5257969839313526622"
            for app_key, app_data in apps_db.items():
                if srv.upper() == app_key or srv.upper() in app_key or app_key in srv.upper():
                    if "id" in app_data: emoji_id = app_data["id"]; break
            kb.append([{"text": f"{srv}", "icon_custom_emoji_id": emoji_id, "callback_data": f"vx_srv_{srv}", "style": "primary"}])
        kb.append([{"text": "Add New Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "vx_add_srv", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text("⚡ <b>Voltx Services Manager</b>\nManage your API-based dynamic services below:"), reply_markup={"inline_keyboard": kb})

    elif data == "vx_add_srv":
        user_states[chat_id] = "wait_vx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter Service Name (e.g. TELEGRAM):"), reply_markup=get_cancel_kb())

    elif data.startswith("vx_srv_"):
        srv = data.replace("vx_srv_", "")
        kb = []
        countries = bot_settings["voltx_services"].get(srv, {})
        flags_db = bot_settings.get("premium_flags", {})
        for c in countries:
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                iso = flag_data.get("iso", "").upper()
                name = flag_data.get("name", "").upper()
                if c.upper() == iso or c.upper() == name or c.upper() in name or name in c.upper():
                    if "id" in flag_data: emoji_id = flag_data["id"]; break
            kb.append([{"text": f"{c} ({len(countries[c])} Ranges)", "icon_custom_emoji_id": emoji_id, "callback_data": f"vx_cnt_{srv}_{c}", "style": "primary"}])
        kb.append([{"text": "Add Country", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"vx_add_cnt_{srv}", "style": "success"}])
        kb.append([{"text": "Delete Service", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"vx_del_srv_{srv}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_voltx_srv", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📂 <b>Service: {srv}</b>\nManage countries for this service:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("vx_add_cnt_"):
        srv = data.replace("vx_add_cnt_", "")
        user_states[chat_id] = "wait_vx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv}
        edit_message(chat_id, msg_id, render_body_text(f"🌍 Enter Country Name for <b>{srv}</b> (e.g. BD, INDIA):"), reply_markup=get_cancel_kb())

    elif data.startswith("vx_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        ranges = bot_settings["voltx_services"][srv].get(cnt, [])
        kb = []
        row = []
        for r in ranges:
            row.append({"text": f"Delete {r}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"vx_dr_{srv}_{cnt}_{r}", "style": "danger"})
            if len(row) == 2:
                kb.append(row)
                row = []
        if row: kb.append(row)
        kb.append([{"text": "Add Range", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"vx_addr_{srv}_{cnt}", "style": "success"}])
        kb.append([{"text": "Delete Entire Country", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"vx_del_cnt_{srv}_{cnt}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"vx_srv_{srv}", "style": "primary"}])
        txt = f"📍 <b>Service: {srv} | Country: {cnt}</b>\n\n<b>Total Ranges:</b> {len(ranges)}\n<i>Click on a range below to delete it, or add a new one.</i>"
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("vx_addr_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        user_states[chat_id] = "wait_vx_addr"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv, "cnt": cnt}
        edit_message(chat_id, msg_id, render_body_text(f"📝 Send the new Range for <b>{cnt}</b> (e.g. 26134):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"vx_cnt_{srv}_{cnt}", "style": "danger"}]]})

    elif data.startswith("vx_dr_"):
        parts = data.split("_")
        srv, cnt, rng = parts[2], parts[3], parts[4]
        if rng in bot_settings["voltx_services"].get(srv, {}).get(cnt, []):
            bot_settings["voltx_services"][srv][cnt].remove(rng)
            save_db()
            answer_callback(call["id"], f"✅ Range {rng} deleted!", show_alert=True)
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"vx_cnt_{srv}_{cnt}", "id": call["id"]})

    elif data.startswith("vx_del_srv_"):
        srv = data.replace("vx_del_srv_", "")
        if srv in bot_settings["voltx_services"]: del bot_settings["voltx_services"][srv]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_voltx_srv", "id": call["id"]})

    elif data.startswith("vx_del_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[3], parts[4]
        if cnt in bot_settings["voltx_services"].get(srv, {}): del bot_settings["voltx_services"][srv][cnt]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"vx_srv_{srv}", "id": call["id"]})

    elif data == "stex_live_ranges":
        kb = {"inline_keyboard": [
            [{"text": "🔄 Refresh", "callback_data": "stex_live_ranges", "style": "success"}],
            [{"text": "◀️ Back", "callback_data": "stex_control", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, get_stex_range_status(), reply_markup=kb)

    elif data == "stex_control":
        edit_message(chat_id, msg_id, render_body_text(f"🚀 <b>Stex Control Panel</b>\n\nTotal API Keys: {len(bot_settings.get('stex_keys', []))}\nManage your Stex API Keys below:"), reply_markup=stex_control_keyboard())

    elif data == "add_stex_key":
        user_states[chat_id] = "wait_for_add_stex_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new Stex API Key:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "danger"}]]})

    elif data == "view_stex_keys":
        kb = []
        for idx, key in enumerate(bot_settings.get("stex_keys", [])):
            safe_name = key[:10] + "..." if len(key)>10 else key
            kb.append([{"text": f"Delete {safe_name}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_stx_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🗑 <b>Select Stex Key to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_stx_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("stex_keys", [])):
            del bot_settings["stex_keys"][idx]
            save_db()
            answer_callback(call["id"], "✅ Stex Key Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "view_stex_keys", "id": call["id"]})

    elif data == "stex_search_country":
        kb = []
        for idx, c in enumerate(bot_settings.get("stex_search_countries", [])):
            kb.append([{"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_ssc_{idx}", "style": "danger"}])
        kb.append([{"text": "Add Country Code", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_stex_search_country", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🌍 <b>Stex Allowed Ranges:</b>\nOnly these ranges/codes will be allowed in Stex Search Number."), reply_markup={"inline_keyboard": kb})

    elif data == "add_stex_search_country":
        user_states[chat_id] = "wait_for_add_ssc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Stex Range Code (e.g. 26134):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_search_country", "style": "danger"}]]})

    elif data.startswith("del_ssc_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("stex_search_countries", [])):
            del bot_settings["stex_search_countries"][idx]
            save_db()
            answer_callback(call["id"], "✅ Stex Range Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "stex_search_country", "id": call["id"]})

    elif data == "manage_stex_srv":
        kb = []
        srvs = bot_settings.get("stex_services", {})
        apps_db = bot_settings.get("premium_apps", {})
        for srv in srvs:
            emoji_id = "5257969839313526622"
            for app_key, app_data in apps_db.items():
                if srv.upper() == app_key or srv.upper() in app_key or app_key in srv.upper():
                    if "id" in app_data: emoji_id = app_data["id"]; break
            kb.append([{"text": f"{srv}", "icon_custom_emoji_id": emoji_id, "callback_data": f"sx_srv_{srv}", "style": "primary"}])
        kb.append([{"text": "Add New Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "sx_add_srv", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text("🚀 <b>Stex Services Manager</b>\nManage your API-based dynamic services below:"), reply_markup={"inline_keyboard": kb})

    elif data == "sx_add_srv":
        user_states[chat_id] = "wait_sx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter Service Name (e.g. TELEGRAM):"), reply_markup=get_cancel_kb())

    elif data.startswith("sx_srv_"):
        srv = data.replace("sx_srv_", "")
        kb = []
        countries = bot_settings["stex_services"].get(srv, {})
        flags_db = bot_settings.get("premium_flags", {})
        for c in countries:
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                iso = flag_data.get("iso", "").upper()
                name = flag_data.get("name", "").upper()
                if c.upper() == iso or c.upper() == name or c.upper() in name or name in c.upper():
                    if "id" in flag_data: emoji_id = flag_data["id"]; break
            kb.append([{"text": f"{c} ({len(countries[c])} Ranges)", "icon_custom_emoji_id": emoji_id, "callback_data": f"sx_cnt_{srv}_{c}", "style": "primary"}])
        kb.append([{"text": "Add Country", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"sx_add_cnt_{srv}", "style": "success"}])
        kb.append([{"text": "Delete Service", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"sx_del_srv_{srv}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_stex_srv", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📂 <b>Service: {srv}</b>\nManage countries for this service:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("sx_add_cnt_"):
        srv = data.replace("sx_add_cnt_", "")
        user_states[chat_id] = "wait_sx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv}
        edit_message(chat_id, msg_id, render_body_text(f"🌍 Enter Country Name for <b>{srv}</b> (e.g. BD, INDIA):"), reply_markup=get_cancel_kb())

    elif data.startswith("sx_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        ranges = bot_settings["stex_services"][srv].get(cnt, [])
        kb = []
        row = []
        for r in ranges:
            row.append({"text": f"Delete {r}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"sx_dr_{srv}_{cnt}_{r}", "style": "danger"})
            if len(row) == 2:
                kb.append(row)
                row = []
        if row: kb.append(row)
        kb.append([{"text": "Add Range", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"sx_addr_{srv}_{cnt}", "style": "success"}])
        kb.append([{"text": "Delete Entire Country", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"sx_del_cnt_{srv}_{cnt}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"sx_srv_{srv}", "style": "primary"}])
        txt = f"📍 <b>Service: {srv} | Country: {cnt}</b>\n\n<b>Total Ranges:</b> {len(ranges)}\n<i>Click on a range below to delete it, or add a new one.</i>"
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("sx_addr_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        user_states[chat_id] = "wait_sx_addr"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv, "cnt": cnt}
        edit_message(chat_id, msg_id, render_body_text(f"📝 Send the new Range for <b>{cnt}</b>:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"sx_cnt_{srv}_{cnt}", "style": "danger"}]]})

    elif data.startswith("sx_dr_"):
        parts = data.split("_")
        srv, cnt, rng = parts[2], parts[3], parts[4]
        if rng in bot_settings["stex_services"].get(srv, {}).get(cnt, []):
            bot_settings["stex_services"][srv][cnt].remove(rng)
            save_db()
            answer_callback(call["id"], f"✅ Range {rng} deleted!", show_alert=True)
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"sx_cnt_{srv}_{cnt}", "id": call["id"]})

    elif data.startswith("sx_del_srv_"):
        srv = data.replace("sx_del_srv_", "")
        if srv in bot_settings["stex_services"]: del bot_settings["stex_services"][srv]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_stex_srv", "id": call["id"]})

    elif data.startswith("sx_del_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[3], parts[4]
        if cnt in bot_settings["stex_services"].get(srv, {}): del bot_settings["stex_services"][srv][cnt]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"sx_srv_{srv}", "id": call["id"]})



    elif data == "manage_fj":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "toggle_fj":
        bot_settings["fj_on"] = not bot_settings["fj_on"]
        save_db()
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "add_fj":
        user_states[chat_id] = "wait_for_add_fj"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send Channel Username or Invite Link:\n<i>(Note: For private channels, use the numeric ID like -100...)</i>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_fj", "style": "danger"}]]})

    elif data.startswith("del_fj_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fj_channels"]):
            del bot_settings["fj_channels"][idx]
            save_db()
            answer_callback(call["id"], "✅ Channel deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "manage_admins":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['user']} <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"), reply_markup=admin_settings_keyboard())

    elif data == "add_adm":
        user_states[chat_id] = "wait_for_add_adm"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID of the new Admin:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_admins", "style": "danger"}]]})

    elif data.startswith("del_adm_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["admins"]):
            del bot_settings["admins"][idx]
            save_db()
            answer_callback(call["id"], "✅ Admin deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"{PEM['user']} <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"), reply_markup=admin_settings_keyboard())

    elif data == "manage_otp_groups":
        edit_message(chat_id, msg_id, render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())

    elif data == "add_fw":
        user_states[chat_id] = "wait_for_add_fw_id"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Group ID/Username to forward messages to:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "danger"}]]})

    elif data.startswith("manage_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            grp_id = bot_settings["fw_groups"][idx]["chat_id"]
            edit_message(chat_id, msg_id, render_body_text(f"🛡 <b>Manage Group:</b> {grp_id}"), reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("add_fwbtn_"):
        idx = int(data.split("_")[2])
        user_states[chat_id] = "wait_for_add_fw_btn"
        temp_data[chat_id] = {"msg_id": msg_id, "fw_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send Custom Inline Button format:\n<code>Button Text - https://link.com</code>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_fw_{idx}", "style": "danger"}]]})

    elif data.startswith("del_fwbtn_"):
        parts = data.split("_")
        idx, b_idx = int(parts[2]), int(parts[3])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            if 0 <= b_idx < len(bot_settings["fw_groups"][idx]["buttons"]):
                del bot_settings["fw_groups"][idx]["buttons"][b_idx]
                save_db()
                answer_callback(call["id"], "✅ Button deleted!", show_alert=True)
                edit_message(chat_id, msg_id, render_body_text(f"🛡 <b>Manage Group:</b> {bot_settings['fw_groups'][idx]['chat_id']}"), reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("del_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            del bot_settings["fw_groups"][idx]
            save_db()
            answer_callback(call["id"], "✅ Group deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())

    elif data.startswith("test_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("fw_groups", [])):
            grp_id = bot_settings["fw_groups"][idx]["chat_id"]
            try:
                res = send_message(grp_id, render_body_text(
                    "┏━━━━━━━━━━━━━━━┓\n"
                    "┃ 📘  WHATSAPP OTP  📘\n"
                    "┗━━━━━━━━━━━━━━━┛\n"
                    "🇧🇩 #BD ➡️ 880 『𝐄𝐗𝐄』 001 #EN\n"
                    f"🕐 {bdt_str()}\n\n"
                    "<i>If you see this, group is working ✅</i>"
                ), reply_markup={"inline_keyboard": [[
                    {"text": "📋 123456", "copy_text": {"text": "123456"}, "style": "success"}
                ]]})
                if res.get("ok"):
                    answer_callback(call["id"], "✅ Test message sent to group!", show_alert=True)
                else:
                    err = res.get("description", "Unknown error")
                    answer_callback(call["id"], f"❌ Failed: {err}", show_alert=True)
            except Exception as e:
                answer_callback(call["id"], f"❌ Error: {str(e)}", show_alert=True)

    elif data == "edit_otp_link":
        user_states[chat_id] = "wait_for_otp_link"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new OTP Group Link:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "danger"}]]})

    elif data == "manage_panels":
        api_count = len([p for p in bot_settings["panels"] if p.get("type") == "API Panel"])
        cpt_count = len([p for p in bot_settings["panels"] if p.get("type", "API Panel") == "Auto Captcha Panel"])
        text = f"{PEM['gear']} <b>Panel Management</b>\n\nSelect which type of panel system you want to manage:"
        kb = {"inline_keyboard": [
            [{"text": f"Manage API Panels ({api_count})", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "manage_api_panels", "style": "primary"}],
            [{"text": f"Manage Auto Captcha Panels ({cpt_count})", "icon_custom_emoji_id": "5353022963132174959", "callback_data": "manage_cpt_panels", "style": "success"}],
            [{"text": "Back to System", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, render_body_text(text), reply_markup=kb)

    elif data in ["manage_api_panels", "manage_cpt_panels"]:
        p_type = "API Panel" if data == "manage_api_panels" else "Auto Captcha Panel"
        p_list = [p for p in bot_settings["panels"] if p.get("type", "API Panel") == p_type]
        icon = f"{PEM['world']} API" if p_type == 'API Panel' else f"{PEM['lock']} Auto Captcha"
        
        text = f"{icon} <b>{p_type}s Management</b>\n\n👀 <b>Active Monitors:</b> {len(p_list)}\n\n🟢 <b>Available Providers:</b>\n"
        for p in p_list:
            status = "Monitoring" if p['status'] == 'ON' else "Stopped"
            login_state = p.get('login_status', '')
            if p['type'] == 'Auto Captcha Panel':
                conf = f" {login_state}" if login_state else f"{PEM['ok']} Configured"
            else:
                conf = f"{PEM['ok']} Configured" if p.get('api_url') else f"{PEM['no']} Not Configured"
            text += f"• {p['name']}: {PEM['ok'] if p['status']=='ON' else PEM['no']} {status} | {conf}\n"
        edit_message(chat_id, msg_id, render_body_text(text), reply_markup=typed_panels_list_keyboard(p_type))

    elif data in ["add_api_panel", "add_cpt_panel"]:
        user_states[chat_id] = "wait_for_panel_name"
        p_type = "api" if data == "add_api_panel" else "logc"
        temp_data[chat_id] = {"msg_id": msg_id, "add_type": p_type}
        edit_message(chat_id, msg_id, render_body_text("📝 Please send the name of the New Provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_{'api' if p_type=='api' else 'cpt'}_panels", "style": "danger"}]]})

    elif data.startswith("add_ptype_"):
        pass

    elif data in ["list_del_api", "list_del_cpt"]:
        p_type = "API Panel" if data == "list_del_api" else "Auto Captcha Panel"
        kb = []
        for idx, p in enumerate(bot_settings["panels"]):
            if p.get("type", "API Panel") == p_type:
                kb.append([{"text": f"Delete {p['name']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"do_del_pnl_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_{'api' if p_type=='API Panel' else 'cpt'}_panels", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['trash']} <b>Select a Provider to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("do_del_pnl_"):
        idx = int(data.split("_")[3])
        if 0 <= idx < len(bot_settings["panels"]):
            p_type = bot_settings["panels"][idx].get("type", "API Panel")
            del bot_settings["panels"][idx]
            save_db()
            answer_callback(call["id"], "✅ Provider Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"manage_{'api' if p_type=='API Panel' else 'cpt'}_panels", "id": "internal"})

    elif data.startswith("tog_pnl_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["panels"]):
            p = bot_settings["panels"][idx]
            
            p["status"] = "ON" if p["status"] == "OFF" else "OFF"
            save_db()
            
            if p["type"] == "Auto Captcha Panel":
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>Login Status:</b> {p.get('login_status', 'Unknown')}\n<b>Login URL:</b> <code>{p.get('login_url', 'None')}</code>\n<b>User:</b> <code>{p.get('username', 'None')}</code>"
            else:
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
            edit_message(chat_id, msg_id, render_body_text(text), reply_markup=panel_config_keyboard(idx))

    elif data.startswith("conf_pnl_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["panels"]):
            p = bot_settings["panels"][idx]
            if p["type"] == "Auto Captcha Panel":
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>Login Status:</b> {p.get('login_status', 'Unknown')}\n<b>Login URL:</b> <code>{p.get('login_url', 'None')}</code>\n<b>User:</b> <code>{p.get('username', 'None')}</code>\n<b>Num Col:</b> {p.get('num_col_name')} (Idx: {p.get('num_col_idx')})\n<b>Msg Col:</b> {p.get('msg_col_name')} (Idx: {p.get('msg_col_idx')})"
            else:
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>\n<b>Full API URL:</b> <code>{p.get('full_api_url', 'None')}</code>"
            edit_message(chat_id, msg_id, render_body_text(text), reply_markup=panel_config_keyboard(idx))

    elif data.startswith("set_p_api_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_api"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the API URL for this provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_tok_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_tok"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Token for this provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_fapi_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_fapi"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the FULL API URL (Example: http://api.com/get?key=YOUR_TOKEN&start=0):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_rec_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_rec"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the number of records to fetch (e.g. 10).\nType <code>0</code> for Unlimited:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("test_p_conn_"):
        idx = int(data.split("_")[3])
        p = bot_settings["panels"][idx]
        wait_msg = send_message(chat_id, render_body_text("⏳ Testing connection. Please wait..."))
        wait_msg_id = wait_msg.get("result", {}).get("message_id") if wait_msg else None
        answer_callback(call["id"])
        
        try:
            parsed = []
            raw_text = ""
            
            if p["type"] == "Auto Captcha Panel":
                sess = panel_sessions.get(idx)
                if not sess:
                    success = attempt_auto_login(p, idx)
                    if not success:
                        if wait_msg_id: delete_message(chat_id, wait_msg_id)
                        send_message(chat_id, render_body_text(f"❌ <b>Auto Login Failed!</b>\nReason: {html.escape(str(p.get('login_status', 'Unknown')))}"))
                        return
                    sess = panel_sessions.get(idx)
                    
                login_url = p.get("login_url", "").strip()
                if not login_url.startswith("http"): login_url = "http://" + login_url
                msg_link = p.get("msg_link", "").strip()
                if not msg_link.startswith("http") and msg_link != "": msg_link = "http://" + msg_link
                check_url = msg_link if msg_link else f"{login_url.split('/login')[0]}/client/SMSCDRStats"
                
                # 🌟 test connection supports sAjaxSource & HTML table parser
                parsed, raw_text = fetch_cpt_panel_cdrs(p, sess, check_url)
                
            else:
                full_url = p.get("full_api_url", "").strip()
                url = p.get("api_url", "").strip()
                token = p.get("token", "").strip()
                if not full_url and not url:
                    if wait_msg_id: delete_message(chat_id, wait_msg_id)
                    send_message(chat_id, render_body_text("❌ Please Set API URL or Full API URL first!"))
                    return
                
                urls_to_try = []
                if full_url:
                    urls_to_try.append(full_url)
                else:
                    if "{token}" in url or "{key}" in url:
                        urls_to_try.append(url.replace("{token}", token).replace("{key}", token))
                    elif "token=" in url or "key=" in url:
                        urls_to_try.append(url)
                    else:
                        sep = '&' if '?' in url else '?'
                        urls_to_try.append(f"{url}{sep}token={token}")
                        urls_to_try.append(f"{url}{sep}key={token}&start=0")
                        urls_to_try.append(f"{url}{sep}key={token}")
                    
                parsed = []
                raw_text = ""
                base_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                
                # Stex API: mauthapi header দিয়ে call করতে হয়
                is_stex = "2oo9.cloud" in (full_url or url) and "tness" in (full_url or url)
                is_voltx = "2oo9.cloud" in (full_url or url) and "tnevs" in (full_url or url)
                
                if is_stex or is_voltx:
                    # token: panel token field অথবা stex_keys/voltx_keys list থেকে নাও
                    auth_token = token
                    if not auth_token:
                        key_list = bot_settings.get("stex_keys" if is_stex else "voltx_keys", [])
                        if key_list:
                            auth_token = key_list[0]
                    
                    if not auth_token:
                        if wait_msg_id: delete_message(chat_id, wait_msg_id)
                        send_message(chat_id, render_body_text(f"❌ No token found!\n\nPlease set token via <b>Set Token</b> button, or add a key in Stex Control."))
                        return
                    
                    # Stex/Voltx: header-based auth, fixed endpoint
                    stex_url = full_url or f"https://api.2oo9.cloud/MXS47FLFX0U/{'tness' if is_stex else 'tnevs'}/@public/api/success-otp"
                    stex_headers = {**base_headers, "mauthapi": auth_token}
                    try:
                        res = stex_get(stex_url, headers=stex_headers)
                        raw_text = res.text
                        resp_json = res.json()
                        if resp_json.get("meta", {}).get("code") == 200:
                            otps = resp_json.get("data", {}).get("otps", [])
                            for item in otps:
                                num = re.sub(r'\D', '', str(item.get("number", "")))
                                msg_text = str(item.get("message", ""))
                                otp = extract_otp_code(msg_text)
                                if num and msg_text and otp:
                                    parsed.append({"number": num, "message": msg_text, "otp": otp})
                        else:
                            # Error message দেখাও
                            err_msg = resp_json.get("message", "Unknown error")
                            err_code = resp_json.get("meta", {}).get("code", "?")
                            if wait_msg_id: delete_message(chat_id, wait_msg_id)
                            send_message(chat_id, render_body_text(f"❌ <b>API Error {err_code}:</b> {html.escape(str(err_msg))}\n\nToken used: <code>{auth_token[:8]}...</code>"))
                            return
                    except Exception as e:
                        if wait_msg_id: delete_message(chat_id, wait_msg_id)
                        send_message(chat_id, render_body_text(f"❌ <b>Connection Error:</b> {html.escape(str(e))}"))
                        return
                else:
                    for try_url in urls_to_try:
                        try:
                            res = stex_get(try_url, headers=base_headers)
                            raw_text = res.text
                            parsed = parse_panel_response(raw_text, p)
                            if parsed:
                                if not full_url and try_url != url and token:
                                    p["api_url"] = try_url.replace(token, "{token}")
                                    save_db()
                                break
                        except: pass
                 
            if wait_msg_id: delete_message(chat_id, wait_msg_id)
                 
            if parsed:
                txt = f"✅ <b>Connection Successful!</b>\n\n🎯 <b>Parsed Data Sample (Max 3):</b>\n\n"
                
                for i, sample in enumerate(parsed[:3]):
                    num = sample['number']
                    msg = sample['message']
                    otp = sample['otp']
                    
                    detected_app = detect_service(msg)
                    app_name = detected_app if detected_app else p.get("name", "Unknown")
                    app_full_name, prem_app_html = get_service_info_html(app_name, msg)
                    
                    txt += f"<b>{i+1}.</b> {prem_app_html} <b>{app_full_name}</b>\n"
                    txt += f"📱 Number: <code>{num}</code>\n"
                    txt += f"📝 Full Msg: <code>{html.escape(msg)}</code>\n"
                    txt += f"🔐 OTP: <code>{otp}</code>\n"
                    txt += "➖" * 12 + "\n"
                    
                send_message(chat_id, render_body_text(txt))
            else:
                if p["type"] == "Auto Captcha Panel":
                    try:
                        soup = BeautifulSoup(raw_text, 'html.parser')
                        tables = soup.find_all('table')
                        if tables:
                            full_table_data = "🔍 FULL TABLE DATA (A-Z)\n" + "="*50 + "\n\n"
                            for t_idx, table in enumerate(tables):
                                full_table_data += f"--- Table {t_idx+1} ---\n"
                                rows = table.find_all('tr')
                                for r_idx, row in enumerate(rows):
                                    cols = row.find_all(['th', 'td'])
                                    col_texts = [f"[{c_idx+1}] {c.get_text(separator=' ', strip=True)}" for c_idx, c in enumerate(cols)]
                                    full_table_data += f"Row {r_idx+1}: {' | '.join(col_texts)}\n"
                                full_table_data += "\n" + "="*50 + "\n"
                            
                            send_document(chat_id, f"Full_Panel_Data_{idx}.txt", full_table_data.encode('utf-8'))
                            fail_txt = f"⚠️ <b>Connected, but couldn't parse OTP data!</b>\n\n<i>আমি ওই লিংকের সম্পূর্ণ (A-Z) ডাটা একটি Text File এ পাঠিয়েছি। ফাইলটি ওপেন করে সঠিক Column Number (যেমন: [1], [3]) চেক করে প্যানেলে আপডেট করে নাও।</i>"
                            send_message(chat_id, render_body_text(fail_txt))
                        else:
                            send_message(chat_id, render_body_text(f"⚠️ <b>Connected, but no HTML Table found!</b>\nMake sure the message link is correct."))
                    except Exception as e:
                        send_message(chat_id, render_body_text(f"❌ <b>Error parsing HTML:</b> {html.escape(str(e))}"))
                else:
                    safe_html = html.escape(str(raw_text)[:300])
                    send_message(chat_id, render_body_text(f"⚠️ <b>Connected, but couldn't find/parse OTP data.</b>\n\n<i>Make sure your API config is correct.</i>\n\nRaw HTML/Data (excerpt):\n<code>{safe_html}...</code>"))
        except Exception as e:
            if wait_msg_id: delete_message(chat_id, wait_msg_id)
            send_message(chat_id, render_body_text(f"❌ <b>Connection Failed!</b>\nError: {html.escape(str(e))}"))

    elif data == "manage_visible_services":
        visible = bot_settings.get("visible_services", [])
        # Get all available services
        all_srvs = set()
        all_srvs.update(bot_settings.get("nexa_services", {}).keys())
        all_srvs.update(bot_settings.get("voltx_services", {}).keys())
        all_srvs.update(bot_settings.get("stex_services", {}).keys())
        all_srvs.update([b["service"] for b in number_batches.values() if b.get("numbers")])

        apps_db = bot_settings.get("premium_apps", {})
        kb = []
        for s in sorted(all_srvs):
            s_up    = s.upper()
            is_vis  = not visible or s_up in [v.upper() for v in visible]
            emoji_id = "5352694861990501856"
            for app_key, app_data in apps_db.items():
                if s_up == app_key or s_up in app_key or app_key in s_up:
                    emoji_id = app_data.get("id", emoji_id)
                    break
            status = "✅" if is_vis else "🔴"
            kb.append([{"text": f"{status} {s}", "icon_custom_emoji_id": emoji_id,
                        "callback_data": f"toggle_service_vis_{s}", "style": "success" if is_vis else "danger"}])
        kb.append([{"text": "✅ Show ALL Services", "callback_data": "show_all_services", "style": "success"}])
        kb.append([{"text": "◀️ Back", "callback_data": "system_settings", "style": "danger"}])
        status_txt = "All services visible" if not visible else f"Showing: {', '.join(visible)}"
        edit_message(chat_id, msg_id, render_body_text(
            f"📱 <b>Visible Services Control</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Control which services users can see.\n"
            f"Current: <b>{status_txt}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Tap to toggle ON/OFF:"
        ), reply_markup={"inline_keyboard": kb})

    elif data.startswith("toggle_service_vis_"):
        srv = data.split("toggle_service_vis_")[1].upper()
        visible = [v.upper() for v in bot_settings.get("visible_services", [])]
        if not visible:
            # Currently showing all — build full list except this one
            all_srvs = set()
            all_srvs.update(bot_settings.get("nexa_services", {}).keys())
            all_srvs.update(bot_settings.get("voltx_services", {}).keys())
            all_srvs.update(bot_settings.get("stex_services", {}).keys())
            all_srvs.update([b["service"] for b in number_batches.values() if b.get("numbers")])
            visible = [s.upper() for s in all_srvs if s.upper() != srv]
        elif srv in visible:
            visible.remove(srv)
        else:
            visible.append(srv)
        bot_settings["visible_services"] = visible
        save_db()
        answer_callback(call["id"], f"{'✅ Enabled' if srv in visible else '🔴 Hidden'}: {srv}")
        handle_callback({"message": call["message"], "data": "manage_visible_services", "id": call["id"]})

    elif data == "show_all_services":
        bot_settings["visible_services"] = []
        save_db()
        answer_callback(call["id"], "✅ All services now visible!", show_alert=True)
        handle_callback({"message": call["message"], "data": "manage_visible_services", "id": call["id"]})

    elif data == "manage_service_rewards":
        rewards = bot_settings.get("service_rewards", {})
        if not rewards:
            reward_lines = "<i>No custom rewards set.\nGlobal reward applies to all services.</i>"
        else:
            reward_lines = ""
            for svc, amt in rewards.items():
                reward_lines += f"📱 <b>{svc}</b>: <code>{amt:.2f} ৳</code>\n"
        kb = {"inline_keyboard": [
            [{"text": "➕ Add/Edit Service Reward", "callback_data": "add_service_reward", "style": "success"}],
            [{"text": "🗑 Remove All Custom Rewards", "callback_data": "clear_service_rewards", "style": "danger"}],
            [{"text": "◀️ Back", "callback_data": "prime_control", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, render_body_text(
            f"💰 <b>Custom Reward Per Service</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🌐 Global OTP Reward: <b>{bot_settings.get('otp_reward', 0.1):.2f} ৳</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{reward_lines}"
            f"━━━━━━━━━━━━━━━\n"
            f"🕐 {bdt_str()}"
        ), reply_markup=kb)

    elif data == "add_service_reward":
        user_states[chat_id] = "wait_service_reward_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            f"📲 <b>Add Custom Reward</b>\n\n"
            f"Enter service name (e.g. INSTAGRAM, WHATSAPP):"
        ), reply_markup={"inline_keyboard": [[{"text": "◀️ Cancel", "callback_data": "manage_service_rewards", "style": "danger"}]]})

    elif data == "clear_service_rewards":
        bot_settings["service_rewards"] = {}
        save_db()
        answer_callback(call["id"], "✅ All custom rewards cleared!", show_alert=True)
        handle_callback({"message": call["message"], "data": "manage_service_rewards", "id": call["id"]})

    elif data == "prime_control":
        if chat_id in user_states: del user_states[chat_id]
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>"), reply_markup=prime_control_keyboard())

    elif data == "prime_toggle_w":
        bot_settings["withdraw_on"] = not bot_settings["withdraw_on"]
        save_db()
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>"), reply_markup=prime_control_keyboard())

    elif data == "prime_toggle_auto":
        bot_settings["auto_traffic_on"] = not bot_settings.get("auto_traffic_on", True)
        save_db()
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>"), reply_markup=prime_control_keyboard())

    elif data == "manage_w_methods":
        edit_message(chat_id, msg_id, render_body_text("💳 <b>WITHDRAWAL METHODS</b>\n\nManage your withdrawal methods below:"), reply_markup=w_methods_keyboard())

    elif data == "add_wm":
        user_states[chat_id] = "wait_for_add_wm"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the name of the new Withdrawal Method:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_w_methods", "style": "danger"}]]})

    elif data.startswith("del_wm_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["w_methods"]):
            del bot_settings["w_methods"][idx]
            save_db()
            answer_callback(call["id"], "✅ Method deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text("💳 <b>WITHDRAWAL METHODS</b>\n\nManage your withdrawal methods below:"), reply_markup=w_methods_keyboard())

    elif data == "prime_toggle_onboard":
        bot_settings["onboarding_on"] = not bot_settings.get("onboarding_on", True)
        save_db()
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>PRIME CONTROL PANEL</b>"), reply_markup=prime_control_keyboard())

    elif data.startswith("prime_"):
        key = data.replace("prime_", "")
        key_map = {"min_w": "min_withdraw", "otp_r": "otp_reward", "ref_r": "refer_reward", "cool": "cooldown", "num_req": "num_req", "num_share": "num_share", "sup_link": "support_link", "w_group": "w_group", "ref_comm": "referral_commission", "auto_int": "auto_traffic_interval", "num_expiry": "number_expiry_minutes"}
        if key in key_map:
            temp_data[chat_id] = {"msg_id": msg_id, "key": key_map[key]}
            user_states[chat_id] = "set_prime"
            cancel_kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_prime_edit", "style": "danger"}]]}
            edit_message(chat_id, msg_id, render_body_text(f"📝 Please send the new value for <code>{key_map[key]}</code>:"), reply_markup=cancel_kb)
            answer_callback(call["id"])



    elif data.startswith("g_s_"):
        service   = data.split("g_s_")[1]
        local_cnts = set([b["country"] for b in number_batches.values() if b["service"] == service and b["numbers"]])
        nexa_cnts  = set(bot_settings.get("nexa_services",  {}).get(service, {}).keys())
        voltx_cnts = set(bot_settings.get("voltx_services", {}).get(service, {}).keys())
        stex_cnts  = set(bot_settings.get("stex_services",  {}).get(service, {}).keys())
        all_countries = local_cnts | nexa_cnts | voltx_cnts | stex_cnts

        c_msg   = bot_settings["custom_messages"].get("select_country", {})
        raw_txt = c_msg.get("text", "📌 Select a country:").replace("{service}", service)
        txt     = render_body_text(raw_txt)

        flags_db = bot_settings.get("premium_flags", {})

        # Traffic count per ISO (last 1h)
        now_t = time.time()
        iso_traffic = Counter(
            t.get("iso", "XX") for t in recent_traffic
            if now_t - t.get("time", 0) <= 3600
        )

        def resolve_country(c):
            """Returns (iso, full_name, emoji_id, traffic_count) for a country key."""
            c_up = c.upper().strip()
            # 1. Try exact ISO match
            for flag_code, fd in flags_db.items():
                fd_iso  = fd.get("iso", "").upper()
                fd_name = fd.get("name", "").upper()
                if c_up == fd_iso or c_up == fd_name:
                    iso = fd.get("iso", c_up)
                    return (iso, fd.get("name", c.title()),
                            fd.get("id", "5780471598922337683"),
                            iso_traffic.get(iso, 0))
            # 2. Try partial name match
            for flag_code, fd in flags_db.items():
                fd_name = fd.get("name", "").upper()
                if c_up in fd_name or fd_name in c_up:
                    iso = fd.get("iso", c_up)
                    return (iso, fd.get("name", c.title()),
                            fd.get("id", "5780471598922337683"),
                            iso_traffic.get(iso, 0))
            # 3. Fallback
            return (c_up, c.title(), "5780471598922337683", iso_traffic.get(c_up, 0))

        # Build sorted list (high traffic first), deduplicating by resolved ISO
        seen_isos = set()
        country_list = []
        for c in all_countries:
            iso, full_name, emoji_id, traf = resolve_country(c)
            if iso in seen_isos:
                continue   # skip duplicate (same country stored as both ISO and full name)
            seen_isos.add(iso)
            country_list.append((c, iso, full_name, emoji_id, traf))
        country_list.sort(key=lambda x: x[4], reverse=True)

        kb = []
        for (c, iso, full_name, emoji_id, traf) in country_list:
            if traf >= 5:   badge = " 🔥"
            elif traf >= 2: badge = " ⚡"
            elif traf >= 1: badge = " ✅"
            else:           badge = ""
            kb.append([{"text": f"{full_name}{badge}",
                        "icon_custom_emoji_id": emoji_id,
                        "callback_data": f"g_c_{service}_{c}",
                        "style": "success"}])

        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                    "callback_data": "close_msg", "style": "danger"}])
        edit_message(chat_id, msg_id, txt, reply_markup={"inline_keyboard": kb})

    elif data.startswith("g_c_") or data.startswith("c_n_"):
        # ১. গ্লোবাল কুলডাউন চেক (সকল নাম্বার মেথডের জন্য)
        now = time.time()
        if now - user_cooldowns.get(chat_id, 0) < bot_settings["cooldown"]:
            answer_callback(call["id"], f"⌛ Please wait {int(bot_settings['cooldown'] - (now - user_cooldowns.get(chat_id, 0)))}s.", show_alert=True)
            return
        
        # কুলডাউন আপডেট
        user_cooldowns[chat_id] = now

        # 🌟 Already has active number? Block unless Change Number button
        if chat_id in user_active_sessions and not data.startswith("c_n_"):
            exp_ts = number_expiry_tracker.get(chat_id, 0)
            remaining = int(exp_ts - time.time()) if exp_ts > time.time() else 0
            if remaining > 0:
                answer_callback(call["id"],
                    f"⚠️ You already have an active number!\nWait {remaining}s for it to expire first.",
                    show_alert=True)
                return

        # আগের নাম্বার এক্সপায়ার করা (only on Change Number)
        if data.startswith("c_n_"):
            expire_previous_number(chat_id)

        # যদি সার্চ নাম্বার থেকে আসে
        if data.startswith("c_n_s_"):
            is_voltx_req = data.endswith("_vtx")
            is_stex_req = data.endswith("_stx")
            clean_data = data[:-4] if (is_voltx_req or is_stex_req) else data
            parts_s = clean_data.split("_", 4)
            
            query = parts_s[3] if len(parts_s) > 3 else ""
            service_from_cb = parts_s[4] if len(parts_s) > 4 else None
            
            allowed_countries = bot_settings.get("search_countries", [])
            voltx_allowed = bot_settings.get("voltx_search_countries", [])
            stex_allowed = bot_settings.get("stex_search_countries", [])
            
            is_nexa_allowed = any(query.startswith(c) for c in allowed_countries) if allowed_countries else False
            is_voltx_allowed = any(query.startswith(c) for c in voltx_allowed) if voltx_allowed else False
            is_stex_allowed = any(query.startswith(c) for c in stex_allowed) if stex_allowed else False
            
            if not is_voltx_req and not is_stex_req and not is_nexa_allowed and not is_voltx_allowed and not is_stex_allowed:
                answer_callback(call["id"], "❌ This country code is not allowed for search!", show_alert=True)
                return
                
            edit_message(chat_id, msg_id, render_body_text("⌛ <i>Processing... Finding Number...</i>"))
            wait_msg_id = msg_id
            
            found_indices = []
            for b_id, b_data in number_batches.items():
                for idx, n_obj in enumerate(b_data["numbers"]):
                    if n_obj["num"].replace("+", "").startswith(query) and chat_id not in n_obj.get("used_by", []):
                        found_indices.append((b_id, idx))
            
            fetched_nums = []
            if not found_indices:
                api_found = False
                if is_voltx_req:
                    voltx_keys = bot_settings.get("voltx_keys", [])
                    for _ in range(bot_settings.get("num_req", 1)):
                        for api_key in voltx_keys:
                            try:
                                headers = {"mauthapi": api_key}
                                payload = {"rid": query}
                                res = stex_post(f"{VOLTX_BASE_URL}/getnum", json_data=payload, headers=headers)
                                resp_data = res.json()
                                if resp_data.get("meta", {}).get("code") == 200 and resp_data.get("data"):
                                    num_str = str(resp_data["data"].get("no_plus_number", "")).replace("+", "")
                                    if not num_str: num_str = str(resp_data["data"].get("national_number", ""))
                                    fetched_nums.append(num_str)
                                    voltx_assigned_numbers[num_str] = chat_id 
                                    api_found = True
                                    total_assigned_stats += 1
                                    break
                            except: continue
                elif is_stex_req or is_stex_allowed:
                    stex_keys = bot_settings.get("stex_keys", [])
                    for _ in range(bot_settings.get("num_req", 1)):
                        if len(fetched_nums) >= bot_settings.get("num_req", 1): break
                        for api_key in stex_keys:
                            try:
                                headers = {"mauthapi": api_key}
                                payload = {"rid": query}
                                res = stex_post(f"{STEX_BASE_URL}/getnum", json_data=payload, headers=headers)
                                resp_data = res.json()
                                if resp_data.get("meta", {}).get("code") == 200 and resp_data.get("data"):
                                    num_str = str(resp_data["data"].get("no_plus_number", "")).replace("+", "")
                                    if not num_str: num_str = str(resp_data["data"].get("national_number", ""))
                                    fetched_nums.append(num_str)
                                    stex_assigned_numbers[num_str] = chat_id 
                                    api_found = True
                                    total_assigned_stats += 1
                                    break
                            except: continue
                else:
                    nexa_keys = bot_settings.get("nexa_keys", [])
                    search_range = query + ("X" * (11 - len(query))) if len(query) < 11 else query
                    
                    for _ in range(bot_settings.get("num_req", 1)):
                        for api_key in nexa_keys:
                            try:
                                headers = {"X-API-Key": api_key}
                                res = requests.post(f"{NEXA_BASE_URL}/api/v1/numbers/get", json={"range": search_range, "format": "normal"}, headers=headers, timeout=10)
                                resp_data = res.json()
                                if resp_data.get("success") and resp_data.get("number"):
                                    num_str = str(resp_data["number"]).replace("+", "")
                                    number_id = resp_data.get("number_id")
                                    fetched_nums.append(num_str)
                                    nexa_assigned_numbers[num_str] = chat_id 
                                    api_found = True
                                    total_assigned_stats += 1
                                    if number_id:
                                        threading.Thread(target=poll_otp_with_status, args=(number_id, num_str, chat_id, api_key), daemon=True).start()
                                    break
                            except: continue


                if not api_found:
                    answer_callback(call["id"], "❌ Number out of stock!", show_alert=True)
                    delete_message(chat_id, wait_msg_id)
                    return
                save_db()
            else:
                random.shuffle(found_indices)
                for b_id, idx in found_indices:
                    if len(fetched_nums) >= bot_settings.get("num_req", 1): break
                    n_obj = number_batches[b_id]["numbers"][idx]
                    num_str = n_obj["num"]
                    fetched_nums.append(num_str)
                    n_obj["shares"] += 1
                    n_obj["used_by"].append(chat_id)
                    total_assigned_stats += 1
                    if n_obj["shares"] >= bot_settings.get("num_share", 1):
                        n_obj["to_remove"] = True
                        used_numbers_list.append(num_str)
                for b_id in number_batches:
                    number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
                save_db()
                
            kb = []
            if service_from_cb:
                app_full_name, _ = get_service_info_html(service_from_cb)
                emoji_id_srv = "5337302974806922068"
                for app_key, app_data in bot_settings.get("premium_apps", {}).items():
                    if service_from_cb.upper() == app_key or service_from_cb.upper() in app_key or app_key in service_from_cb.upper():
                        if "id" in app_data: emoji_id_srv = app_data["id"]; break
                kb.append([{"text": f"{app_full_name}", "icon_custom_emoji_id": emoji_id_srv, "callback_data": "ignore", "style": "success"}])

            flags_db = bot_settings.get("premium_flags", {})
            for num in fetched_nums:
                _, iso = get_flag_and_code(num)
                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                c_name   = get_country_full_name(iso)
                flag_html = get_flag_info_html(iso)
                emoji_id = "5780471598922337683"
                for flag_code, flag_data in flags_db.items():
                    if iso == flag_data.get("iso"):
                        if "id" in flag_data: emoji_id = flag_data["id"]; break
                masked_disp = mask_number(display_num)
                kb.append([{"text": f"{c_name}  {masked_disp}", "icon_custom_emoji_id": emoji_id, "copy_text": {"text": display_num}, "style": "primary"}])
            
            vtx_ext = "_vtx" if is_voltx_req else ""
            stx_ext = "_stx" if is_stex_req or is_stex_allowed else ""
            ext = stx_ext or vtx_ext
            srv_ext = f"_{service_from_cb}" if service_from_cb else ""
            kb.append([{"text": "🔄 Change Number", "icon_custom_emoji_id": "6233525120334306978",
                        "callback_data": f"c_n_s_{query}{srv_ext}{ext}", "style": "danger"},
                       {"text": "📢 OTP Group", "icon_custom_emoji_id": "6233384966961502838",
                        "url": bot_settings["otp_link"], "style": "primary"}])
            
            c_btns = bot_settings["custom_messages"].get("search_number", {}).get("buttons", [])
            for c_b in c_btns: 
                b_copy = c_b.copy()
                if "style" not in b_copy: b_copy["style"] = "primary"
                kb.append([b_copy])
            kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
            
            edit_message(chat_id, wait_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
            user_active_sessions[chat_id] = {"msg_id": wait_msg_id, "nums": fetched_nums}
            # 🌟 Send OTP waiting status message
            exp_ts = number_expiry_tracker.get(chat_id, time.time() + 600)
            service_label = service_from_cb if service_from_cb else query
            if fetched_nums:
                threading.Thread(target=send_waiting_status, args=(chat_id, fetched_nums[0], service_label, exp_ts), daemon=True).start()
            return

        # যদি আপলোড করা বা সার্ভিস থেকে আসে
        parts = data.split("_")
        service = parts[2]
        country = parts[3]

        available_indices = []
        # Check Local Stock First
        for b_id, b_data in number_batches.items():
            if b_data["service"] == service and b_data["country"] == country:
                for idx, n_obj in enumerate(b_data["numbers"]):
                    if chat_id not in n_obj.get("used_by", []):
                        available_indices.append((b_id, idx))

        # IF NO LOCAL STOCK, Check Nexa, Voltx & Stex Services
        if not available_indices:
            nexa_srv_data = bot_settings.get("nexa_services", {}).get(service, {}).get(country)
            voltx_srv_data = bot_settings.get("voltx_services", {}).get(service, {}).get(country)
            stex_srv_data = bot_settings.get("stex_services", {}).get(service, {}).get(country)
            
            target_range = None
            is_voltx = False
            is_stex = False
            
            if nexa_srv_data and len(nexa_srv_data) > 0:
                target_range = random.choice(nexa_srv_data)
            elif voltx_srv_data and len(voltx_srv_data) > 0:
                target_range = random.choice(voltx_srv_data)
                is_voltx = True
            elif stex_srv_data and len(stex_srv_data) > 0:
                # 🌟 STEX: Try auto-detected live range first, fallback to manual
                auto_rid = get_stex_live_rid(service, country)
                target_range = auto_rid if auto_rid else random.choice(stex_srv_data)
                is_stex = True
            else:
                # 🌟 STEX: No manual config — try pure auto range detect
                auto_rid = get_stex_live_rid(service, country)
                if auto_rid:
                    target_range = auto_rid
                    is_stex = True
                
            if target_range:
                user_cooldowns[chat_id] = 0
                ext_flag = "_stx" if is_stex else ("_vtx" if is_voltx else "")
                handle_callback({"message": call["message"], "data": f"c_n_s_{target_range}_{service}{ext_flag}", "id": call["id"]})
                return
            else:
                answer_callback(call["id"], "❌ Number out of stock or range missing!", show_alert=True)
                if data.startswith("c_n_"): delete_message(chat_id, msg_id)
                return

        random.shuffle(available_indices)
        
        fetched_nums = []
        for b_id, idx in available_indices:
            if len(fetched_nums) >= bot_settings["num_req"]: break
            n_obj = number_batches[b_id]["numbers"][idx]
            
            fetched_nums.append(n_obj["num"])
            n_obj["shares"] += 1
            n_obj["used_by"].append(chat_id)
            total_assigned_stats += 1
            
            if n_obj["shares"] >= bot_settings.get("num_share", 1):
                n_obj["to_remove"] = True
                used_numbers_list.append(n_obj["num"])

        for b_id in number_batches:
            number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
        save_db()

        if not fetched_nums:
            answer_callback(call["id"], "❌ You have already taken all numbers or stock is empty!", show_alert=True)
            if data.startswith("c_n_"): delete_message(chat_id, msg_id)
            return

        app_full_name, _ = get_service_info_html(service)
        emoji_id = "5337302974806922068"
        apps_db = bot_settings.get("premium_apps", {})
        for app_key, app_data in apps_db.items():
            if service.upper() == app_key or service.upper() in app_key or app_key in service.upper():
                if "id" in app_data:
                    emoji_id = app_data["id"]
                    break
        kb = [[{"text": f"{app_full_name}", "icon_custom_emoji_id": emoji_id, "callback_data": "ignore", "style": "success"}]]
        
        flags_db = bot_settings.get("premium_flags", {})
        for num in fetched_nums:
            _, iso = get_flag_and_code(num)
            display_num = f"+{num}" if not num.startswith("+") else num
            c_name    = get_country_full_name(iso)
            masked_disp = mask_number(display_num)
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                if iso == flag_data.get("iso"):
                    if "id" in flag_data: emoji_id = flag_data["id"]
                    break
            kb.append([{"text": f"{c_name}  {masked_disp}", "icon_custom_emoji_id": emoji_id, "copy_text": {"text": display_num}, "style": "primary"}])
            
        kb.append([{"text": "🔄 Change Number", "icon_custom_emoji_id": "6233525120334306978", "callback_data": f"c_n_{service}_{country}", "style": "danger"},
                   {"text": "📢 OTP Group", "icon_custom_emoji_id": "6233384966961502838", "url": bot_settings["otp_link"], "style": "primary"}])
                   
        c_btns = bot_settings["custom_messages"].get("get_number", {}).get("buttons", [])
        for c_b in c_btns: 
            b_copy = c_b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
            
        kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        
        text_numbers = "ㅤ\n"
        # সবসময় মেসেজ ইডিট করবে (Change Number করলেও নতুন মেসেজ আসবে না)
        try:
            edit_message(chat_id, msg_id, text_numbers, reply_markup={"inline_keyboard": kb})
            user_active_sessions[chat_id] = {"msg_id": msg_id, "nums": fetched_nums}
        except:
            # যদি মেসেজ ইডিট করা সম্ভব না হয় (যেমন অনেক আগের মেসেজ), তবে নতুন মেসেজ দিবে
            msg_res = send_message(chat_id, text_numbers, reply_markup={"inline_keyboard": kb})
            if msg_res and "result" in msg_res:
                user_active_sessions[chat_id] = {"msg_id": msg_res["result"]["message_id"], "nums": fetched_nums}

        # 🌟 Smart Expiry: register session expiry time
        exp_min = int(bot_settings.get("number_expiry_minutes", 10))
        if exp_min > 0:
            number_expiry_tracker[chat_id] = time.time() + (exp_min * 60)

        # 🌟 Send OTP waiting status message
        exp_ts = number_expiry_tracker.get(chat_id, time.time() + 600)
        if fetched_nums:
            threading.Thread(target=send_waiting_status, args=(chat_id, fetched_nums[0], service, exp_ts), daemon=True).start()
            record_user_number(chat_id, fetched_nums[0], service)

    elif data.startswith("wapp_") or data.startswith("wrej_"):
        # অ্যাডমিন চেক (User ID চেক করতে হবে)
        user_id_clicked = call["from"]["id"]
        if not is_admin(user_id_clicked):
            answer_callback(call["id"], "🚫 Only Bot Admins can process withdrawals!", show_alert=True)
            return
            
        action = "APPROVE" if data.startswith("wapp_") else "REJECT"
        req_id = data.replace("wapp_", "").replace("wrej_", "")
        
        if req_id in pending_withdrawals:
            req_data = pending_withdrawals[req_id]
            u_id, amt = req_data["user_id"], req_data["amount"]
            num = req_data["number"]
            full_name = req_data.get("full_name", u_id)
            
            if action == "APPROVE" and len(num) >= 7:
                masked_num = f"{num[:4]}❖𝐄𝐗𝐄❖{num[-3:]}"
            else:
                masked_num = num
            
            status_text = "APPROVED" if action == "APPROVE" else "REJECTED"
            emoji_icon_id = "5352694861990501856" if action == "APPROVE" else "5420130255174145507"
            new_text = f"🎙 <b>WITHDRAWAL {status_text}</b>\n\n👤 <b>USER:</b> <a href='tg://user?id={u_id}'>{full_name}</a>\n💳 <b>WITHDRAWAL:</b> {amt} TK\n🍏 <b>NUMBER:</b> <code>{masked_num}</code>\n🏦 <b>METHOD:</b> {req_data['method']}\n\n🧾 <b>REQ ID:</b> {req_id}\n👨‍⚖️ <b>PROCESSED BY ADMIN</b>"
            
            kb = {"inline_keyboard": [[{"text": status_text, "icon_custom_emoji_id": emoji_icon_id, "callback_data": "ignore", "style": "success" if action == "APPROVE" else "danger"}]]}
            edit_message(chat_id, msg_id, render_body_text(new_text), reply_markup=kb)
            
            if action == "REJECT":
                update_balance(u_id, amt) 
                send_message(u_id, render_body_text(f"❌ Your {amt} TK withdrawal request was rejected. Balance refunded."))
            else:
                send_message(u_id, render_body_text(f"{PEM['ok']} Your {amt} TK withdrawal request has been paid successfully!"))
            
            if db:
                try: db.collection('withdrawals').document(req_id).update({"status": "approved" if action == "APPROVE" else "rejected"})
                except: pass
                
            del pending_withdrawals[req_id]
        else:
            answer_callback(call["id"], "❌ Request already processed!", show_alert=True)

# ==========================================
# Polling Loop
# ==========================================
def poll_otp_with_status(number_id, num_str, owner_id, api_key):
    headers = {"X-API-Key": api_key}
    for _ in range(150): # 150 * 4 seconds = 10 Minutes Polling
        try:
            res = requests.get(f"{NEXA_BASE_URL}/api/v1/numbers/{number_id}/sms", headers=headers, timeout=10)
            data = res.json()
            if data.get("success") and data.get("otp"):
                otp = str(data["otp"])
                msg_text = data.get("message", f"Your code is {otp}")
                
                # 🌟 সম্পূর্ণ মেসেজ থেকে ড্যাশসহ বা বড় OTP খোঁজার ফিক্স
                extracted_otp = extract_otp_code(msg_text)
                if extracted_otp and len(extracted_otp) > len(otp):
                    otp = extracted_otp
                    
                # 🌟 সম্পূর্ণ মেসেজ থেকে সার্ভিস/অ্যাপ চেনার ফিক্স
                app_name = data.get("service", "Nexa Service")
                detected_app = detect_service(msg_text)
                if detected_app:
                    app_name = detected_app
                
                unique_id = f"POLL_{number_id}_{otp}"
                if unique_id not in processed_otps:
                    processed_otps.add(unique_id)
                    
                    char, iso = get_flag_and_code(num_str)
                    app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                    
                    global recent_traffic
                    current_time = time.time()
                    recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                    recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num_str, "time": current_time})
                    save_local_db()
                    
                    display_num = f"+{num_str}" if not str(num_str).startswith("+") else str(num_str)
                    masked = mask_number(display_num)
                    lang = detect_language(msg_text)
                    
                    send_to_forward_groups(prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, masked, lang, otp, unique_id, msg_text, iso)

                    inbox_msg = render_body_text(f"╔═══════════════╗\n║ {prem_app_html} {get_flag_info_html(display_num)} {display_num} {lang}\n╚═══════════════╝")
                    reward = get_service_reward(app_full_name)
                    inbox_kb = build_inbox_keyboard(otp, app_full_name, reward, owner_id, number=full_number)
                    
                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})
                    
                    increment_user_otp(owner_id, number=full_number)
                break
        except: pass
        time.sleep(4)

def voltx_sms_listener():
    global processed_otps, recent_traffic, voltx_assigned_numbers, panel_otp_log
    while True:
        try:
            voltx_keys = bot_settings.get("voltx_keys", [])
            for api_key in voltx_keys:
                try:
                    headers = {"mauthapi": api_key}
                    res = stex_get(f"{VOLTX_BASE_URL}/success-otp", headers=headers)
                    resp_data = res.json()
                    
                    if resp_data.get("meta", {}).get("code") == 200 and "data" in resp_data and "otps" in resp_data["data"]:
                        for item in resp_data["data"]["otps"]:
                            num = str(item.get("number", "")).replace("+", "")
                            msg_text = str(item.get("message", ""))
                            otp = extract_otp_code(msg_text) or "CODE"
                            otp_id = str(item.get("otp_id", otp))
                            
                            app_name = "Voltx Service"
                            detected_app = detect_service(msg_text)
                            if detected_app: app_name = detected_app
                                
                            unique_id = f"VOLTX_{num}_{otp_id}"
                            
                            if num:
                                pg_now = time.time()
                                panel_otp_log = [t for t in panel_otp_log if pg_now - t.get("time", 0) <= 3600]
                                panel_otp_log.append({"number": num, "time": pg_now})
                            
                            if unique_id not in processed_otps and num:
                                processed_otps.add(unique_id)
                                if len(processed_otps) > 5000: processed_otps = set(list(processed_otps)[-2000:])
                                
                                char, iso = get_flag_and_code(num)
                                app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                                current_time = time.time()
                                
                                recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                                recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                                save_local_db()
                                
                                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                                masked = mask_number(display_num)
                                lang = detect_language(msg_text)
                                
                                send_to_forward_groups(prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, masked, lang, otp, unique_id, msg_text, iso)

                                owner_id = None
                                clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                
                                for uid, session_data in user_active_sessions.items():
                                    for act_num in session_data.get("nums", []):
                                        act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                            owner_id = uid
                                            break
                                    if owner_id: break
                                    
                                if not owner_id:
                                    for vtx_n, n_owner in voltx_assigned_numbers.items():
                                        clean_vtx = str(vtx_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if clean_vtx == clean_api_num or (len(clean_vtx) >= 8 and clean_vtx.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_vtx[-8:])):
                                            owner_id = n_owner
                                            break
                                        
                                if owner_id:
                                    reward = get_service_reward(app_full_name)
                                    send_inbox_otp(owner_id, prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, lang, otp, reward, msg_text)
                                    increment_user_otp(owner_id, number=display_num)
                except: pass
        except: pass
        time.sleep(5)

def global_sms_listener():
    global processed_otps, recent_traffic, nexa_assigned_numbers, panel_otp_log
    while True:
        try:
            nexa_keys = bot_settings.get("nexa_keys", [])
            for api_key in nexa_keys:
                try:
                    headers = {"X-API-Key": api_key}
                    try:
                        res = requests.get(f"{NEXA_BASE_URL}/api/v1/sms/latest", headers=headers, timeout=10)
                        data = res.json()
                    except Exception:
                        continue
                    if data.get("success") and "data" in data:
                        for item in data["data"]:
                            num = str(item.get("number", "")).replace("+", "")
                            msg_text = str(item.get("sms", ""))
                            
                            # 🌟 সম্পূর্ণ মেসেজ থেকে সার্ভিস/অ্যাপ চেনার ফিক্স
                            app_name = item.get("app_name", "Unknown")
                            detected_app = detect_service(msg_text)
                            if detected_app:
                                app_name = detected_app
                                
                            otp = extract_otp_code(msg_text) or "CODE"
                            unique_id = f"NEXA_{num}_{item.get('id', otp)}"
                            
                            if num:
                                pg_now = time.time()
                                panel_otp_log = [t for t in panel_otp_log if pg_now - t.get("time", 0) <= 3600]
                                panel_otp_log.append({"number": num, "time": pg_now})
                            
                            if unique_id not in processed_otps and num:
                                processed_otps.add(unique_id)
                                if len(processed_otps) > 5000: processed_otps = set(list(processed_otps)[-2000:])
                                
                                char, iso = get_flag_and_code(num)
                                app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                                current_time = time.time()
                                
                                recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                                recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                                save_local_db()
                                
                                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                                masked = mask_number(display_num)
                                lang = detect_language(msg_text)
                                
                                send_to_forward_groups(prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, masked, lang, otp, unique_id, msg_text, iso)

                                owner_id = None
                                clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                
                                # ১. Active Sessions থেকে মালিক খোঁজা
                                for uid, session_data in user_active_sessions.items():
                                    for act_num in session_data.get("nums", []):
                                        act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                            owner_id = uid
                                            break
                                    if owner_id: break
                                    
                                # ২. Nexa/API-তে মালিক খোঁজা (Persistent Backup)
                                if not owner_id:
                                    for nexa_n, n_owner in nexa_assigned_numbers.items():
                                        clean_nexa = str(nexa_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if clean_nexa == clean_api_num or (len(clean_nexa) >= 8 and clean_nexa.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_nexa[-8:])):
                                            owner_id = n_owner
                                            break
                                        
                                if owner_id:
                                    reward = get_service_reward(app_full_name)
                                    send_inbox_otp(owner_id, prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, lang, otp, reward, msg_text)
                                    increment_user_otp(owner_id, number=display_num)
                except: continue
        except: pass
        time.sleep(5)


def stex_sms_listener():
    global processed_otps, recent_traffic, stex_assigned_numbers, panel_otp_log
    while True:
        try:
            stex_keys = bot_settings.get("stex_keys", [])
            for api_key in stex_keys:
                try:
                    headers = {"mauthapi": api_key}
                    res = stex_get(f"{STEX_BASE_URL}/success-otp", headers=headers)
                    resp_data = res.json()
                    
                    if resp_data.get("meta", {}).get("code") == 200 and "data" in resp_data and "otps" in resp_data["data"]:
                        for item in resp_data["data"]["otps"]:
                            num = str(item.get("number", "")).replace("+", "")
                            msg_text = str(item.get("message", ""))
                            otp = extract_otp_code(msg_text) or "CODE"
                            otp_id = str(item.get("otp_id", otp))
                            
                            app_name = "Stex Service"
                            detected_app = detect_service(msg_text)
                            if detected_app: app_name = detected_app
                                
                            unique_id = f"STEX_{num}_{otp_id}"
                            
                            if num:
                                pg_now = time.time()
                                panel_otp_log = [t for t in panel_otp_log if pg_now - t.get("time", 0) <= 3600]
                                panel_otp_log.append({"number": num, "time": pg_now})
                            
                            if unique_id not in processed_otps and num:
                                processed_otps.add(unique_id)
                                if len(processed_otps) > 5000: processed_otps = set(list(processed_otps)[-2000:])
                                
                                char, iso = get_flag_and_code(num)
                                app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                                current_time = time.time()
                                
                                recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                                recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                                save_local_db()
                                
                                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                                masked = mask_number(display_num)
                                lang = detect_language(msg_text)
                                
                                send_to_forward_groups(prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, masked, lang, otp, unique_id, msg_text, iso)

                                owner_id = None
                                clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                
                                for uid, session_data in user_active_sessions.items():
                                    for act_num in session_data.get("nums", []):
                                        act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                            owner_id = uid
                                            break
                                    if owner_id: break
                                    
                                if not owner_id:
                                    for stx_n, n_owner in stex_assigned_numbers.items():
                                        clean_stx = str(stx_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if clean_stx == clean_api_num or (len(clean_stx) >= 8 and clean_stx.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_stx[-8:])):
                                            owner_id = n_owner
                                            break
                                        
                                if owner_id:
                                    reward = get_service_reward(app_full_name)
                                    send_inbox_otp(owner_id, prem_app_html, app_full_name, get_flag_info_html(display_num), display_num, lang, otp, reward, msg_text)
                                    increment_user_otp(owner_id, number=display_num)
                except: pass
        except: pass
        time.sleep(5)


# ==========================================
# 🌟 STEX AUTO RANGE DETECTION
# ==========================================
# Stores: { "SERVICE_ISO": {"rid": "8801XXXXX", "time": float} }
stex_live_ranges = {}
_stex_range_lock = threading.Lock()

def _detect_iso_from_rid(rid):
    """Detect ISO country code from number range prefix using phonenumbers."""
    try:
        import phonenumbers as _pn
        p = _pn.parse("+" + rid, None)
        iso = _pn.region_code_for_number(p)
        return iso if iso else None
    except:
        # Fallback: try with existing flag detection
        try:
            _, iso = get_flag_and_code(rid)
            return iso if iso and iso != "XX" else None
        except:
            return None

def stex_range_detector_thread():
    """
    🌟 STEX Auto Range Detection
    - Polls STEX console API every 10s
    - Detects active ranges with service + country
    - Auto updates bot_settings["stex_services"][service][country] = [rid]
    - When traffic drops on a range → new range auto replaces it
    - Admin sees live status in Admin Panel → Stex Control → 📡 Live Ranges
    """
    global stex_live_ranges

    while True:
        try:
            stex_keys = bot_settings.get("stex_keys", [])
            if not stex_keys:
                time.sleep(10)
                continue

            api_key = stex_keys[0]
            headers = {"mauthapi": api_key}

            res = stex_get(f"{STEX_BASE_URL}/console", headers=headers)
            if res.status_code != 200:
                time.sleep(10)
                continue

            data      = res.json()
            hits      = data.get("data", {}).get("hits", [])
            now       = time.time()
            seen_this = set()

            # Count hits per range to detect traffic level
            range_hit_count = {}
            for hit in hits:
                raw_range = str(hit.get("range", "")).strip()
                if raw_range:
                    range_hit_count[raw_range] = range_hit_count.get(raw_range, 0) + 1

            for hit in hits:
                sid       = str(hit.get("sid",     "")).strip()
                msg       = str(hit.get("message", "")).strip()
                raw_range = str(hit.get("range",   "")).strip()

                if not raw_range or raw_range in seen_this:
                    continue
                seen_this.add(raw_range)

                # rid = X বাদ দিয়ে numeric prefix
                rid = raw_range.upper().replace("X", "").strip()
                if not rid:
                    continue

                # ISO detect via phonenumbers
                iso = _detect_iso_from_rid(rid)
                if not iso:
                    continue

                # Service match — message এ আগে, তারপর sid
                stex_services = bot_settings.get("stex_services", {})
                matched_srv = None
                for srv_key in stex_services:
                    if srv_key.lower() in msg.lower():
                        matched_srv = srv_key
                        break
                if not matched_srv:
                    for srv_key in stex_services:
                        if srv_key.lower() == sid.lower():
                            matched_srv = srv_key
                            break
                if not matched_srv and sid:
                    matched_srv = sid.upper()  # নতুন service auto add

                if not matched_srv:
                    continue

                srv_upper = matched_srv.upper()
                key = f"{srv_upper}_{iso}"

                with _stex_range_lock:
                    existing = stex_live_ranges.get(key, {})
                    old_rid  = existing.get("rid", "")
                    range_changed = (old_rid != rid)

                    # Save/update live range
                    stex_live_ranges[key] = {
                        "rid":     rid,
                        "raw":     raw_range,
                        "iso":     iso,
                        "service": srv_upper,
                        "time":    now,
                        "hits":    range_hit_count.get(raw_range, 1)
                    }

                # 🌟 Auto update bot_settings["stex_services"][service][country] = [rid]
                # This is what getnum flow reads — so range auto switches
                if "stex_services" not in bot_settings:
                    bot_settings["stex_services"] = {}
                if srv_upper not in bot_settings["stex_services"]:
                    bot_settings["stex_services"][srv_upper] = {}

                # Always set to current live range (replaces old range automatically)
                bot_settings["stex_services"][srv_upper][iso] = [rid]

                # Also keep country name format if already exists
                # e.g. if "Bangladesh" was set manually, also set ISO "BD"
                if range_changed and old_rid:
                    # Remove old range entries for this service+iso combo
                    for c_key in list(bot_settings["stex_services"].get(srv_upper, {}).keys()):
                        if bot_settings["stex_services"][srv_upper].get(c_key) == [old_rid]:
                            if c_key != iso:
                                del bot_settings["stex_services"][srv_upper][c_key]
                    # No broadcast on range change — only on traffic end

                save_local_db()

            # Expire ranges older than 15 min + remove from stex_services
            with _stex_range_lock:
                expired_keys = [
                    k for k, v in stex_live_ranges.items()
                    if now - v.get("time", 0) > 900
                ]
                for k in expired_keys:
                    entry = stex_live_ranges.pop(k, {})
                    expired_srv = entry.get("service", "")
                    expired_iso = entry.get("iso", "")
                    expired_rid = entry.get("rid", "")
                    if expired_srv and expired_iso:
                        srv_dict = bot_settings.get("stex_services", {}).get(expired_srv, {})
                        if srv_dict.get(expired_iso) == [expired_rid]:
                            del bot_settings["stex_services"][expired_srv][expired_iso]
                            save_local_db()
                    # 🌟 Broadcast when traffic ends
                    if expired_srv and expired_iso and expired_rid:
                        def _traffic_end_bcast(srv, iso_code, rid):
                            try:
                                flag_html = get_flag_info_html(iso_code)
                                c_name    = get_country_full_name(iso_code)
                                _, srv_html = get_service_info_html(srv)
                                txt = render_body_text(
                                    f"⚠️ <b>Traffic Ended</b>\n"
                                    f"━━━━━━━━━━━━━━━\n"
                                    f"{srv_html} <b>{srv}</b>\n"
                                    f"{flag_html} <b>{c_name}</b>\n"
                                    f"━━━━━━━━━━━━━━━\n"
                                    f"📡 Range <code>{rid}XXX</code> inactive.\n"
                                    f"🔴 This country unavailable now.\n"
                                    f"🕐 {bdt_str()}"
                                )
                                for fw in bot_settings.get("fw_groups", []):
                                    try: send_message(fw["chat_id"], txt)
                                    except: pass
                            except: pass
                        threading.Thread(
                            target=_traffic_end_bcast,
                            args=(expired_srv, expired_iso, expired_rid),
                            daemon=True
                        ).start()

        except Exception as e:
            try: log_error("stex_range_detector", e)
            except: pass

        time.sleep(10)


def get_stex_live_rid(service_name, iso_code):
    """
    Returns the current live rid for a given service+country from STEX console.
    Returns None if not available or expired (>15 min).
    Used by STEX getnum flow instead of manual range setting.
    """
    key = f"{service_name.upper()}_{iso_code.upper()}"
    with _stex_range_lock:
        entry = stex_live_ranges.get(key)
    if not entry:
        return None
    if time.time() - entry.get("time", 0) > 900:  # 15 min expiry
        return None
    return entry["rid"]


def get_stex_range_status():
    """Returns admin view of all currently active STEX auto-detected ranges."""
    now = time.time()
    with _stex_range_lock:
        active = {k: v for k, v in stex_live_ranges.items() if now - v.get("time", 0) <= 900}

    if not active:
        return render_body_text(
            "📡 <b>STEX Auto Range Detection</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "<i>No active ranges detected yet.\n"
            "Console is polled every 10s automatically.</i>\n"
            "━━━━━━━━━━━━━━━\n"
            f"🕐 {bdt_str()}"
        )

    lines = ""
    for key, v in sorted(active.items(), key=lambda x: x[1].get("hits", 0), reverse=True):
        age_sec  = int(now - v["time"])
        age_str  = f"{age_sec}s ago" if age_sec < 60 else f"{age_sec // 60}m {age_sec % 60}s ago"
        hits     = v.get("hits", 1)
        flag_html = get_flag_info_html(v["rid"])

        # Traffic level badge
        if hits >= 5:   traffic = "🔥 Hot"
        elif hits >= 2: traffic = "🟡 Normal"
        else:           traffic = "🟢 Active"

        lines += (
            f"{flag_html} <b>{v['service']}</b> — <code>{v['iso']}</code>  {traffic}\n"
            f"   📡 Range: <code>{v['rid']}XXX</code>\n"
            f"   📊 Hits: <b>{hits}</b> | Updated: {age_str}\n\n"
        )

    total = len(active)
    return render_body_text(
        f"📡 <b>STEX Auto Range Detection</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Active Ranges: <b>{total}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{lines}"
        f"━━━━━━━━━━━━━━━\n"
        f"🔄 Auto-updates every 10s\n"
        f"⏳ Expires after 15min of no traffic\n"
        f"🕐 {bdt_str()}"
    )



# ==========================================
# 🌟 LIVE DASHBOARD
# ==========================================
def build_live_dashboard():
    now = datetime.now()
    now_str = now.strftime("%d %b %Y %H:%M:%S")
    current_time = time.time()

    # Active users = those with active sessions right now
    active_users = len(user_active_sessions)
    # Today's OTPs from global aggregate
    today_otps = sum(user_cache[uid].get("today_otps", 0) for uid in user_cache)
    total_otps_ever = bot_settings.get("global_total_otps", 0)
    total_paid = bot_settings.get("global_total_earned", 0.0)
    total_users = len(all_known_users)
    panels_on = len([p for p in bot_settings.get("panels", []) if p.get("status") == "ON"])
    panels_total = len(bot_settings.get("panels", []))

    # Recent OTP rate (last 5 min)
    five_min_ago = current_time - 300
    recent_5min = len([t for t in recent_traffic if t.get("time", 0) >= five_min_ago])

    # Top service right now
    if recent_traffic:
        srv_cnt = Counter(t.get("service", "?") for t in recent_traffic[-20:])
        top_srv = srv_cnt.most_common(1)[0][0] if srv_cnt else "—"
        _, top_srv_html = get_service_info_html(top_srv)
    else:
        top_srv_html = "—"

    txt = (
        f"╔══════════════════╗\n"
        f"║ 📊 <b>LIVE DASHBOARD</b>\n"
        f"╚══════════════════╝\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"🟢 Active Sessions: <b>{active_users}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📈 Today's OTPs: <b>{today_otps}</b>\n"
        f"🚀 All-Time OTPs: <b>{total_otps_ever}</b>\n"
        f"⚡ Last 5 Min: <b>{recent_5min} OTPs</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💸 Total Paid Out: <b>{total_paid:.2f} ৳</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🖥 Panels ON: <b>{panels_on}/{panels_total}</b>\n"
        f"🔥 Hottest Service: {top_srv_html}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⌛ {now_str}"
    )
    return render_body_text(txt)


# ==========================================
# 🌟 USER ACTIVITY HEATMAP
# ==========================================
def build_activity_heatmap():
    """Shows OTP activity by hour of day (last 24h) as a text bar chart."""
    current_time = time.time()
    hour_counts = Counter()
    for t in recent_traffic:
        age = current_time - t.get("time", 0)
        if age <= 86400:  # last 24 hours
            hour = datetime.fromtimestamp(t.get("time", 0)).hour
            hour_counts[hour] += 1

    if not hour_counts:
        return render_body_text("📊 <b>Activity Heatmap</b>\n\n<i>No data yet for the last 24 hours.</i>")

    max_count = max(hour_counts.values()) if hour_counts else 1
    bar_max = 10  # max bar width

    txt = "╔══════════════════╗\n║ 📊 <b>ACTIVITY HEATMAP</b>\n╚══════════════════╝\n"
    txt += "<i>OTP activity by hour (last 24h)</i>\n━━━━━━━━━━━━━━━\n"

    peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
    for h in range(24):
        count = hour_counts.get(h, 0)
        bar_len = int((count / max_count) * bar_max) if max_count else 0
        bar = "█" * bar_len + "░" * (bar_max - bar_len)
        peak_mark = " 🏆" if h == peak_hour and count > 0 else ""
        label = f"{h:02d}:00"
        txt += f"<code>{label}</code> {bar} <b>{count}</b>{peak_mark}\n"

    txt += f"━━━━━━━━━━━━━━━\n🏆 Peak Hour: <b>{peak_hour:02d}:00</b> ({hour_counts.get(peak_hour,0)} OTPs)"
    return render_body_text(txt)


# ==========================================
# 🌟 SMART NUMBER EXPIRY THREAD
# ==========================================
# Track expiry times: {chat_id: expire_timestamp}
number_expiry_tracker = {}

def smart_expiry_thread():
    """🌟 Auto-expires user number sessions after `number_expiry_minutes` minutes."""
    while True:
        try:
            expiry_min = int(bot_settings.get("number_expiry_minutes", 10))
            if expiry_min > 0:
                now = time.time()
                expired_users = []
                for uid, exp_time in list(number_expiry_tracker.items()):
                    if now >= exp_time and uid in user_active_sessions:
                        expired_users.append(uid)

                for uid in expired_users:
                    try:
                        # Expire the number session
                        session_data = user_active_sessions.get(uid, {})
                        prev_msg_id = session_data.get("msg_id")
                        nums = session_data.get("nums", [])

                        for num in nums:
                            for d in [nexa_assigned_numbers, voltx_assigned_numbers, stex_assigned_numbers]:
                                if num in d: del d[num]
                        save_db()

                        kb = [[{"text": "⏰ Number Expired", "icon_custom_emoji_id": "5336997731481193790", "callback_data": "ignore", "style": "danger"}]]
                        try:
                            if prev_msg_id:
                                edit_message(uid, prev_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
                        except: pass

                        send_message(uid, render_body_text(
                            f"⌛ <b>Number Expired!</b>\n"
                            f"━━━━━━━━━━━━\n"
                            f"Your number session has expired after <b>{expiry_min} minutes</b>.\n"
                            f"Please get a new number."
                        ))

                        if uid in user_active_sessions:
                            del user_active_sessions[uid]
                        if uid in number_expiry_tracker:
                            del number_expiry_tracker[uid]
                    except: pass
        except: pass
        time.sleep(15)


# ==========================================
# 🌟 AUTO WELCOME + ONBOARDING
# ==========================================
onboarded_users = set()  # track who already got onboarding

def send_onboarding(chat_id):
    """Sends step-by-step onboarding guide to a new user."""
    if not bot_settings.get("onboarding_on", True):
        return
    if str(chat_id) in onboarded_users:
        return
    onboarded_users.add(str(chat_id))

    steps = [
        (
            "1️⃣ <b>GET A NUMBER</b>\n"
            "━━━━━━━━━━━━\n"
            "➡️ Tap <b>GET NUMBER</b> in the menu\n"
            "➡️ Select the Service (e.g. WhatsApp)\n"
            "➡️ Select a Country\n"
            "➡️ Your number will appear instantly!\n"
            "━━━━━━━━━━━━\n"
            "💡 <i>Tap the number to copy it</i>"
        ),
        (
            "2️⃣ <b>RECEIVE OTP</b>\n"
            "━━━━━━━━━━━━\n"
            "➡️ Use the number on the website/app\n"
            "➡️ Wait for the OTP SMS\n"
            "➡️ Bot will send it to your inbox automatically\n"
            "━━━━━━━━━━━━\n"
            "💡 <i>Tap the green OTP button to copy it</i>"
        ),
        (
            "3️⃣ <b>EARN & REFER</b>\n"
            "━━━━━━━━━━━━\n"
            f"➡️ Each OTP earns you <b>{bot_settings.get('otp_reward', 0.1)} ৳</b>\n"
            f"➡️ Refer friends — earn <b>{bot_settings.get('refer_reward', 0.2)} ৳</b> per referral\n"
            "➡️ Go to <b>Refer</b> to get your link\n"
            "━━━━━━━━━━━━\n"
            "💡 <i>Commission also earned on referral OTPs!</i>"
        ),
        (
            "4️⃣ <b>WITHDRAWAL</b>\n"
            "━━━━━━━━━━━━\n"
            f"➡️ Minimum withdrawal: <b>{bot_settings.get('min_withdraw', 30)} ৳</b>\n"
            "➡️ Methods: " + ", ".join(bot_settings.get("w_methods", ["bKash", "Nagad"])) + "\n"
            "➡️ Go to <b>WITHDRAWAL</b> in the menu\n"
            "━━━━━━━━━━━━\n"
            "✅ <b>You're all set! Enjoy using the bot.</b>"
        )
    ]

    time.sleep(1)
    for i, step_text in enumerate(steps):
        send_message(chat_id, render_body_text(step_text))
        time.sleep(1.5)


# ==========================================
# 🌟 INACTIVE USER RE-ENGAGEMENT
# ==========================================
def inactive_reengagement_thread():
    """🌟 Detects users inactive for 3+ days and sends a re-engagement message."""
    last_run = 0
    while True:
        try:
            time.sleep(3600)  # Check every hour
            if time.time() - last_run < 86400:  # Run once per day
                continue
            last_run = time.time()

            if not db:
                continue

            three_days_ago = time.time() - (3 * 86400)
            msg = render_body_text(
                f"👋 <b>We miss you!</b>\n"
                f"━━━━━━━━━━━━\n"
                f"🔥 There's fresh traffic right now!\n"
                f"📱 Get a new number and start earning OTPs.\n"
                f"━━━━━━━━━━━━\n"
                f"💸 Each OTP = <b>{bot_settings.get('otp_reward', 0.1)} ৳</b>\n"
                f"🎁 Refer friends = <b>{bot_settings.get('refer_reward', 0.2)} ৳</b> bonus!\n"
                f"━━━━━━━━━━━━\n"
                f"➡️ Tap <b>GET NUMBER</b> to start now!"
            )

            sent = 0
            for uid_str in list(all_known_users):
                try:
                    uid = int(uid_str)
                    if is_admin(uid):
                        continue
                    # Check last OTP time from cache or skip if recently active
                    u_data = user_cache.get(uid, {})
                    if u_data.get("today_otps", 0) > 0:
                        continue  # active today
                    # Try sending re-engagement
                    res = send_message(uid, msg)
                    if res and res.get("ok"):
                        sent += 1
                    time.sleep(0.04)
                except: pass

            if sent > 0:
                send_message(OWNER_ID, render_body_text(
                    f"📢 <b>Re-engagement Done!</b>\n✅ Sent to <b>{sent}</b> inactive users."
                ))
        except: pass


def main():
    global BOT_USERNAME
    res = api_call("getMe")
    if res.get("ok"): BOT_USERNAME = res["result"]["username"]
    print(f"🤖 Bot is starting... @{BOT_USERNAME}")
    
    threading.Thread(target=panel_monitor_thread, daemon=True).start()
    threading.Thread(target=global_sms_listener, daemon=True).start()
    threading.Thread(target=voltx_sms_listener, daemon=True).start()
    threading.Thread(target=stex_sms_listener, daemon=True).start()
    threading.Thread(target=stex_range_detector_thread, daemon=True).start()  # 🌟 STEX Auto Range Detect
    threading.Thread(target=daily_reset_thread, daemon=True).start()
    threading.Thread(target=auto_traffic_broadcast_thread, daemon=True).start()
    threading.Thread(target=_firebase_balance_sync_thread, daemon=True).start()
    threading.Thread(target=smart_expiry_thread, daemon=True).start()
    threading.Thread(target=panel_health_thread, daemon=True).start()        # 🌟 Panel Health Monitor
    threading.Thread(target=auto_backup_thread, daemon=True).start()          # 🌟 Daily Auto Backup
    threading.Thread(target=inactive_reengagement_thread, daemon=True).start()

    print("📡 Background APIs & Global SMS Listener Started!")
    
    # 🌟 PRO-LEVEL FAST SYSTEM: 500 Workers Pool
    executor = ThreadPoolExecutor(max_workers=500)
    
    offset = None
    while True:
        try:
            updates = api_call(f"getUpdates?timeout=50&offset={offset}")
            if updates and "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update: 
                        executor.submit(handle_message, update["message"])
                    elif "callback_query" in update: 
                        executor.submit(handle_callback, update["callback_query"])
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    main()    
