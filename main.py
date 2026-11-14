import os
import io
import re
import html
import telebot
import certifi
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# === إعدادات البوت والاتصال ===
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# === ربط قاعدة بيانات MongoDB ===
MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['aman-fusion-bot']
users_collection = db['users']

# === قائمة الآدمن وإعدادات القناة والـ API ===
ADMIN_IDS = [8227136699]
CHANNEL_USERNAME = "@AmanFusion"
RAPID_API_KEY = "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87"
RAPID_API_HOST = "tiktok-scraper7.p.rapidapi.com"

# === قاموس الدول (لترجمة رمز الدولة إلى اسم عربي وعلم) ===
COUNTRIES = {
    "SA": ("المملكة العربية السعودية", "🇸🇦"), "AE": ("الإمارات العربية المتحدة", "🇦🇪"),
    "EG": ("مصر", "🇪🇬"), "YE": ("اليمن", "🇾🇪"), "IQ": ("العراق", "🇮🇶"),
    "MA": ("المغرب", "🇲🇦"), "DZ": ("الجزائر", "🇩🇿"), "KW": ("الكويت", "🇰🇼"),
    "JO": ("الأردن", "🇯🇴"), "QA": ("قطر", "🇶🇦"), "BH": ("البحرين", "🇧🇭"),
    "OM": ("سلطنة عُمان", "🇴🇲"), "SD": ("السودان", "🇸🇩"), "LB": ("لبنان", "🇱🇧"),
    "SY": ("سوريا", "🇸🇾"), "US": ("الولايات المتحدة", "🇺🇸"), "GB": ("المملكة المتحدة", "🇬🇧"),
    "TR": ("تركيا", "🇹🇷"), "FR": ("فرنسا", "🇫🇷"), "DE": ("ألمانيا", "🇩🇪"),
    "KW": ("الكويت", "🇰🇼"), "IN": ("الهند", "🇮🇳"), "ID": ("إندونيسيا", "🇮🇩")
}

# === دوال مساعدة ===
def is_subscribed(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return True 

def register_user(user_id, first_name, username):
    users_collection.update_one(
        {"_id": user_id},
        {"$set": {"first_name": first_name, "username": username, "last_active": datetime.now()},
         "$setOnInsert": {"joined_date": datetime.now(), "is_banned": False}},
        upsert=True
    )

def format_date(timestamp):
    if not timestamp or timestamp == 0: return "غير متوفر"
    try: return datetime.fromtimestamp(int(timestamp)).strftime('%H:%M:%S %d-%m-%Y')
    except: return "غير متوفر"

def get_yes_no(val): return "نعم ✅" if val else "لا ❌"
def get_privacy(val): return "للجميع 🌍" if val == 0 else "مغلق ❌"

def get_country_info(code):
    if not code: return "غير محددة", "🌍"
    return COUNTRIES.get(code.upper(), (code, "🌍"))

def get_account_level(followers):
    if followers > 1000000: return "أسطوري 🌟"
    elif followers > 100000: return "مشهور 🔥"
    elif followers > 10000: return "نجم صاعد ✨"
    elif followers > 1000: return "نشط 🚀"
    else: return "مبتدئ 🐣"

# لوحة المفاتيح السفلية الدائمة
def get_main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, persistent=True)
    markup.add(KeyboardButton("🚀 START"), KeyboardButton("🛠 الخدمات"))
    return markup

# ==========================================
# 🟢 قسم واجهة المستخدم (الخدمات الرئيسية) 🟢
# ==========================================

