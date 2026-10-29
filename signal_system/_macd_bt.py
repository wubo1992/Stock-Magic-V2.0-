#!/usr/bin/env python3
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '.')
from data import fetcher

cutoff = pd.Timestamp('2025-05-19', tz='UTC')
symbols = ['D', 'RAMP', 'CPSH']
print(f'Cutoff: {cutoff}')
data = fetcher.fetch(symbols, history_days=730)
print(f'Got {len(data)} symbols\n')

for holding in [5, 10, 20]:
    print(f'\n{"="*60}')
    print(f'持有 {holding} 天')
    print(f'{"="*60}')

    for t, df in data.items():
        close = df['close']
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        weekly = df.resample('W').agg({'close': 'last', 'open': 'first', 'high': 'max', 'low': 'min', 'volume': 'sum'})
        w_close = weekly['close'].dropna()
        w_ema12 = w_close.ewm(span=12, adjust=False).mean()
        w_ema26 = w_close.ewm(span=26, adjust=False).mean()
        w_macd = w_ema12 - w_ema26
        w_signal = w_macd.ewm(span=9, adjust=False).mean()
        w_hist = w_macd - w_signal

        trades = []
        n = len(df)
        for i in range(1, n):
            daily_date = df.index[i]
            if daily_date < cutoff:
                continue

            today_hist = hist.iloc[i]
            yes_hist = hist.iloc[i-1]
            daily_crossed = (yes_hist < 0) and (today_hist > 0)

            w_idx = w_close.index.get_indexer([daily_date], method='pad')[0]
            if w_idx < 0:
                w_idx = 0
            if w_idx >= len(w_hist):
                continue
            w_today_hist = w_hist.iloc[w_idx]
            w_yes_idx = max(w_idx - 1, 0)
            w_yes_hist = w_hist.iloc[w_yes_idx]
            w_today_macd = w_macd.iloc[w_idx]
            w_today_signal = w_signal.iloc[w_idx]

            weekly_crossed = (w_yes_hist < 0) and (w_today_hist > 0)
            weekly_bullish = (w_today_macd > w_today_signal) and (w_today_hist > 0)

            is_A = daily_crossed and weekly_bullish
            is_B = daily_crossed and weekly_crossed
            is_D = weekly_crossed and not daily_crossed

            if not (is_A or is_B or is_D):
                continue

            cat = 'B' if is_B else ('A' if is_A else 'D')
            entry = df['close'].iloc[i]
            exit_idx = min(i + holding, n - 1)
            exit_price = df['close'].iloc[exit_idx]
            ret = (exit_price - entry) / entry * 100

            trade_date = str(daily_date.date())
            exit_date = str(df.index[exit_idx].date())
            trades.append({
                'date': trade_date,
                'cat': cat,
                'entry': entry,
                'exit': exit_price,
                'ret': ret
            })

        if trades:
            df_trades = pd.DataFrame(trades)
            for cat in ['B', 'A', 'D']:
                sub = df_trades[df_trades['cat'] == cat]
                if len(sub) == 0:
                    continue
                wins = (sub['ret'] > 0).sum()
                avg = sub['ret'].mean()
                print(f'{t} 类{cat}: {len(sub)}次, 胜率{wins}/{len(sub)}={wins/len(sub)*100:.0f}%, 均收益{avg:+.2f}%')
                for _, row in sub.iterrows():
                    print(f"  {row['date']} -> {row['exit']} ({row['ret']:+.2f}%)")
        else:
            print(f'{t}: 无信号')

        print()