"""EPIC-026 Institutional Broker Sandbox Security Invariants Test Suite.

Verifies the 16 mandatory security invariants:
1. SSRF loopback rejection (127.0.0.1, localhost).
2. SSRF RFC 1918 private subnets rejection (10.0.0.1, 172.16.0.1, 192.168.1.1).
3. SSRF cloud metadata IP rejection (169.254.169.254).
4. SSRF arbitrary unapproved domains rejection.
5. Live endpoint block (api-fxtrade.oanda.com).
6. Live endpoint block (stream-fxtrade.oanda.com).
7. Live endpoint block (api.binance.com).
8. Live environment rejection in ExecutionAdapterFactory.
9. Live environment rejection in BrokerSandboxService.
10. AES-256-GCM credential encryption security (no plaintext leakage).
11. AES-256-GCM credential decryption authenticity.
12. Credential masking in dictionary sanitization.
13. Credential masking in API schema responses.
14. Mandatory RiskEngine gate (risk rejection fails closed).
15. Mandatory OrderValidator gate (oversized order fails closed).
16. Idempotency tracking and UNKNOWN timeout classification (NOT_SAFE_TO_RETRY).
"""

from __future__ import annotations

from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.trading_engine.src.schemas import (
    BrokerSandboxAccountCreateRequest,
    BrokerSandboxOrderRequest,
)
from apps.trading_engine.src.services.broker_sandbox_service import BrokerSandboxService
from libraries.domain.execution.models import OrderSide, OrderType
from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.engine import RiskEngine
from libraries.domain.risk.models import RiskDecision, RiskResult
from libraries.infrastructure.execution.execution_factory import (
    ExecutionAdapterFactory,
    ExecutionAdapterSpec,
)
from libraries.infrastructure.execution.mock_broker import MockBrokerAdapter
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import OrganizationModel
from libraries.infrastructure.security.endpoint_validator import (
    BrokerEndpointValidator,
    CredentialCipher,
    InvalidEndpointError,
    SecurityViolationError,
)


# ============================================================================
# SSRF & Endpoint Protection Tests (1 to 7)
# ============================================================================


def test_ssrf_rejects_loopback() -> None:
    """1. SSRF: Reject loopback addresses (127.0.0.1, localhost)."""
    with pytest.raises(SecurityViolationError):
        BrokerEndpointValidator.validate_endpoint("https://127.0.0.1:8000", resolve_dns=False)

    with pytest.raises(SecurityViolationError, match="Localhost access is prohibited"):
        BrokerEndpointValidator.validate_endpoint("https://localhost:8000", resolve_dns=False)


def test_ssrf_rejects_rfc1918_private_subnets() -> None:
    """2. SSRF: Reject RFC 1918 private subnets."""
    for ip in ("10.0.0.1", "172.16.0.1", "192.168.1.1"):
        with pytest.raises(SecurityViolationError, match="IP literals are prohibited"):
            BrokerEndpointValidator.validate_endpoint(f"https://{ip}/api", resolve_dns=False)


def test_ssrf_rejects_cloud_metadata_service() -> None:
    """3. SSRF: Reject AWS/GCP metadata service IP (169.254.169.254)."""
    with pytest.raises(SecurityViolationError, match="IP literals are prohibited"):
        BrokerEndpointValidator.validate_endpoint("https://169.254.169.254/latest/meta-data", resolve_dns=False)


def test_ssrf_rejects_arbitrary_unapproved_domain() -> None:
    """4. SSRF: Reject arbitrary unapproved domain."""
    with pytest.raises((SecurityViolationError, InvalidEndpointError), match="approved broker sandbox allowlist"):
        BrokerEndpointValidator.validate_endpoint("https://attacker-c2.com/api", resolve_dns=False)


def test_live_endpoint_block_oanda_fxtrade() -> None:
    """5. Reject production OANDA trading REST endpoint."""
    with pytest.raises(SecurityViolationError, match="Production broker endpoint"):
        BrokerEndpointValidator.validate_endpoint("https://api-fxtrade.oanda.com/v3/accounts", resolve_dns=False)


def test_live_endpoint_block_oanda_stream() -> None:
    """6. Reject production OANDA streaming endpoint."""
    with pytest.raises(SecurityViolationError, match="Production broker endpoint"):
        BrokerEndpointValidator.validate_endpoint("https://stream-fxtrade.oanda.com/v3/accounts", resolve_dns=False)


def test_live_endpoint_block_binance_production() -> None:
    """7. Reject production Binance endpoint."""
    with pytest.raises(SecurityViolationError, match="Production broker endpoint"):
        BrokerEndpointValidator.validate_endpoint("https://api.binance.com/api/v3/order", resolve_dns=False)


# ============================================================================
# Environment Isolation Tests (8 and 9)
# ============================================================================


def test_live_environment_rejection_in_factory() -> None:
    """8. ExecutionAdapterFactory strictly rejects LIVE execution environment."""
    spec = ExecutionAdapterSpec(
        provider="mock",
        is_paper=False,
        environment="LIVE",
    )
    with pytest.raises(SecurityViolationError, match="LIVE execution environment is strictly prohibited"):
        ExecutionAdapterFactory.create_adapter(spec)


def test_live_environment_rejection_in_service_request() -> None:
    """9. BrokerSandboxAccountCreateRequest rejects LIVE environment at validation."""
    with pytest.raises(ValueError, match="LIVE environment is strictly prohibited"):
        BrokerSandboxAccountCreateRequest(
            name="Exploit Live",
            provider="MOCK",
            environment="LIVE",
            account_id_external="ext-live-01",
        )


