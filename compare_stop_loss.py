#!/usr/bin/env python3
"""Compare all stop-loss thresholds with CORRECT methodology"""
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

all_symbols = set()
for _, buys, sells in RECOMMENDATIONS:
    all_symbols.update(buys)
    all_symbols.update(sells)
all_symbols = sorted(all_symbols)

print("Fetching data...")
result = fetch(all_symbols, history_days=150, live_mode=False)
price_data = {s: df for s, df in result.items() if df is not None and len(df) > 0}

all_trading_dates = set()
start_dt = pd.to_datetime('2026-01-01').tz_localize('UTC')
end_dt = pd.to_datetime(END_DATE).tz_localize('UTC')
for df in price_data.values():
    for idx in df.index:
        if start_dt <= idx <= end_dt:
            all_trading_dates.add(idx)
all_trading_dates = sorted(all_trading_dates)

rec_buys = {}
rec_sells = {}
for date_str, buys, sells in RECOMMENDATIONS:
    rec_buys[date_str] = set(buys)
    rec_sells[date_str] = set(sells)

first_rec_date = {}
rec_count = {}
for date_str, buys, sells in RECOMMENDATIONS:
    for s in buys:
        rec_count[s] = rec_count.get(s, 0) + 1
        if s not in first_rec_date or date_str < first_rec_date[s]:
            first_rec_date[s] = date_str


