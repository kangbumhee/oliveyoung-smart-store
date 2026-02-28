"""AI 상세설명 생성기 - Google Gemini"""
import google.generativeai as genai
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL
from core.logger import get_logger

logger = get_logger(__name__)
genai.configure(api_key=GOOGLE_API_KEY)

REQUIRED_NOTICE_HTML = """
<div style="max-width:100%;margin:40px auto 0;padding:24px;background-color:#f9f9f9;border:1px solid #ddd;border-radius:8px;font-size:16px;color:#666;line-height:2;">
  <h3 style="color:#333;font-size:20px;margin-bottom:12px;border-bottom:2px solid #ddd;padding-bottom:8px;">📌 구매 안내</h3>
  <p>• 본 상품은 <strong>올리브영 공식 온라인몰</strong>에서 구매하여 국내 배송해드리는 상품입니다.</p>
  <p>• 올리브영에서 정식 유통되는 정품만 취급합니다.</p>
  <p>• 주문 확인 후 올리브영에서 구매 → 고객님께 직접 배송되며, 배송기간은 영업일 기준 2~5일 소요됩니다.</p>
  <p>• 이 제품은 구매대행을 통하여 유통되는 제품입니다.</p>
  <p>• 이 제품은 전기용품 및 생활용품 안전관리법에 따른 안전관리대상 제품입니다.</p>
  <h3 style="color:#333;font-size:20px;margin:20px 0 12px;border-bottom:2px solid #ddd;padding-bottom:8px;">📦 배송 안내</h3>
  <p>• 배송사: 한진택배</p>
  <p>• 배송비: 3,000원 (제주/도서산간 추가 5,000원)</p>
  <p>• 출고 후 1~2일 내 수령 가능 (주말/공휴일 제외)</p>
  <h3 style="color:#333;font-size:20px;margin:20px 0 12px;border-bottom:2px solid #ddd;padding-bottom:8px;">🔄 교환/반품 안내</h3>
  <p>• 상품 수령 후 7일 이내 교환/반품 가능</p>
  <p>• 단, 개봉 후 사용한 상품은 교환/반품이 불가합니다.</p>
  <p>• 고객 변심에 의한 반품 시 왕복 배송비 6,000원이 발생합니다.</p>
  <p>• 상품 하자/오배송의 경우 배송비는 판매자가 부담합니다.</p>
</div>
"""


def _build_image_html(image_urls: list[str]) -> tuple[str, list[str]]:
    """첫 번째 이미지는 상단용 HTML, 나머지는 중간 삽입용 리스트로 반환."""
    if not image_urls:
        return "", []
    top = (
        '<div style="margin:0 0 20px 0;text-align:center;">'
        f'<img src="{image_urls[0]}" alt="" style="max-width:100%;height:auto;display:block;margin:0 auto;" />'
        "</div>"
    )
    middle = [
        f'<div style="margin:20px 0;text-align:center;"><img src="{u}" alt="" style="max-width:100%;height:auto;display:block;margin:0 auto;" /></div>'
        for u in image_urls[1:]
    ]
    return top, middle


def _insert_images_between_sections(html: str, middle_images: list[str]) -> str:
    """</section> 또는 </div> 닫는 태그 사이에 이미지를 균등 배치."""
    if not middle_images:
        return html

    for tag in ["</section>", "</div>"]:
        parts = html.split(tag)
        if len(parts) > 2:
            result = parts[0]
            img_idx = 0
            for i, part in enumerate(parts[1:], 1):
                result += tag
                if img_idx < len(middle_images) and i % 2 == 0:
                    result += middle_images[img_idx]
                    img_idx += 1
                result += part
            return result
    return html


class DescriptionGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate(self, product_info: dict) -> str:
        name = product_info.get("name", "")
        brand = product_info.get("brand", "")
        price = product_info.get("price", 0)
        options = product_info.get("options", [])
        rating = product_info.get("avgRating", "")
        review_count = product_info.get("reviewCount", 0)
        category = product_info.get("category", "")
        prompt = f"""당신은 네이버 스마트스토어 상세페이지 전문 디자이너입니다.
상품명: {name}
브랜드: {brand}
가격: {price:,}원
카테고리: {category}
옵션: {options}
평점: {rating}
리뷰수: {review_count}개

요구사항:
1. 깔끔한 HTML (inline CSS만 사용, <style> 태그 금지)
2. 섹션: 상품 소개, 주요 특징(3-5개), 사용방법, 주의사항
3. 색상: 메인 #FF6B35, 서브 #004E89, 배경 #F7F7F7
4. ★★★ 모바일 최적화 필수 ★★★:
   - 모든 텍스트 최소 font-size: 16px (본문), 제목은 22px 이상
   - p, li, span 등 본문 텍스트는 반드시 font-size: 16px 이상
   - h1은 font-size: 24px, h2는 font-size: 20px 이상
   - line-height: 1.8 이상
   - max-width: 100%, padding: 20px
   - 작은 글씨(13px 이하) 절대 사용 금지
5. 이미지 태그 없이 텍스트만
6. 구매를 유도하는 카피 포함
7. 각 섹션은 <section> 태그로 감싸기

HTML 코드만 출력하세요 (```html 태그 없이):"""
        try:
            response = self.model.generate_content(prompt)
            html = response.text.strip()
            if html.startswith("```html"):
                html = html[7:]
            if html.startswith("```"):
                html = html[3:]
            if html.endswith("```"):
                html = html[:-3]
            html = html.strip()

            image_urls = product_info.get("image_urls") or []
            top_img, middle_imgs = _build_image_html(image_urls)
            if top_img:
                html = top_img + html
            if middle_imgs:
                html = _insert_images_between_sections(html, middle_imgs)

            html += REQUIRED_NOTICE_HTML
            logger.info("description_generated", product=name, length=len(html))
            return html
        except Exception as e:
            logger.error("description_failed", product=name, error=str(e))
            return self._fallback_template(product_info)

    def _fallback_template(self, product_info: dict) -> str:
        name = product_info.get("name", "상품")
        brand = product_info.get("brand", "")
        price = product_info.get("price", 0)
        image_urls = product_info.get("image_urls") or []
        top_img, _ = _build_image_html(image_urls)
        return f"""{top_img}<div style="max-width:100%;margin:0 auto;font-family:'Noto Sans KR',sans-serif;padding:20px;">
  <div style="background:#FF6B35;color:#fff;padding:30px;text-align:center;border-radius:12px;">
    <h1 style="margin:0;font-size:24px;">{name}</h1>
    <p style="margin:10px 0 0;font-size:18px;">{brand}</p>
  </div>
  <div style="background:#F7F7F7;padding:20px;margin-top:20px;border-radius:8px;">
    <h2 style="color:#004E89;font-size:20px;">상품 정보</h2>
    <p style="font-size:16px;">브랜드: {brand}</p>
    <p style="font-size:16px;">판매가: {price:,}원</p>
  </div>
</div>""" + REQUIRED_NOTICE_HTML

    def batch_generate(self, products: list[dict]) -> list[dict]:
        results = []
        for product in products:
            html = self.generate(product)
            results.append({"product_name": product.get("name", ""), "html": html, "length": len(html)})
        return results


def generate_description(
    name: str,
    brand: str,
    sale_price: int,
    options: list[dict] | None = None,
    review_count: int = 0,
    avg_rating: float = 0.0,
    review_summary: str = "",
    image_urls: list[str] | None = None,
) -> str:
    product_info = {
        "name": name,
        "brand": brand,
        "price": sale_price,
        "options": options or [],
        "avgRating": str(avg_rating),
        "reviewCount": review_count,
        "category": "",
        "image_urls": image_urls or [],
    }
    return DescriptionGenerator().generate(product_info)
