"""올리브영 크롤러 테스트."""
import pytest
from scraper.oliveyoung_scraper import OliveYoungScraper


class TestOliveYoungScraper:

    def test_price_extraction_regex(self):
        """HTML에서 가격 정규식 추출 테스트."""
        import re
        html = r'\"salePrice\": 19900, \"originPrice\": 27800'
        sale = re.search(r'\\"salePrice\\":\s*(\d+)', html)
        origin = re.search(r'\\"originPrice\\":\s*(\d+)', html)
        assert sale and sale.group(1) == "19900"
        assert origin and origin.group(1) == "27800"

    def test_bulk_batch_calculation(self):
        """배치 사이즈 계산 확인."""
        goods_nos = [f"A{i:012d}" for i in range(10)]
        batch_size = 3
        batches = [
            goods_nos[i:i + batch_size]
            for i in range(0, len(goods_nos), batch_size)
        ]
        assert len(batches) == 4  # 10 / 3 = 3.33 → 4배치
        assert len(batches[-1]) == 1  # 마지막 배치 1개
