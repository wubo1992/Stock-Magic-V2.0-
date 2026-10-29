#!/usr/bin/env python3
"""
分级止盈止损回测
规则：
  - 首次 BUY 推荐：$1000 等权重建仓
  - 盈利 ≥10%：卖一半（剩余继续持有）
  - 盈利 ≥20%：卖另一半（清仓，banned）
  - 亏损 ≥5%：卖一半（剩余继续持有）
  - 亏损 ≥10%：卖另一半（清仓，banned）
  - SELL 推荐：立即清仓（banned）
  - banned 股票永不重新买入
  - stop-loss 和 take-profit 用当日 high/low 触发，以触发价位当日成交
"""
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

positions = {}
pending_entries = {}
pending_exits = {}
banned = set()
trades_log = []

def sellshares(symbol, qty, price, reason, date_str):
    pos = positions[symbol]
    sell_qty = min(qty, pos['shares'])
    if sell_qty <= 0:
        return
    pos['shares'] -= sell_qty
    pos['total_proceeds'] += sell_qty * price
    trades_log.append({
        'symbol': symbol, 'action': reason, 'date': date_str,
        'price': price, 'shares': sell_qty, 'remaining': pos['shares'],
    })
    # Only close position if all remaining shares were sold (full exit)
    if pos['shares'] <= 1e-9:
        pos['shares'] = 0
        pos['sold'] = True
        pos['sell_date'] = date_str
        pos['sell_price'] = price
        pos['sell_reason'] = reason
        banned.add(symbol)

for today in all_trading_dates:
    today_str = today.strftime('%Y-%m-%d')

    # 1. 处理 pending SELL 信号（次日开盘执行）
    to_remove = []
    for (date_str, symbol), (exec_price, reason) in list(pending_exits.items()):
        if date_str == today_str:
            if symbol in positions and not positions[symbol]['sold']:
                pos = positions[symbol]
                sellshares(symbol, pos['shares'], exec_price, 'SELL', today_str)
                positions[symbol]['sell_date'] = today_str
                positions[symbol]['sell_reason'] = 'SELL'
                positions[symbol]['sell_price'] = exec_price
            to_remove.append((date_str, symbol))
    for k in to_remove:
        del pending_exits[k]

    # 2. 处理 pending BUY 信号（次日开盘执行）
    to_remove = []
    for (date_str, symbol), entry_price in list(pending_entries.items()):
        if date_str == today_str:
            if symbol in banned:
                to_remove.append((date_str, symbol))
                continue
            if symbol in positions and not positions[symbol]['sold']:
                to_remove.append((date_str, symbol))
                continue
            shares = 1000 / entry_price
            positions[symbol] = {
                'entry_date': today_str, 'entry_price': entry_price,
                'shares': shares, 'orig_shares': shares,
                'total_proceeds': 0.0, 'sold': False,
                'sell_date': None, 'sell_price': None, 'sell_reason': None,
                'stop_5_triggered': False,
                'tp_10_triggered': False,
            }
            trades_log.append({
                'symbol': symbol, 'action': 'BUY', 'date': today_str,
                'price': entry_price, 'shares': shares, 'remaining': shares,
            })
            to_remove.append((date_str, symbol))
    for k in to_remove:
        del pending_entries[k]

    # 3. 分级止损/止盈（当日价格触发，当日成交）
    for symbol in list(positions.keys()):
        pos = positions[symbol]
        if pos['sold'] or pos['entry_date'] == today_str:
            continue
        df = price_data.get(symbol)
        if df is None or today not in df.index:
            continue
        entry_price = pos['entry_price']
        cur_shares = pos['shares']
        if cur_shares <= 0:
            continue
        high_price = df.loc[today, 'high']
        low_price = df.loc[today, 'low']
        if pd.isna(high_price) or pd.isna(low_price):
            continue
        stop_5  = entry_price * 0.95
        stop_10 = entry_price * 0.90
        tp_10   = entry_price * 1.10
        tp_20   = entry_price * 1.20

        if low_price <= stop_10:
            sellshares(symbol, cur_shares, stop_10, 'STOP_LOSS_100', today_str)
        elif low_price <= stop_5 and not pos.get('stop_5_triggered'):
            sellshares(symbol, cur_shares * 0.5, stop_5, 'STOP_LOSS_50', today_str)
            positions[symbol]['stop_5_triggered'] = True

        cur_shares = positions[symbol]['shares'] if symbol in positions and not positions[symbol]['sold'] else 0
        if cur_shares > 0 and high_price >= tp_20:
            sellshares(symbol, cur_shares, tp_20, 'TAKE_PROFIT_100', today_str)
        elif cur_shares > 0 and high_price >= tp_10 and not pos.get('tp_10_triggered'):
            sellshares(symbol, cur_shares * 0.5, tp_10, 'TAKE_PROFIT_50', today_str)
            positions[symbol]['tp_10_triggered'] = True

    # 4. 收集当日 BUY / SELL 推荐，排队次日开盘执行
    buys_today = rec_buys.get(today_str, set())
    sells_today = rec_sells.get(today_str, set())
    for symbol in sells_today:
        if symbol not in positions or positions[symbol]['sold']:
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
        if symbol in banned:
            continue
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

