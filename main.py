import os
import telebot
import certifi  # المكتبة الجديدة لحل مشكلة الـ SSL
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime

# === إعدادات البوت والاتصال ===
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# === ربط قاعدة بيانات MongoDB (مع حل مشكلة الحماية) ===
MONGO_URI = os.environ.get('MONGO_URI')
# تم إضافة tlsCAFile لتعريف شهادة الأمان وإصلاح خطأ Render
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['aman-fusion-bot']
users_collection = db['users']

# === قائمة الآدمن ===
# ⚠️ مهم: ضع رقم الـ ID الخاص بك هنا بدلاً من هذا الرقم الافتراضي
ADMIN_IDS = [8227136699] 

# === 1. أمر البداية (تسجيل المشتركين) ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    if not users_collection.find_one({"_id": user_id}):
        users_collection.insert_one({
            "_id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_date": datetime.now(),
            "is_banned": False
        })
        
    bot.reply_to(message, f"مرحباً بك يا {first_name} في أمان فيوجن 🛠️ | البوت متصل وقاعدة البيانات تعمل بنجاح 🚀")

# === 2. أمر لوحة الآدمن ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if user_id in ADMIN_IDS:
        users_count = users_collection.count_documents({})
        text = "👑 **لوحة تحكم الإدارة** 👑\n\n"
        text += f"👥 عدد المشتركين الحالي: `{users_count}`\n\n"
        text += "*(قريباً: أزرار الحظر، الإحصائيات، والإرسال للكل...)*"
        bot.reply_to(message, text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "⛔️ عذراً، هذه اللوحة مخصصة للإدارة فقط.")

# === 3. أمر مساعد لمعرفة الـ ID الخاص بك ===
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
