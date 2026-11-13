import os
import telebot
from flask import Flask, request

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك في أمان فيوجن 🛠️ | البوت متصل ويعمل بنجاح تام 🚀")

@app.route('/', methods=['POST'])
def webhook():
    # استخدام الطريقة الأضمن لقراءة البيانات
    json_data = request.get_json(silent=True)
    if json_data:
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Error', 400

@app.route('/')
def index():
    return "Aman Fusion Bot is running smoothly on Render!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))

