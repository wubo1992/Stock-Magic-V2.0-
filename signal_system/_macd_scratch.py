#!/usr/bin/env python3
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '.')
from data import fetcher

symbols = ['NVGS', 'RAMP', 'D', 'CPSH', 'DHX', 'CIBR', 'ETON', 'EVTV', 'HIVE']
print(f'Fetching {len(symbols)} symbols...')
data = fetcher.fetch(symbols, history_days=504)
print(f'Got {len(data)} symbols\n')

results = {}
for t, df in data.items():
    close = df['close']
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal

    last = len(df) - 1
    today = df.index[last]
    today_hist = hist.iloc[last]
    yes_hist = hist.iloc[last-1] if last >= 1 else 0

    daily_crossed = (yes_hist < 0) and (today_hist > 0)

    weekly = df.resample('W').agg({'close': 'last', 'open': 'first', 'high': 'max', 'low': 'min', 'volume': 'sum'})
    w_close = weekly['close'].dropna()
    w_ema12 = w_close.ewm(span=12, adjust=False).mean()
    w_ema26 = w_close.ewm(span=26, adjust=False).mean()
    w_macd = w_ema12 - w_ema26
    w_signal = w_macd.ewm(span=9, adjust=False).mean()
    w_hist = w_macd - w_signal

    w_last = len(w_close) - 1
    w_today_macd = w_macd.iloc[w_last]
    w_today_signal = w_signal.iloc[w_last]
    w_today_hist = w_hist.iloc[w_last]
    w_yes_hist = w_hist.iloc[w_last-1] if w_last >= 1 else 0

    weekly_crossed = (w_yes_hist < 0) and (w_today_hist > 0)
    weekly_bullish = (w_today_macd > w_today_signal) and (w_today_hist > 0)

    if daily_crossed and weekly_crossed:
        cat = 'B'
    elif daily_crossed and weekly_bullish:
        cat = 'A'
    elif daily_crossed or weekly_crossed:
        cat = 'D'
    else:
        cat = 'C'

    results[t] = {
        'day_cross': daily_crossed,
        'week_cross': weekly_crossed,
        'week_bull': weekly_bullish,
        'cat': cat,
        'date': str(today.date())
    }
    print(f'{t}: 日金叉={daily_crossed}, 周金叉={weekly_crossed}, 周多头={weekly_bullish}, 分类={cat}')

print()
print('='*50)
print('B类(日+周双金叉):', [k for k,v in results.items() if v['cat']=='B'])
print('A类(日金叉+周多头):', [k for k,v in results.items() if v['cat']=='A'])
print('D类(日或周金叉):', [k for k,v in results.items() if v['cat']=='D'])
print('C类(无金叉):', [k for k,v in results.items() if v['cat']=='C'])