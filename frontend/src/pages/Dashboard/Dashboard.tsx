import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../../store/store';
import {
  fetchActiveSessions,
  fetchOpenTrades,
  setConnectionStatus,
} from '../../store/slices/tradingSlice';
import TradingChart from '../../components/Charts/TradingChart';
import PerformanceMetrics from '../../components/Metrics/PerformanceMetrics';
import TradesList from '../../components/Trading/TradesList';
import PortfolioSummary from '../../components/Portfolio/PortfolioSummary';
import MarketOverview from '../../components/Market/MarketOverview';
import RealTimeUpdates from '../../components/RealTime/RealTimeUpdates';

const DashboardContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: auto auto auto auto;
  gap: 20px;
  padding: 20px;
  height: 100vh;
  overflow-y: auto;
  background: ${props => props.theme.colors.background};
`;

const DashboardCard = styled.div`
  background: ${props => props.theme.colors.cardBackground};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  
  &.full-width {
    grid-column: 1 / -1;
  }
  
  &.half-width {
    grid-column: span 2;
  }
`;

const CardTitle = styled.h3`
  color: ${props => props.theme.colors.text};
  margin: 0 0 15px 0;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const StatusIndicator = styled.div<{ status: 'connected' | 'disconnected' | 'connecting' }>`
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: ${props => {
    switch (props.status) {
      case 'connected': return '#4CAF50';
      case 'disconnected': return '#F44336';
      case 'connecting': return '#FF9800';
      default: return '#9E9E9E';
    }
  }};
  animation: ${props => props.status === 'connecting' ? 'pulse 1.5s infinite' : 'none'};
  
  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const QuickStats = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
`;

const StatCard = styled.div`
  background: ${props => props.theme.colors.surface};
  padding: 15px;
  border-radius: 6px;
  text-align: center;
  border: 1px solid ${props => props.theme.colors.border};
`;

const StatValue = styled.div`
  font-size: 24px;
  font-weight: bold;
  color: ${props => props.theme.colors.primary};
  margin-bottom: 5px;
`;

const StatLabel = styled.div`
  font-size: 12px;
  color: ${props => props.theme.colors.textSecondary};
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    activeSessions,
    openTrades,
    performance,
    isConnected,
    loading,
    error,
  } = useSelector((state: RootState) => state.trading);

  const [connectionStatus, setConnectionStatusLocal] = useState<'connected' | 'disconnected' | 'connecting'>('connecting');

  useEffect(() => {
    // Initialize dashboard data
    dispatch(fetchActiveSessions());
    dispatch(fetchOpenTrades());

    // Set up WebSocket connection for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      setConnectionStatusLocal('connected');
      dispatch(setConnectionStatus(true));
    };
    
    ws.onclose = () => {
      setConnectionStatusLocal('disconnected');
      dispatch(setConnectionStatus(false));
    };
    
    ws.onerror = () => {
      setConnectionStatusLocal('disconnected');
      dispatch(setConnectionStatus(false));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Handle real-time updates based on message type
        console.log('WebSocket message:', data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    // Cleanup WebSocket on unmount
    return () => {
      ws.close();
    };
  }, [dispatch]);

  // Calculate quick stats
  const totalSessions = activeSessions.length;
  const totalOpenTrades = openTrades.length;
  const totalPnL = performance?.total_pnl || 0;
  const winRate = performance?.win_rate || 0;

  return (
    <DashboardContainer>
      {/* Header with connection status */}
      <DashboardCard className="full-width">
        <CardTitle>
          Trading Dashboard
          <StatusIndicator status={connectionStatus} />
          <span style={{ fontSize: '14px', color: '#666' }}>
            {connectionStatus === 'connected' ? 'Live' : 
             connectionStatus === 'connecting' ? 'Connecting...' : 'Offline'}
          </span>
        </CardTitle>
        
        <QuickStats>
          <StatCard>
            <StatValue>{totalSessions}</StatValue>
            <StatLabel>Active Sessions</StatLabel>
          </StatCard>
          <StatCard>
            <StatValue>{totalOpenTrades}</StatValue>
            <StatLabel>Open Trades</StatLabel>
          </StatCard>
          <StatCard>
            <StatValue style={{ color: totalPnL >= 0 ? '#4CAF50' : '#F44336' }}>
              ${totalPnL.toFixed(2)}
            </StatValue>
            <StatLabel>Total P&L</StatLabel>
          </StatCard>
          <StatCard>
            <StatValue>{winRate.toFixed(1)}%</StatValue>
            <StatLabel>Win Rate</StatLabel>
          </StatCard>
        </QuickStats>
      </DashboardCard>

      {/* Main Trading Chart */}
      <DashboardCard className="half-width">
        <CardTitle>EUR/USD - 1M Chart</CardTitle>
        <TradingChart 
          symbol="EUR_USD" 
          timeframe="1m" 
          height={300}
          showTrades={true}
        />
      </DashboardCard>

      {/* Portfolio Summary */}
      <DashboardCard>
        <CardTitle>Portfolio Summary</CardTitle>
        <PortfolioSummary />
      </DashboardCard>

      {/* Performance Metrics */}
      <DashboardCard>
        <CardTitle>Performance Metrics</CardTitle>
        <PerformanceMetrics />
      </DashboardCard>

      {/* Market Overview */}
      <DashboardCard>
        <CardTitle>Market Overview</CardTitle>
        <MarketOverview />
      </DashboardCard>

      {/* Real-time Updates */}
      <DashboardCard>
        <CardTitle>Real-time Updates</CardTitle>
        <RealTimeUpdates />
      </DashboardCard>

      {/* Recent Trades */}
      <DashboardCard className="full-width">
        <CardTitle>Recent Trades</CardTitle>
        <TradesList 
          trades={openTrades.slice(0, 10)} 
          showPagination={false}
          compact={true}
        />
      </DashboardCard>
    </DashboardContainer>
  );
};

export default Dashboard;