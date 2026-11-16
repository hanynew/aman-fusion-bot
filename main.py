import os
import io
import re
import telebot
import certifi
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime

# استدعاء المحرك المركزي الذي قمنا ببنائه
from tiktok_engine.core.engine import TikTokExtractionEngine

# ==========================================
# ⚙️ إعدادات تشغيل Render الأساسية ⚙️
# ==========================================
app = Flask(__name__)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    BOT_USERNAME = f"@{bot.get_me().username}"
except:
    BOT_USERNAME = "@AmanFusion_bot"

MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['aman-fusion-bot']
users_collection = db['users']

ADMIN_IDS = [8227136699]
CHANNEL_USERNAME = "@AmanFusion"

# تهيئة المحرك المركزي
tiktok_engine = TikTokExtractionEngine()

# ==========================================
# 🌍 القواميس (الدول واللغات) 🌍
# ==========================================
COUNTRIES = {
    "SA": ("المملكة العربية السعودية", "🇸🇦"), "AE": ("الإمارات العربية المتحدة", "🇦🇪"),
    "EG": ("مصر", "🇪🇬"), "YE": ("اليمن", "🇾🇪"), "IQ": ("العراق", "🇮🇶"),
    "MA": ("المغرب", "🇲🇦"), "DZ": ("الجزائر", "🇩🇿"), "KW": ("الكويت", "🇰🇼"),
    "JO": ("الأردن", "🇯🇴"), "QA": ("قطر", "🇶🇦"), "BH": ("البحرين", "🇧🇭"),
    "OM": ("سلطنة عُمان", "🇴🇲"), "SD": ("السودان", "🇸🇩"), "LB": ("لبنان", "🇱🇧"),
    "SY": ("سوريا", "🇸🇾"), "US": ("الولايات المتحدة", "🇺🇸"), "GB": ("المملكة المتحدة", "🇬🇧"),
    "TR": ("تركيا", "🇹🇷"), "FR": ("فرنسا", "🇫🇷"), "DE": ("ألمانيا", "🇩🇪"),
    "IN": ("الهند", "🇮🇳"), "ID": ("إندونيسيا", "🇮🇩"), "RU": ("روسيا", "🇷🇺")
}

LANGUAGES = {
    "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية", "es": "الإسبانية",
    "tr": "التركية", "ur": "الأردية", "id": "الإندونيسية", "hi": "الهندية",
    "zh": "الصينية", "ru": "الروسية", "de": "الألمانية", "ja": "اليابانية", "ko": "الكورية"
}

def get_yes_no(val): return "نعم ✅" if val else "لا ❌"
def get_privacy(val): return "للجميع 🌍" if val == 0 else "مغلق ❌"

def get_country_info(code):
    if not code or code.upper() == "ZZ": return "غير محددة", ""
    return COUNTRIES.get(code.upper(), (code, ""))

def get_language_name(code):
    if not code: return "غير محددة"
    base_code = code.split("-")[0].lower()
    return LANGUAGES.get(base_code, code)

def get_account_level(followers):
    if followers > 1000000: return "أسطوري 🌟"
    elif followers > 100000: return "مشهور 🔥"
    elif followers > 10000: return "نجم صاعد ✨"
    elif followers > 1000: return "نشط 🚀"
    else: return "مبتدئ 🐣"

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

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🚀 START"), KeyboardButton("🛠 الخدمات"))
    return markup

