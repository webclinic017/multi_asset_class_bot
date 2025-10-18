import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import axios from 'axios';

const BacktestingContainer = styled.div`
  padding: 20px;
  color: ${props => props.theme.colors.text};
`;

const MainContent = styled.div`
  width: 100%;
`;

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
      
      // Filter backtest sessions - backend already provides accurate data
      const backtestSessions = response.data
        .filter((session) => session.session_type === 'backtest')
        .map(session => {
          console.log(`Processing session ${session.id}:`, {
            total_trades: session.total_trades,
            winning_trades: session.winning_trades,
            losing_trades: session.losing_trades,
            final_capital: session.final_capital,
            total_return: session.total_return,
            status: session.status
          });
          
          // Use backend-calculated values directly without overriding
          // Only provide defaults for truly missing values
          const processed = {
            ...session,
            // Ensure numeric values are properly typed
            total_return: typeof session.total_return === 'number' ? session.total_return : 0,
            final_capital: typeof session.final_capital === 'number' ? session.final_capital : (session.initial_capital || 0),
            winning_trades: typeof session.winning_trades === 'number' ? session.winning_trades : 0,
            losing_trades: typeof session.losing_trades === 'number' ? session.losing_trades : 0,
            total_trades: typeof session.total_trades === 'number' ? session.total_trades : 0,
          };
          
          console.log(`Processed session ${session.id}:`, {
            total_trades: processed.total_trades,
            winning_trades: processed.winning_trades,
            losing_trades: processed.losing_trades,
            final_capital: processed.final_capital,
            total_return: processed.total_return,
            status: processed.status
          });
          
          return processed;
        });
      
      console.log('Processed backtest sessions:', backtestSessions);
      console.log('Sample session data:', backtestSessions[0]);

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
        <CardTitle>🚀 Run Real Backtest (GPU/Backtrader Engines)</CardTitle>
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

              {/* Futures - Tier 1: High Liquidity (Best for HFT) */}
              <optgroup label="🔥 Tier 1 Futures - High Liquidity (HFT Recommended)">
                <option value="ES">ES - E-mini S&P 500</option>
                <option value="NQ">NQ - E-mini NASDAQ</option>
                <option value="CL">CL - Crude Oil (WTI)</option>
                <option value="GC">GC - Gold</option>
                <option value="YM">YM - E-mini Dow</option>
              </optgroup>

              {/* Futures - Tier 2: Medium Liquidity */}
              <optgroup label="⚡ Tier 2 Futures - Medium Liquidity">
                <option value="NG">NG - Natural Gas</option>
                <option value="SI">SI - Silver</option>
                <option value="HG">HG - Copper</option>
                <option value="ZN">ZN - 10-Year T-Note</option>
                <option value="RB">RB - RBOB Gasoline</option>
                <option value="HO">HO - Heating Oil</option>
              </optgroup>

              {/* Futures - Tier 3: Specialized */}
              <optgroup label="📊 Tier 3 Futures - Specialized">
                <option value="ZC">ZC - Corn</option>
                <option value="ZS">ZS - Soybeans</option>
                <option value="ZW">ZW - Wheat</option>
              </optgroup>
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
        <Card>
          <CardTitle>📊 Backtest Results</CardTitle>
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
              {sessions.map(session => {
                // Debug log for each row render
                console.log(`Rendering row for session ${session.id}:`, {
                  total_trades: session.total_trades,
                  winning_trades: session.winning_trades,
                  losing_trades: session.losing_trades,
                  types: {
                    total_trades: typeof session.total_trades,
                    winning_trades: typeof session.winning_trades,
                    losing_trades: typeof session.losing_trades
                  }
                });
                
                return (
                  <DataGridRow key={session.id}>
                    <div>{session.strategy_name}</div>
                    <div>{session.symbol}</div>
                    <div>{formatDate(session.start_time)} - {session.end_time ? formatDate(session.end_time) : 'Running'}</div>
                    <div>{formatCurrency(session.initial_capital)}</div>
                    <div>{session.final_capital ? formatCurrency(session.final_capital) : '-'}</div>
                    <div style={{ color: (session.total_return || 0) > 0 ? '#22c55e' : '#ef4444' }}>
                      {session.total_return !== null && session.total_return !== undefined ? formatPercentage(session.total_return) : '-'}
                    </div>
                    <div title={`Raw: ${session.total_trades}, Type: ${typeof session.total_trades}`}>
                      {Number(session.total_trades) || 0}
                    </div>
                    <div style={{ color: '#22c55e' }} title={`Raw: ${session.winning_trades}, Type: ${typeof session.winning_trades}`}>
                      {Number(session.winning_trades) || 0}
                    </div>
                    <div style={{ color: '#ef4444' }} title={`Raw: ${session.losing_trades}, Type: ${typeof session.losing_trades}`}>
                      {Number(session.losing_trades) || 0}
                    </div>
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
                );
              })}
            </DataGrid>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
              📊 No backtest results yet. Run your first real backtest above to see authentic results here.
            </div>
          )}
        </Card>
      </MainContent>
    </BacktestingContainer>
  );
};

export default Backtesting;