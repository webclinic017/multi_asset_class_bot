import React from 'react';
import styled from 'styled-components';

const LayoutContainer = styled.div`
  display: flex;
  height: 100vh;
  background: ${props => props.theme.colors.background};
`;

const Sidebar = styled.div`
  width: 250px;
  background: ${props => props.theme.colors.cardBackground};
  border-right: 1px solid ${props => props.theme.colors.border};
  padding: 20px;
`;

const MainContent = styled.div`
  flex: 1;
  overflow: hidden;
`;

const Header = styled.div`
  height: 60px;
  background: ${props => props.theme.colors.cardBackground};
  border-bottom: 1px solid ${props => props.theme.colors.border};
  display: flex;
  align-items: center;
  padding: 0 20px;
`;

const Content = styled.div`
  height: calc(100vh - 60px);
  overflow-y: auto;
`;

const Layout = ({ children }) => {
  return (
    <LayoutContainer>
      <Sidebar>
        <h2 style={{ color: '#00D4AA', marginBottom: '20px' }}>Trading Bot</h2>
        <nav>
          <div style={{ marginBottom: '10px' }}>
            <a href="/" style={{ color: '#E2E8F0', textDecoration: 'none' }}>Dashboard</a>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <a href="/live-trading" style={{ color: '#E2E8F0', textDecoration: 'none' }}>Live Trading</a>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <a href="/backtesting" style={{ color: '#E2E8F0', textDecoration: 'none' }}>Backtesting</a>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <a href="/strategies" style={{ color: '#E2E8F0', textDecoration: 'none' }}>Strategies</a>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <a href="/analytics" style={{ color: '#E2E8F0', textDecoration: 'none' }}>Analytics</a>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <a href="/settings" style={{ color: '#E2E8F0', textDecoration: 'none' }}>Settings</a>
          </div>
        </nav>
      </Sidebar>
      <MainContent>
        <Header>
          <h1 style={{ color: '#E2E8F0', fontSize: '18px' }}>Trading Dashboard</h1>
        </Header>
        <Content>
          {children}
        </Content>
      </MainContent>
    </LayoutContainer>
  );
};

export default Layout;