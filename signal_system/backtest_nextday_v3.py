"""
次日开盘买卖策略回测 - 精简版本

只回测2024-2026的数据，使用更小的股票池
"""

import json
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import numpy as np

# 加载配置
with open('config.yaml') as f:
    config = yaml.safe_load(f)

strategies_config = config.get('strategies', {})

# 导入所有策略
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
    """加载本地缓存的数据（限制股票数量）"""
    cache_dir = Path('data/cache')
    market_data = {}

    # 只加载有足够历史的股票
    for pkl_file in cache_dir.glob('*.pkl'):
        symbol = pkl_file.stem
        try:
            df = pd.read_pickle(pkl_file)
            # 过滤：至少需要500天数据
            if len(df) >= 500:
                # 只保留2024年以后的数据，减少计算量
                df = df[df.index >= pd.Timestamp('2024-01-01', tz='UTC')]
                if len(df) >= 50:  # 2024年后至少50天
                    market_data[symbol] = df.sort_index()
        except Exception as e:
            pass

    print(f"加载了 {len(market_data)} 只股票的数据 (2024至今)")
    return market_data


def get_trading_dates(market_data):
    """获取所有可用的交易日"""
    all_dates = set()
    for symbol, df in market_data.items():
        for idx in df.index:
            all_dates.add(idx.normalize())

    sorted_dates = sorted(all_dates)
    print(f"交易日范围: {sorted_dates[0].date()} ~ {sorted_dates[-1].date()}")
    return sorted_dates


def check_signals_for_date(args):
    """检查某一天的信号（用于并行）"""
    date, symbol, df, strategy_classes = args

    signals = []
    for strat_id, strat_class in strategy_classes:
        if strat_id not in strategies_config:
            continue
        try:
            cfg = strategies_config[strat_id]
            clean_cfg = {k: v for k, v in cfg.items() if not isinstance(v, dict)}
            strategy = strat_class(clean_cfg, {symbol: df}, live_mode=False)
            strategy.positions = {}

            signal = strategy._check_entry(symbol, df, date)
            if signal and signal.data.get("direction") == 'buy':
                signals.append({
                    'strategy': strat_id,
                    'strength': signal.data.get('strength', 3)
                })
        except Exception:
            pass
    return date, symbol, signals


def precompute_buy_signals_parallel(market_data, trading_dates, strategy_classes):
    """并行预计算所有买入信号"""
    buy_signals_by_date = defaultdict(list)

    # 准备任务
    tasks = []
    for date in trading_dates:
        if date.tzinfo is None:
            date = date.tz_localize('UTC')

        for symbol, df in market_data.items():
            df_slice = df[df.index <= date]
            if len(df_slice) >= 200:
                tasks.append((date, symbol, df_slice, strategy_classes))

    print(f"共 {len(tasks)} 个任务，并行计算信号...")

    # 并行执行
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(check_signals_for_date, tasks))

    # 整理结果
    for date, symbol, signals in results:
        if signals:
            buy_signals_by_date[date].append({
                'symbol': symbol,
                'signals': signals,
                'strength': max(s['strength'] for s in signals)
            })

    total_signals = len(buy_signals_by_date)
    print(f"共 {total_signals} 个交易日产生信号")

    return buy_signals_by_date


