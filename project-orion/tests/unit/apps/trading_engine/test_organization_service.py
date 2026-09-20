"""Unit tests for OrganizationService and SQLAlchemyOrganizationRepository."""

from __future__ import annotations

import pytest
from apps.trading_engine.src.services.organization_service import (
    OrganizationService,
    slugify,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.organization.models import (
    MembershipStatus,
    OrganizationRole,
    OrganizationStatus,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.user import UserModel


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provide an isolated in-memory SQLite async database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Pre-seed test users
        user_1 = UserModel(
            id="usr_owner_001",
            username="owner_one",
            email="owner@alpha.dev",
            hashed_password="hashed_pw_1",
            is_active=True,
            is_superuser=False,
        )
        user_2 = UserModel(
            id="usr_trader_002",
            username="trader_two",
            email="trader@alpha.dev",
            hashed_password="hashed_pw_2",
            is_active=True,
            is_superuser=False,
        )
        user_3 = UserModel(
            id="usr_isolated_003",
            username="external_three",
            email="external@beta.dev",
            hashed_password="hashed_pw_3",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([user_1, user_2, user_3])
        await session.commit()
        yield session

    await engine.dispose()


class TestOrganizationService:
    """Test OrganizationService business logic and persistence."""

    def test_slugify_helper(self) -> None:
        assert slugify("Apex Alpha Capital") == "apex-alpha-capital"
        assert slugify("Quantum  Trading  Desk!") == "quantum-trading-desk"
        assert slugify("Global-Macro_100") == "global-macro_100"

    @pytest.mark.asyncio
    async def test_create_organization_success(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org = await service.create_organization(
            name="Apex Alpha Capital",
            slug="apex-alpha",
            meta_data={"tier": "BUSINESS"},
        )
        assert org.id.startswith("org_")
        assert org.name == "Apex Alpha Capital"
        assert org.slug == "apex-alpha"
        assert org.status == OrganizationStatus.ACTIVE
        assert org.meta_data["tier"] == "BUSINESS"

    @pytest.mark.asyncio
    async def test_create_organization_auto_slug(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org = await service.create_organization(name="Apex Trading Desk")
        assert org.slug == "apex-trading-desk"

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug_rejected(
        self, async_session: AsyncSession
    ) -> None:
        service = OrganizationService(session=async_session)
        await service.create_organization(name="Org One", slug="duplicate-slug")

        with pytest.raises(ValueError, match="already in use"):
            await service.create_organization(name="Org Two", slug="duplicate-slug")

    @pytest.mark.asyncio
    async def test_create_organization_blank_name_rejected(
        self, async_session: AsyncSession
    ) -> None:
        service = OrganizationService(session=async_session)
        with pytest.raises(ValueError, match="cannot be blank"):
            await service.create_organization(name="   ")

    @pytest.mark.asyncio
    async def test_get_organization(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        created = await service.create_organization(name="Searchable Fund", slug="searchable-fund")

        by_id = await service.get_organization(created.id)
        assert by_id is not None
        assert by_id.id == created.id
        assert by_id.name == "Searchable Fund"

        by_slug = await service.get_organization_by_slug("searchable-fund")
        assert by_slug is not None
        assert by_slug.id == created.id

        non_existent = await service.get_organization("org_non_existent")
        assert non_existent is None

    @pytest.mark.asyncio
    async def test_add_member_success(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org = await service.create_organization(name="Member Test Fund")

        member = await service.add_member(
            organization_id=org.id,
            user_id="usr_owner_001",
            role=OrganizationRole.OWNER,
        )
        assert member.id.startswith("mem_")
        assert member.organization_id == org.id
        assert member.user_id == "usr_owner_001"
        assert member.role == OrganizationRole.OWNER
        assert member.status == MembershipStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_add_member_duplicate_rejected(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org = await service.create_organization(name="Duplicate Member Fund")

        await service.add_member(
            organization_id=org.id,
            user_id="usr_trader_002",
            role=OrganizationRole.TRADER,
        )

        with pytest.raises(ValueError, match="already a member"):
            await service.add_member(
                organization_id=org.id,
                user_id="usr_trader_002",
                role=OrganizationRole.VIEWER,
            )

    @pytest.mark.asyncio
    async def test_add_member_nonexistent_org_rejected(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        with pytest.raises(ValueError, match="does not exist"):
            await service.add_member(
                organization_id="org_ghost",
                user_id="usr_trader_002",
                role=OrganizationRole.TRADER,
            )

    @pytest.mark.asyncio
    async def test_list_members_and_user_organizations(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org1 = await service.create_organization(name="Fund Alpha", slug="fund-alpha")
        org2 = await service.create_organization(name="Fund Beta", slug="fund-beta")

        await service.add_member(org1.id, "usr_owner_001", OrganizationRole.OWNER)
        await service.add_member(org1.id, "usr_trader_002", OrganizationRole.TRADER)
        await service.add_member(org2.id, "usr_owner_001", OrganizationRole.ADMINISTRATOR)

        # List members of org1
        members_org1 = await service.list_members(org1.id)
        assert len(members_org1) == 2
        user_ids = {m.user_id for m in members_org1}
        assert user_ids == {"usr_owner_001", "usr_trader_002"}

        # List user1 organizations
        user1_orgs = await service.list_user_organizations("usr_owner_001")
        assert len(user1_orgs) == 2
        org_slugs = {o.slug for o in user1_orgs}
        assert org_slugs == {"fund-alpha", "fund-beta"}

        # List user2 organizations
        user2_orgs = await service.list_user_organizations("usr_trader_002")
        assert len(user2_orgs) == 1
        assert user2_orgs[0].slug == "fund-alpha"

    @pytest.mark.asyncio
    async def test_update_member_role(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org = await service.create_organization(name="Role Update Desk")
        await service.add_member(org.id, "usr_trader_002", OrganizationRole.VIEWER)

        # Update role to TRADER
        updated = await service.update_member_role(
            organization_id=org.id,
            user_id="usr_trader_002",
            new_role=OrganizationRole.TRADER,
        )
        assert updated.role == OrganizationRole.TRADER

        # Verify updated in query
        member = await service.get_membership(org.id, "usr_trader_002")
        assert member is not None
        assert member.role == OrganizationRole.TRADER

    @pytest.mark.asyncio
    async def test_remove_member(self, async_session: AsyncSession) -> None:
        service = OrganizationService(session=async_session)
        org = await service.create_organization(name="Removal Desk")
        await service.add_member(org.id, "usr_trader_002", OrganizationRole.TRADER)

        removed = await service.remove_member(org.id, "usr_trader_002")
        assert removed is True

        member = await service.get_membership(org.id, "usr_trader_002")
        assert member is None

    @pytest.mark.asyncio
    async def test_membership_isolation(self, async_session: AsyncSession) -> None:
        """Verify strict membership boundaries between Organization A and B."""
        service = OrganizationService(session=async_session)
        org_a = await service.create_organization(name="Org A", slug="org-a")
        org_b = await service.create_organization(name="Org B", slug="org-b")

        await service.add_member(org_a.id, "usr_owner_001", OrganizationRole.OWNER)
        await service.add_member(org_b.id, "usr_isolated_003", OrganizationRole.OWNER)

        # User 1 is in Org A, but NOT in Org B
        assert await service.get_membership(org_a.id, "usr_owner_001") is not None
        assert await service.get_membership(org_b.id, "usr_owner_001") is None

        # User 3 is in Org B, but NOT in Org A
        assert await service.get_membership(org_b.id, "usr_isolated_003") is not None
        assert await service.get_membership(org_a.id, "usr_isolated_003") is None

    @pytest.mark.asyncio
    async def test_all_seven_roles_assignment(self, async_session: AsyncSession) -> None:
        """Verify that all 7 institutional roles can be assigned without error."""
        service = OrganizationService(session=async_session)
        org = await service.create_organization(name="Multi Role Desk")

        roles_to_test = [
            OrganizationRole.OWNER,
            OrganizationRole.ADMINISTRATOR,
            OrganizationRole.PORTFOLIO_MANAGER,
            OrganizationRole.RISK_OFFICER,
            OrganizationRole.TRADER,
            OrganizationRole.AUDITOR,
            OrganizationRole.VIEWER,
        ]

        for role in roles_to_test:
            # Create a dedicated test user for each role
            user = UserModel(
                id=f"usr_role_{role.value.lower()}",
                username=f"user_{role.value.lower()}",
                email=f"{role.value.lower()}@multirole.dev",
                hashed_password="pw",
                is_active=True,
                is_superuser=False,
            )
            async_session.add(user)
            await async_session.commit()

            mem = await service.add_member(org.id, user.id, role)
            assert mem.role == role
