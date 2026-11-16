import logging
from typing import Dict, Any
from tiktok_engine.providers.rapidapi_provider import TikTokRapidAPIProvider

logger = logging.getLogger(__name__)

class TikTokExtractionEngine:
    """
    المحرك المركزي لإدارة عملية الاستخراج.
    ينسق البيانات ويجمعها من المزودين.
    """
    def __init__(self):
        self.rapid_provider = TikTokRapidAPIProvider()

    def _normalize_date(self, timestamp) -> str:
        if not timestamp or str(timestamp) == "0" or str(timestamp) == "-1":
            return "غير متوفر"
        try:
            ts = int(timestamp)
            if len(str(ts)) > 10: 
                ts = ts / 1000
            from datetime import datetime
            return datetime.fromtimestamp(ts).strftime('%H:%M:%S %d-%m-%Y')
        except Exception:
            return "غير متوفر"

    def extract_tiktok_profile(self, username: str) -> Dict[str, Any]:
        result = {
            "status": "error",
            "message": "حدث خطأ غير معروف",
            "data": None
        }

        # 1. جلب البيانات الخام
        raw_data = self.rapid_provider.get_profile(username)
        
        if not raw_data:
            result["message"] = "لم أتمكن من العثور على هذا الحساب أو الواجهة لا تستجيب."
            return result
            
        user_info = raw_data.get("user", {})
        stats_info = raw_data.get("stats", {})
        
        # 2. صائد الدولة الحقيقي
        region = user_info.get("region", "")
        if not region or region.upper() in ["US", "ZZ"]:
            recent_posts = self.rapid_provider.get_recent_posts(username, count=2)
            if recent_posts:
                vid_region = recent_posts[0].get("author", {}).get("region")
                if vid_region:
                    region = vid_region
        
        # 3. جلب الستوريات
        stories = self.rapid_provider.get_stories(username)
        
        # 4. تنسيق التواريخ
        create_time = self._normalize_date(user_info.get("createTime"))
        modify_time = self._normalize_date(user_info.get("nickNameModifyTime"))
        
        if create_time != "غير متوفر" and create_time == modify_time:
            modify_time = "لم يتم التعديل"
        elif modify_time == "غير متوفر" and create_time != "غير متوفر":
            modify_time = "لم يتم التعديل"

        result["status"] = "success"
        result["message"] = "تم الاستخراج بنجاح"
        result["data"] = {
            "username": username,
            "user_id": user_info.get("id", "غير متوفر"),
            "nickname": user_info.get("nickname", "غير متوفر"),
            "bio": user_info.get("signature", ""),
            "avatar": user_info.get("avatarLarger", ""),
            "region": region,
            "language": user_info.get("language", "en"),
            "is_verified": user_info.get("verified", False),
            "is_private": user_info.get("secret", False),
            "followers": stats_info.get("followerCount", 0),
            "following": stats_info.get("followingCount", 0),
            "friends": stats_info.get("friendCount", 0),
            "likes": stats_info.get("heartCount", 0),
            "videos": stats_info.get("videoCount", 0),
            "create_time_formatted": create_time,
            "modify_time_formatted": modify_time,
            "stories_active": stories,
            "download_setting": user_info.get("downloadSetting", 0),
            "has_store": user_info.get("hasCommerceEntry", False),
            "sells_on_tiktok": user_info.get("withCommerceEntry", False),
            "duet_setting": user_info.get("duetSetting", 0),
            "publish_setting": user_info.get("publishSetting", 0),
            "comment_setting": user_info.get("commentSetting", 0),
            "account_relation": user_info.get("relation", 0),
            "open_favorites": user_info.get("openFavorite", False),
            "embed_ban": user_info.get("preventDownload", False),
            "show_music": user_info.get("showMusic", False),
            "show_questions": user_info.get("showQuestion", False),
            "show_lists": user_info.get("showPlayList", False),
            "suggest_link": user_info.get("needSuggest", False),
            "expand_lists": user_info.get("expandPlayList", False),
            "embed_permission": user_info.get("allowEmbed", True),
            "ftc_compliant": user_info.get("ftc", False),
            "fake_ads": user_info.get("isADVirtual", False),
            "is_under_18": user_info.get("isUnderAge18", False)
        }
        
        return result
