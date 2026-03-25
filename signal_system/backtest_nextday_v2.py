"""
次日开盘买卖策略回测 - 优化版本

先预计算所有买入信号，然后模拟交易
"""

import json
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

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
    """加载本地缓存的所有股票数据"""
    cache_dir = Path('data/cache')
    market_data = {}

    for pkl_file in cache_dir.glob('*.pkl'):
        symbol = pkl_file.stem
        try:
            df = pd.read_pickle(pkl_file)
            if not df.empty:
                market_data[symbol] = df.sort_index()
        except Exception as e:
            print(f"加载 {symbol} 失败: {e}")

    print(f"加载了 {len(market_data)} 只股票的数据")
    return market_data


def get_trading_dates(market_data):
    """获取所有可用的交易日"""
    all_dates = set()
    for symbol, df in market_data.items():
        for idx in df.index:
            all_dates.add(idx.normalize())

    sorted_dates = sorted(all_dates)
    print(f"数据范围: {sorted_dates[0].date()} ~ {sorted_dates[-1].date()}")
    return sorted_dates


def precompute_buy_signals(market_data, trading_dates):
    """预计算所有买入信号"""
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

    # 存储每天的买入信号: {date: {symbol: signal_info}}
    buy_signals_by_date = defaultdict(dict)

    # 跳过前200天
    start_idx = 200

    for i, date in enumerate(trading_dates[start_idx:], start_idx):
        if date.tzinfo is None:
            date = date.tz_localize('UTC')

        if i % 200 == 0:
            print(f"预计算信号: {i - start_idx}/{len(trading_dates) - start_idx}")

        # 初始化策略
        for strat_id, strat_class in strategy_classes:
            if strat_id not in strategies_config:
                continue

            cfg = strategies_config[strat_id]
            clean_cfg = {k: v for k, v in cfg.items() if not isinstance(v, dict)}

            strategy = strat_class(clean_cfg, market_data, live_mode=False)
            strategy.positions = {}

            for symbol, df in market_data.items():
                df_slice = df[df.index <= date]
                if len(df_slice) < 200:
                    continue

                try:
                    signal = strategy._check_entry(symbol, df_slice, date)
                    if signal and signal.data.get("direction") == 'buy':
                        # 记录信号
                        if symbol not in buy_signals_by_date[date]:
                            buy_signals_by_date[date][symbol] = {
                                'strategies': [],
                                'strength': 0,
                            }
                        buy_signals_by_date[date][symbol]['strategies'].append(strat_id)
                        buy_signals_by_date[date][symbol]['strength'] = max(
                            buy_signals_by_date[date][symbol]['strength'],
                            signal.data.get('strength', 3)
                        )
                except Exception as e:
                    pass

    # 统计
    total_signals = sum(len(v) for v in buy_signals_by_date.values())
    print(f"共发现 {total_signals} 个买入信号")

    return buy_signals_by_date


def simulate_trades(market_data, trading_dates, buy_signals_by_date):
    """模拟交易"""
    BUY_AMOUNT = 1000
    trades = []
    pending_entries = {}

    # 创建日期到索引的映射
    date_to_idx = {d: i for i, d in enumerate(trading_dates)}

    start_idx = 200

    for i, date in enumerate(trading_dates[start_idx:], start_idx):
        if date.tzinfo is None:
            date = date.tz_localize('UTC')

        # 1. 检查是否有持仓需要卖出
        to_close = []
        for symbol, pending in list(pending_entries.items()):
            buy_date = pending['buy_date']
            if date.date() > buy_date.date():
                df = market_data.get(symbol)
                if df is not None:
                    df_slice = df[df.index <= date]
                    if not df_slice.empty:
                        sell_price = float(df_slice['open'].iloc[0])
                        buy_price = pending['buy_price']
                        shares = pending['shares']
                        pnl = (sell_price - buy_price) * shares
                        pnl_pct = (sell_price / buy_price - 1) * 100

                        trades.append({
                            'symbol': symbol,
                            'buy_date': buy_date.date(),
                            'sell_date': date.date(),
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'shares': shares,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                        })
                        to_close.append(symbol)

        for symbol in to_close:
            del pending_entries[symbol]

        # 2. 执行前一天产生的买入信号
        if i + 1 < len(trading_dates):
            next_date = trading_dates[i + 1]
            prev_date = trading_dates[i]  # 前一天

            # 获取前一天的买入信号
            if prev_date in buy_signals_by_date:
                for symbol in buy_signals_by_date[prev_date]:
                    if symbol in pending_entries:
                        continue

                    df = market_data.get(symbol)
                    if df is not None:
                        df_slice = df[df.index <= next_date]
                        if not df_slice.empty:
                            buy_price = float(df_slice['open'].iloc[0])
                            if buy_price > 0:
                                shares = BUY_AMOUNT / buy_price
                                pending_entries[symbol] = {
                                    'buy_date': next_date,
                                    'buy_price': buy_price,
                                    'shares': shares,
                                }

        if i % 500 == 0:
            print(f"模拟交易: {i - start_idx}/{len(trading_dates) - start_idx}, 持仓: {len(pending_entries)}, 交易: {len(trades)}")

    return trades


