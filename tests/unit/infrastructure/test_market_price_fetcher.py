"""Unit tests for MarketPriceFetcher."""

import pytest

from yukinoaaa.infrastructure.logging.logger import StructlogLogger
from yukinoaaa.infrastructure.market.price_fetcher import MarketPriceFetcher


@pytest.mark.asyncio
async def test_market_price_fetcher_dynamic_fallback() -> None:
    """Test dynamic algorithmic fallback quotes for custom symbols across asset classes."""
    logger = StructlogLogger()
    fetcher = MarketPriceFetcher(logger=logger)

    # Crypto custom symbol fallback
    res_crypto = fetcher._generate_dynamic_quote("SHIB/USDT", "CRYPTO")
    assert res_crypto["symbol"] == "SHIB/USDT"
    assert res_crypto["asset_class"] == "CRYPTO"
    assert "price" in res_crypto
    assert "change" in res_crypto
    assert "rsi" in res_crypto

    # Commodity custom symbol fallback
    res_comm = fetcher._generate_dynamic_quote("PLATINUM/USD", "COMMODITY")
    assert res_comm["symbol"] == "PLATINUM/USD"
    assert res_comm["asset_class"] == "COMMODITY"
    assert "/ oz" in res_comm["price"] or "$" in res_comm["price"]

    # Forex custom symbol fallback
    res_forex = fetcher._generate_dynamic_quote("EUR/GBP", "FOREX")
    assert res_forex["symbol"] == "EUR/GBP"
    assert res_forex["asset_class"] == "FOREX"


@pytest.mark.asyncio
async def test_market_price_fetcher_fetch_quote() -> None:
    """Test fetch_price_quote entrypoint."""
    logger = StructlogLogger()
    fetcher = MarketPriceFetcher(logger=logger)

    quote = await fetcher.fetch_price_quote("CUSTOM_SYM", "CRYPTO")
    assert quote["symbol"] == "CUSTOM_SYM"
    assert "price" in quote
    assert "change" in quote
