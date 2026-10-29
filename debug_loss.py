#!/usr/bin/env python3
"""Debug: check why OKE, BTC, etc. show massive losses"""
import pandas as pd
import sys
sys.path.insert(0, '/Users/wubo/Desktop/codes/信号系统克劳德V3.1_Minimax支线')
from signal_system.data.fetcher import fetch
import warnings
warnings.filterwarnings('ignore')

symbols = ['OKE', 'BTC', 'SLB', 'WMT', 'PLD', 'CAH', 'VIK', 'RTX', 'EW', 'OXY']
result = fetch(symbols, history_days=150, live_mode=False)
price_data = {s: df for s, df in result.items() if df is not None and len(df) > 0}

# Show entry price vs last price for each
end_dt = pd.to_datetime('2026-04-08').tz_localize('UTC')

for sym in symbols:
    df = price_data.get(sym)
    if df is None:
        print(f"{sym}: NO DATA")
        continue
    # Filter to relevant dates
    df = df[(df.index >= pd.to_datetime('2026-01-01').tz_localize('UTC')) &
            (df.index <= end_dt)]
    first_row = df.iloc[0]
    last_row = df.iloc[-1]
    pct = (last_row['close'] - first_row['close']) / first_row['close'] * 100
    print(f"{sym}:")
    print(f"  首个数据日: {df.index[0].date()}  开:{first_row['open']:.2f}  收:{first_row['close']:.2f}")
    print(f"  末数据日:   {df.index[-1].date()}  开:{last_row['open']:.2f}  收:{last_row['close']:.2f}")
    print(f"  期间涨跌:   {pct:+.2f}%")
    print(f"  数据天数:   {len(df)}")
    # Show entry price scenario for OKE bought on 2026-03-13
    if sym == 'OKE':
        entry_date = pd.to_datetime('2026-03-13').tz_localize('UTC')
        if entry_date in df.index:
            e = df.loc[entry_date]
            print(f"  OKE entry date 2026-03-13: open={e['open']:.2f}, close={e['close']:.2f}, high={e['high']:.2f}, low={e['low']:.2f}")
        else:
            print(f"  OKE entry date 2026-03-13: NOT IN INDEX")
            # Find nearest
            idxs = df.index[df.index >= entry_date]
            if len(idxs) > 0:
                print(f"  Next available: {idxs[0].date()}")
    # Also show high/low for BTC entry date
    if sym == 'BTC':
        entry_date = pd.to_datetime('2026-02-09').tz_localize('UTC')
        if entry_date in df.index:
            e = df.loc[entry_date]
            print(f"  BTC entry date 2026-02-09: open={e['open']:.2f}, close={e['close']:.2f}")
        else:
            print(f"  BTC entry date 2026-02-09: NOT IN INDEX")
        print(f"  BTC all data count: {len(df)}")
        if len(df) > 0:
            print(f"  BTC date range: {df.index[0].date()} to {df.index[-1].date()}")
