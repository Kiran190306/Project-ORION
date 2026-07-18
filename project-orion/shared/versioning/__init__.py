"""
Project ORION - Versioning

Semantic versioning and version management utilities for the platform.
Supports API versioning, schema versioning, and entity versioning.

Architecture follows semver.org specification (2.0.0).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# ─── Version Class ────────────────────────────────────────────


@dataclass(frozen=True)
class Version:
    """
    Semantic version following semver 2.0.0.

    Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    """

    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    _VERSION_PATTERN = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __post_init__(self) -> None:
        if self.major < 0:
            raise ValueError(f"Major version must be >= 0, got {self.major}")
        if self.minor < 0:
            raise ValueError(f"Minor version must be >= 0, got {self.minor}")
        if self.patch < 0:
            raise ValueError(f"Patch version must be >= 0, got {self.patch}")

    @classmethod
    def parse(cls, version_str: str) -> Version:
        """Parse a version string into a Version object."""
        match = cls._VERSION_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"Invalid semantic version string: {version_str}")

        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4) or "",
            build=match.group(5) or "",
        )

    @classmethod
    def create(
        cls,
        major: int = 0,
        minor: int = 1,
        patch: int = 0,
        prerelease: str = "",
        build: str = "",
    ) -> Version:
        """Create a new version."""
        return cls(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            build=build,
        )

    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.build:
            result += f"+{self.build}"
        return result

    def __repr__(self) -> str:
        return f"Version('{self}')"

    def __lt__(self, other: Version) -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch

        # Pre-release versions have lower precedence
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease

        return False

    def __le__(self, other: Version) -> bool:
        return self < other or self == other

    def __gt__(self, other: Version) -> bool:
        return not (self <= other)

    def __ge__(self, other: Version) -> bool:
        return not (self < other)

    @property
    def is_release(self) -> bool:
        """Check if this is a release version (no prerelease)."""
        return not self.prerelease

    @property
    def is_prerelease(self) -> bool:
        """Check if this is a pre-release version."""
        return bool(self.prerelease)

    def bump_major(self) -> Version:
        """Bump major version (breaking changes)."""
        return Version(
            major=self.major + 1,
            minor=0,
            patch=0,
        )

    def bump_minor(self) -> Version:
        """Bump minor version (new features, backward compatible)."""
        return Version(
            major=self.major,
            minor=self.minor + 1,
            patch=0,
        )

    def bump_patch(self) -> Version:
        """Bump patch version (bug fixes, backward compatible)."""
        return Version(
            major=self.major,
            minor=self.minor,
            patch=self.patch + 1,
        )

    def to_dict(self) -> dict[str, str | int]:
        """Serialize to dictionary."""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": self.prerelease,
            "build": self.build,
            "string": str(self),
        }


# ─── Version Range ────────────────────────────────────────────


@dataclass(frozen=True)
class VersionRange:
    """A range of versions (min inclusive, max exclusive)."""

    min_version: Version
    max_version: Version

    def __post_init__(self) -> None:
        if self.min_version >= self.max_version:
            raise ValueError(
                f"min_version ({self.min_version}) must be "
                f"less than max_version ({self.max_version})"
            )

    def contains(self, version: Version) -> bool:
        """Check if a version is within this range."""
        return self.min_version <= version < self.max_version

    def to_dict(self) -> dict[str, str]:
        return {
            "min": str(self.min_version),
            "max": str(self.max_version),
        }


# ─── Common Versions ──────────────────────────────────────────

VERSION_1_0_0 = Version(1, 0, 0)
VERSION_1_1_0 = Version(1, 1, 0)
VERSION_2_0_0 = Version(2, 0, 0)

API_CURRENT_VERSION = Version(1, 0, 0)
API_MINIMUM_VERSION = Version(1, 0, 0)
API_LATEST_VERSION = Version(1, 0, 0)


# ─── Version Compatibility ────────────────────────────────────


def is_compatible(
    requested_version: Version,
    supported_versions: list[Version],
    min_version: Optional[Version] = None,
) -> bool:
    """
    Check if a requested version is compatible with supported versions.

    Args:
        requested_version: The version being requested.
        supported_versions: List of currently supported versions.
        min_version: Minimum acceptable version (optional).

    Returns:
        True if compatible, False otherwise.
    """
    if min_version is not None and requested_version < min_version:
        return False

    for supported in supported_versions:
        if requested_version.major == supported.major:
            return True

    return False


def format_version(version: Version) -> str:
    """Format a version for API headers and responses."""
    return str(version)
