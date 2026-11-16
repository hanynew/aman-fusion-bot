import logging
from typing import Dict, Any
from tiktok_engine.providers.rapidapi_provider import TikTokRapidAPIProvider
from tiktok_engine.providers.tikwm_provider import TikWMProvider
from tiktok_engine.providers.tokapi_provider import TokAPIProvider

logger = logging.getLogger(__name__)

class TikTokExtractionEngine:
    def __init__(self):
        # تسجيل المزودين
        self.rapid_provider = TikTokRapidAPIProvider() # tiktok-scraper7 القديم للتواريخ والستوري
        self.tikwm_provider = TikWMProvider()          # لصيد الدولة من الفيديوهات كاحتياط
        self.tokapi_provider = TokAPIProvider()        # المزود الاحترافي الجديد للدولة والأصدقاء

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
        
        merged_data = {"user": {}, "stats": {}}

        # 1. المصدر الأول الاحترافي: TokAPI (يجلب الأصدقاء والدولة الدقيقة)
        tok_data = self.tokapi_provider.get_profile(username)
        if tok_data:
            merged_data["user"] = {
                "id": tok_data.get("uid", ""),
                "nickname": tok_data.get("nickname", ""),
                "signature": tok_data.get("signature", ""),
                "region": tok_data.get("region", ""),
                "verified": tok_data.get("custom_verify", "") != "",
                "secret": tok_data.get("secret", False)
            }
            if tok_data.get("avatar_larger") and tok_data["avatar_larger"].get("url_list"):
                merged_data["user"]["avatarLarger"] = tok_data["avatar_larger"]["url_list"][0]
            
            merged_data["stats"] = {
                "followerCount": tok_data.get("follower_count", 0),
                "followingCount": tok_data.get("following_count", 0),
                "heartCount": tok_data.get("total_favorited", 0),
                "videoCount": tok_data.get("aweme_count", 0),
                "friendCount": tok_data.get("friend_count", 0)
            }

        # 2. المصدر الثاني الداعم: RapidAPI القديم (يجلب التواريخ واللغة وباقي التفاصيل)
        rapid_data = self.rapid_provider.get_profile(username)
        if rapid_data:
            r_user = rapid_data.get("user", {})
            r_stats = rapid_data.get("stats", {})
            
            # تحديث البيانات الناقصة فقط (لا نستبدل دولة TokAPI بدولة السيرفر)
            for k, v in r_user.items():
                if k == "region" and merged_data["user"].get("region"): continue
                if not merged_data["user"].get(k): merged_data["user"][k] = v
            for k, v in r_stats.items():
                if not merged_data["stats"].get(k): merged_data["stats"][k] = v

        if not merged_data["user"].get("id"):
            result["message"] = "لم أتمكن من العثور على هذا الحساب في جميع المصادر المتاحة."
            return result

        # 3. صائد الدولة النهائي
        region = merged_data["user"].get("region", "")
        if not region or region.upper() in ["US", "ZZ"]:
            recent_posts = self.tikwm_provider.get_recent_posts(username, count=2)
            if recent_posts:
                vid_region = recent_posts[0].get("region")
                if vid_region:
                    region = vid_region

        # 4. محرك الستوري
        stories = []
        rapid_stories = self.rapid_provider.get_stories(username)
        if rapid_stories:
            stories = rapid_stories
        else:
            tikwm_posts = self.tikwm_provider.get_recent_posts(username, count=20)
            for v in tikwm_posts:
                if v.get("is_story") == True or v.get("aweme_type") in [68, 69, 101] or v.get("duration") == 0:
                    stories.append(v)

        create_time = self._normalize_date(merged_data["user"].get("createTime"))
        modify_time = self._normalize_date(merged_data["user"].get("nickNameModifyTime"))
        if create_time != "غير متوفر" and create_time == modify_time:
            modify_time = "لم يتم التعديل"
        elif modify_time == "غير متوفر" and create_time != "غير متوفر":
            modify_time = "لم يتم التعديل"

        result["status"] = "success"
        result["message"] = "تم الاستخراج ودمج البيانات بنجاح"
        result["data"] = {
            "username": username,
            "user_id": merged_data["user"].get("id", "غير متوفر"),
            "nickname": merged_data["user"].get("nickname", "غير متوفر"),
            "bio": merged_data["user"].get("signature", ""),
            "avatar": merged_data["user"].get("avatarLarger", ""),
            "region": region,
            "language": merged_data["user"].get("language", "en"),
            "is_verified": merged_data["user"].get("verified", False),
            "is_private": merged_data["user"].get("secret", False),
            
            "followers": merged_data["stats"].get("followerCount", 0),
            "following": merged_data["stats"].get("followingCount", 0),
            "friends": merged_data["stats"].get("friendCount", 0),
            "likes": merged_data["stats"].get("heartCount", 0),
            "videos": merged_data["stats"].get("videoCount", 0),
            
            "create_time_formatted": create_time,
            "modify_time_formatted": modify_time,
            "stories_active": stories,
            
            "download_setting": merged_data["user"].get("downloadSetting", 0),
            "has_store": merged_data["user"].get("hasCommerceEntry", False),
            "sells_on_tiktok": merged_data["user"].get("withCommerceEntry", False),
            "duet_setting": merged_data["user"].get("duetSetting", 0),
            "publish_setting": merged_data["user"].get("publishSetting", 0),
            "comment_setting": merged_data["user"].get("commentSetting", 0),
            "account_relation": merged_data["user"].get("relation", 0),
            "open_favorites": merged_data["user"].get("openFavorite", False),
            "embed_ban": merged_data["user"].get("preventDownload", False),
            "show_music": merged_data["user"].get("showMusic", False),
            "show_questions": merged_data["user"].get("showQuestion", False),
            "show_lists": merged_data["user"].get("showPlayList", False),
            "suggest_link": merged_data["user"].get("needSuggest", False),
            "expand_lists": merged_data["user"].get("expandPlayList", False),
            "embed_permission": merged_data["user"].get("allowEmbed", True),
            "ftc_compliant": merged_data["user"].get("ftc", False),
            "fake_ads": merged_data["user"].get("isADVirtual", False),
            "is_under_18": merged_data["user"].get("isUnderAge18", False)
        }
        
        return result
