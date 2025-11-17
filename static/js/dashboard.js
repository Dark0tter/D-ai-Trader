// Dashboard JavaScript - Real-time updates
let portfolioChart = null;
let botState = {};

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

// Load bot state and initialize controls
async function loadBotState() {
    try {
        const response = await fetch('/api/bot-state');
        const data = await response.json();
        
        if (data.success) {
            botState = data.state;
            updateControlsUI();
        }
    } catch (error) {
        console.error('Error loading bot state:', error);
    }
}

// Update controls UI based on state
function updateControlsUI() {
    // Safe Mode
    document.getElementById('toggle-safe-mode').checked = botState.safe_mode;
    document.getElementById('safe-mode-status').textContent = botState.safe_mode ? 'Enabled' : 'Disabled';
    document.getElementById('safe-mode-status').classList.toggle('active', botState.safe_mode);
    
    // Bot Running
    document.getElementById('toggle-bot').checked = botState.bot_running;
    document.getElementById('bot-status').textContent = botState.bot_running ? 'Running' : 'Stopped';
    document.getElementById('bot-status').classList.toggle('active', botState.bot_running);
    
    // Risk Level
    document.getElementById('risk-level').value = botState.risk_level || 'moderate';
    updateRiskBreakdown(botState.risk_level || 'moderate');
    
    // AI Learning
    document.getElementById('toggle-learning').checked = botState.ai_learning;
    document.getElementById('learning-status').textContent = botState.ai_learning ? 'Active' : 'Paused';
    document.getElementById('learning-status').classList.toggle('active', botState.ai_learning);
    
    // Alerts
    document.getElementById('toggle-alerts').checked = botState.alerts;
    document.getElementById('alerts-status').textContent = botState.alerts ? 'Enabled' : 'Disabled';
    document.getElementById('alerts-status').classList.toggle('active', botState.alerts);
}

// Update risk breakdown visualization
function updateRiskBreakdown(level) {
    let high, medium, low;
    
    switch(level) {
        case 'conservative':
            high = 10; medium = 20; low = 70;
            break;
        case 'aggressive':
            high = 40; medium = 35; low = 25;
            break;
        default: // moderate
            high = 20; medium = 30; low = 50;
    }
    
    document.getElementById('risk-high').textContent = high + '%';
    document.getElementById('risk-medium').textContent = medium + '%';
    document.getElementById('risk-low').textContent = low + '%';
    
    document.querySelector('.progress.high').style.width = high + '%';
    document.querySelector('.progress.medium').style.width = medium + '%';
    document.querySelector('.progress.low').style.width = low + '%';
}

// Update bot state on server
async function updateBotState(updates) {
    try {
        const response = await fetch('/api/bot-state', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });
        
        const data = await response.json();
        
        if (data.success) {
            botState = data.state;
            showNotification('Settings updated successfully', 'success');
        } else {
            showNotification('Error updating settings: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error updating bot state:', error);
        showNotification('Error updating settings', 'error');
    }
}

// Show notification
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        z-index: 10000;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Initialize control event listeners
function initializeControls() {
    // Safe Mode Toggle
    document.getElementById('toggle-safe-mode').addEventListener('change', (e) => {
        updateBotState({ safe_mode: e.target.checked });
        updateSafeModeInfo();
    });
    
    // Bot Running Toggle
    document.getElementById('toggle-bot').addEventListener('change', (e) => {
        if (!e.target.checked) {
            if (!confirm('Are you sure you want to stop the trading bot?')) {
                e.target.checked = true;
                return;
            }
        }
        updateBotState({ bot_running: e.target.checked });
    });
    
    // Risk Level Select
    document.getElementById('risk-level').addEventListener('change', (e) => {
        updateBotState({ risk_level: e.target.value });
        updateRiskBreakdown(e.target.value);
    });
    
    // AI Learning Toggle
    document.getElementById('toggle-learning').addEventListener('change', (e) => {
        updateBotState({ ai_learning: e.target.checked });
    });
    
    // Alerts Toggle
    document.getElementById('toggle-alerts').addEventListener('change', (e) => {
        updateBotState({ alerts: e.target.checked });
    });
    
    // Emergency Stop
    document.getElementById('emergency-stop').addEventListener('click', async () => {
        if (!confirm('⚠️ EMERGENCY STOP\n\nThis will immediately:\n• Close all open positions\n• Halt the trading bot\n\nAre you sure?')) {
            return;
        }
        
        if (!confirm('This action cannot be undone. Proceed with emergency stop?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/emergency-stop', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                showNotification('Emergency stop executed', 'success');
                await loadBotState();
                await loadData();
            } else {
                showNotification('Error: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error executing emergency stop:', error);
            showNotification('Error executing emergency stop', 'error');
        }
    });
}

// Update safe mode info display
async function updateSafeModeInfo() {
    try {
        const response = await fetch('/api/safe-mode-status');
        const data = await response.json();
        
        if (data.success && data.safe_mode) {
            const sm = data.safe_mode;
            const infoDiv = document.getElementById('safe-mode-info');
            
            let statusColor = '#10b981'; // green
            if (sm.danger_score >= 80) statusColor = '#dc2626';
            else if (sm.danger_score >= 60) statusColor = '#f59e0b';
            else if (sm.danger_score >= 40) statusColor = '#f97316';
            
            infoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span>Danger Score:</span>
                    <strong style="color: ${statusColor}">${sm.danger_score}/100</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Status:</span>
                    <strong>${sm.status}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Capital Multiplier:</span>
                    <strong>${(sm.risk_reduction * 100).toFixed(0)}%</strong>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error updating safe mode info:', error);
    }
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

// CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Load bot state and initialize controls
    loadBotState();
    initializeControls();
    
    // Initial data load
    fetchAllData();
    
    // Update safe mode info
    updateSafeModeInfo();
    
    // Auto-refresh every 10 seconds
    setInterval(fetchAllData, 10000);
    
    // Update safe mode info every 30 seconds
    setInterval(updateSafeModeInfo, 30000);
});
