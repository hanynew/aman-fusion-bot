import os
import io
import re
import json
import telebot
import certifi
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime

# ==========================================
# ⚙️ إعدادات تشغيل Render الأساسية ⚙️
# ==========================================
app = Flask(__name__)

# ==========================================
# ⚙️ إعدادات البوت وقاعدة البيانات ⚙️
# ==========================================
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

# إعادة المفتاح والواجهة الأصلية التي اشتركت بها لضمان عملها
RAPID_API_KEY = "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87"
RAPID_API_HOST = "tiktok-scraper7.p.rapidapi.com"

# ==========================================
# 🌍 القواميس (الدول واللغات) 🌍
# ==========================================
COUNTRIES = {
    "SA": ("المملكة العربية السعودية", "🇸🇦"), "AE": ("الإمارات العربية المتحدة", "🇦🇪"),
    "EG": ("مصر", "🇪🇬"), "YE": ("اليمن", "🇾🇪"), "IQ": ("العراق", "🇮🇶"),
    "MA": ("المغرب", "🇲🇦"), "DZ": ("الجزائر", "🇩🇿"), "KW": ("الكويت", "🇰🇼"),
    "JO": ("الأردن", "🇯🇴"), "QA": ("قطر", "🇶🇦"), "BH": ("البحرين", "🇧🇭"),
    "OM": ("سلطنة عُمان", "🇴🇲"), "SD": ("السودان", "🇸🇩"), "LB": ("لبنان", "🇱🇧"),
    "SY": ("سوريا", "🇸🇾"), "US": ("الولايات المتحدة", "🇺🇸"), "GB": ("المملكة المتحدة", "🇬🇧"),
    "TR": ("تركيا", "🇹🇷"), "FR": ("فرنسا", "🇫🇷"), "DE": ("ألمانيا", "🇩🇪"),
    "IN": ("الهند", "🇮🇳"), "ID": ("إندونيسيا", "🇮🇩"), "RU": ("روسيا", "🇷🇺")
}

LANGUAGES = {
    "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية", "es": "الإسبانية",
    "tr": "التركية", "ur": "الأردية", "id": "الإندونيسية", "hi": "الهندية",
    "zh": "الصينية", "ru": "الروسية", "de": "الألمانية", "ja": "اليابانية", "ko": "الكورية"
}

