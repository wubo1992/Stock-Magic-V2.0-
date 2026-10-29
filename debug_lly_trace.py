#!/usr/bin/env python3
"""Trace LLY through the actual backtest code step by step"""
import pandas as pd
import sys
sys.path.insert(0, '/Users/wubo/Desktop/codes/信号系统克劳德V3.1_Minimax支线')
from signal_system.data.fetcher import fetch
import warnings
warnings.filterwarnings('ignore')

RECOMMENDATIONS = [
    ('2026-01-02', ['NVDA','GOOGL','PINS','THI'], ['DNUT','BSC','LEH','AIG']),
    ('2026-01-05', ['GS','C','COF','LLY','JNJ','JPM','SCHW','AFRM','AAPL'], ['NOK']),
    ('2026-01-06', ['AMAT','LRCX','GS','C','COF','EPD','XOM','CVX','AMZN','AAPL','NVDA','NKE','SBUX','AMD'], ['USAR','FBHS']),
    ('2026-01-07', ['AVGO','CRWD','NVDA','MSFT','AMZN','GOOGL','META','AAPL','LEN','DHI','PHM','CELH','TXRH','MCD','DG','PLTR'], ['TSLA']),
    ('2026-01-08', ['GS','MS','JPM','WFC','C','COF','FDX','HD','DG','IBM','NVR','DAL','GEV','ULTA','TSM'], ['BABA','MELI','SE','COIN','MSTR','PLTR','SMCI','DELL']),
    ('2026-01-09', ['JPM','DAL','TSM','FDX','NET','ULTA','GEV'], ['LAC','DVAX','SAIL','RLGT','FSLR']),
    ('2026-01-12', ['SHOP','NVO','MDT','PFE','BLCO','PLD','SONY'], ['CUBE']),
    ('2026-01-13', ['NVDA','LLY','JPM','DG','WMT','TGT','HD','LOW','RL','GOOGL','JNJ','CAH','AMGN'], ['W','TSLA']),
    ('2026-01-14', ['JNJ','PG','LLY','BAC','C','IBM','INTC','NVDA'], ['MNTN','SCCO','NOW']),
    ('2026-01-15', ['TSM','NVDA','AMD','ASML','KLAC','AMAT','LRCX','META','AAPL','AVGO','BLK','GS','MS','GEV','SBUX','TXRH','TOL','LEN','DHI','PHM','CAVA'], ['DDOG','RGLD','POET','ADSK']),
    ('2026-01-16', ['NFLX','DHI','MMM','UAL','DAL','AXP','BKNG','MAR','JNJ','SCHW','HOOD','PG','FCX','ISRG','FDX','BA','CVS','MU','TSM','RDDT'], ['COST']),
    ('2026-01-20', ['DHI','LEN','NVR','PHM','TOL','PLD','AMT','EQIX','BLK','SCHW','GS','JPM','BAC','WFC','C','GD','LMT','RTX','BA','HON','CAT','FDX'], ['IDRX','FFIE','SHEL','PRO']),
    ('2026-01-21', ['AVGO','MRK','SNY','REGN','BMY','PFE','JNJ','ABBV','LLY','NVO','UPS','FDX','CEG','VST'], ['GOLD','JBLU']),
    ('2026-01-22', ['PLTR','AIP','SMCI','DELL','AMD','INTC','QCOM','AVGO','MRVL','COIN','MSTR','MELI','BABA','AMZN','WMT','COST','ROST','AAPL','GOOGL','META'], ['LCID','FTC','VGC']),
    ('2026-01-23', ['VEEV','TMO','DHR','LLY','ABBV','PFE','JNJ','MKC','HSY','PG','KO','PEP','XOM','VMC','EPD','TGT','PLD','IYR'], ['SBUX','AMD']),
    ('2026-01-26', ['AVGO','PSTG','DELL','ANET','WDC','STX','MU','NVDA','AMD','INTC','AMAT','LRCX','KLAC','ASML','CDNS','SNPS','PYPL','COIN'], ['AMT','APP','PSTG']),
    ('2026-01-27', ['GM','NUE','NVDA','INTC','CRM','ASML','AMAT','KLAC','LRCX','TSM','AIR','CMG','FIX','GLW'], ['UNH','HUM','CVS']),
    ('2026-01-28', ['AEM','META','TSLA','NOW','SBUX','GEV','MU','TXN','LRCX','TEVA'], ['LAC']),
    ('2026-01-29', ['META','MSFT','NVDA','CAT','TSLA','AAPL','GOOGL','LLY','RCL','IBM','PLTR','CARR'], ['ARR','RBRK']),
    ('2026-01-30', ['PLTR','MRK','CMG','AMGN','AAPL','LLY','GOOGL','MCK','AMZN','AFRM','RDDT','ABBV','LUV'], ['RITM','UUUU','TTD','URI','LVS','ROP']),
    ('2026-02-02', ['MRVL','LEU','SPHR'], ['AXON','TDOC','DDS']),
    ('2026-02-03', ['SOLV'], ['LAND']),
    ('2026-02-04', ['AEM','NXT'], ['BCRX','SYF','EOSE']),
    ('2026-02-05', ['AEM','NXT','UAL','FDX','COF'], ['NEM','BCRX','SKW','SYF','EOSE']),
    ('2026-02-06', ['AFRM','TATT','BTC','AEM'], ['KLAC','PATH','TOST','SDIG','BFLY','ENB','HMY','DOW']),
    ('2026-02-07', ['AFRM','TATT','AEM'], ['KLAC','PATH','TOST','SOFI','BFLY','ENB','HMY','DOW']),
    ('2026-02-23', ['VRT','HII','DELL','EPAM','TXN','ADI','CVX'], ['SMCI','RMBS']),
    ('2026-02-24', ['POWL'], ['KYND','NVO','IT']),
    ('2026-02-25', ['SAN','AFRM','SOFI','APLD'], ['FORT','PYPL']),
    ('2026-02-26', ['NVDA','GE','HGE','MCD','CMG','WTS','GXO','RDDT','F','MSCI','CRM'], ['ACHR','OLED']),
    ('2026-02-27', ['USAR','IFF','TPR'], ['AMAT','RIG']),
    ('2026-03-02', ['BROS','NFLX','LMT','COF','GS','COCO','REGN','FTV','MP'], ['MSFT']),
    ('2026-03-03', ['ULTA','CVS','NVDA'], ['USAS','ODD','PGR','NAT','FSLR']),
    ('2026-03-04', ['ACN','AFRM','PAYX'], ['RKT','PEG']),
    ('2026-03-05', ['IMAX'], ['AEIS','GPC','HTGC','ENVX']),
    ('2026-03-06', ['HON','CMG','AKRO','PWR','TTWO'], ['CVX','AFRM','GOLD','SILVER','COPPER','BNAI','ACM','KHC','KMI','DUOL']),
    ('2026-03-09', ['NVT','ARM','INTU'], ['HLI','A','APP']),
    ('2026-03-10', ['AXP','PRIM','LYB','DOW','CRDO'], ['EOG']),
    ('2026-03-11', ['ORCL','GEV','DVN','MDB','TEAM','FSLR','ENPH','LEN','DHI','ETN'], ['MDB','SIBN','RXRX','SOUN']),
    ('2026-03-12', ['ET','EPD','KMI','WMB','OKE','MPLX','ETN','CARR','LMT','RTX'], ['INTC','BABA']),
    ('2026-03-16', ['LLY','NVO','ABBV','PFE','MRK','REGN','BMY','JNJ','GEV','CEG','VST','DHI','LEN','PHM'], ['INTC']),
    ('2026-03-17', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['IWM']),
    ('2026-03-18', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['INTC']),
    ('2026-03-19', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['TSLA','INTC']),
    ('2026-03-20', ['NVDA','AVGO','GEV','CEG','VST','DHI','LEN','PHM','LLY','NVO','ABBV'], ['OLMA','CAG']),
    ('2026-03-23', ['AMZN','META','MSFT','NVDA','GS','JPM','APO','BX','GEV','CEG','VST','AMGN','COST','FDX','XOM','VMC','EPD','LLY','TGT','PLD','IYR'], ['SBUX','AMD']),
    ('2026-03-24', ['AMZN','AVGO','GS','JPM','APO','BX','GEV','CEG','VST','AMGN','COST','FDX'], ['PG','KHC']),
    ('2026-03-25', ['LLY','NVO','ABBV','PFE','MRK','REGN','BMY','JNJ','ISRG','MDT','SYK','BSX','EW','ABT','DXCM','TMO','DHR','VRT','ENPH','ETN'], ['OLMA','CAG']),
    ('2026-03-26', ['RDDT','DELL','AMZN','META','XOM','CVX','HAL','SLB','OXY','VST','GEV','CEG','COF','GE','RTX'], ['MCD','SBUX','CVX']),
    ('2026-03-27', ['XOM','CVX','OXY','HAL','SLB','BKR','GEV','ETN','GLW','AVGO','META','COIN','UBER','DASH','ABNB','VIK'], ['MSFT','NVDA','BRK.B','FCX','AVAV','MCD','SBUX']),
    ('2026-03-30', [], ['TSLA']),
    ('2026-03-31', [], ['TSLA']),
]

