"""Legal acceptance database model for tracking user compliance acknowledgements."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base


class LegalAcceptanceModel(Base):
    """Database entity persisting immutable user legal agreements and acknowledgements."""

    __tablename__ = "legal_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "document_type",
            "document_version",
            name="uq_legal_acceptance_user_doc_ver",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_version: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    acceptance_method: Mapped[str] = mapped_column(String(32), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
