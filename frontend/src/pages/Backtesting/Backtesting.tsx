import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import axios from 'axios';

const BacktestingContainer = styled.div`
  padding: 20px;
  color: ${props => props.theme.colors.text};
`;

const Header = styled.div`
  display: flex;
  justify-content: between;
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
  grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
  background: ${props => props.theme.colors.background};
  padding: 12px;
  font-weight: 600;
  color: ${props => props.theme.colors.text};
  border-bottom: 1px solid ${props => props.theme.colors.border};
`;

const DataGridRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
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

interface BacktestSession {
  id: number;
  strategy_name: string;
  symbol: string;
  start_time: string;
  end_time: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  total_trades: number;
  win_rate: number;
  max_drawdown: number;
  sharpe_ratio: number;
  status: string;
}

interface Strategy {
  id: number;
  name: string;
  strategy_type: string;
  asset_class: string;
  timeframe: string;
}

const Backtesting: React.FC = () => {
  const [sessions, setSessions] = useState<BacktestSession[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    strategy_id: '',
    symbol: 'EUR_USD',
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    initial_capital: 10000,
    timeframe: '1m'
  });

  useEffect(() => {
    fetchSessions();
    fetchStrategies();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await axios.get('/api/sessions');
      const backtestSessions = response.data.filter((session: any) => session.session_type === 'backtest');
      setSessions(backtestSessions);
    } catch (error) {
      console.error('Error fetching sessions:', error);
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

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'initial_capital' ? parseFloat(value) : value
    }));
  };

  const handleRunBacktest = async () => {
    if (!formData.strategy_id) {
      alert('Please select a strategy');
      return;
    }

    setLoading(true);
    try {
      await axios.post('/api/backtest', formData);
      alert('Backtest started successfully!');
      // Refresh sessions after a short delay
      setTimeout(fetchSessions, 2000);
    } catch (error) {
      console.error('Error running backtest:', error);
      alert('Error starting backtest');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <BacktestingContainer>
      <Header>
        <Title>Backtesting</Title>
      </Header>

      <Card>
        <CardTitle>Run New Backtest</CardTitle>
        <FormGrid>
          <FormGroup>
            <Label>Strategy</Label>
            <Select
              name="strategy_id"
              value={formData.strategy_id}
              onChange={handleInputChange}
            >
              <option value="">Select Strategy</option>
              {strategies.map(strategy => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name} ({strategy.timeframe})
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
              <option value="EUR_USD">EUR/USD</option>
              <option value="GBP_USD">GBP/USD</option>
              <option value="USD_JPY">USD/JPY</option>
              <option value="AUD_USD">AUD/USD</option>
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
          {loading ? 'Running Backtest...' : 'Run Backtest'}
        </Button>
      </Card>

      <Card>
        <CardTitle>Backtest Results</CardTitle>
        {sessions.length > 0 ? (
          <DataGrid>
            <DataGridHeader>
              <div>Strategy</div>
              <div>Symbol</div>
              <div>Period</div>
              <div>Initial Capital</div>
              <div>Final Capital</div>
              <div>Return</div>
              <div>Trades</div>
              <div>Status</div>
            </DataGridHeader>
            {sessions.map(session => (
              <DataGridRow key={session.id}>
                <div>{session.strategy_name}</div>
                <div>{session.symbol}</div>
                <div>{formatDate(session.start_time)} - {session.end_time ? formatDate(session.end_time) : 'Running'}</div>
                <div>{formatCurrency(session.initial_capital)}</div>
                <div>{session.final_capital ? formatCurrency(session.final_capital) : '-'}</div>
                <div style={{ color: session.total_return > 0 ? '#22c55e' : '#ef4444' }}>
                  {session.total_return ? formatPercentage(session.total_return) : '-'}
                </div>
                <div>{session.total_trades}</div>
                <div>
                  <StatusBadge className={session.status}>
                    {session.status}
                  </StatusBadge>
                </div>
              </DataGridRow>
            ))}
          </DataGrid>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
            No backtest results available. Run your first backtest to see results here.
          </div>
        )}
        
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
                {sessions.filter(s => s.total_return > 0).length}
              </MetricValue>
              <MetricLabel>Profitable</MetricLabel>
            </MetricCard>
            <MetricCard>
              <MetricValue>
                {sessions.reduce((sum, s) => sum + (s.total_trades || 0), 0)}
              </MetricValue>
              <MetricLabel>Total Trades</MetricLabel>
            </MetricCard>
          </MetricsGrid>
        )}
      </Card>
    </BacktestingContainer>
  );
};

export default Backtesting;