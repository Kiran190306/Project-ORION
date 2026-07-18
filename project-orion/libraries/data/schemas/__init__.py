"""
Data Schemas Module

Module Description:
This module defines all data schemas for the Data Platform Foundation.
It includes market data models, metadata models, and quality models.

Implementation Checklist:
- [ ] Tick data schema
- [ ] OHLC data schema
- [ ] Symbol metadata schema
- [ ] Session metadata schema
- [ ] Holiday calendar schema
- [ ] Daylight saving configuration schema
- [ ] Corporate action schema
- [ ] Data lineage schema
- [ ] Dataset version schema
- [ ] Data quality report schema
- [ ] Dataset registry schema

Dependency Notes:
- Depends on: shared/ (types, enums, constants)
- Used by: All data platform modules
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from shared.constants import DEFAULT_TIMEOUT, MAX_POSITION_SIZE
from shared.enums import OrderSide, OrderStatus
from shared.types import Symbol, Timestamp


class AssetClass(Enum):
    """Asset class enumeration."""

    FOREX = "forex"
    CRYPTO = "crypto"
    EQUITY = "equity"
    COMMODITY = "commodity"
    INDEX = "index"


class DatasetType(Enum):
    """Dataset type enumeration."""

    TICK = "tick"
    OHLC = "ohlc"
    METADATA = "metadata"


class LifecycleStage(Enum):
    """Dataset lifecycle stage enumeration."""

    IMPORT = "import"
    VALIDATION = "validation"
    APPROVAL = "approval"
    ACTIVE = "active"
    ARCHIVE = "archive"
    RETIRE = "retire"


class ChangeType(Enum):
    """Dataset version change type enumeration."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class CorporateActionType(Enum):
    """Corporate action type enumeration."""

    SPLIT = "split"
    DIVIDEND = "dividend"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    SPINOFF = "spinoff"
    SYMBOL_CHANGE = "symbol_change"


@dataclass
class Tick:
    """Tick data schema."""

    tick_id: str
    symbol: str
    timestamp: datetime  # UTC
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Optional[Decimal] = None
    ask_size: Optional[Decimal] = None
    source: str = ""
    source_sequence: Optional[int] = None
    data_version: str = "1.0.0"


@dataclass
class OHLC:
    """OHLC data schema."""

    candle_id: str
    symbol: str
    timeframe: str
    timestamp: datetime  # UTC, aligned to timeframe
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    tick_count: int
    data_version: str = "1.0.0"
    source_version: str = "1.0.0"


@dataclass
class TradingHours:
    """Trading hours schema."""

    monday: Optional[List[time]] = None
    tuesday: Optional[List[time]] = None
    wednesday: Optional[List[time]] = None
    thursday: Optional[List[time]] = None
    friday: Optional[List[time]] = None
    saturday: Optional[List[time]] = None
    sunday: Optional[List[time]] = None


@dataclass
class Session:
    """Session metadata schema."""

    session_id: str
    name: str  # Asian, London, New York
    timezone: str
    start_time: time  # in session timezone
    end_time: time  # in session timezone
    days_of_week: List[int] = field(default_factory=list)  # 0-6, Monday=0
    daylight_saving_aware: bool = False
    daylight_saving_rule: Optional[str] = None


@dataclass
class Holiday:
    """Holiday calendar schema."""

    holiday_id: str
    name: str
    date: date
    affected_symbols: List[str] = field(default_factory=list)
    affected_sessions: List[str] = field(default_factory=list)
    early_close_time: Optional[time] = None
    late_open_time: Optional[time] = None
    full_day_closure: bool = False
    timezone: str = "UTC"


@dataclass
class DaylightSavingConfig:
    """Daylight saving configuration schema."""

    timezone: str = "UTC"
    dst_aware: bool = False

    dst_start_rule: Optional[str] = None  # e.g., "second Sunday in March at 2:00 AM"
    dst_end_rule: Optional[str] = None  # e.g., "first Sunday in November at 2:00 AM"
    dst_offset: Optional[time] = None
    standard_offset: time = time(0, 0)


@dataclass
class MarginRequirements:
    """Margin requirements schema."""

    initial_margin: Decimal = Decimal("0")
    maintenance_margin: Decimal = Decimal("0")
    hedge_margin: Optional[Decimal] = None


@dataclass
class CommissionStructure:
    """Commission structure schema."""

    commission_per_lot: Decimal = Decimal("0")

    commission_per_share: Optional[Decimal] = None
    minimum_commission: Optional[Decimal] = None


