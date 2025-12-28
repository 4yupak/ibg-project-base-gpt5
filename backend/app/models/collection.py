"""
Collection models - for creating and sharing property selections with clients.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import secrets

from .base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin


def generate_share_token() -> str:
    """Generate a unique share token for collection."""
    return secrets.token_urlsafe(16)


class Collection(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Collection - a curated selection of projects and units for a client.
    Can be shared via unique link.
    """
    
    __tablename__ = "collections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Owner (agent who created the collection)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Client info (optional, for tracking)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Collection details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # AI-generated selling page content
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Share settings
    share_token: Mapped[str] = mapped_column(
        String(32), 
        unique=True, 
        nullable=False, 
        default=generate_share_token
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Optional password protection
    
    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Display settings
    show_prices: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_availability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    default_language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    
    # Branding
    show_agent_branding: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_agency_branding: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Statistics
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # amoCRM integration
    amocrm_lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amocrm_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="collections", foreign_keys=[owner_id])
    items: Mapped[List["CollectionItem"]] = relationship(
        "CollectionItem",
        back_populates="collection",
        order_by="CollectionItem.sort_order"
    )
    events: Mapped[List["CollectionEvent"]] = relationship(
        "CollectionEvent",
        back_populates="collection"
    )
    
    __table_args__ = (
        Index("ix_collections_owner_active", "owner_id", "is_active"),
    )
    
    @property
    def share_url(self) -> str:
        """Generate the share URL for this collection."""
        return f"/c/{self.share_token}"
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class CollectionItem(Base, TimestampMixin):
    """
    Item in a collection - can be a project or a specific unit.
    """
    
    __tablename__ = "collection_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    
    # Can be either project or unit (or both - unit implies project)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("units.id"), nullable=True, index=True)
    
    # Agent's notes/comments for client
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    note_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Highlight this item
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Display order
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Snapshot of price at time of adding (for comparison)
    price_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_snapshot_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Relationships
    collection: Mapped["Collection"] = relationship("Collection", back_populates="items")
    project: Mapped["Project"] = relationship("Project")
    unit: Mapped["Unit"] = relationship("Unit")
    
    __table_args__ = (
        Index("ix_collection_items_collection", "collection_id"),
        UniqueConstraint("collection_id", "project_id", "unit_id", name="uq_collection_item"),
    )


class CollectionEvent(Base, TimestampMixin):
    """
    Events/analytics for collection - views, inquiries, PDF downloads.
    """
    
    __tablename__ = "collection_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    
    # Event type
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # view, pdf_download, inquiry, whatsapp_click
    
    # Client info (from request)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Additional data
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # If inquiry, store the message
    inquiry_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inquiry_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inquiry_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    inquiry_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # amoCRM sync
    amocrm_synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    collection: Mapped["Collection"] = relationship("Collection", back_populates="events")
    
    __table_args__ = (
        Index("ix_collection_events_collection_type", "collection_id", "event_type"),
        Index("ix_collection_events_created", "created_at"),
    )
