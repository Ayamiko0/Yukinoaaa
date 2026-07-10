"""Bidirectional Symbol Mapper between standardized notation and exchange formats."""

from yukinoaaa.domain.exceptions import ValidationException
from yukinoaaa.domain.market.models import Symbol


class SymbolMapper:
    """Manages mappings between standard symbols (e.g., 'BTC/USDT') and exchange symbols (e.g., 'BTCUSDT')."""

    def __init__(self) -> None:
        """Initialize bidirectional symbol registries."""
        # Mapping: exchange_id -> { standard_symbol -> raw_symbol }
        self._to_raw: dict[str, dict[str, str]] = {}
        # Mapping: exchange_id -> { raw_symbol -> standard_symbol }
        self._to_standard: dict[str, dict[str, str]] = {}

    def register_mapping(self, exchange_id: str, standard_symbol: str, raw_symbol: str) -> None:
        """Register a specific symbol mapping for an exchange."""
        std = standard_symbol.strip().upper()
        raw = raw_symbol.strip()
        if not std or not raw:
            raise ValidationException("Symbols cannot be empty during registration")

        if exchange_id not in self._to_raw:
            self._to_raw[exchange_id] = {}
            self._to_standard[exchange_id] = {}

        self._to_raw[exchange_id][std] = raw
        self._to_standard[exchange_id][raw] = std

    def to_exchange_symbol(self, exchange_id: str, symbol: Symbol | str) -> str:
        """Convert a standard symbol or string to exchange-specific raw symbol string."""
        std_str = symbol.standardized if isinstance(symbol, Symbol) else symbol.strip().upper()
        exchange_map = self._to_raw.get(exchange_id, {})
        if std_str in exchange_map:
            return exchange_map[std_str]
        # Default heuristic: strip slash for crypto/forex if unmapped
        return std_str.replace("/", "")

    def to_standard_symbol(
        self, exchange_id: str, raw_symbol: str, default_quote: str = "USDT"
    ) -> str:
        """Convert an exchange raw symbol string back to standard notation (e.g., 'BTC/USDT')."""
        raw = raw_symbol.strip()
        exchange_map = self._to_standard.get(exchange_id, {})
        if raw in exchange_map:
            return exchange_map[raw]

        # Heuristic parsing if not explicitly mapped
        if "/" in raw:
            return raw.upper()
        if raw.endswith(default_quote):
            base = raw[: -len(default_quote)]
            return f"{base}/{default_quote}".upper()
        if len(raw) == 6 and exchange_id in ("mt5", "forex"):
            # e.g., EURUSD -> EUR/USD
            return f"{raw[:3]}/{raw[3:]}".upper()

        return raw.upper()
