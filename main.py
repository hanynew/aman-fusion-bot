import os
import html
import telebot
import certifi
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# === إعدادات البوت والاتصال ===
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# === ربط قاعدة بيانات MongoDB ===
MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['aman-fusion-bot']
users_collection = db['users']

# === قائمة الآدمن وإعدادات القناة ===
ADMIN_IDS = [8227136699]
CHANNEL_USERNAME = "@AmanFusion"

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
    if not timestamp or timestamp == 0:
        return "غير متوفر"
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime('%H:%M:%S %d-%m-%Y')
    except:
        return "غير متوفر"

def get_bool_emoji(val):
    return "✅" if val else "❌"

def get_privacy_status(val):
    return "للجميع 🌍" if val == 0 else "مغلق ❌"

# ==========================================
# 🟢 قسم واجهة المستخدم (الخدمات الرئيسية) 🟢
# ==========================================

def send_main_menu(chat_id, first_name):
    markup = InlineKeyboardMarkup()
    btn_profile = InlineKeyboardButton("📊 بيانات الحساب", callback_data="service_profile")
    btn_download = InlineKeyboardButton("📥 تحميل بدون علامة مائية", callback_data="service_download")
    btn_media = InlineKeyboardButton("🔍 البحث عن الوسائط", callback_data="service_media")
    markup.add(btn_profile)
    markup.add(btn_download)
    markup.add(btn_media)
    text = f"مرحباً بك يا {first_name} في أمان فيوجن 🛠️\n\n✨ **يرجى اختيار الخدمة المطلوبة من القائمة أدناه:**"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "مستخدم"
    username = message.from_user.username
    user_data = users_collection.find_one({"_id": user_id})
    
    if user_data and user_data.get("is_banned", False):
        bot.reply_to(message, "⛔️ عذراً، لقد تم حظرك من استخدام هذا البوت.")
        return

    if not is_subscribed(CHANNEL_USERNAME, user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 اضغط هنا للاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        bot.reply_to(message, f"👋 أهلاً بك يا {first_name}\n\n⚠️ عذراً، لا يمكنك استخدام البوت إلا بعد الاشتراك في قناتنا الرسمية.\n\nاشترك من الزر بالأسفل ثم اضغط (تحقق من الاشتراك) 👇", reply_markup=markup)
        return

    register_user(user_id, first_name, username)
    send_main_menu(message.chat.id, first_name)

# ==========================================
# 🔴 قسم لوحة تحكم الإدارة (الآدمن) 🔴
# ==========================================

@bot.message_handler(commands=['myid'])
def send_id(message):
    bot.reply_to(message, f"الآي دي الخاص بك هو: <code>{message.from_user.id}</code>", parse_mode="HTML")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        users_count = users_collection.count_documents({})
        banned_count = users_collection.count_documents({"is_banned": True})
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 قائمة المشتركين", callback_data="stats"))
        markup.row(InlineKeyboardButton("⛔️ حظر", callback_data="ban_user"), InlineKeyboardButton("🔓 فك حظر", callback_data="unban_user"))
        markup.add(InlineKeyboardButton(f"🚫 المحظورين ({banned_count})", callback_data="banned_list"))
        markup.add(InlineKeyboardButton("📢 إذاعة للكل", callback_data="broadcast"))
        text = f"👑 <b>لوحة تحكم أمان فيوجن</b> 👑\n\n👥 إجمالي المشتركين: <code>{users_count}</code>\n🚫 المحظورين: <code>{banned_count}</code>\n\nاختر الإجراء المطلوب من الأزرار أدناه:"
        bot.reply_to(message, text, parse_mode="HTML", reply_markup=markup)
    else:
        bot.reply_to(message, "⛔️ عذراً، هذه اللوحة مخصصة للإدارة فقط.")

# ==========================================
# ⚙️ معالجة جميع ضغطات الأزرار (خدمات + آدمن) ⚙️
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # --- أزرار الخدمات ---
    if call.data == "check_sub":
        if is_subscribed(CHANNEL_USERNAME, call.from_user.id):
            bot.answer_callback_query(call.id, "✅ تم التحقق، شكراً لاشتراكك!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            register_user(call.from_user.id, call.from_user.first_name, call.from_user.username)
            send_main_menu(call.message.chat.id, call.from_user.first_name)
        else:
            bot.answer_callback_query(call.id, "❌ لم تقم بالاشتراك بعد! اشترك أولاً ثم اضغط تحقق.", show_alert=True)
        return

    if call.data == "service_profile":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📊 أرسل الآن يوزر الحساب الذي تريد تحليله مسبوقاً بـ @ (أو رابط الحساب):\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_profile_link)
        return
        
    if call.data == "service_download":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📥 أرسل الآن رابط الفيديو لتحميله بدون علامة مائية:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_download_link)
        return
        
    if call.data == "service_media":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔍 أرسل الكلمة المفتاحية للبحث عن الوسائط:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_media_search)
        return

    # --- أزرار عرض الحساب (تعمل كرد أولي للآزرار الجديدة) ---
    if call.data.startswith("info_btn_"):
        btn_type = call.data.split("_")[2]
        if btn_type == "country":
            bot.answer_callback_query(call.id, "🌍 سيتم برمجة جلب الدولة المتقدم قريباً!", show_alert=True)
        elif btn_type == "following":
            bot.answer_callback_query(call.id, "👣 سيتم برمجة سحب قائمة من يتابعهم قريباً!", show_alert=True)
        elif btn_type == "followers":
            bot.answer_callback_query(call.id, "👥 سيتم برمجة سحب قائمة المتابعين قريباً!", show_alert=True)
        elif btn_type == "contact":
            bot.answer_callback_query(call.id, "📧 سيتم برمجة فحص البريد والرقم قريباً!", show_alert=True)
        elif btn_type == "level":
            bot.answer_callback_query(call.id, "⭐ سيتم تحليل مستوى الحساب قريباً!", show_alert=True)
        elif btn_type == "story":
            bot.answer_callback_query(call.id, "🎬 سيتم برمجة تحميل الستوري قريباً!", show_alert=True)
        return

    # --- أزرار الآدمن ---
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔️ غير مصرح لك.", show_alert=True)
        return

    if call.data == "stats":
        bot.answer_callback_query(call.id, "جاري جلب قائمة المشتركين...")
        users = list(users_collection.find({}))
        if not users:
            bot.send_message(call.message.chat.id, "لا يوجد مشتركين مسجلين بعد.")
            return
        text = "📊 <b>قائمة المشتركين (بدون أرقام جوال):</b>\n🟢 نشط | 🟡 متوسط | 🔴 منقطع\n〰️〰️〰️〰️〰️〰️\n"
        now = datetime.now()
        for idx, u in enumerate(users, start=1):
            diff = now - u.get("last_active", u.get("joined_date", now))
            status = "🟢" if diff <= timedelta(days=1) else "🟡" if diff <= timedelta(days=7) else "🔴"
            username = f"@{html.escape(str(u.get('username')))}" if u.get("username") else "لا يوجد يوزر"
            text += f"{idx}. {status} <b>{html.escape(str(u.get('first_name', 'بدون اسم')))}</b>\n   🆔 <code>{u['_id']}</code> | {username}\n"
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")

    elif call.data == "banned_list":
        banned_users = list(users_collection.find({"is_banned": True}))
        if not banned_users:
            bot.answer_callback_query(call.id, "لا يوجد مستخدمين محظورين حالياً ✅", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        text = "🚫 <b>قائمة المستخدمين المحظورين:</b>\n\n"
        for idx, u in enumerate(banned_users, start=1):
            username = f"(@{html.escape(str(u.get('username')))})" if u.get("username") else ""
            text += f"{idx}. <b>{html.escape(str(u.get('first_name', 'بدون اسم')))}</b> {username}\n   🆔 <code>{u['_id']}</code>\n"
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")

    elif call.data == "ban_user":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "⛔️ أرسل الآن رقم الآي دي (ID) الخاص بالمستخدم لحظر حسابه:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_ban)

    elif call.data == "unban_user":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔓 أرسل الآن رقم الآي دي (ID) الخاص بالمستخدم لرفع الحظر عنه:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_unban)

    elif call.data == "broadcast":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الآن الرسالة (نص، صورة، فيديو، أو ملف) التي تريد إذاعتها للكل:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_broadcast)


