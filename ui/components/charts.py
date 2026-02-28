"""차트 컴포넌트."""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from core.database import SessionLocal, PriceHistory, Order


def render_price_chart(product_id: int):
    """상품별 가격 변동 차트."""
    session = SessionLocal()
    history = (
        session.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.changed_at)
        .all()
    )
    session.close()

    if not history:
        return None

    df = pd.DataFrame([{
        "시간": h.changed_at,
        "올리브영가": h.oy_price_after,
        "판매가": h.selling_price_after,
    } for h in history])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["시간"], y=df["올리브영가"], name="올리브영가", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=df["시간"], y=df["판매가"], name="판매가", mode="lines+markers"))
    fig.update_layout(
        title="가격 변동 이력",
        xaxis_title="시간",
        yaxis_title="가격 (원)",
        height=400,
    )
    return fig


def render_order_status_chart():
    """주문 상태별 파이 차트."""
    session = SessionLocal()
    orders = session.query(Order).all()
    session.close()

    if not orders:
        return None

    status_counts = {}
    for o in orders:
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    fig = px.pie(
        names=list(status_counts.keys()),
        values=list(status_counts.values()),
        title="주문 상태 분포",
    )
    fig.update_layout(height=400)
    return fig


def render_daily_profit_chart(days: int = 30):
    """일별 예상 수익 차트."""
    session = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)
    orders = (
        session.query(Order)
        .filter(Order.ordered_at >= cutoff, Order.status != "error")
        .all()
    )
    session.close()

    if not orders:
        return None

    daily_data = {}
    for o in orders:
        day = o.ordered_at.strftime("%m/%d") if o.ordered_at else "N/A"
        if day not in daily_data:
            daily_data[day] = {"orders": 0, "revenue": 0}
        daily_data[day]["orders"] += 1
        daily_data[day]["revenue"] += o.order_amount or 0

    df = pd.DataFrame([
        {"날짜": k, "주문수": v["orders"], "매출": v["revenue"]}
        for k, v in daily_data.items()
    ])

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["날짜"], y=df["매출"], name="매출"))
    fig.update_layout(title=f"최근 {days}일 매출", height=400)
    return fig
