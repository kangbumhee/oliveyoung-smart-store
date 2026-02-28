"""
엔트리포인트. 백그라운드 자동화 데몬 또는 UI 실행.
"""
import sys
import signal
import time
from core.logger import setup_logging, get_logger
from core.database import init_db
from automation.pipeline import AutomationPipeline

log = get_logger("main")


def main():
    setup_logging("INFO")
    init_db()

    pipeline = AutomationPipeline()
    pipeline.initialize()
    pipeline.start_automation()

    log.info("bot_started", mode="daemon")
    print("\n" + "=" * 50)
    print("🛒 올리브영 → 스마트스토어 자동화 봇 실행중")
    print("=" * 50)
    print("  ▸ 가격/재고 동기화: 10분 간격")
    print("  ▸ 신규 주문 확인: 3분 간격")
    print("  ▸ 올리브영 자동구매: 3분 간격")
    print("  ▸ 운송장 자동등록: 30분 간격")
    print("=" * 50)
    print("  Ctrl+C로 종료")
    print()

    def graceful_shutdown(signum, frame):
        print("\n⏹ 종료 중...")
        pipeline.stop_automation()
        log.info("bot_stopped", reason="user_interrupt")
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # 메인 루프 (스케줄러가 백그라운드에서 동작)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        graceful_shutdown(None, None)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ui":
        import subprocess
        subprocess.run(["streamlit", "run", "ui/app.py", "--server.port=8501"])
    else:
        main()
