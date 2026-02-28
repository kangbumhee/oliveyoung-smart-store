"""APScheduler 기반 자동화 스케줄러."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config.settings import (
    PRICE_SYNC_INTERVAL, ORDER_CHECK_INTERVAL, TRACKING_CHECK_INTERVAL
)
from core.logger import get_logger

log = get_logger("scheduler")
scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def register_jobs(
    price_sync_fn,
    order_check_fn,
    tracking_update_fn,
    oy_purchase_fn,
):
    """자동화 작업 등록."""
    scheduler.add_job(
        price_sync_fn,
        trigger=IntervalTrigger(minutes=PRICE_SYNC_INTERVAL),
        id="price_sync",
        name="가격/재고 동기화",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        order_check_fn,
        trigger=IntervalTrigger(minutes=ORDER_CHECK_INTERVAL),
        id="order_check",
        name="신규 주문 확인",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        oy_purchase_fn,
        trigger=IntervalTrigger(minutes=ORDER_CHECK_INTERVAL),
        id="oy_purchase",
        name="올리브영 자동 구매",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        tracking_update_fn,
        trigger=IntervalTrigger(minutes=TRACKING_CHECK_INTERVAL),
        id="tracking_update",
        name="운송장 자동 등록",
        replace_existing=True,
        max_instances=1,
    )
    log.info("scheduler_jobs_registered", jobs=len(scheduler.get_jobs()))


def start():
    if not scheduler.running:
        scheduler.start()
        log.info("scheduler_started")


def stop():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")


def get_job_status() -> list[dict]:
    """모든 작업 상태 반환 (UI용)."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else "없음",
            "pending": job.pending,
        })
    return jobs
