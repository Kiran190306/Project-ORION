"""Domain models, enums, and value objects for Legal, Trust & Risk Disclosures."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime


class LegalDocumentType(str, enum.Enum):
    """Canonical identifier for legal documents and public disclosures."""

    TERMS_OF_SERVICE = "TERMS_OF_SERVICE"
    PRIVACY_POLICY = "PRIVACY_POLICY"
    PAPER_RISK_DISCLOSURE = "PAPER_RISK_DISCLOSURE"
    REFUND_POLICY = "REFUND_POLICY"
    SECURITY_DISCLOSURE = "SECURITY_DISCLOSURE"


class LegalConsentKind(str, enum.Enum):
    """Legal nature of the user's action with respect to a document.

    Distinguishes contractual agreement from informational acknowledgement.
    """

    AGREEMENT = "AGREEMENT"          # Contractual consent (e.g. Terms of Service)
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"  # Receipt & notice acknowledgement (e.g. Privacy, Risk)
    INFORMATIONAL = "INFORMATIONAL"  # Purely informative; no user consent required (e.g. Security)


class DocumentStatus(str, enum.Enum):
    """Lifecycle publication status of a legal document version."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class LegalAcceptanceMethod(str, enum.Enum):
    """Method/context by which user consent or acknowledgement was submitted."""

    WEB_REGISTRATION = "WEB_REGISTRATION"
    WEB_IN_APP = "WEB_IN_APP"
    API = "API"


@dataclass(frozen=True, slots=True)
class LegalDocumentMetadata:
    """Metadata describing a specific versioned legal document."""

    document_type: LegalDocumentType
    version: str
    title: str
    summary: str
    effective_date: str
    status: DocumentStatus
    consent_kind: LegalConsentKind
    requires_consent: bool
    content_filename: str


@dataclass(frozen=True, slots=True)
class LegalAcceptanceRecord:
    """Domain representation of an immutable user legal acceptance/acknowledgement."""

    id: str
    user_id: str
    organization_id: str | None
    document_type: LegalDocumentType
    document_version: str
    accepted_at: datetime
    acceptance_method: LegalAcceptanceMethod
    user_agent: str | None
