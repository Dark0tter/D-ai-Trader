// Dashboard JavaScript - Real-time updates
let portfolioChart = null;

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Format percentage
function formatPercent(value) {
    return (value * 100).toFixed(2) + '%';
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Update account overview
function updateAccountOverview(data) {
    document.getElementById('portfolio-value').textContent = formatCurrency(data.account.portfolio_value);
    document.getElementById('cash-value').textContent = formatCurrency(data.account.cash);
    document.getElementById('buying-power').textContent = formatCurrency(data.account.buying_power);
    document.getElementById('position-count').textContent = data.positions.length;
    
    // Update config
    document.getElementById('trading-mode').textContent = data.trading_mode.toUpperCase();
    document.getElementById('strategy').textContent = data.strategy;
    document.getElementById('watchlist').textContent = data.watchlist.join(', ');
}

// Update positions table
function updatePositions(positions) {
    const tbody = document.getElementById('positions-body');
    
    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No open positions</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => `
        <tr>
            <td><strong>${pos.symbol}</strong></td>
            <td>${pos.qty}</td>
            <td>${formatCurrency(pos.avg_entry_price)}</td>
            <td>${formatCurrency(pos.current_price)}</td>
            <td>${formatCurrency(pos.market_value)}</td>
            <td class="${pos.unrealized_pl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${formatCurrency(pos.unrealized_pl)}
            </td>
            <td class="${pos.unrealized_plpc >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${formatPercent(pos.unrealized_plpc)}
            </td>
        </tr>
    `).join('');
}

// Update trades table
function updateTrades(trades) {
    const tbody = document.getElementById('trades-body');
    
    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">No trades yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = trades.slice(0, 20).map(trade => `
        <tr>
            <td>${formatDate(trade.entry_date)}</td>
            <td><strong>${trade.symbol}</strong></td>
            <td>${trade.side}</td>
            <td>${trade.quantity}</td>
            <td>${formatCurrency(trade.entry_price)}</td>
            <td>${trade.exit_price ? formatCurrency(trade.exit_price) : '--'}</td>
            <td class="${trade.pnl && trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${trade.pnl ? formatCurrency(trade.pnl) : '--'}
            </td>
            <td><span class="status-badge status-${trade.status.toLowerCase()}">${trade.status}</span></td>
        </tr>
    `).join('');
}

// Update performance metrics
function updatePerformance(data) {
    const metrics = data.metrics;
    
    document.getElementById('total-trades').textContent = metrics.total_trades;
    document.getElementById('winning-trades').textContent = metrics.winning_trades;
    document.getElementById('losing-trades').textContent = metrics.losing_trades;
    document.getElementById('win-rate').textContent = metrics.win_rate.toFixed(1) + '%';
    
    const totalPnlEl = document.getElementById('total-pnl');
    totalPnlEl.textContent = formatCurrency(metrics.total_pnl);
    totalPnlEl.className = 'card-value ' + (metrics.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative');
    
    const avgPnlEl = document.getElementById('avg-pnl');
    avgPnlEl.textContent = formatCurrency(metrics.avg_pnl);
    avgPnlEl.className = 'card-value ' + (metrics.avg_pnl >= 0 ? 'pnl-positive' : 'pnl-negative');
    
    // Update chart
    updatePortfolioChart(data.portfolio_history, metrics.initial_capital);
}

// Update AI stats
function updateAIStats(data) {
    const stats = data.ai_stats;
    
    document.getElementById('states-learned').textContent = stats.states_learned;
    document.getElementById('ai-win-rate').textContent = stats.win_rate.toFixed(1) + '%';
    document.getElementById('avg-reward').textContent = stats.avg_reward.toFixed(3);
    document.getElementById('exploration-rate').textContent = (stats.exploration_rate * 100).toFixed(1) + '%';
}

// Update portfolio chart
function updatePortfolioChart(history, initialCapital) {
    const ctx = document.getElementById('portfolio-chart');
    
    if (!ctx) return;
    
    if (portfolioChart) {
        portfolioChart.destroy();
    }
    
    const labels = history.map(h => new Date(h.timestamp).toLocaleDateString());
    const values = history.map(h => h.total_value);
    
    portfolioChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Portfolio Value',
                data: values,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }, {
                label: 'Initial Capital',
                data: Array(labels.length).fill(initialCapital),
                borderColor: '#94a3b8',
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

// Update logs
function updateLogs(logs) {
    const container = document.getElementById('logs-container');
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="log-entry">No logs available</div>';
        return;
    }
    
    container.innerHTML = logs.slice(-50).reverse().map(log => {
        let className = 'log-entry';
        if (log.includes('ERROR')) className += ' error';
        else if (log.includes('WARNING')) className += ' warning';
        else if (log.includes('INFO')) className += ' info';
        
        return `<div class="${className}">${escapeHtml(log)}</div>`;
    }).join('');
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Update last update time
function updateLastUpdateTime() {
    const now = new Date();
    document.getElementById('last-update').textContent = 
        `Last updated: ${now.toLocaleTimeString()}`;
}

// Fetch all data
async function fetchAllData() {
    try {
        // Fetch status
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        
        if (statusData.success) {
            updateAccountOverview(statusData);
            updatePositions(statusData.positions);
        }
        
        // Fetch trades
        const tradesRes = await fetch('/api/trades');
        const tradesData = await tradesRes.json();
        
        if (tradesData.success) {
            updateTrades(tradesData.trades);
        }
        
        // Fetch performance
        const perfRes = await fetch('/api/performance');
        const perfData = await perfRes.json();
        
        if (perfData.success) {
            updatePerformance(perfData);
        }
        
        // Fetch AI stats
        const aiRes = await fetch('/api/ai-stats');
        const aiData = await aiRes.json();
        
        if (aiData.success) {
            updateAIStats(aiData);
        }
        
        // Fetch logs
        const logsRes = await fetch('/api/logs');
        const logsData = await logsRes.json();
        
        if (logsData.success) {
            updateLogs(logsData.logs);
        }
        
        updateLastUpdateTime();
        
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Initial load
    fetchAllData();
    
    // Auto-refresh every 10 seconds
    setInterval(fetchAllData, 10000);
});
