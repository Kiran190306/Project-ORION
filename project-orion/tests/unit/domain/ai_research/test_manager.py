"""Tests for EPIC-011 AI Research manager lifecycle."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.engine import AIResearchEngine
from libraries.domain.ai_research.exceptions import AIResearchError, ConfigurationError
from libraries.domain.ai_research.manager import AIResearchManager
from libraries.domain.ai_research.models import PlatformState, ResearchPlatformConfig


class TestAIResearchManagerInitialization:
    """Test manager initialization."""

    def test_default_init(self):
        mgr = AIResearchManager()
        assert isinstance(mgr.config, ResearchPlatformConfig)
        assert mgr.engine is None
        assert mgr.state == PlatformState.INITIALIZING

    def test_init_with_config(self):
        cfg = ResearchPlatformConfig(name="test-platform", random_seed=99)
        mgr = AIResearchManager(config=cfg)
        assert mgr.config.random_seed == 99
        assert mgr.config.name == "test-platform"

    def test_init_with_engine(self):
        engine = AIResearchEngine()
        mgr = AIResearchManager(engine=engine)
        assert mgr.engine is engine

    def test_config_property(self):
        mgr = AIResearchManager()
        assert mgr.config is mgr._config

    def test_engine_property(self):
        engine = AIResearchEngine()
        mgr = AIResearchManager(engine=engine)
        assert mgr.engine is engine

    def test_state_property(self):
        mgr = AIResearchManager()
        assert mgr.state == PlatformState.INITIALIZING


class TestAIResearchManagerLifecycle:
    """Test manager lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize_sets_ready(self):
        mgr = AIResearchManager()
        assert mgr.state == PlatformState.INITIALIZING
        await mgr.initialize()
        assert mgr.state == PlatformState.READY

    @pytest.mark.asyncio
    async def test_initialize_twice_raises_error(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        with pytest.raises(AIResearchError, match="Cannot initialize"):
            await mgr.initialize()

    @pytest.mark.asyncio
    async def test_shutdown_sets_shutdown(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        await mgr.shutdown()
        assert mgr.state == PlatformState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_shutdown_twice_raises_error(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        await mgr.shutdown()
        with pytest.raises(AIResearchError, match="Already shut down"):
            await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_clears_engine(self):
        mgr = AIResearchManager(engine=AIResearchEngine())
        await mgr.initialize()
        await mgr.shutdown()
        assert mgr.engine is None

    @pytest.mark.asyncio
    async def test_reset_returns_to_initializing(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        await mgr.reset()
        assert mgr.state == PlatformState.INITIALIZING

    @pytest.mark.asyncio
    async def test_reset_clears_start_time(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        await mgr.reset()
        health = await mgr.health_check()
        assert health["uptime_seconds"] is None

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        mgr = AIResearchManager(engine=AIResearchEngine())
        assert mgr.state == PlatformState.INITIALIZING
        await mgr.initialize()
        assert mgr.state == PlatformState.READY
        health = await mgr.health_check()
        assert health["is_healthy"] is True
        await mgr.shutdown()
        assert mgr.state == PlatformState.SHUTDOWN


class TestAIResearchManagerHealthCheck:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health_check_before_init(self):
        mgr = AIResearchManager()
        health = await mgr.health_check()
        assert health["state"] == "initializing"
        assert health["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_after_init(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        health = await mgr.health_check()
        assert health["state"] == "ready"
        assert health["is_healthy"] is True
        assert health["uptime_seconds"] is not None
        assert health["engine_configured"] is False
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_with_engine(self):
        mgr = AIResearchManager(engine=AIResearchEngine())
        await mgr.initialize()
        health = await mgr.health_check()
        assert health["engine_configured"] is True

    @pytest.mark.asyncio
    async def test_health_check_after_shutdown(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        await mgr.shutdown()
        health = await mgr.health_check()
        assert health["is_healthy"] is False
        assert health["uptime_seconds"] is None


class TestAIResearchManagerConfigurationValidation:
    """Test configuration validation."""

    @pytest.mark.asyncio
    async def test_valid_config(self):
        mgr = AIResearchManager()
        await mgr.initialize()
        assert mgr.state == PlatformState.READY

    @pytest.mark.asyncio
    async def test_valid_custom_config_passes(self):
        mgr = AIResearchManager(config=ResearchPlatformConfig(name="valid-name"))
        await mgr.initialize()
        assert mgr.state == PlatformState.READY
