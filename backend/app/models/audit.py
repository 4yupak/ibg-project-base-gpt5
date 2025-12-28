"""
Audit logging and system monitoring models.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, TimestampMixin


class AuditAction(str, enum.Enum):
    """Types of audit actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    SHARE = "share"
    APPROVE = "approve"
    REJECT = "reject"


class AuditLog(Base, TimestampMixin):
    """
    Audit log for tracking all important actions in the system.
    """
    
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Who performed the action
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Action details
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction), nullable=False, index=True)
    
    # What was affected
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # project, unit, collection, etc.
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Human-readable name
    
    # Changes (for update actions)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Additional context
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Request info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_created", "created_at"),
    )


class SystemLog(Base, TimestampMixin):
    """
    System logs for errors, warnings, and important system events.
    """
    
    __tablename__ = "system_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Log level
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # debug, info, warning, error, critical
    
    # Source
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Module/service name
    
    # Message
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Additional data
    exception: Mapped[str | None] = mapped_column(Text, nullable=True)  # Exception traceback
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Additional context data
    
    # Related entities (optional)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Request info (if from API request)
    request_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    __table_args__ = (
        Index("ix_system_logs_level_source", "level", "source"),
        Index("ix_system_logs_created", "created_at"),
    )


class ParsingError(Base, TimestampMixin):
    """
    Specific log for price parsing errors - for easy monitoring and fixing.
    """
    
    __tablename__ = "parsing_errors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Related entities
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    price_version_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("price_versions.id"), nullable=True, index=True)
    
    # Error details
    error_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Types: schema_mismatch, invalid_data, currency_error, payment_plan_error, duplicate, unknown
    
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Affected data
    affected_row: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # The row that caused error
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Source file info
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(100), nullable=True)  # For Excel/Sheets
    
    # Resolution
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Notification
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        Index("ix_parsing_errors_project", "project_id"),
        Index("ix_parsing_errors_type_resolved", "error_type", "is_resolved"),
        Index("ix_parsing_errors_created", "created_at"),
    )


from sqlalchemy import Boolean
