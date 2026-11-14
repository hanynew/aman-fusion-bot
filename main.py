import os
import io
import re
import html
import telebot
import certifi
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime

# === إعدادات البوت والاتصال ===
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

try:
    BOT_USERNAME = f"@{bot.get_me().username}"
except:
    BOT_USERNAME = "@AmanFusionBot"

# === ربط قاعدة بيانات MongoDB ===
MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['aman-fusion-bot']
users_collection = db['users']

# === قائمة الآدمن وإعدادات الـ API ===
ADMIN_IDS = [8227136699]
CHANNEL_USERNAME = "@AmanFusion"
RAPID_API_KEY = "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87"
RAPID_API_HOST = "tiktok-scraper7.p.rapidapi.com"

# === قاموس الدول ===
COUNTRIES = {
    "SA": ("المملكة العربية السعودية", "🇸🇦"), "AE": ("الإمارات العربية المتحدة", "🇦🇪"),
    "EG": ("مصر", "🇪🇬"), "YE": ("اليمن", "🇾🇪"), "IQ": ("العراق", "🇮🇶"),
    "MA": ("المغرب", "🇲🇦"), "DZ": ("الجزائر", "🇩🇿"), "KW": ("الكويت", "🇰🇼"),
    "JO": ("الأردن", "🇯🇴"), "QA": ("قطر", "🇶🇦"), "BH": ("البحرين", "🇧🇭"),
    "OM": ("سلطنة عُمان", "🇴🇲"), "SD": ("السودان", "🇸🇩"), "LB": ("لبنان", "🇱🇧"),
    "SY": ("سوريا", "🇸🇾"), "US": ("الولايات المتحدة", "🇺🇸"), "GB": ("المملكة المتحدة", "🇬🇧"),
    "TR": ("تركيا", "🇹🇷"), "FR": ("فرنسا", "🇫🇷"), "DE": ("ألمانيا", "🇩🇪"),
    "IN": ("الهند", "🇮🇳"), "ID": ("إندونيسيا", "🇮🇩"), "RU": ("روسيا", "🇷🇺"),
    "BR": ("البرازيل", "🇧🇷"), "PK": ("باكستان", "🇵🇰")
}

# === دوال مساعدة ===
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
    if not timestamp or str(timestamp) == "0": return "غير متوفر"
    try:
        ts = int(timestamp)
        if len(str(ts)) > 10: ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime('%H:%M:%S %d-%m-%Y')
    except: return "غير متوفر"

def get_yes_no(val): return "نعم ✅" if val else "لا ❌"
def get_privacy(val): return "للجميع 🌍" if val == 0 else "مغلق ❌"

def get_country_info(code):
    if not code: return "غير محددة", ""
    return COUNTRIES.get(code.upper(), (code, ""))

def get_account_level(followers):
    if followers > 1000000: return "أسطوري 🌟"
    elif followers > 100000: return "مشهور 🔥"
    elif followers > 10000: return "نجم صاعد ✨"
    elif followers > 1000: return "نشط 🚀"
    else: return "مبتدئ 🐣"

# جلب بيانات المستخدم من نقطتي اتصال مختلفتين لضمان الشمولية
def fetch_user_data(unique_id):
    url_info = "https://tiktok-scraper7.p.rapidapi.com/user/info"
    url_detail = "https://tiktok-scraper7.p.rapidapi.com/user/detail"
    headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}
    
    data = {}
    try:
        # المحاولة الأولى: user/info
        res_info = requests.get(url_info, headers=headers, params={"unique_id": unique_id}).json()
        if res_info.get("code") == 0 and res_info.get("data"):
            data.update(res_info["data"])
    except: pass

    try:
        # المحاولة الثانية: user/detail لجلب البيانات المفقودة (مثل الدولة والأصدقاء)
        # ملاحظة: بعض واجهات API تقبل unique_id وبعضها يطلب user_id. سنجرب unique_id أولاً
        res_detail = requests.get(url_detail, headers=headers, params={"unique_id": unique_id}).json()
        if res_detail.get("code") == 0 and res_detail.get("data"):
            # دمج البيانات
            if "user" in res_detail["data"]:
                data.setdefault("user", {}).update(res_detail["data"]["user"])
            if "stats" in res_detail["data"]:
                data.setdefault("stats", {}).update(res_detail["data"]["stats"])
    except: pass
    
    return data

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🚀 START"), KeyboardButton("🛠 الخدمات"))
    return markup

