import requests
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TikTokRapidAPIProvider:
    """
    مزود بيانات يعتمد على tiktok-scraper7 من RapidAPI.
    مسؤول عن جلب البيانات الأولية فقط دون معالجتها، مع معالجة الأخطاء والـ Rate Limit.
    """
    def __init__(self):
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")
        self.host = "tiktok-scraper7.p.rapidapi.com"
        self.base_url = f"https://{self.host}"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }
        self.timeout = 10 

    def _make_request(self, endpoint, params):
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                js = response.json()
                if js.get("code") == 0 and js.get("data"):
                    return js["data"]
                else:
                    logging.warning(f"RapidAPI returned error code or empty data for endpoint: {endpoint}")
                    return None
            elif response.status_code == 429:
                logging.error(f"Rate Limited by RapidAPI on endpoint: {endpoint}")
                return None
            else:
                logging.error(f"RapidAPI HTTP Error {response.status_code} on endpoint: {endpoint}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"RapidAPI Timeout on endpoint: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"RapidAPI Network Error: {e}")
            return None

    def get_profile(self, username: str):
        return self._make_request("user/info", {"unique_id": username})

    def get_stories(self, username: str):
        data = self._make_request("user/story", {"unique_id": username})
        if data and "itemList" in data:
            return data["itemList"]
        return []

    def get_recent_posts(self, username: str, count: int = 3):
        data = self._make_request("user/posts", {"unique_id": username, "count": count})
        if data and "itemList" in data:
            return data["itemList"]
        return []
