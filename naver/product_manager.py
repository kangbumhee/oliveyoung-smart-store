"""
네이버 스마트스토어 상품 등록/수정/삭제.
커머스 API v2 사용.
"""
import json
from pathlib import Path
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from core.logger import get_logger
from config.settings import NAVER_API_BASE
from config.delivery_template import get_detail_attribute, DELIVERY_INFO
from naver.commerce_auth import naver_auth

log = get_logger("naver_product")


class NaverProductManager:
    """스마트스토어 상품 관리."""

    PRODUCT_URL = f"{NAVER_API_BASE}/v2/products"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def register_product(
        self,
        name: str,
        selling_price: int,
        category_id: str,
        detail_html: str,
        image_urls: list[str],
        options: list[dict] | None = None,
        stock: int = 999,
        brand: str = "",
        oliveyoung_category: str = "",
    ) -> dict:
        """
        스마트스토어에 상품 등록.

        Returns:
            {"smartstoreChannelProductNo": "...", "originProductNo": "..."}
        """
        uploaded_images = self._upload_images(image_urls)

        detail_attr = get_detail_attribute(
            oliveyoung_category=oliveyoung_category,
            product_name=name,
            brand=brand,
        )
        option_info = self._build_options(options) if options and len(options) > 1 else None
        if option_info:
            detail_attr["optionInfo"] = option_info

        payload = {
            "originProduct": {
                "statusType": "SALE",
                "saleType": "NEW",
                "leafCategoryId": str(category_id),
                "name": name,
                "salePrice": selling_price,
                "stockQuantity": stock,
                "detailContent": detail_html,
                "images": {
                    "representativeImage": uploaded_images[0] if uploaded_images else {},
                    "optionalImages": uploaded_images[1:5] if len(uploaded_images) > 1 else [],
                },
                "deliveryInfo": DELIVERY_INFO,
                "detailAttribute": detail_attr,
            },
            "smartstoreChannelProduct": {
                "naverShoppingRegistration": True,
                "channelProductDisplayStatusType": "ON",
            },
        }

        debug_file = Path("data/last_payload.json")
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        debug_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        response = requests.post(
            self.PRODUCT_URL,
            json=payload,
            headers=naver_auth.headers,
        )

        if response.status_code == 200:
            result = response.json()
            log.info("naver_product_registered", name=name, result=result)
            return result
        else:
            log.error(
                "naver_product_register_failed",
                status=response.status_code,
                body=response.text,
            )
            raise Exception(f"상품 등록 실패: {response.status_code} - {response.text}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def update_price(self, product_no: str, new_price: int) -> bool:
        """상품 판매가 수정."""
        url = f"{self.PRODUCT_URL}/{product_no}"
        payload = {"originProduct": {"salePrice": new_price}}
        response = requests.put(url, json=payload, headers=naver_auth.headers)
        if response.status_code == 200:
            log.info("naver_price_updated", product_no=product_no, price=new_price)
            return True
        log.error("naver_price_update_failed", status=response.status_code)
        return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def update_stock(self, product_no: str, stock: int) -> bool:
        """상품 재고 수정."""
        url = f"{self.PRODUCT_URL}/{product_no}"
        payload = {"originProduct": {"stockQuantity": stock}}
        response = requests.put(url, json=payload, headers=naver_auth.headers)
        if response.status_code == 200:
            log.info("naver_stock_updated", product_no=product_no, stock=stock)
            return True
        return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def update_price_and_stock(
        self, product_no: str, price: int, stock: int
    ) -> bool:
        """판매가 + 재고 동시 수정."""
        url = f"{self.PRODUCT_URL}/{product_no}"
        payload = {
            "originProduct": {
                "salePrice": price,
                "stockQuantity": stock,
            }
        }
        response = requests.put(url, json=payload, headers=naver_auth.headers)
        success = response.status_code == 200
        log.info(
            "naver_price_stock_updated",
            product_no=product_no, price=price, stock=stock, success=success,
        )
        return success

    def pause_product(self, product_no: str) -> bool:
        """상품 판매중지."""
        url = f"{self.PRODUCT_URL}/{product_no}"
        payload = {"originProduct": {"statusType": "SUSPENSION"}}
        response = requests.put(url, json=payload, headers=naver_auth.headers)
        return response.status_code == 200

    def _build_options(self, oy_options: list[dict]) -> dict:
        """올리브영 옵션 → 네이버 옵션 형식 변환."""
        option_combinations = []
        for idx, opt in enumerate(oy_options):
            if opt.get("soldOut"):
                continue
            option_combinations.append({
                "optionName1": opt.get("name", f"옵션{idx+1}"),
                "stockQuantity": opt.get("quantity", 0),
                "price": 0,
                "usable": not opt.get("soldOut", False),
            })

        return {
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {"optionGroupName1": "옵션"},
            "optionCombinations": option_combinations,
        }

    def _upload_images(self, urls: list[str]) -> list[dict]:
        """이미지 URL → 네이버 이미지 호스팅 업로드."""
        uploaded = []
        img_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        for url in urls[:5]:
            try:
                img_response = requests.get(url, timeout=10, headers=img_headers)
                if img_response.status_code != 200:
                    log.warning("image_download_failed", url=url, status=img_response.status_code)
                    continue
                if len(img_response.content) < 1000:
                    log.warning("image_too_small", url=url, size=len(img_response.content))
                    continue

                upload_url = f"{NAVER_API_BASE}/v1/product-images/upload"
                files = {"imageFiles": ("image.jpg", img_response.content, "image/jpeg")}
                headers = {"Authorization": f"Bearer {naver_auth.token}"}

                upload_response = requests.post(upload_url, files=files, headers=headers)
                if upload_response.status_code == 200:
                    data = upload_response.json()
                    images = data.get("images", [])
                    if images:
                        uploaded.append({"url": images[0].get("url", "")})
                else:
                    log.warning("image_upload_failed", url=url, status=upload_response.status_code)
            except Exception as e:
                log.error("image_upload_failed", url=url, error=str(e))

        return uploaded
