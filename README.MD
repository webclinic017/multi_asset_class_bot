+ Use working_bot_aug11_2025.py for updated code
+ Imports below are available from pip install ta \
+ from ta.momentum import RSIIndicator \
from ta.trend import SMAIndicator, MACD \
from ta.volatility import BollingerBands, AverageTrueRange \
+ Tried ta-lib and pandas_ta but encountred numpy.NaN errors to resolve Linux -> Windows migration issues \
+ Timetamp in log file name causes issues with ":" character, which is why strftime is used \
+ Backtrader cpu maxcpus options enables multiprocessing without pool
high memory usage switch 8-10 core

+ python main.py --mode live --config config/config.yaml

+ python main.py --mode backtest --config config/config.yaml

+ python main.py --mode optimize --config config/config.yaml