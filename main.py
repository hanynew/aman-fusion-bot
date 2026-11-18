import os
import io
import re
import json
import time
import logging
import certifi
import telebot
from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient

# 🥷 استدعاء مكتبة الاختراق
from curl_cffi import requests as cffi_requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# 🔥 استدعاء القناصة (السكربتات المستقلة التي صنعناها) 🔥
from tiktok_engine.features.country_hunter import CountryHunter
from tiktok_engine.features.story_hunter import StoryHunter

# ==========================================
# ⚙️ إعدادات النظام والتسجيل ⚙️
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AmanFusion")

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    BOT_USERNAME = f"@{bot.get_me().username}"
except:
    BOT_USERNAME = "@AmanFusion_bot"

MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['aman-fusion-bot']
users_collection = db['users']

ADMIN_IDS = [8227136699]
CHANNEL_USERNAME = "@AmanFusion"

# ==========================================
# 🛡️ المعمارية الهندسية (القواطع والذاكرة) 🛡️
# ==========================================
class CircuitBreaker:
    def __init__(self, threshold=5, cooldown=60):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = 0
        self.opened_at = 0.0

    def allow(self) -> bool:
        if self.failures < self.threshold: return True
        if time.time() - self.opened_at > self.cooldown:
            self.failures = self.threshold - 1 
            return True
        return False
    def success(self): self.failures = 0
    def failure(self):
        self.failures += 1
        if self.failures >= self.threshold: self.opened_at = time.time()

class MemoryCache:
    def __init__(self, ttl=300):
        self.cache = {}
        self.ttl = ttl
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl: return data
            else: del self.cache[key]
        return None
    def set(self, key, value):
        self.cache[key] = (value, time.time())

# ==========================================
# 🚀 محرك أمان فيوجن السريع (Fast Profile Engine) 🚀
# ==========================================
class TikTokFastEngine:
    """هذا المحرك أصبح الآن خفيفاً جداً وسريعاً، يجلب البيانات الأساسية فقط"""
    def __init__(self):
        self.breaker = CircuitBreaker()
        self.cache = MemoryCache(ttl=300) 
        self.impersonate = "chrome120"
        self.timeout = 10

    def _normalize_date(self, timestamp) -> str:
        if not timestamp or str(timestamp) == "0" or str(timestamp) == "-1": return "غير متوفر"
        try:
            ts = int(timestamp)
            if len(str(ts)) > 10: ts = ts / 1000
            return datetime.fromtimestamp(ts).strftime('%H:%M:%S %d-%m-%Y')
        except Exception: return "غير متوفر"

    def extract_profile(self, username: str):
        username = username.lstrip("@").strip()
        cached_data = self.cache.get(username)
        if cached_data: return cached_data

        result = {"status": "error", "message": "حدث خطأ غير معروف", "data": None}
        
        if not self.breaker.allow():
            result["message"] = "النظام في وضع التبريد (Cooldown)، جرب بعد دقيقة."
            return result
        
        try:
            url = f"https://www.tiktok.com/@{username}"
            res = cffi_requests.get(url, impersonate=self.impersonate, timeout=self.timeout)
            
            if res.status_code == 200:
                self.breaker.success()
                match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>', res.text)
                if not match:
                    result["message"] = "لم أتمكن من سحب البيانات، الحساب قد يكون محظوراً."
                    return result
                
                json_data = json.loads(match.group(1))
                state = json_data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
                user_info = state.get("userInfo", {})
                
                if not user_info or not user_info.get("user"):
                    result["message"] = "هذا الحساب غير موجود أو محذوف."
                    return result

                user = user_info.get("user", {})
                stats = user_info.get("stats", {})

                # استخراج الدولة الأساسية إن وجدت
                region = user.get("region", "")
                app_context = json_data.get("__DEFAULT_SCOPE__", {}).get("webapp.app-context", {})
                if app_context and app_context.get("appContext", {}).get("region"):
                     region = app_context["appContext"]["region"]

                create_time = self._normalize_date(user.get("createTime"))
                modify_time = self._normalize_date(user.get("nickNameModifyTime"))
                if create_time != "غير متوفر" and create_time == modify_time:
                    modify_time = "لم يتم التعديل"

                result["status"] = "success"
                result["data"] = {
                    "username": username,
                    "user_id": user.get("id", "غير متوفر"),
                    "nickname": user.get("nickname", "غير متوفر"),
                    "bio": user.get("signature", ""),
                    "avatar": user.get("avatarLarger", ""),
                    "region": region,
                    "language": user.get("language", "en"),
                    "is_verified": user.get("verified", False),
                    "is_private": user.get("secret", False),
                    "followers": stats.get("followerCount", 0),
                    "following": stats.get("followingCount", 0),
                    "friends": stats.get("friendCount", 0),
                    "likes": stats.get("heartCount", 0),
                    "videos": stats.get("videoCount", 0),
                    "create_time_formatted": create_time,
                    "modify_time_formatted": modify_time,
                    "download_setting": user.get("downloadSetting", 0),
                    "has_store": user.get("hasCommerceEntry", False),
                    "sells_on_tiktok": user.get("withCommerceEntry", False),
                    "duet_setting": user.get("duetSetting", 0),
                    "publish_setting": user.get("publishSetting", 0),
                    "comment_setting": user.get("commentSetting", 0),
                    "account_relation": user.get("relation", 0),
                    "open_favorites": user.get("openFavorite", False),
                    "embed_ban": user.get("preventDownload", False),
                    "show_music": user.get("showMusic", False),
                    "ftc_compliant": user.get("ftc", False),
                    "fake_ads": user.get("isADVirtual", False)
                }
                self.cache.set(username, result)
                return result
            elif res.status_code == 404:
                self.breaker.success()
                result["message"] = "هذا الحساب غير موجود."
                return result
            else:
                self.breaker.failure()
        except Exception as e:
            self.breaker.failure()
            logger.error(f"Fast Engine Error: {e}")
        
        result["message"] = "فشل الاتصال بسيرفرات تيك توك، جرب بعد قليل."
        return result

