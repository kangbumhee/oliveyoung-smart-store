"""
가격/재고 동기화.
올리브영 가격 변동 시 → 마진 적용하여 스마트스토어 자동 반영.
"""
from datetime import datetime
from decimal import Decimal
from core.database import SessionLocal, Product, PriceHistory
from core.logger import get_logger
from config.settings import calculate_selling_price, CATEGORY_MARGINS
from scraper.oliveyoung_scraper import OliveYoungScraper
from naver.product_manager import NaverProductManager

log = get_logger("price_sync")


class PriceSyncService:
    """올리브영 ↔ 스마트스토어 가격/재고 동기화."""

    def __init__(self):
        self.scraper = OliveYoungScraper()
        self.naver = NaverProductManager()
        self._browser_started = False

    def _ensure_browser(self):
        if not self._browser_started:
            self.scraper.start_browser()
            self._browser_started = True

    def sync_all(self):
        """등록된 모든 활성 상품 가격/재고 동기화."""
        self._ensure_browser()
        session = SessionLocal()

        try:
            products = (
                session.query(Product)
                .filter(
                    Product.is_active == True,
                    Product.auto_sync == True,
                    Product.status == "registered",
                    Product.naver_product_id.isnot(None),
                )
                .all()
            )

            if not products:
                log.info("price_sync_no_products")
                return

            goods_nos = [p.goods_no for p in products]
            log.info("price_sync_start", count=len(goods_nos))

            oy_data_list = self.scraper.scrape_bulk_prices(goods_nos)
            oy_data_map = {d["goodsNo"]: d for d in oy_data_list if d}

            updated_count = 0
            for product in products:
                oy_data = oy_data_map.get(product.goods_no)
                if not oy_data:
                    continue

                new_oy_price = oy_data.get("salePrice", 0)
                if new_oy_price <= 0:
                    continue

                if new_oy_price != product.oy_sale_price:
                    old_oy_price = product.oy_sale_price
                    old_selling = product.selling_price

                    cat_margin = CATEGORY_MARGINS.get(product.parent_category)
                    pricing = calculate_selling_price(
                        new_oy_price,
                        margin_rate=Decimal(str(product.margin_rate)),
                        category_margin=cat_margin,
                    )

                    new_selling = pricing["selling_price"]

                    product.oy_sale_price = new_oy_price
                    product.selling_price = new_selling
                    product.last_price_changed_at = datetime.utcnow()
                    product.last_synced_at = datetime.utcnow()

                    history = PriceHistory(
                        product_id=product.id,
                        oy_price_before=old_oy_price,
                        oy_price_after=new_oy_price,
                        selling_price_before=old_selling,
                        selling_price_after=new_selling,
                    )
                    session.add(history)

                    self.naver.update_price(product.naver_product_id, new_selling)

                    log.info(
                        "price_changed",
                        goods_no=product.goods_no,
                        oy_old=product.oy_sale_price,
                        oy_new=new_oy_price,
                        sell_old=old_selling,
                        sell_new=new_selling,
                        profit=pricing["total_profit"],
                    )
                    updated_count += 1

                options = oy_data.get("options")
                if options:
                    total_stock = sum(
                        o.get("quantity", 0) for o in options
                        if isinstance(o, dict) and not o.get("soldOut")
                    )
                    if total_stock != product.total_stock:
                        product.total_stock = total_stock
                        if total_stock == 0:
                            product.status = "soldout"
                            self.naver.pause_product(product.naver_product_id)
                            log.warning("product_soldout", goods_no=product.goods_no)
                        else:
                            self.naver.update_stock(
                                product.naver_product_id, total_stock
                            )

                product.last_synced_at = datetime.utcnow()

            session.commit()
            log.info("price_sync_complete", updated=updated_count, total=len(products))

        except Exception as e:
            session.rollback()
            log.error("price_sync_error", error=str(e))
            raise
        finally:
            session.close()
