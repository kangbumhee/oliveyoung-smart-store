"""
SQLAlchemy + SQLite 데이터베이스.
상품, 주문, 가격이력, 자동화 로그 관리.
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, JSON, ForeignKey, Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from config.settings import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Product(Base):
    """상품 마스터 테이블."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_no = Column(String(50), unique=True, nullable=False, index=True)  # 올리브영 상품번호
    naver_product_id = Column(String(50), nullable=True, index=True)        # 스마트스토어 상품ID
    naver_channel_product_no = Column(String(50), nullable=True)

    # 올리브영 정보
    brand = Column(String(200))
    name = Column(String(500), nullable=False)
    original_name = Column(String(500))  # 원본 상품명 (올리브영)
    parent_category = Column(String(100))
    category = Column(String(100))
    naver_category_id = Column(String(20))

    # 가격
    oy_original_price = Column(Integer, default=0)
    oy_sale_price = Column(Integer, default=0)
    selling_price = Column(Integer, default=0)       # 스마트스토어 판매가
    margin_rate = Column(Float, default=0.15)

    # 상태
    status = Column(String(20), default="pending")   # pending/registered/paused/soldout/error
    is_active = Column(Boolean, default=True)
    auto_sync = Column(Boolean, default=True)        # 자동 가격동기화 여부

    # 메타
    image_url = Column(String(1000))
    detail_html = Column(Text)
    options_json = Column(JSON)
    oy_url = Column(String(1000))
    review_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)
    total_stock = Column(Integer, default=0)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime)
    last_price_changed_at = Column(DateTime)

    # 관계
    price_history = relationship("PriceHistory", back_populates="product")
    orders = relationship("Order", back_populates="product")

    __table_args__ = (
        Index("idx_status_active", "status", "is_active"),
    )


class PriceHistory(Base):
    """가격 변동 이력."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    oy_price_before = Column(Integer)
    oy_price_after = Column(Integer)
    selling_price_before = Column(Integer)
    selling_price_after = Column(Integer)
    changed_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="price_history")


class Order(Base):
    """주문 관리."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"))

    # 스마트스토어 주문 정보
    naver_order_no = Column(String(100), unique=True, index=True)
    naver_product_order_no = Column(String(100), unique=True, index=True)
    buyer_name = Column(String(100))
    buyer_phone = Column(String(50))
    buyer_address = Column(Text)
    buyer_zipcode = Column(String(20))
    order_quantity = Column(Integer, default=1)
    order_option = Column(String(500))
    order_amount = Column(Integer)

    # 올리브영 구매 정보
    oy_order_no = Column(String(100))
    oy_purchase_price = Column(Integer)
    oy_purchase_status = Column(String(30), default="pending")

    # 운송장 정보
    delivery_company = Column(String(50))
    tracking_number = Column(String(100))
    tracking_registered = Column(Boolean, default=False)

    # 상태
    status = Column(String(30), default="new")
    error_message = Column(Text)

    # 타임스탬프
    ordered_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    oy_ordered_at = Column(DateTime)
    shipped_at = Column(DateTime)
    tracking_sent_at = Column(DateTime)
    completed_at = Column(DateTime)

    product = relationship("Product", back_populates="orders")


class AutomationLog(Base):
    """자동화 실행 로그."""
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), index=True)
    status = Column(String(20))
    message = Column(Text)
    details = Column(JSON)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    duration_seconds = Column(Float)


class SystemConfig(Base):
    """런타임 설정 (UI에서 변경 가능)."""
    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """테이블 생성."""
    Base.metadata.create_all(engine)


def get_session():
    """DB 세션 반환."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
