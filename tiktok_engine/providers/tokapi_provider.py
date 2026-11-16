import requests
import os
import logging

logger = logging.getLogger(__name__)

class TokAPIProvider:
    """
    المزود الاحترافي الأساسي لاستخراج البيانات العميقة (الدولة، الأصدقاء) 
    يعتمد على TokAPI Mobile Version.
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
            url = f"{self.base_url}/user/search"
            params = {"keyword": username}
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                js = response.json()
                if js.get("user_list") and len(js["user_list"]) > 0:
                    return js["user_list"][0].get("user_info", {})
                else:
                    logger.warning(f"TokAPI: User not found in search results for {username}")
                    return None
            else:
                logger.error(f"TokAPI Error {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"TokAPI Exception: {e}")
            return None
