# Playwright Browser Automation Skill

이 프로젝트에서 Playwright는 올리브영 자동 구매 및 운송장 추출에 사용됩니다.

## 사용 시나리오
1. 올리브영 로그인 (persistent context로 세션 유지)
2. 상품 페이지 이동 → 옵션 선택 → 수량 설정
3. 배송지를 스마트스토어 구매자 주소로 설정
4. 결제 진행 (무통장입금 우선)
5. 주문완료 페이지에서 주문번호 추출
6. 마이페이지 → 주문/배송 조회에서 운송장번호 추출

## 핵심 패턴
- launch_persistent_context: 로그인 세션 유지
- wait_for_load_state("networkidle"): 페이지 완전 로딩 대기
- query_selector_all + text_content: 동적 요소 탐색
- evaluate(): DOM에서 직접 데이터 추출
- asyncio.sleep(): 자연스러운 행동 패턴 (봇 탐지 우회)

## 올리브영 페이지 구조
- 상품 상세: /store/goods/getGoodsDetail.do?goodsNo=xxx
- 마이페이지: /store/mypage/getMyPageMain.do
- 주문 목록: /store/mypage/getMyOrderDetailList.do
- 로그인: /store/auth/login.do

## 주의사항
- 결제 보안모듈(ActiveX, 이니시스 등)이 있어 headless=True에서 실패할 수 있음
- 처음 로그인 시 CAPTCHA가 나올 수 있어 수동 개입 대기(60초) 포함
- user_data_dir을 유지하여 쿠키/세션 보존
