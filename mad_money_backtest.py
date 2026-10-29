"""
Mad Money 2026 Q1 回测
规则：
1. 首次买入推荐日期以1000美元等权重买入
2. 已有持仓时，跳过后续买入推荐（不追加）
3. 出现卖出推荐且股票已在持仓中：卖出
4. 止损：持仓从买入价下跌 ≥8% 时，次日开盘止损（独立每日扫描，不依赖推荐日期）
5. 卖出后，可以接受新的买入推荐
6. 回测截止：2026-04-08
"""

import pandas as pd
import numpy as np
from datetime import datetime
from data.fetcher import fetch
import warnings
warnings.filterwarnings('ignore')

RECOMMENDATIONS = [
    ("2026-01-02", ["NVDA", "GOOGL", "PINS", "THI"], ["DNUT", "BSC", "LEH", "AIG"]),
    ("2026-01-05", ["GS", "C", "COF", "LLY", "JNJ", "JPM", "SCHW", "AFRM", "AAPL"], ["NOK"]),
    ("2026-01-06", ["AMAT", "LRCX", "GS", "C", "COF", "EPD", "XOM", "CVX", "AMZN", "AAPL", "NVDA", "NKE", "SBUX", "AMD"], ["USAR", "FBHS"]),
    ("2026-01-07", ["AVGO", "CRWD", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AAPL", "LEN", "DHI", "PHM", "CELH", "TXRH", "MCD", "DG", "PLTR"], ["TSLA"]),
    ("2026-01-08", ["GS", "MS", "JPM", "WFC", "C", "COF", "FDX", "HD", "DG", "IBM", "NVR", "DAL", "GEV", "ULTA", "TSM"], ["BABA", "MELI", "SE", "COIN", "MSTR", "PLTR", "SMCI", "DELL"]),
    ("2026-01-09", ["JPM", "DAL", "TSM", "FDX", "NET", "ULTA", "GEV"], ["LAC", "DVAX", "SAIL", "RLGT", "FSLR"]),
    ("2026-01-12", ["SHOP", "NVO", "MDT", "PFE", "BLCO", "PLD", "SONY"], ["CUBE"]),
    ("2026-01-13", ["NVDA", "LLY", "JPM", "DG", "WMT", "TGT", "HD", "LOW", "RL", "GOOGL", "JNJ", "CAH", "AMGN"], ["W", "TSLA"]),
    ("2026-01-14", ["JNJ", "PG", "LLY", "BAC", "C", "IBM", "INTC", "NVDA"], ["MNTN", "SCCO", "NOW"]),
    ("2026-01-15", ["TSM", "NVDA", "AMD", "ASML", "KLAC", "AMAT", "LRCX", "META", "AAPL", "AVGO", "BLK", "GS", "MS", "GEV", "SBUX", "TXRH", "TOL", "LEN", "DHI", "PHM", "CAVA"], ["DDOG", "RGLD", "POET", "ADSK"]),
    ("2026-01-16", ["NFLX", "DHI", "MMM", "UAL", "DAL", "AXP", "BKNG", "MAR", "JNJ", "SCHW", "HOOD", "PG", "FCX", "ISRG", "FDX", "BA", "CVS", "MU", "TSM", "RDDT"], ["COST"]),
    ("2026-01-20", ["DHI", "LEN", "NVR", "PHM", "TOL", "PLD", "AMT", "EQIX", "BLK", "SCHW", "GS", "JPM", "BAC", "WFC", "C", "GD", "LMT", "RTX", "BA", "HON", "CAT", "FDX"], ["IDRX", "FFIE", "SHEL", "PRO"]),
    ("2026-01-21", ["AVGO", "MRK", "SNY", "REGN", "BMY", "PFE", "JNJ", "ABBV", "LLY", "NVO", "UPS", "FDX", "CEG", "VST"], ["GOLD", "JBLU"]),
    ("2026-01-22", ["PLTR", "AIP", "SMCI", "DELL", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "COIN", "MSTR", "MELI", "BABA", "AMZN", "WMT", "COST", "ROST", "AAPL", "GOOGL", "META"], ["LCID", "FTC", "VGC"]),
    ("2026-01-23", ["VEEV", "TMO", "DHR", "LLY", "ABBV", "PFE", "JNJ", "MKC", "HSY", "PG", "KO", "PEP", "XOM", "VMC", "EPD", "TGT", "PLD", "IYR"], ["SBUX", "AMD"]),
    ("2026-01-26", ["AVGO", "PSTG", "DELL", "ANET", "WDC", "STX", "MU", "NVDA", "AMD", "INTC", "AMAT", "LRCX", "KLAC", "ASML", "CDNS", "SNPS", "PYPL", "COIN"], ["AMT", "APP", "PSTG"]),
    ("2026-01-27", ["GM", "NUE", "NVDA", "INTC", "CRM", "ASML", "AMAT", "KLAC", "LRCX", "TSM", "AIR", "CMG", "FIX", "GLW"], ["UNH", "HUM", "CVS"]),
    ("2026-01-28", ["AEM", "META", "TSLA", "NOW", "SBUX", "GEV", "MU", "TXN", "LRCX", "TEVA"], ["LAC"]),
    ("2026-01-29", ["META", "MSFT", "NVDA", "CAT", "TSLA", "AAPL", "GOOGL", "LLY", "RCL", "IBM", "PLTR", "CARR"], ["ARR", "RBRK"]),
    ("2026-01-30", ["PLTR", "MRK", "CMG", "AMGN", "AAPL", "LLY", "GOOGL", "MCK", "AMZN", "AFRM", "RDDT", "ABBV", "LUV"], ["RITM", "UUUU", "TTD", "URI", "LVS", "ROP"]),
    ("2026-02-02", ["MRVL", "LEU", "SPHR"], ["AXON", "TDOC", "DDS"]),
    ("2026-02-03", ["SOLV"], ["LAND"]),
    ("2026-02-04", ["AEM", "NXT"], ["BCRX", "SYF", "EOSE"]),
    ("2026-02-05", ["AEM", "NXT", "UAL", "FDX", "COF"], ["NEM", "BCRX", "SKW", "SYF", "EOSE"]),
    ("2026-02-06", ["AFRM", "TATT", "BTC", "AEM"], ["KLAC", "PATH", "TOST", "SDIG", "BFLY", "ENB", "HMY", "DOW"]),
    ("2026-02-07", ["AFRM", "TATT", "AEM"], ["KLAC", "PATH", "TOST", "SOFI", "BFLY", "ENB", "HMY", "DOW"]),
    ("2026-02-23", ["VRT", "HII", "DELL", "EPAM", "TXN", "ADI", "CVX"], ["SMCI", "RMBS"]),
    ("2026-02-24", ["POWL"], ["KYND", "NVO", "IT"]),
    ("2026-02-25", ["SAN", "AFRM", "SOFI", "APLD"], ["FORT", "PYPL"]),
    ("2026-02-26", ["NVDA", "GE", "HGE", "MCD", "CMG", "WTS", "GXO", "RDDT", "F", "MSCI", "CRM"], ["ACHR", "OLED"]),
    ("2026-02-27", ["USAR", "IFF", "TPR"], ["AMAT", "RIG"]),
    ("2026-03-02", ["BROS", "NFLX", "LMT", "COF", "GS", "COCO", "REGN", "FTV", "MP"], ["MSFT"]),
    ("2026-03-03", ["ULTA", "CVS", "NVDA"], ["USAS", "ODD", "PGR", "NAT", "FSLR"]),
    ("2026-03-04", ["ACN", "AFRM", "PAYX"], ["RKT", "PEG"]),
    ("2026-03-05", ["IMAX"], ["AEIS", "GPC", "HTGC", "ENVX"]),
    ("2026-03-06", ["HON", "CMG", "AKRO", "PWR", "TTWO"], ["CVX", "AFRM", "GOLD", "SILVER", "COPPER", "BNAI", "ACM", "KHC", "KMI", "DUOL"]),
    ("2026-03-09", ["NVT", "ARM", "INTU"], ["HLI", "A", "APP"]),
    ("2026-03-10", ["AXP", "PRIM", "LYB", "DOW", "CRDO"], ["EOG"]),
    ("2026-03-11", ["ORCL", "GEV", "DVN", "MDB", "TEAM", "FSLR", "ENPH", "LEN", "DHI", "ETN"], ["MDB", "SIBN", "RXRX", "SOUN"]),
    ("2026-03-12", ["ET", "EPD", "KMI", "WMB", "OKE", "MPLX", "ETN", "CARR", "LMT", "RTX"], ["INTC", "BABA"]),
    ("2026-03-16", ["LLY", "NVO", "ABBV", "PFE", "MRK", "REGN", "BMY", "JNJ", "GEV", "CEG", "VST", "DHI", "LEN", "PHM"], ["INTC"]),
    ("2026-03-17", ["NVDA", "AVGO", "GEV", "CEG", "VST", "DHI", "LEN", "PHM", "LLY", "NVO", "ABBV"], ["IWM"]),
    ("2026-03-18", ["NVDA", "AVGO", "GEV", "CEG", "VST", "DHI", "LEN", "PHM", "LLY", "NVO", "ABBV"], ["INTC"]),
    ("2026-03-19", ["NVDA", "AVGO", "GEV", "CEG", "VST", "DHI", "LEN", "PHM", "LLY", "NVO", "ABBV"], ["TSLA", "INTC"]),
    ("2026-03-20", ["NVDA", "AVGO", "GEV", "CEG", "VST", "DHI", "LEN", "PHM", "LLY", "NVO", "ABBV"], ["OLMA", "CAG"]),
    ("2026-03-23", ["AMZN", "META", "MSFT", "NVDA", "GS", "JPM", "APO", "BX", "GEV", "CEG", "VST", "AMGN", "COST", "FDX", "XOM", "VMC", "EPD", "LLY", "TGT", "PLD", "IYR"], ["SBUX", "AMD"]),
    ("2026-03-24", ["AMZN", "AVGO", "GS", "JPM", "APO", "BX", "GEV", "CEG", "VST", "AMGN", "COST", "FDX"], ["PG", "KHC"]),
    ("2026-03-25", ["LLY", "NVO", "ABBV", "PFE", "MRK", "REGN", "BMY", "JNJ", "ISRG", "MDT", "SYK", "BSX", "EW", "ABT", "DXCM", "TMO", "DHR", "VRT", "ENPH", "ETN"], ["OLMA", "CAG"]),
    ("2026-03-26", ["RDDT", "DELL", "AMZN", "META", "XOM", "CVX", "HAL", "SLB", "OXY", "VST", "GEV", "CEG", "COF", "GE", "RTX"], ["MCD", "SBUX", "CVX"]),
    ("2026-03-27", ["XOM", "CVX", "OXY", "HAL", "SLB", "BKR", "GEV", "ETN", "GLW", "AVGO", "META", "COIN", "UBER", "DASH", "ABNB", "VIK"], ["MSFT", "NVDA", "BRK.B", "FCX", "AVAV", "MCD", "SBUX"]),
    ("2026-03-30", [], ["TSLA"]),
    ("2026-03-31", [], ["TSLA"]),
]

END_DATE = "2026-04-08"


def run_backtest():
    # ============================================================
    # 第一步：收集所有股票，建立每日交易日历
    # ============================================================
    all_symbols = set()
    for _, buys, sells in RECOMMENDATIONS:
        all_symbols.update(buys)
        all_symbols.update(sells)
    all_symbols = sorted(all_symbols)

    print(f"需要获取数据的股票数量: {len(all_symbols)}")

    price_data = {}
    history_days = 150
    print(f"正在获取 {len(all_symbols)} 只股票的历史数据 (history_days={history_days})...")

    try:
        result = fetch(all_symbols, history_days=history_days, live_mode=False)
        for symbol, df in result.items():
            if df is not None and len(df) > 0:
                price_data[symbol] = df
        print(f"成功获取 {len(price_data)} 只股票的数据")
    except Exception as e:
        print(f"获取数据失败: {e}")
        return

    # 建立全局交易日历（所有推荐日期 + 数据范围）
    all_trading_dates = set()
    start_dt = pd.to_datetime("2026-01-01").tz_localize("UTC")
    end_dt = pd.to_datetime(END_DATE).tz_localize("UTC")
    for df in price_data.values():
        for idx in df.index:
            if start_dt <= idx <= end_dt:
                all_trading_dates.add(idx)
    all_trading_dates = sorted(all_trading_dates)
    print(f"交易日历共 {len(all_trading_dates)} 个交易日")

    # ============================================================
    # 第二步：建立推荐事件映射
    # ============================================================
    rec_buys = {}   # date_str -> set of symbols
    rec_sells = {}  # date_str -> set of symbols
    for date_str, buys, sells in RECOMMENDATIONS:
        rec_buys[date_str] = set(buys)
        rec_sells[date_str] = set(sells)

    # ============================================================
    # 第三步：独立每日扫描
    # positions: symbol -> {entry_date, entry_price, shares, sold, sell_date, sell_price, sell_reason}
    # pending_entries: {(date_str, symbol): entry_price}  # 等待次日开盘入场的 BUY 信号
    # pending_exits:   {(date_str, symbol): exit_price}  # 等待次日开盘入场的 SELL 信号
    # ============================================================
    positions = {}       # 当前持仓
    trades = []          # 所有交易记录
    pending_entries = {}   # {(date, symbol): price}  BUY 已确认，等次日开盘执行
    pending_exits = {}      # {(date, symbol): (price, reason)}  SELL 已确认，等次日开盘执行

    for i, today in enumerate(all_trading_dates):
        today_str = today.strftime('%Y-%m-%d')

        # ---- A. 执行上一天确定的 pending 订单（开盘价）----
        # 先执行出场（止损/SELL），再执行入场（BUY）
        today_str_from_ts = today.strftime('%Y-%m-%d') if hasattr(today, 'strftime') else str(today)[:10]
        to_remove_pending_exit = []
        for (date_str, symbol), (price, reason) in pending_exits.items():
            if date_str == today_str_from_ts:
                if symbol in positions and not positions[symbol]['sold']:
                    positions[symbol]['sold'] = True
                    positions[symbol]['sell_date'] = today_str_from_ts
                    positions[symbol]['sell_price'] = price
                    positions[symbol]['sell_reason'] = reason
                    trades.append({
                        "symbol": symbol,
                        "action": reason,  # "STOP_LOSS" or "SELL"
                        "date": today_str_from_ts,
                        "price": price,
                        "shares": positions[symbol]['shares']
                    })
                to_remove_pending_exit.append((date_str, symbol))
        for k in to_remove_pending_exit:
            del pending_exits[k]

        to_remove_pending_entry = []
        for (date_str, symbol), price in pending_entries.items():
            if date_str == today_str_from_ts:
                if symbol not in positions or positions[symbol]['sold']:
                    shares = 1000 / price
                    positions[symbol] = {
                        "entry_date": today_str_from_ts,
                        "entry_price": price,
                        "shares": shares,
                        "sold": False,
                        "sell_date": None,
                        "sell_price": None,
                        "sell_reason": None
                    }
                    trades.append({
                        "symbol": symbol,
                        "action": "BUY",
                        "date": today_str_from_ts,
                        "price": price,
                        "shares": shares
                    })
                to_remove_pending_entry.append((date_str, symbol))
        for k in to_remove_pending_entry:
            del pending_entries[k]

        # ---- B. 止损检查：每个持仓股，独立扫描今天之前的每日收盘价 ----
        for symbol in list(positions.keys()):
            pos = positions[symbol]
            if pos['sold']:
                continue
            df = price_data.get(symbol)
            if df is None:
                continue

            entry_dt = pd.to_datetime(pos['entry_date']).tz_localize("UTC")
            entry_price = pos['entry_price']

            # 找今天的下一个交易日（用股票自己的 dataframe）
            next_td = None
            for idx in df.index:
                if idx > today:
                    next_td = idx
                    break

            # 扫描从 entry 到 today 的所有收盘价
            for idx in df.index:
                if idx < entry_dt:
                    continue
                if idx > today:
                    break
                close_price = df.loc[idx, 'close']
                if pd.isna(close_price):
                    continue
                drawdown = (close_price - entry_price) / entry_price
                if drawdown <= -0.08:
                    # 止损触发：用下一个交易日开盘价执行
                    if next_td is not None:
                        exec_price = df.loc[next_td, 'open']
                        exec_date_str = next_td.strftime('%Y-%m-%d') if hasattr(next_td, 'strftime') else str(next_td)[:10]
                        pending_exits[(exec_date_str, symbol)] = (exec_price, "STOP_LOSS")
                    break

        # ---- C. 处理今天的推荐信号 ----
        buys_today = rec_buys.get(today_str, set())
        sells_today = rec_sells.get(today_str, set())

        # SELL 信号
        for symbol in sells_today:
            if symbol not in positions or positions[symbol]['sold']:
                continue
            pos = positions[symbol]
            if pos['sold']:
                continue
            df = price_data.get(symbol)
            if df is None:
                continue
            # 找下一个交易日开盘执行
            next_td = None
            for idx in df.index:
                if idx > today:
                    next_td = idx
                    break
            if next_td is not None:
                exec_price = df.loc[next_td, 'open']
                exec_date_str = next_td.strftime('%Y-%m-%d') if hasattr(next_td, 'strftime') else str(next_td)[:10]
                pending_exits[(exec_date_str, symbol)] = (exec_price, "SELL")

        # BUY 信号
        for symbol in buys_today:
            if symbol in positions and not positions[symbol]['sold']:
                continue  # 已有持仓，跳过
            df = price_data.get(symbol)
            if df is None:
                continue
            # 找下一个交易日开盘执行
            next_td = None
            for idx in df.index:
                if idx > today:
                    next_td = idx
                    break
            if next_td is not None:
                exec_price = df.loc[next_td, 'open']
                exec_date_str = next_td.strftime('%Y-%m-%d') if hasattr(next_td, 'strftime') else str(next_td)[:10]
                pending_entries[(exec_date_str, symbol)] = exec_price

    # ============================================================
    # 第四步：计算收益率
    # ============================================================
    results = []
    for symbol, pos in positions.items():
        entry_value = pos["entry_price"] * pos["shares"]

        if pos['sold'] and pos['sell_price'] and pos['sell_price'] > 0:
            exit_value = pos["sell_price"] * pos["shares"]
            ret = (exit_value - entry_value) / entry_value * 100
            final_value = exit_value
            entry_dt = pd.to_datetime(pos["entry_date"]).tz_localize("UTC")
            sell_dt = pd.to_datetime(pos["sell_date"]).tz_localize("UTC")
            holding_days = (sell_dt - entry_dt).days
            traded = True
            last_date_str = pos["sell_date"]
            last_price = pos["sell_price"]
            reason = pos.get("sell_reason", "SELL")
        else:
            df = price_data.get(symbol)
            if df is not None:
                last_price = df.iloc[-1]['close']
                last_date = df.index[-1]
                if not pd.isna(last_price):
                    exit_value = last_price * pos["shares"]
                    ret = (exit_value - entry_value) / entry_value * 100
                    final_value = exit_value
                    entry_dt = pd.to_datetime(pos["entry_date"]).tz_localize("UTC")
                    holding_days = (last_date - entry_dt).days
                else:
                    exit_value = entry_value
                    ret = 0
                    final_value = entry_value
                    last_price = 0
                    last_date_str = END_DATE
                    holding_days = 0
            else:
                exit_value = entry_value
                ret = 0
                final_value = entry_value
                last_price = 0
                last_date_str = END_DATE
                holding_days = 0
            traded = False
            last_date_str = last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date)[:10]
            reason = ""

        results.append({
            "symbol": symbol,
            "entry_date": pos["entry_date"],
            "entry_price": pos["entry_price"],
            "sell_date": last_date_str,
            "sell_price": last_price,
            "shares": pos["shares"],
            "return_pct": ret,
            "final_value": final_value,
            "holding_days": holding_days,
            "traded": traded,
            "sell_reason": reason if pos['sold'] else ("持仓中" if not traded else "")
        })

    # ============================================================
    # 输出
    # ============================================================
    df_results = pd.DataFrame(results)

    print("\n" + "="*100)
    print("Mad Money 2026 Q1 回测结果（8% 止损，独立每日扫描）")
    print("="*100)

    if len(df_results) == 0:
        print("无交易记录")
        return

    print("\n【交易记录】")
    buy_trades = [t for t in trades if t['action'] == 'BUY']
    sell_trades = [t for t in trades if t['action'] == 'SELL']
    sl_trades = [t for t in trades if t['action'] == 'STOP_LOSS']
    print(f"总交易次数: {len(trades)} (买入:{len(buy_trades)} 卖出:{len(sell_trades)} 止损:{len(sl_trades)})")

    df_results = df_results.sort_values('return_pct', ascending=False)
    print("\n【个股表现】")
    print("-"*100)
    print(f"{'股票':<10} {'买入日期':<12} {'买入价':<10} {'卖出日期':<12} {'卖出价':<10} {'收益率':>10} {'持有天':>6} {'状态':<6}")
    print("-"*100)
    for _, row in df_results.iterrows():
        status = row.get('sell_reason', 'SELL') if row['traded'] else "持仓中"
        status = status if status else ("已卖" if row['traded'] else "持仓中")
        print(f"{row['symbol']:<10} {row['entry_date']:<12} ${row['entry_price']:<9.2f} {str(row['sell_date']):<12} ${row['sell_price']:<9.2f} {row['return_pct']:>9.2f}% {row['holding_days']:>6}天 {status:<8}")

    wins = df_results[df_results['return_pct'] > 0]
    losses = df_results[df_results['return_pct'] <= 0]

    print("\n" + "="*100)
    print("【统计汇总】")
    print("="*100)
    print(f"交易股票数: {len(df_results)}")
    print(f"盈利股票: {len(wins)} ({len(wins)/len(df_results)*100:.1f}%)")
    print(f"亏损股票: {len(losses)} ({len(losses)/len(df_results)*100:.1f}%)")
    print(f"胜率: {len(wins)/len(df_results)*100:.1f}%")
    print(f"平均收益率: {df_results['return_pct'].mean():.2f}%")

    initial_capital = 1000 * len(df_results)
    total_final_value = df_results['final_value'].sum()
    correct_total_return = (total_final_value - initial_capital) / initial_capital * 100

    print(f"\n【组合表现】")
    print(f"初始资金: ${initial_capital:,.2f}")
    print(f"最终价值: ${total_final_value:,.2f}")
    print(f"总收益率: {correct_total_return:.2f}%")
    print(f"最大单笔亏损: {df_results['return_pct'].min():.2f}%")
    print(f"\n【持有天数】")
    print(f"平均: {df_results['holding_days'].mean():.1f} 天，最短: {df_results['holding_days'].min()} 天，最长: {df_results['holding_days'].max()} 天")
    print("="*100)


if __name__ == "__main__":
    run_backtest()