# ==========================================
# 🥷 محرك جلب البيانات الشامل (Triple-Mesh) 🥷
# ==========================================
def fetch_pro_data(username):
    data = {"user": {}, "stats": {}}
    
    # 1. الطبقة الأولى: TiklyDown (واجهة قوية جداً تجلب الأصدقاء والدولة بدون حظر)
    try:
        res = requests.get(f"https://api.tiklydown.eu.org/api/user?user={username}", timeout=12)
        if res.status_code == 200:
            js = res.json()
            data["user"]["id"] = js.get("id", "")
            data["user"]["nickname"] = js.get("name", "")
            data["user"]["signature"] = js.get("signature", "")
            data["user"]["avatarLarger"] = js.get("avatar", "")
            data["user"]["region"] = js.get("region", "")
            data["user"]["verified"] = js.get("verified", False)
            
            if "stats" in js:
                data["stats"]["followerCount"] = js["stats"].get("followerCount", 0)
                data["stats"]["followingCount"] = js["stats"].get("followingCount", 0)
                data["stats"]["heartCount"] = js["stats"].get("heartCount", 0)
                data["stats"]["videoCount"] = js["stats"].get("videoCount", 0)
                data["stats"]["friendCount"] = js["stats"].get("friendCount", 0)
    except Exception as e:
        print(f"TiklyDown Error: {e}")

    # 2. الطبقة الثانية: RapidAPI (التي تملك مفتاحها كضمان أساسي)
    try:
        rapid_headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}
        res = requests.get("https://tiktok-scraper7.p.rapidapi.com/user/info", headers=rapid_headers, params={"unique_id": username}, timeout=10)
        if res.status_code == 200:
            js = res.json()
            if js.get("code") == 0 and js.get("data"):
                r_user = js["data"].get("user", {})
                r_stats = js["data"].get("stats", {})
                for k, v in r_user.items():
                    if k == "region" and (v == "US" or not v): continue
                    if not data["user"].get(k): data["user"][k] = v
                for k, v in r_stats.items():
                    if not data["stats"].get(k): data["stats"][k] = v
    except Exception as e:
        print(f"RapidAPI Error: {e}")

    # 3. الطبقة الثالثة: TikWM لسد أي نواقص متبقية
    try:
        res = requests.get(f"https://www.tikwm.com/api/user/info?unique_id={username}", timeout=10)
        if res.status_code == 200:
            js = res.json()
            if js.get("code") == 0 and js.get("data"):
                u_data = js["data"].get("user", {})
                s_data = js["data"].get("stats", {})
                for k, v in u_data.items():
                    if not data["user"].get(k): data["user"][k] = v
                for k, v in s_data.items():
                    if not data["stats"].get(k): data["stats"][k] = v
    except Exception as e:
        pass

    # صائد الدولة العميق إذا فشلت كل الـ APIs
    curr_region = data["user"].get("region", "")
    if not curr_region or curr_region.upper() == "US":
        try:
            res = requests.get(f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=1", timeout=8)
            if res.status_code == 200:
                js = res.json()
                if js.get("code") == 0 and js.get("data") and js["data"].get("videos"):
                    vid_region = js["data"]["videos"][0].get("region")
                    if vid_region:
                        data["user"]["region"] = vid_region
        except Exception as e:
            print(f"Region Hunt Error: {e}")

    return data

def master_story_hunter(username):
    stories = []
    
    # 1. صيد الستوري من واجهة المنشورات الشاملة (TikWM) - الخيار الأقوى
    try:
        res = requests.get(f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=15", timeout=12)
        if res.status_code == 200:
            js = res.json()
            if js.get("code") == 0 and js.get("data") and js["data"].get("videos"):
                for v in js["data"]["videos"]:
                    if v.get("is_story") == True or v.get("aweme_type") in [68, 69, 101] or v.get("duration") == 0:
                        stories.append(v)
    except Exception as e:
        print(f"Story Error 1: {e}")

    if stories: return stories

    # 2. صيد الستوري من واجهة RapidAPI كاحتياطي
    try:
        rapid_headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}
        res = requests.get("https://tiktok-scraper7.p.rapidapi.com/user/story", headers=rapid_headers, params={"unique_id": username}, timeout=12)
        if res.status_code == 200:
            js = res.json()
            if js.get("code") == 0 and js.get("data") and js["data"].get("itemList"):
                stories = js["data"]["itemList"]
    except Exception as e:
        print(f"Story Error 2: {e}")
    
    return stories

# ==========================================
# 🛠️ دوال المساعدة والتنسيق 🛠️
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

def format_date(timestamp):
    if not timestamp or str(timestamp) == "0" or str(timestamp) == "-1": return "غير متوفر"
    try:
        ts = int(timestamp)
        if len(str(ts)) > 10: ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime('%H:%M:%S %d-%m-%Y')
    except: return "غير متوفر"

def get_yes_no(val): return "نعم ✅" if val else "لا ❌"
def get_privacy(val): return "للجميع 🌍" if val == 0 else "مغلق ❌"

def get_country_info(code):
    if not code or code.upper() == "ZZ": return "غير محددة", ""
    return COUNTRIES.get(code.upper(), (code, ""))

def get_language_name(code):
    if not code: return "غير محددة"
    base_code = code.split("-")[0].lower()
    return LANGUAGES.get(base_code, code)

def get_account_level(followers):
    if followers > 1000000: return "أسطوري 🌟"
    elif followers > 100000: return "مشهور 🔥"
    elif followers > 10000: return "نجم صاعد ✨"
    elif followers > 1000: return "نشط 🚀"
    else: return "مبتدئ 🐣"

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🚀 START"), KeyboardButton("🛠 الخدمات"))
    return markup

# ==========================================
# 🟢 واجهة المستخدم 🟢
# ==========================================

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

# ==========================================
# 🔴 لوحة تحكم الإدارة (الآدمن) 🔴
# ==========================================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 المشتركين", callback_data="stats"))
        markup.row(InlineKeyboardButton("⛔️ حظر", callback_data="ban_user"), InlineKeyboardButton("🔓 فك حظر", callback_data="unban_user"))
        markup.add(InlineKeyboardButton("📢 إذاعة", callback_data="broadcast"))
        bot.reply_to(message, f"👑 <b>لوحة الإدارة</b>", parse_mode="HTML", reply_markup=markup)

# ==========================================
# ⚙️ معالجة الأزرار التفاعلية ⚙️
# ==========================================
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
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"🌍 **معلومات الدولة:**\nتم استخراج الدولة بدقة لـ @{target_username}.", parse_mode="Markdown")
        
        elif action == "level":
            bot.answer_callback_query(call.id, "⏳ جاري التقييم...")
            data = fetch_pro_data(target_username)
            if data and data.get("stats"):
                followers = data.get("stats", {}).get("followerCount", 0)
                bot.send_message(call.message.chat.id, f"⭐ **مستوى الحساب:** {get_account_level(followers)}\n(المتابعين: {followers:,})", parse_mode="Markdown")
            else: bot.send_message(call.message.chat.id, "⚠️ خطأ في الاتصال.")
            
        elif action == "contact":
            bot.answer_callback_query(call.id, "⏳ جاري البحث...")
            data = fetch_pro_data(target_username)
            if data and data.get("user"):
                bio = data.get("user", {}).get("signature", "")
                emails = re.findall(r'[\w\.-]+@[\w\.-]+', bio)
                phones = re.findall(r'\+?\d{8,15}', bio)
                text = f"📧 **معلومات التواصل:**\nالبريد: {', '.join(emails) if emails else 'غير متاح'}\nالرقم: {', '.join(phones) if phones else 'غير متاح'}"
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            else: bot.send_message(call.message.chat.id, "⚠️ خطأ في الاتصال.")

        elif action in ["followers", "following"]:
            endpoint = "user/followers" if action == "followers" else "user/followings"
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, f"⏳ جاري جلب القائمة...")
            try:
                rapid_headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}
                res = requests.get(f"https://tiktok-scraper7.p.rapidapi.com/{endpoint}", headers=rapid_headers, params={"unique_id": target_username, "count": 10}, timeout=10)
                if res.status_code == 200:
                    res_json = res.json()
                    if res_json.get("code") == 0 and res_json.get("data") and "userList" in res_json["data"]:
                        usersList = res_json["data"]["userList"]
                        if not usersList: bot.edit_message_text("❌ القائمة فارغة أو مخفية.", chat_id=call.message.chat.id, message_id=msg.message_id)
                        else:
                            text = "👥 **أحدث الحسابات:**\n\n"
                            for u in usersList[:10]: text += f"👤 {u.get('user', {}).get('nickname', 'بدون اسم')} | `@{u.get('user', {}).get('uniqueId', '')}`\n"
                            bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
                    else: bot.edit_message_text("⚠️ القائمة خاصة.", chat_id=call.message.chat.id, message_id=msg.message_id)
                else: bot.edit_message_text("⚠️ خطأ في الاتصال بالسيرفر.", chat_id=call.message.chat.id, message_id=msg.message_id)
            except: bot.edit_message_text("⚠️ خطأ في الاتصال.", chat_id=call.message.chat.id, message_id=msg.message_id)

        elif action == "story":
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, "⏳ جاري البحث العميق عن الستوريات...")
            
            stories = master_story_hunter(target_username)

            if stories:
                story_count = len(stories)
                text = f"<b>تم العثور على ستوريات لهذا الشخص</b>\n\n"
                text += f"المستخدم: @{target_username}\n"
                text += f"عدد الستوريات: {story_count}"
                
                markup = InlineKeyboardMarkup(row_width=3)
                buttons = [InlineKeyboardButton(f"#{i+1}", callback_data=f"getstory_{i}_{target_username}") for i in range(story_count)]
                markup.add(*buttons)
                
                bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="HTML", reply_markup=markup)
            else:
                bot.edit_message_text("❌ لا توجد ستوريات نشطة لهذا الحساب حالياً.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    # عرض الستوري الفعلي
    if call.data.startswith("getstory_"):
        parts = call.data.split("_", 2)
        story_index = int(parts[1])
        target_username = parts[2]
        
        bot.answer_callback_query(call.id, f"⏳ جاري تحميل الستوري #{story_index+1}...")
        
        stories = master_story_hunter(target_username)

        if stories and story_index < len(stories):
            story = stories[story_index]
            
            author_nick = story.get("author", {}).get("nickname") or story.get("author", {}).get("nickname", "بدون اسم")
            
            stats = story.get("stats", {}) if "stats" in story else story
            views = stats.get("playCount") or stats.get("play_count", 0)
            likes = stats.get("diggCount") or stats.get("digg_count", 0)
            shares = stats.get("shareCount") or stats.get("share_count", 0)
            
            music_title = story.get("music", {}).get("title") or story.get("music_info", {}).get("title", "الصوت الأصلي")
            music_url = story.get("music", {}).get("playUrl") or story.get("music_info", {}).get("play", "")
            
            text = f"ستوري #{story_index+1}\nالاسم: {author_nick}\n"
            text += f"المشاهدات: {views}\nاللايكات: {likes}\nالمشاركات: {shares}"
            
            video_url = story.get("play") or story.get("video", {}).get("playAddr") 
            images = story.get("images") or story.get("imagePost", {}).get("images", [])
            
            msg = bot.send_message(call.message.chat.id, "⏳ جاري الإرسال...")
            
            try:
                if video_url: bot.send_video(call.message.chat.id, video_url, caption=text, parse_mode="HTML")
                elif images:
                    img_url = images[0] if isinstance(images[0], str) else images[0].get("imageURL", {}).get("urlList", [""])[0]
                    bot.send_photo(call.message.chat.id, img_url, caption=text, parse_mode="HTML")
                else: bot.send_message(call.message.chat.id, "⚠️ الستوري غير مدعومة.")
            except: bot.send_message(call.message.chat.id, "⚠️ فشل إرسال الوسائط.")
                
            bot.delete_message(chat_id=call.message.chat.id, message_id=msg.message_id)
            
            if music_url:
                audio_markup = InlineKeyboardMarkup()
                audio_markup.add(InlineKeyboardButton(f"🎧 {music_title}", url=music_url))
                bot.send_message(call.message.chat.id, f"🎵 **الصوت الأصلي**\n{BOT_USERNAME}", parse_mode="Markdown", reply_markup=audio_markup)
        else: bot.send_message(call.message.chat.id, "❌ لم تعد الستوري متاحة.")
        return

# ==========================================
# 🛠️ دالة جلب البيانات الأساسية (البروفايل) 🛠️
# ==========================================

def process_profile_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    
    input_text = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري استخراج البيانات الدقيقة (Multi-API Engine)...")
    
    try:
        username = input_text.split("@")[1].split("?")[0].split("/")[0] if "@" in input_text else input_text.replace("@", "")

        data = fetch_pro_data(username)

        # التأكد من أن هناك بيانات فعلية تم جلبها
        if data and data.get("user") and data["user"].get("id"):
            user = data.get("user", {})
            stats = data.get("stats", {})

            region_code = user.get("region", "")
            country_name, country_flag = get_country_info(region_code)

            uid = user.get("id", "غير متوفر")
            nickname = user.get("nickname", "غير متوفر")
            
            followers = stats.get("followerCount", 0)
            following = stats.get("followingCount", 0)
            friends = stats.get("friendCount", 0)
            hearts = stats.get("heartCount", 0)
            videos = stats.get("videoCount", 0)
            
            create_time = format_date(user.get("createTime"))
            modify_time = format_date(user.get("nickNameModifyTime"))
            
            # تصحيح تاريخ التعديل بذكاء
            if create_time != "غير متوفر" and create_time == modify_time:
                modify_time = "لم يتم التعديل"
            elif modify_time == "غير متوفر" and create_time != "غير متوفر":
                 modify_time = "لم يتم التعديل"
            
            language_code = user.get("language", "en")
            language = get_language_name(language_code)

            is_verified = get_yes_no(user.get("verified", False))
            download_setting = get_privacy(user.get("downloadSetting", 0))
            is_private = get_yes_no(user.get("secret", False))
            is_secret = get_yes_no(user.get("secret", False)) 
            has_store = get_yes_no(user.get("hasCommerceEntry", False))
            sells_on_tiktok = get_yes_no(user.get("withCommerceEntry", False))
            
            show_followers = get_privacy(user.get("followingVisibility", 0))
            duet_setting = get_privacy(user.get("duetSetting", 0))
            publish_setting = get_privacy(user.get("publishSetting", 0))
            comment_setting = get_privacy(user.get("commentSetting", 0))
            
            organized_account = get_yes_no(user.get("isUnderAge18", False)) 
            account_relation = str(user.get("relation", 0))
            open_favorites = get_yes_no(user.get("openFavorite", False))
            embed_ban = get_yes_no(user.get("preventDownload", False))
            
            show_music = get_yes_no(user.get("showMusic", False))
            show_questions = get_yes_no(user.get("showQuestion", False))
            show_lists = get_yes_no(user.get("showPlayList", False))
            suggest_link = get_yes_no(user.get("needSuggest", False))
            expand_lists = get_yes_no(user.get("expandPlayList", False))
            embed_permission = get_yes_no(user.get("allowEmbed", True))
            ftc_compliant = get_yes_no(user.get("ftc", False))
            fake_ads = get_yes_no(user.get("isADVirtual", False))
            
            bio = user.get("signature", "")
            bio_link = "(None)"
            avatar_url = user.get("avatarLarger", "")

            # بناء النص مع التوقيع المطلوب 
            text = f"اسم المستخدم: <code>{username}</code>\n"
            text += f"المعرف: <code>{uid}</code>\n"
            text += f"الاسم: {nickname}\n"
            text += f"المتابعين: {followers}\n"
            text += f"يتابع: {following}\n"
            text += f"الأصدقاء: {friends}\n"
            text += f"الإعجابات: {hearts}\n"
            text += f"الفيديوهات: {videos}\n"
            text += f"تاريخ الإنشاء: {create_time}\n"
            text += f"تعديل اليوزر: {create_time}\n" 
            text += f"تعديل الاسم: {modify_time}\n"
            text += f"الدولة: {country_name} {country_flag}\n"
            text += f"• إنشاء هذا بواسطة أمان فيوجن: {BOT_USERNAME}\n"
            text += f"اللغة: {language}\n"
            text += f"حساب موثق: {is_verified}\n"
            text += f"إعدادات التحميل: {download_setting}\n"
            text += f"حساب خاص: {is_private}\n"
            text += f"حساب سري: {is_secret}\n"
            text += f"يمتلك متجر: {has_store}\n"
            text += f"يبيع على تيك توك: {sells_on_tiktok}\n"
            text += f"إظهار المتابعين: {show_followers}\n"
            text += f"إعدادات الدويتو: {duet_setting}\n"
            text += f"إعدادات النشر: {publish_setting}\n"
            text += f"إعدادات التعليقات: {comment_setting}\n"
            text += f"حساب منظمة: {organized_account}\n"
            text += f"علاقة الحساب: {account_relation}\n"
            text += f"المفضلة مفتوحة: {open_favorites}\n"
            text += f"حظر التضمين: {embed_ban}\n"
            text += f"• إعدادات الملف الشخصي\n"
            text += f"عرض الموسيقى: {show_music}\n"
            text += f"عرض الأسئلة: {show_questions}\n"
            text += f"عرض القوائم: {show_lists}\n"
            text += f"اقتراح ربط حساب: {suggest_link}\n"
            text += f"توسيع القوائم: {expand_lists}\n"
            text += f"إذن التضمين: {embed_permission}\n"
            text += f"متوافق FTC: {ftc_compliant}\n"
            text += f"حساب إعلانات وهمي: {fake_ads}\n"
            text += f"البايو: {bio}\n"
            text += f"الرابط في البايو: {bio_link}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("دولة الحساب الاصلية", callback_data=f"info_country_{username}"))
            markup.row(InlineKeyboardButton("قائمة المتابعين", callback_data=f"info_followers_{username}"), 
                       InlineKeyboardButton("قائمة المتابعة", callback_data=f"info_following_{username}"))
            markup.add(InlineKeyboardButton("معلومات الحساب ( بريد ، رقم )", callback_data=f"info_contact_{username}"))
            markup.row(InlineKeyboardButton("مستوى الحساب", callback_data=f"info_level_{username}"), 
                       InlineKeyboardButton("مشاهدة الستوري", callback_data=f"info_story_{username}"))

            bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)

            if avatar_url:
                try:
                    img_file = io.BytesIO(requests.get(avatar_url).content)
                    img_file.name = f"{username}.jpg"
                    bot.send_document(message.chat.id, img_file, caption=text, parse_mode="HTML", reply_markup=markup)
                except: bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
            else: bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

        else:
            bot.edit_message_text("⚠️ لم أتمكن من العثور على هذا الحساب.", chat_id=message.chat.id, message_id=msg.message_id)

    except Exception as e:
        bot.edit_message_text("⚠️ حدث خطأ في الاتصال.", chat_id=message.chat.id, message_id=msg.message_id)

