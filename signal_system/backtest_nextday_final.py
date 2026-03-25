"""
次日开盘买卖策略回测 - 最终版
"""

import json
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import numpy as np

with open('config.yaml') as f:
    config = yaml.safe_load(f)

strategies_config = config.get('strategies', {})

from strategies.v1_wizard.sepa_minervini import SEPAStrategy
from strategies.v1_plus.sepa_plus import SEPAPlusStrategy
from strategies.v_oneil.sepa_oneil import ONeilStrategy
from strategies.v_ryan.sepa_ryan import RyanStrategy
from strategies.v_kell.sepa_kell import KellStrategy
from strategies.v_kullamaggi.sepa_kullamaggi import KullamaggiStrategy
from strategies.v_zanger.zanger_strategy import ZangerStrategy
from strategies.v_stine.sepa_stine import StineStrategy
from strategies.v_weinstein.weinstein_strategy import WeinsteinStrategy


def load_market_data():
    cache_dir = Path('data/cache')
    market_data = {}

    for pkl_file in cache_dir.glob('*.pkl'):
        symbol = pkl_file.stem
        try:
            df = pd.read_pickle(pkl_file)
            if len(df) >= 500:
                df = df[df.index >= pd.Timestamp('2024-01-01', tz='UTC')]
                if len(df) >= 50:
                    # 添加一个normalized的date列用于比较
                    df = df.copy()
                    df['trade_date'] = df.index.normalize()
                    market_data[symbol] = df.sort_index()
        except Exception:
            pass

    print(f"加载: {len(market_data)} 只股票")
    return market_data


def get_trading_dates(market_data):
    all_dates = set()
    for df in market_data.values():
        all_dates.update(df['trade_date'].unique())
    sorted_dates = sorted(all_dates)
    print(f"交易日: {sorted_dates[0].date()} ~ {sorted_dates[-1].date()}")
    return sorted_dates


def check_signals_for_date(args):
    date, symbol, df, strategy_classes, ts = args
    signals = []
    for strat_id, strat_class in strategy_classes:
        if strat_id not in strategies_config:
            continue
        try:
            cfg = strategies_config[strat_id]
            clean_cfg = {k: v for k, v in cfg.items() if not isinstance(v, dict)}
            strategy = strat_class(clean_cfg, {symbol: df}, live_mode=False)
            strategy.positions = {}
            signal = strategy._check_entry(symbol, df, ts)
            if signal and signal.data.get("direction") == 'buy':
                signals.append({
                    'strategy': strat_id,
                    'strength': signal.data.get('strength', 3)
                })
        except Exception:
            pass
    return date, symbol, signals


def precompute_buy_signals_parallel(market_data, trading_dates, strategy_classes):
    buy_signals_by_date = defaultdict(list)

    tasks = []
    for date in trading_dates:
        # 确保date是Timestamp对象
        date_ts = pd.Timestamp(date)
        for symbol, df in market_data.items():
            df_slice = df[df['trade_date'] <= date_ts]
            if len(df_slice) >= 200:
                # 构造一个用于策略的timestamp
                ts = date_ts + pd.Timedelta(hours=23, minutes=59)
                tasks.append((date_ts.date(), symbol, df_slice, strategy_classes, ts))

    print(f"任务: {len(tasks)}")

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(check_signals_for_date, tasks))

    for date, symbol, signals in results:
        if signals:
            buy_signals_by_date[date].append({
                'symbol': symbol,
                'signals': signals,
                'strength': max(s['strength'] for s in signals)
            })

    print(f"产生信号的交易日: {len(buy_signals_by_date)}")
    return buy_signals_by_date


