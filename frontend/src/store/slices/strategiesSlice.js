import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const initialState = {
  strategies: [],
  currentStrategy: null,
  loading: false,
  error: null,
};

export const fetchStrategies = createAsyncThunk(
  'strategies/fetchStrategies',
  async () => {
    const response = await fetch('/api/strategies');
    if (!response.ok) {
      throw new Error('Failed to fetch strategies');
    }
    return response.json();
  }
);

export const createStrategy = createAsyncThunk(
  'strategies/createStrategy',
  async (strategyData) => {
    const response = await fetch('/api/strategies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategyData),
    });
    if (!response.ok) {
      throw new Error('Failed to create strategy');
    }
    return response.json();
  }
);

const strategiesSlice = createSlice({
  name: 'strategies',
  initialState,
  reducers: {
    setCurrentStrategy: (state, action) => {
      state.currentStrategy = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchStrategies.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStrategies.fulfilled, (state, action) => {
        state.loading = false;
        state.strategies = action.payload;
      })
      .addCase(fetchStrategies.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(createStrategy.fulfilled, (state, action) => {
        state.strategies.push(action.payload);
      });
  },
});

export const { setCurrentStrategy, clearError } = strategiesSlice.actions;
export default strategiesSlice.reducer;