engine = TikTokFastEngine()

# ==========================================
# 🌍 القواميس وتنسيق النصوص 🌍
# ==========================================
LANGUAGES = {
    "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية", "es": "الإسبانية",
    "tr": "التركية", "ur": "الأردية", "id": "الإندونيسية", "hi": "الهندية",
    "zh": "الصينية", "ru": "الروسية", "de": "الألمانية", "ja": "اليابانية", "ko": "الكورية"
}

def get_yes_no(val): return "نعم ✅" if val else "لا ❌"
def get_privacy(val): return "للجميع 🌍" if val == 0 else "مغلق ❌"
def get_language_name(code):
    if not code: return "غير محددة"
    return LANGUAGES.get(code.split("-")[0].lower(), code)

# ==========================================
# 🟢 واجهة المستخدم وتيليجرام 🟢
# ==========================================
def is_subscribed(chat_id, user_id):
    try: return bot.get_chat_member(chat_id, user_id).status in ['member', 'administrator', 'creator']
    except: return True 

def register_user(user_id, first_name, username):
    users_collection.update_one(
        {"_id": user_id},
        {"$set": {"first_name": first_name, "username": username, "last_active": datetime.now()},
         "$setOnInsert": {"joined_date": datetime.now(), "is_banned": False}},
        upsert=True
    )

def get_main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🚀 START"), KeyboardButton("🛠 الخدمات"))
    return markup

