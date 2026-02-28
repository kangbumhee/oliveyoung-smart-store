@echo off
echo 🛒 올리브영 → 스마트스토어 자동화 봇 설치
echo ============================================

python -m venv venv
call venv\Scripts\activate

pip install -r requirements.txt

playwright install chromium

if not exist data mkdir data
if not exist logs mkdir logs

if not exist .env (
    copy .env.example .env
    echo ⚠️  .env 파일을 편집하여 API 키를 입력하세요!
)

python -c "from core.database import init_db; init_db()"

echo.
echo ✅ 설치 완료!
echo.
echo 사용법:
echo   1. .env 파일에 API 키 입력
echo   2. streamlit run ui/app.py   → UI 실행
echo   3. python main.py            → 백그라운드 데몬
echo.
pause