def send_main_menu(chat_id, first_name):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 بيانات الحساب", callback_data="service_profile"))
    markup.add(InlineKeyboardButton("📥 تحميل بدون علامة مائية", callback_data="service_download"))
    markup.add(InlineKeyboardButton("🔍 البحث عن الوسائط", callback_data="service_media"))
    text = f"مرحباً بك يا {first_name} في أمان فيوجن 🛠️\n\n✨ **يرجى اختيار الخدمة المطلوبة من القائمة أدناه:**"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "مستخدم"
    username = message.from_user.username
    
    if users_collection.find_one({"_id": user_id, "is_banned": True}):
        bot.reply_to(message, "⛔️ عذراً، لقد تم حظرك من استخدام هذا البوت.")
        return

    if not is_subscribed(CHANNEL_USERNAME, user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 اضغط هنا للاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        bot.reply_to(message, f"👋 أهلاً بك يا {first_name}\n\n⚠️ يجب الاشتراك في قناتنا أولاً.", reply_markup=markup)
        return

    register_user(user_id, first_name, username)
    # إرسال رسالة ترحيبية لتثبيت الكيبورد السفلي الدائم
    bot.send_message(message.chat.id, "تم تفعيل القائمة السفلية بنجاح ✅", reply_markup=get_main_reply_keyboard())
    send_main_menu(message.chat.id, first_name)

# التقاط الأزرار السفلية الدائمة
@bot.message_handler(func=lambda message: message.text in ["🚀 START", "🛠 الخدمات"])
def handle_reply_keyboard(message):
    if message.text == "🚀 START":
        send_welcome(message)
    elif message.text == "🛠 الخدمات":
        send_main_menu(message.chat.id, message.from_user.first_name or "مستخدم")

# ==========================================
# 🔴 قسم لوحة تحكم الإدارة (الآدمن) 🔴
# ==========================================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        users_count = users_collection.count_documents({})
        banned_count = users_collection.count_documents({"is_banned": True})
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 قائمة المشتركين", callback_data="stats"))
        markup.row(InlineKeyboardButton("⛔️ حظر", callback_data="ban_user"), InlineKeyboardButton("🔓 فك حظر", callback_data="unban_user"))
        markup.add(InlineKeyboardButton("📢 إذاعة للكل", callback_data="broadcast"))
        bot.reply_to(message, f"👑 <b>لوحة الإدارة</b> 👑\n👥 المشتركين: {users_count}\n🚫 المحظورين: {banned_count}", parse_mode="HTML", reply_markup=markup)

# ==========================================
# ⚙️ معالجة جميع ضغطات الأزرار (خدمات + آدمن) ⚙️
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # === خدمات البوت الأساسية ===
    if call.data == "check_sub":
        if is_subscribed(CHANNEL_USERNAME, call.from_user.id):
            bot.answer_callback_query(call.id, "✅ تم التحقق، شكراً لاشتراكك!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id, call.from_user.first_name)
        else:
            bot.answer_callback_query(call.id, "❌ لم تقم بالاشتراك بعد!", show_alert=True)
        return

    if call.data == "service_profile":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📊 أرسل يوزر الحساب مسبوقاً بـ @ (أو رابط الحساب):")
        bot.register_next_step_handler(msg, process_profile_link)
        return
        
    if call.data == "service_download":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📥 أرسل رابط الفيديو لتحميله:")
        bot.register_next_step_handler(msg, process_download_link)
        return

    # === الأزرار التفاعلية لبيانات الحساب ===
    if call.data.startswith("info_"):
        parts = call.data.split("_")
        action = parts[1]
        target_username = parts[2] if len(parts) > 2 else ""

        bot.answer_callback_query(call.id, "⏳ جاري تنفيذ الطلب...")

        if action == "country":
            bot.send_message(call.message.chat.id, f"🌍 **معلومات الدولة:**\nيتم جلب هذه الدولة من إعدادات حساب المستخدم (Region) في سيرفرات تيك توك. وهي تعكس الدولة التي تم تسجيل الحساب منها.", parse_mode="Markdown")
        
        elif action == "level":
            # جلب البيانات سريعاً لتقييم المستوى
            url = "https://tiktok-scraper7.p.rapidapi.com/user/info"
            res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username}).json()
            if res.get("code") == 0:
                followers = res["data"]["stats"].get("followerCount", 0)
                level = get_account_level(followers)
                bot.send_message(call.message.chat.id, f"⭐ **مستوى الحساب:** {level}\n(بناءً على عدد المتابعين: {followers:,})", parse_mode="Markdown")
            
        elif action == "contact":
            url = "https://tiktok-scraper7.p.rapidapi.com/user/info"
            res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username}).json()
            if res.get("code") == 0:
                bio = res["data"]["user"].get("signature", "")
                emails = re.findall(r'[\w\.-]+@[\w\.-]+', bio)
                phones = re.findall(r'\+?\d{8,15}', bio)
                text = "📧 **معلومات التواصل المستخرجة:**\n\n"
                text += f"البريد: {', '.join(emails) if emails else 'غير متاح للعامة'}\n"
                text += f"الرقم: {', '.join(phones) if phones else 'غير متاح للعامة'}\n"
                text += "\n*(ملاحظة: تيك توك يمنع استخراج الإيميلات المخفية، يتم استخراج المتاح في البايو فقط)*"
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

        elif action == "story":
            msg = bot.send_message(call.message.chat.id, "⏳ جاري البحث عن ستوري...")
            url = "https://tiktok-scraper7.p.rapidapi.com/user/story"
            res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username}).json()
            if res.get("code") == 0 and res.get("data"):
                bot.edit_message_text("✅ تم العثور على ستوري، جاري جلب الروابط...", chat_id=call.message.chat.id, message_id=msg.message_id)
                # إرسال رسالة توضيحية لعدم دعم الخطة المجانية لعرض الميديا المباشر حالياً إن لم يتوفر
                bot.send_message(call.message.chat.id, "🎬 **تنبيه:** تم الوصول لنقطة (Story API). بعض الفيديوهات تتطلب خطة مدفوعة في RapidAPI لتحميلها كفيديو مباشر في تيليجرام.")
            else:
                bot.edit_message_text("❌ لا توجد ستوري نشطة لهذا الحساب حالياً، أو الحساب خاص.", chat_id=call.message.chat.id, message_id=msg.message_id)

        elif action in ["followers", "following"]:
            endpoint = "user/followers" if action == "followers" else "user/followings"
            msg = bot.send_message(call.message.chat.id, f"⏳ جاري جلب القائمة...")
            url = f"https://tiktok-scraper7.p.rapidapi.com/{endpoint}"
            res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": target_username, "count": 10}).json()
            
            if res.get("code") == 0 and res.get("data") and "userList" in res["data"]:
                usersList = res["data"]["userList"]
                if not usersList:
                    bot.edit_message_text("❌ القائمة فارغة أو مخفية بقرار الخصوصية.", chat_id=call.message.chat.id, message_id=msg.message_id)
                    return
                text = "👥 **أحدث الحسابات في القائمة:**\n\n"
                for u in usersList[:10]:
                    text += f"👤 {u.get('user', {}).get('nickname', 'بدون اسم')} | `@{u.get('user', {}).get('uniqueId', '')}`\n"
                bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("⚠️ تعذر جلب القائمة. قد يكون الحساب خاصاً أو الخطة الحالية للـ API لا تدعم هذه القائمة.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    # === دوال الإدارة ===
    if call.from_user.id in ADMIN_IDS:
        if call.data == "stats":
            pass # (نفس الكود السابق للآدمن)
        elif call.data == "ban_user":
            pass
        elif call.data == "unban_user":
            pass
        elif call.data == "broadcast":
            pass

# ==========================================
# 🛠️ دالة جلب البيانات الأساسية 🛠️
# ==========================================

def process_profile_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    
    input_text = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري استخراج بيانات الحساب التفصيلية...")
    
    try:
        username = input_text.split("@")[1].split("?")[0].split("/")[0] if "@" in input_text else input_text.replace("@", "")

        url = "https://tiktok-scraper7.p.rapidapi.com/user/info"
        res = requests.get(url, headers={"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": RAPID_API_HOST}, params={"unique_id": username}).json()

        if res.get("code") == 0 and res.get("data"):
            user = res["data"].get("user", {})
            stats = res["data"].get("stats", {})

            # استخراج الدولة الحقيقية وترجمتها للعربية مع العلم
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

            # بناء النص النهائي (متطابق مع الصورة)
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
            # عرض الدولة الحقيقية مع العلم
            text += f"الدولة: {country_name} {country_flag}\n"
            # عرض يوزر البوت تبعك كما طلبت
            text += f"• تم هذا بواسطة بوت أمان فيوجن: @bdallhshay7\n"
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

            # الأزرار السفلية الحقيقية (تحمل يوزر الحساب ليتم استدعاؤه)
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
                    # إرسال الصورة كملف Document لتظهر مصغرة 
                    img_file = io.BytesIO(requests.get(avatar_url).content)
                    img_file.name = f"AmanFusion_{username}.jpg"
                    bot.send_document(message.chat.id, img_file, caption=text, parse_mode="HTML", reply_markup=markup)
                except:
                    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

        else:
            bot.edit_message_text("⚠️ لم أتمكن من العثور على هذا الحساب.", chat_id=message.chat.id, message_id=msg.message_id)

    except Exception as e:
        bot.edit_message_text("⚠️ حدث خطأ في الاتصال. تأكد من صحة اليوزر.", chat_id=message.chat.id, message_id=msg.message_id)

def process_download_link(message):
    bot.reply_to(message, f"⏳ جاري برمجة هذه الميزة...")

# ==========================================
# 🌐 إعدادات سيرفر Render 🌐
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return 'OK', 200
    return "Aman Fusion Bot is running!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
