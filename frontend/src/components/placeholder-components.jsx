import React from 'react';
import styled from 'styled-components';

const PlaceholderContainer = styled.div`
  padding: 20px;
  background: ${props => props.theme.colors.surface};
  border-radius: 8px;
  text-align: center;
  color: ${props => props.theme.colors.textSecondary};
`;

// Performance Metrics Component
export const PerformanceMetrics = () => (
  <PlaceholderContainer>
    <h4>Performance Metrics</h4>
    <div style={{ marginTop: '10px' }}>
      <div>Total Return: +12.5%</div>
      <div>Sharpe Ratio: 1.8</div>
      <div>Max Drawdown: -5.2%</div>
      <div>Win Rate: 68%</div>
    </div>
  </PlaceholderContainer>
);

// Trades List Component
export const TradesList = ({ trades = [], showPagination = true, compact = false }) => (
  <PlaceholderContainer>
    <h4>Recent Trades</h4>
    <div style={{ marginTop: '10px' }}>
      {trades.length > 0 ? (
        trades.map((trade, index) => (
          <div key={index} style={{ marginBottom: '5px' }}>
            {trade.symbol} - {trade.side} - ${trade.pnl?.toFixed(2) || '0.00'}
          </div>
        ))
      ) : (
        <div>No trades available</div>
      )}
    </div>
  </PlaceholderContainer>
);

// Portfolio Summary Component
export const PortfolioSummary = () => (
  <PlaceholderContainer>
    <h4>Portfolio Summary</h4>
    <div style={{ marginTop: '10px' }}>
      <div>Total Value: $102,500.00</div>
      <div>Cash: $25,000.00</div>
      <div>P&L: +$2,500.00</div>
      <div>Open Positions: 3</div>
    </div>
  </PlaceholderContainer>
);

// Market Overview Component
export const MarketOverview = () => (
  <PlaceholderContainer>
    <h4>Market Overview</h4>
    <div style={{ marginTop: '10px' }}>
      <div>EUR/USD: 1.1234 (+0.15%)</div>
      <div>GBP/USD: 1.2567 (-0.08%)</div>
      <div>USD/JPY: 149.85 (+0.22%)</div>
      <div>Market Status: Open</div>
    </div>
  </PlaceholderContainer>
);

// Real-time Updates Component
export const RealTimeUpdates = () => (
  <PlaceholderContainer>
    <h4>Real-time Updates</h4>
    <div style={{ marginTop: '10px' }}>
      <div>🟢 Connected to live feed</div>
      <div>📈 New signal: EUR/USD BUY</div>
      <div>💰 Trade closed: +15.5 pips</div>
      <div>⚡ Last update: Just now</div>
    </div>
  </PlaceholderContainer>
);

// Page Components
export const LiveTrading = () => (
  <div style={{ padding: '20px' }}>
    <h1>Live Trading</h1>
    <PlaceholderContainer>
      Live trading interface will be implemented here.
      This page will show real-time trading controls and monitoring.
    </PlaceholderContainer>
  </div>
);

export const Backtesting = () => (
  <div style={{ padding: '20px' }}>
    <h1>Backtesting</h1>
    <PlaceholderContainer>
      Backtesting interface will be implemented here.
      This page will allow users to run historical strategy tests.
    </PlaceholderContainer>
  </div>
);

export const Strategies = () => (
  <div style={{ padding: '20px' }}>
    <h1>Strategies</h1>
    <PlaceholderContainer>
      Strategy management interface will be implemented here.
      This page will show available strategies and their configurations.
    </PlaceholderContainer>
  </div>
);

export const Analytics = () => (
  <div style={{ padding: '20px' }}>
    <h1>Analytics</h1>
    <PlaceholderContainer>
      Analytics dashboard will be implemented here.
      This page will show detailed performance analysis and reports.
    </PlaceholderContainer>
  </div>
);

export const Settings = () => (
  <div style={{ padding: '20px' }}>
    <h1>Settings</h1>
    <PlaceholderContainer>
      Settings interface will be implemented here.
      This page will allow users to configure system preferences.
    </PlaceholderContainer>
  </div>
);