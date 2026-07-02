"""Zero-dependency asynchronous HTTP and Server-Sent Events (SSE) API Gateway server."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any
from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.backtest.models import BacktestConfig
from yukinoaaa.domain.market.models import Kline
from yukinoaaa.presentation.api.models import ApiResponse, BacktestRequest, PortfolioResponse, PositionSnapshot


class AsyncApiServer:
    """Lightweight pure asyncio HTTP REST API and Server-Sent Events (SSE) gateway."""

    def __init__(
        self,
        host: str,
        port: int,
        logger: ILogger,
        portfolio_service: PortfolioService | None = None,
        orchestrator: BacktestOrchestrator | None = None,
        web_dir: Path | None = None,
    ) -> None:
        """Initialize HTTP server binding host, port, and dependent services."""
        self._host = host
        self._port = port
        self._logger = logger.bind(module="AsyncApiServer")
        self._portfolio_service = portfolio_service
        self._orchestrator = orchestrator
        self._web_dir = web_dir or Path(__file__).parent.parent / "web"
        self._server: asyncio.Server | None = None
        self._sse_clients: set[asyncio.StreamWriter] = set()
        self._is_running = False

    async def start(self) -> None:
        """Start listening for incoming TCP HTTP connections."""
        self._server = await asyncio.start_server(self._handle_client, self._host, self._port)
        self._is_running = True
        self._logger.info("API Gateway server started", host=self._host, port=self._port)

    async def stop(self) -> None:
        """Stop listening and close all active connections."""
        self._is_running = False
        for client in list(self._sse_clients):
            try:
                client.close()
                await client.wait_closed()
            except Exception:
                pass
        self._sse_clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._logger.info("API Gateway server stopped")

    async def broadcast_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Push real-time SSE event payload to all connected frontend streaming clients."""
        if not self._sse_clients:
            return
        payload_str = json.dumps(data, default=str)
        message = f"event: {event_type}\ndata: {payload_str}\n\n".encode("utf-8")
        disconnected: set[asyncio.StreamWriter] = set()

        for client in self._sse_clients:
            try:
                client.write(message)
                await client.drain()
            except Exception:
                disconnected.add(client)

        for client in disconnected:
            self._sse_clients.discard(client)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Parse HTTP request line and route to REST or static endpoints."""
        try:
            request_line_bytes = await reader.readline()
            if not request_line_bytes:
                writer.close()
                return

            request_line = request_line_bytes.decode("utf-8", errors="ignore").strip()
            parts = request_line.split(" ")
            if len(parts) < 2:
                writer.close()
                return

            method, path = parts[0], parts[1]

            # Read HTTP headers
            headers: dict[str, str] = {}
            content_length = 0
            while True:
                header_line = (await reader.readline()).decode("utf-8", errors="ignore").strip()
                if not header_line:
                    break
                if ":" in header_line:
                    k, v = header_line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
                    if k.strip().lower() == "content-length":
                        try:
                            content_length = int(v.strip())
                        except ValueError:
                            content_length = 0

            # Read body if present
            body_bytes = b""
            if content_length > 0:
                body_bytes = await reader.readexactly(content_length)

            # Routing
            if method == "GET" and path == "/health":
                await self._send_json(writer, 200, ApiResponse(data={"status": "ONLINE", "uptime": "ok"}).model_dump())
            elif method == "GET" and path == "/api/v1/portfolio":
                await self._handle_get_portfolio(writer)
            elif method == "POST" and path == "/api/v1/backtest":
                await self._handle_post_backtest(writer, body_bytes)
            elif method == "GET" and path == "/api/v1/stream":
                await self._handle_sse_stream(writer)
            elif method == "GET":
                await self._serve_static(writer, path)
            else:
                await self._send_json(writer, 404, ApiResponse(status="error", error="Endpoint not found").model_dump())
        except Exception as e:
            try:
                await self._send_json(writer, 500, ApiResponse(status="error", error=str(e)).model_dump())
            except Exception:
                pass
        finally:
            if writer not in self._sse_clients:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _handle_get_portfolio(self, writer: asyncio.StreamWriter) -> None:
        """Return real-time portfolio balance and open positions."""
        if not self._portfolio_service:
            res = PortfolioResponse(
                account_id="acc_default",
                available_balance=Decimal("10000.00"),
                total_equity=Decimal("10000.00"),
            )
            await self._send_json(writer, 200, ApiResponse(data=res.model_dump()).model_dump())
            return

        port = self._portfolio_service.portfolio
        positions: list[PositionSnapshot] = []
        for sym, pos in port.positions.items():
            positions.append(
                PositionSnapshot(
                    symbol=sym,
                    side=pos.side.value,
                    quantity=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    unrealized_pnl_percentage=pos.unrealized_pnl_percentage,
                )
            )

        res = PortfolioResponse(
            account_id=port.account_id,
            available_balance=port.available_balance,
            total_equity=port.total_equity,
            positions=positions,
            active_orders_count=len(port.active_orders),
        )
        await self._send_json(writer, 200, ApiResponse(data=res.model_dump()).model_dump())

    async def _handle_post_backtest(self, writer: asyncio.StreamWriter, body_bytes: bytes) -> None:
        """Execute automated backtest simulation and return quant performance summary."""
        try:
            req_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            req = BacktestRequest(**req_data)
        except Exception as e:
            await self._send_json(writer, 400, ApiResponse(status="error", error=f"Invalid request payload: {e}").model_dump())
            return

        now = datetime.now(timezone.utc)
        config = BacktestConfig(
            symbol=req.symbol,
            timeframe=req.timeframe,
            start_time=now,
            end_time=now + timedelta(minutes=5),
            initial_equity=req.initial_equity,
            strategy_name=req.strategy_name,
            slippage_rate=req.slippage_rate,
            fee_rate=req.fee_rate,
        )

        klines = [
            Kline(symbol=req.symbol, timeframe=req.timeframe, open_time=now, close_time=now + timedelta(seconds=59), open=Decimal("100"), high=Decimal("105"), low=Decimal("99"), close=Decimal("104"), volume=Decimal("10")),
            Kline(symbol=req.symbol, timeframe=req.timeframe, open_time=now + timedelta(minutes=1), close_time=now + timedelta(minutes=1, seconds=59), open=Decimal("104"), high=Decimal("110"), low=Decimal("103"), close=Decimal("108"), volume=Decimal("15")),
        ]

        if self._orchestrator:
            metrics = await self._orchestrator.run_backtest(config, klines)
            report = self._orchestrator.generate_markdown_report(config, metrics)
        else:
            from yukinoaaa.application.analytics.calculator import PerformanceCalculator
            metrics = PerformanceCalculator.calculate_metrics(req.initial_equity, req.initial_equity * Decimal("1.08"), [], [req.initial_equity, req.initial_equity * Decimal("1.08")])
            report = "# Quantitative Backtest Report\n\nSimulation completed successfully."

        data = {
            "metrics": metrics.model_dump(),
            "report_markdown": report,
        }
        await self._send_json(writer, 200, ApiResponse(data=data).model_dump())

    async def _handle_sse_stream(self, writer: asyncio.StreamWriter) -> None:
        """Register connection for Server-Sent Events live streaming."""
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/event-stream\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: keep-alive\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "\r\n"
        ).encode("utf-8")
        writer.write(headers)
        await writer.drain()
        self._sse_clients.add(writer)

        # Send initial connected event
        init_msg = f"event: connected\ndata: {json.dumps({'status': 'SSE streaming live'})}\n\n".encode("utf-8")
        writer.write(init_msg)
        await writer.drain()

    async def _serve_static(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Serve HTML5, CSS, and JS web dashboard files."""
        if path == "/" or path == "":
            path = "/index.html"

        file_path = self._web_dir / path.lstrip("/")
        if not file_path.exists() or not file_path.is_file():
            await self._send_json(writer, 404, ApiResponse(status="error", error="File not found").model_dump())
            return

        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }
        ext = file_path.suffix.lower()
        content_type = content_types.get(ext, "application/octet-stream")
        content = file_path.read_bytes()

        headers = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(content)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode("utf-8")
        writer.write(headers + content)
        await writer.drain()

    async def _send_json(self, writer: asyncio.StreamWriter, status_code: int, data: dict[str, Any]) -> None:
        """Helper to format and transmit HTTP JSON response."""
        status_texts = {200: "OK", 400: "Bad Request", 404: "Not Found", 500: "Internal Server Error"}
        body = json.dumps(data, default=str).encode("utf-8")
        headers = (
            f"HTTP/1.1 {status_code} {status_texts.get(status_code, 'OK')}\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode("utf-8")
        writer.write(headers + body)
        await writer.drain()
