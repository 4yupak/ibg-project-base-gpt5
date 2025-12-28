"""
Base model and common mixins for all database models.
"""
from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuditMixin:
    """Mixin for audit trail (who created/updated)."""
    
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )


class VersionMixin:
    """Mixin for optimistic locking."""
    
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )


class I18nMixin:
    """Mixin for internationalization (RU/EN content)."""
    
    name_ru: Mapped[str | None] = mapped_column(String(500), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    def get_name(self, lang: str = "en") -> str | None:
        """Get name in specified language with fallback."""
        if lang == "ru":
            return self.name_ru or self.name_en
        return self.name_en or self.name_ru
    
    def get_description(self, lang: str = "en") -> str | None:
        """Get description in specified language with fallback."""
        if lang == "ru":
            return self.description_ru or self.description_en
        return self.description_en or self.description_ru


class VisibilityMixin:
    """Mixin for visibility control (public/internal/partners)."""
    
    visibility: Mapped[str] = mapped_column(
        String(20),
        default="internal",
        nullable=False
    )  # public, internal, partners_only
    
    @property
    def is_public(self) -> bool:
        return self.visibility == "public"
    
    @property
    def is_internal(self) -> bool:
        return self.visibility == "internal"
    
    @property
    def is_partners_only(self) -> bool:
        return self.visibility == "partners_only"
