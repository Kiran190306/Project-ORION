"""Integration tests for EPIC-017 Phase 4: Cryptographic Member Invitations.

Verifies:
1. Cryptographic invitation issuance (SHA-256 hashing, unexposed raw tokens).
2. Successful single-use acceptance granting institutional role and organization membership.
3. Rejection of already-accepted tokens (single-use invariant).
4. Rejection of expired tokens (HTTP 410 Gone and status transition to EXPIRED).
5. Rejection of invalid / forged tokens (HTTP 400 Bad Request).
6. Invitation revocation workflow and rejection of revoked tokens.
7. Cross-tenant isolation (Org A cannot view or revoke Org B invitations).
8. Role escalation control: Only an Owner can invite another user as OWNER.
"""

from __future__ import annotations

import hashlib
import pathlib
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import create_access_token, get_password_hash
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    AuditLogModel,
    OrganizationInvitationModel,
    OrganizationMemberModel,
    OrganizationModel,
    UserModel,
)


@pytest.fixture
async def invitation_env():
    """Set up an isolated database with 2 organizations and users for invitation testing."""
    db_file = f"test_inv_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_a_id = "org_alpha_fund"
    org_b_id = "org_beta_fund"

    user_owner_a = "usr_owner_a"
    user_admin_a = "usr_admin_a"
    user_owner_b = "usr_owner_b"
    user_invitee = "usr_invitee_clean"

    async with db_manager.session() as session:
        # Organizations
        org_a = OrganizationModel(id=org_a_id, name="Alpha Fund", slug="alpha-fund", status="ACTIVE", meta_data={})
        org_b = OrganizationModel(id=org_b_id, name="Beta Fund", slug="beta-fund", status="ACTIVE", meta_data={})
        session.add_all([org_a, org_b])

        # Users
        u_owner_a = UserModel(id=user_owner_a, username="owner_a", email="owner@alpha.dev", hashed_password=get_password_hash("Pass123!"), is_active=True, is_superuser=False)
        u_admin_a = UserModel(id=user_admin_a, username="admin_a", email="admin@alpha.dev", hashed_password=get_password_hash("Pass123!"), is_active=True, is_superuser=False)
        u_owner_b = UserModel(id=user_owner_b, username="owner_b", email="owner@beta.dev", hashed_password=get_password_hash("Pass123!"), is_active=True, is_superuser=False)
        u_invitee = UserModel(id=user_invitee, username="invitee_user", email="invitee@external.dev", hashed_password=get_password_hash("Pass123!"), is_active=True, is_superuser=False)
        session.add_all([u_owner_a, u_admin_a, u_owner_b, u_invitee])

        # Memberships
        m_owner_a = OrganizationMemberModel(id="mem_owner_a", organization_id=org_a_id, user_id=user_owner_a, role="OWNER", status="ACTIVE", meta_data={})
        m_admin_a = OrganizationMemberModel(id="mem_admin_a", organization_id=org_a_id, user_id=user_admin_a, role="ADMINISTRATOR", status="ACTIVE", meta_data={})
        m_owner_b = OrganizationMemberModel(id="mem_owner_b", organization_id=org_b_id, user_id=user_owner_b, role="OWNER", status="ACTIVE", meta_data={})
        session.add_all([m_owner_a, m_admin_a, m_owner_b])

        await session.commit()

    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url=db_url,
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal("100000.00"),
        worker_enabled=False,
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = True

    adapter_config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal("100000.00"),
    )
    paper_adapter = PaperExecutionAdapter(config=adapter_config)

    app = create_app(
        settings=settings,
        db_manager=db_manager,
        redis_client=mock_redis,
        paper_adapter=paper_adapter,
    )

    token_owner_a = create_access_token({"sub": user_owner_a, "username": "owner_a"})
    token_admin_a = create_access_token({"sub": user_admin_a, "username": "admin_a"})
    token_owner_b = create_access_token({"sub": user_owner_b, "username": "owner_b"})
    token_invitee = create_access_token({"sub": user_invitee, "username": "invitee_user"})

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield {
            "client": client,
            "db_manager": db_manager,
            "org_a_id": org_a_id,
            "org_b_id": org_b_id,
            "token_owner_a": token_owner_a,
            "token_admin_a": token_admin_a,
            "token_owner_b": token_owner_b,
            "token_invitee": token_invitee,
            "user_invitee": user_invitee,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_invitation_issuance_and_acceptance(invitation_env: dict):
    """Owner creates an invitation; invitee accepts; membership and audit trail are established."""
    client: AsyncClient = invitation_env["client"]
    db_manager: DatabaseManager = invitation_env["db_manager"]
    org_a_id: str = invitation_env["org_a_id"]
    token_owner_a: str = invitation_env["token_owner_a"]
    token_invitee: str = invitation_env["token_invitee"]
    user_invitee: str = invitation_env["user_invitee"]

    headers_owner = {
        "Authorization": f"Bearer {token_owner_a}",
        "X-Organization-ID": org_a_id,
    }

    # 1. Issue Invitation
    invite_resp = await client.post(
        f"/api/v1/organizations/{org_a_id}/members/invite",
        headers=headers_owner,
        json={
            "email": "invitee@external.dev",
            "role": "TRADER",
        },
    )
    assert invite_resp.status_code == 201, invite_resp.text
    inv_data = invite_resp.json()

    assert inv_data["email"] == "invitee@external.dev"
    assert inv_data["role"] == "TRADER"
    assert inv_data["status"] == "PENDING"
    raw_token = inv_data["invitation_token"]
    assert len(raw_token) > 30

    # Verify SHA-256 hash in database
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    async with db_manager.session() as session:
        inv_model = (await session.execute(
            select(OrganizationInvitationModel).where(
                OrganizationInvitationModel.token_hash == expected_hash
            )
        )).scalar_one()
        assert inv_model.status == "PENDING"
        assert inv_model.role == "TRADER"

    # 2. Invitee Accepts Invitation
    headers_invitee = {
        "Authorization": f"Bearer {token_invitee}",
    }
    accept_resp = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers=headers_invitee,
    )
    assert accept_resp.status_code == 200, accept_resp.text
    accept_data = accept_resp.json()

    assert accept_data["organization_id"] == org_a_id
    assert accept_data["user_id"] == user_invitee
    assert accept_data["role"] == "TRADER"
    assert accept_data["status"] == "ACTIVE"

    # Verify database state after acceptance
    async with db_manager.session() as session:
        # Invitation marked ACCEPTED
        updated_inv = (await session.execute(
            select(OrganizationInvitationModel).where(
                OrganizationInvitationModel.token_hash == expected_hash
            )
        )).scalar_one()
        assert updated_inv.status == "ACCEPTED"
        assert updated_inv.accepted_at is not None

        # Membership exists
        member = (await session.execute(
            select(OrganizationMemberModel).where(
                OrganizationMemberModel.organization_id == org_a_id,
                OrganizationMemberModel.user_id == user_invitee,
            )
        )).scalar_one()
        assert member.role == "TRADER"
        assert member.status == "ACTIVE"

        # Audit log exists
        audit = (await session.execute(
            select(AuditLogModel).where(
                AuditLogModel.organization_id == org_a_id,
                AuditLogModel.event_type == "invitation.accepted",
            )
        )).scalar_one()
        assert audit.actor == user_invitee


