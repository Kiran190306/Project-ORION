"""Legal, Trust & Risk Disclosure API route endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from libraries.domain.legal import (
    LegalAcceptanceMethod,
    LegalDocumentType,
)

from ..dependencies import (
    get_current_active_user,
    get_legal_service,
)
from ..schemas import (
    LegalAcceptanceResponse,
    LegalDocumentDetailResponse,
    LegalDocumentResponse,
    SubmitLegalAcceptanceRequest,
)
from ..services.legal_service import LegalService

logger = logging.getLogger("trading_engine.routes.legal")

router = APIRouter(prefix="/api/v1/legal", tags=["Legal & Trust Disclosures"])


@router.get(
    "/documents",
    response_model=list[LegalDocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Active Legal Documents",
    description="Returns public catalog of active legal documents, disclosures, versions, and consent requirements.",
)
async def list_legal_documents(
    legal_service: Annotated[LegalService, Depends(get_legal_service)],
) -> list[LegalDocumentResponse]:
    """Retrieve public catalog of active legal documents."""
    docs = legal_service.list_active_documents()
    return [
        LegalDocumentResponse(
            document_type=d.document_type.value,
            version=d.version,
            title=d.title,
            summary=d.summary,
            effective_date=d.effective_date,
            status=d.status.value,
            consent_kind=d.consent_kind.value,
            requires_consent=d.requires_consent,
        )
        for d in docs
    ]


@router.get(
    "/documents/{document_type}",
    response_model=LegalDocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Legal Document Detail",
    description="Returns full document metadata and Markdown prose content for a specified document type.",
)
async def get_legal_document(
    document_type: str,
    legal_service: Annotated[LegalService, Depends(get_legal_service)],
    version: str | None = None,
) -> LegalDocumentDetailResponse:
    """Retrieve detailed legal document with Markdown text."""
    try:
        doc_type_enum = LegalDocumentType(document_type.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown legal document type '{document_type}'",
        ) from exc

    doc_meta = legal_service.get_document_metadata(doc_type_enum, version)
    if doc_meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal document '{document_type}' version '{version or 'ACTIVE'}' not found",
        )

    try:
        content = legal_service.get_document_content(doc_type_enum, version)
    except FileNotFoundError as exc:
        logger.error("Legal document file missing: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document content temporarily unavailable",
        ) from exc

    return LegalDocumentDetailResponse(
        document_type=doc_meta.document_type.value,
        version=doc_meta.version,
        title=doc_meta.title,
        summary=doc_meta.summary,
        effective_date=doc_meta.effective_date,
        status=doc_meta.status.value,
        consent_kind=doc_meta.consent_kind.value,
        requires_consent=doc_meta.requires_consent,
        content_markdown=content,
    )


@router.post(
    "/acceptances",
    response_model=LegalAcceptanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Legal Acceptance",
    description="Records an immutable user agreement or acknowledgement for a specific legal document version.",
)
async def submit_legal_acceptance(
    request: SubmitLegalAcceptanceRequest,
    http_request: Request,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    legal_service: Annotated[LegalService, Depends(get_legal_service)],
) -> LegalAcceptanceResponse:
    """Record an authenticated user's acceptance or acknowledgement."""
    try:
        doc_type_enum = LegalDocumentType(request.document_type.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type '{request.document_type}'",
        ) from exc

    user_id = str(user["id"])
    org_id = http_request.headers.get("X-Organization-ID")
    user_agent = http_request.headers.get("User-Agent")

    try:
        record = await legal_service.record_acceptance(
            user_id=user_id,
            document_type=doc_type_enum,
            version=request.version,
            method=LegalAcceptanceMethod.WEB_IN_APP,
            organization_id=org_id,
            user_agent=user_agent,
        )
        return LegalAcceptanceResponse(
            id=record.id,
            user_id=record.user_id,
            organization_id=record.organization_id,
            document_type=record.document_type.value,
            document_version=record.document_version,
            accepted_at=record.accepted_at,
            acceptance_method=record.acceptance_method.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/acceptances",
    response_model=list[LegalAcceptanceResponse],
    status_code=status.HTTP_200_OK,
    summary="List User Legal Acceptances",
    description="Returns compliance acceptance history for the current authenticated user.",
)
async def list_user_legal_acceptances(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    legal_service: Annotated[LegalService, Depends(get_legal_service)],
) -> list[LegalAcceptanceResponse]:
    """List acceptance history for the calling user."""
    user_id = str(user["id"])
    records = await legal_service.list_user_acceptances(user_id)
    return [
        LegalAcceptanceResponse(
            id=r.id,
            user_id=r.user_id,
            organization_id=r.organization_id,
            document_type=r.document_type.value,
            document_version=r.document_version,
            accepted_at=r.accepted_at,
            acceptance_method=r.acceptance_method.value,
        )
        for r in records
    ]
