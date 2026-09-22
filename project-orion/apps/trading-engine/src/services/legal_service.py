"""Legal service managing document metadata retrieval, version validation, and acceptance persistence."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.legal import (
    LegalAcceptanceMethod,
    LegalAcceptanceRecord,
    LegalDocumentMetadata,
    LegalDocumentRegistry,
    LegalDocumentType,
    get_canonical_registry,
)
from libraries.infrastructure.persistence.models.audit import AuditLogModel
from libraries.infrastructure.persistence.models.legal_acceptance import (
    LegalAcceptanceModel,
)

logger = logging.getLogger("trading_engine.services.legal")


class LegalService:
    """Service orchestrating legal document discovery, acceptance verification, and audit trail."""

    def __init__(
        self,
        session: AsyncSession,
        registry: LegalDocumentRegistry | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or get_canonical_registry()

    def list_active_documents(self) -> list[LegalDocumentMetadata]:
        """Return all active legal documents and disclosures."""
        return self.registry.list_active_documents()

    def get_document_metadata(
        self, document_type: LegalDocumentType, version: str | None = None
    ) -> LegalDocumentMetadata | None:
        """Resolve document metadata by type and optional version."""
        return self.registry.get_document(document_type, version)

    def get_document_content(
        self, document_type: LegalDocumentType, version: str | None = None
    ) -> str:
        """Load markdown content for document."""
        return self.registry.get_document_content(document_type, version)

    async def record_acceptance(
        self,
        user_id: str,
        document_type: LegalDocumentType,
        version: str,
        method: LegalAcceptanceMethod = LegalAcceptanceMethod.WEB_IN_APP,
        organization_id: str | None = None,
        user_agent: str | None = None,
    ) -> LegalAcceptanceRecord:
        """Record an immutable document acceptance or acknowledgement.

        Validates version currency and deduplicates idempotent submissions.
        """
        if not self.registry.is_valid_active_version(document_type, version):
            raise ValueError(
                f"Document version '{version}' is not an active version for {document_type.value}"
            )

        # 1. Check for existing acceptance record
        stmt = select(LegalAcceptanceModel).where(
            LegalAcceptanceModel.user_id == user_id,
            LegalAcceptanceModel.document_type == document_type.value,
            LegalAcceptanceModel.document_version == version,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing is not None:
            logger.info(
                "Idempotent legal acceptance skipped for user %s, document %s v%s",
                user_id,
                document_type.value,
                version,
            )
            return LegalAcceptanceRecord(
                id=existing.id,
                user_id=existing.user_id,
                organization_id=existing.organization_id,
                document_type=LegalDocumentType(existing.document_type),
                document_version=existing.document_version,
                accepted_at=existing.accepted_at,
                acceptance_method=LegalAcceptanceMethod(existing.acceptance_method),
                user_agent=existing.user_agent,
            )

        # 2. Persist new immutable acceptance record
        now = datetime.now(timezone.utc)
        record_id = f"lacc_{uuid.uuid4().hex[:16]}"
        model = LegalAcceptanceModel(
            id=record_id,
            user_id=user_id,
            organization_id=organization_id,
            document_type=document_type.value,
            document_version=version,
            accepted_at=now,
            acceptance_method=method.value,
            user_agent=user_agent[:255] if user_agent else None,
        )
        self.session.add(model)

        # 3. Emit immutable compliance audit log event
        doc_meta = self.registry.get_document(document_type, version)
        consent_kind = doc_meta.consent_kind.value if doc_meta else "ACKNOWLEDGEMENT"

        audit_entry = AuditLogModel(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="LEGAL_DOCUMENT_ACCEPTED",
            component="legal_service",
            actor=user_id,
            details={
                "acceptance_id": record_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "document_type": document_type.value,
                "document_version": version,
                "consent_kind": consent_kind,
                "acceptance_method": method.value,
            },
            timestamp=now,
        )
        self.session.add(audit_entry)
        await self.session.flush()

        logger.info(
            "Persisted legal acceptance %s for user %s, doc %s v%s",
            record_id,
            user_id,
            document_type.value,
            version,
        )
        return LegalAcceptanceRecord(
            id=record_id,
            user_id=user_id,
            organization_id=organization_id,
            document_type=document_type,
            document_version=version,
            accepted_at=now,
            acceptance_method=method,
            user_agent=model.user_agent,
        )

    async def record_registration_consents(
        self,
        user_id: str,
        organization_id: str | None = None,
        user_agent: str | None = None,
    ) -> list[LegalAcceptanceRecord]:
        """Record mandatory initial legal agreements and acknowledgements during registration."""
        records: list[LegalAcceptanceRecord] = []
        mandatory_docs = self.registry.get_mandatory_registration_documents()

        for doc in mandatory_docs:
            rec = await self.record_acceptance(
                user_id=user_id,
                document_type=doc.document_type,
                version=doc.version,
                method=LegalAcceptanceMethod.WEB_REGISTRATION,
                organization_id=organization_id,
                user_agent=user_agent,
            )
            records.append(rec)

        return records

    async def list_user_acceptances(
        self, user_id: str
    ) -> Sequence[LegalAcceptanceRecord]:
        """Query historical acceptances for an authenticated user."""
        stmt = (
            select(LegalAcceptanceModel)
            .where(LegalAcceptanceModel.user_id == user_id)
            .order_by(LegalAcceptanceModel.accepted_at.asc())
        )
        res = await self.session.execute(stmt)
        models = res.scalars().all()
        return [
            LegalAcceptanceRecord(
                id=m.id,
                user_id=m.user_id,
                organization_id=m.organization_id,
                document_type=LegalDocumentType(m.document_type),
                document_version=m.document_version,
                accepted_at=m.accepted_at,
                acceptance_method=LegalAcceptanceMethod(m.acceptance_method),
                user_agent=m.user_agent,
            )
            for m in models
        ]
