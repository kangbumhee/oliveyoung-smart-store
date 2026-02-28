"""
네이버 스마트스토어 주문 조회/발주확인.
"""
import requests
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from core.logger import get_logger
from config.settings import NAVER_API_BASE
from naver.commerce_auth import naver_auth

log = get_logger("naver_order")


class NaverOrderManager:
    """주문 조회 및 발주 확인."""

    BASE = f"{NAVER_API_BASE}/v1/pay-order"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_new_orders(self) -> list[dict]:
        """
        신규 주문 (발주확인 전) 목록 조회.
        최근 3일간 PAYED 상태 주문.
        """
        url = f"{self.BASE}/seller/product-orders/last-changed-statuses"
        params = {
            "lastChangedFrom": (datetime.now() - timedelta(days=3)).strftime(
                "%Y-%m-%dT00:00:00.000+09:00"
            ),
            "lastChangedType": "PAYED",
        }
        response = requests.get(url, params=params, headers=naver_auth.headers)

        if response.status_code == 200:
            data = response.json()
            orders = data.get("data", {}).get("lastChangeStatuses", [])
            log.info("naver_new_orders", count=len(orders))
            return orders
        else:
            log.error("naver_orders_failed", status=response.status_code)
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_order_detail(self, product_order_no: str) -> dict:
        """주문 상세 정보 조회."""
        url = f"{self.BASE}/seller/product-orders/{product_order_no}"
        response = requests.get(url, headers=naver_auth.headers)
        if response.status_code == 200:
            return response.json().get("data", {})
        return {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def confirm_order(self, product_order_nos: list[str]) -> bool:
        """발주 확인 처리."""
        url = f"{self.BASE}/seller/product-orders/confirm"
        payload = {"productOrderIds": product_order_nos}
        response = requests.post(url, json=payload, headers=naver_auth.headers)
        success = response.status_code == 200
        log.info("naver_order_confirmed", orders=product_order_nos, success=success)
        return success
