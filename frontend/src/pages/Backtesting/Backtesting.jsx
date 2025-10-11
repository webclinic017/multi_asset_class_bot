import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import RealTimeLogs from '../../components/Logs/RealTimeLogs';

const BacktestingContainer = styled.div`
  padding: 20px;
  color: ${props => props.theme.colors.text};
`;

const MainContent = styled.div`
  display: grid;
  grid-template-columns: 3fr 1fr;
  gap: 24px;
`;

const LeftColumn = styled.div``;

const RightColumn = styled.div``;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
`;

const Title = styled.h1`
  color: ${props => props.theme.colors.text};
  margin: 0;
  font-size: 28px;
  font-weight: 600;
`;

const Card = styled.div`
  background: ${props => props.theme.colors.surface};
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid ${props => props.theme.colors.border};
`;

const CardTitle = styled.h3`
  color: ${props => props.theme.colors.text};
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
`;

const FormGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 14px;
  margin-bottom: 6px;
  font-weight: 500;
`;

const Input = styled.input`
  background: ${props => props.theme.colors.background};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 10px 12px;
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
  }
`;

const Select = styled.select`
  background: ${props => props.theme.colors.background};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 10px 12px;
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
  }
`;

const Button = styled.button`
  background: ${props => props.theme.colors.primary};
  color: white;
  border: none;
  border-radius: 6px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: ${props => props.theme.colors.primaryHover};
  }
  
  &:disabled {
    background: ${props => props.theme.colors.textSecondary};
    cursor: not-allowed;
  }
`;

const DataGrid = styled.div`
  background: ${props => props.theme.colors.surface};
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid ${props => props.theme.colors.border};
`;

const DataGridHeader = styled.div`
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 1.2fr 1fr 1fr 1fr 0.8fr 0.8fr 0.8fr 1fr 0.8fr;
  background: ${props => props.theme.colors.background};
  padding: 12px;
  font-weight: 600;
  color: ${props => props.theme.colors.text};
  border-bottom: 1px solid ${props => props.theme.colors.border};
`;

const DataGridRow = styled.div`
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 1.2fr 1fr 1fr 1fr 0.8fr 0.8fr 0.8fr 1fr 0.8fr;
  padding: 12px;
  border-bottom: 1px solid ${props => props.theme.colors.border};
  color: ${props => props.theme.colors.text};
  
  &:hover {
    background: ${props => props.theme.colors.background};
  }
  
  &:last-child {
    border-bottom: none;
  }
`;

const StatusBadge = styled.span`
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  
  &.completed {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
  
  &.running {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }
  
  &.failed {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
`;

const MetricsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-top: 20px;
`;

const MetricCard = styled.div`
  background: ${props => props.theme.colors.background};
  padding: 16px;
  border-radius: 8px;
  text-align: center;
`;

const MetricValue = styled.div`
  font-size: 24px;
  font-weight: 700;
  color: ${props => props.theme.colors.primary};
  margin-bottom: 4px;
