#!/usr/bin/env python3
"""Trace LLY execution in detail"""
import pandas as pd
import sys
sys.path.insert(0, '/Users/wubo/Desktop/codes/信号系统克劳德V3.1_Minimax支线')
from signal_system.data.fetcher import fetch
import warnings
warnings.filterwarnings('ignore')

result = fetch(['LLY'], history_days=150, live_mode=False)
df = result.get('LLY')
print(f"LLY date range: {df.index[0].date()} to {df.index[-1].date()}")
print(f"LLY data rows: {len(df)}")

# Filter to relevant period
start = pd.to_datetime('2026-01-01').tz_localize('UTC')
end = pd.to_datetime('2026-04-10').tz_localize('UTC')
df = df[(df.index >= start) & (df.index <= end)]

# Find entry
entry_date = None
for idx in df.index:
    if idx >= pd.to_datetime('2026-01-06').tz_localize('UTC'):
        entry_date = idx
        break
entry_price = df.loc[entry_date, 'open']
stop_5 = entry_price * 0.95
stop_10 = entry_price * 0.90
tp_10 = entry_price * 1.10
tp_20 = entry_price * 1.20
print(f"\nLLY Entry: {entry_date.date()} open={entry_price:.2f}")
print(f"Stop-5%: {stop_5:.2f}, Stop-10%: {stop_10:.2f}")
print(f"TP+10%: {tp_10:.2f}, TP+20%: {tp_20:.2f}")

# Simulate what happened
shares = 1000 / entry_price
print(f"Shares: {shares:.4f}")
print(f"\nDaily high/low analysis:")
for idx in df.index:
    high = df.loc[idx, 'high']
    low = df.loc[idx, 'low']
    close = df.loc[idx, 'close']
    date_str = idx.strftime('%Y-%m-%d')
    triggers = []
    if low <= stop_10:
        triggers.append(f'STOP10 @ {stop_10:.2f}')
    elif low <= stop_5:
        triggers.append(f'STOP5 @ {stop_5:.2f}')
    if high >= tp_20:
        triggers.append(f'TP20 @ {tp_20:.2f}')
    elif high >= tp_10:
        triggers.append(f'TP10 @ {tp_10:.2f}')
    if triggers:
        print(f"  {date_str}  H:{high:.2f}  L:{low:.2f}  C:{close:.2f}  >>> {', '.join(triggers)}")
