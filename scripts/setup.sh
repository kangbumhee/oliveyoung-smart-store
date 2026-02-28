#!/bin/bash
# 초기 설정 스크립트

echo "🛒 올리브영 → 스마트스토어 자동화 봇 설치"
echo "============================================"

# Python 가상환경
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 디렉토리 생성
mkdir -p data logs

# .env 파일
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  .env 파일을 편집하여 API 키를 입력하세요!"
fi

# DB 초기화
python -c "from core.database import init_db; init_db()"

echo ""
echo "✅ 설치 완료!"
echo ""
echo "사용법:"
echo "  1. .env 파일에 API 키 입력"
echo "  2. streamlit run ui/app.py   → UI 실행"
echo "  3. python main.py            → 백그라운드 데몬"
echo ""