@pytest.mark.asyncio
async def test_single_use_invitation_enforcement(invitation_env: dict):
    """An invitation token can only be accepted once; subsequent attempts must fail."""
    client: AsyncClient = invitation_env["client"]
    org_a_id: str = invitation_env["org_a_id"]
    token_owner_a: str = invitation_env["token_owner_a"]
    token_invitee: str = invitation_env["token_invitee"]

    headers_owner = {
        "Authorization": f"Bearer {token_owner_a}",
        "X-Organization-ID": org_a_id,
    }

    # Issue
    r1 = await client.post(
        f"/api/v1/organizations/{org_a_id}/members/invite",
        headers=headers_owner,
        json={"email": "singleuse@test.com", "role": "VIEWER"},
    )
    token = r1.json()["invitation_token"]

    # First acceptance succeeds
    headers_invitee = {"Authorization": f"Bearer {token_invitee}"}
    r2 = await client.post(f"/api/v1/invitations/{token}/accept", headers=headers_invitee)
    assert r2.status_code == 200

    # Second acceptance fails
    r3 = await client.post(f"/api/v1/invitations/{token}/accept", headers=headers_invitee)
    assert r3.status_code == 400
    err = (r3.json().get("message") or r3.json().get("detail", "")).lower()
    assert "already" in err


@pytest.mark.asyncio
async def test_expired_invitation_rejection(invitation_env: dict):
    """An expired token must return HTTP 410 Gone and update status to EXPIRED."""
    client: AsyncClient = invitation_env["client"]
    db_manager: DatabaseManager = invitation_env["db_manager"]
    org_a_id: str = invitation_env["org_a_id"]
    token_owner_a: str = invitation_env["token_owner_a"]
    token_invitee: str = invitation_env["token_invitee"]

    headers_owner = {
        "Authorization": f"Bearer {token_owner_a}",
        "X-Organization-ID": org_a_id,
    }

    # Issue
    r1 = await client.post(
        f"/api/v1/organizations/{org_a_id}/members/invite",
        headers=headers_owner,
        json={"email": "expired@test.com", "role": "AUDITOR"},
    )
    raw_token = r1.json()["invitation_token"]
    inv_id = r1.json()["id"]

    # Force expiration date to the past in database
    async with db_manager.session() as session:
        inv = (await session.execute(
            select(OrganizationInvitationModel).where(OrganizationInvitationModel.id == inv_id)
        )).scalar_one()
        inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await session.commit()

    # Attempt acceptance
    headers_invitee = {"Authorization": f"Bearer {token_invitee}"}
    r2 = await client.post(f"/api/v1/invitations/{raw_token}/accept", headers=headers_invitee)
    assert r2.status_code == 410
    err = (r2.json().get("message") or r2.json().get("detail", "")).lower()
    assert "expired" in err

    # Confirm status transitioned to EXPIRED in database
    async with db_manager.session() as session:
        inv = (await session.execute(
            select(OrganizationInvitationModel).where(OrganizationInvitationModel.id == inv_id)
        )).scalar_one()
        assert inv.status == "EXPIRED"


