"""
운송장 자동 추출 → 스마트스토어 자동 등록.
"""
import asyncio
from datetime import datetime
from core.database import SessionLocal, Order
from core.logger import get_logger
from scraper.oliveyoung_buyer import OliveYoungBuyer
from naver.shipping_manager import NaverShippingManager

log = get_logger("tracking_updater")


class TrackingUpdater:
    """운송장 자동 등록 서비스."""

    def __init__(self):
        self.buyer = OliveYoungBuyer()
        self.shipping = NaverShippingManager()
        self._buyer_started = False

    async def _ensure_buyer(self):
        if not self._buyer_started:
            await self.buyer.start()
            self._buyer_started = True

    def update_tracking(self):
        """운송장 미등록 주문 → 올리브영에서 추적 → 스마트스토어 등록."""
        asyncio.run(self._update_async())

    async def _update_async(self):
        await self._ensure_buyer()
        session = SessionLocal()

        try:
            orders = (
                session.query(Order)
                .filter(
                    Order.status == "oy_ordered",
                    Order.tracking_registered == False,
                    Order.oy_order_no.isnot(None),
                )
                .all()
            )

            if not orders:
                return

            log.info("tracking_check_start", count=len(orders))

            for order in orders:
                tracking = await self.buyer.get_tracking_info(order.oy_order_no)

                if tracking and tracking.get("tracking_number"):
                    company = tracking["delivery_company"] or "CJ대한통운"
                    number = tracking["tracking_number"]

                    success = self.shipping.dispatch_order(
                        product_order_no=order.naver_product_order_no,
                        delivery_company=company,
                        tracking_number=number,
                    )

                    if success:
                        order.delivery_company = company
                        order.tracking_number = number
                        order.tracking_registered = True
                        order.status = "tracking_sent"
                        order.tracking_sent_at = datetime.utcnow()
                        order.shipped_at = datetime.utcnow()
                        log.info(
                            "tracking_registered",
                            naver_order=order.naver_order_no,
                            company=company,
                            tracking=number,
                        )
                    else:
                        log.error(
                            "tracking_register_failed",
                            naver_order=order.naver_order_no,
                        )

            session.commit()
            log.info("tracking_update_complete")

        except Exception as e:
            session.rollback()
            log.error("tracking_update_error", error=str(e))
        finally:
            session.close()
