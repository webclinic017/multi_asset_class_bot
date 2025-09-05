import React, { useState, useEffect } from 'react';
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

const StatusDot = styled.div<{ active: boolean }>`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${props => props.active ? props.theme.colors.success : props.theme.colors.textSecondary};
`;

const StatusText = styled.span`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 12px;
`;

interface Strategy {
  id: number;
  name: string;
  description: string;
  strategy_type: string;
  asset_class: string;
  timeframe: string;
  parameters: Record<string, any>;
  created_at: string;
  is_active: boolean;
}

const Strategies: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [editingParameters, setEditingParameters] = useState<Record<string, any>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStrategies();
  }, []);

  const fetchStrategies = async () => {
    try {
      const response = await axios.get('/api/strategies');
      setStrategies(response.data);
      if (response.data.length > 0 && !selectedStrategy) {
        setSelectedStrategy(response.data[0]);
        setEditingParameters(response.data[0].parameters);
      }
    } catch (error) {
      console.error('Error fetching strategies:', error);
    }
  };

  const handleStrategySelect = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setEditingParameters(strategy.parameters);
    setIsEditing(false);
  };

  const handleParameterChange = (key: string, value: any) => {
    setEditingParameters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSaveParameters = async () => {
    if (!selectedStrategy) return;

    setLoading(true);
    try {
      // In a real implementation, you would have an API endpoint to update strategy parameters
      // For now, we'll just update the local state
      const updatedStrategy = {
        ...selectedStrategy,
        parameters: editingParameters
      };
      
      setStrategies(prev => 
        prev.map(s => s.id === selectedStrategy.id ? updatedStrategy : s)
      );
      setSelectedStrategy(updatedStrategy);
      setIsEditing(false);
      
      alert('Strategy parameters updated successfully!');
    } catch (error) {
      console.error('Error updating strategy:', error);
      alert('Error updating strategy parameters');
    } finally {
      setLoading(false);
    }
  };

  const handleResetParameters = () => {
    if (selectedStrategy) {
      setEditingParameters(selectedStrategy.parameters);
    }
  };

  const renderParameterInput = (key: string, value: any) => {
    const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0;
    
    if (typeof value === 'number' || !isNaN(numericValue)) {
      return (
        <ParameterInput
          type="number"
          value={editingParameters[key] || value}
          onChange={(e) => handleParameterChange(key, parseFloat(e.target.value) || 0)}
          step={value < 1 ? "0.001" : "1"}
          disabled={!isEditing}
        />
      );
    } else if (typeof value === 'boolean') {
      return (
        <ParameterInput
          type="checkbox"
          checked={editingParameters[key] !== undefined ? editingParameters[key] : value}
          onChange={(e) => handleParameterChange(key, e.target.checked)}
          disabled={!isEditing}
        />
      );
    } else {
      return (
        <ParameterInput
          type="text"
          value={editingParameters[key] || value}
          onChange={(e) => handleParameterChange(key, e.target.value)}
          disabled={!isEditing}
        />
      );
    }
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
            className={selectedStrategy?.id === strategy.id ? 'selected' : ''}
            onClick={() => handleStrategySelect(strategy)}
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
              <StatusDot active={strategy.is_active} />
              <StatusText>{strategy.is_active ? 'Active' : 'Inactive'}</StatusText>
            </StatusIndicator>
          </StrategyCard>
        ))}
      </StrategiesGrid>

      {selectedStrategy && (
        <Card>
          <CardTitle>Strategy Parameters - {selectedStrategy.name}</CardTitle>
          
          <ParametersSection>
            <ParametersGrid>
              {Object.entries(selectedStrategy.parameters).map(([key, value]) => (
                <ParameterGroup key={key}>
                  <ParameterLabel>{key.replace(/_/g, ' ')}</ParameterLabel>
                  {isEditing ? (
                    renderParameterInput(key, value)
                  ) : (
                    <ParameterValue>
                      {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value.toString()}
                    </ParameterValue>
                  )}
                </ParameterGroup>
              ))}
            </ParametersGrid>
            
            <ButtonGroup>
              {isEditing ? (
                <>
                  <Button onClick={handleSaveParameters} disabled={loading}>
                    {loading ? 'Saving...' : 'Save Changes'}
                  </Button>
                  <SecondaryButton onClick={handleResetParameters}>
                    Reset
                  </SecondaryButton>
                  <SecondaryButton onClick={() => setIsEditing(false)}>
                    Cancel
                  </SecondaryButton>
                </>
              ) : (
                <Button onClick={() => setIsEditing(true)}>
                  Edit Parameters
                </Button>
              )}
            </ButtonGroup>
          </ParametersSection>
        </Card>
      )}
    </StrategiesContainer>
  );
};

export default Strategies;