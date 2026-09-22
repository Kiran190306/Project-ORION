"""Canonical registry for Legal, Trust & Risk Disclosure documents."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from .models import (
    DocumentStatus,
    LegalConsentKind,
    LegalDocumentMetadata,
    LegalDocumentType,
)

_CONTENT_DIR: Final[Path] = Path(__file__).parent / "content"


class LegalDocumentRegistry:
    """In-memory canonical catalog of versioned legal documents and disclosures."""

    def __init__(self, content_dir: Path | None = None) -> None:
        self._content_dir = content_dir or _CONTENT_DIR
        self._documents: dict[tuple[LegalDocumentType, str], LegalDocumentMetadata] = {}
        self._active_versions: dict[LegalDocumentType, str] = {}
        self._register_default_documents()

    def _register_default_documents(self) -> None:
        """Initialize default v1.0 canonical documents."""
        defaults = [
            LegalDocumentMetadata(
                document_type=LegalDocumentType.TERMS_OF_SERVICE,
                version="1.0",
                title="Terms of Service",
                summary="Governs platform usage, software licensing, account obligations, acceptable use, and limitations of liability.",
                effective_date="2026-09-22",
                status=DocumentStatus.ACTIVE,
                consent_kind=LegalConsentKind.AGREEMENT,
                requires_consent=True,
                content_filename="TERMS_OF_SERVICE_v1.0.md",
            ),
            LegalDocumentMetadata(
                document_type=LegalDocumentType.PRIVACY_POLICY,
                version="1.0",
                title="Privacy Policy & Data Disclosure",
                summary="Discloses data collection, credential protection, ephemeral session storage, and third-party cloud infrastructure processors.",
                effective_date="2026-09-22",
                status=DocumentStatus.ACTIVE,
                consent_kind=LegalConsentKind.ACKNOWLEDGEMENT,
                requires_consent=True,
                content_filename="PRIVACY_POLICY_v1.0.md",
            ),
            LegalDocumentMetadata(
                document_type=LegalDocumentType.PAPER_RISK_DISCLOSURE,
                version="1.0",
                title="Paper Trading & Financial Risk Disclosure",
                summary="Mandatory disclosure of $0.00 capital at risk, simulation execution limits, hypothetical backtesting disclaimers, and absence of investment advice.",
                effective_date="2026-09-22",
                status=DocumentStatus.ACTIVE,
                consent_kind=LegalConsentKind.ACKNOWLEDGEMENT,
                requires_consent=True,
                content_filename="PAPER_RISK_DISCLOSURE_v1.0.md",
            ),
            LegalDocumentMetadata(
                document_type=LegalDocumentType.REFUND_POLICY,
                version="1.0",
                title="Refund & Subscription Cancellation Policy",
                summary="Outlines recurring monthly subscription billing, self-service cancellation, Stripe test-mode operations, and refund policies.",
                effective_date="2026-09-22",
                status=DocumentStatus.ACTIVE,
                consent_kind=LegalConsentKind.ACKNOWLEDGEMENT,
                requires_consent=False,
                content_filename="REFUND_POLICY_v1.0.md",
            ),
            LegalDocumentMetadata(
                document_type=LegalDocumentType.SECURITY_DISCLOSURE,
                version="1.0",
                title="Security & Trust Architecture",
                summary="Technical overview of implemented security controls including JWT security, AES-256-GCM encryption, rate limiting, and RBAC.",
                effective_date="2026-09-22",
                status=DocumentStatus.ACTIVE,
                consent_kind=LegalConsentKind.INFORMATIONAL,
                requires_consent=False,
                content_filename="SECURITY_DISCLOSURE_v1.0.md",
            ),
        ]

        for doc in defaults:
            self._documents[(doc.document_type, doc.version)] = doc
            if doc.status == DocumentStatus.ACTIVE:
                self._active_versions[doc.document_type] = doc.version

    def get_document(
        self, document_type: LegalDocumentType, version: str | None = None
    ) -> LegalDocumentMetadata | None:
        """Resolve document metadata by type and optional version.

        If version is omitted, returns the currently ACTIVE version.
        """
        target_version = version or self._active_versions.get(document_type)
        if not target_version:
            return None
        return self._documents.get((document_type, target_version))

    def get_document_content(
        self, document_type: LegalDocumentType, version: str | None = None
    ) -> str:
        """Load markdown prose content for the specified document."""
        doc = self.get_document(document_type, version)
        if doc is None:
            raise FileNotFoundError(
                f"No legal document registered for {document_type.value} version {version or 'ACTIVE'}"
            )
        filepath = self._content_dir / doc.content_filename
        if not filepath.is_file():
            raise FileNotFoundError(
                f"Legal content file not found on disk: {filepath}"
            )
        return filepath.read_text(encoding="utf-8")

    def list_active_documents(self) -> list[LegalDocumentMetadata]:
        """Return all active legal documents."""
        return [
            doc
            for doc in self._documents.values()
            if doc.status == DocumentStatus.ACTIVE
        ]

    def is_valid_active_version(
        self, document_type: LegalDocumentType, version: str
    ) -> bool:
        """Check if a given version string corresponds to the currently active version."""
        active_ver = self._active_versions.get(document_type)
        return active_ver is not None and active_ver == version.strip()

    def get_mandatory_registration_documents(self) -> list[LegalDocumentMetadata]:
        """Retrieve documents that must be accepted/acknowledged during new user registration."""
        return [
            doc
            for doc in self.list_active_documents()
            if doc.requires_consent
        ]


_CANONICAL_REGISTRY = LegalDocumentRegistry()


def get_canonical_registry() -> LegalDocumentRegistry:
    """Return singleton canonical legal document registry."""
    return _CANONICAL_REGISTRY
