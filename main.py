import os
import telebot
import certifi
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime
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

# === قائمة الآدمن ===
# تم وضع الـ ID الخاص بك كمدير
ADMIN_IDS = [8227136699] 

# === 1. أمر البداية (تسجيل المشتركين) ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # تسجيل المستخدم إذا لم يكن مسجلاً مسبقاً
    if not users_collection.find_one({"_id": user_id}):
        users_collection.insert_one({
            "_id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_date": datetime.now(),
            "is_banned": False
        })
        
    bot.reply_to(message, f"مرحباً بك يا {first_name} في أمان فيوجن 🛠️ | البوت متصل وقاعدة البيانات تعمل بنجاح 🚀")

# === 2. أمر لوحة الآدمن (مع الأزرار الشفافة) ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if user_id in ADMIN_IDS:
        users_count = users_collection.count_documents({})
        
        # إنشاء لوحة المفاتيح الشفافة
        markup = InlineKeyboardMarkup()
        
        # إنشاء الأزرار
        btn_broadcast = InlineKeyboardButton("📢 إرسال رسالة للكل", callback_data="broadcast")
        btn_stats = InlineKeyboardButton("📊 إحصائيات مفصلة", callback_data="stats")
        btn_ban = InlineKeyboardButton("⛔️ حظر مستخدم", callback_data="ban_user")
        
        # ترتيب الأزرار (زر الإرسال فوق، وزري الإحصائيات والحظر تحته)
        markup.add(btn_broadcast)
        markup.row(btn_stats, btn_ban)
        
        text = "👑 **مرحباً بك في لوحة تحكم أمان فيوجن** 👑\n\n"
        text += f"👥 إجمالي المشتركين: `{users_count}`\n\n"
        text += "اختر الإجراء المطلوب من الأزرار أدناه:"
        
        bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.reply_to(message, "⛔️ عذراً، هذه اللوحة مخصصة للإدارة فقط.")

# === 3. أمر مساعد لمعرفة الـ ID ===
@bot.message_handler(commands=['myid'])
def send_id(message):
    bot.reply_to(message, f"الآي دي الخاص بك هو: `{message.from_user.id}`", parse_mode="Markdown")

# === إعدادات سيرفر Render (Webhook) ===
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
