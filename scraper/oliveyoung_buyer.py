"""
올리브영 자동 구매 (Playwright persistent context).
스마트스토어 주문이 들어오면 구매자 주소로 직접 배송.
"""
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext
from core.logger import get_logger
from config.settings import (
    OLIVEYOUNG_BASE_URL, OLIVEYOUNG_ID, OLIVEYOUNG_PW,
    PLAYWRIGHT_USER_DATA_DIR,
)

log = get_logger("oy_buyer")


class OliveYoungBuyer:
    """올리브영 자동 구매 + 운송장 추출."""

    def __init__(self):
        self.playwright = None
        self.browser: BrowserContext | None = None
        self.page: Page | None = None
        self._logged_in = False

    async def start(self):
        """Playwright persistent context 시작."""
        Path(PLAYWRIGHT_USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_USER_DATA_DIR,
            headless=True,
            locale="ko-KR",
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self.browser.new_page()
        log.info("oy_buyer_started")

    async def ensure_login(self):
        """올리브영 로그인 상태 확인 및 로그인."""
        if self._logged_in:
            return

        await self.page.goto(f"{OLIVEYOUNG_BASE_URL}/store/mypage/getMyPageMain.do")
        await self.page.wait_for_load_state("networkidle")

        if "login" in self.page.url.lower():
            log.info("oy_login_required")
            await self.page.fill('input[name="loginId"]', OLIVEYOUNG_ID)
            await self.page.fill('input[name="password"]', OLIVEYOUNG_PW)
            await self.page.click('button[type="submit"], .btnLogin, #loginBtn')
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)

            if "login" in self.page.url.lower():
                log.warning("oy_login_manual_intervention_needed")
                await asyncio.sleep(60)

        self._logged_in = True
        log.info("oy_logged_in")

    async def purchase_product(
        self,
        goods_no: str,
        option_name: str | None,
        quantity: int,
        buyer_name: str,
        buyer_phone: str,
        buyer_address: str,
        buyer_zipcode: str,
    ) -> dict:
        """올리브영에서 상품 구매 → 구매자 주소로 직배송."""
        await self.ensure_login()
        log.info("oy_purchase_start", goods_no=goods_no, buyer=buyer_name)

        try:
            url = f"{OLIVEYOUNG_BASE_URL}/store/goods/getGoodsDetail.do?goodsNo={goods_no}"
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            if option_name:
                option_selectors = await self.page.query_selector_all(
                    '.option_list li, .prd_option_box select option'
                )
                for opt in option_selectors:
                    text = await opt.text_content()
                    if option_name in (text or ""):
                        await opt.click()
                        await asyncio.sleep(1)
                        break

            for _ in range(quantity - 1):
                plus_btn = await self.page.query_selector('.btn_plus, .btnQtyPlus')
                if plus_btn:
                    await plus_btn.click()
                    await asyncio.sleep(0.3)

            buy_btn = await self.page.query_selector(
                '.btnBuy, .btn_buy, [data-attr="구매하기"]'
            )
            if buy_btn:
                await buy_btn.click()
            else:
                cart_btn = await self.page.query_selector('.btnCart, .btn_cart')
                if cart_btn:
                    await cart_btn.click()
                    await asyncio.sleep(2)
                    await self.page.goto(
                        f"{OLIVEYOUNG_BASE_URL}/store/order/getOrderDetail.do"
                    )

            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)

            await self._fill_delivery_info(
                buyer_name, buyer_phone, buyer_address, buyer_zipcode
            )

            order_no = await self._process_payment()

            log.info("oy_purchase_complete", goods_no=goods_no, order_no=order_no)
            return {"success": True, "order_no": order_no}

        except Exception as e:
            log.error("oy_purchase_failed", goods_no=goods_no, error=str(e))
            return {"success": False, "error": str(e)}

    async def _fill_delivery_info(
        self, name: str, phone: str, address: str, zipcode: str
    ):
        """주문 페이지에서 배송지 정보 입력."""
        change_btn = await self.page.query_selector(
            '.btn_change_addr, .btnChgAddr, [data-type="changeAddr"]'
        )
        if change_btn:
            await change_btn.click()
            await asyncio.sleep(2)

        await self.page.fill('input[name="receiverNm"], #receiverNm', name)
        phone_parts = re.match(r'(\d{3})(\d{3,4})(\d{4})', phone.replace("-", ""))
        if phone_parts:
            phone_fields = await self.page.query_selector_all(
                'input[name*="rcvrPhone"], input[name*="receiverPhone"]'
            )
            if len(phone_fields) >= 3:
                await phone_fields[0].fill(phone_parts.group(1))
                await phone_fields[1].fill(phone_parts.group(2))
                await phone_fields[2].fill(phone_parts.group(3))
            elif len(phone_fields) == 1:
                await phone_fields[0].fill(phone.replace("-", ""))

        addr_field = await self.page.query_selector(
            'input[name="receiverAddr"], #receiverAddr, input[name*="address"]'
        )
        if addr_field:
            await addr_field.fill(address)

        zip_field = await self.page.query_selector(
            'input[name="zipCode"], #zipCode, input[name*="zip"]'
        )
        if zip_field:
            await zip_field.fill(zipcode)

        await asyncio.sleep(1)

    async def _process_payment(self) -> str:
        """결제 처리."""
        agree_all = await self.page.query_selector(
            '#allAgree, .chk_all input, [name="agreeAll"]'
        )
        if agree_all:
            await agree_all.click()
            await asyncio.sleep(0.5)

        pay_btn = await self.page.query_selector(
            '.btn_payment, .btnPay, #btnPayment, [data-type="payment"]'
        )
        if pay_btn:
            await pay_btn.click()

        await asyncio.sleep(5)

        order_no = ""
        try:
            order_text = await self.page.text_content('.order_num, .orderNo, #orderNo')
            if order_text:
                match = re.search(r'[A-Z]?\d{10,}', order_text)
                if match:
                    order_no = match.group()
        except Exception:
            pass

        return order_no

    async def get_tracking_info(self, oy_order_no: str) -> dict | None:
        """올리브영 마이페이지에서 운송장 정보 추출."""
        await self.ensure_login()

        await self.page.goto(
            f"{OLIVEYOUNG_BASE_URL}/store/mypage/getMyOrderDetailList.do"
        )
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        tracking_js = f"""
        (function() {{
            var rows = document.querySelectorAll('.order_list_item, .order_item, tr');
            for (var row of rows) {{
                if (row.textContent.includes('{oy_order_no}')) {{
                    var trackBtn = row.querySelector('.btn_track, .btnDelivery, a[href*="tracking"]');
                    if (trackBtn) {{
                        var href = trackBtn.getAttribute('href') || trackBtn.getAttribute('onclick') || '';
                        var match = href.match(/(\\d{{10,}})/);
                        var company = row.textContent.match(/(CJ대한통운|한진택배|롯데택배|우체국택배|로젠택배)/);
                        return JSON.stringify({{
                            tracking_number: match ? match[1] : null,
                            delivery_company: company ? company[1] : null,
                        }});
                    }}
                }}
            }}
            return JSON.stringify(null);
        }})();
        """
        result = await self.page.evaluate(tracking_js)
        data = json.loads(result) if isinstance(result, str) else result

        if data and data.get("tracking_number"):
            log.info("oy_tracking_found", order=oy_order_no, tracking=data)
            return data

        log.info("oy_tracking_not_ready", order=oy_order_no)
        return None

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
