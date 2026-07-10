"""Mock AI adapter for deterministic simulation and automated tests."""

from yukinoaaa.application.interfaces.ai import IAIService
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.ai.models import AIAnalysisResult, MarketContextSnapshot, SentimentType


class MockAIAdapter(IAIService):
    """Mock implementation of IAIService returning deterministic analysis."""

    def __init__(self, logger: ILogger | None = None) -> None:
        """Initialize mock AI adapter."""
        if logger is not None:
            self._logger = logger.bind(module="MockAIAdapter")
        else:
            from yukinoaaa.infrastructure.logging.logger import StructlogLogger

            self._logger = StructlogLogger().bind(module="MockAIAdapter")

    async def is_available(self) -> bool:
        """Always return True for mock adapter."""
        return True

    async def generate_response(
        self, _prompt: str, _system_prompt: str | None = None
    ) -> str:
        """Return simulated AI response text."""
        return "Simulated quantitative reasoning output for prompt."

    async def analyze_market(self, context: MarketContextSnapshot) -> AIAnalysisResult:
        """Return deterministic AI quantitative assessment based on RSI."""
        sentiment = SentimentType.NEUTRAL
        recommendation = "HOLD"
        factors = ["Neutral market momentum"]

        if context.rsi_14 is not None:
            if context.rsi_14 < 35.0:
                sentiment = SentimentType.BULLISH
                recommendation = "BUY"
                factors = ["RSI indicates oversold support level"]
            elif context.rsi_14 > 65.0:
                sentiment = SentimentType.BEARISH
                recommendation = "SELL"
                factors = ["RSI indicates overbought resistance level"]

        return AIAnalysisResult(
            symbol=context.symbol,
            model_name="mock_quant_v1",
            sentiment=sentiment,
            confidence_score=0.85,
            summary=f"Simulated AI market analysis for {context.symbol} at ${context.current_price:,.2f}.",
            key_factors=factors,
            recommendation=recommendation,
        )
