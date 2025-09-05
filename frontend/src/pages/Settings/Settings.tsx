import React from 'react';
import styled from 'styled-components';

const SettingsContainer = styled.div`
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

const Settings: React.FC = () => {
  return (
    <SettingsContainer>
      <Title>Settings</Title>
      <PlaceholderCard>
        Settings interface will be implemented here.
        This page will allow users to configure system preferences.
      </PlaceholderCard>
    </SettingsContainer>
  );
};

export default Settings;