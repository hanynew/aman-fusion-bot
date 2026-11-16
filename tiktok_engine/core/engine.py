import logging
from typing import Dict, Any
from tiktok_engine.providers.tokapi_provider import TokAPIProvider
from tiktok_engine.providers.tikwm_provider import TikWMProvider

logger = logging.getLogger(__name__)

class TikTokExtractionEngine:
    def __init__(self):
        # الاعتماد الكلي على الواجهات القوية فقط
        self.tokapi_provider = TokAPIProvider()
        self.tikwm_provider = TikWMProvider()

    def _normalize_date(self, timestamp) -> str:
        if not timestamp or str(timestamp) == "0" or str(timestamp) == "-1":
            return "غير متوفر"
        try:
            ts = int(timestamp)
            if len(str(ts)) > 10: ts = ts / 1000
            from datetime import datetime
            return datetime.fromtimestamp(ts).strftime('%H:%M:%S %d-%m-%Y')
        except Exception:
            return "غير متوفر"

    def extract_tiktok_profile(self, username: str) -> Dict[str, Any]:
        result = {"status": "error", "message": "حدث خطأ غير معروف", "data": None}
        
        # 1. السحب المباشر السريع من الواجهة الاحترافية (بدون تأخير الواجهات المجانية)
        tok_data = self.tokapi_provider.get_profile(username)
        
        if not tok_data or not tok_data.get("uid"):
            result["message"] = "لم أتمكن من العثور على هذا الحساب."
            return result

        # 2. بناء هيكل البيانات الاحترافي
        create_time = self._normalize_date(tok_data.get("create_time"))
        modify_time = self._normalize_date(tok_data.get("unique_id_modify_time"))
        
        if create_time != "غير متوفر" and create_time == modify_time:
            modify_time = "لم يتم التعديل"
        elif modify_time == "غير متوفر" and create_time != "غير متوفر":
            modify_time = "لم يتم التعديل"

        # 3. صائد الدولة النهائي (الاحتياطي)
        region = tok_data.get("region", "")
        if not region or region.upper() in ["US", "ZZ"]:
            recent_posts = self.tikwm_provider.get_recent_posts(username, count=2)
            if recent_posts:
                vid_region = recent_posts[0].get("region")
                if vid_region:
                    region = vid_region

        # 4. محرك الستوري (عبر TikWM مباشرة)
        stories = []
        tikwm_posts = self.tikwm_provider.get_recent_posts(username, count=20)
        for v in tikwm_posts:
            if v.get("is_story") == True or v.get("aweme_type") in [68, 69, 101] or v.get("duration") == 0:
                stories.append(v)

        result["status"] = "success"
        result["message"] = "تم الاستخراج بنجاح"
        
        # ربط البيانات
        avatar_url = ""
        if tok_data.get("avatar_larger") and tok_data["avatar_larger"].get("url_list"):
            avatar_url = tok_data["avatar_larger"]["url_list"][0]

        result["data"] = {
            "username": username,
            "user_id": tok_data.get("uid", "غير متوفر"),
            "nickname": tok_data.get("nickname", "غير متوفر"),
            "bio": tok_data.get("signature", ""),
            "avatar": avatar_url,
            "region": region,
            "language": tok_data.get("language", "en"),
            "is_verified": tok_data.get("custom_verify", "") != "",
            "is_private": tok_data.get("secret", False),
            
            "followers": tok_data.get("follower_count", 0),
            "following": tok_data.get("following_count", 0),
            "friends": tok_data.get("friend_count", 0),
            "likes": tok_data.get("total_favorited", 0),
            "videos": tok_data.get("aweme_count", 0),
            
            "create_time_formatted": create_time,
            "modify_time_formatted": modify_time,
            "stories_active": stories,
            
            "download_setting": tok_data.get("download_setting", 0),
            "has_store": tok_data.get("has_commerce_entry", False),
            "sells_on_tiktok": tok_data.get("with_commerce_entry", False),
            "duet_setting": tok_data.get("duet_setting", 0),
            "publish_setting": tok_data.get("publish_setting", 0),
            "comment_setting": tok_data.get("comment_setting", 0),
            "account_relation": tok_data.get("relation", 0),
            "open_favorites": tok_data.get("open_favorite", False),
            "embed_ban": tok_data.get("prevent_download", False),
            "show_music": tok_data.get("show_music", False),
            "show_questions": tok_data.get("show_question", False),
            "show_lists": tok_data.get("show_play_list", False),
            "suggest_link": tok_data.get("need_suggest", False),
            "expand_lists": tok_data.get("expand_play_list", False),
            "embed_permission": tok_data.get("allow_embed", True),
            "ftc_compliant": tok_data.get("ftc", False),
            "fake_ads": tok_data.get("is_ad_virtual", False),
            "is_under_18": tok_data.get("is_under_age_18", False)
        }
        
        return result
