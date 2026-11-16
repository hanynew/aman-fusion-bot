import requests
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

class TikWMProvider:
    def __init__(self):
        self.base_url = "https://www.tikwm.com/api/user"
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        self.timeout = 12

    def get_recent_posts(self, username: str, count: int = 15):
        try:
            response = requests.get(f"{self.base_url}/posts?unique_id={username}&count={count}", headers=self.headers, timeout=self.timeout, verify=False)
            if response.status_code == 200:
                js = response.json()
                if js.get("code") == 0 and js.get("data") and js["data"].get("videos"):
                    return js["data"]["videos"]
            return []
        except Exception as e:
            logger.error(f"TikWM Posts Error: {e}")
            return []
