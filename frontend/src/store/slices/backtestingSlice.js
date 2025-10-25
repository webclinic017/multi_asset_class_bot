import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const initialState = {
  backtests: [],
  currentBacktest: null,
  loading: false,
  error: null,
  progress: 0,
  sentiment: null,
  sentimentLoading: false,
  sentimentError: null,
};

export const runBacktest = createAsyncThunk(
  'backtesting/runBacktest',
  async (backtestData) => {
    const response = await fetch('/api/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backtestData),
    });
    if (!response.ok) {
      throw new Error('Failed to start backtest');
    }
    return response.json();
  }
);

export const fetchSentiment = createAsyncThunk(
  'backtesting/fetchSentiment',
  async (symbol) => {
    const response = await fetch(`/api/sentiment/${symbol}`);
    if (!response.ok) {
      throw new Error('Failed to fetch sentiment');
    }
    return response.json();
  }
);

export const fetchSessionSentiment = createAsyncThunk(
  'backtesting/fetchSessionSentiment',
  async (sessionId) => {
    const response = await fetch(`/api/sessions/${sessionId}/sentiment`);
    if (!response.ok) {
      throw new Error('Failed to fetch session sentiment');
    }
    return response.json();
  }
);

const backtestingSlice = createSlice({
  name: 'backtesting',
  initialState,
  reducers: {
    setCurrentBacktest: (state, action) => {
      state.currentBacktest = action.payload;
    },
    updateProgress: (state, action) => {
      state.progress = action.payload;
    },
    updateSentiment: (state, action) => {
      state.sentiment = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    clearSentimentError: (state) => {
      state.sentimentError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(runBacktest.pending, (state) => {
        state.loading = true;
        state.error = null;
        state.progress = 0;
      })
      .addCase(runBacktest.fulfilled, (state, action) => {
        state.loading = false;
        state.backtests.push(action.payload);
        state.currentBacktest = action.payload;
      })
      .addCase(runBacktest.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(fetchSentiment.pending, (state) => {
        state.sentimentLoading = true;
        state.sentimentError = null;
      })
      .addCase(fetchSentiment.fulfilled, (state, action) => {
        state.sentimentLoading = false;
        state.sentiment = action.payload;
      })
      .addCase(fetchSentiment.rejected, (state, action) => {
        state.sentimentLoading = false;
        state.sentimentError = action.error.message;
      })
      .addCase(fetchSessionSentiment.pending, (state) => {
        state.sentimentLoading = true;
        state.sentimentError = null;
      })
      .addCase(fetchSessionSentiment.fulfilled, (state, action) => {
        state.sentimentLoading = false;
        state.sentiment = action.payload.current_sentiment;
      })
      .addCase(fetchSessionSentiment.rejected, (state, action) => {
        state.sentimentLoading = false;
        state.sentimentError = action.error.message;
      });
  },
});

export const {
  setCurrentBacktest,
  updateProgress,
  updateSentiment,
  clearError,
  clearSentimentError
} = backtestingSlice.actions;

export default backtestingSlice.reducer;