# OliveYoung → SmartStore 완전 자동화

## Quick Start
pip install -r requirements.txt && playwright install chromium
cp .env.example .env  # 환경변수 편집
streamlit run ui/app.py  # UI 실행
python main.py  # 백그라운드 데몬

## Test
pytest tests/ -v

## Key Files
- automation/pipeline.py — 전체 자동화 오케스트레이터
- scraper/oliveyoung_scraper.py — 올리브영 고속 크롤링 (내부 API)
- scraper/oliveyoung_buyer.py — 올리브영 자동 구매 (Playwright)
- naver/commerce_auth.py — 네이버 API 인증 (bcrypt 서명)
- config/settings.py — 마진율, 배송비 등 핵심 설정
