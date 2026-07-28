"""Tests for version_manager module."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import VersionError
from libraries.domain.ai_research.version_manager import VersionManager


class TestVersionManager:
    def test_create_version(self):
        vm = VersionManager()
        import asyncio

        record = asyncio.run(
            vm.create_version(
                entity_type="experiment",
                entity_id="exp-1",
                version="1.0.0",
            )
        )
        assert record.entity_type == "experiment"
        assert record.entity_id == "exp-1"
        assert record.version == "1.0.0"

    def test_create_version_with_previous(self):
        vm = VersionManager()
        import asyncio

        asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))
        record = asyncio.run(
            vm.create_version("experiment", "exp-1", "1.1.0", previous_version="1.0.0")
        )
        assert record.previous_version == "1.0.0"

    def test_create_duplicate_version_raises_error(self):
        vm = VersionManager()
        import asyncio

        asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))
        with pytest.raises(VersionError, match="already exists"):
            asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))

    def test_create_invalid_entity_type(self):
        vm = VersionManager()
        import asyncio

        with pytest.raises(VersionError, match="unsupported entity type"):
            asyncio.run(vm.create_version("invalid", "x", "1.0.0"))

    def test_get_version(self):
        vm = VersionManager()
        import asyncio

        asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))
        record = asyncio.run(vm.get_version("experiment", "exp-1", "1.0.0"))
        assert record is not None

    def test_get_version_nonexistent(self):
        vm = VersionManager()
        import asyncio

        record = asyncio.run(vm.get_version("experiment", "exp-1", "1.0.0"))
        assert record is None

    def test_list_versions(self):
        vm = VersionManager()
        import asyncio

        asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))
        asyncio.run(vm.create_version("experiment", "exp-1", "1.1.0"))
        asyncio.run(vm.create_version("experiment", "exp-1", "1.2.0"))
        versions = asyncio.run(vm.list_versions("experiment", "exp-1"))
        assert len(versions) == 3

    def test_list_versions_empty(self):
        vm = VersionManager()
        import asyncio

        versions = asyncio.run(vm.list_versions("experiment", "exp-1"))
        assert versions == ()

    def test_get_latest_version(self):
        vm = VersionManager()
        import asyncio

        asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))
        asyncio.run(vm.create_version("experiment", "exp-1", "2.0.0"))
        latest = asyncio.run(vm.get_latest_version("experiment", "exp-1"))
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_get_latest_version_nonexistent(self):
        vm = VersionManager()
        import asyncio

        latest = asyncio.run(vm.get_latest_version("experiment", "exp-1"))
        assert latest is None

    def test_get_stats(self):
        vm = VersionManager()
        import asyncio

        asyncio.run(vm.create_version("experiment", "exp-1", "1.0.0"))
        asyncio.run(vm.create_version("experiment", "exp-1", "1.1.0"))
        asyncio.run(vm.create_version("dataset", "ds-1", "1.0.0"))
        stats = asyncio.run(vm.get_stats())
        assert stats["total_versions"] == 3
        assert stats["total_entities"] == 2

    def test_version_for_dataset(self):
        vm = VersionManager()
        import asyncio

        record = asyncio.run(vm.create_version("dataset", "ds-1", "1.0.0"))
        assert record.entity_type == "dataset"

    def test_version_for_strategy(self):
        vm = VersionManager()
        import asyncio

        record = asyncio.run(vm.create_version("strategy", "s-1", "1.0.0"))
        assert record.entity_type == "strategy"

    def test_version_for_config(self):
        vm = VersionManager()
        import asyncio

        record = asyncio.run(vm.create_version("config", "cfg-1", "1.0.0"))
        assert record.entity_type == "config"

    def test_version_with_metadata(self):
        vm = VersionManager()
        import asyncio

        record = asyncio.run(
            vm.create_version(
                "experiment",
                "exp-1",
                "1.0.0",
                metadata={"author": "test", "description": "initial"},
            )
        )
        assert record.metadata["author"] == "test"
