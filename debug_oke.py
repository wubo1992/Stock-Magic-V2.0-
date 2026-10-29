#!/usr/bin/env python3
"""Debug OKE specifically"""
import pandas as pd
import sys
sys.path.insert(0, '/Users/wubo/Desktop/codes/信号系统克劳德V3.1_Minimax支线')
from signal_system.data.fetcher import fetch
import warnings
warnings.filterwarnings('ignore')

result = fetch(['OKE'], history_days=150, live_mode=False)
df = result.get('OKE')
print(f"OKE data shape: {df.shape if df is not None else 'None'}")
print(f"OKE index type: {type(df.index) if df is not None else 'N/A'}")
print(f"OKE date range: {df.index[0]} to {df.index[-1]}" if df is not None else "")

# Check the actual entry date
entry_date = pd.to_datetime('2026-03-13').tz_localize('UTC')
print(f"\nEntry date: {entry_date}")
print(f"In index? {entry_date in df.index}")

# Get entry price (open of next trading day after 2026-03-13)
entry_ts = None
for idx in df.index:
    if idx > pd.to_datetime('2026-03-13').tz_localize('UTC'):
        entry_ts = idx
        break

print(f"Entry timestamp: {entry_ts}")
if entry_ts is not None:
    entry_price = df.loc[entry_ts, 'open']
    print(f"Entry open price: {entry_price}")

    # Last price
    last_price = df.iloc[-1]['close']
    last_date = df.index[-1]
    print(f"Last close ({last_date.date()}): {last_price}")

    # P&L
    shares = 1000 / entry_price
    orig_val = 1000
    curr_val = last_price * shares
    ret = (curr_val - orig_val) / orig_val * 100
    print(f"Return: {ret:+.2f}%")

# What is df.iloc[-1] actually showing?
print(f"\ndf.iloc[-1] date: {df.index[-1].date()}")
print(f"df.iloc[-1] open: {df.iloc[-1]['open']:.2f}")
print(f"df.iloc[-1] close: {df.iloc[-1]['close']:.2f}")

# Show some rows around 2026-03-13
print("\nRows around 2026-03-13:")
for idx in df.index:
    if idx >= pd.to_datetime('2026-03-12').tz_localize('UTC') and idx <= pd.to_datetime('2026-03-15').tz_localize('UTC'):
        print(f"  {idx.date()}  O:{df.loc[idx,'open']:.2f}  H:{df.loc[idx,'high']:.2f}  L:{df.loc[idx,'low']:.2f}  C:{df.loc[idx,'close']:.2f}")
