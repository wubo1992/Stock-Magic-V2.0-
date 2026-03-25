"""
次日开盘买卖策略回测

规则：
1. 收集所有现有策略的买入信号
2. 第二天开盘买入（$1000/只股票）
3. 持有一天后，第二天开盘卖出
4. 计算单日收益
"""

import json
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import numpy as np

# 加载配置
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# 加载所有策略配置
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


# 加载市场数据
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


# 初始化所有策略
def init_strategies(market_data):
    """初始化所有策略实例"""
    strategy_instances = []

    # 加载持仓（如果是回测模式，不需要）
    positions = {}

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

    for strat_id, strat_class in strategy_classes:
        if strat_id in strategies_config:
            cfg = strategies_config[strat_id]
            # 克隆配置，移除嵌套结构
            clean_cfg = {k: v for k, v in cfg.items() if not isinstance(v, dict)}

            strategy = strat_class(clean_cfg, market_data, live_mode=False)
            strategy.positions = {}  # 清空持仓
            strategy_instances.append(strategy)
            print(f"初始化策略: {strat_id}")

    return strategy_instances


def run_backtest(market_data, trading_dates, strategy_instances):
    """运行回测"""
    BUY_AMOUNT = 1000  # 每次买入金额

    # 交易记录
    trades = []
    pending_entries = {}  # {symbol: {'buy_date': date, 'buy_price': float, 'shares': float}}

    # 跳过前200天（需要足够历史数据计算指标）
    start_idx = 200

    for i, date in enumerate(trading_dates[start_idx:], start_idx):
        if date.tzinfo is None:
            date = date.tz_localize('UTC')

        # 1. 检查是否有持仓需要卖出
        to_close = []
        for symbol, pending in list(pending_entries.items()):
            buy_date = pending['buy_date']
            # 持有一天后卖出
            if date.date() > buy_date.date():
                # 卖出
                df = market_data.get(symbol)
                if df is not None:
                    df_slice = df[df.index <= date]
                    if not df_slice.empty:
                        # 开盘卖出
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

        # 清理已卖出的
        for symbol in to_close:
            del pending_entries[symbol]

        # 2. 收集所有策略的买入信号
        buy_signals = set()  # 使用set去重

        for strategy in strategy_instances:
            # 临时清空持仓
            original_positions = dict(strategy.positions)
            strategy.positions = {}

            # 运行策略获取当天信号
            for symbol, df in market_data.items():
                df_slice = df[df.index <= date]
                if len(df_slice) < 200:
                    continue

                signal = strategy._check_entry(symbol, df_slice, date)
                if signal and signal.data.get("direction") == 'buy':
                    buy_signals.add(symbol)

            # 恢复持仓
            strategy.positions = original_positions

        # 3. 第二天开盘买入
        # 找到下一个交易日
        if i + 1 < len(trading_dates):
            next_date = trading_dates[i + 1]
            if next_date.tzinfo is None:
                next_date = next_date.tz_localize('UTC')

            for symbol in buy_signals:
                if symbol in pending_entries:
                    continue  # 已有持仓

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

        # 进度显示
        if (i - start_idx) % 500 == 0:
            print(f"进度: {i - start_idx}/{len(trading_dates) - start_idx}, 持仓: {len(pending_entries)}, 交易: {len(trades)}")

    return trades


def analyze_results(trades):
    """分析回测结果"""
    if not trades:
        print("没有交易记录")
        return

    trades_df = pd.DataFrame(trades)

    print("\n" + "="*60)
    print("回测结果汇总")
    print("="*60)

    print(f"\n总交易次数: {len(trades)}")
    print(f"盈利交易: {len(trades_df[trades_df['pnl'] > 0])}")
    print(f"亏损交易: {len(trades_df[trades_df['pnl'] <= 0])}")
    print(f"胜率: {len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100:.1f}%")

    print(f"\n总收益: ${trades_df['pnl'].sum():,.2f}")
    print(f"平均收益: ${trades_df['pnl'].mean():.2f}")
    print(f"平均收益率: {trades_df['pnl_pct'].mean():.2f}%")

    print(f"\n最大单笔盈利: ${trades_df['pnl'].max():.2f}")
    print(f"最大单笔亏损: ${trades_df['pnl'].min():.2f}")

    print(f"\n按股票统计:")
    stock_stats = trades_df.groupby('symbol').agg({
        'pnl': ['count', 'sum', 'mean'],
        'pnl_pct': 'mean'
    }).round(2)
    stock_stats.columns = ['交易次数', '总收益', '平均收益', '平均收益率%']
    stock_stats = stock_stats.sort_values('总收益', ascending=False)
    print(stock_stats.head(20))

    return trades_df


def main():
    print("加载市场数据...")
    market_data = load_market_data()

    print("\n获取交易日...")
    trading_dates = get_trading_dates(market_data)

    print("\n初始化策略...")
    strategy_instances = init_strategies(market_data)

    print("\n运行回测...")
    trades = run_backtest(market_data, trading_dates, strategy_instances)

    print("\n分析结果...")
    trades_df = analyze_results(trades)

    # 保存结果
    if trades_df is not None:
        output_file = 'output/v_nextday/trades.csv'
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        trades_df.to_csv(output_file, index=False)
        print(f"\n交易记录已保存到: {output_file}")


if __name__ == '__main__':
    main()