# ---- 结果汇总 ----
results = []
for symbol, pos in positions.items():
    if pos['sold']:
        total_value = pos['total_proceeds']
        ret = (total_value - 1000) / 1000 * 100
        reason = pos.get('sell_reason', '?')
    else:
        df = price_data.get(symbol)
        if df is not None:
            last_price = df.iloc[-1]['close']
            if not pd.isna(last_price):
                total_value = pos['total_proceeds'] + last_price * pos['shares']
                ret = (total_value - 1000) / 1000 * 100
            else:
                ret = 0
        else:
            ret = 0
        reason = '持仓中'
    results.append({
        'symbol': symbol,
        'entry_date': pos['entry_date'],
        'entry_price': pos['entry_price'],
        'sell_date': pos['sell_date'],
        'return_pct': ret,
        'reason': reason,
        'rec_count': rec_count.get(symbol, 1),
        'total_proceeds': pos.get('total_proceeds', 0),
        'remaining_shares': pos['shares'],
    })

df_results = pd.DataFrame(results)

# ---- 打印汇总 ----
print("\n" + "="*70)
print("分级止盈止损回测结果")
print("="*70)
print(f"总持仓股票数:     {len(df_results)}")
print(f"banned 股票数:   {len(banned)}")
print(f"仍持仓中:        {len(df_results[df_results['reason']=='持仓中'])}")
print(f"已清仓:          {len(df_results[df_results['reason']!='持仓中'])}")

stop_50  = len(df_results[df_results['reason']=='STOP_LOSS_50'])
df_trades = pd.DataFrame(trades_log)
sell_events = df_trades[df_trades['action'] != 'BUY']
stop_50  = len(sell_events[sell_events['action']=='STOP_LOSS_50'])
stop_100 = len(sell_events[sell_events['action']=='STOP_LOSS_100'])
tp_50    = len(sell_events[sell_events['action']=='TAKE_PROFIT_50'])
tp_100   = len(sell_events[sell_events['action']=='TAKE_PROFIT_100'])
sell_sig = len(sell_events[sell_events['action']=='SELL'])
print(f"\n卖出事件分布（按实际触发次数）:")
print(f"  止损50%(亏5%):   {stop_50} 次（5%触发后降仓，剩余继续持有）")
print(f"  止损100%(亏10%): {stop_100} 次（10%触发或5%后10%触发，清仓）")
print(f"  止盈50%(盈10%):  {tp_50} 次（10%触发后降仓，剩余继续持有）")
print(f"  止盈100%(盈20%): {tp_100} 次（20%触发或10%后20%触发，清仓）")
print(f"  SELL信号:         {sell_sig} 次")

total_initial = len(df_results) * 1000
total_pnl = df_results['return_pct'].sum() * 10
portfolio_return = total_pnl / total_initial * 100
win_rate = len(df_results[df_results['return_pct'] > 0]) / len(df_results) * 100
max_loss = df_results['return_pct'].min()
max_gain = df_results['return_pct'].max()
print(f"\n【组合收益率】   {portfolio_return:+.2f}%  (总本金${total_initial:,} → 盈亏${total_pnl:+,.0f})")
print(f"胜率:             {win_rate:.1f}%")
print(f"最大单笔亏损:      {max_loss:+.2f}%")
print(f"最大单笔盈利:      {max_gain:+.2f}%")

# Top/Bottom 10
df_sorted = df_results.sort_values('return_pct', ascending=False)
print(f"\n最佳10笔:")
for _, r in df_sorted.head(10).iterrows():
    proceeds = r['total_proceeds']
    remaining_val = r['remaining_shares'] * (price_data.get(r['symbol']).iloc[-1]['close'] if r['reason']=='持仓中' and r['symbol'] in price_data else 0)
    print(f"  {r['symbol']:6s}  {r['entry_date']}  {str(r['sell_date']):10s}  {r['reason']:15s}  {r['return_pct']:+.2f}%  兑现${proceeds:.0f}  剩股{r['remaining_shares']:.2f}")
print(f"\n最差10笔:")
for _, r in df_sorted.tail(10).iterrows():
    proceeds = r['total_proceeds']
    remaining_val = r['remaining_shares'] * (price_data.get(r['symbol']).iloc[-1]['close'] if r['reason']=='持仓中' and r['symbol'] in price_data else 0)
    print(f"  {r['symbol']:6s}  {r['entry_date']}  {str(r['sell_date']):10s}  {r['reason']:15s}  {r['return_pct']:+.2f}%  兑现${proceeds:.0f}  剩股{r['remaining_shares']:.2f}")
