"""
Database models package.
Import all models here for Alembic migrations discovery.
"""

from .base import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    I18nMixin,
    VisibilityMixin,
)

from .user import (
    User,
    UserSession,
    UserRole,
    AuthProvider,
)

from .location import (
    Country,
    City,
    District,
    Infrastructure,
)

from .project import (
    Developer,
    Project,
    ProjectPhase,
    ProjectInfrastructure,
    PropertyType,
    ProjectStatus,
    OwnershipType,
)

from .unit import (
    Unit,
    UnitPaymentSchedule,
    UnitStatus,
    UnitType,
    ViewType,
)

from .price import (
    PaymentPlan,
    PriceVersion,
    PriceHistory,
    ExchangeRate,
    PriceSourceType,
    PriceVersionStatus,
)

from .collection import (
    Collection,
    CollectionItem,
    CollectionEvent,
)

from .audit import (
    AuditLog,
    SystemLog,
    ParsingError,
    AuditAction,
)


__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "VersionMixin",
    "I18nMixin",
    "VisibilityMixin",
    # User
    "User",
    "UserSession",
    "UserRole",
    "AuthProvider",
    # Location
    "Country",
    "City",
    "District",
    "Infrastructure",
    # Project
    "Developer",
    "Project",
    "ProjectPhase",
    "ProjectInfrastructure",
    "PropertyType",
    "ProjectStatus",
    "OwnershipType",
    # Unit
    "Unit",
    "UnitPaymentSchedule",
    "UnitStatus",
    "UnitType",
    "ViewType",
    # Price
    "PaymentPlan",
    "PriceVersion",
    "PriceHistory",
    "ExchangeRate",
    "PriceSourceType",
    "PriceVersionStatus",
    # Collection
    "Collection",
    "CollectionItem",
    "CollectionEvent",
    # Audit
    "AuditLog",
    "SystemLog",
    "ParsingError",
    "AuditAction",
]