# ==========================================
# 🛠️ دوال معالجة الخدمات (الرد على المستخدم) 🛠️
# ==========================================

def process_profile_link(message):
    if message.text and message.text.strip() == '/cancel':
        bot.reply_to(message, "تم الإلغاء. يمكنك اختيار خدمة أخرى من القائمة /start")
        return
    
    input_text = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري استخراج بيانات الحساب التفصيلية... يرجى الانتظار.")
    
    try:
        username = input_text
        if "tiktok.com" in username:
            if "@" in username:
                username = username.split("@")[1].split("?")[0].split("/")[0]
            else:
                bot.edit_message_text("⚠️ يرجى إرسال يوزر الحساب مسبوقاً بـ @ أو رابط مباشر.", chat_id=message.chat.id, message_id=msg.message_id)
                return
        username = username.replace("@", "")

        # الاتصال بـ API
        url = "https://tiktok-scraper7.p.rapidapi.com/user/info"
        querystring = {"unique_id": username}
        headers = {
            "x-rapidapi-key": "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87",
            "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if data.get("code") == 0 and data.get("data"):
            user = data["data"].get("user", {})
            stats = data["data"].get("stats", {})

            # استخراج البيانات المتطابقة مع الصورة
            uid = user.get("id", "غير متوفر")
            nickname = user.get("nickname", "غير متوفر")
            followers = stats.get("followerCount", 0)
            following = stats.get("followingCount", 0)
            friends = stats.get("friendCount", 0)
            hearts = stats.get("heartCount", 0)
            videos = stats.get("videoCount", 0)
            
            create_time = format_date(user.get("createTime"))
            modify_time = format_date(user.get("nickNameModifyTime"))
            
            region = user.get("region", "غير متوفر")
            language = user.get("language", "English")
            is_verified = get_bool_emoji(user.get("verified", False))
            is_private = get_bool_emoji(user.get("secret", False))
            has_store = get_bool_emoji(user.get("hasCommerceEntry", False))
            
            download_setting = get_privacy_status(user.get("downloadSetting", 0))
            duet_setting = get_privacy_status(user.get("duetSetting", 0))
            comment_setting = get_privacy_status(user.get("commentSetting", 0))
            
            bio = user.get("signature", "")
            bio_link = user.get("bioLink", {}).get("link", "(None)")
            avatar_url = user.get("avatarLarger")

            # بناء النص بنفس التنسيق المطلوب
            text = f"اسم المستخدم: <code>{username}</code>\n"
            text += f"المعرف: <code>{uid}</code>\n"
            text += f"الاسم: {nickname}\n"
            text += f"المتابعين: {followers:,}\n"
            text += f"يتابع: {following:,}\n"
            text += f"الأصدقاء: {friends:,}\n"
            text += f"الإعجابات: {hearts:,}\n"
            text += f"الفيديوهات: {videos:,}\n"
            text += f"تاريخ الإنشاء: {create_time}\n"
            text += f"تعديل الاسم: {modify_time}\n"
            text += f"الدولة: {region} 🌍\n"
            text += f"اللغة: {language}\n"
            text += f"حساب موثق: {is_verified}\n"
            text += f"إعدادات التحميل: {download_setting}\n"
            text += f"حساب خاص: {is_private}\n"
            text += f"يمتلك متجر: {has_store}\n"
            text += f"إعدادات الدويتو: {duet_setting}\n"
            text += f"إعدادات التعليقات: {comment_setting}\n"
            text += f"البايو: {bio}\n"
            text += f"الرابط في البايو: {bio_link}\n"

            # إنشاء الأزرار السفلية المطابقة للصورة
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("دولة الحساب الاصلية", callback_data=f"info_btn_country"))
            markup.row(InlineKeyboardButton("قائمة المتابعين", callback_data="info_btn_followers"), 
                       InlineKeyboardButton("قائمة المتابعة", callback_data="info_btn_following"))
            markup.add(InlineKeyboardButton("معلومات الحساب ( بريد ، رقم )", callback_data="info_btn_contact"))
            markup.row(InlineKeyboardButton("مستوى الحساب", callback_data="info_btn_level"), 
                       InlineKeyboardButton("مشاهدة الستوري", callback_data="info_btn_story"))

            # إرسال الصورة مع البيانات والأزرار
            bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
            if avatar_url:
                bot.send_photo(message.chat.id, avatar_url, caption=text, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

        else:
            bot.edit_message_text("⚠️ لم أتمكن من العثور على هذا الحساب.", chat_id=message.chat.id, message_id=msg.message_id)

    except Exception as e:
        bot.edit_message_text("⚠️ حدث خطأ أثناء الاتصال بالسيرفر. حاول مرة أخرى.", chat_id=message.chat.id, message_id=msg.message_id)


def process_download_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.")
        return
    bot.reply_to(message, f"⏳ جاري معالجة الرابط وجلب الفيديو بدون علامة مائية...\n\n(سنقوم برمجتها في الخطوة القادمة)")

def process_media_search(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.")
        return
    bot.reply_to(message, f"⏳ جاري البحث عن الوسائط...\n\n(سنقوم برمجتها لاحقاً)")

# ==========================================
# 🔐 دوال تنفيذ الحظر والإذاعة للآدمن 🔐
# ==========================================

def process_ban(message):
    if message.text == "/cancel": return
    try:
        target_id = int(message.text.strip())
        if target_id in ADMIN_IDS: return bot.reply_to(message, "⚠️ لا يمكنك حظر الإدارة!")
        users_collection.update_one({"_id": target_id}, {"$set": {"is_banned": True}})
        bot.reply_to(message, f"✅ تم حظر <code>{target_id}</code>", parse_mode="HTML")
    except:
        bot.reply_to(message, "⚠️ أرسل الآي دي فقط.")

def process_unban(message):
    if message.text == "/cancel": return
    try:
        target_id = int(message.text.strip())
        users_collection.update_one({"_id": target_id}, {"$set": {"is_banned": False}})
        bot.reply_to(message, f"✅ تم فك الحظر عن <code>{target_id}</code>", parse_mode="HTML")
    except:
        bot.reply_to(message, "⚠️ أرسل الآي دي فقط.")

def process_broadcast(message):
    if message.text == "/cancel": return
    bot.reply_to(message, "⏳ جاري الإذاعة...")
    success = failed = 0
    for u in users_collection.find({"is_banned": False}):
        try:
            bot.copy_message(u["_id"], message.chat.id, message.message_id)
            success += 1
        except:
            failed += 1
    bot.reply_to(message, f"📢 <b>تمت الإذاعة!</b>\nنجاح: {success}\nفشل: {failed}", parse_mode="HTML")

# ==========================================
# 🌐 إعدادات سيرفر Render (Webhook) 🌐
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return 'OK', 200
    return "Aman Fusion Bot is running!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
