import requests
import os
import logging

logger = logging.getLogger(__name__)

class TokAPIProvider:
    """
    المزود الاحترافي الأساسي لاستخراج البيانات العميقة (الدولة، الأصدقاء).
    يعتمد على الاستخراج المباشر لليوزر (Direct Fetch) لتجاوز خطأ 404 في البحث.
    """
    def __init__(self):
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")
        self.host = "tokapi-mobile-version.p.rapidapi.com"
        # تم إزالة /v1 من الرابط الأساسي، لأن بعض نقاط النهاية لديهم ترفضه
        self.base_url = f"https://{self.host}"
        self.headers = {
            "content-type": "application/json",
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }
        self.timeout = 15

    def get_profile(self, username: str):
        try:
            # استخدام نقطة النهاية المباشرة (Direct Endpoint) الموثقة
            detail_url = f"{self.base_url}/v1/user/{username}"
            payload = {}
            
            response = requests.post(detail_url, headers=self.headers, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                js = response.json()
                if js.get("user"):
                    return js["user"]
                elif js.get("user_info"):
                    return js["user_info"]
                else:
                    logger.warning(f"TokAPI: Data structure mismatch for {username}")
                    return None
            else:
                logger.error(f"TokAPI Direct Fetch Error: HTTP {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"TokAPI Exception: {e}")
            return None
