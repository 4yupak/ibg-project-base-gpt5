"""
Location models: Country, City, District with geo data.
"""
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    ForeignKey, JSON, Index, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Conditional import for GeoAlchemy2 (only for PostgreSQL with PostGIS)
try:
    from geoalchemy2 import Geometry
    HAS_GEOALCHEMY = True
except ImportError:
    HAS_GEOALCHEMY = False
    # Dummy Geometry for SQLite compatibility
    def Geometry(*args, **kwargs):
        return Text

from .base import Base, TimestampMixin, I18nMixin, VisibilityMixin, AuditMixin


class Country(Base, TimestampMixin, I18nMixin):
    """Country model."""
    
    __tablename__ = "countries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)  # ISO 3166-1 alpha-3
    
    # I18nMixin provides: name_ru, name_en, description_ru, description_en
    
    # Geo
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Default currency
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    cities: Mapped[List["City"]] = relationship("City", back_populates="country")


class City(Base, TimestampMixin, I18nMixin, VisibilityMixin):
    """City model."""
    
    __tablename__ = "cities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(Integer, ForeignKey("countries.id"), nullable=False, index=True)
    
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # I18nMixin provides: name_ru, name_en, description_ru, description_en
    
    # Geo
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_zoom: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    
    # Bounding box for map view
    bbox_north: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_south: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_east: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_west: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # SEO
    meta_title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    country: Mapped["Country"] = relationship("Country", back_populates="cities")
    districts: Mapped[List["District"]] = relationship("District", back_populates="city")
    
    __table_args__ = (
        Index("ix_cities_country_active", "country_id", "is_active"),
    )


class District(Base, TimestampMixin, I18nMixin, VisibilityMixin, AuditMixin):
    """District model with detailed info and boundaries."""
    
    __tablename__ = "districts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(Integer, ForeignKey("cities.id"), nullable=False, index=True)
    
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # I18nMixin provides: name_ru, name_en, description_ru, description_en
    
    # Extended descriptions
    advantages_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    advantages_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience_ru: Mapped[str | None] = mapped_column(Text, nullable=True)  # "Для каких ЦА"
    target_audience_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Geo
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # GeoJSON boundary polygon (for map display)
    boundary = Column(Geometry('POLYGON', srid=4326), nullable=True)
    boundary_geojson: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Fallback if PostGIS not used
    
    # Statistics (cached, updated periodically)
    projects_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Cover image
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gallery: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of image URLs
    
    # SEO
    meta_title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    city: Mapped["City"] = relationship("City", back_populates="districts")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="district")
    infrastructure: Mapped[List["Infrastructure"]] = relationship(
        "Infrastructure",
        back_populates="district"
    )
    
    __table_args__ = (
        Index("ix_districts_city_active", "city_id", "is_active"),
        Index("ix_districts_visibility", "visibility"),
    )


class Infrastructure(Base, TimestampMixin, I18nMixin):
    """Points of Interest (POI) - beaches, schools, malls, etc."""
    
    __tablename__ = "infrastructure"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("districts.id"), nullable=True, index=True)
    
    # I18nMixin provides: name_ru, name_en, description_ru, description_en
    
    # Type: beach, school, hospital, mall, restaurant, airport, etc.
    poi_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    poi_category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Sub-category
    
    # Geo
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    
    # Address
    address_ru: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # External references
    google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Display
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Icon name for map
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="infrastructure")
    
    __table_args__ = (
        Index("ix_infrastructure_type", "poi_type"),
        Index("ix_infrastructure_district_type", "district_id", "poi_type"),
    )
