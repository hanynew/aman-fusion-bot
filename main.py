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

# === دالة فحص الاشتراك في القناة ===
def is_subscribed(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return True 

# === دالة مساعدة لتسجيل المستخدم ===
def register_user(user_id, first_name, username):
    users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "first_name": first_name,
                "username": username,
                "last_active": datetime.now()
            },
            "$setOnInsert": {
                "joined_date": datetime.now(),
                "is_banned": False
            }
        },
        upsert=True
    )

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
    
    text = f"مرحباً بك يا {first_name} في أمان فيوجن 🛠️\n\n"
    text += "✨ **يرجى اختيار الخدمة المطلوبة من القائمة أدناه:**"
    
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
        btn_channel = InlineKeyboardButton("📢 اضغط هنا للاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        btn_check = InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")
        markup.add(btn_channel)
        markup.add(btn_check)
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
        btn_stats = InlineKeyboardButton("📊 قائمة المشتركين", callback_data="stats")
        btn_ban = InlineKeyboardButton("⛔️ حظر", callback_data="ban_user")
        btn_unban = InlineKeyboardButton("🔓 فك حظر", callback_data="unban_user")
        btn_banned_list = InlineKeyboardButton(f"🚫 المحظورين ({banned_count})", callback_data="banned_list")
        btn_broadcast = InlineKeyboardButton("📢 إذاعة للكل", callback_data="broadcast")

        markup.add(btn_stats)
        markup.row(btn_ban, btn_unban)
        markup.add(btn_banned_list)
        markup.add(btn_broadcast)

        text = "👑 <b>لوحة تحكم أمان فيوجن</b> 👑\n\n"
        text += f"👥 إجمالي المشتركين: <code>{users_count}</code>\n"
        text += f"🚫 المحظورين: <code>{banned_count}</code>\n\n"
        text += "اختر الإجراء المطلوب من الأزرار أدناه:"

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
        msg = bot.send_message(call.message.chat.id, "📊 أرسل الآن رابط الحساب الذي تريد تحليله:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_profile_link)
        return
        
    if call.data == "service_download":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📥 أرسل الآن رابط الفيديو (تيك توك، انستجرام، الخ) لتحميله بدون علامة مائية:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_download_link)
        return
        
    if call.data == "service_media":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔍 أرسل الكلمة المفتاحية للبحث عن الوسائط:\n(أو أرسل /cancel للإلغاء)")
        bot.register_next_step_handler(msg, process_media_search)
        return

    # --- أزرار الآدمن ---
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔️ غير مصرح لك.", show_alert=True)
        return

    if call.data == "stats":
        bot.answer_callback_query(call.id, "جاري جلب قائمة المشتركين...")
        users = list(users_collection.find({}))
        now = datetime.now()

        if not users:
            bot.send_message(call.message.chat.id, "لا يوجد مشتركين مسجلين بعد.")
            return

        text = "📊 <b>قائمة المشتركين (بدون أرقام جوال):</b>\n🟢 نشط | 🟡 متوسط | 🔴 منقطع\n〰️〰️〰️〰️〰️〰️\n"
        for idx, u in enumerate(users, start=1):
            last_active = u.get("last_active", u.get("joined_date", now))
            diff = now - last_active
            status = "🟢" if diff <= timedelta(days=1) else "🟡" if diff <= timedelta(days=7) else "🔴"
            user_id = u["_id"]
            name = html.escape(str(u.get("first_name", "بدون اسم")))
            username = f"@{html.escape(str(u.get('username')))}" if u.get("username") else "لا يوجد يوزر"
            ban_tag = " [محظور 🚫]" if u.get("is_banned", False) else ""
            text += f"{idx}. {status} <b>{name}</b>{ban_tag}\n   🆔 <code>{user_id}</code> | {username}\n"

        bot.send_message(call.message.chat.id, text, parse_mode="HTML")

    elif call.data == "banned_list":
        banned_users = list(users_collection.find({"is_banned": True}))
        if not banned_users:
            bot.answer_callback_query(call.id, "لا يوجد مستخدمين محظورين حالياً ✅", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        text = "🚫 <b>قائمة المستخدمين المحظورين:</b>\n\n"
        for idx, u in enumerate(banned_users, start=1):
            name = html.escape(str(u.get("first_name", "بدون اسم")))
            username = f"(@{html.escape(str(u.get('username')))})" if u.get("username") else ""
            text += f"{idx}. <b>{name}</b> {username}\n   🆔 <code>{u['_id']}</code>\n"
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
    msg = bot.reply_to(message, "⏳ جاري استخراج بيانات الحساب... يرجى الانتظار.")
    
    try:
        username = input_text
        if "tiktok.com" in username:
            if "@" in username:
                username = username.split("@")[1].split("?")[0].split("/")[0]
            else:
                bot.edit_message_text("⚠️ عذراً، يرجى إرسال يوزر الحساب أو رابط مباشر للحساب.", chat_id=message.chat.id, message_id=msg.message_id)
                return
                
        username = username.replace("@", "")

        text = f"📊 <b>بيانات حساب تيك توك</b> 📊\n\n"
        text += f"👤 <b>الاسم:</b> (جاري الربط)\n"
        text += f"🔗 <b>اليوزر:</b> <code>@{username}</code>\n"
        text += f"👥 <b>المتابعين:</b> (جاري الربط)\n"
        text += f"👣 <b>يتابع:</b> (جاري الربط)\n"
        text += f"❤️ <b>الإعجابات:</b> (جاري الربط)\n\n"
        text += f"📝 <b>البايو:</b>\n(جاري الربط)\n"
        
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
        
    except Exception:
        bot.edit_message_text("⚠️ حدث خطأ غير متوقع. يرجى التأكد من كتابة اليوزر بشكل صحيح.", chat_id=message.chat.id, message_id=msg.message_id)

def process_download_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء. يمكنك اختيار خدمة أخرى من القائمة /start")
        return
    bot.reply_to(message, f"⏳ جاري معالجة الرابط وجلب الفيديو بدون علامة مائية...\n\n(هنا سنقوم بربط أداة التحميل الفعلية)")

def process_media_search(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء. يمكنك اختيار خدمة أخرى من القائمة /start")
        return
    bot.reply_to(message, f"⏳ جاري البحث عن الوسائط...\n\n(هنا سنقوم بربط محرك البحث)")

# ==========================================
# 🔐 دوال تنفيذ الحظر والإذاعة للآدمن 🔐
# ==========================================

def process_ban(message):
    if message.text and message.text.strip() == "/cancel":
        bot.reply_to(message, "تم إلغاء العملية.")
        return
    try:
        target_id = int(message.text.strip())
        if target_id in ADMIN_IDS:
            bot.reply_to(message, "⚠️ لا يمكنك حظر حساب الإدارة!")
            return
        result = users_collection.update_one({"_id": target_id}, {"$set": {"is_banned": True}})
        if result.matched_count > 0:
            bot.reply_to(message, f"✅ تم حظر المستخدم <code>{target_id}</code> بنجاح.", parse_mode="HTML")
        else:
            bot.reply_to(message, "⚠️ هذا الآي دي غير مسجل في البوت.")
    except Exception:
        bot.reply_to(message, "⚠️ خطأ: يرجى إرسال أرقام الآي دي فقط.")

def process_unban(message):
    if message.text and message.text.strip() == "/cancel":
        bot.reply_to(message, "تم إلغاء العملية.")
        return
    try:
        target_id = int(message.text.strip())
        result = users_collection.update_one({"_id": target_id}, {"$set": {"is_banned": False}})
        if result.matched_count > 0:
            bot.reply_to(message, f"✅ تم رفع الحظر عن المستخدم <code>{target_id}</code> بنجاح.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"⚠️ الآي دي <code>{target_id}</code> غير موجود في قاعدة البيانات.", parse_mode="HTML")
    except Exception:
        bot.reply_to(message, "⚠️ خطأ: يرجى إرسال أرقام الآي دي فقط.")

def process_broadcast(message):
    if message.text and message.text.strip() == "/cancel":
        bot.reply_to(message, "تم إلغاء الإذاعة.")
        return
    
    bot.reply_to(message, "⏳ جاري إرسال الإذاعة لجميع المشتركين... يرجى الانتظار.")
    users = users_collection.find({"is_banned": False})
    
    success = 0
    failed = 0
    for u in users:
        try:
            bot.copy_message(u["_id"], message.chat.id, message.message_id)
            success += 1
        except Exception:
            failed += 1
            
    bot.reply_to(message, f"📢 <b>تم الانتهاء من الإذاعة بنجاح!</b>\n\n✅ وصلت إلى: {success} مشترك\n❌ فشلت مع: {failed} مشترك (ربما حظروا البوت)", parse_mode="HTML")

# ==========================================
# 🌐 إعدادات سيرفر Render (Webhook) 🌐
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return "Aman Fusion Bot is running!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
