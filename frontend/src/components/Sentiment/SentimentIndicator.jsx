import React from 'react';
import styled from 'styled-components';

const SentimentContainer = styled.div`
  padding: 0;
`;

const SentimentHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
`;

const SentimentTitle = styled.h3`
  color: ${props => props.theme.colors.text};
  margin: 0;
  font-size: 18px;
  font-weight: 600;
`;

const SignalBadge = styled.span`
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  
  &.bullish {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
  
  &.bearish {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
  
  &.neutral {
    background: rgba(156, 163, 175, 0.1);
    color: #9ca3af;
  }
`;

const SignalIcon = styled.span`
  font-size: 16px;
`;

const ScoreSection = styled.div`
  margin-bottom: 16px;
`;

const ScoreHeader = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
`;

const ScoreLabel = styled.div`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 14px;
`;

const ScoreValue = styled.div`
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  font-weight: 600;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
`;

const ProgressFill = styled.div`
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
  background: ${props => 
    props.signal === 'BULLISH' ? '#22c55e' :
    props.signal === 'BEARISH' ? '#ef4444' :
    '#9ca3af'
  };
`;

const MetricsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
`;

const MetricBox = styled.div`
  text-align: center;
`;

const MetricLabel = styled.div`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 11px;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const MetricValue = styled.div`
  color: ${props => props.theme.colors.text};
  font-size: 14px;
  font-weight: 600;
`;

const Timestamp = styled.div`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 11px;
  text-align: center;
  margin-top: 12px;
`;

const LoadingMessage = styled.div`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 14px;
  text-align: center;
  padding: 20px;
`;

const ErrorMessage = styled.div`
  color: #ef4444;
  font-size: 14px;
  text-align: center;
  padding: 20px;
`;

const SentimentIndicator = ({ sentiment, loading, error }) => {
  if (loading) {
    return (
      <SentimentContainer>
        <LoadingMessage>Loading sentiment...</LoadingMessage>
      </SentimentContainer>
    );
  }

  if (error) {
    return (
      <SentimentContainer>
        <ErrorMessage>{error}</ErrorMessage>
      </SentimentContainer>
    );
  }

  if (!sentiment) {
    return (
      <SentimentContainer>
        <LoadingMessage>No sentiment data available</LoadingMessage>
      </SentimentContainer>
    );
  }

  const getSentimentIcon = (signal) => {
    switch (signal) {
      case 'BULLISH':
        return '📈';
      case 'BEARISH':
        return '📉';
      case 'NEUTRAL':
      default:
        return '➡️';
    }
  };

  const sentimentPercentage = ((sentiment.sentiment_score + 1) / 2) * 100;
  const signalClass = sentiment.signal.toLowerCase();

  return (
    <SentimentContainer>
      <SentimentHeader>
        <SentimentTitle>Market Sentiment</SentimentTitle>
        <SignalBadge className={signalClass}>
          <SignalIcon>{getSentimentIcon(sentiment.signal)}</SignalIcon>
          {sentiment.signal}
        </SignalBadge>
      </SentimentHeader>

      <ScoreSection>
        <ScoreHeader>
          <ScoreLabel>Sentiment Score</ScoreLabel>
          <ScoreValue>{sentiment.sentiment_score.toFixed(2)}</ScoreValue>
        </ScoreHeader>
        <ProgressBar title={`Score: ${sentiment.sentiment_score.toFixed(2)} (-1 to 1)`}>
          <ProgressFill 
            signal={sentiment.signal}
            style={{ width: `${sentimentPercentage}%` }}
          />
        </ProgressBar>
      </ScoreSection>

      <MetricsGrid>
        <MetricBox>
          <MetricLabel>Confidence</MetricLabel>
          <MetricValue>{(sentiment.confidence * 100).toFixed(0)}%</MetricValue>
        </MetricBox>
        <MetricBox>
          <MetricLabel>News</MetricLabel>
          <MetricValue>{sentiment.news_count}</MetricValue>
        </MetricBox>
        <MetricBox>
          <MetricLabel>Category</MetricLabel>
          <MetricValue>{sentiment.category}</MetricValue>
        </MetricBox>
      </MetricsGrid>

      {sentiment.timestamp && (
        <Timestamp>
          Updated: {new Date(sentiment.timestamp).toLocaleString()}
        </Timestamp>
      )}
    </SentimentContainer>
  );
};

export default SentimentIndicator;