def simulate_trades(market_data, trading_dates, buy_signals_by_date):
    BUY_AMOUNT = 1000
    trades = []
    pending = {}

    # 日期转索引
    date_idx = {d: i for i, d in enumerate(trading_dates)}

    for i, date in enumerate(trading_dates):
        if i % 100 == 0:
            print(f"模拟: {i}/{len(trading_dates)}, 持仓: {len(pending)}")

        # 卖出: 持有一天后次日卖出
        to_close = []
        for sym, p in list(pending.items()):
            buy_idx = date_idx[p['buy_date']]
            if i > buy_idx + 1:  # 至少持有一天
                df = market_data.get(sym)
                if df is not None:
                    sell_row = df[df['trade_date'] == date]
                    if not sell_row.empty:
                        sell_price = float(sell_row['close'].iloc[0])  # 次日收盘价
                        buy_price = p['buy_price']
                        shares = p['shares']
                        pnl = (sell_price - buy_price) * shares
                        pnl_pct = (sell_price / buy_price - 1) * 100

                        trades.append({
                            'symbol': sym,
                            'buy_date': p['buy_date'].date(),
                            'sell_date': date.date(),
                            'buy_price': round(buy_price, 2),
                            'sell_price': round(sell_price, 2),
                            'shares': round(shares, 4),
                            'pnl': round(pnl, 2),
                            'pnl_pct': round(pnl_pct, 2),
                        })
                        to_close.append(sym)

        for sym in to_close:
            del pending[sym]

        # 买入: 执行前一天的信号
        if i + 1 < len(trading_dates):
            next_date = trading_dates[i + 1]
            prev_date = trading_dates[i]

            for sig in buy_signals_by_date.get(prev_date, []):
                sym = sig['symbol']
                if sym in pending:
                    continue

                df = market_data.get(sym)
                if df is not None:
                    buy_row = df[df['trade_date'] == next_date]
                    if not buy_row.empty:
                        buy_price = float(buy_row['open'].iloc[0])
                        if buy_price > 0:
                            shares = BUY_AMOUNT / buy_price
                            pending[sym] = {
                                'buy_date': next_date,
                                'buy_price': buy_price,
                                'shares': shares,
                            }

    return trades


def analyze_results(trades):
    if not trades:
        print("无交易")
        return None

    df = pd.DataFrame(trades)

    print("\n" + "="*60)
    print("次日开盘买卖策略回测结果")
    print("="*60)
    print(f"参数: 每次买入 $1000, 持有一天后次日收盘卖出")
    print(f"数据: 2024-01 ~ 2026-03")

    print(f"\n总交易: {len(df)}")
    wins = len(df[df['pnl'] > 0])
    losses = len(df[df['pnl'] <= 0])
    print(f"盈利: {wins}, 亏损: {losses}, 胜率: {wins/len(df)*100:.1f}%")

    print(f"\n总收益: ${df['pnl'].sum():,.2f}")
    print(f"平均收益: ${df['pnl'].mean():.2f}")
    print(f"平均收益率: {df['pnl_pct'].mean():.2f}%")
    print(f"收益标准差: {df['pnl_pct'].std():.2f}%")

    print(f"\n最大盈利: ${df['pnl'].max():.2f} ({df['pnl_pct'].max():.2f}%)")
    print(f"最大亏损: ${df['pnl'].min():.2f} ({df['pnl_pct'].min():.2f}%)")

    print(f"\n按股票 (Top 15):")
    stock = df.groupby('symbol')['pnl'].agg(['count', 'sum', 'mean']).sort_values('sum', ascending=False)
    stock.columns = ['次数', '总收益', '平均']
    print(stock.head(15).to_string())

    print(f"\n按月:")
    df['month'] = pd.to_datetime(df['sell_date']).dt.to_period('M')
    monthly = df.groupby('month').agg({'pnl': ['count', 'sum', 'mean'], 'pnl_pct': 'mean'})
    monthly.columns = ['次数', '总收益', '平均', '收益率%']
    print(monthly.tail(20).to_string())

    return df


def main():
    print("加载数据...")
    market_data = load_market_data()

    print("\n交易日...")
    trading_dates = get_trading_dates(market_data)

    print("\n策略...")
    strategy_classes = [
        ('v1', SEPAStrategy), ('v1_plus', SEPAPlusStrategy), ('v_oneil', ONeilStrategy),
        ('v_ryan', RyanStrategy), ('v_kell', KellStrategy), ('v_kullamaggi', KullamaggiStrategy),
        ('v_zanger', ZangerStrategy), ('v_stine', StineStrategy), ('v_weinstein', WeinsteinStrategy),
    ]

    print("\n计算信号...")
    signals = precompute_buy_signals_parallel(market_data, trading_dates, strategy_classes)

    print("\n模拟交易...")
    trades = simulate_trades(market_data, trading_dates, signals)

    print("\n分析...")
    df = analyze_results(trades)

    if df is not None:
        Path('output/v_nextday').mkdir(parents=True, exist_ok=True)
        df.to_csv('output/v_nextday/trades.csv', index=False)
        print("\n已保存")


if __name__ == '__main__':
    main()
