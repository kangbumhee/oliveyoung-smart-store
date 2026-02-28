"""
올리브영 고속 크롤링.
내부 API를 JS fetch로 호출하는 방식 (타입 C: driver.get + fetch 병행).
SeleniumBase uc=True로 봇탐지 우회.
"""
import json
import time
import random
from typing import Any
from seleniumbase import SB
from core.logger import get_logger
from config.settings import (
    OLIVEYOUNG_BASE_URL, OLIVEYOUNG_MOBILE_URL,
    CRAWL_DELAY_MIN, CRAWL_DELAY_MAX, CRAWL_429_WAIT, CRAWL_MAX_RETRIES,
)

log = get_logger("oy_scraper")


class OliveYoungScraper:
    """올리브영 내부 API 기반 고속 크롤러."""

    def __init__(self):
        self.sb = None
        self.driver = None
        self._session_ready = False

    def start_browser(self):
        """SeleniumBase 브라우저 시작 (uc=True 봇탐지 우회)."""
        self.sb_context = SB(uc=True, locale="ko", headed=False)
        self.sb = self.sb_context.__enter__()
        self.driver = self.sb.driver
        self._init_session()

    def _init_session(self):
        """올리브영 메인페이지 접속하여 세션/쿠키 확보."""
        log.info("oy_session_init")
        self.sb.uc_open_with_reconnect(
            f"{OLIVEYOUNG_BASE_URL}/store/main/main.do",
            reconnect_time=15,
        )
        time.sleep(3)
        try:
            self.sb.uc_gui_click_captcha()
            time.sleep(3)
        except Exception:
            pass
        self._session_ready = True
        log.info("oy_session_ready")

    def _delay(self):
        """랜덤 딜레이 (0.3~0.6초)."""
        time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))

    def _execute_fetch(self, js_code: str, retries: int = CRAWL_MAX_RETRIES) -> Any:
        """
        브라우저 내 JS fetch 실행 (세션 유지).
        429 에러 시 자동 대기 후 재시도.
        """
        for attempt in range(retries):
            try:
                result = self.driver.execute_async_script(js_code)
                if result and "429" not in str(result):
                    return json.loads(result) if isinstance(result, str) else result
                log.warning("oy_rate_limit", attempt=attempt + 1)
                time.sleep(CRAWL_429_WAIT)
            except Exception as e:
                log.error("oy_fetch_error", error=str(e), attempt=attempt + 1)
                time.sleep(CRAWL_429_WAIT)
        return None

    def scrape_best_list(self, category_no: str = "", rows: int = 100) -> list[dict]:
        """올리브영 베스트 상품 목록 크롤링."""
        url = (
            f"{OLIVEYOUNG_BASE_URL}/store/main/getBestList.do"
            f"?fltDispCatNo={category_no}&rowsPerPage={rows}"
        )
        log.info("oy_scrape_best", category=category_no, rows=rows)
        self.driver.get(url)
        time.sleep(3)

        items_js = """
        return JSON.stringify(
            [...document.querySelectorAll('.cate_prd_list .item')].map(el => ({
                goodsNo: (el.querySelector('a[data-goods-no]') || {}).getAttribute('data-goods-no') || '',
                name: (el.querySelector('.tx_name') || {}).textContent || '',
                brand: (el.querySelector('.tx_brand') || {}).textContent || '',
                price: (el.querySelector('.tx_cur .tx_num') || {}).textContent || '0',
                originalPrice: (el.querySelector('.tx_org .tx_num') || {}).textContent || '0',
                image: (el.querySelector('img') || {}).src || '',
                reviewCount: (el.querySelector('.cnt') || {}).textContent || '0',
            }))
        );
        """
        try:
            result = self.driver.execute_script(items_js)
            items = json.loads(result) if result else []
            log.info("oy_best_scraped", count=len(items))
            return items
        except Exception as e:
            log.error("oy_best_error", error=str(e))
            return []

    def scrape_product_detail(self, goods_no: str) -> dict:
        """상품 상세 정보 수집 (fetch 병행 호출로 고속)."""
        log.info("oy_detail_scrape", goods_no=goods_no)

        js_code = f"""
        var callback = arguments[arguments.length - 1];
        (async function() {{
            try {{
                var results = await Promise.allSettled([
                    fetch('/store/goods/getGoodsDetail.do?goodsNo={goods_no}',
                        {{credentials: 'include'}}).then(r => r.text()),
                    fetch('{OLIVEYOUNG_MOBILE_URL}/review/api/v2/reviews/{goods_no}/stats')
                        .then(r => r.json()),
                    fetch('/goods/api/v1/option?goodsNumber={goods_no}&optionNumber=001',
                        {{credentials: 'include'}}).then(r => r.json()),
                    fetch('/claim-front/api/v1/goods/getGoodsQnACount?goodsNo={goods_no}',
                        {{credentials: 'include'}}).then(r => r.json()),
                    fetch('{OLIVEYOUNG_MOBILE_URL}/review/api/v1/reviews/{goods_no}/summary')
                        .then(r => r.json())
                ]);

                var html = results[0].status === 'fulfilled' ? results[0].value : '';
                var salePrice = (html.match(/\\"salePrice\\":\\s*(\\d+)/) || [])[1] || '0';
                var originalPrice = (html.match(/\\"originPrice\\":\\s*(\\d+)/) || [])[1] || '0';
                var goodsName = (html.match(/\\"goodsName\\":\\s*\\"([^"\\\\]+)/) || [])[1] || '';
                var brandName = (html.match(/\\"brandName\\":\\s*\\"([^"\\\\]+)/) || [])[1] || '';

                callback(JSON.stringify({{
                    goodsNo: '{goods_no}',
                    name: goodsName,
                    brand: brandName,
                    salePrice: parseInt(salePrice),
                    originalPrice: parseInt(originalPrice),
                    reviewStats: results[1].status === 'fulfilled' ? results[1].value : null,
                    options: results[2].status === 'fulfilled' ? results[2].value : null,
                    qnaCount: results[3].status === 'fulfilled' ? results[3].value : null,
                    reviewSummary: results[4].status === 'fulfilled' ? results[4].value : null,
                }}));
            }} catch(e) {{
                callback(JSON.stringify({{error: e.message}}));
            }}
        }})();
        """
        result = self._execute_fetch(js_code)
        self._delay()
        return result or {}

    def scrape_price_and_stock(self, goods_no: str) -> dict:
        """가격/재고만 빠르게 조회 (가격 동기화용)."""
        js_code = f"""
        var callback = arguments[arguments.length - 1];
        (async function() {{
            try {{
                var results = await Promise.allSettled([
                    fetch('/store/goods/getGoodsDetail.do?goodsNo={goods_no}',
                        {{credentials: 'include'}}).then(r => r.text()),
                    fetch('/goods/api/v1/option?goodsNumber={goods_no}&optionNumber=001',
                        {{credentials: 'include'}}).then(r => r.json())
                ]);
                var html = results[0].status === 'fulfilled' ? results[0].value : '';
                var salePrice = (html.match(/\\"salePrice\\":\\s*(\\d+)/) || [])[1] || '0';
                callback(JSON.stringify({{
                    goodsNo: '{goods_no}',
                    salePrice: parseInt(salePrice),
                    options: results[1].status === 'fulfilled' ? results[1].value : null,
                }}));
            }} catch(e) {{
                callback(JSON.stringify({{error: e.message}}));
            }}
        }})();
        """
        result = self._execute_fetch(js_code)
        self._delay()
        return result or {}

    def scrape_bulk_prices(self, goods_nos: list[str]) -> list[dict]:
        """복수 상품 가격/재고 일괄 조회."""
        results = []
        batch_size = 3
        for i in range(0, len(goods_nos), batch_size):
            batch = goods_nos[i:i + batch_size]
            for gno in batch:
                data = self.scrape_price_and_stock(gno)
                if data:
                    results.append(data)
            self._delay()
        log.info("oy_bulk_prices", total=len(results))
        return results

    def close(self):
        """브라우저 종료."""
        if self.sb:
            try:
                self.sb_context.__exit__(None, None, None)
            except Exception:
                pass