# ==========================================
# 🟢 واجهة المستخدم 🟢
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

    if call.data.startswith("info_"):
        parts = call.data.split("_", 2)
        action = parts[1]
        target_username = parts[2]

        if action == "country":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"🌍 **معلومات الدولة:**\nتم استخراج الدولة بدقة لـ @{target_username}.", parse_mode="Markdown")
        
        elif action == "level":
            bot.answer_callback_query(call.id, "⏳ جاري التقييم...")
            data = tiktok_engine.extract_tiktok_profile(target_username)
            if data and data.get("status") == "success":
                followers = data["data"].get("followers", 0)
                bot.send_message(call.message.chat.id, f"⭐ **مستوى الحساب:** {get_account_level(followers)}\n(المتابعين: {followers:,})", parse_mode="Markdown")
            else: bot.send_message(call.message.chat.id, "⚠️ خطأ في الاتصال.")
            
        elif action == "contact":
            bot.answer_callback_query(call.id, "⏳ جاري البحث...")
            data = tiktok_engine.extract_tiktok_profile(target_username)
            if data and data.get("status") == "success":
                bio = data["data"].get("bio", "")
                emails = re.findall(r'[\w\.-]+@[\w\.-]+', bio)
                phones = re.findall(r'\+?\d{8,15}', bio)
                text = f"📧 **معلومات التواصل:**\nالبريد: {', '.join(emails) if emails else 'غير متاح'}\nالرقم: {', '.join(phones) if phones else 'غير متاح'}"
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            else: bot.send_message(call.message.chat.id, "⚠️ خطأ في الاتصال.")

        elif action in ["followers", "following"]:
            bot.answer_callback_query(call.id, "هذه الميزة تخضع للتطوير المعماري حالياً.")
            return

        elif action == "story":
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, "⏳ جاري فحص الستوريات عبر المحرك...")
            
            # جلب الستوريات من المحرك
            profile_data = tiktok_engine.extract_tiktok_profile(target_username)
            stories = profile_data.get("data", {}).get("stories_active", []) if profile_data.get("status") == "success" else []

            if stories:
                story_count = len(stories)
                text = f"<b>تم العثور على ستوريات لهذا الشخص</b>\n\n"
                text += f"المستخدم: @{target_username}\n"
                text += f"عدد الستوريات: {story_count}"
                
                markup = InlineKeyboardMarkup(row_width=3)
                buttons = [InlineKeyboardButton(f"#{i+1}", callback_data=f"getstory_{i}_{target_username}") for i in range(story_count)]
                markup.add(*buttons)
                
                bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=msg.message_id, parse_mode="HTML", reply_markup=markup)
            else:
                bot.edit_message_text("❌ لا توجد ستوريات نشطة لهذا الحساب حالياً.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    if call.data.startswith("getstory_"):
        parts = call.data.split("_", 2)
        story_index = int(parts[1])
        target_username = parts[2]
        
        bot.answer_callback_query(call.id, f"⏳ جاري تحميل الستوري #{story_index+1}...")
        
        profile_data = tiktok_engine.extract_tiktok_profile(target_username)
        stories = profile_data.get("data", {}).get("stories_active", []) if profile_data.get("status") == "success" else []

        if stories and story_index < len(stories):
            story = stories[story_index]
            
            author_data = story.get("author", {})
            author_nick = author_data.get("nickname", "بدون اسم")
            
            stats = story.get("stats", {})
            views = stats.get("playCount", 0)
            likes = stats.get("diggCount", 0)
            shares = stats.get("shareCount", 0)
            
            music_title = story.get("music", {}).get("title", "الصوت الأصلي")
            music_url = story.get("music", {}).get("playUrl", "")
            
            text = f"ستوري #{story_index+1}\nالاسم: {author_nick}\n"
            text += f"المشاهدات: {views}\nاللايكات: {likes}\nالمشاركات: {shares}"
            
            video_url = story.get("video", {}).get("playAddr", "")
            images = story.get("imagePost", {}).get("images", [])
            
            msg = bot.send_message(call.message.chat.id, "⏳ جاري الإرسال...")
            
            try:
                if video_url: bot.send_video(call.message.chat.id, video_url, caption=text, parse_mode="HTML")
                elif images:
                    img_url = images[0].get("imageURL", {}).get("urlList", [""])[0] if isinstance(images[0], dict) else images[0]
                    bot.send_photo(call.message.chat.id, img_url, caption=text, parse_mode="HTML")
                else: bot.send_message(call.message.chat.id, "⚠️ الستوري غير مدعومة.")
            except: bot.send_message(call.message.chat.id, "⚠️ فشل إرسال الوسائط.")
                
            bot.delete_message(chat_id=call.message.chat.id, message_id=msg.message_id)
            
            if music_url:
                audio_markup = InlineKeyboardMarkup()
                audio_markup.add(InlineKeyboardButton(f"🎧 {music_title}", url=music_url))
                bot.send_message(call.message.chat.id, f"🎵 **الصوت الأصلي**\n{BOT_USERNAME}", parse_mode="Markdown", reply_markup=audio_markup)
        else: bot.send_message(call.message.chat.id, "❌ لم تعد الستوري متاحة.")
        return

# ==========================================
# 🛠️ معالجة التقرير ودمج البيانات 🛠️
# ==========================================
def process_profile_link(message):
    if message.text == '/cancel':
        bot.reply_to(message, "تم الإلغاء.", reply_markup=get_main_reply_keyboard())
        return
    
    input_text = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري استخراج البيانات عبر محرك أمان فيوجن المركزي...")
    
    try:
        username = input_text.split("@")[1].split("?")[0].split("/")[0] if "@" in input_text else input_text.replace("@", "")

        # 🚀 الاستدعاء النظيف من المحرك
        engine_response = tiktok_engine.extract_tiktok_profile(username)

        if engine_response["status"] == "success":
            d = engine_response["data"]

            country_name, country_flag = get_country_info(d["region"])
            language = get_language_name(d["language"])
            
            bio_link = "(None)"
            
            text = f"اسم المستخدم: <code>{d['username']}</code>\n"
            text += f"المعرف: <code>{d['user_id']}</code>\n"
            text += f"الاسم: {d['nickname']}\n"
            text += f"المتابعين: {d['followers']}\n"
            text += f"يتابع: {d['following']}\n"
            text += f"الأصدقاء: {d['friends']}\n"
            text += f"الإعجابات: {d['likes']}\n"
            text += f"الفيديوهات: {d['videos']}\n"
            text += f"تاريخ الإنشاء: {d['create_time_formatted']}\n"
            text += f"تعديل اليوزر: {d['create_time_formatted']}\n" 
            text += f"تعديل الاسم: {d['modify_time_formatted']}\n"
            text += f"الدولة: {country_name} {country_flag}\n"
            text += f"• إنشاء هذا بواسطة أمان فيوجن: {BOT_USERNAME}\n"
            text += f"اللغة: {language}\n"
            text += f"حساب موثق: {get_yes_no(d['is_verified'])}\n"
            text += f"إعدادات التحميل: {get_privacy(d['download_setting'])}\n"
            text += f"حساب خاص: {get_yes_no(d['is_private'])}\n"
            text += f"يمتلك متجر: {get_yes_no(d['has_store'])}\n"
            text += f"يبيع على تيك توك: {get_yes_no(d['sells_on_tiktok'])}\n"
            text += f"إعدادات الدويتو: {get_privacy(d['duet_setting'])}\n"
            text += f"إعدادات النشر: {get_privacy(d['publish_setting'])}\n"
            text += f"إعدادات التعليقات: {get_privacy(d['comment_setting'])}\n"
            text += f"حساب منظمة: {get_yes_no(d['is_under_18'])}\n"
            text += f"علاقة الحساب: {d['account_relation']}\n"
            text += f"المفضلة مفتوحة: {get_yes_no(d['open_favorites'])}\n"
            text += f"حظر التضمين: {get_yes_no(d['embed_ban'])}\n"
            text += f"• إعدادات الملف الشخصي\n"
            text += f"عرض الموسيقى: {get_yes_no(d['show_music'])}\n"
            text += f"عرض الأسئلة: {get_yes_no(d['show_questions'])}\n"
            text += f"عرض القوائم: {get_yes_no(d['show_lists'])}\n"
            text += f"اقتراح ربط حساب: {get_yes_no(d['suggest_link'])}\n"
            text += f"توسيع القوائم: {get_yes_no(d['expand_lists'])}\n"
            text += f"إذن التضمين: {get_yes_no(d['embed_permission'])}\n"
            text += f"متوافق FTC: {get_yes_no(d['ftc_compliant'])}\n"
            text += f"حساب إعلانات وهمي: {get_yes_no(d['fake_ads'])}\n"
            text += f"البايو: {d['bio']}\n"
            text += f"الرابط في البايو: {bio_link}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("دولة الحساب الاصلية", callback_data=f"info_country_{username}"))
            markup.row(InlineKeyboardButton("قائمة المتابعين", callback_data=f"info_followers_{username}"), 
                       InlineKeyboardButton("قائمة المتابعة", callback_data=f"info_following_{username}"))
            markup.add(InlineKeyboardButton("معلومات الحساب ( بريد ، رقم )", callback_data=f"info_contact_{username}"))
            markup.row(InlineKeyboardButton("مستوى الحساب", callback_data=f"info_level_{username}"), 
                       InlineKeyboardButton("مشاهدة الستوري", callback_data=f"info_story_{username}"))

            bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)

            if d['avatar']:
                try:
                    img_file = io.BytesIO(requests.get(d['avatar']).content)
                    img_file.name = f"{username}.jpg"
                    bot.send_document(message.chat.id, img_file, caption=text, parse_mode="HTML", reply_markup=markup)
                except: bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
            else: bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

        else:
            bot.edit_message_text(f"⚠️ {engine_response['message']}", chat_id=message.chat.id, message_id=msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ حدث خطأ داخلي في المحرك: {e}", chat_id=message.chat.id, message_id=msg.message_id)

# ==========================================
# 🌐 إعدادات سيرفر Render (Webhook) 🌐
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        return 'OK', 200
    return "Aman Fusion Engine is running!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
