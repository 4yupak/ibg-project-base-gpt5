"""
Unit model - individual property units within projects.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Index, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin


class UnitStatus(str, enum.Enum):
    """Unit availability status."""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    HIDDEN = "hidden"  # Temporarily hidden from listings


class UnitType(str, enum.Enum):
    """Unit bedroom type."""
    STUDIO = "studio"
    ONE_BR = "1br"
    TWO_BR = "2br"
    THREE_BR = "3br"
    FOUR_BR = "4br"
    FIVE_BR = "5br"
    SIX_BR = "6br"
    SEVEN_BR = "7br"
    EIGHT_BR = "8br"
    NINE_BR = "9br"
    TEN_BR = "10br"
    PENTHOUSE = "penthouse"


class ViewType(str, enum.Enum):
    """Unit view type."""
    SEA = "sea"
    POOL = "pool"
    GARDEN = "garden"
    MOUNTAIN = "mountain"
    CITY = "city"
    PARK = "park"
    GOLF = "golf"
    LAKE = "lake"
    RIVER = "river"
    NONE = "none"


class Unit(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Individual unit within a project."""
    
    __tablename__ = "units"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Relations
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    phase_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("project_phases.id"), nullable=True, index=True)
    
    # Identifiers
    unit_number: Mapped[str] = mapped_column(String(50), nullable=False)  # Unit number/code within project
    building: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Building name/number if multiple
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    
    # Type
    unit_type: Mapped[UnitType] = mapped_column(
        SQLEnum(UnitType),
        nullable=False,
        index=True
    )
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bathrooms: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1, 1.5, 2, etc.
    
    # Layout
    layout_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "Type A", "Corner Unit"
    layout_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Area
    area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    area_sqft: Mapped[float | None] = mapped_column(Float, nullable=True)  # Calculated: sqm * 10.764
    indoor_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    outdoor_area: Mapped[float | None] = mapped_column(Float, nullable=True)  # Balcony, terrace
    land_area: Mapped[float | None] = mapped_column(Float, nullable=True)  # For villas
    
    # View
    view_type: Mapped[ViewType | None] = mapped_column(SQLEnum(ViewType), nullable=True)
    view_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Price - Original currency
    price: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="THB", nullable=False)
    price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Price - USD (calculated at exchange rate on update date)
    price_usd: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    price_per_sqm_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    exchange_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # Rate used for USD calc
    exchange_rate_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Previous price (for "было/стало")
    previous_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)  # % change from previous
    price_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Payment
    downpayment_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    downpayment_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    downpayment_amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Status
    status: Mapped[UnitStatus] = mapped_column(
        SQLEnum(UnitStatus),
        default=UnitStatus.AVAILABLE,
        nullable=False,
        index=True
    )
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Features
    features: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of feature slugs
    furniture: Mapped[str | None] = mapped_column(String(50), nullable=True)  # furnished, semi-furnished, unfurnished
    
    # Media
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of image URLs
    floor_plan_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Internal notes (not visible to clients)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Price tracking
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_version_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("price_versions.id"), nullable=True)
    
    # Review status
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="units")
    phase: Mapped["ProjectPhase"] = relationship("ProjectPhase", back_populates="units")
    price_history: Mapped[List["PriceHistory"]] = relationship("PriceHistory", back_populates="unit")
    payment_schedules: Mapped[List["UnitPaymentSchedule"]] = relationship("UnitPaymentSchedule", back_populates="unit")
    
    __table_args__ = (
        UniqueConstraint("project_id", "unit_number", name="uq_unit_project_number"),
        Index("ix_units_project_status", "project_id", "status"),
        Index("ix_units_project_type", "project_id", "unit_type"),
        Index("ix_units_price_range", "price_usd", "status"),
        Index("ix_units_bedrooms_status", "bedrooms", "status"),
        Index("ix_units_floor_status", "floor", "status"),
    )


class UnitPaymentSchedule(Base, TimestampMixin):
    """Payment schedule for a specific unit."""
    
    __tablename__ = "unit_payment_schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    payment_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payment_plans.id"), nullable=True)
    
    # Payment details
    milestone: Mapped[str] = mapped_column(String(100), nullable=False)  # "Booking", "30%", "Completion"
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_description: Mapped[str | None] = mapped_column(String(255), nullable=True)  # "On signing", "Q2 2025"
    
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="payment_schedules")
    payment_plan: Mapped["PaymentPlan"] = relationship("PaymentPlan")