`;

const MetricLabel = styled.div`
  font-size: 12px;
  color: ${props => props.theme.colors.textSecondary};
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const Backtesting = () => {
  const [sessions, setSessions] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [sessionStatus, setSessionStatus] = useState({});
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [formData, setFormData] = useState({
    strategy_id: '',
    symbol: 'EUR_USD',
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    initial_capital: 100000,
    timeframe: '1m'
  });

  useEffect(() => {
    fetchSessions();
    fetchStrategies();
    setupWebSocket();
    
    // Cleanup WebSocket on unmount
    return () => {
      if (window.backtestWs) {
        window.backtestWs.close();
      }
    };
  }, []);

  const setupWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      console.log('Attempting WebSocket connection to:', wsUrl);
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
         if (data.type === 'backtest_completed' || data.type === 'backtest_failed') {
           console.log('Backtest status update received, refreshing sessions...');
           // Refresh sessions when backtest completes
           setTimeout(fetchSessions, 1000);
         } else if (data.type === 'backtest_status') {
           setSessionStatus(prevStatus => ({
             ...prevStatus,
             [data.session_id]: data.status,
           }));
         }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setWsConnected(false);
        // Attempt to reconnect after 5 seconds
        setTimeout(setupWebSocket, 5000);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };
      
      window.backtestWs = ws;
    } catch (error) {
      console.error('Failed to setup WebSocket:', error);
    }
  };

  const fetchSessions = async () => {
    try {
      // Add cache-busting parameter to ensure fresh data
      const timestamp = new Date().getTime();
      const response = await axios.get(`/api/sessions?_t=${timestamp}`);
      console.log('=== API RESPONSE DEBUG ===');
      console.log('Full response data:', response.data);
      const backtestSessions = response.data
        .filter((session) => session.session_type === 'backtest')
        .map(session => ({
          ...session,
          total_return: session.total_return || 0,
          final_capital: session.final_capital || session.initial_capital,
          winning_trades: session.winning_trades || 0,
          losing_trades: session.losing_trades || 0,
          total_trades: session.total_trades || 0,
        }));
      
      console.log('Processed backtest sessions:', backtestSessions);

      setSessions(backtestSessions);
    } catch (error) {
      console.error('Error fetching sessions:', error);
      alert('Failed to fetch backtest sessions. Please check if the backend server is running.');
    }
  };

  const fetchStrategies = async () => {
    try {
      const response = await axios.get('/api/strategies');
      setStrategies(response.data);
    } catch (error) {
      console.error('Error fetching strategies:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'initial_capital' ? parseFloat(value) : value
    }));
    
    // Reset strategy selection when symbol changes
    if (name === 'symbol') {
      setFormData(prev => ({
        ...prev,
        strategy_id: ''
      }));
    }
  };

  const getCompatibleStrategies = () => {
    const selectedSymbol = formData.symbol;

    return strategies.filter(strategy => {
      const strategyName = strategy.name.toLowerCase();
      const selectedSymbolFormatted = selectedSymbol.replace('_', '/').toLowerCase();
      const selectedSymbolUnderscore = selectedSymbol.toLowerCase();

      // HFT strategies are compatible with all symbols
      if (strategy.strategy_type === 'hft') {
        return true;
      }

      // Check if strategy name contains the selected symbol
      return strategyName.includes(selectedSymbolFormatted) ||
             strategyName.includes(selectedSymbolUnderscore) ||
             strategyName.includes(selectedSymbol.toLowerCase());
    });
  };

  const handleRunBacktest = async () => {
    if (!formData.strategy_id) {
      alert('Please select a strategy');
      return;
    }

    setLoading(true);
    try {
      console.log('Starting backtest with data:', formData);
      const response = await axios.post('/api/backtest', formData);
      console.log('Backtest response:', response.data);
      
      alert(`✅ Real backtest started successfully!\n\nSession ID: ${response.data.session_id}\n\nUsing: ${response.data.note}\n\nResults will appear below when completed.`);
      
      // Refresh sessions immediately to show the new running session
      setTimeout(() => {
        fetchSessions();
      }, 1000);
    } catch (error) {
      console.error('Error running backtest:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Error starting backtest';
      alert(`❌ Backtest Error:\n\n${errorMessage}\n\nPlease check:\n- Backend server is running\n- Database connection is working\n- Market data exists for selected symbol`);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'Running...';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  return (
    <BacktestingContainer>
      <Header>
        <div>
          <Title>Backtesting</Title>
          <div style={{ fontSize: '12px', color: wsConnected ? '#22c55e' : '#ef4444', marginTop: '8px' }}>
            WebSocket: {wsConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <Button onClick={fetchSessions} style={{ padding: '8px 16px', fontSize: '13px' }}>
          🔄 Refresh Results
        </Button>
      </Header>

      <Card>
        <CardTitle>🚀 Run Real Backtest (GPU/Backtrader Engines) - <span style={{color: '#22c55e', fontWeight: 'bold'}}>$100,000 Initial Capital</span></CardTitle>
        <FormGrid>
          <FormGroup>
            <Label>Strategy</Label>
            <Select
              name="strategy_id"
              value={formData.strategy_id}
              onChange={handleInputChange}
            >
              <option value="">Select Strategy</option>
              {getCompatibleStrategies().map(strategy => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name} ({strategy.timeframe}) - {strategy.asset_class.toUpperCase()}
                </option>
              ))}
            </Select>
          </FormGroup>
          
          <FormGroup>
            <Label>Symbol</Label>
            <Select
              name="symbol"
              value={formData.symbol}
              onChange={handleInputChange}
            >
              {/* Forex Pairs */}
              <option value="EUR_USD">EUR/USD (Forex)</option>
              <option value="GBP_USD">GBP/USD (Forex)</option>
              <option value="USD_JPY">USD/JPY (Forex)</option>
              <option value="AUD_USD">AUD/USD (Forex)</option>
              <option value="USDCAD">USD/CAD (Forex)</option>
              <option value="USDCHF">USD/CHF (Forex)</option>
              <option value="NZDUSD">NZD/USD (Forex)</option>

              {/* Crypto */}
              <option value="BTC_USD">BTC/USD (Crypto)</option>
              <option value="ETH_USD">ETH/USD (Crypto)</option>
              <option value="SOL_USD">SOL/USD (Crypto)</option>

              {/* Futures - Energy */}
              <option value="WTI_CRUDE_OIL">WTI Crude Oil (Futures)</option>
              <option value="BRENT_CRUDE_OIL">Brent Crude Oil (Futures)</option>
              <option value="NATURAL_GAS">Natural Gas (Futures)</option>

              {/* Futures - Metals */}
              <option value="GOLD">Gold (Futures)</option>
              <option value="SILVER">Silver (Futures)</option>
              <option value="COPPER">Copper (Futures)</option>
              <option value="PLATINUM">Platinum (Futures)</option>
              <option value="PALLADIUM">Palladium (Futures)</option>

              {/* Futures - Agriculture */}
              <option value="CORN">Corn (Futures)</option>
              <option value="WHEAT">Wheat (Futures)</option>
              <option value="SOYBEANS">Soybeans (Futures)</option>
              <option value="COFFEE">Coffee (Futures)</option>
              <option value="COTTON">Cotton (Futures)</option>
              <option value="SUGAR">Sugar (Futures)</option>

              {/* Futures - Livestock */}
              <option value="LIVE_CATTLE">Live Cattle (Futures)</option>
              <option value="FEEDER_CATTLE">Feeder Cattle (Futures)</option>
              <option value="LEAN_HOGS">Lean Hogs (Futures)</option>

              {/* Futures - Financial */}
              <option value="E_MINI_S&P">E-mini S&P 500 (Futures)</option>
              <option value="E_MINI_NASDAQ">E-mini Nasdaq-100 (Futures)</option>
              <option value="E_MINI_RUSSELL">E-mini Russell 2000 (Futures)</option>
              <option value="E_MINI_DOW">E-mini Dow Jones (Futures)</option>
              <option value="T_BOND">30-Year T-Bond (Futures)</option>
              <option value="T_NOTE">10-Year T-Note (Futures)</option>
              <option value="FIVE_YEAR">5-Year T-Note (Futures)</option>
              <option value="TWO_YEAR">2-Year T-Note (Futures)</option>

              {/* Currency Futures */}
              <option value="EURO_FX">Euro FX (Futures)</option>
              <option value="BRITISH_POUND">British Pound (Futures)</option>
              <option value="JAPANESE_YEN">Japanese Yen (Futures)</option>
              <option value="AUSTRALIAN_DOLLAR">Australian Dollar (Futures)</option>
              <option value="CANADIAN_DOLLAR">Canadian Dollar (Futures)</option>
              <option value="NEW_ZEALAND_DOLLAR">New Zealand Dollar (Futures)</option>
              <option value="SWISS_FRANC">Swiss Franc (Futures)</option>
            </Select>
          </FormGroup>
          
          <FormGroup>
            <Label>Start Date</Label>
            <Input
              type="date"
              name="start_date"
              value={formData.start_date}
              onChange={handleInputChange}
            />
          </FormGroup>
          
          <FormGroup>
            <Label>End Date</Label>
            <Input
              type="date"
              name="end_date"
              value={formData.end_date}
              onChange={handleInputChange}
            />
          </FormGroup>
          
          <FormGroup>
            <Label>Initial Capital</Label>
            <Input
              type="number"
              name="initial_capital"
              value={formData.initial_capital}
              onChange={handleInputChange}
              min="1000"
              step="1000"
            />
          </FormGroup>
          
          <FormGroup>
            <Label>Timeframe</Label>
            <Select
              name="timeframe"
              value={formData.timeframe}
              onChange={handleInputChange}
            >
              <option value="1m">1 Minute</option>
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="1d">1 Day</option>
            </Select>
          </FormGroup>
        </FormGrid>
        
        <Button onClick={handleRunBacktest} disabled={loading}>
          {loading ? '⚡ Running Real Backtest...' : '🚀 Run Real Backtest (No Simulation)'}
        </Button>
      </Card>

      <MainContent>
        <LeftColumn>
          <Card>
            <CardTitle>Backtest Results</CardTitle>
            {sessions.length > 0 && (
              <MetricsGrid>
                <MetricCard>
                  <MetricValue>{sessions.length}</MetricValue>
                  <MetricLabel>Total Backtests</MetricLabel>
                </MetricCard>
                <MetricCard>
                  <MetricValue>
                    {sessions.filter(s => s.status === 'completed').length}
                  </MetricValue>
                  <MetricLabel>Completed</MetricLabel>
                </MetricCard>
                <MetricCard>
                  <MetricValue>
                    {sessions.filter(s => (s.total_return || 0) > 0).length}
                  </MetricValue>
                  <MetricLabel>Profitable</MetricLabel>
                </MetricCard>
                <MetricCard>
                  <MetricValue>
                    {sessions.reduce((sum, s) => sum + (s.total_trades || 0), 0)}
                  </MetricValue>
                  <MetricLabel>Total Trades</MetricLabel>
                </MetricCard>
                <MetricCard>
                  <MetricValue>
                    {sessions.reduce((sum, s) => sum + (s.winning_trades || 0), 0)}
                  </MetricValue>
                  <MetricLabel>Total Wins</MetricLabel>
                </MetricCard>
                <MetricCard>
                  <MetricValue>
                    {sessions.length > 0 ?
                      ((sessions.reduce((sum, s) => sum + (s.winning_trades || 0), 0) /
                        Math.max(1, sessions.reduce((sum, s) => sum + (s.total_trades || 0), 0))) * 100).toFixed(1) + '%'
                      : '0%'}
                  </MetricValue>
                  <MetricLabel>Overall Win Rate</MetricLabel>
                </MetricCard>
              </MetricsGrid>
            )}

            {sessions.length > 0 ? (
              <DataGrid style={{ marginTop: '24px' }}>
                <DataGridHeader>
                  <div>Strategy</div>
                  <div>Symbol</div>
                  <div>Period</div>
                  <div>Initial Capital</div>
                  <div>Final Capital</div>
                  <div>Return</div>
                  <div>Total Trades</div>
                  <div>Winning</div>
                  <div>Losing</div>
                  <div>Run Time</div>
                  <div>Status</div>
                </DataGridHeader>
                {sessions.map(session => (
                  <DataGridRow key={session.id}>
                    <div>{session.strategy_name}</div>
                    <div>{session.symbol}</div>
                    <div>{formatDate(session.start_time)} - {session.end_time ? formatDate(session.end_time) : 'Running'}</div>
                    <div>{formatCurrency(session.initial_capital)}</div>
                    <div>{session.final_capital ? formatCurrency(session.final_capital) : '-'}</div>
                    <div style={{ color: (session.total_return || 0) > 0 ? '#22c55e' : '#ef4444' }}>
                      {session.total_return !== null && session.total_return !== undefined ? formatPercentage(session.total_return) : '-'}
                    </div>
                    <div>{session.total_trades}</div>
                    <div style={{ color: '#22c55e' }}>{session.winning_trades}</div>
                    <div style={{ color: '#ef4444' }}>{session.losing_trades}</div>
                    <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                      {session.status === 'running' ?
                        `Started: ${formatDateTime(session.start_time)}` :
                        session.end_time ?
                          `${Math.round((new Date(session.end_time) - new Date(session.start_time)) / 1000)}s` :
                          formatDateTime(session.start_time)
                      }
                    </div>
                    <div>
                      <StatusBadge className={sessionStatus[session.id] || session.status}>
                        {sessionStatus[session.id] || session.status}
                      </StatusBadge>
                    </div>
                  </DataGridRow>
                ))}
              </DataGrid>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                📊 No backtest results yet. Run your first real backtest above to see authentic results here.
              </div>
            )}
          </Card>
        </LeftColumn>
        <RightColumn>
          <RealTimeLogs />
        </RightColumn>
      </MainContent>
    </BacktestingContainer>
  );
};

export default Backtesting;