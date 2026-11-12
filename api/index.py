import os
import telebot
from flask import Flask, request

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

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

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            # طريقة القراءة المتوافقة مع Vercel
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            pass
        return "OK", 200
    else:
        return "Aman Fusion Bot is running!", 200