# ==========================================
# 🟢 واجهة المستخدم والخدمات الأساسية 🟢
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

    # الأزرار التفاعلية (استخدام username للـ API بدلاً من uid لتجنب أخطاء تيك توك)
    if call.data.startswith("info_"):
        parts = call.data.split("_", 2)
        action = parts[1]
        target_username = parts[2]

        if action == "country":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"🌍 **معلومات الدولة:**\nيتم جلب الدولة من خوادم تيك توك لـ @{target_username}.", parse_mode="Markdown")
        
        elif action == "level":
            bot.answer_callback_query(call.id, "⏳ جاري التقييم...")
            data = fetch_user_data(target_username)
            if data:
                followers = data.get("stats", {}).get("followerCount", 0)
                bot.send_message(call.message.chat.id, f"⭐ **مستوى الحساب:** {get_account_level(followers)}\n(المتابعين: {followers:,})", parse_mode="Markdown")
            else: bot.send_message(call.message.chat.id, "⚠️ خطأ في الاتصال.")
            
        elif action == "contact":
            bot.answer_callback_query(call.id, "⏳ جاري البحث...")
            data = fetch_user_data(target_username)
            if data:
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
            url = f"https://tiktok-scraper7.p.rapidapi.com/{endpoint}"
            try:
                res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username, "count": 10}).json()
                if res.get("code") == 0 and res.get("data") and "userList" in res["data"]:
                    usersList = res["data"]["userList"]
                    if not usersList: bot.edit_message_text("❌ القائمة فارغة أو مخفية.", chat_id=call.message.chat.id, message_id=msg.message_id)
                    else:
                        text = "👥 **أحدث الحسابات:**\n\n"
                        for u in usersList[:10]: text += f"👤 {u.get('user', {}).get('nickname', 'بدون اسم')} | `@{u.get('user', {}).get('uniqueId', '')}`\n"
                        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
                else: bot.edit_message_text("⚠️ القائمة خاصة.", chat_id=call.message.chat.id, message_id=msg.message_id)
            except: bot.edit_message_text("⚠️ خطأ في الاتصال.", chat_id=call.message.chat.id, message_id=msg.message_id)

        # استخراج الستوري باستخدام unique_id
        elif action == "story":
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, "⏳ جاري البحث عن ستوريات...")
            url = "https://tiktok-scraper7.p.rapidapi.com/user/story"
            try:
                res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username}).json()
                if res.get("code") == 0 and res.get("data") and res["data"].get("itemList"):
                    stories = res["data"]["itemList"]
                    story_count = len(stories)
                    uid = stories[0].get("author", {}).get("id", "غير معروف")
                    
                    text = f"<b>تم العثور على ستوريات لهذا الشخص</b>\n\n"
                    text += f"المستخدم: @{target_username}\n"
                    text += f"عدد الستوريات: {story_count}"
                    
                    markup = InlineKeyboardMarkup(row_width=3)
                    buttons = [InlineKeyboardButton(f"#{i+1}", callback_data=f"getstory_{i}_{target_username}") for i in range(story_count)]
                    markup.add(*buttons)
                    
                    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="HTML", reply_markup=markup)
                else:
                    bot.edit_message_text("❌ لا توجد ستوريات نشطة لهذا الحساب حالياً.", chat_id=call.message.chat.id, message_id=msg.message_id)
            except Exception as e:
                bot.edit_message_text("⚠️ تعذر الاتصال بخادم الستوري.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    # عرض الستوري الفعلي
    if call.data.startswith("getstory_"):
        parts = call.data.split("_", 2)
        story_index = int(parts[1])
        target_username = parts[2]
        
        bot.answer_callback_query(call.id, f"⏳ جاري تحميل الستوري #{story_index+1}...")
        url = "https://tiktok-scraper7.p.rapidapi.com/user/story"
        try:
            res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username}).json()
            if res.get("code") == 0 and res.get("data") and res["data"].get("itemList"):
                stories = res["data"]["itemList"]
                if story_index < len(stories):
                    story = stories[story_index]
                    
                    author_nick = story.get("author", {}).get("nickname", "بدون اسم")
                    stats = story.get("stats", {})
                    music_title = story.get("music", {}).get("title", "الصوت الأصلي")
                    music_url = story.get("music", {}).get("playUrl", "")
                    
                    text = f"ستوري #{story_index+1}\nالاسم: {author_nick}\n"
                    text += f"المشاهدات: {stats.get('playCount', 0)}\nاللايكات: {stats.get('diggCount', 0)}\nالمشاركات: {stats.get('shareCount', 0)}"
                    
                    video_url = story.get("video", {}).get("playAddr", "")
                    images = story.get("imagePost", {}).get("images", [])
                    
                    msg = bot.send_message(call.message.chat.id, "⏳ جاري الإرسال...")
                    
                    if video_url: bot.send_video(call.message.chat.id, video_url, caption=text, parse_mode="HTML")
                    elif images: bot.send_photo(call.message.chat.id, images[0].get("imageURL", {}).get("urlList", [""])[0], caption=text, parse_mode="HTML")
                    else: bot.send_message(call.message.chat.id, "⚠️ الستوري غير مدعومة.")
                        
                    bot.delete_message(chat_id=call.message.chat.id, message_id=msg.message_id)
                    
                    if music_url:
                        audio_markup = InlineKeyboardMarkup()
                        audio_markup.add(InlineKeyboardButton(f"🎧 {music_title}", url=music_url))
                        bot.send_message(call.message.chat.id, f"🎵 **الصوت الأصلي**\n{BOT_USERNAME}", parse_mode="Markdown", reply_markup=audio_markup)
            else: bot.send_message(call.message.chat.id, "❌ لم تعد الستوري متاحة.")
        except Exception: bot.send_message(call.message.chat.id, "⚠️ حدث خطأ.")
        return

