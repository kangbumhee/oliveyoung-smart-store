"""AI 카테고리 분류기 - Google Gemini"""
import json
import google.generativeai as genai
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL
from config.category_mapping import OLIVEYOUNG_TO_NAVER, get_naver_category
from core.logger import get_logger
from naver.category_fetcher import NaverCategoryFetcher

logger = get_logger(__name__)
genai.configure(api_key=GOOGLE_API_KEY)


class CategoryClassifier:
    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.category_fetcher = NaverCategoryFetcher()

    def classify(self, product_name: str, oliveyoung_category: str = "") -> dict:
        # 1차: API 기반 동적 매칭
        try:
            result = self.category_fetcher.get_best_match(oliveyoung_category, product_name)
            if result and result.get("id"):
                return {
                    "naver_category_id": result["id"],
                    "naver_category_name": result["name"],
                    "method": "api_search",
                }
        except Exception as e:
            logger.warning("api_category_search_failed", error=str(e))

        # 2차: 룰 기반 폴백
        if oliveyoung_category:
            naver_cat = get_naver_category(oliveyoung_category)
            if naver_cat:
                return {
                    "naver_category_id": naver_cat["id"],
                    "naver_category_name": naver_cat["name"],
                    "method": "rule_based",
                }

        # 3차: AI
        return self._ai_classify(product_name, oliveyoung_category)

    def _ai_classify(self, product_name: str, oliveyoung_category: str) -> dict:
        category_list = json.dumps({k: v for k, v in OLIVEYOUNG_TO_NAVER.items()}, ensure_ascii=False, indent=2)
        prompt = f"""당신은 네이버 스마트스토어 카테고리 분류 전문가입니다.
상품명: {product_name}
올리브영 카테고리: {oliveyoung_category}
사용 가능한 네이버 카테고리 목록:
{category_list}
반드시 아래 JSON 형식으로만 응답하세요:
{{"naver_category_id": "카테고리ID", "naver_category_name": "카테고리명", "confidence": 0.95}}"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            result = json.loads(text)
            result["method"] = "ai_gemini"
            logger.info("ai_classified", product=product_name, result=result)
            return result
        except Exception as e:
            logger.error("ai_classify_failed", product=product_name, error=str(e))
            return {"naver_category_id": "50000803", "naver_category_name": "스킨케어 기타", "method": "fallback", "confidence": 0.0}

    def batch_classify(self, products: list[dict]) -> list[dict]:
        results = []
        for product in products:
            result = self.classify(product_name=product.get("name", ""), oliveyoung_category=product.get("category", ""))
            result["product_name"] = product.get("name", "")
            results.append(result)
        return results


def classify_category(
    product_name: str,
    brand: str,
    parent_category: str,
    category: str,
) -> str:
    """기존 호환: 네이버 카테고리 ID만 반환."""
    oliveyoung_category = f"{parent_category} > {category}" if (parent_category and category) else parent_category or category
    out = CategoryClassifier().classify(product_name=product_name, oliveyoung_category=oliveyoung_category)
    return out.get("naver_category_id", "50000803")
