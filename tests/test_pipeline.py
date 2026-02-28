"""가격 계산 및 파이프라인 테스트."""
import pytest
from decimal import Decimal
from config.settings import calculate_selling_price


class TestPriceCalculation:
    """마진 기반 가격 계산 테스트 (가장 중요!)."""

    def test_basic_margin(self):
        """기본 마진율 15% 테스트."""
        result = calculate_selling_price(19900, margin_rate=Decimal("0.15"))
        # 19900 * 1.15 + 500 = 23385 → 100원 올림 → 23400
        assert result["selling_price"] == 23400
        assert result["smartstore_shipping"] == 3000
        assert result["oliveyoung_price"] == 19900

    def test_free_shipping_threshold(self):
        """올리브영 무료배송 기준 (2만원 이상)."""
        result = calculate_selling_price(25000)
        assert result["oliveyoung_shipping"] == 0
        assert result["shipping_profit"] == 3000  # 배송비 전액 이득

    def test_paid_shipping(self):
        """올리브영 유료배송 (2만원 미만)."""
        result = calculate_selling_price(15000)
        assert result["oliveyoung_shipping"] == 2500
        assert result["shipping_profit"] == 500  # 3000 - 2500

    def test_total_profit_calculation(self):
        """총 이익 = 마진 + 배송차익."""
        result = calculate_selling_price(19900, margin_rate=Decimal("0.15"))
        assert result["total_profit"] == result["margin_amount"] + result["shipping_profit"]

    def test_buyer_total_payment(self):
        """구매자 총 결제액 = 판매가 + 배송비."""
        result = calculate_selling_price(19900)
        assert result["total_buyer_pays"] == result["selling_price"] + 3000

    def test_100_won_rounding(self):
        """100원 단위 올림 확인."""
        result = calculate_selling_price(10000, margin_rate=Decimal("0.13"))
        # 10000 * 1.13 + 500 = 11800 → 이미 100원 단위
        assert result["selling_price"] % 100 == 0

    def test_high_margin(self):
        """높은 마진율 테스트."""
        result = calculate_selling_price(50000, margin_rate=Decimal("0.30"))
        assert result["selling_price"] > 50000
        assert result["margin_amount"] > 0

    def test_cheap_product(self):
        """저가 상품 마진 테스트."""
        result = calculate_selling_price(3000, margin_rate=Decimal("0.20"))
        # 3000 * 1.20 + 500 = 4100
        assert result["selling_price"] >= 4100
        assert result["oliveyoung_shipping"] == 2500  # 2만원 미만

    def test_category_margin_override(self):
        """카테고리별 마진 오버라이드."""
        result = calculate_selling_price(
            20000,
            margin_rate=Decimal("0.10"),
            category_margin=Decimal("0.25"),
        )
        # category_margin이 우선: 20000 * 1.25 + 500 = 25500
        assert result["margin_rate"] == 0.25

    def test_zero_price_handling(self):
        """0원 상품 처리."""
        result = calculate_selling_price(0)
        assert result["selling_price"] >= 0
