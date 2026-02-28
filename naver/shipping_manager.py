"""
운송장 등록 / 발송 처리.
"""
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from core.logger import get_logger
from config.settings import NAVER_API_BASE, DELIVERY_COMPANY_CODES
from naver.commerce_auth import naver_auth

log = get_logger("naver_shipping")


class NaverShippingManager:
    """운송장 등록 및 발송 처리."""

    BASE = f"{NAVER_API_BASE}/v1/pay-order"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def dispatch_order(
        self,
        product_order_no: str,
        delivery_company: str,
        tracking_number: str,
    ) -> bool:
        """
        발송 처리 (운송장 등록).
        """
        company_code = DELIVERY_COMPANY_CODES.get(delivery_company, "CJGLS")

        url = f"{self.BASE}/seller/product-orders/dispatch"
        payload = {
            "dispatchProductOrders": [
                {
                    "productOrderId": product_order_no,
                    "deliveryMethod": "DELIVERY",
                    "deliveryCompanyCode": company_code,
                    "trackingNumber": tracking_number,
                }
            ]
        }

        response = requests.post(url, json=payload, headers=naver_auth.headers)
        success = response.status_code == 200

        log.info(
            "naver_dispatch",
            order=product_order_no,
            company=delivery_company,
            tracking=tracking_number,
            success=success,
        )

        if not success:
            log.error("naver_dispatch_failed", body=response.text)

        return success