def analyze_results(trades):
    """分析回测结果"""
    if not trades:
        print("没有交易记录")
        return None

    trades_df = pd.DataFrame(trades)

    print("\n" + "="*60)
    print("次日开盘买卖策略回测结果")
    print("="*60)
    print(f"\n回测参数:")
    print(f"  买入金额: $1000/只")
    print(f"  持仓周期: 1个交易日（次日开盘卖出）")

    print(f"\n总交易次数: {len(trades)}")
    wins = len(trades_df[trades_df['pnl'] > 0])
    losses = len(trades_df[trades_df['pnl'] <= 0])
    print(f"盈利交易: {wins}")
    print(f"亏损交易: {losses}")
    print(f"胜率: {wins / len(trades_df) * 100:.1f}%")

    print(f"\n总收益: ${trades_df['pnl'].sum():,.2f}")
    print(f"平均收益: ${trades_df['pnl'].mean():.2f}")
    print(f"平均收益率: {trades_df['pnl_pct'].mean():.2f}%")
    print(f"收益率标准差: {trades_df['pnl_pct'].std():.2f}%")

    print(f"\n最大单笔盈利: ${trades_df['pnl'].max():.2f} ({trades_df['pnl_pct'].max():.2f}%)")
    print(f"最大单笔亏损: ${trades_df['pnl'].min():.2f} ({trades_df['pnl_pct'].min():.2f}%)")

    print(f"\n按股票统计 (Top 20):")
    stock_stats = trades_df.groupby('symbol').agg({
        'pnl': ['count', 'sum', 'mean'],
        'pnl_pct': ['mean', 'std']
    }).round(2)
    stock_stats.columns = ['次数', '总收益', '平均收益', '平均收益率%', '收益率标准差']
    stock_stats = stock_stats.sort_values('总收益', ascending=False)
    print(stock_stats.head(20).to_string())

    # 按年份统计
    trades_df['year'] = pd.to_datetime(trades_df['sell_date']).dt.year
    print(f"\n按年份统计:")
    yearly = trades_df.groupby('year').agg({
        'pnl': ['count', 'sum', 'mean'],
        'pnl_pct': 'mean'
    }).round(2)
    yearly.columns = ['次数', '总收益', '平均收益', '平均收益率%']
    print(yearly.to_string())

    return trades_df


def main():
    print("加载市场数据...")
    market_data = load_market_data()

    print("\n获取交易日...")
    trading_dates = get_trading_dates(market_data)

    print("\n预计算买入信号...")
    buy_signals_by_date = precompute_buy_signals(market_data, trading_dates)

    print("\n模拟交易...")
    trades = simulate_trades(market_data, trading_dates, buy_signals_by_date)

    print("\n分析结果...")
    trades_df = analyze_results(trades)

    if trades_df is not None:
        output_file = 'output/v_nextday/trades.csv'
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        trades_df.to_csv(output_file, index=False)
        print(f"\n交易记录已保存到: {output_file}")


if __name__ == '__main__':
    main()
