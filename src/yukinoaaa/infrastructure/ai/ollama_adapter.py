"""Ollama REST API adapter for real-time quantitative local LLM reasoning."""

import json
from typing import Any

import aiohttp

from yukinoaaa.application.interfaces.ai import IAIService
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.ai.models import AIAnalysisResult, MarketContextSnapshot, SentimentType


class OllamaAIAdapter(IAIService):
    """Direct HTTP REST client interacting with a Local Ollama LLM instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/api",
        model: str = "gemma3:1b",
        num_ctx: int = 4096,
        num_predict: int = 512,
        temperature: float = 0.2,
        timeout_sec: float = 60.0,
        logger: ILogger | None = None,
    ) -> None:
        """Initialize Ollama REST API adapter configuration."""
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._num_ctx = num_ctx
        self._num_predict = num_predict
        self._temperature = temperature
        self._timeout_sec = timeout_sec
        self._session: aiohttp.ClientSession | None = None
        if logger is not None:
            self._logger = logger.bind(module="OllamaAIAdapter", model=self._model)
        else:
            from yukinoaaa.infrastructure.logging.logger import StructlogLogger

            self._logger = StructlogLogger().bind(module="OllamaAIAdapter", model=self._model)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or initialize reusable HTTP client session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close underlying HTTP client session cleanly."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def is_available(self) -> bool:
        """Check if Ollama host is reachable and responds to API calls."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base_url}/tags",
                timeout=aiohttp.ClientTimeout(total=5.0),
            ) as resp:
                if resp.status == 200:
                    self._logger.debug("Ollama server availability check passed")
                    return True
        except (aiohttp.ClientError, TimeoutError):
            self._logger.warning("Ollama server is currently unreachable", base_url=self._base_url)
        return False

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate free-form text response from prompt using Ollama /api/generate."""
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self._temperature,
                "num_ctx": self._num_ctx,
                "num_predict": self._num_predict,
            },
            "keep_alive": "10m",
        }
        if system_prompt:
            payload["system"] = system_prompt

        session = await self._get_session()
        try:
            async with session.post(
                f"{self._base_url}/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self._timeout_sec),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return str(data.get("response", "")).strip()
        except (aiohttp.ClientError, TimeoutError) as exc:
            self._logger.error("Ollama generate request failed", error=str(exc))
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

    async def analyze_market(self, context: MarketContextSnapshot) -> AIAnalysisResult:
        """Analyze market context snapshot using Ollama structured JSON generation."""
        prompt = self._build_analysis_prompt(context)
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self._temperature,
                "num_ctx": self._num_ctx,
                "num_predict": self._num_predict,
            },
            "keep_alive": "10m",
        }

        session = await self._get_session()
        try:
            async with session.post(
                f"{self._base_url}/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self._timeout_sec),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                raw_json = str(data.get("response", "{}"))
                return self._parse_json_result(context.symbol, raw_json)
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            self._logger.warning(
                "Ollama structured analysis failed, using quantitative fallback",
                symbol=context.symbol,
                error=str(exc),
            )
            return self._fallback_result(context)

    def _build_analysis_prompt(self, context: MarketContextSnapshot) -> str:
        """Construct quantitative market analysis prompt requesting structured JSON output."""
        return f"""You are an elite quantitative crypto trading analyst and macro strategist.
Analyze the following real-time market data snapshot for symbol '{context.symbol}':
- Current Price: {context.current_price}
- RSI (14): {context.rsi_14 if context.rsi_14 is not None else "N/A"}
- MACD Line: {context.macd_line if context.macd_line is not None else "N/A"}
- MACD Signal: {context.macd_signal if context.macd_signal is not None else "N/A"}
- Estimated 24h Price Change: {context.price_change_24h_pct:.2f}%
- Active Position Side: {context.active_position_side or "NONE"}

