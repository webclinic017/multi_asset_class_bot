import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  theme: 'dark',
  sidebarOpen: true,
  notifications: [],
  loading: false,
  activeTab: 'dashboard',
  chartSettings: {
    timeframe: '1m',
    indicators: ['ema', 'volume'],
    theme: 'dark',
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action) => {
      state.theme = action.payload;
    },
    
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload;
    },
    
    addNotification: (state, action) => {
      state.notifications.push({
        id: Date.now(),
        ...action.payload,
        timestamp: new Date().toISOString(),
      });
    },
    
    removeNotification: (state, action) => {
      state.notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      );
    },
    
    clearNotifications: (state) => {
      state.notifications = [];
    },
    
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    
    setActiveTab: (state, action) => {
      state.activeTab = action.payload;
    },
    
    updateChartSettings: (state, action) => {
      state.chartSettings = { ...state.chartSettings, ...action.payload };
    },
  },
});

export const {
  setTheme,
  toggleSidebar,
  setSidebarOpen,
  addNotification,
  removeNotification,
  clearNotifications,
  setLoading,
  setActiveTab,
  updateChartSettings,
} = uiSlice.actions;

export default uiSlice.reducer;