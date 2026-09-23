"""Onboarding state and progress persistence models for Project ORION."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class OnboardingStatus(str, enum.Enum):
    """Lifecycle status of an institutional tenant onboarding journey."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class OnboardingStep(str, enum.Enum):
    """Sequential steps of the guided paper trading onboarding workflow."""

    WELCOME = "WELCOME"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    STRATEGY = "STRATEGY"
    RISK = "RISK"
    PAPER_TRADING_READY = "PAPER_TRADING_READY"


# Canonical progression order for onboarding steps
ONBOARDING_STEP_SEQUENCE: list[OnboardingStep] = [
    OnboardingStep.WELCOME,
    OnboardingStep.EMAIL_VERIFICATION,
    OnboardingStep.STRATEGY,
    OnboardingStep.RISK,
    OnboardingStep.PAPER_TRADING_READY,
]


class OnboardingProgressModel(Base, TimestampMixin):
    """Database entity persisting user and tenant onboarding progress."""

    __tablename__ = "onboarding_progress"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_onboarding_progress_user_org",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=OnboardingStatus.NOT_STARTED.value,
        nullable=False,
        index=True,
    )
    current_step: Mapped[str] = mapped_column(
        String(32),
        default=OnboardingStep.WELCOME.value,
        nullable=False,
    )
    completed_steps: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    user = relationship("UserModel", backref="onboarding_progress")
    organization = relationship("OrganizationModel", backref="onboarding_progress")
