import requests
import os
import logging

logger = logging.getLogger(__name__)

class TokAPIProvider:
    """
    المزود الاحترافي الأساسي لاستخراج البيانات العميقة (الدولة، الأصدقاء)
    """
    def __init__(self):
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")
        self.host = "tokapi-mobile-version.p.rapidapi.com"
        self.base_url = f"https://{self.host}/v1"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }
        self.timeout = 15

    def get_profile(self, username: str):
        try:
            # 1. مسار البحث الصحيح لجلب المعرف (uid)
            search_url = f"{self.base_url}/search/user"
            params = {"keyword": username, "cursor": 0}
            response = requests.get(search_url, headers=self.headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                js = response.json()
                user_info = None
                
                if js.get("user_list") and len(js["user_list"]) > 0:
                    # البحث عن التطابق الدقيق لليوزر
                    for u in js["user_list"]:
                        info = u.get("user_info", {})
                        if info.get("unique_id", "").lower() == username.lower():
                            user_info = info
                            break
                            
                    if not user_info:
                        user_info = js["user_list"][0].get("user_info", {})

                    # 2. الاستخراج العميق (لضمان جلب الدولة والأصدقاء بدقة)
                    uid = user_info.get("uid")
                    if uid:
                        detail_url = f"{self.base_url}/user/{uid}"
                        detail_res = requests.get(detail_url, headers=self.headers, timeout=self.timeout)
                        if detail_res.status_code == 200:
                            detail_js = detail_res.json()
                            if detail_js.get("user"):
                                return detail_js["user"]
                    
                    return user_info
                else:
                    logger.warning(f"TokAPI: User not found for {username}")
                    return None
            else:
                logger.error(f"TokAPI Search Error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"TokAPI Exception: {e}")
            return None