def run_backtest(stop_pct):
    positions = {}
    trades = []
    pending_entries = {}
    pending_exits = {}

    for today in all_trading_dates:
        today_str = today.strftime('%Y-%m-%d')

        to_remove = []
        for (date_str, symbol), (price, reason) in list(pending_exits.items()):
            if date_str == today_str:
                if symbol in positions and not positions[symbol]['sold']:
                    positions[symbol]['sold'] = True
                    positions[symbol]['sell_date'] = today_str
                    positions[symbol]['sell_price'] = price
                    positions[symbol]['sell_reason'] = reason
                    trades.append({'symbol': symbol, 'action': reason, 'date': today_str, 'price': price})
                to_remove.append((date_str, symbol))
        for k in to_remove:
            del pending_exits[k]

        to_remove = []
        for (date_str, symbol), entry_price in list(pending_entries.items()):
            if date_str == today_str:
                if symbol not in positions or positions[symbol]['sold']:
                    shares = 1000 / entry_price
                    positions[symbol] = {'entry_date': today_str, 'entry_price': entry_price, 'shares': shares, 'sold': False, 'sell_date': None, 'sell_price': None, 'sell_reason': None}
                    trades.append({'symbol': symbol, 'action': 'BUY', 'date': today_str, 'price': entry_price})
                to_remove.append((date_str, symbol))
        for k in to_remove:
            del pending_entries[k]

        for symbol in list(positions.keys()):
            pos = positions[symbol]
            if pos['sold'] or pos['entry_date'] == today_str:
                continue
            df = price_data.get(symbol)
            if df is None or today not in df.index:
                continue
            stop_price = pos['entry_price'] * (1 - stop_pct)
            low_price = df.loc[today, 'low']
            if pd.isna(low_price):
                continue
            if low_price <= stop_price:
                positions[symbol]['sold'] = True
                positions[symbol]['sell_date'] = today_str
                positions[symbol]['sell_price'] = stop_price
                positions[symbol]['sell_reason'] = 'STOP_LOSS'
                trades.append({'symbol': symbol, 'action': 'STOP_LOSS', 'date': today_str, 'price': stop_price})

        buys_today = rec_buys.get(today_str, set())
        sells_today = rec_sells.get(today_str, set())
        for symbol in sells_today:
            if symbol not in positions or positions[symbol]['sold']:
                continue
            if positions[symbol]['sold']:
                continue
            df = price_data.get(symbol)
            if df is None:
                continue
            next_td = None
            for idx in df.index:
                if idx > today:
                    next_td = idx
                    break
            if next_td is not None:
                exec_price = df.loc[next_td, 'open']
                exec_date_str = next_td.strftime('%Y-%m-%d')
                pending_exits[(exec_date_str, symbol)] = (exec_price, 'SELL')
        for symbol in buys_today:
            if symbol in positions and not positions[symbol]['sold']:
                continue
            df = price_data.get(symbol)
            if df is None:
                continue
            next_td = None
            for idx in df.index:
                if idx > today:
                    next_td = idx
                    break
            if next_td is not None:
                entry_price = df.loc[next_td, 'open']
                exec_date_str = next_td.strftime('%Y-%m-%d')
                pending_entries[(exec_date_str, symbol)] = entry_price

    results = []
    for symbol, pos in positions.items():
        entry_value = pos['entry_price'] * pos['shares']
        if pos['sold'] and pos['sell_price'] and pos['sell_price'] > 0:
            exit_value = pos['sell_price'] * pos['shares']
            ret = (exit_value - entry_value) / entry_value * 100
            reason = pos.get('sell_reason', '?')
        else:
            df = price_data.get(symbol)
            if df is not None:
                last_price = df.iloc[-1]['close']
                if not pd.isna(last_price):
                    exit_value = last_price * pos['shares']
                    ret = (exit_value - entry_value) / entry_value * 100
                else:
                    ret = 0
            else:
                ret = 0
            reason = '持仓中'
        first_rec = first_rec_date.get(symbol, pos['entry_date'])
        results.append({'symbol': symbol, 'entry_date': pos['entry_date'], 'entry_price': pos['entry_price'], 'sell_date': pos['sell_date'], 'return_pct': ret, 'reason': reason, 'rec_count': rec_count.get(symbol, 1)})

    df_results = pd.DataFrame(results)

    # Portfolio return: sum of P&L / sum of initial capital
    total_initial_capital = len(results) * 1000  # each position starts with $1000
    total_pnl = df_results['return_pct'].sum() * 10  # each % is $10 (on $1000)
    portfolio_return = total_pnl / total_initial_capital * 100

    # Also compute simple sum (for comparison)
    sum_return = df_results['return_pct'].sum()
    max_loss = df_results['return_pct'].min()
    stop_triggers = len(df_results[df_results['reason'] == 'STOP_LOSS'])
    win_rate = len(df_results[df_results['return_pct'] > 0]) / len(df_results) * 100
    trade_count = len(df_results)
    sell_count = len(df_results[df_results['reason'] == 'SELL'])
    held_count = len(df_results[df_results['reason'] == '持仓中'])
    stop_count = stop_triggers
    best = df_results.loc[df_results['return_pct'].idxmax()] if len(df_results) > 0 else None
    worst = df_results.loc[df_results['return_pct'].idxmin()] if len(df_results) > 0 else None

    return {
        'portfolio_return': portfolio_return,
        'sum_return': sum_return,
        'max_loss': max_loss,
        'stop_triggers': stop_triggers,
        'win_rate': win_rate,
        'trade_count': trade_count,
        'sell_count': sell_count,
        'held_count': held_count,
        'stop_count': stop_count,
        'total_initial_capital': total_initial_capital,
        'total_pnl': total_pnl,
        'best': best,
        'worst': worst,
    }


print("\nRunning backtests for all stop-loss thresholds...")
for stop_pct in [0.05, 0.08, 0.10]:
    print(f"\n{'='*60}")
    print(f"Testing {int(stop_pct*100)}% stop-loss...")
    r = run_backtest(stop_pct)
    print(f"  持仓总笔数:     {r['trade_count']}")
    print(f"  持仓中(still held): {r['held_count']}")
    print(f"  STOP_LOSS触发: {r['stop_count']}")
    print(f"  SELL信号卖出:   {r['sell_count']}")
    print(f"  胜率:           {r['win_rate']:.1f}%")
    print(f"  最大亏损:       {r['max_loss']:+.2f}%")
    print(f"  ---")
    print(f"  【组合收益率】  {r['portfolio_return']:+.2f}%  (总本金${r['total_initial_capital']:,} → 盈利${r['total_pnl']:+,.0f})")
    print(f"  【累计回报率】  {r['sum_return']:+.2f}%  (各持仓独立回报之和)")
    if r['best'] is not None:
        print(f"  最佳持仓: {r['best']['symbol']} {r['best']['return_pct']:+.2f}%")
    if r['worst'] is not None:
        print(f"  最差持仓: {r['worst']['symbol']} {r['worst']['return_pct']:+.2f}%")