def send_main_menu(chat_id, first_name):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 بيانات الحساب", callback_data="service_profile"))
    markup.add(InlineKeyboardButton("📥 تحميل بدون علامة مائية", callback_data="service_download"))
    markup.add(InlineKeyboardButton("🔍 البحث عن الوسائط", callback_data="service_media"))
    text = f"مرحباً بك يا {first_name} في أمان فيوجن 🛠️\n\n✨ **يرجى اختيار الخدمة المطلوبة:**"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "مستخدم"
    username = message.from_user.username
    if users_collection.find_one({"_id": user_id, "is_banned": True}):
        bot.reply_to(message, "⛔️ عذراً، تم حظرك.", reply_markup=get_main_reply_keyboard())
        return
    if not is_subscribed(CHANNEL_USERNAME, user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        bot.reply_to(message, f"👋 أهلاً بك\n\n⚠️ يجب الاشتراك أولاً.", reply_markup=markup)
        return
    register_user(user_id, first_name, username)
    bot.send_message(message.chat.id, "✅ القائمة الرئيسية", reply_markup=get_main_reply_keyboard())
    send_main_menu(message.chat.id, first_name)

@bot.message_handler(func=lambda message: message.text in ["🚀 START", "🛠 الخدمات"])
def handle_reply_keyboard(message):
    if message.text == "🚀 START": send_welcome(message)
    elif message.text == "🛠 الخدمات": send_main_menu(message.chat.id, message.from_user.first_name or "مستخدم")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "check_sub":
        if is_subscribed(CHANNEL_USERNAME, call.from_user.id):
            bot.answer_callback_query(call.id, "✅ تم التحقق!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id, call.from_user.first_name)
        else: bot.answer_callback_query(call.id, "❌ لم تشترك بعد!", show_alert=True)
        return

    if call.data == "service_profile":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📊 أرسل يوزر الحساب مسبوقاً بـ @:")
        bot.register_next_step_handler(msg, process_profile_link)
        return

    if call.data.startswith("info_"):
        parts = call.data.split("_", 2)
        action = parts[1]
        target_username = parts[2]

        if action == "country":
            bot.answer_callback_query(call.id, "⏳ جاري الهجوم واستخراج الدولة العميقة...")
            # 🎯 استدعاء قناص الدولة المستقل
            hunter = CountryHunter()
            result = hunter.hunt(target_username)
            if result["status"] == "success":
                text = f"🌍 **تم اصطياد الدولة بنجاح:**\nالدولة: {result['country_name']} {result['flag']}\nرمز الدولة: {result['code']}"
            else:
                text = f"⚠️ {result['message']}"
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
        elif action == "contact":
            bot.answer_callback_query(call.id, "⏳ جاري البحث...")
            profile_data = engine.extract_profile(target_username)
            if profile_data.get("status") == "success":
                bio = profile_data["data"].get("bio", "")
                emails = re.findall(r'[\w\.-]+@[\w\.-]+', bio)
                phones = re.findall(r'\+?\d{8,15}', bio)
                text = f"📧 **معلومات التواصل:**\nالبريد: {', '.join(emails) if emails else 'غير متاح'}\nالرقم: {', '.join(phones) if phones else 'غير متاح'}"
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            else: bot.send_message(call.message.chat.id, "⚠️ خطأ في الاتصال.")

        elif action == "story":
            bot.answer_callback_query(call.id, "⏳ يتم الآن تشغيل قناص الستوري...")
            msg = bot.send_message(call.message.chat.id, "⏳ جاري الهجوم العميق لجلب الستوريات النشطة...")
            
            # 🎯 استدعاء قناص الستوري المستقل
            hunter = StoryHunter()
            stories = hunter.hunt(target_username)

            if stories:
                story_count = len(stories)
                text = f"<b>تم العثور على ستوريات لهذا الشخص</b>\n\nالمستخدم: @{target_username}\nعدد الستوريات: {story_count}"
                markup = InlineKeyboardMarkup(row_width=3)
                buttons = [InlineKeyboardButton(f"#{i+1}", callback_data=f"getstory_{i}_{target_username}") for i in range(story_count)]
                markup.add(*buttons)
                bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="HTML", reply_markup=markup)
            else:
                bot.edit_message_text("❌ لا توجد ستوريات نشطة لهذا الحساب حالياً.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    if call.data.startswith("getstory_"):
        parts = call.data.split("_", 2)
        story_index = int(parts[1])
        target_username = parts[2]
        
        bot.answer_callback_query(call.id, f"⏳ جاري تحميل الستوري #{story_index+1}...")
        
        # 🎯 استخدام قناص الستوري لجلب المحتوى
        hunter = StoryHunter()
        stories = hunter.hunt(target_username)

        if stories and story_index < len(stories):
            story = stories[story_index]
            text = f"ستوري #{story_index+1}\nالاسم: {story['author_name']}\nالمشاهدات: {story['views']}\nاللايكات: {story['likes']}\nالمشاركات: {story['shares']}"
            
            msg = bot.send_message(call.message.chat.id, "⏳ جاري الإرسال...")
            try:
                if story['video_url']: bot.send_video(call.message.chat.id, story['video_url'], caption=text, parse_mode="HTML")
                elif story['images']:
                    img_url = story['images'][0].get("imageURL", {}).get("urlList", [""])[0] if isinstance(story['images'][0], dict) else story['images'][0]
                    bot.send_photo(call.message.chat.id, img_url, caption=text, parse_mode="HTML")
                else: bot.send_message(call.message.chat.id, "⚠️ الستوري غير مدعومة.")
            except: bot.send_message(call.message.chat.id, "⚠️ فشل إرسال الوسائط.")
                
            bot.delete_message(chat_id=call.message.chat.id, message_id=msg.message_id)
            if story['music_url']:
                audio_markup = InlineKeyboardMarkup()
                audio_markup.add(InlineKeyboardButton(f"🎧 {story['music_title']}", url=story['music_url']))
                bot.send_message(call.message.chat.id, f"🎵 **الصوت الأصلي**\n{BOT_USERNAME}", parse_mode="Markdown", reply_markup=audio_markup)
        else: bot.send_message(call.message.chat.id, "❌ لم تعد الستوري متاحة.")
        return

def process_profile_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    
    input_text = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري السحب السريع للبيانات الأساسية...")
    
    try:
        username = input_text.split("@")[1].split("?")[0].split("/")[0] if "@" in input_text else input_text.replace("@", "")

        engine_response = engine.extract_profile(username)

        if engine_response["status"] == "success":
            d = engine_response["data"]
            language = get_language_name(d["language"])
            
            # ترتيب عرض الدولة (توجيه المستخدم لزر الدولة إذا كانت مخفية)
            display_region = "اضغط على زر (دولة الحساب الاصلية) للبحث العميق 🔍" if not d["region"] or d["region"].upper() in ["ZZ", "US"] else f"تم الكشف مبدئياً: {d['region'].upper()}"

            text = f"اسم المستخدم: <code>{d['username']}</code>\n"
            text += f"المعرف: <code>{d['user_id']}</code>\n"
            text += f"الاسم: {d['nickname']}\n"
            text += f"المتابعين: {d['followers']}\n"
            text += f"يتابع: {d['following']}\n"
            text += f"الأصدقاء: {d['friends']}\n"
            text += f"الإعجابات: {d['likes']}\n"
            text += f"الفيديوهات: {d['videos']}\n"
            text += f"تاريخ الإنشاء: {d['create_time_formatted']}\n"
            text += f"تعديل اليوزر: {d['create_time_formatted']}\n" 
            text += f"تعديل الاسم: {d['modify_time_formatted']}\n"
            text += f"الدولة: {display_region}\n"
            text += f"• إنشاء هذا بواسطة أمان فيوجن: {BOT_USERNAME}\n"
            text += f"اللغة: {language}\n"
            text += f"حساب موثق: {get_yes_no(d['is_verified'])}\n"
            text += f"إعدادات التحميل: {get_privacy(d['download_setting'])}\n"
            text += f"حساب خاص: {get_yes_no(d['is_private'])}\n"
            text += f"يمتلك متجر: {get_yes_no(d['has_store'])}\n"
            text += f"يبيع على تيك توك: {get_yes_no(d['sells_on_tiktok'])}\n"
            text += f"إعدادات الدويتو: {get_privacy(d['duet_setting'])}\n"
            text += f"إعدادات النشر: {get_privacy(d['publish_setting'])}\n"
            text += f"إعدادات التعليقات: {get_privacy(d['comment_setting'])}\n"
            text += f"حساب منظمة: {get_yes_no(d['is_under_18'])}\n"
            text += f"علاقة الحساب: {d['account_relation']}\n"
            text += f"المفضلة مفتوحة: {get_yes_no(d['open_favorites'])}\n"
            text += f"حظر التضمين: {get_yes_no(d['embed_ban'])}\n"
            text += f"• إعدادات الملف الشخصي\n"
            text += f"عرض الموسيقى: {get_yes_no(d['show_music'])}\n"
            text += f"متوافق FTC: {get_yes_no(d['ftc_compliant'])}\n"
            text += f"البايو: {d['bio']}\n"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("دولة الحساب الاصلية", callback_data=f"info_country_{username}"))
            markup.row(InlineKeyboardButton("قائمة المتابعين", callback_data=f"info_followers_{username}"), InlineKeyboardButton("قائمة المتابعة", callback_data=f"info_following_{username}"))
            markup.add(InlineKeyboardButton("معلومات الحساب ( بريد ، رقم )", callback_data=f"info_contact_{username}"))
            markup.row(InlineKeyboardButton("مستوى الحساب", callback_data=f"info_level_{username}"), InlineKeyboardButton("مشاهدة الستوري", callback_data=f"info_story_{username}"))

            bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)

            if d['avatar']:
                try:
                    import urllib3
                    urllib3.disable_warnings()
                    img_file = io.BytesIO(cffi_requests.get(d['avatar'], impersonate="chrome120").content)
                    img_file.name = f"{username}.jpg"
                    bot.send_document(message.chat.id, img_file, caption=text, parse_mode="HTML", reply_markup=markup)
                except: bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
            else: bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

        else:
            bot.edit_message_text(f"⚠️ {engine_response['message']}", chat_id=message.chat.id, message_id=msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ حدث خطأ داخلي في النظام: {e}", chat_id=message.chat.id, message_id=msg.message_id)

# ==========================================
# 🌐 إعدادات سيرفر Render 🌐
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return 'OK', 200
    return "Aman Fusion Advanced Modular Engine is running!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
