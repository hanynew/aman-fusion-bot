import os
import logging
from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)

COUNTRIES = {
    "SA": ("المملكة العربية السعودية", "🇸🇦"), "AE": ("الإمارات العربية المتحدة", "🇦🇪"),
    "EG": ("مصر", "🇪🇬"), "YE": ("اليمن", "🇾🇪"), "IQ": ("العراق", "🇮🇶"),
    "MA": ("المغرب", "🇲🇦"), "DZ": ("الجزائر", "🇩🇿"), "KW": ("الكويت", "🇰🇼"),
    "JO": ("الأردن", "🇯🇴"), "QA": ("قطر", "🇶🇦"), "BH": ("البحرين", "🇧🇭"),
    "OM": ("سلطنة عُمان", "🇴🇲"), "SD": ("السودان", "🇸🇩"), "LB": ("لبنان", "🇱🇧"),
    "SY": ("سوريا", "🇸🇾"), "US": ("الولايات المتحدة", "🇺🇸"), "GB": ("المملكة المتحدة", "🇬🇧"),
    "TR": ("تركيا", "🇹🇷"), "FR": ("فرنسا", "🇫🇷"), "DE": ("ألمانيا", "🇩🇪"),
    "IN": ("الهند", "🇮🇳"), "ID": ("إندونيسيا", "🇮🇩"), "RU": ("روسيا", "🇷🇺")
}

class CountryHunter:
    """
    قناص متوحش لجلب الدولة بأي ثمن.
    يستخدم السحب المباشر (Direct API Fetch) لإجبار السيرفر على إرجاع الدولة.
    """
    def __init__(self):
        self.impersonate = "chrome120"
        self.timeout = 10
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")

    def _get_country_details(self, code: str):
        if not code or code.upper() in ["ZZ", ""]:
            return "غير محددة", ""
        return COUNTRIES.get(code.upper(), (code, "🌍"))

    def hunt(self, username: str) -> dict:
        username = username.lstrip("@").strip()
        region_code = None

        # 🎯 الطبقة الأولى: اصطياد الدولة من فيديوهات المستخدم
        try:
            url = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=3"
            res = cffi_requests.get(url, impersonate=self.impersonate, timeout=self.timeout)
            if res.status_code == 200:
                videos = res.json().get("data", {}).get("videos", [])
                if videos and len(videos) > 0:
                    region_code = videos[0].get("region")
        except Exception as e:
            logger.error(f"CountryHunter Layer 1 Error: {e}")

        # 🎯 الطبقة الثانية (الهجوم المباشر): الاستخراج الجبري عبر TokAPI
        if not region_code or region_code.upper() in ["US", "ZZ"]:
            try:
                headers = {
                    "content-type": "application/json",
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "tokapi-mobile-version.p.rapidapi.com"
                }
                # استخدام المسار المباشر (POST) الذي يجلب البيانات العميقة جداً
                url = f"https://tokapi-mobile-version.p.rapidapi.com/v1/user/{username}"
                payload = {}
                
                res = cffi_requests.post(url, headers=headers, json=payload, impersonate=self.impersonate, timeout=self.timeout)
                
                if res.status_code == 200:
                    js_data = res.json()
                    
                    # استخراج الـ region من أي مكان ممكن في الـ JSON
                    if js_data.get("user"):
                        region_code = js_data["user"].get("region")
                    elif js_data.get("user_info"):
                        region_code = js_data["user_info"].get("region")
                        
            except Exception as e:
                logger.error(f"CountryHunter Layer 2 Error: {e}")

        # 🎯 التقييم النهائي
        if region_code and region_code.upper() not in ["ZZ", "US", ""]:
            country_name, flag = self._get_country_details(region_code)
            return {
                "status": "success", 
                "country_name": country_name, 
                "flag": flag, 
                "code": region_code.upper()
            }
        else:
            return {
                "status": "error", 
                "message": "لا يمكن تحديد الدولة بدقة (صاحب الحساب يخفي موقعه بـ VPN أو خوادم تيك توك تحجب دولته)."
            }
