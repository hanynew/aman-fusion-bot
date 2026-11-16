import requests
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

class TiklyDownProvider:
    def __init__(self):
        self.base_url = "https://api.tiklydown.eu.org/api/user"
        self.timeout = 15

    def get_profile(self, username: str):
        try:
            # نستخدم verify=False لتخطي أخطاء شهادة SSL الخاصة بهم
            response = requests.get(f"{self.base_url}?user={username}", timeout=self.timeout, verify=False)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"TiklyDown Provider Error: {e}")
            return None
