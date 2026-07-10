"""AI service abstract interface definition."""

from abc import ABC, abstractmethod

from yukinoaaa.domain.ai.models import AIAnalysisResult, MarketContextSnapshot


class IAIService(ABC):
    """Abstract contract for Quantitative AI / LLM reasoning engines."""

    @abstractmethod
    async def analyze_market(self, context: MarketContextSnapshot) -> AIAnalysisResult:
        """Analyze market snapshot and return structured quantitative synthesis."""
        ...

    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate free-form text response from prompt context."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if local AI runtime / engine is reachable and healthy."""
        ...
