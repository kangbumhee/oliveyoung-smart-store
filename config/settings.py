"""
전역 설정 관리.
마진율 기반 자동 판매가 계산 로직의 핵심.
"""
import os
from decimal import Decimal, ROUND_UP
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_config(key: str, default: str = "") -> str:
    try:
        from core.secret_manager import get_secret
        return get_secret(key, default)
    except Exception:
        return os.getenv(key, default)


# ── 경로 ──
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── 네이버 커머스 API ──
NAVER_CLIENT_ID: str = _get_config("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET: str = _get_config("NAVER_CLIENT_SECRET")
NAVER_SELLER_ID: str = os.getenv("NAVER_SELLER_ID", "")
SMARTSTORE_STORE_NAME: str = _get_config("SMARTSTORE_STORE_NAME")
NAVER_API_BASE: str = "https://api.commerce.naver.com/external"

# ── Google Gemini ──
GOOGLE_API_KEY: str = _get_config("GOOGLE_API_KEY")
GEMINI_MODEL: str = _get_config("GEMINI_MODEL", "gemini-2.0-flash")

# ── 올리브영 ──
OLIVEYOUNG_ID: str = _get_config("OLIVEYOUNG_ID")
OLIVEYOUNG_PW: str = _get_config("OLIVEYOUNG_PW")
OLIVEYOUNG_BASE_URL: str = "https://www.oliveyoung.co.kr"
OLIVEYOUNG_MOBILE_URL: str = "https://m.oliveyoung.co.kr"

# ── 마진/가격 설정 (Decimal 필수) ──
DEFAULT_MARGIN_RATE: Decimal = Decimal(os.getenv("DEFAULT_MARGIN_RATE", "0.15"))
SMARTSTORE_SHIPPING_FEE: int = int(os.getenv("SMARTSTORE_SHIPPING_FEE", "3000"))
OLIVEYOUNG_SHIPPING_FEE: int = int(os.getenv("OLIVEYOUNG_SHIPPING_FEE", "2500"))
OLIVEYOUNG_FREE_SHIPPING_THRESHOLD: int = 20000  # 올리브영 무료배송 기준
SHIPPING_PROFIT_BUFFER: int = int(os.getenv("SHIPPING_PROFIT_BUFFER", "500"))

# ── 스케줄 주기 (분) ──
PRICE_SYNC_INTERVAL: int = int(os.getenv("PRICE_SYNC_INTERVAL", "10"))
ORDER_CHECK_INTERVAL: int = int(os.getenv("ORDER_CHECK_INTERVAL", "3"))
TRACKING_CHECK_INTERVAL: int = int(os.getenv("TRACKING_CHECK_INTERVAL", "30"))

# ── DB ──
DB_PATH: str = os.getenv("DB_PATH", str(DATA_DIR / "bot.db"))

# ── Playwright ──
PLAYWRIGHT_USER_DATA_DIR: str = os.getenv(
    "PLAYWRIGHT_USER_DATA_DIR",
    os.getenv("PLAYWRIGHT_PROFILE_DIR", str(DATA_DIR / "browser_profile")),
)


def calculate_selling_price(
    oliveyoung_price: int,
    margin_rate: Decimal | None = None,
    category_margin: Decimal | None = None,
) -> dict:
    """
    올리브영 가격 기반 스마트스토어 판매가 자동 계산.

    로직:
    1. 올리브영 원가에 마진율 적용
    2. 배송비 보전 금액 추가
    3. 100원 단위 올림 (깔끔한 가격)
    4. 올리브영 배송비 vs 스마트스토어 배송비 차액 계산

    Returns:
        {
            "oliveyoung_price": 19900,
            "margin_rate": 0.15,
            "selling_price": 23400,        # 스마트스토어 판매가 (배송비 별도)
            "smartstore_shipping": 3000,   # 구매자 부담 배송비
            "oliveyoung_shipping": 2500,   # 올리브영 배송비 (or 0)
            "shipping_profit": 500,        # 배송비 차익
            "margin_amount": 2985,         # 마진 금액
            "total_profit": 3485,          # 총 이익 (마진 + 배송차익)
            "total_buyer_pays": 26400,     # 구매자 총 결제액
        }
    """
    rate = category_margin or margin_rate or DEFAULT_MARGIN_RATE
    oy_price = Decimal(str(oliveyoung_price))

    # 마진 적용 + 배송비 보전
    raw_price = oy_price * (1 + rate) + Decimal(str(SHIPPING_PROFIT_BUFFER))

    # 100원 단위 올림
    selling_price = int(
        (raw_price / 100).to_integral_value(rounding=ROUND_UP) * 100
    )

    # 올리브영 배송비 계산
    oy_shipping = 0 if oliveyoung_price >= OLIVEYOUNG_FREE_SHIPPING_THRESHOLD else OLIVEYOUNG_SHIPPING_FEE

    # 배송비 차익 (구매자가 낸 3000 - 올리브영 실제 배송비)
    shipping_profit = SMARTSTORE_SHIPPING_FEE - oy_shipping

    # 마진 금액
    margin_amount = selling_price - oliveyoung_price

    return {
        "oliveyoung_price": oliveyoung_price,
        "margin_rate": float(rate),
        "selling_price": selling_price,
        "smartstore_shipping": SMARTSTORE_SHIPPING_FEE,
        "oliveyoung_shipping": oy_shipping,
        "shipping_profit": shipping_profit,
        "margin_amount": margin_amount,
        "total_profit": margin_amount + shipping_profit,
        "total_buyer_pays": selling_price + SMARTSTORE_SHIPPING_FEE,
    }


# ── 카테고리별 마진율 오버라이드 ──
CATEGORY_MARGINS: dict[str, Decimal] = {
    "스킨케어": Decimal("0.15"),
    "메이크업": Decimal("0.18"),
    "바디케어": Decimal("0.12"),
    "헤어케어": Decimal("0.12"),
    "향수/디퓨저": Decimal("0.20"),
    "남성": Decimal("0.15"),
    "미용소품": Decimal("0.20"),
    "건강식품": Decimal("0.13"),
}

# ── 크롤링 설정 ──
CRAWL_DELAY_MIN: float = 0.3
CRAWL_DELAY_MAX: float = 0.6
CRAWL_429_WAIT: int = 15
CRAWL_MAX_RETRIES: int = 3

# ── 네이버 택배사 코드 ──
DELIVERY_COMPANY_CODES: dict[str, str] = {
    "CJ대한통운": "CJGLS",
    "우체국택배": "EPOST",
    "한진택배": "HANJIN",
    "롯데택배": "LOTTE",
    "로젠택배": "LOGEN",
    "드림택배": "KDEXP",
}
