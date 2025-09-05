import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import axios from 'axios';

const ConfigContainer = styled.div`
  padding: 20px;
  color: ${props => props.theme.colors.text};
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

const BackButton = styled.button`
  background: transparent;
  color: ${props => props.theme.colors.text};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: ${props => props.theme.colors.surface};
    border-color: ${props => props.theme.colors.primary};
  }
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

const StrategyInfo = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 30px;
`;

const InfoItem = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

const InfoLabel = styled.label`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const InfoValue = styled.div`
  background: ${props => props.theme.colors.background};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 10px 12px;
  color: ${props => props.theme.colors.text};
  font-size: 14px;
`;

const ParametersGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
`;

const ParameterGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const ParameterLabel = styled.label`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 14px;
  font-weight: 500;
  text-transform: capitalize;
`;

const ParameterInput = styled.input`
  background: ${props => props.theme.colors.background};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 12px 14px;
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
    box-shadow: 0 0 0 2px ${props => props.theme.colors.primary}20;
  }
  
  &:disabled {
    background: ${props => props.theme.colors.surface};
    color: ${props => props.theme.colors.textSecondary};
    cursor: not-allowed;
  }
`;

const ParameterDescription = styled.div`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 12px;
  margin-top: 4px;
  font-style: italic;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 16px;
  justify-content: flex-end;
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

const SecondaryButton = styled(Button)`
  background: transparent;
  color: ${props => props.theme.colors.text};
  border: 1px solid ${props => props.theme.colors.border};
  
  &:hover {
    background: ${props => props.theme.colors.surface};
    border-color: ${props => props.theme.colors.primary};
  }
`;

const StatusBadge = styled.span`
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  
  &.active {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
  
  &.inactive {
    background: rgba(156, 163, 175, 0.1);
    color: #9ca3af;
  }
`;

