"""
Price versioning and history models - core for price ingestion pipeline.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, TimestampMixin, AuditMixin


class PriceSourceType(str, enum.Enum):
    """Source type for price data."""
    PDF = "pdf"
    EXCEL = "excel"
    GOOGLE_SHEETS = "google_sheets"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    YANDEX_DISK = "yandex_disk"
    MANUAL = "manual"
    API = "api"


class PriceVersionStatus(str, enum.Enum):
    """Status of price version processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentPlan(Base, TimestampMixin, AuditMixin):
    """Payment plan template for a project."""
    
    __tablename__ = "payment_plans"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Plan structure as JSON array
    # [{"milestone": "Booking", "percentage": 10, "due": "On signing"}, ...]
    schedule: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    # Total installment period
    installment_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="payment_plans")
    
    __table_args__ = (
        Index("ix_payment_plans_project_active", "project_id", "is_active"),
    )


class PriceVersion(Base, TimestampMixin, AuditMixin):
    """
    Price version - represents a single price update/import for a project.
    Each import of prices creates a new PriceVersion.
    """
    
    __tablename__ = "price_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Version identifier
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Source information
    source_type: Mapped[PriceSourceType] = mapped_column(
        SQLEnum(PriceSourceType),
        nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # URL to original file
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256 hash for dedup
    
    # Processing status
    status: Mapped[PriceVersionStatus] = mapped_column(
        SQLEnum(PriceVersionStatus),
        default=PriceVersionStatus.PENDING,
        nullable=False
    )
    
    # Processing timestamps
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Results
    units_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_unchanged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Currency info at time of import
    original_currency: Mapped[str] = mapped_column(String(3), default="THB", nullable=False)
    exchange_rate_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    exchange_rate_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Errors and warnings
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of error messages
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of warnings
    
    # Raw data (stored for debugging/reprocessing)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Review
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Notification sent
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="price_versions")
    price_history_entries: Mapped[List["PriceHistory"]] = relationship("PriceHistory", back_populates="price_version")
    
    __table_args__ = (
        Index("ix_price_versions_project_version", "project_id", "version_number"),
    )


class PriceHistory(Base, TimestampMixin):
    """
    Price history - tracks individual unit price changes.
    Stores "было/стало" (before/after) for each price change.
    """
    
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id"), nullable=False)
    price_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("price_versions.id"), nullable=False)
    
    # Old values
    old_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # New values
    new_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Change summary
    price_change: Mapped[float | None] = mapped_column(Float, nullable=True)  # Absolute change
    price_change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)  # % change
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # created, updated, status_change
    
    # Currency at time of change
    currency: Mapped[str] = mapped_column(String(3), default="THB", nullable=False)
    exchange_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="price_history")
    price_version: Mapped["PriceVersion"] = relationship("PriceVersion", back_populates="price_history_entries")
    
    __table_args__ = (
        Index("ix_price_history_unit_version", "unit_id", "price_version_id"),
    )


class ExchangeRate(Base, TimestampMixin):
    """Exchange rate history for currency conversions."""
    
    __tablename__ = "exchange_rates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Source of rate
    source: Mapped[str] = mapped_column(String(50), default="api", nullable=False)
    
    # Date this rate is valid for
    rate_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    __table_args__ = (
        Index("ix_exchange_rates_pair_date", "base_currency", "target_currency", "rate_date"),
    )