END_DATE = '2026-04-08'
all_symbols = ['LLY']
result = fetch(all_symbols, history_days=150, live_mode=False)
price_data = {s: df for s, df in result.items() if df is not None and len(df) > 0}
df = price_data['LLY']

all_trading_dates = sorted(set(
    idx for idx in df.index
    if pd.to_datetime('2026-01-01').tz_localize('UTC') <= idx <= pd.to_datetime(END_DATE).tz_localize('UTC')
))

rec_buys = {}
rec_sells = {}
for date_str, buys, sells in RECOMMENDATIONS:
    rec_buys[date_str] = set(buys)
    rec_sells[date_str] = set(sells)

positions = {}
pending_entries = {}
pending_exits = {}
banned = set()

def sellshares(symbol, qty, price, reason, date_str):
    pos = positions[symbol]
    sold_shares = min(qty, pos['shares'])
    if sold_shares <= 0:
        return
    pos['shares'] -= sold_shares
    pos['total_proceeds'] += sold_shares * price
    if pos['shares'] <= 0.5:
        pos['shares'] = 0
        pos['sold'] = True
        pos['sell_date'] = date_str
        pos['sell_price'] = price
        pos['sell_reason'] = reason
        banned.add(symbol)
    print(f"    [{date_str}] SELL {reason}: {sold_shares:.4f}@{price:.2f} -> proceeds=${pos['total_proceeds']:.2f}, remaining={pos['shares']:.4f}, banned={symbol in banned}")

