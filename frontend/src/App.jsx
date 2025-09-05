import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider } from 'styled-components';
import { store } from './store/store';
import { GlobalStyle, darkTheme } from './styles/theme';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard/Dashboard';
import {
  LiveTrading,
  Backtesting,
  Strategies,
  Analytics,
  Settings,
} from './components/placeholder-components';
import './App.css';

const App = () => {
  return (
    <Provider store={store}>
      <ThemeProvider theme={darkTheme}>
        <GlobalStyle />
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live-trading" element={<LiveTrading />} />
              <Route path="/backtesting" element={<Backtesting />} />
              <Route path="/strategies" element={<Strategies />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </Router>
      </ThemeProvider>
    </Provider>
  );
};

export default App;