def simulate_trades(market_data, trading_dates, buy_signals_by_date):
    """模拟交易"""
    BUY_AMOUNT = 1000
    trades = []
    pending_entries = {}

    date_to_idx = {d: i for i, d in enumerate(trading_dates)}

    for i, date in enumerate(trading_dates):
        if date.tzinfo is None:
            date = date.tz_localize('UTC')

        # 1. 检查卖出 - 持有一天后卖出
        to_close = []
        for symbol, pending in list(pending_entries.items()):
            buy_date = pending['buy_date']
            # 找到买入日期之后的下一个交易日
            buy_idx = date_to_idx.get(buy_date, 0)
            if i > buy_idx + 1:  # 至少持有一天
                df = market_data.get(symbol)
                if df is not None:
                    # 获取下一个交易日的价格
                    if i < len(trading_dates):
                        sell_date = trading_dates[i]
                        df_slice = df[df.index <= sell_date]
                        if not df_slice.empty:
                            # 找下一个交易日的开盘价（不是当天的）
                            # 因为数据时间戳是前一天的04:00，我们需要找下一个不同的日期
                            sell_price = float(df_slice['close'].iloc[-1])  # 用收盘价更准确
                            buy_price = pending['buy_price']
                            shares = pending['shares']
                            pnl = (sell_price - buy_price) * shares
                            pnl_pct = (sell_price / buy_price - 1) * 100

                            trades.append({
                                'symbol': symbol,
                                'buy_date': buy_date.date(),
                                'sell_date': sell_date.date(),
                                'buy_price': round(buy_price, 2),
                                'sell_price': round(sell_price, 2),
                                'shares': round(shares, 4),
                                'pnl': round(pnl, 2),
                                'pnl_pct': round(pnl_pct, 2),
                            })
                            to_close.append(symbol)

        for symbol in to_close:
            del pending_entries[symbol]

        # 2. 执行前一天信号 - 次日开盘买入
        if i + 1 < len(trading_dates):
            next_date = trading_dates[i + 1]
            prev_date = trading_dates[i]

            for sig_info in buy_signals_by_date.get(prev_date, []):
                symbol = sig_info['symbol']
                if symbol in pending_entries:
                    continue

                df = market_data.get(symbol)
                if df is not None:
                    # 次日开盘买入 - 使用次日开盘价
                    df_slice = df[df.index <= next_date]
                    if not df_slice.empty:
                        buy_price = float(df_slice['open'].iloc[-1])
                        if buy_price > 0:
                            shares = BUY_AMOUNT / buy_price
                            pending_entries[symbol] = {
                                'buy_date': next_date,
                                'buy_price': buy_price,
                                'shares': shares,
                            }

        if i % 100 == 0:
            print(f"模拟: {i}/{len(trading_dates)}, 持仓: {len(pending_entries)}, 交易: {len(trades)}")

    return trades


def analyze_results(trades):
    """分析结果"""
    if not trades:
        print("没有交易")
        return None

    df = pd.DataFrame(trades)

    print("\n" + "="*60)
    print("次日开盘买卖策略回测结果")
    print("="*60)
    print(f"\n参数: 每次买入 $1000, 持有一天后开盘卖出")
    print(f"数据范围: 2024-01 ~ 2026-03")

    print(f"\n总交易: {len(df)}")
    wins = len(df[df['pnl'] > 0])
    losses = len(df[df['pnl'] <= 0])
    print(f"盈利: {wins}, 亏损: {losses}, 胜率: {wins/len(df)*100:.1f}%")

    print(f"\n总收益: ${df['pnl'].sum():,.2f}")
    print(f"平均收益: ${df['pnl'].mean():.2f}")
    print(f"平均收益率: {df['pnl_pct'].mean():.2f}%")

    print(f"\n最大盈利: ${df['pnl'].max():.2f} ({df['pnl_pct'].max():.2f}%)")
    print(f"最大亏损: ${df['pnl'].min():.2f} ({df['pnl_pct'].min():.2f}%)")

    print(f"\n按股票 (Top 15):")
    stock = df.groupby('symbol')['pnl'].agg(['count', 'sum', 'mean']).sort_values('sum', ascending=False)
    stock.columns = ['次数', '总收益', '平均']
    print(stock.head(15).to_string())

    # 按年月
    df['month'] = pd.to_datetime(df['sell_date']).dt.to_period('M')
    print(f"\n按月统计:")
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
        ('v1', SEPAStrategy),
        ('v1_plus', SEPAPlusStrategy),
        ('v_oneil', ONeilStrategy),
        ('v_ryan', RyanStrategy),
        ('v_kell', KellStrategy),
        ('v_kullamaggi', KullamaggiStrategy),
        ('v_zanger', ZangerStrategy),
        ('v_stine', StineStrategy),
        ('v_weinstein', WeinsteinStrategy),
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
        print("\n已保存到 output/v_nextday/trades.csv")


if __name__ == '__main__':
    main()
