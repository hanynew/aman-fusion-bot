import requests
import os
import logging

logger = logging.getLogger(__name__)

class TokAPIProvider:
    """
    المزود الاحترافي الأساسي.
    يعتمد على نقطة البحث العامة (Search User) التي لا تتغير، 
    مع استخراج البيانات العميقة من داخل نتائج البحث.
    """
    def __init__(self):
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")
        self.host = "tokapi-mobile-version.p.rapidapi.com"
        # المسار الأساسي الثابت
        self.base_url = f"https://{self.host}/v1"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }
        self.timeout = 15

    def get_profile(self, username: str):
        try:
            # استخدام نقطة البحث العامة (تعمل بطلب GET حسب توثيقهم الثابت)
            search_url = f"{self.base_url}/search/user"
            params = {
                "keyword": username,
                "cursor": 0
            }
            
            response = requests.get(search_url, headers=self.headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                js = response.json()
                
                if js.get("user_list") and len(js["user_list"]) > 0:
                    # البحث عن التطابق التام لليوزر داخل النتائج
                    for item in js["user_list"]:
                        user_info = item.get("user_info", {})
                        if user_info.get("unique_id", "").lower() == username.lower():
                            return user_info
                    
                    # إذا لم نجد تطابقاً تاماً، نأخذ النتيجة الأولى
                    return js["user_list"][0].get("user_info", {})
                else:
                    logger.warning(f"TokAPI: Search returned empty list for {username}")
                    return None
            else:
                logger.error(f"TokAPI Search Error: HTTP {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"TokAPI Exception: {e}")
            return None
