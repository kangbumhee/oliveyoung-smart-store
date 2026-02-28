"""네이버 커머스 API 테스트."""
import pytest
from unittest.mock import patch, MagicMock
from naver.commerce_auth import NaverCommerceAuth
from naver.product_manager import NaverProductManager
from naver.shipping_manager import NaverShippingManager
from config.settings import DELIVERY_COMPANY_CODES


class TestNaverAuth:

    def test_token_signature_format(self):
        """서명 형식 검증."""
        auth = NaverCommerceAuth()
        # 실제 발급은 안되지만 구조 테스트
        assert auth._token is None
        assert auth._expires_at is None

    def test_headers_property(self):
        """헤더에 Bearer 토큰 포함 확인."""
        auth = NaverCommerceAuth()
        auth._token = "test_token_123"
        from datetime import datetime, timedelta
        auth._expires_at = datetime.now() + timedelta(hours=2)
        headers = auth.headers
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"


class TestDeliveryCompanyCodes:

    def test_cj_code(self):
        assert DELIVERY_COMPANY_CODES["CJ대한통운"] == "CJGLS"

    def test_lotte_code(self):
        assert DELIVERY_COMPANY_CODES["롯데택배"] == "LOTTE"

    def test_hanjin_code(self):
        assert DELIVERY_COMPANY_CODES["한진택배"] == "HANJIN"


class TestShippingManager:

    @patch("naver.shipping_manager.requests.post")
    @patch("naver.shipping_manager.naver_auth")
    def test_dispatch_payload_structure(self, mock_auth, mock_post):
        """발송처리 API 페이로드 구조 확인."""
        mock_auth.headers = {"Authorization": "Bearer test"}
        mock_post.return_value = MagicMock(status_code=200)

        sm = NaverShippingManager()
        result = sm.dispatch_order(
            product_order_no="2024010112345",
            delivery_company="CJ대한통운",
            tracking_number="1234567890",
        )

        assert result is True
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        dispatch = payload["dispatchProductOrders"][0]
        assert dispatch["deliveryCompanyCode"] == "CJGLS"
        assert dispatch["trackingNumber"] == "1234567890"
