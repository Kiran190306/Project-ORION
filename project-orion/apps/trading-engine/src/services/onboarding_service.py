"""Institutional onboarding application service orchestrating atomic registration."""

from __future__ import annotations

import copy
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

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
from libraries.infrastructure.persistence.models.onboarding import (
    ONBOARDING_STEP_SEQUENCE,
    OnboardingProgressModel,
)
from libraries.infrastructure.persistence.models.onboarding import (
    OnboardingStatus as ModelOnboardingStatus,
)
from libraries.infrastructure.persistence.models.onboarding import (
    OnboardingStep as ModelOnboardingStep,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.risk import RiskLimitModel
from libraries.infrastructure.persistence.models.strategy import StrategyConfigModel
from libraries.infrastructure.persistence.models.user import UserModel, UserStatus

from ..schemas import (
    OnboardingStatus,
    OnboardingStatusResponse,
    OnboardingStep,
    OnboardingStepDetail,
)
from .auth import (
    create_access_token,
    generate_secure_token,
    get_password_hash,
    hash_security_token,
)
from .legal_service import LegalService
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
    onboarding_progress: OnboardingProgressModel | None = None


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
        user_agent: str | None = None,
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

            # Dispatch email verification (non-blocking for registration transaction)
            try:
                email_svc = get_email_service()
                await email_svc.send_verification_email(clean_email, raw_token, clean_username)
            except Exception as email_exc:  # noqa: BLE001
                logger.warning(
                    "Failed to dispatch verification email during onboarding for %s: %s",
                    clean_email,
                    email_exc,
                )

            # 8b. Record mandatory legal agreements and acknowledgements (Terms, Privacy, Risk Disclosure)
            legal_svc = LegalService(session=self.session)
            await legal_svc.record_registration_consents(
                user_id=user_id,
                organization_id=org_id,
                user_agent=user_agent,
            )

            # 8c. Initialize Persistent Onboarding Progress
            onboarding_progress = OnboardingProgressModel(
                id=f"obp_{uuid.uuid4().hex[:16]}",
                user_id=user_id,
                organization_id=org_id,
                status=ModelOnboardingStatus.NOT_STARTED.value,
                current_step=ModelOnboardingStep.WELCOME.value,
                completed_steps=[],
                completed_at=None,
                meta_data={"registered_via": "onboarding_service"},
                created_at=now,
                updated_at=now,
            )
            self.session.add(onboarding_progress)

            ob_audit = AuditLogModel(
                id=f"aud_{uuid.uuid4().hex[:16]}",
                organization_id=org_id,
                event_type="ONBOARDING_STARTED",
                component="onboarding_service",
                actor=user_id,
                details={"initial_step": ModelOnboardingStep.WELCOME.value},
                timestamp=now,
            )
            self.session.add(ob_audit)

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
                onboarding_progress=onboarding_progress,
            )
        except Exception:
            await self.session.rollback()
            raise

    async def get_or_create_progress(
        self,
        user_id: str,
        organization_id: str,
    ) -> OnboardingStatusResponse:
        """Retrieve or initialize persistent onboarding progress for user and organization."""
        now = datetime.now(timezone.utc)
        stmt = select(OnboardingProgressModel).where(
            OnboardingProgressModel.user_id == user_id,
            OnboardingProgressModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        progress = res.scalar_one_or_none()

        if progress is None:
            # Initialize record for legacy or newly authenticated tenant
            progress = OnboardingProgressModel(
                id=f"obp_{uuid.uuid4().hex[:16]}",
                user_id=user_id,
                organization_id=organization_id,
                status=ModelOnboardingStatus.NOT_STARTED.value,
                current_step=ModelOnboardingStep.WELCOME.value,
                completed_steps=[],
                completed_at=None,
                meta_data={"initialized_via": "get_or_create_progress"},
                created_at=now,
                updated_at=now,
            )
            self.session.add(progress)
            await self.session.flush()

        # Query user state for authoritative checks
        user_stmt = select(UserModel).where(UserModel.id == user_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        email_verified = bool(user.email_verified) if user else False

        # Query paper account state
        acc_stmt = select(AccountModel).where(
            AccountModel.organization_id == organization_id,
            AccountModel.broker_name == "paper",
            AccountModel.is_active == True,
        )
        acc_res = await self.session.execute(acc_stmt)
        paper_account = acc_res.scalar_one_or_none()
        paper_account_ready = paper_account is not None and paper_account.balance > 0

        # Query strategy configuration state
        strat_stmt = select(StrategyConfigModel).where(
            StrategyConfigModel.organization_id == organization_id,
            StrategyConfigModel.is_active == True,
        )
        strat_res = await self.session.execute(strat_stmt)
        active_strat = strat_res.scalar_one_or_none()
        strategy_configured = (
            active_strat is not None
            or ModelOnboardingStep.STRATEGY.value in (progress.completed_steps or [])
            or (progress.meta_data or {}).get("step_data", {}).get("STRATEGY") is not None
        )

        # Query risk configuration state
        risk_stmt = select(RiskLimitModel).where(
            RiskLimitModel.organization_id == organization_id,
            RiskLimitModel.is_enabled == True,
        )
        risk_res = await self.session.execute(risk_stmt)
        active_risk = risk_res.scalar_one_or_none()
        risk_configured = (
            active_risk is not None
            or ModelOnboardingStep.RISK.value in (progress.completed_steps or [])
            or (progress.meta_data or {}).get("step_data", {}).get("RISK") is not None
        )

        # Authoritative synchronization:
        # If user.email_verified is True, and WELCOME has been completed, auto-complete EMAIL_VERIFICATION
        completed_set = set(progress.completed_steps or [])
        updated = False

        if (
            email_verified
            and ModelOnboardingStep.WELCOME.value in completed_set
            and ModelOnboardingStep.EMAIL_VERIFICATION.value not in completed_set
        ):
            completed_set.add(ModelOnboardingStep.EMAIL_VERIFICATION.value)
            progress.completed_steps = [s.value for s in ONBOARDING_STEP_SEQUENCE if s.value in completed_set]
            updated = True

        # Check completed status transition
        all_done = all(s.value in completed_set for s in ONBOARDING_STEP_SEQUENCE)
        if all_done:
            if progress.status != ModelOnboardingStatus.COMPLETED.value:
                progress.status = ModelOnboardingStatus.COMPLETED.value
                progress.completed_at = progress.completed_at or now
                progress.current_step = ModelOnboardingStep.PAPER_TRADING_READY.value
                updated = True
        elif completed_set:
            if progress.status == ModelOnboardingStatus.NOT_STARTED.value:
                progress.status = ModelOnboardingStatus.IN_PROGRESS.value
                updated = True
            # Find next incomplete step
            for s in ONBOARDING_STEP_SEQUENCE:
                if s.value not in completed_set:
                    if progress.current_step != s.value:
                        progress.current_step = s.value
                        updated = True
                    break

        if updated:
            progress.updated_at = now
            await self.session.flush()

        return self._build_status_response(
            progress=progress,
            email_verified=email_verified,
            paper_account_ready=paper_account_ready,
            strategy_configured=strategy_configured,
            risk_configured=risk_configured,
        )

    async def complete_step(
        self,
        user_id: str,
        organization_id: str,
        step_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> OnboardingStatusResponse:
        """Atomically validate and advance persistent onboarding step."""
        now = datetime.now(timezone.utc)
        step_upper = step_name.strip().upper()
        valid_steps = [s.value for s in ONBOARDING_STEP_SEQUENCE]
        if step_upper not in valid_steps:
            raise ValueError(f"Invalid onboarding step '{step_name}'. Valid steps: {valid_steps}")

        # Retrieve or initialize progress
        stmt = select(OnboardingProgressModel).where(
            OnboardingProgressModel.user_id == user_id,
            OnboardingProgressModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        progress = res.scalar_one_or_none()
        if progress is None:
            # First initialize
            await self.get_or_create_progress(user_id=user_id, organization_id=organization_id)
            res = await self.session.execute(stmt)
            progress = res.scalar_one()

        completed_set = set(progress.completed_steps or [])

        # Idempotency: if step is already completed, return status directly
        if step_upper in completed_set:
            return await self.get_or_create_progress(user_id=user_id, organization_id=organization_id)

        # Disallow mutation if already completed
        if progress.status == ModelOnboardingStatus.COMPLETED.value:
            return await self.get_or_create_progress(user_id=user_id, organization_id=organization_id)

        # Sequence enforcement: All prior steps must be completed
        step_index = valid_steps.index(step_upper)
        for prior_idx in range(step_index):
            prior_step = valid_steps[prior_idx]
            if prior_step not in completed_set:
                raise ValueError(
                    f"Cannot complete step '{step_upper}'. Prerequisite step '{prior_step}' must be completed first."
                )

        # Authoritative prerequisite checks:
        user_stmt = select(UserModel).where(UserModel.id == user_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found.")

        if step_upper == ModelOnboardingStep.EMAIL_VERIFICATION.value and not user.email_verified:
            raise ValueError(
                "Email address is not verified. Please verify your corporate email before completing this step."
            )

        if step_upper == ModelOnboardingStep.PAPER_TRADING_READY.value:
            acc_stmt = select(AccountModel).where(
                AccountModel.organization_id == organization_id,
                AccountModel.broker_name == "paper",
                AccountModel.is_active == True,
            )
            acc_res = await self.session.execute(acc_stmt)
            paper_account = acc_res.scalar_one_or_none()
            if paper_account is None or paper_account.balance <= 0:
                raise ValueError("Active paper trading account with positive balance is required.")

        # Advance step
        completed_set.add(step_upper)
        progress.completed_steps = [s.value for s in ONBOARDING_STEP_SEQUENCE if s.value in completed_set]
        flag_modified(progress, "completed_steps")

        # Store metadata if provided
        if metadata:
            current_meta = copy.deepcopy(progress.meta_data or {})
            step_data = current_meta.setdefault("step_data", {})
            step_data[step_upper] = metadata
            progress.meta_data = current_meta
            flag_modified(progress, "meta_data")

        # Update status and current_step
        all_done = all(s.value in completed_set for s in ONBOARDING_STEP_SEQUENCE)
        if all_done:
            progress.status = ModelOnboardingStatus.COMPLETED.value
            progress.completed_at = now
            progress.current_step = ModelOnboardingStep.PAPER_TRADING_READY.value
        else:
            progress.status = ModelOnboardingStatus.IN_PROGRESS.value
            for s in ONBOARDING_STEP_SEQUENCE:
                if s.value not in completed_set:
                    progress.current_step = s.value
                    break

        progress.updated_at = now
        self.session.add(progress)

        # Emit audit log event
        step_audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="ONBOARDING_STEP_COMPLETED",
            component="onboarding_service",
            actor=user_id,
            details={
                "step": step_upper,
                "status": progress.status,
                "current_step": progress.current_step,
            },
            timestamp=now,
        )
        self.session.add(step_audit)

        if all_done:
            comp_audit = AuditLogModel(
                id=f"aud_{uuid.uuid4().hex[:16]}",
                organization_id=organization_id,
                event_type="ONBOARDING_COMPLETED",
                component="onboarding_service",
                actor=user_id,
                details={"completed_steps": progress.completed_steps},
                timestamp=now,
            )
            self.session.add(comp_audit)

        await self.session.flush()

        return await self.get_or_create_progress(user_id=user_id, organization_id=organization_id)

    def _build_status_response(
        self,
        progress: OnboardingProgressModel,
        email_verified: bool,
        paper_account_ready: bool,
        strategy_configured: bool,
        risk_configured: bool,
    ) -> OnboardingStatusResponse:
        """Construct structured OnboardingStatusResponse with step details."""
        completed_set = set(progress.completed_steps or [])
        completed_step_enums = [OnboardingStep(s) for s in progress.completed_steps if s in OnboardingStep.__members__]

        # Determine next step
        next_step: OnboardingStep | None = None
        if progress.status != ModelOnboardingStatus.COMPLETED.value:
            for s in ONBOARDING_STEP_SEQUENCE:
                if s.value not in completed_set and s.value != progress.current_step:
                    next_step = OnboardingStep(s.value)
                    break

        # Step descriptions & descriptors
        step_meta = {
            OnboardingStep.WELCOME: (
                "Welcome & Platform Overview",
                "Account registered and institutional workspace initialized.",
                False,
            ),
            OnboardingStep.EMAIL_VERIFICATION: (
                "Corporate Email Verification",
                "Verify your corporate email address to activate trade execution.",
                True,
            ),
            OnboardingStep.STRATEGY: (
                "Strategy Selection & Configuration",
                "Select and configure an algorithmic strategy for your paper trading portfolio.",
                False,
            ),
            OnboardingStep.RISK: (
                "Risk Thresholds & Limits",
                "Review and set portfolio drawdown and daily loss limit constraints.",
                False,
            ),
            OnboardingStep.PAPER_TRADING_READY: (
                "Paper Trading Simulation Ready",
                "Confirm paper trading balance and activate institutional simulation environment.",
                False,
            ),
        }

        steps_detail: list[OnboardingStepDetail] = []
        valid_step_values = [s.value for s in ONBOARDING_STEP_SEQUENCE]

        for s in ONBOARDING_STEP_SEQUENCE:
            schema_step = OnboardingStep(s.value)
            title, desc, is_auto = step_meta[schema_step]
            is_comp = s.value in completed_set

            # Prerequisite met if all prior steps are completed
            idx = valid_step_values.index(s.value)
            prereqs_met = True
            for p_idx in range(idx):
                if valid_step_values[p_idx] not in completed_set:
                    prereqs_met = False
                    break

            steps_detail.append(
                OnboardingStepDetail(
                    step=schema_step,
                    title=title,
                    description=desc,
                    is_completed=is_comp,
                    is_automated=is_auto,
                    prerequisites_met=prereqs_met,
                )
            )

        completed_at = progress.completed_at
        if completed_at is not None and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        created_at = progress.created_at
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        updated_at = progress.updated_at
        if updated_at is not None and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        return OnboardingStatusResponse(
            id=progress.id,
            user_id=progress.user_id,
            organization_id=progress.organization_id,
            status=OnboardingStatus(progress.status),
            current_step=OnboardingStep(progress.current_step),
            completed_steps=completed_step_enums,
            next_step=next_step,
            steps=steps_detail,
            email_verified=email_verified,
            paper_account_ready=paper_account_ready,
            strategy_configured=strategy_configured,
            risk_configured=risk_configured,
            completed_at=completed_at,
            created_at=created_at,
            updated_at=updated_at,
        )
