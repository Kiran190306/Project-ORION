"""Root test configuration and fixtures for Project ORION test suite."""

from __future__ import annotations

import sys
import types
from pathlib import Path

# Ensure apps.trading_engine maps to apps/trading-engine directory
repo_root = Path(__file__).resolve().parent.parent
engine_dir = repo_root / "apps" / "trading-engine"
if str(engine_dir) not in sys.path:
    sys.path.insert(0, str(engine_dir))

if "apps.trading_engine" not in sys.modules:
    mod = types.ModuleType("apps.trading_engine")
    mod.__path__ = [str(engine_dir)]
    sys.modules["apps.trading_engine"] = mod
