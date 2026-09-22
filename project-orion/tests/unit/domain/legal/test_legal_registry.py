"""Unit tests for LegalDocumentRegistry in domain layer."""

from __future__ import annotations

from libraries.domain.legal import (
    DocumentStatus,
    LegalConsentKind,
    LegalDocumentType,
    get_canonical_registry,
)


class TestLegalDocumentRegistry:
    """Test suite verifying canonical legal document registration and retrieval."""

    def test_canonical_registry_contains_five_active_documents(self) -> None:
        registry = get_canonical_registry()
        active_docs = registry.list_active_documents()
        assert len(active_docs) == 5

        doc_types = {d.document_type for d in active_docs}
        expected_types = {
            LegalDocumentType.TERMS_OF_SERVICE,
            LegalDocumentType.PRIVACY_POLICY,
            LegalDocumentType.PAPER_RISK_DISCLOSURE,
            LegalDocumentType.REFUND_POLICY,
            LegalDocumentType.SECURITY_DISCLOSURE,
        }
        assert doc_types == expected_types

    def test_document_metadata_attributes(self) -> None:
        registry = get_canonical_registry()
        terms = registry.get_document(LegalDocumentType.TERMS_OF_SERVICE)
        assert terms is not None
        assert terms.version == "1.0"
        assert terms.title == "Terms of Service"
        assert terms.status == DocumentStatus.ACTIVE
        assert terms.consent_kind == LegalConsentKind.AGREEMENT
        assert terms.requires_consent is True

        privacy = registry.get_document(LegalDocumentType.PRIVACY_POLICY)
        assert privacy is not None
        assert privacy.consent_kind == LegalConsentKind.ACKNOWLEDGEMENT
        assert privacy.requires_consent is True

        risk = registry.get_document(LegalDocumentType.PAPER_RISK_DISCLOSURE)
        assert risk is not None
        assert risk.consent_kind == LegalConsentKind.ACKNOWLEDGEMENT
        assert risk.requires_consent is True

        security = registry.get_document(LegalDocumentType.SECURITY_DISCLOSURE)
        assert security is not None
        assert security.consent_kind == LegalConsentKind.INFORMATIONAL
        assert security.requires_consent is False

    def test_get_document_content_loads_markdown(self) -> None:
        registry = get_canonical_registry()
        content = registry.get_document_content(LegalDocumentType.TERMS_OF_SERVICE)
        assert "Terms of Service" in content
        assert "Draft for legal review" in content
        assert "$0.00 Capital at Risk" in content

    def test_is_valid_active_version(self) -> None:
        registry = get_canonical_registry()
        assert registry.is_valid_active_version(LegalDocumentType.TERMS_OF_SERVICE, "1.0") is True
        assert registry.is_valid_active_version(LegalDocumentType.TERMS_OF_SERVICE, "2.0") is False
        assert registry.is_valid_active_version(LegalDocumentType.TERMS_OF_SERVICE, "0.9") is False

    def test_get_mandatory_registration_documents(self) -> None:
        registry = get_canonical_registry()
        mandatory = registry.get_mandatory_registration_documents()
        assert len(mandatory) == 3
        mandatory_types = {d.document_type for d in mandatory}
        assert mandatory_types == {
            LegalDocumentType.TERMS_OF_SERVICE,
            LegalDocumentType.PRIVACY_POLICY,
            LegalDocumentType.PAPER_RISK_DISCLOSURE,
        }
