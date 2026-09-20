"""Project ORION apps package.

Provides namespace alias 'apps.trading_engine' for the 'apps/trading-engine'
directory to support standard Python imports alongside kebab-case directory conventions.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

# Provide 'apps.trading_engine' alias for 'apps/trading-engine'
_engine_dir = Path(__file__).resolve().parent / "trading-engine"
if _engine_dir.exists() and "apps.trading_engine" not in sys.modules:
    _mod = types.ModuleType("apps.trading_engine")
    _mod.__path__ = [str(_engine_dir)]
    sys.modules["apps.trading_engine"] = _mod
