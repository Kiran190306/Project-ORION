"""Unit tests for LegalService."""

from __future__ import annotations

import uuid

import pytest
from apps.trading_engine.src.services.legal_service import LegalService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.legal import (
    LegalAcceptanceMethod,
    LegalDocumentType,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.audit import AuditLogModel
from libraries.infrastructure.persistence.models.legal_acceptance import (
    LegalAcceptanceModel,
)
from libraries.infrastructure.persistence.models.user import UserModel, UserStatus


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provide an isolated in-memory SQLite async session with schema initialized."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///:memory:?cache=shared_{uuid.uuid4().hex[:8]}",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def sample_user(async_session: AsyncSession) -> UserModel:
    """Create a sample user in the test database."""
    user = UserModel(
        id=f"usr_{uuid.uuid4().hex[:12]}",
        username="trader_legal_test",
        email="trader@orion.legal",
        hashed_password="hashed_dummy_password",
        is_active=True,
        is_superuser=False,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    return user


class TestLegalService:
    """Test suite for LegalService acceptance management and audit logging."""

    async def test_record_acceptance_persists_model_and_audit(
        self, async_session: AsyncSession, sample_user: UserModel
    ) -> None:
        service = LegalService(session=async_session)

        record = await service.record_acceptance(
            user_id=sample_user.id,
            document_type=LegalDocumentType.TERMS_OF_SERVICE,
            version="1.0",
            method=LegalAcceptanceMethod.WEB_IN_APP,
            organization_id=None,
            user_agent="Mozilla/5.0 LegalTester",
        )
        await async_session.commit()

        assert record.id.startswith("lacc_")
        assert record.user_id == sample_user.id
        assert record.document_type == LegalDocumentType.TERMS_OF_SERVICE
        assert record.document_version == "1.0"
        assert record.acceptance_method == LegalAcceptanceMethod.WEB_IN_APP
        assert record.user_agent == "Mozilla/5.0 LegalTester"

        # Verify DB persistence
        stmt = select(LegalAcceptanceModel).where(LegalAcceptanceModel.id == record.id)
        res = await async_session.execute(stmt)
        model = res.scalar_one_or_none()
        assert model is not None
        assert model.user_id == sample_user.id

        # Verify audit log emission
        audit_stmt = select(AuditLogModel).where(
            AuditLogModel.event_type == "LEGAL_DOCUMENT_ACCEPTED"
        )
        audit_res = await async_session.execute(audit_stmt)
        audit_entry = audit_res.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.actor == sample_user.id
        assert audit_entry.details["document_type"] == "TERMS_OF_SERVICE"
        assert audit_entry.details["consent_kind"] == "AGREEMENT"

    async def test_record_acceptance_idempotency_deduplicates(
        self, async_session: AsyncSession, sample_user: UserModel
    ) -> None:
        service = LegalService(session=async_session)

        # First acceptance
        rec1 = await service.record_acceptance(
            user_id=sample_user.id,
            document_type=LegalDocumentType.PRIVACY_POLICY,
            version="1.0",
        )
        await async_session.commit()

        # Duplicate acceptance call
        rec2 = await service.record_acceptance(
            user_id=sample_user.id,
            document_type=LegalDocumentType.PRIVACY_POLICY,
            version="1.0",
        )
        await async_session.commit()

        assert rec1.id == rec2.id

        # Ensure only 1 record exists in DB
        stmt = select(LegalAcceptanceModel).where(
            LegalAcceptanceModel.user_id == sample_user.id,
            LegalAcceptanceModel.document_type == "PRIVACY_POLICY",
        )
        res = await async_session.execute(stmt)
        all_models = res.scalars().all()
        assert len(all_models) == 1

    async def test_record_acceptance_rejects_invalid_version(
        self, async_session: AsyncSession, sample_user: UserModel
    ) -> None:
        service = LegalService(session=async_session)

        with pytest.raises(ValueError, match="not an active version"):
            await service.record_acceptance(
                user_id=sample_user.id,
                document_type=LegalDocumentType.TERMS_OF_SERVICE,
                version="99.9",
            )

    async def test_record_registration_consents(
        self, async_session: AsyncSession, sample_user: UserModel
    ) -> None:
        service = LegalService(session=async_session)

        records = await service.record_registration_consents(
            user_id=sample_user.id,
            organization_id="org_test_123",
            user_agent="RegistrationClient",
        )
        await async_session.commit()

        assert len(records) == 3
        types = {r.document_type for r in records}
        assert types == {
            LegalDocumentType.TERMS_OF_SERVICE,
            LegalDocumentType.PRIVACY_POLICY,
            LegalDocumentType.PAPER_RISK_DISCLOSURE,
        }

        for r in records:
            assert r.acceptance_method == LegalAcceptanceMethod.WEB_REGISTRATION
            assert r.organization_id == "org_test_123"

        # Check user acceptances query
        user_records = await service.list_user_acceptances(sample_user.id)
        assert len(user_records) == 3
