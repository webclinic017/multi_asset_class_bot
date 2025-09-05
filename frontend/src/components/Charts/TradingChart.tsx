import React, { useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { createChart, IChartApi, ISeriesApi, CandlestickData, LineData } from 'lightweight-charts';

interface TradingChartProps {
  symbol: string;
  timeframe: string;
  height?: number;
  showTrades?: boolean;
  showIndicators?: boolean;
}

interface Trade {
  time: number;
  price: number;
  side: 'BUY' | 'SELL';
  pnl?: number;
}

const ChartContainer = styled.div<{ height: number }>`
  width: 100%;
  height: ${props => props.height}px;
  position: relative;
  background: ${props => props.theme.colors.surface};
  border-radius: 4px;
  overflow: hidden;
`;

const ChartControls = styled.div`
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  gap: 5px;
`;

const ControlButton = styled.button<{ active?: boolean }>`
  background: ${props => props.active ? props.theme.colors.primary : props.theme.colors.surface};
  color: ${props => props.active ? 'white' : props.theme.colors.text};
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: ${props => props.theme.colors.primary};
    color: white;
  }
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
`;

const TradingChart: React.FC<TradingChartProps> = ({
  symbol,
  timeframe,
  height = 400,
  showTrades = false,
  showIndicators = true,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const rsiSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeIndicators, setActiveIndicators] = useState({
    ema: true,
    rsi: false,
    volume: true,
  });

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#1a1a1a' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#485c7b',
      },
      timeScale: {
        borderColor: '#485c7b',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Create candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#4CAF50',
      downColor: '#F44336',
      borderDownColor: '#F44336',
      borderUpColor: '#4CAF50',
      wickDownColor: '#F44336',
      wickUpColor: '#4CAF50',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Create volume series
    if (activeIndicators.volume) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume',
      });
      
      chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

      volumeSeriesRef.current = volumeSeries;
    }

    // Create EMA series
    if (activeIndicators.ema) {
      const emaSeries = chart.addLineSeries({
        color: '#FF6B35',
        lineWidth: 2,
        title: 'EMA(21)',
      });
      emaSeriesRef.current = emaSeries;
    }

    // Load market data
    loadMarketData();

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [symbol, timeframe, height, activeIndicators]);

  const loadMarketData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch market data from API
      const response = await fetch(`/api/market-data/${symbol}?timeframe=${timeframe}&limit=500`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch market data');
      }

      const data = await response.json();

      if (data.length === 0) {
        // Generate sample data for demonstration
        const sampleData = generateSampleData();
        updateChartData(sampleData);
      } else {
        // Convert API data to chart format
        const chartData = data.map((item: any) => ({
          time: new Date(item.timestamp).getTime() / 1000,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
          volume: item.volume,
        }));
        
        updateChartData(chartData);
      }

      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setLoading(false);
      
      // Generate sample data on error
      const sampleData = generateSampleData();
      updateChartData(sampleData);
    }
  };

  const generateSampleData = () => {
    const data = [];
    const basePrice = 1.1000;
    let currentPrice = basePrice;
    const now = Math.floor(Date.now() / 1000);
    const interval = timeframe === '1m' ? 60 : timeframe === '5m' ? 300 : 3600;

    for (let i = 500; i >= 0; i--) {
      const time = now - (i * interval);
      const volatility = 0.0005;
      
      const open = currentPrice;
      const change = (Math.random() - 0.5) * volatility * 2;
      const high = open + Math.abs(change) + Math.random() * volatility;
      const low = open - Math.abs(change) - Math.random() * volatility;
      const close = open + change;
      const volume = Math.random() * 1000000;

      data.push({
        time,
        open,
        high,
        low,
        close,
        volume,
      });

      currentPrice = close;
    }

    return data;
  };

  const updateChartData = (data: any[]) => {
    if (!candlestickSeriesRef.current) return;

    // Update candlestick data
    const candlestickData: CandlestickData[] = data.map(item => ({
      time: item.time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    candlestickSeriesRef.current.setData(candlestickData);

    // Update volume data
    if (volumeSeriesRef.current) {
      const volumeData = data.map(item => ({
        time: item.time,
        value: item.volume,
        color: item.close >= item.open ? '#4CAF50' : '#F44336',
      }));
      volumeSeriesRef.current.setData(volumeData);
    }

    // Update EMA data
    if (emaSeriesRef.current) {
      const emaData = calculateEMA(data, 21);
      emaSeriesRef.current.setData(emaData);
    }

    // Add trade markers if enabled
    if (showTrades) {
      addTradeMarkers();
    }
  };

  const calculateEMA = (data: any[], period: number): LineData[] => {
    const emaData: LineData[] = [];
    const multiplier = 2 / (period + 1);
    let ema = data[0]?.close || 0;

    data.forEach((item, index) => {
      if (index === 0) {
        ema = item.close;
      } else {
        ema = (item.close - ema) * multiplier + ema;
      }

      emaData.push({
        time: item.time,
        value: ema,
      });
    });

    return emaData;
  };

  const addTradeMarkers = () => {
    if (!candlestickSeriesRef.current) return;

    // Sample trade markers
    const trades: Trade[] = [
      { time: Math.floor(Date.now() / 1000) - 3600, price: 1.1050, side: 'BUY', pnl: 15.5 },
      { time: Math.floor(Date.now() / 1000) - 1800, price: 1.1075, side: 'SELL', pnl: -8.2 },
    ];

    const markers = trades.map(trade => ({
      time: trade.time,
      position: 'belowBar' as const,
      color: trade.side === 'BUY' ? '#4CAF50' : '#F44336',
      shape: trade.side === 'BUY' ? 'arrowUp' as const : 'arrowDown' as const,
      text: `${trade.side} ${trade.pnl ? (trade.pnl > 0 ? '+' : '') + trade.pnl.toFixed(1) : ''}`,
    }));

    candlestickSeriesRef.current.setMarkers(markers);
  };

  const toggleIndicator = (indicator: keyof typeof activeIndicators) => {
    setActiveIndicators(prev => ({
      ...prev,
      [indicator]: !prev[indicator],
    }));
  };

  return (
    <ChartContainer height={height}>
      <ChartControls>
        <ControlButton
          active={activeIndicators.ema}
          onClick={() => toggleIndicator('ema')}
        >
          EMA
        </ControlButton>
        <ControlButton
          active={activeIndicators.rsi}
          onClick={() => toggleIndicator('rsi')}
        >
          RSI
        </ControlButton>
        <ControlButton
          active={activeIndicators.volume}
          onClick={() => toggleIndicator('volume')}
        >
          Volume
        </ControlButton>
      </ChartControls>
      
      <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />
      
      {loading && (
        <LoadingOverlay>
          Loading chart data...
        </LoadingOverlay>
      )}
      
      {error && (
        <LoadingOverlay>
          Error: {error}
        </LoadingOverlay>
      )}
    </ChartContainer>
  );
};

export default TradingChart;