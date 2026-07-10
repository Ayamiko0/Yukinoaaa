"""Application service orchestrating AI market analysis workflows."""

from decimal import Decimal

from yukinoaaa.application.interfaces.ai import IAIService
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.ai.models import AIAnalysisResult, MarketContextSnapshot


class MarketAnalysisAIService:
    """Service responsible for synthesizing market metrics and executing AI analysis."""

    def __init__(self, ai_service: IAIService, logger: ILogger) -> None:
        """Initialize AI application service with underlying adapter and logger."""
        self._ai_service = ai_service
        self._logger = logger.bind(module="MarketAnalysisAIService")

    async def analyze_symbol(
        self,
        symbol: str,
        current_price: Decimal,
        rsi_value: float | None = None,
        macd_line: float | None = None,
        macd_signal: float | None = None,
        price_change_24h_pct: float = 0.0,
        active_position_side: str | None = None,
    ) -> AIAnalysisResult:
        """Construct market snapshot and perform quantitative AI evaluation."""
        self._logger.info("Initiating quantitative AI market analysis", symbol=symbol)
        snapshot = MarketContextSnapshot(
            symbol=symbol.upper(),
            current_price=current_price,
            rsi_14=rsi_value,
            macd_line=macd_line,
            macd_signal=macd_signal,
            price_change_24h_pct=price_change_24h_pct,
            active_position_side=active_position_side,
        )

        result = await self._ai_service.analyze_market(snapshot)
        self._logger.info(
            "AI analysis completed",
            symbol=result.symbol,
            sentiment=result.sentiment.value,
            confidence=result.confidence_score,
            recommendation=result.recommendation,
        )
        return result