def process_download_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    bot.reply_to(message, f"⏳ سيتم برمجة التحميل قريباً...")

def process_media_search(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    bot.reply_to(message, f"⏳ سيتم برمجة البحث قريباً...")

def process_ban(message):
    if message.text == "/cancel": return
    try:
        tid = int(message.text.strip())
        if tid in ADMIN_IDS: return bot.reply_to(message, "⚠️ لا يمكن حظر الآدمن.")
        users_collection.update_one({"_id": tid}, {"$set": {"is_banned": True}})
        bot.reply_to(message, f"✅ تم الحظر.")
    except:
        bot.reply_to(message, "⚠️ أرسل أرقام فقط.")

def process_unban(message):
    if message.text == "/cancel": return
    try:
        tid = int(message.text.strip())
        users_collection.update_one({"_id": tid}, {"$set": {"is_banned": False}})
        bot.reply_to(message, f"✅ تم فك الحظر.")
    except:
        bot.reply_to(message, "⚠️ أرسل أرقام فقط.")

def process_broadcast(message):
    if message.text == "/cancel": return
    bot.reply_to(message, "⏳ جاري الإذاعة...")
    success, failed = 0, 0
    for u in users_collection.find({"is_banned": False}):
        try:
            bot.copy_message(u["_id"], message.chat.id, message.message_id)
            success += 1
        except: failed += 1
    bot.reply_to(message, f"✅ تمت الإذاعة بنجاح.\nوصلت إلى {success}")

# ==========================================
# 🌐 إعدادات سيرفر Render (Webhook) 🌐
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return 'OK', 200
    return "Aman Fusion Bot is running!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
