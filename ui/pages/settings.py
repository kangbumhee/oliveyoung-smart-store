"""설정 페이지 - API 키 관리 + 시스템 설정"""
import streamlit as st
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.secret_manager import save_secrets, load_secrets, get_secret, mask_key, delete_secrets
from config.settings import (
    DEFAULT_MARGIN_RATE,
    SMARTSTORE_SHIPPING_FEE,
    OLIVEYOUNG_SHIPPING_FEE,
    SHIPPING_PROFIT_BUFFER,
    PRICE_SYNC_INTERVAL,
    ORDER_CHECK_INTERVAL,
    TRACKING_CHECK_INTERVAL,
    CATEGORY_MARGINS,
    DELIVERY_COMPANY_CODES,
    calculate_selling_price,
)


def render():
    st.title("⚙️ 설정")

    if "secrets_loaded" not in st.session_state:
        st.session_state.saved_secrets = load_secrets()
        st.session_state.secrets_loaded = True

    saved = st.session_state.saved_secrets

    tab_keys, tab_pricing, tab_schedule, tab_shipping, tab_advanced = st.tabs([
        "🔑 API 키 관리",
        "💰 가격 설정",
        "⏱️ 스케줄 설정",
        "🚚 배송 설정",
        "🔧 고급 설정",
    ])

    # ── TAB 1: API 키 관리 ──
    with tab_keys:
        st.subheader("🔑 API 키 관리")
        st.caption("모든 키는 암호화되어 로컬에 저장됩니다.")

        key_configs = [
            {"env_key": "NAVER_CLIENT_ID", "label": "네이버 커머스 - Client ID", "is_pw": False, "help": "커머스API센터에서 발급"},
            {"env_key": "NAVER_CLIENT_SECRET", "label": "네이버 커머스 - Client Secret", "is_pw": True, "help": "커머스API센터에서 발급"},
            {"env_key": "SMARTSTORE_STORE_NAME", "label": "스마트스토어 스토어명", "is_pw": False, "help": "smartstore.naver.com/여기부분 (예: mumuriri)"},
            {"env_key": "GOOGLE_API_KEY", "label": "Google Gemini API Key", "is_pw": True, "help": "aistudio.google.com/apikey"},
            {"env_key": "OLIVEYOUNG_ID", "label": "올리브영 로그인 ID", "is_pw": False, "help": "올리브영 계정"},
            {"env_key": "OLIVEYOUNG_PW", "label": "올리브영 로그인 PW", "is_pw": True, "help": "올리브영 비밀번호"},
        ]

        registered = sum(1 for k in key_configs if saved.get(k["env_key"]))
        total = len(key_configs)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("등록된 키", f"{registered}/{total}")
        with c2:
            st.metric("설정 상태", "✅ 완료" if registered == total else "⚠️ 미완료")
        with c3:
            st.metric("암호화", "🔐 AES-128")

        st.divider()

        with st.form("api_keys_form", clear_on_submit=False):
            input_values = {}
            for cfg in key_configs:
                ek = cfg["env_key"]
                current = saved.get(ek, "")
                status = f"현재: {mask_key(current)}" if current else "미설정"
                st.caption(f"{cfg['label']} ({status})")
                input_values[ek] = st.text_input(
                    label=cfg["label"],
                    value="",
                    type="password" if cfg["is_pw"] else "default",
                    placeholder=cfg["help"],
                    key=f"input_{ek}",
                    label_visibility="collapsed",
                )

            col_save, col_clear, col_test = st.columns(3)
            with col_save:
                save_clicked = st.form_submit_button("💾 저장", use_container_width=True, type="primary")
            with col_clear:
                clear_clicked = st.form_submit_button("🗑️ 전체 삭제", use_container_width=True)
            with col_test:
                test_clicked = st.form_submit_button("🧪 연결 테스트", use_container_width=True)

        if save_clicked:
            updated = dict(saved)
            changes = []
            for ek, nv in input_values.items():
                nv = nv.strip()
                if nv:
                    updated[ek] = nv
                    changes.append(ek)
            if changes:
                if save_secrets(updated):
                    st.session_state.saved_secrets = updated
                    st.success(f"✅ {len(changes)}개 키 저장됨: {', '.join(changes)}")
                    st.rerun()
                else:
                    st.error("❌ 저장 실패")
            else:
                st.info("변경된 값 없음")

        if clear_clicked:
            if delete_secrets():
                st.session_state.saved_secrets = {}
                st.warning("🗑️ 모든 키 삭제됨")
                st.rerun()

        if test_clicked:
            _run_connection_tests(saved)

        with st.expander("📖 API 키 발급 가이드"):
            st.markdown("""
**네이버 커머스 API**: [apicenter.commerce.naver.com](https://apicenter.commerce.naver.com/) → 앱 등록 → ID/Secret 발급

**Google Gemini API**: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API Key (무료)

**올리브영**: 일반 올리브영 온라인몰 로그인 계정
            """)

    # ── TAB 2: 가격 설정 ──
    with tab_pricing:
        st.subheader("💰 가격 / 마진 설정")

        margin = st.slider("기본 마진율 (%)", 5, 50, int(float(DEFAULT_MARGIN_RATE) * 100), 1, key="margin_slider")

        st.divider()
        st.markdown("**카테고리별 마진율**")
        cat_margins = {}
        for cat, rate in CATEGORY_MARGINS.items():
            cat_margins[cat] = st.slider(f"{cat}", 5, 50, int(float(rate) * 100), 1, key=f"cat_{cat}")

        st.divider()
        st.markdown("**가격 시뮬레이션**")
        sim_price = st.number_input("올리브영 원가 (원)", value=19900, step=100, key="sim_price")
        result = calculate_selling_price(sim_price, margin_rate=Decimal(str(margin / 100)))

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.metric("판매가", f"{result['selling_price']:,}원")
        with p2:
            st.metric("마진 수익", f"{result['margin_amount']:,}원")
        with p3:
            st.metric("배송 수익", f"{result['shipping_profit']:,}원")
        with p4:
            st.metric("총 수익", f"{result['total_profit']:,}원")

        if st.button("💾 가격 설정 저장", key="save_pricing", type="primary"):
            updated = dict(st.session_state.saved_secrets)
            updated["DEFAULT_MARGIN_RATE"] = str(margin / 100)
            if save_secrets(updated):
                st.session_state.saved_secrets = updated
                st.success("✅ 저장 완료")

    # ── TAB 3: 스케줄 설정 ──
    with tab_schedule:
        st.subheader("⏱️ 자동화 스케줄")
        s1, s2 = st.columns(2)
        with s1:
            pi = st.number_input("가격 동기화 주기 (분)", 1, 60, PRICE_SYNC_INTERVAL, key="pi")
            oi = st.number_input("주문 확인 주기 (분)", 1, 30, ORDER_CHECK_INTERVAL, key="oi")
        with s2:
            ti = st.number_input("운송장 확인 주기 (분)", 5, 120, TRACKING_CHECK_INTERVAL, key="ti")
            st.info(f"가격: {pi}분 | 주문: {oi}분 | 운송장: {ti}분")

        if st.button("💾 스케줄 저장", key="save_sched", type="primary"):
            updated = dict(st.session_state.saved_secrets)
            updated["PRICE_SYNC_INTERVAL"] = str(pi)
            updated["ORDER_CHECK_INTERVAL"] = str(oi)
            updated["TRACKING_CHECK_INTERVAL"] = str(ti)
            if save_secrets(updated):
                st.session_state.saved_secrets = updated
                st.success("✅ 저장 완료 (재시작 시 적용)")

    # ── TAB 4: 배송 설정 ──
    with tab_shipping:
        st.subheader("🚚 배송 설정")
        d1, d2, d3 = st.columns(3)
        with d1:
            ss_fee = st.number_input("스마트스토어 배송비", value=SMARTSTORE_SHIPPING_FEE, step=500, key="ss_fee")
        with d2:
            oy_fee = st.number_input("올리브영 배송비", value=OLIVEYOUNG_SHIPPING_FEE, step=500, key="oy_fee")
        with d3:
            buf = st.number_input("배송 이익 버퍼", value=SHIPPING_PROFIT_BUFFER, step=100, key="buf")

        st.info(f"배송 차익: {ss_fee - oy_fee:,}원")
        st.divider()
        st.markdown("**택배사 코드**")
        for company, code in DELIVERY_COMPANY_CODES.items():
            st.text(f"  {company} → {code}")

        if st.button("💾 배송 설정 저장", key="save_ship", type="primary"):
            updated = dict(st.session_state.saved_secrets)
            updated["SMARTSTORE_SHIPPING_FEE"] = str(ss_fee)
            updated["OLIVEYOUNG_SHIPPING_FEE"] = str(oy_fee)
            updated["SHIPPING_PROFIT_BUFFER"] = str(buf)
            if save_secrets(updated):
                st.session_state.saved_secrets = updated
                st.success("✅ 저장 완료")

    # ── TAB 5: 고급 설정 ──
    with tab_advanced:
        st.subheader("🔧 고급 설정")

        gemini_model = st.selectbox("Gemini 모델", ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"], key="gem_model")

        st.divider()
        st.markdown("**데이터 관리**")
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("🗄️ DB 초기화", key="reset_db"):
                try:
                    from core.database import init_db
                    init_db()
                    st.success("✅ DB 초기화 완료")
                except Exception as e:
                    st.error(f"❌ {e}")
        with a2:
            if st.button("📋 로그 삭제", key="clear_logs"):
                import shutil
                from config.settings import LOGS_DIR
                try:
                    if LOGS_DIR.exists():
                        shutil.rmtree(LOGS_DIR)
                        LOGS_DIR.mkdir()
                    st.success("✅ 로그 삭제")
                except Exception as e:
                    st.error(f"❌ {e}")
        with a3:
            if st.button("🔑 API키 리셋", key="reset_keys"):
                if delete_secrets():
                    st.session_state.saved_secrets = {}
                    st.warning("삭제됨")
                    st.rerun()

        if st.button("💾 고급 설정 저장", key="save_adv", type="primary"):
            updated = dict(st.session_state.saved_secrets)
            updated["GEMINI_MODEL"] = gemini_model
            if save_secrets(updated):
                st.session_state.saved_secrets = updated
                st.success("✅ 저장 완료")


def _run_connection_tests(saved: dict):
    st.markdown("---")
    st.markdown("#### 🧪 연결 테스트")

    google_key = saved.get("GOOGLE_API_KEY", "")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            test_model = genai.GenerativeModel("gemini-2.0-flash")
            response = test_model.generate_content("hi")
            if response.text:
                st.success("✅ Google Gemini: 연결 성공")
        except Exception as e:
            st.error(f"❌ Google Gemini: {e}")
    else:
        st.warning("⬜ Google Gemini: 키 미등록")

    naver_id = saved.get("NAVER_CLIENT_ID", "")
    naver_secret = saved.get("NAVER_CLIENT_SECRET", "")
    if naver_id and naver_secret:
        try:
            import time
            import requests
            import bcrypt as _bcrypt
            import pybase64
            timestamp = str(int((time.time() - 3) * 1000))
            password = f"{naver_id}_{timestamp}"
            secret_bytes = naver_secret.encode("utf-8")
            if not secret_bytes.startswith(b"$2a$") and not secret_bytes.startswith(b"$2b$"):
                st.error("❌ 네이버 SECRET이 bcrypt 형식이 아닙니다. $2a$로 시작해야 합니다.")
            else:
                hashed = _bcrypt.hashpw(password.encode("utf-8"), secret_bytes)
                sign = pybase64.standard_b64encode(hashed).decode("utf-8")
                res = requests.post(
                    "https://api.commerce.naver.com/external/v1/oauth2/token",
                    data={"client_id": naver_id, "timestamp": timestamp, "client_secret_sign": sign, "grant_type": "client_credentials", "type": "SELF"},
                )
                if res.status_code == 200 and "access_token" in res.json():
                    st.success("✅ 네이버 커머스 API: 토큰 발급 성공")
                else:
                    st.error(f"❌ 네이버 API: {res.status_code} - {res.text[:200]}")
        except Exception as e:
            st.error(f"❌ 네이버 API: {e}")
    else:
        st.warning("⬜ 네이버 커머스 API: 키 미등록")

    oy_id = saved.get("OLIVEYOUNG_ID", "")
    if oy_id:
        st.info(f"ℹ️ 올리브영: {mask_key(oy_id)} 등록됨")
    else:
        st.warning("⬜ 올리브영: 미등록")
