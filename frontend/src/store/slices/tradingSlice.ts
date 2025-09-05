import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

// Types
export interface Trade {
  id: number;
  session_id: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_time: string;
  exit_time?: string;
  entry_price: number;
  exit_price?: number;
  quantity: number;
  pnl?: number;
  pnl_pips?: number;
  status: 'open' | 'closed' | 'cancelled';
  exit_reason?: string;
  signal_strength?: number;
  confidence?: number;
}

export interface TradingSession {
  id: number;
  session_type: 'live' | 'backtest';
  strategy_id: number;
  strategy_name: string;
  symbol: string;
  start_time: string;
  end_time?: string;
  initial_capital: number;
  final_capital?: number;
  total_return?: number;
  max_drawdown?: number;
  sharpe_ratio?: number;
  win_rate?: number;
  total_trades: number;
  status: 'active' | 'completed' | 'stopped' | 'failed';
}

export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_ratio: number;
}

export interface PortfolioSnapshot {
  id: number;
  session_id: number;
  timestamp: string;
  total_value: number;
  cash_balance: number;
  unrealized_pnl: number;
  realized_pnl: number;
  open_positions: number;
  daily_pnl: number;
  drawdown: number;
}

interface TradingState {
  // Sessions
  sessions: TradingSession[];
  activeSessions: TradingSession[];
  currentSession: TradingSession | null;
  
  // Trades
  trades: Trade[];
  openTrades: Trade[];
  
  // Performance
  performance: PerformanceMetrics | null;
  portfolioSnapshots: PortfolioSnapshot[];
  
  // UI State
  loading: boolean;
  error: string | null;
  
  // Real-time data
  isConnected: boolean;
  lastUpdate: string | null;
}

const initialState: TradingState = {
  sessions: [],
  activeSessions: [],
  currentSession: null,
  trades: [],
  openTrades: [],
  performance: null,
  portfolioSnapshots: [],
  loading: false,
  error: null,
  isConnected: false,
  lastUpdate: null,
};

// Async thunks
export const fetchTradingSessions = createAsyncThunk(
  'trading/fetchSessions',
  async (limit: number = 100) => {
    const response = await fetch(`/api/sessions?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to fetch trading sessions');
    }
    return response.json();
  }
);

export const fetchActiveSessions = createAsyncThunk(
  'trading/fetchActiveSessions',
  async () => {
    const response = await fetch('/api/sessions/active');
    if (!response.ok) {
      throw new Error('Failed to fetch active sessions');
    }
    return response.json();
  }
);

export const createTradingSession = createAsyncThunk(
  'trading/createSession',
  async (sessionData: {
    strategy_id: number;
    symbol: string;
    initial_capital: number;
    session_type: 'live' | 'backtest';
  }) => {
    const response = await fetch('/api/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(sessionData),
    });
    if (!response.ok) {
      throw new Error('Failed to create trading session');
    }
    return response.json();
  }
);

export const fetchSessionTrades = createAsyncThunk(
  'trading/fetchSessionTrades',
  async ({ sessionId, limit = 1000 }: { sessionId: number; limit?: number }) => {
    const response = await fetch(`/api/sessions/${sessionId}/trades?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to fetch session trades');
    }
    return response.json();
  }
);

export const fetchOpenTrades = createAsyncThunk(
  'trading/fetchOpenTrades',
  async () => {
    const response = await fetch('/api/trades/open');
    if (!response.ok) {
      throw new Error('Failed to fetch open trades');
    }
    return response.json();
  }
);

export const fetchSessionPerformance = createAsyncThunk(
  'trading/fetchSessionPerformance',
  async (sessionId: number) => {
    const response = await fetch(`/api/sessions/${sessionId}/performance`);
    if (!response.ok) {
      throw new Error('Failed to fetch session performance');
    }
    return response.json();
  }
);

export const fetchPortfolioSnapshots = createAsyncThunk(
  'trading/fetchPortfolioSnapshots',
  async ({ 
    sessionId, 
    startTime, 
    endTime 
  }: { 
    sessionId: number; 
    startTime?: string; 
    endTime?: string; 
  }) => {
    let url = `/api/sessions/${sessionId}/portfolio`;
    const params = new URLSearchParams();
    
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch portfolio snapshots');
    }
    return response.json();
  }
);

