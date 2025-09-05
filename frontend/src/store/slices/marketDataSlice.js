import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const initialState = {
  marketData: {},
  currentSymbol: 'EUR_USD',
  currentTimeframe: '1m',
  loading: false,
  error: null,
  lastUpdate: null,
};

// Async thunks
export const fetchMarketData = createAsyncThunk(
  'marketData/fetchMarketData',
  async ({ symbol, timeframe, limit = 1000, startTime, endTime }) => {
    let url = `/api/market-data/${symbol}?timeframe=${timeframe}&limit=${limit}`;
    
    if (startTime) url += `&start_time=${startTime}`;
    if (endTime) url += `&end_time=${endTime}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch market data');
    }
    
    const data = await response.json();
    return { symbol, timeframe, data };
  }
);

const marketDataSlice = createSlice({
  name: 'marketData',
  initialState,
  reducers: {
    setCurrentSymbol: (state, action) => {
      state.currentSymbol = action.payload;
    },
    
    setCurrentTimeframe: (state, action) => {
      state.currentTimeframe = action.payload;
    },
    
    updateMarketData: (state, action) => {
      const { symbol, timeframe, data } = action.payload;
      const key = `${symbol}_${timeframe}`;
      state.marketData[key] = data;
      state.lastUpdate = new Date().toISOString();
    },
    
    clearError: (state) => {
      state.error = null;
    },
  },
  
  extraReducers: (builder) => {
    builder
      .addCase(fetchMarketData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMarketData.fulfilled, (state, action) => {
        state.loading = false;
        const { symbol, timeframe, data } = action.payload;
        const key = `${symbol}_${timeframe}`;
        state.marketData[key] = data;
        state.lastUpdate = new Date().toISOString();
      })
      .addCase(fetchMarketData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch market data';
      });
  },
});

export const {
  setCurrentSymbol,
  setCurrentTimeframe,
  updateMarketData,
  clearError,
} = marketDataSlice.actions;

export default marketDataSlice.reducer;