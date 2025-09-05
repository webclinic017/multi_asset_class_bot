import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const initialState = {
  backtests: [],
  currentBacktest: null,
  loading: false,
  error: null,
  progress: 0,
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
    clearError: (state) => {
      state.error = null;
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
      });
  },
});

export const { setCurrentBacktest, updateProgress, clearError } = backtestingSlice.actions;
export default backtestingSlice.reducer;