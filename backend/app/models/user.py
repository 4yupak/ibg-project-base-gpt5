"""
User and authentication models.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, TimestampMixin, SoftDeleteMixin


class UserRole(str, enum.Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"
    AGENT = "agent"  # Internal agent
    CONTENT_MANAGER = "content_manager"
    ANALYST = "analyst"
    PARTNER = "partner"  # External agent / partner
    CLIENT = "client"  # Client with collection link access


class AuthProvider(str, enum.Enum):
    """Authentication providers."""
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"
    PHONE = "phone"


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Authentication
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        SQLEnum(AuthProvider), 
        default=AuthProvider.EMAIL,
        nullable=False
    )
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Google/Apple user ID
    
    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Role & Permissions
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.AGENT,
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Agency info (for agents/partners)
    agency_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agency_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Preferences
    preferred_language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)  # en, ru
    preferred_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    preferred_unit: Mapped[str] = mapped_column(String(10), default="sqm", nullable=False)  # sqm, sqft
    
    # Metadata
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # amoCRM integration
    amocrm_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Relationships
    collections: Mapped[List["Collection"]] = relationship(
        "Collection", 
        back_populates="owner",
        foreign_keys="Collection.owner_id"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        foreign_keys="AuditLog.user_id"
    )
    
    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on role."""
        permissions_map = {
            UserRole.ADMIN: ["*"],  # All permissions
            UserRole.AGENT: [
                "projects:read", "units:read", "collections:*",
                "analytics:read", "prices:read"
            ],
            UserRole.CONTENT_MANAGER: [
                "projects:read", "projects:update_content",
                "units:read", "districts:update_content"
            ],
            UserRole.ANALYST: [
                "projects:read", "units:read", "analytics:*",
                "export:csv", "prices:read", "errors:read"
            ],
            UserRole.PARTNER: [
                "projects:read", "units:read", "collections:create",
                "prices:read"
            ],
            UserRole.CLIENT: ["collections:read_shared"]
        }
        
        user_permissions = permissions_map.get(self.role, [])
        
        if "*" in user_permissions:
            return True
        if permission in user_permissions:
            return True
        
        # Check wildcard permissions (e.g., "collections:*" matches "collections:create")
        permission_base = permission.split(":")[0]
        if f"{permission_base}:*" in user_permissions:
            return True
        
        return False


class UserSession(Base, TimestampMixin):
    """User session for tracking active sessions."""
    
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationship
    user: Mapped["User"] = relationship("User")
