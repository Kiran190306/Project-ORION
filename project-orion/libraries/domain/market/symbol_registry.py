"""Concurrency-safe registry for canonical symbols and provider aliases."""

from __future__ import annotations

import asyncio

from .exceptions import DuplicateSymbolError, UnknownSymbolError
from .models import Symbol
from .normalization import NormalizationEngine


class SymbolRegistry:
    """Store immutable instrument definitions and provider-specific aliases."""

    def __init__(self, normalizer: NormalizationEngine | None = None) -> None:
        self._normalizer = normalizer or NormalizationEngine()
        self._symbols: dict[str, Symbol] = {}
        self._aliases: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def register(self, symbol: Symbol, aliases: tuple[str, ...] = ()) -> None:
        """Register a symbol and aliases atomically.

        Raises:
            DuplicateSymbolError: If a canonical code or alias already exists.
        """
        canonical = self._normalizer.normalize_symbol(symbol.code)
        normalized_aliases = tuple(self._normalizer.normalize_symbol(alias) for alias in aliases)
        keys = (canonical, *normalized_aliases)
        async with self._lock:
            if any(key in self._symbols or key in self._aliases for key in keys):
                duplicate = next(
                    key for key in keys if key in self._symbols or key in self._aliases
                )
                raise DuplicateSymbolError(duplicate)
            self._symbols[canonical] = symbol
            self._aliases.update({alias: canonical for alias in normalized_aliases})

    async def get(self, symbol_or_alias: str) -> Symbol:
        """Resolve and return an active immutable instrument definition."""
        key = self._normalizer.normalize_symbol(symbol_or_alias)
        async with self._lock:
            canonical = self._aliases.get(key, key)
            symbol = self._symbols.get(canonical)
        if symbol is None or not symbol.active:
            raise UnknownSymbolError(symbol_or_alias)
        return symbol

    async def list_symbols(self) -> tuple[Symbol, ...]:
        """Return registered symbols in deterministic canonical-code order."""
        async with self._lock:
            return tuple(self._symbols[key] for key in sorted(self._symbols))

    async def load_canonical_instruments(self) -> None:
        """Seed registry with all active canonical instruments and standard aliases.

        Uses the single central canonical authority `canonical_instruments()`.
        """
        from libraries.domain.market_data.normalization import (
            _COMMON_SYMBOL_ALIASES,
            canonical_instruments,
        )

        for inst in canonical_instruments().values():
            symbol_obj = Symbol.from_instrument(inst)
            aliases = tuple(
                alias
                for alias, canonical in _COMMON_SYMBOL_ALIASES.items()
                if canonical == inst.symbol
            )
            await self.register(symbol_obj, aliases=aliases)

    @classmethod
    async def create_with_canonical_instruments(
        cls, normalizer: NormalizationEngine | None = None
    ) -> SymbolRegistry:
        """Factory creating and initializing a SymbolRegistry seeded with all canonical instruments."""
        registry = cls(normalizer=normalizer)
        await registry.load_canonical_instruments()
        return registry
