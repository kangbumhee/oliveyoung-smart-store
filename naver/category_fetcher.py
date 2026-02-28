"""네이버 커머스 API로 전체 카테고리 조회 후 로컬 캐싱"""
import json
import requests
from pathlib import Path
from naver.commerce_auth import naver_auth
from core.logger import get_logger

logger = get_logger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "naver_categories.json"


class NaverCategoryFetcher:
    def __init__(self):
        self.auth = naver_auth
        self.categories = []
        self.leaf_categories = []

    def fetch_all(self, force=False) -> list:
        """전체 카테고리를 API로 가져와 캐싱"""
        if not force and CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                self.categories = json.load(f)
                self._build_leaf_list()
                logger.info("categories_loaded_from_cache", count=len(self.categories))
                return self.categories

        token = self.auth.token
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;charset=UTF-8"
        }
        res = requests.get(
            "https://api.commerce.naver.com/external/v1/categories",
            headers=headers,
        )
        if res.status_code == 200:
            self.categories = res.json()
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
            self._build_leaf_list()
            logger.info("categories_fetched_from_api", count=len(self.categories))
        else:
            logger.error("category_fetch_failed", status=res.status_code)
        return self.categories

    def _build_leaf_list(self):
        """leaf 카테고리만 추출"""
        self.leaf_categories = [c for c in self.categories if c.get("leaf", False)]

    def search(self, keyword: str, limit=10) -> list:
        """키워드로 leaf 카테고리 검색"""
        if not self.leaf_categories:
            self.fetch_all()
        results = []
        keyword_lower = keyword.lower()
        for cat in self.leaf_categories:
            name = cat.get("wholeCategoryName", "").lower()
            if keyword_lower in name:
                results.append({
                    "id": str(cat.get("id")),
                    "name": cat.get("wholeCategoryName", ""),
                    "leaf": cat.get("leaf", False),
                })
                if len(results) >= limit:
                    break
        return results

    def get_best_match(self, oliveyoung_category: str, product_name: str = "") -> dict:
        """올리브영 카테고리+상품명으로 최적 leaf 카테고리 자동 선택"""
        if not self.leaf_categories:
            self.fetch_all()

        # ── 권한 없는 화장품 카테고리 → 50000803 강제 변환 ──
        BLOCKED_COSMETIC_IDS = {
            "50000438", "50000463", "50000437", "50000440", "50000441",
            "50000453", "50000474", "50000466", "50000439", "50000442",
            "50000443", "50000444", "50000445", "50000446", "50000447",
            "50000448", "50000449", "50000450", "50000451", "50000452",
            "50000454", "50000455", "50000456", "50000457", "50000458",
            "50000459", "50000460", "50000461", "50000462", "50000464",
            "50000465", "50000467", "50000468", "50000469", "50000470",
            "50000471", "50000472", "50000473", "50000475", "50000476",
        }
        SAFE_COSMETIC = {"id": "50000803", "name": "화장품/미용 > 스킨케어 > 기타스킨케어", "leaf": True}

        search_terms = self._generate_search_terms(oliveyoung_category, product_name)

        health_keywords = [
            "비타민", "유산균", "콜라겐", "오메가", "루테인",
            "프로틴", "홍삼", "인삼", "생식", "다이어트",
            "건강식품", "건강기능", "식품",
        ]

        for term in search_terms:
            results = self.search(term)
            if results:
                is_health = any(k in term or k in product_name for k in health_keywords)

                if is_health:
                    non_beauty = [r for r in results if "화장품" not in r["name"] and "미용" not in r["name"]]
                    if non_beauty:
                        match = non_beauty[0]
                    else:
                        match = results[0]
                else:
                    beauty = [r for r in results if "화장품" in r["name"] or "미용" in r["name"]]
                    if beauty:
                        match = beauty[0]
                    else:
                        match = results[0]

                # 권한 차단 카테고리면 50000803으로 대체
                if match["id"] in BLOCKED_COSMETIC_IDS:
                    logger.info("blocked_category_redirected",
                                original_id=match["id"],
                                original_name=match["name"],
                                redirected_to="50000803")
                    return SAFE_COSMETIC
                return match

        # 최종 폴백
        health_in_product = any(
            k in product_name for k in ["생식", "비타민", "유산균", "홍삼", "프로틴", "다이어트", "식품"]
        )
        if health_in_product:
            fallback = self.search("건강식품")
            if fallback:
                return fallback[0]
            return {"id": "50018980", "name": "식품 > 건강식품 > 건강분말 > 기타건강분말", "leaf": True}

        return SAFE_COSMETIC

    def _generate_search_terms(self, category: str, product_name: str) -> list:
        """올리브영 카테고리에서 검색어 생성"""
        terms = []

        KEYWORD_MAP = {
            "로션": ["로션"],
            "스킨": ["스킨/토너"],
            "토너": ["스킨/토너"],
            "에센스": ["에센스/세럼/앰플"],
            "세럼": ["에센스/세럼/앰플"],
            "앰플": ["에센스/세럼/앰플"],
            "크림": ["크림"],
            "미스트": ["미스트"],
            "오일": ["페이스오일"],
            "아이크림": ["아이케어"],
            "선크림": ["선케어"],
            "선스틱": ["선케어"],
            "자외선": ["선케어"],
            "클렌징": ["클렌징"],
            "클렌저": ["클렌징"],
            "클렌징폼": ["클렌징폼"],
            "클렌징오일": ["클렌징오일"],
            "클렌징워터": ["클렌징워터"],
            "필링": ["필링/각질"],
            "마스크팩": ["마스크/팩"],
            "팩": ["마스크/팩"],
            "패드": ["패드"],
            "립": ["립메이크업"],
            "립스틱": ["립스틱"],
            "립틴트": ["립틴트/라커"],
            "립글로스": ["립글로스"],
            "파운데이션": ["파운데이션"],
            "쿠션": ["쿠션"],
            "프라이머": ["메이크업베이스/프라이머"],
            "컨실러": ["컨실러"],
            "블러셔": ["블러셔/하이라이터"],
            "아이섀도": ["아이섀도"],
            "아이라이너": ["아이라이너"],
            "마스카라": ["마스카라"],
            "아이브로우": ["아이브로"],
            "네일": ["네일"],
            "매니큐어": ["네일에나멜/젤네일"],
            "향수": ["여성향수"],
            "퍼퓸": ["여성향수"],
            "바디로션": ["바디로션/크림"],
            "바디워시": ["바디워시"],
            "바디": ["바디케어"],
            "핸드크림": ["핸드크림"],
            "데오드란트": ["데오드란트"],
            "샴푸": ["샴푸"],
            "린스": ["린스/컨디셔너"],
            "컨디셔너": ["린스/컨디셔너"],
            "트리트먼트": ["헤어트리트먼트/팩"],
            "헤어오일": ["헤어에센스/오일"],
            "헤어에센스": ["헤어에센스/오일"],
            "스타일링": ["스타일링"],
            "염색": ["헤어컬러"],
            "두피": ["두피케어"],
            "비타민": ["비타민"],
            "유산균": ["유산균"],
            "콜라겐": ["콜라겐"],
            "오메가": ["오메가3"],
            "루테인": ["루테인"],
            "프로틴": ["프로틴"],
            "홍삼": ["홍삼/인삼"],
            "생식": ["생식"],
            "다이어트": ["다이어트식품"],
            "식품": ["건강식품"],
            "건강기능": ["건강기능식품"],
            "치약": ["치약"],
            "칫솔": ["칫솔"],
            "면도": ["면도기"],
            "생리대": ["생리대"],
            "물티슈": ["물티슈"],
        }

        for key, values in KEYWORD_MAP.items():
            if key in category:
                terms.extend(values)

        for key, values in KEYWORD_MAP.items():
            if key in product_name:
                for v in values:
                    if v not in terms:
                        terms.append(v)

        if category:
            terms.append(category)

        return terms
