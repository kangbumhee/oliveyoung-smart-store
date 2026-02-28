"""
Streamlit 메인 대시보드.
사용자 중심 편의 기능 + 전체 자동화 제어.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
import requests as _requests

sys.path.insert(0, str(Path(__file__).parent.parent))


def _get_oliveyoung_images(goods_no: str, thumbnail_url: str = "", max_images: int = 5) -> list[str]:
    """OliveYoung 상품의 메인 이미지 여러 장을 반환한다."""
    images = []
    _headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # 방법: URL 패턴 직접 생성 + HEAD 확인
    try:
        num_part = goods_no.replace("A", "")
        folder1, folder2 = num_part[:4], num_part[4:8]
        base = (
            f"https://image.oliveyoung.co.kr/cfimages/cf-goods/uploads/images/"
            f"thumbnails/10/{folder1}/{folder2}/{goods_no}"
        )
        for i in range(1, 21):  # 1~20 전체 스캔 (번호가 연속이 아닌 상품 대응)
            if len(images) >= max_images:
                break
            url = f"{base}{i:02d}ko.jpg"
            try:
                r = _requests.head(url, timeout=5, headers=_headers)
                if r.status_code == 200:
                    images.append(url)
            except Exception:
                continue
    except Exception:
        pass

    # fallback: 썸네일 1장
    if not images and thumbnail_url:
        images = [thumbnail_url]

    return images[:max_images]

from core.database import init_db, SessionLocal, Product, Order, PriceHistory, AutomationLog
from core.scheduler import get_job_status
from config.settings import (
    calculate_selling_price, DEFAULT_MARGIN_RATE, CATEGORY_MARGINS,
    SMARTSTORE_SHIPPING_FEE, OLIVEYOUNG_SHIPPING_FEE,
)
from automation.pipeline import AutomationPipeline

st.set_page_config(
    page_title="올리브영 → 스마트스토어 자동화",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

if "pipeline" not in st.session_state:
    st.session_state.pipeline = AutomationPipeline()
    st.session_state.pipeline.initialize()
    st.session_state.automation_running = False


with st.sidebar:
    st.title("🛒 OY → SS Bot")
    st.divider()

    page = st.radio(
        "메뉴",
        ["📊 대시보드", "📦 상품 관리", "🛍️ 주문 관리", "💰 마진 계산기",
         "📤 엑셀 업로드", "⚙️ 설정", "📋 로그"],
        label_visibility="hidden",
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ 자동화 시작", use_container_width=True,
                     disabled=st.session_state.automation_running):
            st.session_state.pipeline.start_automation()
            st.session_state.automation_running = True
            st.success("자동화 시작됨!")
    with col2:
        if st.button("⏹ 자동화 중지", use_container_width=True,
                     disabled=not st.session_state.automation_running):
            st.session_state.pipeline.stop_automation()
            st.session_state.automation_running = False
            st.warning("자동화 중지됨")

    status = "🟢 실행중" if st.session_state.automation_running else "🔴 중지"
    st.caption(f"상태: {status}")

    if st.session_state.automation_running:
        st.divider()
        st.caption("📅 스케줄 현황")
        for job in get_job_status():
            st.caption(f"  {job['name']}: {job['next_run']}")


if page == "📊 대시보드":
    st.title("📊 대시보드")
    session = SessionLocal()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total = session.query(Product).filter(Product.is_active == True).count()
        st.metric("등록 상품", f"{total}개")
    with col2:
        orders_today = (
            session.query(Order)
            .filter(Order.ordered_at >= datetime.today().replace(hour=0))
            .count()
        )
        st.metric("오늘 주문", f"{orders_today}건")
    with col3:
        pending = session.query(Order).filter(Order.status.in_(["new", "confirmed"])).count()
        st.metric("처리 대기", f"{pending}건")
    with col4:
        errors = session.query(Order).filter(Order.status == "error").count()
        st.metric("에러", f"{errors}건", delta_color="inverse")

    st.divider()

    st.subheader("📈 최근 가격 변동")
    price_changes = (
        session.query(PriceHistory)
        .order_by(PriceHistory.changed_at.desc())
        .limit(10)
        .all()
    )
    if price_changes:
        df = pd.DataFrame([{
            "시간": h.changed_at.strftime("%m/%d %H:%M"),
            "올리브영(전)": f"{h.oy_price_before:,}",
            "올리브영(후)": f"{h.oy_price_after:,}",
            "판매가(전)": f"{h.selling_price_before:,}",
            "판매가(후)": f"{h.selling_price_after:,}",
        } for h in price_changes])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("아직 가격 변동 이력이 없습니다.")

    st.subheader("🛍️ 최근 주문")
    recent_orders = (
        session.query(Order)
        .order_by(Order.ordered_at.desc())
        .limit(10)
        .all()
    )
    if recent_orders:
        df = pd.DataFrame([{
            "주문번호": o.naver_order_no,
            "구매자": o.buyer_name,
            "금액": f"{o.order_amount:,}원" if o.order_amount else "-",
            "상태": o.status,
            "운송장": o.tracking_number or "-",
            "주문시간": o.ordered_at.strftime("%m/%d %H:%M") if o.ordered_at else "-",
        } for o in recent_orders])
        st.dataframe(df, use_container_width=True)

    session.close()


elif page == "💰 마진 계산기":
    st.title("💰 마진 계산기")
    st.caption("올리브영 가격을 입력하면 자동으로 판매가와 이익을 계산합니다.")

    col1, col2 = st.columns(2)
    with col1:
        oy_price = st.number_input("올리브영 판매가 (원)", min_value=0, value=19900, step=100)
    with col2:
        margin = st.slider("마진율 (%)", min_value=5, max_value=50, value=15)

    from decimal import Decimal
    result = calculate_selling_price(oy_price, margin_rate=Decimal(str(margin / 100)))

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("스마트스토어 판매가", f"{result['selling_price']:,}원")
    with col2:
        st.metric("구매자 총 결제액", f"{result['total_buyer_pays']:,}원",
                  help="판매가 + 배송비 3,000원")
    with col3:
        st.metric("순이익", f"{result['total_profit']:,}원",
                  delta=f"마진 {result['margin_amount']:,} + 배송차익 {result['shipping_profit']:,}")

    st.divider()
    st.json(result)


elif page == "📤 엑셀 업로드":
    st.title("📤 엑셀 업로드 → 일괄 등록")
    st.caption("올리브영 크롤링 엑셀 파일을 업로드하면 AI가 자동으로 변환하여 스마트스토어에 등록합니다.")

    uploaded = st.file_uploader("엑셀 파일 업로드", type=["xlsx", "xls", "csv"])

    if uploaded:
        if uploaded.name.endswith(".csv"):
            sample = uploaded.read(1000).decode()
            uploaded.seek(0)
            df = pd.read_csv(uploaded, sep="\t" if "\t" in sample else ",")
        else:
            df = pd.read_excel(uploaded)

        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"총 {len(df)}개 상품")

        margin_input = st.slider("일괄 마진율 (%)", 5, 50, 15)

        if st.button("💰 판매가 미리보기"):
            from decimal import Decimal
            preview_rows = []
            for _, row in df.iterrows():
                oy_price = int(row.get("salePrice", 0))
                pricing = calculate_selling_price(
                    oy_price,
                    margin_rate=Decimal(str(margin_input / 100)),
                )
                preview_rows.append({
                    "상품명": str(row.get("name", ""))[:40],
                    "올리브영가": f"{oy_price:,}",
                    "판매가": f"{pricing['selling_price']:,}",
                    "구매자결제": f"{pricing['total_buyer_pays']:,}",
                    "순이익": f"{pricing['total_profit']:,}",
                })
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

        st.divider()

        if st.button("🚀 스마트스토어 일괄 등록", type="primary"):
            from decimal import Decimal
            from ai.category_classifier import classify_category
            from ai.description_generator import generate_description
            from ai.option_converter import convert_options
            from naver.product_manager import NaverProductManager

            naver_pm = NaverProductManager()
            session = SessionLocal()
            progress = st.progress(0)
            status_text = st.empty()

            for idx, row in df.iterrows():
                try:
                    progress.progress((idx + 1) / len(df))
                    name = str(row.get("name", ""))
                    status_text.text(f"처리중 ({idx+1}/{len(df)}): {name[:30]}...")

                    oy_price = int(row.get("salePrice", 0))
                    pricing = calculate_selling_price(
                        oy_price, margin_rate=Decimal(str(margin_input / 100))
                    )

                    cat_id = classify_category(
                        name,
                        str(row.get("brand", "")),
                        str(row.get("parentCategory", "")),
                        str(row.get("category", "")),
                    )

                    thumbnail_url = str(row.get("image", ""))
                    goods_no_str = str(row.get("goodsNo", ""))
                    image_url_list = _get_oliveyoung_images(goods_no_str, thumbnail_url)

                    detail = generate_description(
                        name=name,
                        brand=str(row.get("brand", "")),
                        sale_price=pricing["selling_price"],
                        review_count=int(row.get("reviewCount", 0)),
                        avg_rating=float(row.get("avgRating", 0)),
                        image_urls=image_url_list,
                    )

                    options_raw = row.get("options", "[]")
                    options = convert_options(options_raw)

                    oliveyoung_cat = f"{row.get('parentCategory', '')} {row.get('category', '')}".strip()
                    result = naver_pm.register_product(
                        name=name,
                        selling_price=pricing["selling_price"],
                        category_id=cat_id,
                        detail_html=detail,
                        image_urls=image_url_list,
                        options=options if options else None,
                        stock=int(row.get("totalStock", 999)),
                        brand=str(row.get("brand", "")),
                        oliveyoung_category=oliveyoung_cat,
                    )

                    existing = session.query(Product).filter_by(
                        goods_no=str(row.get("goodsNo", ""))
                    ).first()

                    if existing:
                        existing.naver_product_id = result.get("originProductNo")
                        existing.naver_channel_product_no = result.get("smartstoreChannelProductNo")
                        existing.selling_price = pricing["selling_price"]
                        existing.oy_sale_price = oy_price
                        existing.margin_rate = margin_input / 100
                        existing.status = "registered"
                        existing.detail_html = detail
                        existing.naver_category_id = cat_id
                        existing.updated_at = datetime.utcnow()
                    else:
                        product = Product(
                            goods_no=str(row.get("goodsNo", "")),
                            naver_product_id=result.get("originProductNo"),
                            naver_channel_product_no=result.get("smartstoreChannelProductNo"),
                            brand=str(row.get("brand", "")),
                            name=name,
                            original_name=name,
                            parent_category=str(row.get("parentCategory", "")),
                            category=str(row.get("category", "")),
                            naver_category_id=cat_id,
                            oy_original_price=int(row.get("originalPrice", 0)),
                            oy_sale_price=oy_price,
                            selling_price=pricing["selling_price"],
                            margin_rate=margin_input / 100,
                            status="registered",
                            image_url=str(row.get("image", "")),
                            detail_html=detail,
                            options_json=options,
                            oy_url=str(row.get("url", "")),
                            review_count=int(row.get("reviewCount", 0)),
                            avg_rating=float(row.get("avgRating", 0)),
                            total_stock=int(row.get("totalStock", 999)),
                        )
                        session.add(product)
                    session.commit()

                except Exception as e:
                    st.error(f"❌ {name[:30]}: {str(e)}")
                    session.rollback()

            session.close()
            st.success(f"✅ {len(df)}개 상품 등록 완료!")


elif page == "📦 상품 관리":
    st.title("📦 상품 관리")
    session = SessionLocal()
    products = session.query(Product).order_by(Product.created_at.desc()).all()

    if products:
        df = pd.DataFrame([{
            "ID": p.id,
            "상품명": p.name[:40],
            "브랜드": p.brand,
            "올리브영가": f"{p.oy_sale_price:,}",
            "판매가": f"{p.selling_price:,}",
            "마진율": f"{p.margin_rate*100:.0f}%",
            "재고": p.total_stock,
            "상태": p.status,
            "자동동기화": "✅" if p.auto_sync else "❌",
            "마지막동기화": p.last_synced_at.strftime("%m/%d %H:%M") if p.last_synced_at else "-",
        } for p in products])
        st.dataframe(df, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 전체 가격 동기화"):
                st.session_state.pipeline.manual_price_sync()
                st.success("가격 동기화 완료!")
        with col2:
            if st.button("📋 주문 확인"):
                st.session_state.pipeline.manual_order_check()
                st.success("주문 확인 완료!")
        with col3:
            if st.button("📦 운송장 업데이트"):
                st.session_state.pipeline.manual_tracking()
                st.success("운송장 업데이트 완료!")
    else:
        st.info("등록된 상품이 없습니다. '엑셀 업로드'에서 상품을 등록하세요.")

    session.close()


elif page == "🛍️ 주문 관리":
    st.title("🛍️ 주문 관리")
    session = SessionLocal()

    status_filter = st.selectbox(
        "상태 필터", ["전체", "new", "confirmed", "oy_ordered", "tracking_sent", "error"]
    )

    query = session.query(Order).order_by(Order.ordered_at.desc())
    if status_filter != "전체":
        query = query.filter(Order.status == status_filter)

    orders = query.limit(50).all()

    if orders:
        df = pd.DataFrame([{
            "주문번호": o.naver_order_no,
            "구매자": o.buyer_name,
            "금액": f"{o.order_amount:,}" if o.order_amount else "-",
            "상태": o.status,
            "올리브영주문": o.oy_order_no or "-",
            "운송장": o.tracking_number or "-",
            "에러": o.error_message or "-",
        } for o in orders])
        st.dataframe(df, use_container_width=True)

        if st.button("🔄 에러 주문 재시도"):
            for o in orders:
                if o.status == "error":
                    o.status = "new"
                    o.error_message = None
            session.commit()
            st.success("에러 주문 재시도 예약됨!")
    else:
        st.info("주문 내역이 없습니다.")

    session.close()


elif page == "⚙️ 설정":
    from ui.pages.settings import render as render_settings
    render_settings()


elif page == "📋 로그":
    st.title("📋 자동화 로그")
    session = SessionLocal()
    logs = (
        session.query(AutomationLog)
        .order_by(AutomationLog.started_at.desc())
        .limit(100)
        .all()
    )
    if logs:
        df = pd.DataFrame([{
            "시간": l.started_at.strftime("%m/%d %H:%M:%S"),
            "작업": l.task_type,
            "상태": l.status,
            "메시지": l.message or "",
            "소요시간": f"{l.duration_seconds:.1f}s" if l.duration_seconds else "-",
        } for l in logs])
        st.dataframe(df, use_container_width=True)
    session.close()
