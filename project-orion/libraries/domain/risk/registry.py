"""Risk Policy Registry - central registry for risk policy discovery.

Supports:
- register() with duplicate and capacity protection
- unregister() by policy name
- get() by policy name
- list() with optional category/severity/enabled filtering
- count() of registered policies
- Policy chaining ordering by priority then severity
"""

from __future__ import annotations

import asyncio
from typing import Any

from libraries.domain.risk.exceptions import (
    PolicyNotFoundError,
    PolicyRegistrationError,
    RegistryError,
    RegistryFullError,
)
from libraries.domain.risk.interfaces import RiskPolicy
from libraries.domain.risk.models import PolicyCategory, PolicySeverity


class RiskPolicyRegistry:
    """Central registry for risk policies.

    Thread-safe via asyncio.Lock. Supports dynamic policy registration,
    lookup, and filtering.
    """

    MAX_POLICIES: int = 100

    def __init__(self, max_policies: int | None = None) -> None:
        self._policies: dict[str, RiskPolicy] = {}
        self._max_policies = max_policies or self.MAX_POLICIES
        self._lock = asyncio.Lock()

    @property
    def max_policies(self) -> int:
        return self._max_policies

    async def register(self, policy: RiskPolicy) -> None:
        """Register a risk policy.

        Args:
            policy: RiskPolicy instance to register.

        Raises:
            PolicyRegistrationError: If a policy with the same name
                already exists.
            RegistryFullError: If the registry capacity is exhausted.
        """
        async with self._lock:
            if policy.name in self._policies:
                raise PolicyRegistrationError(
                    f"Policy '{policy.name}' is already registered"
                )

            if len(self._policies) >= self._max_policies:
                raise RegistryFullError(
                    f"Registry capacity ({self._max_policies}) exhausted; "
                    f"cannot register '{policy.name}'"
                )

            # Validate policy has required attributes
            if not policy.name.strip():
                raise PolicyRegistrationError("Policy name cannot be empty")
            if policy.priority < 0:
                raise PolicyRegistrationError(
                    f"Policy '{policy.name}' has negative priority"
                )

            self._policies[policy.name] = policy

    async def unregister(self, policy_name: str) -> None:
        """Unregister a policy by name.

        Args:
            policy_name: Name of the policy to remove.

        Raises:
            PolicyNotFoundError: If the policy is not found.
        """
        async with self._lock:
            policy = self._policies.pop(policy_name, None)
            if policy is None:
                raise PolicyNotFoundError(f"Policy '{policy_name}' not found")

    async def get(self, policy_name: str) -> RiskPolicy:
        """Get a policy by name.

        Args:
            policy_name: Policy name to look up.

        Returns:
            The registered policy.

        Raises:
            PolicyNotFoundError: If not found.
        """
        async with self._lock:
            policy = self._policies.get(policy_name)
            if policy is None:
                raise PolicyNotFoundError(f"Policy '{policy_name}' not found")
            return policy

    async def list(
        self,
        category: PolicyCategory | None = None,
        severity: PolicySeverity | None = None,
        enabled_only: bool | None = None,
    ) -> list[RiskPolicy]:
        """List registered policies, optionally filtered.

        Results are ordered by priority (ascending) then severity
        (descending) for proper policy chaining.

        Args:
            category: Filter by policy category.
            severity: Filter by minimum severity.
            enabled_only: If True, only return enabled policies.

        Returns:
            Ordered list of matching policies.
        """
        async with self._lock:
            policies = list(self._policies.values())

        # Apply filters
        if category is not None:
            policies = [p for p in policies if p.category == category]

        if severity is not None:
            policies = [p for p in policies if p.severity >= severity]

        if enabled_only is True:
            policies = [p for p in policies if p.enabled]
        elif enabled_only is False:
            policies = [p for p in policies if not p.enabled]

        # Sort by priority ascending, then severity descending
        policies.sort(key=lambda p: (p.priority, -p.severity.value))

        return policies

    async def list_enabled(self) -> list[RiskPolicy]:
        """Convenience: return all enabled policies in execution order."""
        return await self.list(enabled_only=True)

    async def list_by_category(self, category: PolicyCategory) -> list[RiskPolicy]:
        """Convenience: return all policies in a category."""
        return await self.list(category=category)

    async def contains(self, policy_name: str) -> bool:
        """Check if a policy name is registered.

        Args:
            policy_name: Policy name to check.

        Returns:
            True if registered.
        """
        async with self._lock:
            return policy_name in self._policies

    async def count(self) -> int:
        """Return the number of registered policies."""
        async with self._lock:
            return len(self._policies)

    async def enabled_count(self) -> int:
        """Return the number of enabled policies."""
        async with self._lock:
            return sum(1 for p in self._policies.values() if p.enabled)

    async def disabled_count(self) -> int:
        """Return the number of disabled policies."""
        async with self._lock:
            return sum(1 for p in self._policies.values() if not p.enabled)

    async def get_all(self) -> list[RiskPolicy]:
        """Return all registered policies (unordered)."""
        async with self._lock:
            return list(self._policies.values())

    async def clear(self) -> None:
        """Unregister all policies."""
        async with self._lock:
            self._policies.clear()

    async def get_policy_names(self) -> list[str]:
        """Return names of all registered policies."""
        async with self._lock:
            return list(self._policies.keys())

    async def get_categories(self) -> list[PolicyCategory]:
        """Return distinct categories of registered policies."""
        async with self._lock:
            categories: set[PolicyCategory] = {p.category for p in self._policies.values()}
            return sorted(categories, key=lambda c: c.value)

