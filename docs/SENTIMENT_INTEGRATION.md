# Sentiment Analysis Integration Guide

## Overview

The sentiment analyzer has been fully integrated into the multi_asset_bot for both backend and frontend, providing real-time market sentiment analysis during backtesting and live trading.

## Features

### Backend Integration

1. **Sentiment API Endpoints** (`api/main.py`)
   - `GET /api/sentiment/{symbol}` - Get current sentiment for a symbol
   - `GET /api/sentiment/{symbol}/events` - Get upcoming news events
   - `GET /api/sentiment/{symbol}/pre-event-strategy` - Get pre-event trading strategy
   - `GET /api/sessions/{session_id}/sentiment` - Get sentiment history for a session

2. **Backtest Integration**
   - Sentiment data is fetched at the start of each backtest
   - Real-time sentiment updates are broadcast via WebSocket
   - Sentiment scores are logged for analysis

3. **Sentiment Analyzer** (`sentiment/futures_sentiment_analyzer.py`)
   - **FuturesSentimentAnalyzer**: Analyzes news from RSS feeds using TextBlob
   - **CommodityNewsEventMonitor**: Monitors high-impact economic events
   - **SocialSentimentAnalyzer**: Analyzes Reddit sentiment (optional)

### Frontend Integration

1. **Redux Store** (`frontend/src/store/slices/backtestingSlice.js`)
   - `fetchSentiment(symbol)` - Async action to fetch sentiment
   - `fetchSessionSentiment(sessionId)` - Fetch sentiment for a session
   - `updateSentiment(data)` - Update sentiment from WebSocket
   - State: `sentiment`, `sentimentLoading`, `sentimentError`

2. **Sentiment Indicator Component** (`frontend/src/components/Sentiment/SentimentIndicator.jsx`)
   - Visual display of sentiment score (-1 to 1)
   - Signal indicator (BULLISH/BEARISH/NEUTRAL)
   - Confidence level and news count
   - Real-time updates via WebSocket

3. **Backtesting Page Integration** (`frontend/src/pages/Backtesting/Backtesting.jsx`)
   - Sentiment panel displayed alongside backtest form
   - Automatic sentiment updates when symbol changes
   - WebSocket integration for real-time sentiment updates

## Usage

### Running the Web Server with Sentiment

```bash
run_webserver.bat --mode server-only
```

The sentiment analyzer will automatically initialize when the server starts.

### API Examples

#### Get Sentiment for a Symbol

```bash
curl http://localhost:8000/api/sentiment/ES?hours_back=24
```

Response:
```json
{
  "symbol": "ES",
  "sentiment_score": 0.35,
  "news_count": 15,
  "confidence": 0.75,
  "signal": "BULLISH",
  "timestamp": "2024-01-15T10:30:00",
  "category": "indices"
}
```

#### Get Upcoming Events

```bash
curl http://localhost:8000/api/sentiment/CL/events?minutes_ahead=60
```

Response:
```json
{
  "symbol": "CL",
  "events": [
    {
      "event": "eia_crude_inventory",
      "time": "2024-01-15T10:30:00",
      "minutes_until": 45,
      "impact": "HIGH",
      "action": "TIGHTEN_STOPS"
    }
  ],
  "timestamp": "2024-01-15T09:45:00"
}
```

### Frontend Usage

The sentiment indicator automatically appears on the Backtesting page:

1. Select a symbol from the dropdown
2. Sentiment data loads automatically
3. View sentiment score, signal, and confidence
4. Monitor news count and category

## Supported Symbols

### Futures
- **Energy**: CL (Crude Oil), NG (Natural Gas), RB (Gasoline), HO (Heating Oil)
- **Metals**: GC (Gold), SI (Silver), HG (Copper)
- **Indices**: ES (S&P 500), NQ (NASDAQ), YM (Dow)
- **Agriculture**: ZC (Corn), ZS (Soybeans), ZW (Wheat)
- **Financial**: ZN (10-Year T-Note)

### Forex
- EUR_USD, GBP_USD, USD_JPY, AUD_USD, etc.

### Crypto
- BTC_USD, ETH_USD, SOL_USD

## Sentiment Data Sources

### Free RSS Feeds
- **Reuters**: Business and commodity news
- **EIA**: Energy Information Administration
- **USDA**: Agricultural reports
- **Kitco**: Precious metals news
- **MarketWatch**: Financial markets
- **CNBC**: Business news

### News Event Calendar
- EIA Crude Inventory (Weekly, Wednesday 10:30 AM ET)
- EIA Gas Storage (Weekly, Thursday 10:30 AM ET)
- FOMC Meetings (8x/year)
- CPI Reports (Monthly)
- Non-Farm Payrolls (Monthly, First Friday)
- USDA WASDE Reports (Monthly)

## Sentiment Scoring

- **Score Range**: -1.0 (Very Bearish) to +1.0 (Very Bullish)
- **Signals**:
  - BULLISH: score > 0.3
  - BEARISH: score < -0.3
  - NEUTRAL: -0.3 ≤ score ≤ 0.3

- **Confidence**: Based on number of relevant news articles (0-1)
- **Time Decay**: Recent news weighted more heavily

## WebSocket Events

### Sentiment Update
```json
{
  "type": "sentiment_update",
  "session_id": 123,
  "sentiment": {
    "symbol": "ES",
    "score": 0.35,
    "signal": "BULLISH",
    "confidence": 0.75,
    "news_count": 15
  }
}
```

## Configuration

### Backend Configuration
The sentiment analyzer is initialized in `api/main.py`:

```python
sentiment_analyzer = FuturesSentimentAnalyzer()
news_monitor = CommodityNewsEventMonitor()
```

### Frontend Configuration
Redux store is configured in `frontend/src/store/store.js` with the backtesting slice.

## Limitations

1. **Historical Data**: Sentiment analysis uses current news, not historical sentiment
2. **Backtest Caveat**: During backtests, sentiment shows current market sentiment for reference only
3. **Rate Limits**: RSS feeds may have rate limits; sentiment updates every hour by default
4. **Free Sources**: Uses only free news sources; premium APIs not included

## Future Enhancements

1. **Historical Sentiment Storage**: Store sentiment data for historical analysis
2. **Sentiment-Based Signals**: Integrate sentiment into strategy signals
3. **Custom News Sources**: Add configurable news sources
4. **Sentiment Alerts**: Real-time alerts for significant sentiment changes
5. **Social Media Integration**: Enhanced Reddit/Twitter sentiment analysis

## Troubleshooting

### Sentiment Not Loading
- Check if backend server is running
- Verify internet connection for RSS feeds
- Check browser console for errors

### WebSocket Not Connecting
- Ensure WebSocket endpoint is accessible
- Check firewall settings
- Verify port 8000 is not blocked

### No News Data
- Some symbols may have limited news coverage
- Try a more popular symbol (ES, CL, GC)
- Check if RSS feeds are accessible

## Testing

To test the sentiment integration:

1. Start the web server:
   ```bash
   run_webserver.bat --mode server-only
   ```

2. Open browser to `http://localhost:8000`

3. Navigate to Backtesting page

4. Select a symbol (e.g., ES, CL, GC)

5. Verify sentiment indicator appears with:
   - Sentiment score
   - Signal (BULLISH/BEARISH/NEUTRAL)
   - Confidence level
   - News count

6. Run a backtest and verify sentiment updates via WebSocket

## Support

For issues or questions:
- Check logs in `logs/trading_bot.log`
- Review API documentation at `http://localhost:8000/docs`
- Examine WebSocket messages in browser console

## License

This sentiment integration uses free, publicly available news sources and is intended for educational and research purposes only.