// Slice
const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    setCurrentSession: (state, action: PayloadAction<TradingSession | null>) => {
      state.currentSession = action.payload;
    },
    
    setConnectionStatus: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },
    
    updateLastUpdate: (state) => {
      state.lastUpdate = new Date().toISOString();
    },
    
    addTrade: (state, action: PayloadAction<Trade>) => {
      state.trades.unshift(action.payload);
      if (action.payload.status === 'open') {
        state.openTrades.unshift(action.payload);
      }
    },
    
    updateTrade: (state, action: PayloadAction<Trade>) => {
      const index = state.trades.findIndex(trade => trade.id === action.payload.id);
      if (index !== -1) {
        state.trades[index] = action.payload;
      }
      
      // Update open trades
      const openIndex = state.openTrades.findIndex(trade => trade.id === action.payload.id);
      if (action.payload.status === 'open') {
        if (openIndex === -1) {
          state.openTrades.push(action.payload);
        } else {
          state.openTrades[openIndex] = action.payload;
        }
      } else if (openIndex !== -1) {
        state.openTrades.splice(openIndex, 1);
      }
    },
    
    addPortfolioSnapshot: (state, action: PayloadAction<PortfolioSnapshot>) => {
      state.portfolioSnapshots.push(action.payload);
      // Keep only last 1000 snapshots for performance
      if (state.portfolioSnapshots.length > 1000) {
        state.portfolioSnapshots = state.portfolioSnapshots.slice(-1000);
      }
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    resetTradingState: (state) => {
      return { ...initialState, isConnected: state.isConnected };
    },
  },
  
  extraReducers: (builder) => {
    // Fetch trading sessions
    builder
      .addCase(fetchTradingSessions.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTradingSessions.fulfilled, (state, action) => {
        state.loading = false;
        state.sessions = action.payload;
      })
      .addCase(fetchTradingSessions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch trading sessions';
      });
    
    // Fetch active sessions
    builder
      .addCase(fetchActiveSessions.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchActiveSessions.fulfilled, (state, action) => {
        state.loading = false;
        state.activeSessions = action.payload;
      })
      .addCase(fetchActiveSessions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch active sessions';
      });
    
    // Create trading session
    builder
      .addCase(createTradingSession.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createTradingSession.fulfilled, (state, action) => {
        state.loading = false;
        state.sessions.unshift(action.payload);
        if (action.payload.status === 'active') {
          state.activeSessions.unshift(action.payload);
        }
      })
      .addCase(createTradingSession.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create trading session';
      });
    
    // Fetch session trades
    builder
      .addCase(fetchSessionTrades.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchSessionTrades.fulfilled, (state, action) => {
        state.loading = false;
        state.trades = action.payload;
      })
      .addCase(fetchSessionTrades.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch session trades';
      });
    
    // Fetch open trades
    builder
      .addCase(fetchOpenTrades.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchOpenTrades.fulfilled, (state, action) => {
        state.loading = false;
        state.openTrades = action.payload;
      })
      .addCase(fetchOpenTrades.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch open trades';
      });
    
    // Fetch session performance
    builder
      .addCase(fetchSessionPerformance.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchSessionPerformance.fulfilled, (state, action) => {
        state.loading = false;
        state.performance = action.payload;
      })
      .addCase(fetchSessionPerformance.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch session performance';
      });
    
    // Fetch portfolio snapshots
    builder
      .addCase(fetchPortfolioSnapshots.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchPortfolioSnapshots.fulfilled, (state, action) => {
        state.loading = false;
        state.portfolioSnapshots = action.payload;
      })
      .addCase(fetchPortfolioSnapshots.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch portfolio snapshots';
      });
  },
});

export const {
  setCurrentSession,
  setConnectionStatus,
  updateLastUpdate,
  addTrade,
  updateTrade,
  addPortfolioSnapshot,
  clearError,
  resetTradingState,
} = tradingSlice.actions;

export default tradingSlice.reducer;