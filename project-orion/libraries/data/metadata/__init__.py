"""
Metadata Module

Module Description:
This module provides metadata management for data platform.
It handles symbol metadata, session metadata, holiday calendars, and DST configurations.

Implementation Checklist:
- [ ] Metadata manager
- [ ] Symbol metadata storage
- [ ] Session metadata storage
- [ ] Holiday calendar storage
- [ ] DST configuration storage
- [ ] Metadata queries
- [ ] Metadata updates

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/, libraries/data/storage/, libraries/data/cache/
- Used by: datasets/, pipelines/, normalizers/
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from libraries.data.cache import CacheManager
from libraries.data.schemas import (
    AssetClass,
    DaylightSavingConfig,
    Holiday,
    Session,
    SymbolMetadata,
    TradingHours,
)
from libraries.data.storage import StorageManager
from shared.errors import OrionError


class MetadataError(OrionError):
    """Metadata error."""

    pass


class MetadataManager:
    """Manager for metadata storage and retrieval."""

    def __init__(self, storage: StorageManager, cache: Optional[CacheManager] = None):
        """Initialize metadata manager.

        Args:
            storage: Storage manager
            cache: Optional cache manager
        """
        self.storage = storage
        self.cache = cache or CacheManager()

    def save_symbol_metadata(self, metadata: SymbolMetadata) -> bool:
        """Save symbol metadata."""
        try:
            path = f"metadata/symbols/{metadata.symbol}.json"
            self.storage.write(path, metadata)

            # Invalidate cache
            cache_key = f"metadata:symbol:{metadata.symbol}"
            self.cache.delete(cache_key)

            return True
        except Exception as e:
            raise MetadataError(f"Failed to save symbol metadata: {str(e)}")

    def get_symbol_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Get symbol metadata."""
        try:
            # Check cache first
            cache_key = f"metadata:symbol:{symbol}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return SymbolMetadata(**cached) if isinstance(cached, dict) else cached

            # Load from storage
            path = f"metadata/symbols/{symbol}.json"
            metadata = self.storage.read(path)

            if metadata is not None:
                # Cache the result
                self.cache.set(cache_key, metadata)
                return SymbolMetadata(**metadata) if isinstance(metadata, dict) else metadata

            return None
        except Exception as e:
            raise MetadataError(f"Failed to get symbol metadata: {str(e)}")

    def list_symbols(self) -> List[str]:
        """List all symbols with metadata."""
        try:
            files = self.storage.list("metadata/symbols/")
            return [f.replace("metadata/symbols/", "").replace(".json", "") for f in files]
        except Exception as e:
            raise MetadataError(f"Failed to list symbols: {str(e)}")

    def save_session_metadata(self, session: Session) -> bool:
        """Save session metadata."""
        try:
            path = f"metadata/sessions/{session.session_id}.json"
            self.storage.write(path, session)
            return True
        except Exception as e:
            raise MetadataError(f"Failed to save session metadata: {str(e)}")

    def get_session_metadata(self, session_id: str) -> Optional[Session]:
        """Get session metadata."""
        try:
            path = f"metadata/sessions/{session_id}.json"
            return self.storage.read(path)
        except Exception as e:
            raise MetadataError(f"Failed to get session metadata: {str(e)}")

    def save_holiday_calendar(self, holiday: Holiday) -> bool:
        """Save holiday calendar entry."""
        try:
            path = f"metadata/holidays/{holiday.holiday_id}.json"
            self.storage.write(path, holiday)
            return True
        except Exception as e:
            raise MetadataError(f"Failed to save holiday calendar: {str(e)}")

    def get_holidays_for_symbol(self, symbol: str, year: int) -> List[Holiday]:
        """Get holidays for symbol in year."""
        try:
            # TODO: Implement holiday filtering logic
            files = self.storage.list("metadata/holidays/")
            holidays = []
            for file in files:
                holiday = self.storage.read(file)
                if holiday and symbol in holiday.affected_symbols:
                    holidays.append(holiday)
            return holidays
        except Exception as e:
            raise MetadataError(f"Failed to get holidays: {str(e)}")

    def save_dst_configuration(self, config: DaylightSavingConfig) -> bool:
        """Save DST configuration."""
        try:
            path = f"metadata/dst/{config.timezone}.json"
            self.storage.write(path, config)
            return True
        except Exception as e:
            raise MetadataError(f"Failed to save DST configuration: {str(e)}")

    def get_dst_configuration(self, timezone: str) -> Optional[DaylightSavingConfig]:
        """Get DST configuration for timezone."""
        try:
            path = f"metadata/dst/{timezone}.json"
            return self.storage.read(path)
        except Exception as e:
            raise MetadataError(f"Failed to get DST configuration: {str(e)}")

    def apply_dst_adjustment(self, timestamp: datetime, timezone: str) -> datetime:
        """Apply DST adjustment to timestamp."""
        try:
            config = self.get_dst_configuration(timezone)
            if not config or not config.dst_aware:
                return timestamp

            # TODO: Implement DST adjustment logic
            return timestamp
        except Exception as e:
            raise MetadataError(f"Failed to apply DST adjustment: {str(e)}")
