"""Tests for AdaptiveFlowController."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.backpressure import (
    AdaptiveFlowController,
    BackpressureMode,
)


class TestAdaptiveFlowController:
    def test_initial_state_not_paused(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
            )
            assert not await ctrl.is_paused()

        asyncio.run(exercise())

    def test_pause_at_high_water_mark(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
                mode=BackpressureMode.PAUSE_PRODUCER,
            )

            await ctrl.update_depth(50)
            assert not await ctrl.is_paused()

            await ctrl.update_depth(100)
            assert await ctrl.is_paused()

        asyncio.run(exercise())

    def test_resume_at_low_water_mark(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
                mode=BackpressureMode.PAUSE_PRODUCER,
            )

            await ctrl.update_depth(100)
            assert await ctrl.is_paused()

            await ctrl.update_depth(50)
            assert not await ctrl.is_paused()

        asyncio.run(exercise())

    def test_drop_events_mode_never_pauses(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
                mode=BackpressureMode.DROP_EVENTS,
            )

            await ctrl.update_depth(200)
            assert not await ctrl.is_paused()

        asyncio.run(exercise())

    def test_wait_if_paused_blocks(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
            )

            await ctrl.update_depth(100)

            # Should block briefly then resume
            async def resume_after_delay() -> None:
                await asyncio.sleep(0.05)
                await ctrl.resume()

            async def wait_for_resume() -> None:
                await ctrl.wait_if_paused()

            await asyncio.gather(wait_for_resume(), resume_after_delay())

        asyncio.run(exercise())

    def test_manual_pause_and_resume(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController()
            assert not await ctrl.is_paused()

            await ctrl.pause()
            assert await ctrl.is_paused()

            await ctrl.resume()
            assert not await ctrl.is_paused()

        asyncio.run(exercise())

    def test_get_state_returns_snapshot(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
                mode=BackpressureMode.PAUSE_PRODUCER,
            )

            await ctrl.update_depth(75)
            state = await ctrl.get_state()
            assert state.high_water_mark == 100
            assert state.low_water_mark == 50
            assert state.mode == BackpressureMode.PAUSE_PRODUCER

        asyncio.run(exercise())

    def test_adaptive_mode_throttling(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
                mode=BackpressureMode.ADAPTIVE,
            )

            # Between watermarks
            delay = await ctrl.compute_throttle_delay(75)
            assert delay > 0

            # Below low water mark
            delay = await ctrl.compute_throttle_delay(25)
            assert delay == 0.0

            # At high water mark
            delay = await ctrl.compute_throttle_delay(100)
            assert delay == 0.1

        asyncio.run(exercise())

    def test_invalid_watermarks(self) -> None:
        with pytest.raises(ValueError):
            AdaptiveFlowController(high_water_mark=50, low_water_mark=100)

    def test_tracks_pause_resume_counts(self) -> None:
        async def exercise() -> None:
            ctrl = AdaptiveFlowController(
                high_water_mark=100,
                low_water_mark=50,
            )

            await ctrl.pause()
            await ctrl.resume()
            await ctrl.pause()
            await ctrl.resume()

            state = await ctrl.get_state()
            assert state.total_pause_events == 2
            assert state.total_resume_events == 2

        asyncio.run(exercise())
