import React from 'react';
import styled from 'styled-components';

const AnalyticsContainer = styled.div`
  padding: 20px;
  color: ${props => props.theme.colors.text};
`;

const Title = styled.h1`
  color: ${props => props.theme.colors.text};
  margin: 0 0 30px 0;
  font-size: 28px;
  font-weight: 600;
`;

const PlaceholderCard = styled.div`
  background: ${props => props.theme.colors.surface};
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  border: 1px solid ${props => props.theme.colors.border};
  color: ${props => props.theme.colors.textSecondary};
`;

const Analytics: React.FC = () => {
  return (
    <AnalyticsContainer>
      <Title>Analytics</Title>
      <PlaceholderCard>
        Analytics dashboard will be implemented here.
        This page will show detailed performance analysis and reports.
      </PlaceholderCard>
    </AnalyticsContainer>
  );
};

export default Analytics;