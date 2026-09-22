"""Institutional onboarding application service orchestrating atomic registration."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.models import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    OrganizationStatus,
)
from libraries.domain.subscription.models import Subscription
from libraries.infrastructure.communication.email_service import get_email_service
from libraries.infrastructure.persistence.models.account import AccountModel
from libraries.infrastructure.persistence.models.audit import AuditLogModel
from libraries.infrastructure.persistence.models.auth_token import (
    AuthTokenModel,
    TokenType,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel, UserStatus

from .auth import (
    create_access_token,
    generate_secure_token,
    get_password_hash,
    hash_security_token,
)
from .organization_service import slugify
from .subscription_service import SubscriptionService

logger = logging.getLogger("trading_engine.services.onboarding")


@dataclass(frozen=True)
class OnboardingResult:
    """Immutable aggregate payload returned upon successful tenant onboarding."""

    user: UserModel
    organization: Organization
    membership: OrganizationMember
    subscription: Subscription
    account: AccountModel
    access_token: str


class OnboardingService:
    """Coordinates atomic customer registration, organization creation, and provisioning."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sub_service = SubscriptionService(session=session)

    async def register_organization(
        self,
        username: str,
        email: str,
        password: str,
        organization_name: str,
        organization_slug: str | None = None,
        full_name: str | None = None,
    ) -> OnboardingResult:
        """Execute transactional onboarding creating User, Organization, Owner, Subscription, and Paper Account."""
        clean_username = username.strip()
        clean_email = email.strip().lower()
        clean_org_name = organization_name.strip()

        if len(clean_username) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if not clean_email or "@" not in clean_email:
            raise ValueError("A valid email address is required.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not clean_org_name:
            raise ValueError("Organization name cannot be blank.")

        final_slug = organization_slug.strip().lower() if organization_slug else slugify(clean_org_name)
        if not final_slug:
            raise ValueError("Organization slug cannot be blank.")

        # 1. Uniqueness pre-checks
        user_check = await self.session.execute(
            select(UserModel).where(
                (UserModel.username == clean_username) | (UserModel.email == clean_email)
            )
        )
        existing_user = user_check.scalar_one_or_none()
        if existing_user is not None:
            if existing_user.username == clean_username:
                raise ValueError(f"Username '{clean_username}' is already registered.")
            raise ValueError(f"Email '{clean_email}' is already registered.")

        org_check = await self.session.execute(
            select(OrganizationModel).where(OrganizationModel.slug == final_slug)
        )
        if org_check.scalar_one_or_none() is not None:
            raise ValueError(f"Organization slug '{final_slug}' is already in use.")

        now = datetime.now(timezone.utc)
        user_id = f"usr_{uuid.uuid4().hex[:16]}"
        org_id = f"org_{uuid.uuid4().hex[:16]}"
        member_id = f"mem_{uuid.uuid4().hex[:16]}"

        try:
            # 2. Create User
            user = UserModel(
                id=user_id,
                username=clean_username,
                email=clean_email,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=False,
                status=UserStatus.ACTIVE.value,
                email_verified=False,
                password_changed_at=now,
                full_name=full_name.strip() if full_name else None,
                meta_data={"registered_via": "onboarding_service"},
                created_at=now,
                updated_at=now,
            )
            self.session.add(user)
            await self.session.flush()

            # 3. Create Organization
            org_model = OrganizationModel(
                id=org_id,
                name=clean_org_name,
                slug=final_slug,
                status=OrganizationStatus.ACTIVE.value,
                meta_data={"onboarded_by": user_id},
                created_at=now,
                updated_at=now,
            )
            self.session.add(org_model)
            await self.session.flush()

            # 4. Create Owner Membership
            member_model = OrganizationMemberModel(
                id=member_id,
                organization_id=org_id,
                user_id=user_id,
                role=OrganizationRole.OWNER.value,
                status=MembershipStatus.ACTIVE.value,
                meta_data={"is_initial_owner": True},
                created_at=now,
                updated_at=now,
            )
            self.session.add(member_model)
            await self.session.flush()

            # 5. Provision default Free Subscription
            subscription = await self.sub_service.assign_default_subscription(org_id)

            # 6. Provision default Initial Paper Trading Account ($100,000.00 USD)
            initial_balance = Decimal("100000.00")
            account = AccountModel(
                id=f"acc-{org_id[:8]}-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                organization_id=org_id,
                broker_name="paper",
                account_number=f"PAPER-ORG-{org_id[:6].upper()}-{uuid.uuid4().hex[:4].upper()}",
                currency="USD",
                balance=initial_balance,
                equity=initial_balance,
                margin=Decimal(0),
                margin_free=initial_balance,
                margin_level=0.0,
                leverage=100,
                is_live=False,
                is_active=True,
                meta_data={"created_by": "onboarding_service", "organization_id": org_id},
                created_at=now,
                updated_at=now,
            )
            self.session.add(account)

            # 7. Record immutable Audit Log
            audit = AuditLogModel(
                id=f"aud_{uuid.uuid4().hex[:16]}",
                organization_id=org_id,
                event_type="organization.onboarded",
                component="onboarding_service",
                actor=user_id,
                details={
                    "organization_name": clean_org_name,
                    "organization_slug": final_slug,
                    "owner_username": clean_username,
                    "initial_balance": str(initial_balance),
                },
                timestamp=now,
            )
            self.session.add(audit)

            # 8. Create Email Verification Token and record USER_REGISTERED event
            raw_token = generate_secure_token()
            token_hash = hash_security_token(raw_token)
            token_record = AuthTokenModel(
                id=f"tok_{uuid.uuid4().hex[:16]}",
                user_id=user_id,
                token_hash=token_hash,
                token_type=TokenType.EMAIL_VERIFICATION.value,
                expires_at=now + timedelta(hours=24),
                used_at=None,
                created_at=now,
                updated_at=now,
            )
            self.session.add(token_record)

            domain_part = clean_email.split("@")[1] if "@" in clean_email else "example.com"
            masked_email = clean_email[:2] + "***@" + domain_part
            user_audit = AuditLogModel(
                id=f"aud_{uuid.uuid4().hex[:16]}",
                organization_id=org_id,
                event_type="USER_REGISTERED",
                component="auth",
                actor=user_id,
                details={"username": clean_username, "email": masked_email},
                timestamp=now,
            )
            self.session.add(user_audit)
            await self.session.flush()

            # Dispatch email verification
            email_svc = get_email_service()
            await email_svc.send_verification_email(clean_email, raw_token, clean_username)

            # 9. Generate Access Token
            access_token = create_access_token(
                data={"sub": user.id, "username": user.username}
            )

            organization = Organization(
                id=org_model.id,
                name=org_model.name,
                slug=org_model.slug,
                status=OrganizationStatus(org_model.status),
                created_at=org_model.created_at,
                updated_at=org_model.updated_at,
                meta_data=dict(org_model.meta_data or {}),
            )
            membership = OrganizationMember(
                id=member_model.id,
                organization_id=member_model.organization_id,
                user_id=member_model.user_id,
                role=OrganizationRole(member_model.role),
                status=MembershipStatus(member_model.status),
                created_at=member_model.created_at,
                updated_at=member_model.updated_at,
                meta_data=dict(member_model.meta_data or {}),
            )

            logger.info("Successfully onboarded organization %s (%s) with owner %s", org_id, final_slug, user_id)
            return OnboardingResult(
                user=user,
                organization=organization,
                membership=membership,
                subscription=subscription,
                account=account,
                access_token=access_token,
            )
        except Exception:
            await self.session.rollback()
            raise
