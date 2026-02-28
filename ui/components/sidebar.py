"""사이드바 컴포넌트."""
import streamlit as st


def render_automation_status(is_running: bool):
    """자동화 상태 표시."""
    if is_running:
        st.markdown(
            '<div style="padding:10px;background:#d4edda;border-radius:8px;text-align:center;">'
            '🟢 <b>자동화 실행중</b></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="padding:10px;background:#f8d7da;border-radius:8px;text-align:center;">'
            '🔴 <b>자동화 중지됨</b></div>',
            unsafe_allow_html=True,
        )


def render_quick_stats(total_products: int, today_orders: int, pending: int, errors: int):
    """퀵 통계."""
    st.caption(f"📦 상품 {total_products}개 | 🛍️ 오늘 {today_orders}건 | ⏳ 대기 {pending}건 | ❌ 에러 {errors}건")
