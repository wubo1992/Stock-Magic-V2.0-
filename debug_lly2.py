#!/usr/bin/env python3
"""Debug LLY step by step"""
import pandas as pd
import sys
sys.path.insert(0, '/Users/wubo/Desktop/codes/信号系统克劳德V3.1_Minimax支线')
from signal_system.data.fetcher import fetch
import warnings
warnings.filterwarnings('ignore')

RECOMMENDATIONS = [
    ('2026-01-06', ['AMAT','LRCX','GS','C','COF','EPD','XOM','CVX','AMZN','AAPL','NVDA','NKE','SBUX','AMD'], ['USAR','FBHS']),
    ('2026-01-13', ['NVDA','LLY','JPM','DG','WMT','TGT','HD','LOW','RL','GOOGL','JNJ','CAH','AMGN'], ['W','TSLA']),
    ('2026-01-14', ['JNJ','PG','LLY','BAC','C','IBM','INTC','NVDA'], ['MNTN','SCCO','NOW']),
    ('2026-01-23', ['VEEV','TMO','DHR','LLY','ABBV','PFE','JNJ','MKC','HSY','PG','KO','PEP','XOM','VMC','EPD','TGT','PLD','IYR'], ['SBUX','AMD']),
    ('2026-01-30', ['PLTR','MRK','CMG','AMGN','AAPL','LLY','GOOGL','MCK','AMZN','AFRM','RDDT','ABBV','LUV'], ['RITM','UUUU','TTD','URI','LVS','ROP']),
    ('2026-03-16', ['LLY','NVO','ABBV','PFE','MRK','REGN','BMY','JNJ','GEV','CEG','VST','DHI','LEN','PHM'], ['INTC']),
    ('2026-03-17', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['IWM']),
    ('2026-03-18', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['INTC']),
    ('2026-03-19', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['TSLA','INTC']),
    ('2026-03-20', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['OLMA','CAG']),
    ('2026-03-23', ['AMZN','META','MSFT','NVDA','GS','JPM','APO','BX','GEV','CEG','VST','AMGN','COST','FDX','XOM','VMC','EPD','LLY','TGT','PLD','IYR'], ['SBUX','AMD']),
    ('2026-03-25', ['LLY','NVO','ABBV','PFE','MRK','REGN','BMY','JNJ','ISRG','MDT','SYK','BSX','EW','ABT','DXCM','TMO','DHR','VRT','ENPH','ETN'], ['OLMA','CAG']),
]

END_DATE = '2026-04-08'
all_symbols = ['LLY']
result = fetch(all_symbols, history_days=150, live_mode=False)
df = result.get('LLY')
print(f"LLY rows: {len(df)}")
print(f"LLY index[0]: {df.index[0].date()}")
print(f"LLY index[-1]: {df.index[-1].date()}")

# Filter
df = df[(df.index >= pd.to_datetime('2026-01-01').tz_localize('UTC')) &
         (df.index <= pd.to_datetime(END_DATE).tz_localize('UTC'))]
print(f"After filter: {len(df)} rows")
print(f"First 5 rows:")
for i in range(min(5, len(df))):
    row = df.iloc[i]
    print(f"  {df.index[i].date()}  O:{row['open']:.2f}  H:{row['high']:.2f}  L:{row['low']:.2f}  C:{row['close']:.2f}")

# Find actual entry price for LLY on 2026-01-06
entry_ts = None
for idx in df.index:
    if idx >= pd.to_datetime('2026-01-05').tz_localize('UTC'):
        entry_ts = idx
        break
print(f"\nLLY entry: {entry_ts.date()} open={df.loc[entry_ts,'open']:.2f}")
entry_price = df.loc[entry_ts, 'open']
shares = 1000 / entry_price
print(f"Shares: {shares:.4f}")
print(f"Stop-5: {entry_price*0.95:.2f}, Stop-10: {entry_price*0.90:.2f}")
print(f"TP+10: {entry_price*1.10:.2f}, TP+20: {entry_price*1.20:.2f}")

# Simulate step by step
pos = {'shares': shares, 'total_proceeds': 0.0}
print(f"\nStart: shares={pos['shares']:.4f}, proceeds={pos['total_proceeds']:.2f}")

for i, (idx, row) in enumerate(df.iterrows()):
    if idx == entry_ts:
        print(f"  [{idx.date()}] === ENTRY === shares={pos['shares']:.4f}")
        continue

    high = row['high']
    low = row['low']
    close = row['close']
    date_str = idx.strftime('%Y-%m-%d')
    stop_5 = entry_price * 0.95
    stop_10 = entry_price * 0.90
    tp_10 = entry_price * 1.10
    tp_20 = entry_price * 1.20

    # Stop-loss first
    if low <= stop_10 and pos['shares'] > 0:
        sold = min(pos['shares'], pos['shares'])
        proceeds = sold * stop_10
        print(f"  [{date_str}] STOP10: sell ALL {pos['shares']:.4f}@${stop_10:.2f} => proceeds+${proceeds:.2f}")
        pos['shares'] -= sold
        pos['total_proceeds'] += proceeds
        print(f"         shares={pos['shares']:.4f}, total_proceeds=${pos['total_proceeds']:.2f}")
        break
    elif low <= stop_5 and pos['shares'] > 0:
        sell_qty = pos['shares'] * 0.5
        sell_qty = max(1, int(sell_qty))  # at least 1 share
        sell_qty = min(sell_qty, pos['shares'])
        proceeds = sell_qty * stop_5
        print(f"  [{date_str}] STOP5: sell {sell_qty}@{stop_5:.2f} => proceeds+${proceeds:.2f}, shares={pos['shares']:.4f}->{pos['shares']-sell_qty:.4f}")
        pos['shares'] -= sell_qty
        pos['total_proceeds'] += proceeds
        print(f"         shares={pos['shares']:.4f}, total_proceeds=${pos['total_proceeds']:.2f}")
    elif pos['shares'] > 0 and high >= tp_20:
        print(f"  [{date_str}] TP20: sell ALL {pos['shares']:.4f}@{tp_20:.2f}")
        pos['total_proceeds'] += pos['shares'] * tp_20
        pos['shares'] = 0
        break
    elif pos['shares'] > 0 and high >= tp_10:
        sell_qty = pos['shares'] * 0.5
        sell_qty = max(1, int(sell_qty))
        sell_qty = min(sell_qty, pos['shares'])
        print(f"  [{date_str}] TP10: sell {sell_qty}@{tp_10:.2f} => shares={pos['shares']:.4f}->{pos['shares']-sell_qty:.4f}")
        pos['shares'] -= sell_qty
        pos['total_proceeds'] += sell_qty * tp_10

print(f"\nFinal: shares={pos['shares']:.4f}, total_proceeds=${pos['total_proceeds']:.2f}")
print(f"Return: {(pos['total_proceeds'] - 1000) / 1000 * 100:+.2f}%")
