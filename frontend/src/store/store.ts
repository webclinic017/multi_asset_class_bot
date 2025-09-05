import { configureStore } from '@reduxjs/toolkit';
import tradingReducer from './slices/tradingSlice';
import marketDataReducer from './slices/marketDataSlice';
import strategiesReducer from './slices/strategiesSlice';
import backtestingReducer from './slices/backtestingSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    trading: tradingReducer,
    marketData: marketDataReducer,
    strategies: strategiesReducer,
    backtesting: backtestingReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;