for today in all_trading_dates:
    today_str = today.strftime('%Y-%m-%d')
    buys_today = rec_buys.get(today_str, set())
    sells_today = rec_sells.get(today_str, set())

    # Pending exits
    to_remove = []
    for (date_str, symbol), (exec_price, reason) in list(pending_exits.items()):
        if date_str == today_str and symbol in positions and not positions[symbol]['sold']:
            print(f"[{today_str}] PENDING SELL {symbol} {reason} @ {exec_price:.2f}")
            sellshares(symbol, positions[symbol]['shares'], exec_price, 'SELL', today_str)
            to_remove.append((date_str, symbol))
    for k in to_remove:
        del pending_exits[k]

    # Pending entries
    to_remove = []
    for (date_str, symbol), entry_price in list(pending_entries.items()):
        if date_str == today_str:
            if symbol in banned:
                print(f"[{today_str}] PENDING BUY {symbol} SKIPPED (banned)")
            elif symbol in positions and not positions[symbol]['sold']:
                print(f"[{today_str}] PENDING BUY {symbol} SKIPPED (already held)")
            else:
                shares = 1000 / entry_price
                positions[symbol] = {
                    'entry_date': today_str, 'entry_price': entry_price,
                    'shares': shares, 'orig_shares': shares,
                    'total_proceeds': 0.0, 'sold': False,
                    'sell_date': None, 'sell_price': None, 'sell_reason': None,
                }
                print(f"[{today_str}] BUY {symbol}: price={entry_price:.2f}, shares={shares:.4f}")
            to_remove.append((date_str, symbol))
    for k in to_remove:
        del pending_entries[k]

    # Stop-loss / take-profit
    for symbol in list(positions.keys()):
        pos = positions[symbol]
        if pos['sold'] or pos['entry_date'] == today_str:
            continue
        if today not in df.index:
            continue
        entry_price = pos['entry_price']
        cur_shares = pos['shares']
        if cur_shares <= 0:
            continue
        high = df.loc[today, 'high']
        low = df.loc[today, 'low']
        if pd.isna(high) or pd.isna(low):
            continue
        stop_5 = entry_price * 0.95
        stop_10 = entry_price * 0.90
        tp_10 = entry_price * 1.10
        tp_20 = entry_price * 1.20

        if low <= stop_10:
            print(f"[{today_str}] STOP10: {symbol} low={low:.2f}<={stop_10:.2f}, shares={cur_shares:.4f}")
            sellshares(symbol, cur_shares, stop_10, 'STOP_LOSS_100', today_str)
        elif low <= stop_5:
            sell_qty = int(cur_shares * 0.5)
            if sell_qty >= 1:
                print(f"[{today_str}] STOP5: {symbol} low={low:.2f}<={stop_5:.2f}, sell_qty={sell_qty}, shares={cur_shares:.4f}")
                sellshares(symbol, sell_qty, stop_5, 'STOP_LOSS_50', today_str)
            else:
                print(f"[{today_str}] STOP5: {symbol} low={low:.2f}<={stop_5:.2f}, but sell_qty={sell_qty}<1, SKIP")

        cur_shares = positions[symbol]['shares'] if symbol in positions and not positions[symbol]['sold'] else 0
        if cur_shares > 0 and high >= tp_20:
            print(f"[{today_str}] TP20: {symbol} high={high:.2f}>={tp_20:.2f}")
            sellshares(symbol, cur_shares, tp_20, 'TAKE_PROFIT_100', today_str)
        elif cur_shares > 0 and high >= tp_10:
            sell_qty = int(cur_shares * 0.5)
            if sell_qty >= 1:
                print(f"[{today_str}] TP10: {symbol} high={high:.2f}>={tp_10:.2f}, sell_qty={sell_qty}")
                sellshares(symbol, sell_qty, tp_10, 'TAKE_PROFIT_50', today_str)

    # Queue BUY signals
    for symbol in buys_today:
        if symbol in banned:
            continue
        if symbol in positions and not positions[symbol]['sold']:
            continue
        next_td = None
        for idx in df.index:
            if idx > today:
                next_td = idx
                break
        if next_td is not None:
            entry_price = df.loc[next_td, 'open']
            pending_entries[(next_td.strftime('%Y-%m-%d'), symbol)] = entry_price
            print(f"[{today_str}] QUEUE BUY {symbol} for {next_td.strftime('%Y-%m-%d')} @ {entry_price:.2f}")

    # Queue SELL signals
    for symbol in sells_today:
        if symbol not in positions or positions[symbol]['sold']:
            continue
        next_td = None
        for idx in df.index:
            if idx > today:
                next_td = idx
                break
        if next_td is not None:
            exec_price = df.loc[next_td, 'open']
            pending_exits[(next_td.strftime('%Y-%m-%d'), symbol)] = (exec_price, 'SELL')

print(f"\nFinal LLY: {positions.get('LLY')}")