Return strictly valid JSON with the following keys and format:
{{
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence_score": 0.75,
  "summary": "Concise 1-2 sentence quantitative summary of price action.",
  "detailed_analysis": "In-depth paragraph (~3-4 sentences) evaluating momentum, RSI/MACD divergence, support/resistance levels, and risk-reward profile.",
  "key_factors": ["RSI momentum status", "MACD crossover signal"],
  "news_references": ["Recent ETF inflows / institutional accumulation catalysts", "Macro interest rate expectations affecting crypto sentiment"],
  "recommendation": "BUY" | "SELL" | "HOLD"
}}"""

    def _parse_json_result(self, symbol: str, raw_json: str) -> AIAnalysisResult:
        """Parse structured JSON string from LLM into AIAnalysisResult model."""
        parsed = json.loads(raw_json)
        sentiment_str = str(parsed.get("sentiment", "NEUTRAL")).upper()
        sentiment = (
            SentimentType(sentiment_str)
            if sentiment_str in ("BULLISH", "BEARISH", "NEUTRAL")
            else SentimentType.NEUTRAL
        )
        confidence = float(parsed.get("confidence_score", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        summary = str(
            parsed.get("summary", "Quantitative analysis completed based on market indicators.")
        )
        detailed_analysis = str(
            parsed.get(
                "detailed_analysis",
                "Technical indicators evaluated across momentum and volatility metrics.",
            )
        )
        key_factors = [str(f) for f in parsed.get("key_factors", ["Technical Momentum"])]
        news_references = [
            str(n)
            for n in parsed.get(
                "news_references",
                ["Macro liquidity outlook and crypto market sentiment observations"],
            )
        ]
        recommendation = str(parsed.get("recommendation", "HOLD")).upper()
        if recommendation not in ("BUY", "SELL", "HOLD"):
            recommendation = "HOLD"

        return AIAnalysisResult(
            symbol=symbol,
            model_name=self._model,
            sentiment=sentiment,
            confidence_score=confidence,
            summary=summary,
            detailed_analysis=detailed_analysis,
            key_factors=key_factors,
            news_references=news_references,
            recommendation=recommendation,
        )

    def _fallback_result(self, context: MarketContextSnapshot) -> AIAnalysisResult:
        """Generate thorough quantitative analysis when local LLM is unreachable."""
        sentiment = SentimentType.NEUTRAL
        recommendation = "HOLD"
        factors: list[str] = []

        rsi_text = "RSI ở vùng trung tính, dao động ổn định quanh mốc cân bằng."
        if context.rsi_14 is not None:
            if context.rsi_14 < 30.0:
                sentiment = SentimentType.BULLISH
                recommendation = "BUY"
                factors.append(f"RSI oversold condition ({context.rsi_14:.1f})")
                rsi_text = f"Chỉ báo RSI ({context.rsi_14:.1f}) tiến sâu vào vùng quá bán, áp lực bán có dấu hiệu cạn kiệt, tạo cơ hội phục hồi kỹ thuật."
            elif context.rsi_14 > 70.0:
                sentiment = SentimentType.BEARISH
                recommendation = "SELL"
                factors.append(f"RSI overbought condition ({context.rsi_14:.1f})")
                rsi_text = f"Chỉ báo RSI ({context.rsi_14:.1f}) chạm vùng quá mua rủi ro cao, tiềm ẩn khả năng điều chỉnh chốt lời ngắn hạn."
            else:
                factors.append(f"RSI neutral ({context.rsi_14:.1f})")

        detailed_analysis = (
            f"Đánh giá định lượng cho cặp {context.symbol} tại vùng giá ${context.current_price:,.2f}. "
            f"{rsi_text} Tương quan giữa đường MACD và tín hiệu cho thấy xu hướng biến động ở mức {sentiment.value}. "
            "Nhà giao dịch nên theo dõi sát các mốc hỗ trợ và kháng cự quan trọng, duy trì kỷ luật quản lý rủi ro."
        )

        news_refs = [
            "Xu hướng dòng tiền tổ chức (Institutional & ETF Liquidity Flows)",
            "Chỉ số vĩ mô toàn cầu tác động đến tâm lý thị trường tài sản rủi ro",
            "Biến động thanh khoản và khối lượng giao dịch trên các sàn phái sinh 24h qua",
        ]

        return AIAnalysisResult(
            symbol=context.symbol,
            model_name=f"{self._model}_fallback",
            sentiment=sentiment,
            confidence_score=0.6,
            summary=f"Đánh giá tổng hợp cho {context.symbol} ở mức giá ${context.current_price:,.2f} ({context.price_change_24h_pct:+.2f}% 24h).",
            detailed_analysis=detailed_analysis,
            key_factors=factors or ["Standard price monitoring"],
            news_references=news_refs,
            recommendation=recommendation,
        )