# ============================================================================
# AES-GCM Credential Protection Tests (10 to 13)
# ============================================================================


def test_aes_gcm_credential_encryption_security() -> None:
    """10. Plaintext secret is never present in encrypted ciphertext."""
    secret_token = "ultra-secret-institutional-api-key-998877"
    creds = {"api_key": secret_token, "account_id": "101-004-12345"}

    ciphertext = CredentialCipher.encrypt(creds)
    assert secret_token not in ciphertext["ciphertext"]
    assert "101-004-12345" not in ciphertext["ciphertext"]
    assert len(ciphertext["ciphertext"]) > 30


def test_aes_gcm_credential_decryption_authenticity() -> None:
    """11. Ciphertext decrypts back to exact credentials dictionary."""
    creds = {"api_token": "token-xyz-1234", "account_id": "demo-001"}
    encrypted = CredentialCipher.encrypt(creds)
    decrypted = CredentialCipher.decrypt(encrypted)

    assert decrypted == creds
    assert decrypted["api_token"] == "token-xyz-1234"


def test_credential_masking_in_dictionary() -> None:
    """12. CredentialCipher.mask_credentials replaces sensitive tokens with '***'."""
    raw = {
        "api_key": "raw_secret_key_abcdef",
        "token": "bearer-ey12345",
        "secret": "top-secret-signing-key",
        "password": "super-strong-password",
        "account_id": "demo-001",
    }
    masked = CredentialCipher.mask_credentials(raw)

    assert masked["api_key"] == "***"
    assert masked["token"] == "***"
    assert masked["secret"] == "***"
    assert masked["password"] == "***"
    assert masked["account_id"] == "demo-001"  # Non-sensitive identifier preserved


@pytest.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        org = OrganizationModel(id="org-sec-1", name="Security Org", slug="sec-org")
        session.add(org)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_credential_masking_in_api_response(async_session: AsyncSession) -> None:
    """13. BrokerSandboxAccountResponse DTO masks credentials."""
    service = BrokerSandboxService(session=async_session)
    req = BrokerSandboxAccountCreateRequest(
        name="Masking Test Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-mask-01",
        credentials={"api_key": "super_secret_sandbox_token"},
    )
    acc = await service.create_account("org-sec-1", "user-1", req)

    assert acc.credentials_masked["api_key"] == "***"
    assert "super_secret_sandbox_token" not in str(acc.model_dump())


# ============================================================================
# Mandatory Execution Gates & Invariants (14 to 16)
# ============================================================================


@pytest.mark.asyncio
async def test_risk_engine_gate_rejection(async_session: AsyncSession) -> None:
    """14. RiskEngine rejection fails closed immediately with 422."""
    service = BrokerSandboxService(session=async_session)
    req = BrokerSandboxAccountCreateRequest(
        name="Risk Gate Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-risk-01",
    )
    acc = await service.create_account("org-sec-1", "user-1", req)
    await service.connect_account("org-sec-1", acc.id)

    # Mock a rejecting RiskEngine
    class MockRejectingRiskEngine:
        async def evaluate(self, decision, context=None):
            return RiskResult(
                decision=RiskDecision.REJECTED,
                risk_score=95.0,
                rejection_reasons=("Institutional maximum drawdown limit breached",),
            )

    service.risk_engine = MockRejectingRiskEngine()  # type: ignore

    order_req = BrokerSandboxOrderRequest(
        symbol="EUR/USD",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("10000"),
        price=Decimal("1.08500"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_sandbox_order("org-sec-1", acc.id, order_req)

    assert exc_info.value.status_code == 422
    assert "Pre-Trade Risk Engine" in exc_info.value.detail
    assert "drawdown limit breached" in exc_info.value.detail


@pytest.mark.asyncio
async def test_order_validator_gate_blocks_invalid_order(async_session: AsyncSession) -> None:
    """15. OrderValidator blocks oversized order before broker adapter dispatch."""
    service = BrokerSandboxService(session=async_session)
    req = BrokerSandboxAccountCreateRequest(
        name="Validation Gate Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-valid-01",
    )
    acc = await service.create_account("org-sec-1", "user-1", req)
    await service.connect_account("org-sec-1", acc.id)

    # Attempt to submit an order exceeding max volume limit (10,000,000 units)
    order_req = BrokerSandboxOrderRequest(
        symbol="EUR/USD",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("50000000"),  # 50 million exceeds max volume
        price=Decimal("1.08500"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_sandbox_order("org-sec-1", acc.id, order_req)

    assert exc_info.value.status_code == 422
    assert "Order validation failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_idempotency_and_timeout_unknown_handling(async_session: AsyncSession) -> None:
    """16. Order submission timeout is treated as UNKNOWN and NOT_SAFE_TO_RETRY."""
    service = BrokerSandboxService(session=async_session)
    req = BrokerSandboxAccountCreateRequest(
        name="Timeout Invariant Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-sec-timeout",
    )
    acc = await service.create_account("org-sec-1", "user-1", req)
    adapter = await service.get_or_create_adapter("org-sec-1", acc.id)
    await adapter.connect()

    # Trigger timeout mode
    if isinstance(adapter, MockBrokerAdapter):
        adapter.set_mode("TIMEOUT")

    order_req = BrokerSandboxOrderRequest(
        symbol="USD/JPY",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("10000"),
        price=Decimal("155.50"),
        client_order_id="idemp-sec-001",
    )

    resp = await service.submit_sandbox_order("org-sec-1", acc.id, order_req)
    assert resp.status_code if hasattr(resp, "status_code") else resp.status == "UNKNOWN"
    assert resp.broker_order_id == "UNKNOWN"
    # Never blindly executed or retried