@dataclass
class SwapRates:
    """Swap rates schema."""

    long_swap: Decimal = Decimal("0")
    short_swap: Decimal = Decimal("0")


@dataclass
class SymbolMetadata:
    """Symbol metadata schema."""

    symbol_id: str
    symbol: str
    asset_class: AssetClass
    base_currency: str
    quote_currency: str
    pip_size: Decimal
    tick_size: Decimal
    contract_size: Decimal
    trading_hours: TradingHours
    sessions: List[Session] = field(default_factory=list)
    holidays: List[Holiday] = field(default_factory=list)
    daylight_saving: DaylightSavingConfig = field(default_factory=DaylightSavingConfig)
    margin_requirements: MarginRequirements = field(default_factory=MarginRequirements)
    commission_structure: CommissionStructure = field(default_factory=CommissionStructure)
    swap_rates: SwapRates = field(default_factory=SwapRates)
    active: bool = True
    listed_date: Optional[datetime] = None
    delisted_date: Optional[datetime] = None
    data_sources: List[str] = field(default_factory=list)
    data_quality_score: float = 1.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Transformation:
    """Transformation record schema."""

    transformation_id: str
    transformation_type: str
    parameters: dict[str, object]
    timestamp: datetime


@dataclass
class QualityCheck:
    """Quality check result schema."""

    check_id: str
    check_name: str
    check_type: str
    passed: bool
    score: float
    details: dict[str, object]
    timestamp: datetime


@dataclass
class DataLineage:
    """Data lineage schema."""

    lineage_id: str
    dataset_id: str
    dataset_type: DatasetType
    version: str

    # Source
    source_id: str
    source_type: str
    source_timestamp: datetime

    # Transformation
    transformations: List[Transformation] = field(default_factory=list)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # dataset IDs

    # Quality
    quality_score: float = 1.0
    quality_checks: List[QualityCheck] = field(default_factory=list)

    # Storage
    storage_location: str = ""
    storage_checksum: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class DatasetVersion:
    """Dataset version schema."""

    version_id: str
    dataset_id: str
    version: str
    previous_version: Optional[str] = None

    # Changes
    change_type: ChangeType = ChangeType.PATCH
    change_description: str = ""

    # Quality
    quality_score: float = 1.0

    # Compatibility
    backward_compatible: bool = True
    forward_compatible: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class DateRange:
    """Date range schema."""

    start_date: date
    end_date: date


@dataclass
class QualityIssue:
    """Quality issue schema."""

    issue_id: str
    issue_type: str
    severity: str
    description: str
    location: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class DataQualityReport:
    """Data quality report schema."""

    report_id: str
    dataset_id: str
    dataset_version: str
    report_timestamp: datetime = field(default_factory=datetime.utcnow)

    # Component Scores
    missing_candle_score: float = 1.0
    duplicate_score: float = 1.0
    timestamp_score: float = 1.0
    outlier_score: float = 1.0
    file_score: float = 1.0
    gap_score: float = 1.0
    session_score: float = 1.0
    timezone_score: float = 1.0
    symbol_score: float = 1.0
    checksum_score: float = 1.0

    # Overall Score
    overall_score: float = 1.0
    quality_bucket: str = "excellent"

    # Issues
    issues: List[QualityIssue] = field(default_factory=list)
    warnings: List[QualityIssue] = field(default_factory=list)
    quality_checks: List[QualityCheck] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Decision
    approved: bool = True
    approval_threshold: float = 0.9

    # Metadata
    checker_version: str = "1.0.0"
    checked_by: str = ""


@dataclass
class DatasetRegistry:
    """Dataset registry schema."""

    registry_id: str
    dataset_id: str
    dataset_type: DatasetType
    dataset_version: str

    # Identification
    symbol: str
    timeframe: Optional[str] = None
    date_range: Optional[DateRange] = None

    # Quality
    quality_score: float = 1.0
    quality_bucket: str = "excellent"

    # Lifecycle
    lifecycle_stage: LifecycleStage = LifecycleStage.IMPORT
    stage_entry_date: datetime = field(default_factory=datetime.utcnow)
    stage_exit_date: Optional[datetime] = None

    # Source
    source_id: str = ""
    source_type: str = ""

    # Storage
    storage_location: str = ""
    storage_checksum: str = ""
    storage_size_bytes: int = 0

    # Lineage
    lineage_id: str = ""
    dependencies: List[str] = field(default_factory=list)

    # Usage
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
