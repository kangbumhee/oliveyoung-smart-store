"""
전체 자동화 파이프라인 오케스트레이터.
"""
from core.logger import get_logger, setup_logging
from core.database import init_db
from core.scheduler import register_jobs, start, stop
from automation.price_sync import PriceSyncService
from automation.order_processor import OrderProcessor
from automation.tracking_updater import TrackingUpdater

log = get_logger("pipeline")


class AutomationPipeline:
    """완전 자동화 파이프라인."""

    def __init__(self):
        self.price_sync = PriceSyncService()
        self.order_processor = OrderProcessor()
        self.tracking_updater = TrackingUpdater()

    def initialize(self):
        """시스템 초기화."""
        setup_logging("INFO")
        init_db()
        log.info("pipeline_initialized")

    def start_automation(self):
        """자동화 스케줄러 시작."""
        register_jobs(
            price_sync_fn=self.price_sync.sync_all,
            order_check_fn=self.order_processor.check_new_orders,
            oy_purchase_fn=self.order_processor.process_pending_purchases,
            tracking_update_fn=self.tracking_updater.update_tracking,
        )
        start()
        log.info("automation_started")

    def stop_automation(self):
        stop()
        log.info("automation_stopped")

    def manual_price_sync(self):
        self.price_sync.sync_all()

    def manual_order_check(self):
        self.order_processor.check_new_orders()

    def manual_purchase(self):
        self.order_processor.process_pending_purchases()

    def manual_tracking(self):
        self.tracking_updater.update_tracking()
