import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import axios from 'axios';

const StrategiesContainer = styled.div`
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

const StrategiesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
`;

const StrategyCard = styled.div`
  background: ${props => props.theme.colors.surface};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
  cursor: pointer;
  
  &:hover {
    border-color: ${props => props.theme.colors.primary};
    transform: translateY(-2px);
  }
  
  &.selected {
    border-color: ${props => props.theme.colors.primary};
    background: ${props => props.theme.colors.background};
  }
`;

const StrategyHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
`;

const StrategyName = styled.h4`
  color: ${props => props.theme.colors.text};
  margin: 0;
  font-size: 16px;
  font-weight: 600;
`;

const StrategyBadge = styled.span`
  background: ${props => props.theme.colors.primary};
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
`;

const StrategyDescription = styled.p`
  color: ${props => props.theme.colors.textSecondary};
  margin: 0 0 16px 0;
  font-size: 14px;
  line-height: 1.4;
`;

const StrategyMeta = styled.div`
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
`;

const MetaItem = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const MetaLabel = styled.span`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const MetaValue = styled.span`
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  font-weight: 500;
`;

const ParametersSection = styled.div`
  border-top: 1px solid ${props => props.theme.colors.border};
  padding-top: 16px;
`;

const ParametersGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
`;

const ParameterGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

const ParameterLabel = styled.label`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const ParameterInput = styled.input`
  background: ${props => props.theme.colors.background};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 8px 10px;
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
  }
`;

const ParameterValue = styled.div`
  background: ${props => props.theme.colors.background};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 6px;
  padding: 8px 10px;
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  min-height: 36px;
  display: flex;
  align-items: center;
`;

const Button = styled.button`
  background: ${props => props.theme.colors.primary};
  color: white;
  border: none;
  border-radius: 6px;
  padding: 10px 20px;
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

const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
  margin-top: 20px;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
`;

const StatusDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${props => props.active ? props.theme.colors.success : props.theme.colors.textSecondary};
`;

const StatusText = styled.span`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 12px;
`;

const Strategies = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState([]);
  const [activeSessions, setActiveSessions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStrategies();
    fetchActiveSessions();
  }, []);

  const fetchStrategies = async () => {
    try {
      const response = await axios.get('/api/strategies');
      setStrategies(response.data);
    } catch (error) {
      console.error('Error fetching strategies:', error);
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

  const isStrategyActive = (strategyId) => {
    return activeSessions.some(session => session.strategy_id === strategyId);
  };

  const handleStrategyClick = (strategy) => {
    navigate(`/strategies/${strategy.id}/config`);
  };

  return (
    <StrategiesContainer>
      <Header>
        <Title>Trading Strategies</Title>
      </Header>

      <StrategiesGrid>
        {strategies.map(strategy => (
          <StrategyCard
            key={strategy.id}
            onClick={() => handleStrategyClick(strategy)}
          >
            <StrategyHeader>
              <StrategyName>{strategy.name}</StrategyName>
              <StrategyBadge>{strategy.strategy_type}</StrategyBadge>
            </StrategyHeader>
            
            <StrategyDescription>{strategy.description}</StrategyDescription>
            
            <StrategyMeta>
              <MetaItem>
                <MetaLabel>Asset Class</MetaLabel>
                <MetaValue>{strategy.asset_class.toUpperCase()}</MetaValue>
              </MetaItem>
              <MetaItem>
                <MetaLabel>Timeframe</MetaLabel>
                <MetaValue>{strategy.timeframe}</MetaValue>
              </MetaItem>
              <MetaItem>
                <MetaLabel>Parameters</MetaLabel>
                <MetaValue>{Object.keys(strategy.parameters).length}</MetaValue>
              </MetaItem>
            </StrategyMeta>
            
            <StatusIndicator>
              <StatusDot active={isStrategyActive(strategy.id)} />
              <StatusText>{isStrategyActive(strategy.id) ? 'Active' : 'Inactive'}</StatusText>
            </StatusIndicator>
          </StrategyCard>
        ))}
      </StrategiesGrid>

    </StrategiesContainer>
  );
};

export default Strategies;