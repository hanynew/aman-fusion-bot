import os
import logging
from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)

class StoryHunter:
    """
    قناص مزدوج الطبقات لجلب الستوريات.
    يهاجم عبر واجهات عامة، وإذا فشل يهاجم عبر واجهة مخصصة للستوري فقط.
    """
    def __init__(self):
        self.impersonate = "chrome120"
        self.timeout = 15
        # مفتاحك الخاص بـ RapidAPI
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")

    def hunt(self, username: str) -> list:
        username = username.lstrip("@").strip()
        stories = []
        
        # 🎯 الطبقة الأولى: الهجوم السريع عبر TikWM
        try:
            url = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=30"
            res = cffi_requests.get(url, impersonate=self.impersonate, timeout=self.timeout)
            
            if res.status_code == 200:
                videos = res.json().get("data", {}).get("videos", [])
                for v in videos:
                    # صيد الستوري من بين المنشورات
                    if v.get("is_story") == True or v.get("aweme_type") in [68, 69, 101] or v.get("duration") == 0:
                        stories.append({
                            "author_name": v.get("author", {}).get("nickname", "بدون اسم"),
                            "views": v.get("play_count") or v.get("stats", {}).get("playCount", 0),
                            "likes": v.get("digg_count") or v.get("stats", {}).get("diggCount", 0),
                            "shares": v.get("share_count") or v.get("stats", {}).get("shareCount", 0),
                            "video_url": v.get("play") or v.get("video", {}).get("playAddr", ""),
                            "images": v.get("images") or v.get("imagePost", {}).get("images", []),
                            "music_title": v.get("music_info", {}).get("title") or v.get("music", {}).get("title", "الصوت الأصلي"),
                            "music_url": v.get("music_info", {}).get("play") or v.get("music", {}).get("playUrl", "")
                        })
        except Exception as e:
            logger.error(f"StoryHunter Layer 1 Error: {e}")

        # إذا نجحت الطبقة الأولى، لا داعي لإكمال الهجوم
        if len(stories) > 0:
            return stories

        # 🎯 الطبقة الثانية: الهجوم العميق والمخصص للستوري (عبر tiktok-scraper7)
        try:
            url = "https://tiktok-scraper7.p.rapidapi.com/user/story"
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
            }
            params = {"user_name": username}
            
            # نستخدم curl_cffi لتزوير البصمة حتى مع RapidAPI لضمان عدم حظر الطلب
            res = cffi_requests.get(url, headers=headers, params=params, impersonate=self.impersonate, timeout=self.timeout)
            
            if res.status_code == 200:
                data = res.json().get("data", {})
                
                # استخراج قائمة الستوريات بغض النظر عن هيكل الاستجابة
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("item_list", data.get("items", []))
                    
                for v in items:
                    # سحب الفيديو
                    video_url = ""
                    if v.get("video") and v["video"].get("play_addr"):
                        video_url = v["video"]["play_addr"].get("url_list", [""])[0]
                    elif v.get("play"):
                        video_url = v.get("play")
                        
                    # سحب الصور (إذا كانت الستوري صورة)
                    images = []
                    if v.get("image_post_info"):
                        for img in v["image_post_info"].get("images", []):
                            if img.get("display_image"):
                                images.append(img["display_image"].get("url_list", [""])[0])
                    elif v.get("images"):
                        images = v.get("images")
                        
                    # سحب الموسيقى
                    music_title = v.get("music", {}).get("title", "الصوت الأصلي")
                    music_url = ""
                    if v.get("music") and v["music"].get("play_url"):
                        music_url = v["music"]["play_url"].get("url_list", [""])[0]

                    stories.append({
                        "author_name": v.get("author", {}).get("nickname", "بدون اسم"),
                        "views": v.get("statistics", {}).get("play_count") or v.get("play_count", 0),
                        "likes": v.get("statistics", {}).get("digg_count") or v.get("digg_count", 0),
                        "shares": v.get("statistics", {}).get("share_count") or v.get("share_count", 0),
                        "video_url": video_url,
                        "images": images,
                        "music_title": music_title,
                        "music_url": music_url
                    })
        except Exception as e:
            logger.error(f"StoryHunter Layer 2 Error: {e}")

        return stories
