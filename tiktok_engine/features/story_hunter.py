import logging
from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)

class StoryHunter:
    """
    سكربت متخصص فقط في الهجوم على خوادم الوسائط لجلب الستوريات النشطة (Stories).
    معزول تماماً لضمان عدم تعطيل استخراج بيانات الملف الشخصي.
    """
    def __init__(self):
        # استخدام متصفح وهمي لتخطي الجدار الناري
        self.impersonate = "chrome120"
        self.timeout = 15

    def hunt(self, username: str) -> list:
        username = username.lstrip("@").strip()
        stories = []
        
        try:
            # طلب أحدث المنشورات للبحث عن الستوريات النشطة بداخلها
            url = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=20"
            res = cffi_requests.get(url, impersonate=self.impersonate, timeout=self.timeout)
            
            if res.status_code == 200:
                js_data = res.json()
                videos = js_data.get("data", {}).get("videos", [])
                
                for v in videos:
                    # الخوارزمية: تيك توك يميز الستوري بهذه المعرفات الرقمية أو بمدة 0
                    if v.get("is_story") == True or v.get("aweme_type") in [68, 69, 101] or v.get("duration") == 0:
                        
                        # تنسيق البيانات وتغليفها لتكون جاهزة لزر التيليجرام
                        stories.append({
                            "author_name": v.get("author", {}).get("nickname", "بدون اسم"),
                            "views": v.get("play_count") or v.get("stats", {}).get("playCount", 0),
                            "likes": v.get("digg_count") or v.get("stats", {}).get("diggCount", 0),
                            "shares": v.get("share_count") or v.get("stats", {}).get("shareCount", 0),
                            "video_url": v.get("play") or v.get("video", {}).get("playAddr", ""),
                            # الستوري قد تكون صورة بدلاً من فيديو
                            "images": v.get("images") or v.get("imagePost", {}).get("images", []),
                            "music_title": v.get("music_info", {}).get("title") or v.get("music", {}).get("title", "الصوت الأصلي"),
                            "music_url": v.get("music_info", {}).get("play") or v.get("music", {}).get("playUrl", "")
                        })
        except Exception as e:
            logger.error(f"StoryHunter Error: {e}")
            
        return stories
