import os
import telebot
from http.server import BaseHTTPRequestHandler

# جلب التوكن
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

# أمر البدء
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك في أمان فيوجن 🛠️ | البوت يعمل بنجاح!")

# إعداد خادم Vercel الأساسي
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            update = telebot.types.Update.de_json(post_data)
            bot.process_new_updates([update])
            
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("Aman Fusion Bot is running perfectly!".encode('utf-8'))