const LoadingSpinner = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: ${props => props.theme.colors.textSecondary};
`;

// Parameter descriptions for better UX
const PARAMETER_DESCRIPTIONS = {
  fast_ema: "Fast Exponential Moving Average period for quick trend detection",
  slow_ema: "Slow Exponential Moving Average period for trend confirmation",
  fast_length: "Fast moving average length for trend analysis",
  slow_length: "Slow moving average length for trend confirmation",
  rsi_period: "RSI calculation period for momentum analysis",
  rsi_oversold: "RSI level below which asset is considered oversold",
  rsi_overbought: "RSI level above which asset is considered overbought",
  stop_loss_pips: "Stop loss distance in pips for risk management",
  take_profit_pips: "Take profit target in pips for profit taking",
  position_size_percent: "Position size as percentage of account balance",
  max_risk_per_trade: "Maximum risk per trade as percentage of account",
  macd_fast: "MACD fast EMA period",
  macd_slow: "MACD slow EMA period",
  macd_signal: "MACD signal line period",
  bb_period: "Bollinger Bands calculation period",
  bb_std: "Bollinger Bands standard deviation multiplier",
  atr_period: "Average True Range calculation period",
  use_gpu: "Enable GPU acceleration for faster calculations",
  dynamic_sizing: "Enable dynamic position sizing based on market conditions"
};

const StrategyConfig = () => {
  const { strategyId } = useParams();
  const navigate = useNavigate();
  
  const [strategy, setStrategy] = useState(null);
  const [parameters, setParameters] = useState({});
  const [originalParameters, setOriginalParameters] = useState({});
  const [activeSessions, setActiveSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchStrategy();
    fetchActiveSessions();
  }, [strategyId]);

  useEffect(() => {
    // Check if parameters have changed
    const changed = JSON.stringify(parameters) !== JSON.stringify(originalParameters);
    setHasChanges(changed);
  }, [parameters, originalParameters]);

  const fetchStrategy = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/strategies/${strategyId}`);
      setStrategy(response.data);
      setParameters(response.data.parameters);
      setOriginalParameters(response.data.parameters);
    } catch (error) {
      console.error('Error fetching strategy:', error);
      alert('Error loading strategy details');
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveSessions = async () => {
    try {
      const response = await axios.get('/api/sessions/active');
      setActiveSessions(response.data);
    } catch (error) {
      console.error('Error fetching active sessions:', error);
    }
  };

  const isStrategyActive = () => {
    if (!strategy) return false;
    return activeSessions.some(session => session.strategy_id === strategy.id);
  };

  const handleParameterChange = (key, value) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      // Update strategy parameters via API
      await axios.put(`/api/strategies/${strategyId}`, {
        ...strategy,
        parameters: parameters
      });
      
      setOriginalParameters(parameters);
      alert('Strategy parameters updated successfully!');
      
    } catch (error) {
      console.error('Error saving strategy:', error);
      alert('Error saving strategy parameters');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setParameters(originalParameters);
  };

  const handleBack = () => {
    if (hasChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to go back?')) {
        navigate('/strategies');
      }
    } else {
      navigate('/strategies');
    }
  };

  const renderParameterInput = (key, value) => {
    const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0;
    
    if (typeof value === 'boolean') {
      return (
        <ParameterInput
          type="checkbox"
          checked={parameters[key] !== undefined ? parameters[key] : value}
          onChange={(e) => handleParameterChange(key, e.target.checked)}
        />
      );
    } else if (typeof value === 'number' || !isNaN(numericValue)) {
      return (
        <ParameterInput
          type="number"
          value={parameters[key] !== undefined ? parameters[key] : value}
          onChange={(e) => handleParameterChange(key, parseFloat(e.target.value) || 0)}
          step={value < 1 ? "0.001" : "1"}
        />
      );
    } else {
      return (
        <ParameterInput
          type="text"
          value={parameters[key] !== undefined ? parameters[key] : value}
          onChange={(e) => handleParameterChange(key, e.target.value)}
        />
      );
    }
  };

  if (loading) {
    return (
      <ConfigContainer>
        <LoadingSpinner>Loading strategy configuration...</LoadingSpinner>
      </ConfigContainer>
    );
  }

  if (!strategy) {
    return (
      <ConfigContainer>
        <Header>
          <Title>Strategy Not Found</Title>
          <BackButton onClick={() => navigate('/strategies')}>
            Back to Strategies
          </BackButton>
        </Header>
      </ConfigContainer>
    );
  }

  return (
    <ConfigContainer>
      <Header>
        <Title>Configure Strategy: {strategy.name}</Title>
        <BackButton onClick={handleBack}>
          Back to Strategies
        </BackButton>
      </Header>

      <Card>
        <CardTitle>Strategy Information</CardTitle>
        <StrategyInfo>
          <InfoItem>
            <InfoLabel>Strategy Type</InfoLabel>
            <InfoValue>{strategy.strategy_type}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>Asset Class</InfoLabel>
            <InfoValue>{strategy.asset_class.toUpperCase()}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>Timeframe</InfoLabel>
            <InfoValue>{strategy.timeframe}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>Status</InfoLabel>
            <InfoValue>
              <StatusBadge className={isStrategyActive() ? 'active' : 'inactive'}>
                {isStrategyActive() ? 'Active' : 'Inactive'}
              </StatusBadge>
            </InfoValue>
          </InfoItem>
        </StrategyInfo>
        
        <InfoItem>
          <InfoLabel>Description</InfoLabel>
          <InfoValue>{strategy.description}</InfoValue>
        </InfoItem>
      </Card>

      <Card>
        <CardTitle>Strategy Parameters</CardTitle>
        <ParametersGrid>
          {Object.entries(strategy.parameters).map(([key, value]) => (
            <ParameterGroup key={key}>
              <ParameterLabel>{key.replace(/_/g, ' ')}</ParameterLabel>
              {renderParameterInput(key, value)}
              {PARAMETER_DESCRIPTIONS[key] && (
                <ParameterDescription>
                  {PARAMETER_DESCRIPTIONS[key]}
                </ParameterDescription>
              )}
            </ParameterGroup>
          ))}
        </ParametersGrid>
        
        <ButtonGroup>
          <SecondaryButton onClick={handleReset} disabled={!hasChanges}>
            Reset Changes
          </SecondaryButton>
          <Button onClick={handleSave} disabled={!hasChanges || saving}>
            {saving ? 'Saving...' : 'Save Parameters'}
          </Button>
        </ButtonGroup>
      </Card>
    </ConfigContainer>
  );
};

export default StrategyConfig;