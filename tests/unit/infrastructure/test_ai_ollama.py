"""Unit tests for AI local LLM domain, application service, and Ollama adapter."""

from decimal import Decimal

import pytest

from yukinoaaa.application.ai.service import MarketAnalysisAIService
from yukinoaaa.domain.ai.models import AIAnalysisResult, MarketContextSnapshot, SentimentType
from yukinoaaa.infrastructure.ai.mock_adapter import MockAIAdapter
from yukinoaaa.infrastructure.ai.ollama_adapter import OllamaAIAdapter
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_mock_ai_adapter() -> None:
    """Test MockAIAdapter deterministic analysis behavior."""
    logger = StructlogLogger()
    adapter = MockAIAdapter(logger=logger)

    assert await adapter.is_available() is True
    resp = await adapter.generate_response("Test prompt")
    assert "Simulated" in resp

    # Test bullish oversold condition
    bullish_ctx = MarketContextSnapshot(
        symbol="BTC/USDT",
        current_price=Decimal("90000.00"),
        rsi_14=25.0,
    )
    res_bull = await adapter.analyze_market(bullish_ctx)
    assert res_bull.sentiment == SentimentType.BULLISH
    assert res_bull.recommendation == "BUY"

    # Test bearish overbought condition
    bearish_ctx = MarketContextSnapshot(
        symbol="BTC/USDT",
        current_price=Decimal("105000.00"),
        rsi_14=75.0,
    )
    res_bear = await adapter.analyze_market(bearish_ctx)
    assert res_bear.sentiment == SentimentType.BEARISH
    assert res_bear.recommendation == "SELL"


@pytest.mark.asyncio
async def test_ollama_adapter_parsing_and_fallback() -> None:
    """Test OllamaAIAdapter JSON result parsing and quantitative fallback."""
    logger = StructlogLogger()
    adapter = OllamaAIAdapter(model="gemma3", logger=logger)

    parsed = adapter._parse_json_result(
        "BTC/USDT",
        '{"sentiment": "BULLISH", "confidence_score": 0.88, "summary": "Strong rally", "detailed_analysis": "RSI momentum positive", "key_factors": ["MACD crossover"], "news_references": ["ETF flows"], "recommendation": "BUY"}',
    )
    assert parsed.symbol == "BTC/USDT"
    assert parsed.sentiment == SentimentType.BULLISH
    assert parsed.confidence_score == 0.88
    assert parsed.recommendation == "BUY"
    assert parsed.key_factors == ["MACD crossover"]
    assert parsed.detailed_analysis == "RSI momentum positive"
    assert parsed.news_references == ["ETF flows"]

    # Test quantitative fallback
    fallback_ctx = MarketContextSnapshot(
        symbol="ETH/USDT",
        current_price=Decimal("3500.00"),
        rsi_14=20.0,
    )
    res_fallback = adapter._fallback_result(fallback_ctx)
    assert res_fallback.symbol == "ETH/USDT"
    assert res_fallback.sentiment == SentimentType.BULLISH
    assert res_fallback.recommendation == "BUY"

    await adapter.close()


@pytest.mark.asyncio
async def test_market_analysis_ai_service() -> None:
    """Test MarketAnalysisAIService orchestration."""
    logger = StructlogLogger()
    adapter = MockAIAdapter(logger=logger)
    service = MarketAnalysisAIService(ai_service=adapter, logger=logger)

    result = await service.analyze_symbol(
        symbol="SOL/USDT",
        current_price=Decimal("210.00"),
        rsi_value=50.0,
        macd_line=1.2,
        macd_signal=1.0,
        price_change_24h_pct=3.5,
    )
    assert isinstance(result, AIAnalysisResult)
    assert result.symbol == "SOL/USDT"
    assert result.sentiment == SentimentType.NEUTRAL
