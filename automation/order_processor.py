"""
주문 자동 처리.
스마트스토어 신규 주문 → 올리브영 자동 구매 → 구매자 주소 직배송.
"""
import asyncio
from datetime import datetime
from core.database import SessionLocal, Product, Order
from core.logger import get_logger
from naver.order_manager import NaverOrderManager
from scraper.oliveyoung_buyer import OliveYoungBuyer

log = get_logger("order_processor")


class OrderProcessor:
    """주문 자동 처리 파이프라인."""

    def __init__(self):
        self.naver_orders = NaverOrderManager()
        self.buyer = OliveYoungBuyer()
        self._buyer_started = False

    async def _ensure_buyer(self):
        if not self._buyer_started:
            await self.buyer.start()
            self._buyer_started = True

    def check_new_orders(self):
        """스마트스토어 신규 주문 확인 → DB 저장."""
        session = SessionLocal()
        try:
            new_orders = self.naver_orders.get_new_orders()
            saved_count = 0

            for order_status in new_orders:
                product_order_no = order_status.get("productOrderId", "")

                existing = (
                    session.query(Order)
                    .filter(Order.naver_product_order_no == product_order_no)
                    .first()
                )
                if existing:
                    continue

                detail = self.naver_orders.get_order_detail(product_order_no)
                if not detail:
                    continue

                product_order = detail.get("productOrder", {})
                shippingAddress = product_order.get("shippingAddress", {})

                product_name = product_order.get("productName", "")
                product = (
                    session.query(Product)
                    .filter(Product.name.contains(product_name[:30]))
                    .first()
                )

                order = Order(
                    naver_order_no=product_order.get("orderId", ""),
                    naver_product_order_no=product_order_no,
                    product_id=product.id if product else None,
                    buyer_name=shippingAddress.get("name", ""),
                    buyer_phone=shippingAddress.get("tel1", ""),
                    buyer_address=(
                        f"{shippingAddress.get('baseAddress', '')} "
                        f"{shippingAddress.get('detailedAddress', '')}"
                    ),
                    buyer_zipcode=shippingAddress.get("zipCode", ""),
                    order_quantity=product_order.get("quantity", 1),
                    order_option=product_order.get("optionContents", ""),
                    order_amount=product_order.get("totalPaymentAmount", 0),
                    status="new",
                )
                session.add(order)
                saved_count += 1

            session.commit()
            if saved_count:
                log.info("new_orders_saved", count=saved_count)

        except Exception as e:
            session.rollback()
            log.error("order_check_failed", error=str(e))
        finally:
            session.close()

    def process_pending_purchases(self):
        """대기 중인 주문 → 올리브영 자동 구매."""
        asyncio.run(self._process_purchases_async())

    async def _process_purchases_async(self):
        """올리브영 자동 구매 실행."""
        await self._ensure_buyer()
        session = SessionLocal()

        try:
            pending_orders = (
                session.query(Order)
                .filter(Order.status == "new")
                .order_by(Order.ordered_at)
                .limit(5)
                .all()
            )

            for order in pending_orders:
                product = (
                    session.query(Product)
                    .filter(Product.id == order.product_id)
                    .first()
                )
                if not product:
                    order.status = "error"
                    order.error_message = "상품 정보 없음"
                    continue

                self.naver_orders.confirm_order([order.naver_product_order_no])
                order.status = "confirmed"
                order.confirmed_at = datetime.utcnow()
                session.commit()

                order.status = "oy_ordering"
                session.commit()

                result = await self.buyer.purchase_product(
                    goods_no=product.goods_no,
                    option_name=order.order_option,
                    quantity=order.order_quantity,
                    buyer_name=order.buyer_name,
                    buyer_phone=order.buyer_phone,
                    buyer_address=order.buyer_address,
                    buyer_zipcode=order.buyer_zipcode,
                )

                if result.get("success"):
                    order.oy_order_no = result.get("order_no", "")
                    order.oy_purchase_price = product.oy_sale_price
                    order.oy_purchase_status = "purchased"
                    order.oy_ordered_at = datetime.utcnow()
                    order.status = "oy_ordered"
                    log.info(
                        "oy_purchase_success",
                        naver_order=order.naver_order_no,
                        oy_order=order.oy_order_no,
                    )
                else:
                    order.status = "error"
                    order.error_message = result.get("error", "구매 실패")
                    log.error(
                        "oy_purchase_failed",
                        naver_order=order.naver_order_no,
                        error=order.error_message,
                    )

                session.commit()

        except Exception as e:
            session.rollback()
            log.error("purchase_processing_failed", error=str(e))
        finally:
            session.close()
