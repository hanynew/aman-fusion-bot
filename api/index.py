import os
import telebot
from flask import Flask, request

# جلب التوكن من إعدادات Vercel
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# الرد على أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "مرحباً بك في أمان فيوجن 🛠️ | Aman Fusion\n\n"
        "أنا بوت خدمات شامل، يمكنني مساعدتك في:\n"
        "📱 جلب بيانات حسابات تيك توك\n"
        "📥 تحميل الفيديوهات بدون علامة مائية\n"
        "🗣️ تحويل النص لصوت والعكس\n"
        "🎵 تحميل الأغاني من الصوتيات\n\n"
        "سيتم تفعيل هذه الخدمات قريباً!"
    )
    bot.reply_to(message, welcome_text)

# تشغيل البوت واستقبال الرسائل
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Aman Fusion Bot is running!", 200