@pytest.mark.asyncio
async def test_invalid_token_rejection(invitation_env: dict):
    """Submitting a forged or non-existent token returns HTTP 400 Bad Request."""
    client: AsyncClient = invitation_env["client"]
    token_invitee: str = invitation_env["token_invitee"]

    headers = {"Authorization": f"Bearer {token_invitee}"}
    resp = await client.post("/api/v1/invitations/completely_invalid_token_12345/accept", headers=headers)
    assert resp.status_code == 400
    err = (resp.json().get("message") or resp.json().get("detail", "")).lower()
    assert "invalid" in err


@pytest.mark.asyncio
async def test_invitation_revocation(invitation_env: dict):
    """Owner can revoke a pending invitation; acceptance of a revoked token fails."""
    client: AsyncClient = invitation_env["client"]
    org_a_id: str = invitation_env["org_a_id"]
    token_owner_a: str = invitation_env["token_owner_a"]
    token_invitee: str = invitation_env["token_invitee"]

    headers_owner = {
        "Authorization": f"Bearer {token_owner_a}",
        "X-Organization-ID": org_a_id,
    }

    # Issue
    r1 = await client.post(
        f"/api/v1/organizations/{org_a_id}/members/invite",
        headers=headers_owner,
        json={"email": "revokeme@test.com", "role": "TRADER"},
    )
    inv_id = r1.json()["id"]
    raw_token = r1.json()["invitation_token"]

    # Revoke
    rev_resp = await client.delete(
        f"/api/v1/organizations/{org_a_id}/invitations/{inv_id}",
        headers=headers_owner,
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "revoked"

    # Attempt acceptance of revoked token
    headers_invitee = {"Authorization": f"Bearer {token_invitee}"}
    accept_resp = await client.post(f"/api/v1/invitations/{raw_token}/accept", headers=headers_invitee)
    assert accept_resp.status_code == 400
    err = (accept_resp.json().get("message") or accept_resp.json().get("detail", "")).lower()
    assert "revoked" in err


@pytest.mark.asyncio
async def test_cross_tenant_invitation_isolation(invitation_env: dict):
    """User in Org B cannot list or revoke invitations belonging to Org A."""
    client: AsyncClient = invitation_env["client"]
    org_a_id: str = invitation_env["org_a_id"]
    org_b_id: str = invitation_env["org_b_id"]
    token_owner_a: str = invitation_env["token_owner_a"]
    token_owner_b: str = invitation_env["token_owner_b"]

    headers_owner_a = {
        "Authorization": f"Bearer {token_owner_a}",
        "X-Organization-ID": org_a_id,
    }
    # Create invitation in Org A
    r1 = await client.post(
        f"/api/v1/organizations/{org_a_id}/members/invite",
        headers=headers_owner_a,
        json={"email": "alpha_internal@test.com", "role": "VIEWER"},
    )
    inv_id = r1.json()["id"]

    # Org B owner attempts to list Org A invitations with Org B header -> 403 Cross-tenant
    headers_owner_b_spoof = {
        "Authorization": f"Bearer {token_owner_b}",
        "X-Organization-ID": org_b_id,
    }
    r2 = await client.get(f"/api/v1/organizations/{org_a_id}/invitations", headers=headers_owner_b_spoof)
    assert r2.status_code == 403

    # Org B owner attempts to delete Org A invitation -> 403
    r3 = await client.delete(
        f"/api/v1/organizations/{org_a_id}/invitations/{inv_id}",
        headers=headers_owner_b_spoof,
    )
    assert r3.status_code == 403


@pytest.mark.asyncio
async def test_only_owner_can_invite_owner(invitation_env: dict):
    """An ADMINISTRATOR has MEMBER_INVITE permission, but cannot assign the OWNER role."""
    client: AsyncClient = invitation_env["client"]
    org_a_id: str = invitation_env["org_a_id"]
    token_admin_a: str = invitation_env["token_admin_a"]

    headers_admin = {
        "Authorization": f"Bearer {token_admin_a}",
        "X-Organization-ID": org_a_id,
    }

    # Administrator attempts to invite another OWNER
    resp = await client.post(
        f"/api/v1/organizations/{org_a_id}/members/invite",
        headers=headers_admin,
        json={"email": "newowner@test.com", "role": "OWNER"},
    )
    assert resp.status_code == 400
    err = (resp.json().get("message") or resp.json().get("detail", "")).lower()
    assert "only an owner can invite another owner" in err
