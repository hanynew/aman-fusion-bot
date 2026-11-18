import os
import logging
from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)

# قاموس الدول المدمج (لجعل الملف مستقلاً تماماً)
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
    سكربت هندسي متخصص فقط في تتبع البصمة الجغرافية لحسابات تيك توك.
    يعتمد على استراتيجية متعددة الطبقات (Multi-Layer Strategy).
    """
    def __init__(self):
        self.impersonate = "chrome120"
        self.timeout = 10
        # جلب مفتاح RapidAPI من بيئة الرندر للطبقة الاحتياطية
        self.api_key = os.environ.get("RAPID_API_KEY", "d86d0f27e5msh3e53feb79423346p15c726jsn459f001aaa87")

    def _get_country_details(self, code: str):
        if not code or code.upper() in ["ZZ", ""]:
            return "غير محددة", ""
        return COUNTRIES.get(code.upper(), (code, "🌍"))

    def hunt(self, username: str) -> dict:
        username = username.lstrip("@").strip()
        region_code = None

        # 🎯 الطبقة الأولى: اصطياد الدولة من سيرفرات الوسائط (أدق طريقة)
        # المستخدم قد يضع بروكسي، لكن فيديوهاته السابقة تفضحه.
        try:
            url = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=3"
            res = cffi_requests.get(url, impersonate=self.impersonate, timeout=self.timeout)
            if res.status_code == 200:
                videos = res.json().get("data", {}).get("videos", [])
                if videos and len(videos) > 0:
                    region_code = videos[0].get("region")
        except Exception as e:
            logger.error(f"CountryHunter Layer 1 (Media) Error: {e}")

        # 🎯 الطبقة الثانية: البحث العميق عبر TokAPI (خطة بديلة)
        if not region_code or region_code.upper() in ["US", "ZZ"]:
            try:
                headers = {
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "tokapi-mobile-version.p.rapidapi.com"
                }
                url = "https://tokapi-mobile-version.p.rapidapi.com/v1/search/user"
                params = {"keyword": username, "cursor": 0}
                res = cffi_requests.get(url, headers=headers, params=params, impersonate=self.impersonate, timeout=self.timeout)
                
                if res.status_code == 200:
                    user_list = res.json().get("user_list", [])
                    for item in user_list:
                        info = item.get("user_info", {})
                        if info.get("unique_id", "").lower() == username.lower():
                            region_code = info.get("region")
                            break
            except Exception as e:
                logger.error(f"CountryHunter Layer 2 (API) Error: {e}")

        # 🎯 التقييم النهائي للنتيجة
        if region_code and region_code.upper() not in ["ZZ"]:
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
                "message": "لا يمكن تحديد الدولة بدقة (صاحب الحساب يخفي موقعه بـ VPN أو لم ينشر أي محتوى)."
            }
