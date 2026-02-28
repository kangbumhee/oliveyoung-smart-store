"""AI 옵션 변환기 - Google Gemini"""
import json
import google.generativeai as genai
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL
from core.logger import get_logger

logger = get_logger(__name__)
genai.configure(api_key=GOOGLE_API_KEY)


class OptionConverter:
    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def convert(self, oliveyoung_options: list | str, product_name: str = "") -> dict:
        if isinstance(oliveyoung_options, str):
            try:
                oliveyoung_options = json.loads(oliveyoung_options)
            except json.JSONDecodeError:
                oliveyoung_options = []
        if not oliveyoung_options:
            return {"optionCombinations": [], "method": "empty"}
        rule_result = self._rule_based_convert(oliveyoung_options)
        if rule_result:
            return rule_result
        return self._ai_convert(oliveyoung_options, product_name)

    def _rule_based_convert(self, options: list) -> dict | None:
        try:
            if not isinstance(options, list):
                return None
            valid_options = [opt for opt in options if isinstance(opt, dict)]
            if not valid_options:
                return None

            combinations = []
            for i, opt in enumerate(valid_options):
                name = opt.get("name", opt.get("optionName", f"옵션{i+1}"))
                price = opt.get("price", opt.get("salePrice", 0))
                stock = opt.get("quantity", opt.get("stock", 0))
                if isinstance(price, str):
                    price = int(price.replace(",", "").replace("원", ""))
                combinations.append({"id": i + 1, "optionName1": str(name), "stockQuantity": int(stock) if stock else 999, "price": int(price), "usable": True})
            if combinations:
                logger.info("rule_based_option", count=len(combinations))
                return {"optionCombinations": combinations, "method": "rule_based"}
        except Exception as e:
            logger.warning("rule_based_failed", error=str(e))
        return None

    def _ai_convert(self, options: list, product_name: str) -> dict:
        prompt = f"""올리브영 상품 옵션을 네이버 스마트스토어 형식으로 변환하세요.
상품명: {product_name}
올리브영 옵션 원본:
{json.dumps(options, ensure_ascii=False, indent=2)}
반드시 아래 JSON 형식으로만 응답:
{{"optionCombinations": [{{"id": 1, "optionName1": "옵션명", "stockQuantity": 999, "price": 15000, "usable": true}}]}}
JSON만 출력하세요:"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            result = json.loads(text)
            result["method"] = "ai_gemini"
            logger.info("ai_option_convert", product=product_name, count=len(result.get("optionCombinations", [])))
            return result
        except Exception as e:
            logger.error("ai_option_failed", product=product_name, error=str(e))
            return {"optionCombinations": [{"id": 1, "optionName1": "기본", "stockQuantity": 999, "price": 0, "usable": True}], "method": "fallback"}

    def batch_convert(self, products: list[dict]) -> list[dict]:
        results = []
        for product in products:
            converted = self.convert(oliveyoung_options=product.get("options", []), product_name=product.get("name", ""))
            converted["product_name"] = product.get("name", "")
            results.append(converted)
        return results


def convert_options(oy_options_json: str | list) -> list[dict]:
    """기존 호환: 네이버 옵션 리스트 형식 반환 (product_manager에서 사용)."""
    converter = OptionConverter()
    raw = converter.convert(oy_options_json)
    combos = raw.get("optionCombinations", [])
    return [
        {
            "name": c.get("optionName1", "기본"),
            "quantity": c.get("stockQuantity", 0),
            "soldOut": not c.get("usable", True),
            "additionalPrice": c.get("price", 0),
        }
        for c in combos
    ]


def clean_option_name_ai(option_name: str) -> str:
    """AI로 옵션명 정리 (기존 호환)."""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            f"다음 옵션명을 스마트스토어에 적합하게 깔끔하게 정리해주세요. "
            f"불필요한 마케팅 문구, 특수문자, 이모지 제거. 핵심 정보만 남겨주세요. 정리된 옵션명만 답해주세요.\n\n옵션명: {option_name}"
        )
        cleaned = response.text.strip()
        return cleaned if cleaned else option_name
    except Exception:
        return option_name
