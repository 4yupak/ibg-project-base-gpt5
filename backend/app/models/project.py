"""
Project and Developer models - core entities for property listings.
"""
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, Date, DateTime,
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

# Conditional import for GeoAlchemy2 (only for PostgreSQL with PostGIS)
try:
    from geoalchemy2 import Geometry
    HAS_GEOALCHEMY = True
except ImportError:
    HAS_GEOALCHEMY = False
    def Geometry(*args, **kwargs):
        return Text

from .base import Base, TimestampMixin, I18nMixin, VisibilityMixin, AuditMixin, SoftDeleteMixin


class PropertyType(str, enum.Enum):
    """Types of properties."""
    APARTMENT = "apartment"
    VILLA = "villa"
    TOWNHOUSE = "townhouse"
    PENTHOUSE = "penthouse"
    STUDIO = "studio"
    DUPLEX = "duplex"
    LAND = "land"


class ProjectStatus(str, enum.Enum):
    """Project construction/sales status."""
    PRESALE = "presale"
    UNDER_CONSTRUCTION = "under_construction"
    READY = "ready"
    COMPLETED = "completed"
    SOLD_OUT = "sold_out"


class OwnershipType(str, enum.Enum):
    """Property ownership type."""
    FREEHOLD = "freehold"
    LEASEHOLD = "leasehold"
    MIXED = "mixed"


class Developer(Base, TimestampMixin, I18nMixin, SoftDeleteMixin):
    """Developer / Builder company."""
    
    __tablename__ = "developers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # I18nMixin provides: name_ru, name_en, description_ru, description_en
    
    # Company info
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Statistics (cached)
    projects_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_projects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="developer")


class Project(Base, TimestampMixin, I18nMixin, VisibilityMixin, AuditMixin, SoftDeleteMixin):
    """Main project entity - a development/building with units."""
    
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Relations
    developer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("developers.id"), nullable=True, index=True)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey("districts.id"), nullable=False, index=True)
    
    # Identifiers
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    internal_code: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)  # Internal reference
    
    # I18nMixin provides: name_ru, name_en, description_ru, description_en
    
    # Extended content
    sales_points_ru: Mapped[str | None] = mapped_column(Text, nullable=True)  # Key selling points
    sales_points_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Type & Status
    property_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # List of PropertyType values
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.UNDER_CONSTRUCTION,
        nullable=False,
        index=True
    )
    construction_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100%
    
    # Ownership
    ownership_type: Mapped[OwnershipType] = mapped_column(
        SQLEnum(OwnershipType),
        default=OwnershipType.FREEHOLD,
        nullable=False
    )
    leasehold_years: Mapped[int | None] = mapped_column(Integer, nullable=True)  # If leasehold
    
    # Completion dates
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_quarter: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g., "Q2 2025"
    completion_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    
    # Location
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    address_ru: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Price summary (calculated from units, cached)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    max_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_price_per_sqm_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price_per_sqm_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_currency: Mapped[str] = mapped_column(String(3), default="THB", nullable=False)
    
    # Unit statistics (cached)
    total_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Bedroom range
    min_bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Area range
    min_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Media
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gallery: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of image URLs
    master_plan_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    virtual_tour_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    construction_photos: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Progress photos
    
    # Amenities & Features
    amenities: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of amenity slugs
    features: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Additional features
    
    # Internal infrastructure (inside the project)
    internal_infrastructure_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_infrastructure_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Price update tracking
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Source of last price update
    
    # Review status
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Display
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # SEO
    meta_title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # External references
    notion_page_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amocrm_catalog_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Relationships
    developer: Mapped["Developer"] = relationship("Developer", back_populates="projects")
    district: Mapped["District"] = relationship("District", back_populates="projects")
    phases: Mapped[List["ProjectPhase"]] = relationship("ProjectPhase", back_populates="project")
    units: Mapped[List["Unit"]] = relationship("Unit", back_populates="project")
    price_versions: Mapped[List["PriceVersion"]] = relationship("PriceVersion", back_populates="project")
    payment_plans: Mapped[List["PaymentPlan"]] = relationship("PaymentPlan", back_populates="project")
    nearby_infrastructure: Mapped[List["ProjectInfrastructure"]] = relationship(
        "ProjectInfrastructure",
        back_populates="project"
    )
    
    __table_args__ = (
        Index("ix_projects_district_status", "district_id", "status"),
        Index("ix_projects_visibility_active", "visibility", "is_active"),
        Index("ix_projects_price_range", "min_price_usd", "max_price_usd"),
        Index("ix_projects_completion", "completion_year", "completion_quarter"),
        Index("ix_projects_developer", "developer_id", "is_active"),
    )


class ProjectPhase(Base, TimestampMixin):
    """Project construction phase."""
    
    __tablename__ = "project_phases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Dates
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="planned", nullable=False)
    construction_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Statistics
    total_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="phases")
    units: Mapped[List["Unit"]] = relationship("Unit", back_populates="phase")


class ProjectInfrastructure(Base, TimestampMixin):
    """Link between project and nearby infrastructure with distance."""
    
    __tablename__ = "project_infrastructure"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    infrastructure_id: Mapped[int] = mapped_column(Integer, ForeignKey("infrastructure.id"), nullable=False)
    
    # Distance
    distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_minutes_walk: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_minutes_drive: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="nearby_infrastructure")
    infrastructure: Mapped["Infrastructure"] = relationship("Infrastructure")
    
    __table_args__ = (
        Index("ix_project_infrastructure_project", "project_id"),
    )
