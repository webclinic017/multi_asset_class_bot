"""
Advanced Quantitative Crypto Trading Strategy
Institutional-grade strategy with sophisticated quantitative techniques
"""

import backtrader as bt
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import talib
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class AdvancedQuantCryptoStrategy(bt.Strategy):
    """
    Advanced quantitative crypto trading strategy with:
    - Volatility regime detection
    - Multi-timeframe momentum analysis
    - Advanced mean reversion techniques
    - Dynamic position sizing with Kelly Criterion
    - Crypto-specific risk management
    - Market microstructure analysis
    - News sentiment analysis integration
    - Machine learning features
    - Sentiment-based trade filtering and exits
    """
    
    params = (
        # Volatility Regime Detection
        ('vol_lookback', 20),
        ('vol_threshold_low', 0.15),
        ('vol_threshold_high', 0.35),
        
        # Multi-timeframe Momentum
        ('momentum_short', 5),
        ('momentum_medium', 20),
        ('momentum_long', 50),
        ('momentum_threshold', 0.02),
        
        # Mean Reversion
        ('bb_period', 20),
        ('bb_std', 2.0),
        ('rsi_period', 14),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        
        # Kelly Criterion Position Sizing
        ('kelly_lookback', 100),
        ('max_kelly_fraction', 0.25),
        ('min_position_size', 0.01),
        ('max_position_size', 0.20),
        
        # Risk Management
        ('max_drawdown', 0.15),
        ('var_confidence', 0.05),
        ('correlation_threshold', 0.7),
        ('max_positions', 3),
        
        # Market Microstructure
        ('volume_ma_period', 20),
        ('price_impact_threshold', 0.001),
        ('bid_ask_spread_max', 0.005),
        
        # Machine Learning
        ('ml_lookback', 200),
        ('ml_retrain_frequency', 50),
        ('ml_confidence_threshold', 0.6),
        
        # Sentiment Analysis
        ('sentiment_weight', 0.3),
        ('sentiment_threshold', 0.1),
        ('news_lookback_hours', 24),
        
        # General
        ('printlog', False),
        ('debug_mode', False)
    )

    def __init__(self):
        """Initialize advanced quantitative crypto strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.datavolume = self.datas[0].volume
        
        # Order and position management
        self.order = None
        self.position_entry_price = None
        self.position_entry_time = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown_current = 0.0
        self.peak_value = 0.0
        
        # Volatility regime tracking
        self.current_regime = 'normal'  # low, normal, high
        self.regime_history = []
        
        # Multi-timeframe momentum
        self.momentum_signals = {'short': 0, 'medium': 0, 'long': 0}
        
        # Kelly Criterion data
        self.trade_returns = []
        self.kelly_fraction = 0.1
        
        # Machine Learning
        self.ml_model = None
        self.ml_features = []
        self.ml_predictions = []
        self.bars_since_retrain = 0
        
        # Market microstructure
        self.volume_profile = []
        self.price_impact_history = []
        
        # Sentiment data
        self.sentiment_score = 0.0
        self.sentiment_history = []
        
        # Initialize technical indicators
        self._init_indicators()
        
        # Initialize ML features
        self._init_ml_features()
        
        self.logger.info("Advanced Quantitative Crypto Strategy initialized")

    def _init_indicators(self):
        """Initialize technical indicators"""
        # Volatility indicators
        self.atr = bt.indicators.ATR(period=self.p.vol_lookback)
        self.volatility = bt.indicators.StdDev(self.dataclose, period=self.p.vol_lookback)
        
        # Momentum indicators
        self.momentum_short = bt.indicators.Momentum(period=self.p.momentum_short)
        self.momentum_medium = bt.indicators.Momentum(period=self.p.momentum_medium)
        self.momentum_long = bt.indicators.Momentum(period=self.p.momentum_long)
        
        # Mean reversion indicators
        self.bollinger = bt.indicators.BollingerBands(period=self.p.bb_period, devfactor=self.p.bb_std)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        
        # Volume indicators
        self.volume_ma = bt.indicators.SMA(self.datavolume, period=self.p.volume_ma_period)
        self.volume_ratio = self.datavolume / self.volume_ma
        
        # Additional indicators for ML features
        self.macd = bt.indicators.MACD()
        self.stochastic = bt.indicators.Stochastic()
        self.williams_r = bt.indicators.WilliamsR()
        self.cci = bt.indicators.CommodityChannelIndex()

    def _init_ml_features(self):
        """Initialize machine learning feature extraction"""
        self.feature_names = [
            'returns_1', 'returns_5', 'returns_20',
            'volatility', 'volume_ratio', 'rsi', 'macd_signal',
            'bb_position', 'momentum_short', 'momentum_long',
            'stoch_k', 'williams_r', 'cci', 'atr_ratio'
        ]

    def next(self):
        """Main strategy logic"""
        # Minimum data requirement check - be more conservative
        min_required = max(self.p.momentum_long, self.p.bb_period, self.p.vol_lookback) + 10
        if len(self.data) < min_required:
            return
            
        try:
            # Update regime detection
            self._update_volatility_regime()
            
            # Update momentum signals
            self._update_momentum_signals()
            
            # Update Kelly Criterion
            self._update_kelly_criterion()
            
            # Update ML model if needed (only if we have enough data)
            if len(self.data) >= self.p.ml_lookback:
                if self.bars_since_retrain >= self.p.ml_retrain_frequency:
                    self._retrain_ml_model()
                    self.bars_since_retrain = 0
                else:
                    self.bars_since_retrain += 1
            
            # Get ML prediction
            ml_signal = self._get_ml_prediction()
            
            # Update sentiment analysis
            self._update_sentiment_analysis()
            
            # Calculate position size using Kelly Criterion
            position_size = self._calculate_kelly_position_size()
            
            # Risk management checks
            if not self._risk_management_check():
                return
            
            # Generate trading signals
            signal = self._generate_composite_signal(ml_signal)
            
            # Execute trades based on signals
            self._execute_trades(signal, position_size)
            
            # Update performance metrics
            self._update_performance_metrics()
            
        except (IndexError, ValueError, ZeroDivisionError) as e:
            self.logger.warning(f"Strategy execution error: {e}")
            return

    def _update_volatility_regime(self):
        """Update volatility regime detection"""
        if len(self.data) < self.p.vol_lookback:
            return
            
        current_vol = self.volatility[0]
        
        if current_vol < self.p.vol_threshold_low:
            regime = 'low'
        elif current_vol > self.p.vol_threshold_high:
            regime = 'high'
        else:
            regime = 'normal'
        
        if regime != self.current_regime:
            self.log(f'Volatility regime change: {self.current_regime} -> {regime} (vol: {current_vol:.4f})')
            self.current_regime = regime
        
        self.regime_history.append(regime)
        if len(self.regime_history) > 100:
            self.regime_history.pop(0)

    def _update_momentum_signals(self):
        """Update multi-timeframe momentum analysis"""
        if len(self.data) < self.p.momentum_long:
            return
            
        # Calculate momentum scores
        short_mom = (self.dataclose[0] - self.dataclose[-self.p.momentum_short]) / self.dataclose[-self.p.momentum_short]
        medium_mom = (self.dataclose[0] - self.dataclose[-self.p.momentum_medium]) / self.dataclose[-self.p.momentum_medium]
        long_mom = (self.dataclose[0] - self.dataclose[-self.p.momentum_long]) / self.dataclose[-self.p.momentum_long]
        
        # Convert to signals
        self.momentum_signals['short'] = 1 if short_mom > self.p.momentum_threshold else (-1 if short_mom < -self.p.momentum_threshold else 0)
        self.momentum_signals['medium'] = 1 if medium_mom > self.p.momentum_threshold else (-1 if medium_mom < -self.p.momentum_threshold else 0)
        self.momentum_signals['long'] = 1 if long_mom > self.p.momentum_threshold else (-1 if long_mom < -self.p.momentum_threshold else 0)

    def _update_kelly_criterion(self):
        """Update Kelly Criterion calculation"""
        if len(self.trade_returns) < 10:
            self.kelly_fraction = 0.1
            return
        
        returns = np.array(self.trade_returns[-self.p.kelly_lookback:])
        
        if len(returns) == 0:
            return
            
        # Calculate Kelly fraction
        mean_return = np.mean(returns)
        variance = np.var(returns)
        
        if variance > 0:
            kelly = mean_return / variance
            self.kelly_fraction = np.clip(kelly, 0, self.p.max_kelly_fraction)
        else:
            self.kelly_fraction = 0.1

    def _retrain_ml_model(self):
        """Retrain machine learning model"""
        if len(self.data) < self.p.ml_lookback:
            return
            
        try:
            # Extract features and labels
            features, labels = self._extract_ml_data()
            
            if len(features) < 50:  # Need minimum data
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.2, random_state=42
            )
            
            # Train model
            self.ml_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.ml_model.fit(X_train, y_train)
            
            # Evaluate model
            train_score = self.ml_model.score(X_train, y_train)
            test_score = self.ml_model.score(X_test, y_test)
            
            self.log(f'ML model retrained - Train: {train_score:.3f}, Test: {test_score:.3f}')
            
        except Exception as e:
            self.logger.warning(f"ML model training failed: {e}")

    def _extract_ml_data(self):
        """Extract features and labels for ML model"""
        features = []
        labels = []
        
        lookback = min(len(self.data), self.p.ml_lookback)
        
        for i in range(20, lookback - 5):  # Need some lookback and forward data
            try:
                # Extract features
                feature_vector = self._extract_features_at_bar(i)
                
                # Calculate future return (label)
                future_return = (self.dataclose[-lookback + i + 5] - self.dataclose[-lookback + i]) / self.dataclose[-lookback + i]
                
                # Convert to classification label
                if future_return > 0.01:
                    label = 1  # Buy
                elif future_return < -0.01:
                    label = -1  # Sell
                else:
                    label = 0  # Hold
                
                features.append(feature_vector)
                labels.append(label)
                
            except (IndexError, ZeroDivisionError):
                continue
        
        return np.array(features), np.array(labels)

    def _extract_features_at_bar(self, bar_offset):
        """Extract feature vector at specific bar"""
        try:
            # Price-based features
            returns_1 = (self.dataclose[-bar_offset] - self.dataclose[-bar_offset - 1]) / self.dataclose[-bar_offset - 1]
            returns_5 = (self.dataclose[-bar_offset] - self.dataclose[-bar_offset - 5]) / self.dataclose[-bar_offset - 5]
            returns_20 = (self.dataclose[-bar_offset] - self.dataclose[-bar_offset - 20]) / self.dataclose[-bar_offset - 20]
            
            # Technical indicators
            volatility = self.volatility[-bar_offset] if len(self.volatility) > bar_offset else 0
            volume_ratio = self.volume_ratio[-bar_offset] if len(self.volume_ratio) > bar_offset else 1
            rsi = self.rsi[-bar_offset] if len(self.rsi) > bar_offset else 50
            macd_signal = self.macd.macd[-bar_offset] - self.macd.signal[-bar_offset] if len(self.macd.macd) > bar_offset else 0
            
            # Bollinger Bands position
            bb_mid = self.bollinger.mid[-bar_offset] if len(self.bollinger.mid) > bar_offset else self.dataclose[-bar_offset]
            bb_position = (self.dataclose[-bar_offset] - bb_mid) / bb_mid if bb_mid > 0 else 0
            
            # Momentum
            momentum_short = self.momentum_short[-bar_offset] if len(self.momentum_short) > bar_offset else 0
            momentum_long = self.momentum_long[-bar_offset] if len(self.momentum_long) > bar_offset else 0
            
            # Other indicators
            stoch_k = self.stochastic.percK[-bar_offset] if len(self.stochastic.percK) > bar_offset else 50
            williams_r = self.williams_r[-bar_offset] if len(self.williams_r) > bar_offset else -50
            cci = self.cci[-bar_offset] if len(self.cci) > bar_offset else 0
            atr_ratio = self.atr[-bar_offset] / self.dataclose[-bar_offset] if len(self.atr) > bar_offset and self.dataclose[-bar_offset] > 0 else 0
            
            return [
                returns_1, returns_5, returns_20,
                volatility, volume_ratio, rsi, macd_signal,
                bb_position, momentum_short, momentum_long,
                stoch_k, williams_r, cci, atr_ratio
            ]
            
        except (IndexError, ZeroDivisionError):
            return [0] * len(self.feature_names)

    def _get_ml_prediction(self):
        """Get ML model prediction"""
        if self.ml_model is None:
            return 0
        
        try:
            # Extract current features
            current_features = self._extract_features_at_bar(0)
            features_array = np.array(current_features).reshape(1, -1)
            
            # Get prediction and probability
            prediction = self.ml_model.predict(features_array)[0]
            probabilities = self.ml_model.predict_proba(features_array)[0]
            
            # Check confidence
            max_prob = np.max(probabilities)
            
            if max_prob < self.p.ml_confidence_threshold:
                return 0  # Low confidence, no signal
            
            return prediction
            
        except Exception as e:
            self.logger.warning(f"ML prediction failed: {e}")
            return 0

    def _update_sentiment_analysis(self):
        """Update sentiment analysis (placeholder for integration)"""
        # This would integrate with news sentiment analysis
        # For now, using a simple momentum-based proxy
        try:
            if len(self.data) >= 5:
                recent_returns = [(self.dataclose[-i] - self.dataclose[-i-1]) / self.dataclose[-i-1] for i in range(1, 5)]
                self.sentiment_score = np.tanh(np.mean(recent_returns) * 10)  # Normalize to [-1, 1]
            else:
                self.sentiment_score = 0.0
                
            self.sentiment_history.append(self.sentiment_score)
            if len(self.sentiment_history) > 100:
                self.sentiment_history.pop(0)
                
        except (IndexError, ZeroDivisionError):
            self.sentiment_score = 0.0

    def _calculate_kelly_position_size(self):
        """Calculate position size using Kelly Criterion"""
        base_size = self.kelly_fraction
        
        # Adjust for volatility regime
        if self.current_regime == 'high':
            base_size *= 0.5  # Reduce size in high volatility
        elif self.current_regime == 'low':
            base_size *= 1.2  # Increase size in low volatility
        
        # Adjust for sentiment
        sentiment_adjustment = 1 + (self.sentiment_score * self.p.sentiment_weight)
        base_size *= sentiment_adjustment
        
        # Apply limits
        position_size = np.clip(base_size, self.p.min_position_size, self.p.max_position_size)
        
        return position_size

    def _risk_management_check(self):
        """Comprehensive risk management checks"""
        # Check maximum drawdown
        current_value = self.broker.get_value()
        if self.peak_value == 0:
            self.peak_value = current_value
        else:
            self.peak_value = max(self.peak_value, current_value)
        
        current_drawdown = (self.peak_value - current_value) / self.peak_value
        
        if current_drawdown > self.p.max_drawdown:
            self.log(f'Maximum drawdown exceeded: {current_drawdown:.3f}')
            return False
        
        # Check position limits
        if len(self.broker.positions) >= self.p.max_positions:
            return False
        
        return True

    def _generate_composite_signal(self, ml_signal):
        """Generate composite trading signal"""
        signals = []
        weights = []
        
        # ML signal
        if ml_signal != 0:
            signals.append(ml_signal)
            weights.append(0.4)
        
        # Momentum signals
        momentum_score = (
            self.momentum_signals['short'] * 0.5 +
            self.momentum_signals['medium'] * 0.3 +
            self.momentum_signals['long'] * 0.2
        )
        if abs(momentum_score) > 0.1:
            signals.append(np.sign(momentum_score))
            weights.append(0.3)
        
        # Mean reversion signal
        if self.rsi[0] < self.p.rsi_oversold and self.dataclose[0] < self.bollinger.bot[0]:
            signals.append(1)  # Oversold, buy signal
            weights.append(0.2)
        elif self.rsi[0] > self.p.rsi_overbought and self.dataclose[0] > self.bollinger.top[0]:
            signals.append(-1)  # Overbought, sell signal
            weights.append(0.2)
        
        # Sentiment signal
        if abs(self.sentiment_score) > self.p.sentiment_threshold:
            signals.append(np.sign(self.sentiment_score))
            weights.append(0.1)
        
        # Calculate weighted signal
        if not signals:
            return 0
        
        weighted_signal = np.average(signals, weights=weights)
        
        # Apply threshold
        if weighted_signal > 0.3:
            return 1
        elif weighted_signal < -0.3:
            return -1
        else:
            return 0

    def _execute_trades(self, signal, position_size):
        """Execute trades based on signals"""
        if self.order:
            return
        
        current_price = self.dataclose[0]
        cash = self.broker.get_cash()
        
        if signal == 1 and not self.position:  # Buy signal
            # Calculate position size in shares
            position_value = cash * position_size
            shares = int(position_value / current_price)
            
            if shares > 0:
                self.order = self.buy(size=shares)
                self.position_entry_price = current_price
                self.position_entry_time = len(self.data)
                self.log(f'BUY CREATE - Price: {current_price:.4f}, Size: {shares}, Kelly: {self.kelly_fraction:.3f}')
        
        elif signal == -1 and self.position:  # Sell signal (close long)
            self.order = self.close()
            self.log(f'SELL CREATE - Price: {current_price:.4f}, Reason: Signal')
        
        # Stop loss and take profit
        elif self.position and self.position_entry_price:
            pnl_pct = (current_price - self.position_entry_price) / self.position_entry_price
            
            # Dynamic stop loss based on volatility
            stop_loss_pct = -0.03 * (1 + self.volatility[0])  # Wider stops in high vol
            take_profit_pct = 0.06 * (1 + self.volatility[0])  # Wider targets in high vol
            
            if pnl_pct <= stop_loss_pct:
                self.order = self.close()
                self.log(f'STOP LOSS - Price: {current_price:.4f}, PnL: {pnl_pct:.3f}')
            elif pnl_pct >= take_profit_pct:
                self.order = self.close()
                self.log(f'TAKE PROFIT - Price: {current_price:.4f}, PnL: {pnl_pct:.3f}')

    def _update_performance_metrics(self):
        """Update performance tracking metrics"""
        current_value = self.broker.get_value()
        
        # Update peak value for drawdown calculation
        if current_value > self.peak_value:
            self.peak_value = current_value

    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            self.logger.info(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Order notification"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED - Price: {order.executed.price:.4f}, Size: {order.executed.size}')
            else:
                self.log(f'SELL EXECUTED - Price: {order.executed.price:.4f}, Size: {order.executed.size}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """Trade notification"""
        if not trade.isclosed:
            return

        self.trade_count += 1
        trade_return = trade.pnl / (trade.price * trade.size) if trade.size > 0 else 0
        self.trade_returns.append(trade_return)
        
        # Keep only recent trades for Kelly calculation
        if len(self.trade_returns) > self.p.kelly_lookback:
            self.trade_returns.pop(0)

        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        self.total_pnl += trade.pnl
        self.log(f'TRADE CLOSED - PnL: {trade.pnl:.4f}, Return: {trade_return:.4f}')

    def stop(self):
        """Strategy completion"""
        final_value = self.broker.get_value()
        initial_capital = 10000
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        win_rate = (self.winning_trades / max(self.trade_count, 1)) * 100
        
        self.log('=== ADVANCED QUANT CRYPTO STRATEGY RESULTS ===')
        self.log(f'Final Value: ${final_value:.2f}')
        self.log(f'Total Return: {total_return:.2f}%')
        self.log(f'Total Trades: {self.trade_count}')
        self.log(f'Win Rate: {win_rate:.1f}%')
        self.log(f'Kelly Fraction: {self.kelly_fraction:.3f}')
        self.log(f'Current Regime: {self.current_regime}')
        self.log(f'Sentiment Score: {self.sentiment_score:.3f}')

if __name__ == "__main__":
    print("Advanced Quantitative Crypto Strategy loaded successfully")
    print("Features:")
    print("- Volatility regime detection")
    print("- Multi-timeframe momentum analysis")
    print("- Advanced mean reversion techniques")
    print("- Dynamic position sizing with Kelly Criterion")
    print("- Crypto-specific risk management")
    print("- Market microstructure analysis")
    print("- Machine learning features")
    print("- Sentiment-based trade filtering")