"""Unit tests for Organization and Member domain entities and value objects."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.organization.models import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    OrganizationStatus,
)


class TestOrganizationDomainModel:
    """Test Organization domain entity behavior and validation."""

    def test_organization_creation_valid(self) -> None:
        now = datetime.now(timezone.utc)
        org = Organization(
            id="org_1234567890abcdef",
            name="Apex Alpha Capital",
            slug="apex-alpha-capital",
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            meta_data={"jurisdiction": "US"},
        )
        assert org.id == "org_1234567890abcdef"
        assert org.name == "Apex Alpha Capital"
        assert org.slug == "apex-alpha-capital"
        assert org.status == OrganizationStatus.ACTIVE
        assert org.is_active is True
        assert org.meta_data["jurisdiction"] == "US"

    def test_organization_validation_empty_id(self) -> None:
        with pytest.raises(ValueError, match="Organization id must not be empty"):
            Organization(id="", name="Valid Name", slug="valid-slug")

    def test_organization_validation_empty_name(self) -> None:
        with pytest.raises(ValueError, match="Organization name must not be empty"):
            Organization(id="org_123", name="   ", slug="valid-slug")

    def test_organization_validation_empty_slug(self) -> None:
        with pytest.raises(ValueError, match="Organization slug must not be empty"):
            Organization(id="org_123", name="Valid Name", slug="")

    def test_organization_status_suspended(self) -> None:
        org = Organization(
            id="org_123",
            name="Suspended Desk",
            slug="suspended-desk",
            status=OrganizationStatus.SUSPENDED,
        )
        assert org.is_active is False
        assert org.status == OrganizationStatus.SUSPENDED

    def test_organization_immutability(self) -> None:
        org = Organization(id="org_123", name="Immutable Org", slug="immutable-org")
        field_to_mutate = "name"
        with pytest.raises((AttributeError, TypeError)):
            setattr(org, field_to_mutate, "Mutated Org")


class TestOrganizationRole:
    """Test the seven institutional roles defined in EPIC-016/EPIC-017."""

    def test_seven_roles_exist(self) -> None:
        expected_roles = {
            "OWNER",
            "ADMINISTRATOR",
            "PORTFOLIO_MANAGER",
            "RISK_OFFICER",
            "TRADER",
            "AUDITOR",
            "VIEWER",
        }
        actual_roles = {r.value for r in OrganizationRole}
        assert actual_roles == expected_roles
        assert len(OrganizationRole) == 7

    def test_role_from_str_variations(self) -> None:
        assert OrganizationRole.from_str("owner") == OrganizationRole.OWNER
        assert OrganizationRole.from_str("Portfolio Manager") == OrganizationRole.PORTFOLIO_MANAGER
        assert OrganizationRole.from_str("risk_officER") == OrganizationRole.RISK_OFFICER
        assert OrganizationRole.from_str("TRADER") == OrganizationRole.TRADER
        assert OrganizationRole.from_str("  Auditor  ") == OrganizationRole.AUDITOR
        assert OrganizationRole.from_str("viewer") == OrganizationRole.VIEWER
        assert OrganizationRole.from_str("administrator") == OrganizationRole.ADMINISTRATOR

    def test_role_from_str_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid organization role 'SUPERUSER'"):
            OrganizationRole.from_str("SUPERUSER")


class TestOrganizationMemberDomainModel:
    """Test OrganizationMember domain entity behavior."""

    def test_member_creation_valid(self) -> None:
        now = datetime.now(timezone.utc)
        member = OrganizationMember(
            id="mem_1234567890abcdef",
            organization_id="org_test_001",
            user_id="usr_trader_001",
            role=OrganizationRole.TRADER,
            status=MembershipStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        assert member.id == "mem_1234567890abcdef"
        assert member.organization_id == "org_test_001"
        assert member.user_id == "usr_trader_001"
        assert member.role == OrganizationRole.TRADER
        assert member.status == MembershipStatus.ACTIVE
        assert member.is_active is True

    def test_member_validation_empty_fields(self) -> None:
        with pytest.raises(ValueError, match="Membership id must not be empty"):
            OrganizationMember(
                id="",
                organization_id="org_1",
                user_id="usr_1",
                role=OrganizationRole.VIEWER,
            )

        with pytest.raises(ValueError, match="Organization id must not be empty"):
            OrganizationMember(
                id="mem_1",
                organization_id="",
                user_id="usr_1",
                role=OrganizationRole.VIEWER,
            )

        with pytest.raises(ValueError, match="User id must not be empty"):
            OrganizationMember(
                id="mem_1",
                organization_id="org_1",
                user_id="",
                role=OrganizationRole.VIEWER,
            )

    def test_member_status_lifecycle(self) -> None:
        assert MembershipStatus.ACTIVE.value == "ACTIVE"
        assert MembershipStatus.SUSPENDED.value == "SUSPENDED"
        assert MembershipStatus.INVITED.value == "INVITED"

    def test_member_immutability(self) -> None:
        member = OrganizationMember(
            id="mem_1",
            organization_id="org_1",
            user_id="usr_1",
            role=OrganizationRole.VIEWER,
        )
        field_to_mutate = "role"
        with pytest.raises((AttributeError, TypeError)):
            setattr(member, field_to_mutate, OrganizationRole.OWNER)
