from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    theme: Mapped[str] = mapped_column(String(10), default="system")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watch_user_symbol"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    average_entry_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    condition: Mapped[dict] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=900)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    provider: Mapped[str] = mapped_column(String(30), default="none")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_payment_id: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="XTR")
    status: Mapped[str] = mapped_column(String(20), default="successful")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
