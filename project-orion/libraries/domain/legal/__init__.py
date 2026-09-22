"""Legal, Trust & Risk Disclosure domain layer."""

from .models import (
    DocumentStatus,
    LegalAcceptanceMethod,
    LegalAcceptanceRecord,
    LegalConsentKind,
    LegalDocumentMetadata,
    LegalDocumentType,
)
from .registry import LegalDocumentRegistry, get_canonical_registry

__all__ = [
    "DocumentStatus",
    "LegalAcceptanceMethod",
    "LegalAcceptanceRecord",
    "LegalConsentKind",
    "LegalDocumentMetadata",
    "LegalDocumentRegistry",
    "LegalDocumentType",
    "get_canonical_registry",
]
