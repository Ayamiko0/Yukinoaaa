"""Tests for bidirectional symbol mapper."""

from yukinoaaa.application.market.symbol_mapper import SymbolMapper
from yukinoaaa.domain.market.models import Symbol


def test_symbol_mapper_registration_and_conversion() -> None:
    """Verify explicit mapping registration and bidirectional conversion."""
    mapper = SymbolMapper()
    mapper.register_mapping(exchange_id="binance", standard_symbol="BTC/USDT", raw_symbol="BTCUSDT")
    mapper.register_mapping(exchange_id="okx", standard_symbol="BTC/USDT", raw_symbol="BTC-USDT-SWAP")

    sym = Symbol(base_asset="BTC", quote_asset="USDT")
    assert mapper.to_exchange_symbol("binance", sym) == "BTCUSDT"
    assert mapper.to_exchange_symbol("okx", sym) == "BTC-USDT-SWAP"

    assert mapper.to_standard_symbol("binance", "BTCUSDT") == "BTC/USDT"
    assert mapper.to_standard_symbol("okx", "BTC-USDT-SWAP") == "BTC/USDT"


def test_symbol_mapper_default_heuristics() -> None:
    """Verify conversion heuristics when mapping is not explicitly registered."""
    mapper = SymbolMapper()
    assert mapper.to_exchange_symbol("unknown_ex", "ETH/USDT") == "ETHUSDT"
    assert mapper.to_standard_symbol("unknown_ex", "ETHUSDT") == "ETH/USDT"
    assert mapper.to_standard_symbol("mt5", "EURUSD") == "EUR/USD"
