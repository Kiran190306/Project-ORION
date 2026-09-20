"""Organization and OrganizationMember database models for SaaS multi-tenancy."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class OrganizationModel(Base, TimestampMixin):
    """Database entity representing an institutional tenant organization."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    members = relationship(
        "OrganizationMemberModel",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship(
        "SubscriptionModel",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationMemberModel(Base, TimestampMixin):
    """Database entity representing a user's membership and institutional role in an organization."""

    __tablename__ = "organization_members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), default="VIEWER", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )

    # Relationships
    organization = relationship("OrganizationModel", back_populates="members")
    user = relationship("UserModel", backref="organization_memberships")
