"""ExecutionContext - aggregates all inputs for the Execution Engine.

Provides a single context object with market data, account info,
broker availability, and risk assessment for order execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