# ==========================================
# 🛠️ دالة جلب البيانات الأساسية (البروفايل) 🛠️
# ==========================================

def process_profile_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    
    input_text = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري استخراج البيانات الدقيقة...")
    
    try:
        username = input_text.split("@")[1].split("?")[0].split("/")[0] if "@" in input_text else input_text.replace("@", "")

        # استخدام الدالة المزدوجة لضمان الشمولية
        data = fetch_user_data(username)

        if data:
            user = data.get("user", {})
            stats = data.get("stats", {})

            # استخراج الدولة بدقة
            region_code = user.get("region") or user.get("country") or user.get("iso3166") or ""
            country_name, country_flag = get_country_info(region_code)

            uid = user.get("id", "غير متوفر")
            nickname = user.get("nickname", "غير متوفر")
            
            # استخراج الإحصائيات (تم دمجها من الاستعلامين)
            followers = stats.get("followerCount", 0)
            following = stats.get("followingCount", 0)
            friends = stats.get("friendCount", 0)
            hearts = stats.get("heartCount", 0)
            videos = stats.get("videoCount", 0)
            
            create_time = format_date(user.get("createTime"))
            modify_time = format_date(user.get("nickNameModifyTime"))
            
            language = user.get("language", "English")
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
            bio_link = user.get("bioLink", {}).get("link", "(None)")
            avatar_url = user.get("avatarLarger", "")

            # بناء النص
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
            text += f"• {BOT_USERNAME}\n"
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

            # استخدام username للأزرار لضمان التوافق مع API الستوري
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
