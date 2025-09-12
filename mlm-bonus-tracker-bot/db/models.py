from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import enum

from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    func,
    Index,
    Enum,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


# -----------------------
# ENUMы
# -----------------------
class UserRole(str, enum.Enum):
    admin = "admin"
    moderator = "moderator"
    partner = "partner"
    client = "client"
    content = "content"  # для контент-менеджеров


class BonusStatus(str, enum.Enum):
    potential = "potential"
    confirmed = "confirmed"
    withdrawn = "withdrawn"


class DealStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    confirmed = "confirmed"
    closed = "closed"


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class NewsStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


# -----------------------
# Пользователи
# -----------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    username: Mapped[Optional[str]] = mapped_column(String(64))
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.partner, index=True)

    sponsor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    level: Mapped[int] = mapped_column(Integer, default=0)

    # 🔑 только баллы, статус вычисляется динамически через utils.roles.get_user_status
    status_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    sponsor: Mapped[Optional["User"]] = relationship(
        back_populates="referrals",
        remote_side="User.id",
        uselist=False,
    )
    referrals: Mapped[List["User"]] = relationship(
        back_populates="sponsor",
        cascade="all,delete",
        foreign_keys=[sponsor_id],
    )

    deals: Mapped[List["Deal"]] = relationship(back_populates="user", cascade="all,delete-orphan")
    bonuses: Mapped[List["Bonus"]] = relationship(back_populates="user", cascade="all,delete-orphan")
    payouts: Mapped[List["Payout"]] = relationship(back_populates="user", cascade="all,delete-orphan")
    materials: Mapped[List["News"]] = relationship(back_populates="author", cascade="all,delete-orphan")
    instructions: Mapped[List["Instruction"]] = relationship(back_populates="author", cascade="all,delete-orphan")
    reviews: Mapped[List["Review"]] = relationship(back_populates="user", cascade="all,delete-orphan")


Index("ix_users_role_status_points", User.role, User.status_points)


# -----------------------
# Сделки
# -----------------------
class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), default=DealStatus.new, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="deals")


Index("ix_deals_user_status", Deal.user_id, Deal.status)


# -----------------------
# Лиды
# -----------------------
class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    name: Mapped[Optional[str]] = mapped_column(String(128))
    phone: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship()


# -----------------------
# Бонусы
# -----------------------
class Bonus(Base):
    __tablename__ = "bonuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[BonusStatus] = mapped_column(Enum(BonusStatus), default=BonusStatus.potential, index=True)
    comment: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="bonuses")


# -----------------------
# Выплаты
# -----------------------
class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[PayoutStatus] = mapped_column(Enum(PayoutStatus), default=PayoutStatus.pending, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="payouts")


# -----------------------
# Контент (Новости/Материалы)
# -----------------------
class News(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status: Mapped[NewsStatus] = mapped_column(Enum(NewsStatus), default=NewsStatus.published, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    author: Mapped[Optional["User"]] = relationship(back_populates="materials")


# -----------------------
# Инструкции
# -----------------------
class Instruction(Base):
    __tablename__ = "instructions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    author: Mapped[Optional["User"]] = relationship(back_populates="instructions")


# -----------------------
# Отзывы
# -----------------------
class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="reviews")


Index("ix_reviews_user_approved", Review.user_id, Review.approved)
