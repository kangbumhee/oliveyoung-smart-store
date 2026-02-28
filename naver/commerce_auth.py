"""
네이버 커머스 API 인증 토큰 관리.
bcrypt 서명 → 토큰 발급 → 3시간 만료 자동 갱신.
"""
import time
import urllib.parse
import requests
import bcrypt
import pybase64
from datetime import datetime, timedelta
from core.logger import get_logger
from config.settings import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_API_BASE

log = get_logger("naver_auth")


class NaverCommerceAuth:
    """네이버 커머스 API 인증 관리."""

    TOKEN_URL = f"{NAVER_API_BASE}/v1/oauth2/token"

    def __init__(self):
        self._token: str | None = None
        self._expires_at: datetime | None = None

    @property
    def token(self) -> str:
        """유효한 토큰 반환. 만료 30분 전이면 자동 갱신."""
        if self._token and self._expires_at:
            if datetime.now() < self._expires_at - timedelta(minutes=30):
                return self._token
        return self._refresh_token()

    @property
    def headers(self) -> dict:
        """API 호출용 헤더."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _refresh_token(self) -> str:
        """bcrypt 서명으로 새 토큰 발급."""
        timestamp = str(int((time.time() - 3) * 1000))
        password = f"{NAVER_CLIENT_ID}_{timestamp}"

        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            NAVER_CLIENT_SECRET.encode("utf-8"),
        )
        client_secret_sign = pybase64.standard_b64encode(hashed).decode("utf-8")

        params = {
            "client_id": NAVER_CLIENT_ID,
            "timestamp": timestamp,
            "client_secret_sign": client_secret_sign,
            "grant_type": "client_credentials",
            "type": "SELF",
        }

        url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
        response = requests.post(
            url, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code == 200:
            data = response.json()
            self._token = data["access_token"]
            expires_in = data.get("expires_in", 10800)
            self._expires_at = datetime.now() + timedelta(seconds=expires_in)
            log.info("naver_token_refreshed", expires_in=expires_in)
            return self._token
        else:
            log.error("naver_token_failed", status=response.status_code, body=response.text)
            raise Exception(f"네이버 토큰 발급 실패: {response.status_code}")


# 싱글톤
naver_auth = NaverCommerceAuth()
