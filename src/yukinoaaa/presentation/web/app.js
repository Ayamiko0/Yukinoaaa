/**
 * Yukinoaaa Trading Assistant | Frontend Real-Time Streaming & UI Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initRealtimeStream();
    initPortfolioSync();
    initBacktestStudio();
});

function initRealtimeStream() {
    const navStatus = document.getElementById('nav-status');
    const tickerPrice = document.getElementById('ticker-price');
    const liveCandle = document.getElementById('live-candle');

    // Simulate real-time price tick fluctuations or SSE connection
    let basePrice = 95420.50;
    setInterval(() => {
        const delta = (Math.random() - 0.48) * 45;
        basePrice += delta;
        tickerPrice.textContent = basePrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        
        if (delta > 0) {
            liveCandle.style.height = '95%';
            liveCandle.className = 'candle bull active';
        } else {
            liveCandle.style.height = '65%';
            liveCandle.className = 'candle bear active';
        }
    }, 2500);

    // Try SSE stream if server connected
    try {
        const evtSource = new EventSource('/api/v1/stream');
        evtSource.addEventListener('connected', (e) => {
            navStatus.textContent = 'REALTIME SSE';
        });
        evtSource.addEventListener('TickReceived', (e) => {
            const data = JSON.parse(e.data);
            if (data.price) {
                tickerPrice.textContent = parseFloat(data.price).toLocaleString('en-US', { minimumFractionDigits: 2 });
            }
        });
    } catch (err) {
        console.log('SSE fallback mode');
    }
}

function initPortfolioSync() {
    const btnRefresh = document.getElementById('btn-refresh');
    const navEquity = document.getElementById('nav-equity');
    const portBalance = document.getElementById('port-balance');
    const portEquity = document.getElementById('port-equity');
    const portPosCount = document.getElementById('port-pos-count');
    const tbody = document.getElementById('positions-tbody');

    async function sync() {
        try {
            const res = await fetch('/api/v1/portfolio');
            const json = await res.json();
            if (json.status === 'success' && json.data) {
                const d = json.data;
                const eqStr = `$${parseFloat(d.total_equity).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
                navEquity.textContent = eqStr;
                portBalance.textContent = `$${parseFloat(d.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
                portEquity.textContent = eqStr;
                portPosCount.textContent = d.positions.length;

                if (d.positions.length > 0) {
                    tbody.innerHTML = d.positions.map(p => `
                        <tr>
                            <td><strong>${p.symbol}</strong></td>
                            <td><span class="tag ${p.side === 'LONG' ? '' : 'purple'}">${p.side}</span></td>
                            <td>${p.quantity}</td>
                            <td>$${parseFloat(p.entry_price).toFixed(2)}</td>
                            <td style="color: ${p.unrealized_pnl >= 0 ? 'var(--success-green)' : 'var(--danger-red)'}; font-weight: 700;">
                                $${parseFloat(p.unrealized_pnl).toFixed(2)} (${(parseFloat(p.unrealized_pnl_percentage) * 100).toFixed(2)}%)
                            </td>
                            <td><button class="btn-refresh" style="font-size: 0.75rem;">Close</button></td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No open trading positions. Risk bounds protected.</td></tr>';
                }
            }
        } catch (err) {
            console.log('Syncing in local offline mode');
        }
    }

    btnRefresh.addEventListener('click', sync);
    sync();
}

function initBacktestStudio() {
    const form = document.getElementById('backtest-form');
    const resultsArea = document.getElementById('analytics-results');
    const btnRun = document.getElementById('btn-run-bt');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        btnRun.disabled = true;
        btnRun.textContent = '⏳ Executing Simulation...';

        const formData = new FormData(form);
        const payload = {
            symbol: formData.get('symbol'),
            strategy_name: formData.get('strategy_name'),
            initial_equity: parseFloat(formData.get('initial_equity') || '10000'),
            timeframe: '1m',
        };

        try {
            const res = await fetch('/api/v1/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const json = await res.json();
            if (json.status === 'success' && json.data) {
                const m = json.data.metrics;
                resultsArea.innerHTML = `
                    <div style="width: 100%;">
                        <h3 style="margin-bottom: 1rem; font-family: var(--font-heading); color: var(--accent-cyan);">📊 Quantitative Simulation Report</h3>
                        <div class="metrics-grid">
                            <div class="metric-box">
                                <span class="m-lbl">Total Return</span>
                                <span class="m-val" style="color: ${m.total_return_percentage >= 0 ? 'var(--success-green)' : 'var(--danger-red)'};">
                                    ${(parseFloat(m.total_return_percentage) * 100).toFixed(2)}%
                                </span>
                            </div>
                            <div class="metric-box">
                                <span class="m-lbl">Win Rate</span>
                                <span class="m-val">${(parseFloat(m.win_rate) * 100).toFixed(2)}%</span>
                            </div>
                            <div class="metric-box">
                                <span class="m-lbl">Sharpe Ratio</span>
                                <span class="m-val">${parseFloat(m.sharpe_ratio).toFixed(2)}</span>
                            </div>
                            <div class="metric-box">
                                <span class="m-lbl">Profit Factor</span>
                                <span class="m-val">${parseFloat(m.profit_factor).toFixed(2)}</span>
                            </div>
                            <div class="metric-box">
                                <span class="m-lbl">Max Drawdown</span>
                                <span class="m-val" style="color: var(--danger-red);">${(parseFloat(m.max_drawdown_percentage) * 100).toFixed(2)}%</span>
                            </div>
                            <div class="metric-box">
                                <span class="m-lbl">Total Trades</span>
                                <span class="m-val">${m.total_trades}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
        } catch (err) {
            resultsArea.innerHTML = '<div style="color: var(--danger-red);">Error communicating with API Gateway server.</div>';
        } finally {
            btnRun.disabled = false;
            btnRun.textContent = '🚀 Execute Simulation';
        }
    });
}
