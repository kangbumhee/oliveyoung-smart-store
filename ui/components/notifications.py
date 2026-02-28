"""알림 컴포넌트."""
import streamlit as st
from core.database import SessionLocal, Order, Product


def check_alerts() -> list[dict]:
    """시스템 알림 확인."""
    alerts = []
    session = SessionLocal()

    # 에러 주문
    error_orders = session.query(Order).filter(Order.status == "error").count()
    if error_orders > 0:
        alerts.append({
            "type": "error",
            "message": f"❌ 에러 주문 {error_orders}건이 있습니다. 확인이 필요합니다.",
        })

    # 품절 상품
    soldout = session.query(Product).filter(Product.status == "soldout").count()
    if soldout > 0:
        alerts.append({
            "type": "warning",
            "message": f"⚠️ 품절 상품 {soldout}개 - 올리브영 재고 확인 필요",
        })

    # 운송장 미등록 (24시간 이상)
    from datetime import datetime, timedelta
    stale_orders = (
        session.query(Order)
        .filter(
            Order.status == "oy_ordered",
            Order.tracking_registered == False,
            Order.oy_ordered_at < datetime.utcnow() - timedelta(hours=24),
        )
        .count()
    )
    if stale_orders > 0:
        alerts.append({
            "type": "warning",
            "message": f"📦 운송장 미등록 {stale_orders}건 (24시간 초과)",
        })

    # 처리 대기 주문
    pending = session.query(Order).filter(Order.status.in_(["new", "confirmed"])).count()
    if pending > 0:
        alerts.append({
            "type": "info",
            "message": f"🛍️ 처리 대기 주문 {pending}건",
        })

    session.close()
    return alerts


def render_alerts():
    """알림 렌더링."""
    alerts = check_alerts()
    for alert in alerts:
        if alert["type"] == "error":
            st.error(alert["message"])
        elif alert["type"] == "warning":
            st.warning(alert["message"])
        else:
            st.info(alert["message"])
