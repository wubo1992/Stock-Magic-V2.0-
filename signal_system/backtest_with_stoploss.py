"""
次日开盘买卖策略回测 - 带止损止盈版本

规则：
1. 任何策略产生买入信号 → 次日开盘买入 $1000
2. 持续持仓，每天检查：
   - 止损: -5% 减仓一半，-10% 清仓
   - 止盈: +10% 减仓一半，+20% 清仓
"""

import yaml
from pathlib import Path
from collections import defaultdict

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
            # 至少500天数据，2024年后至少100天
            if len(df) >= 500:
                df = df[df.index >= pd.Timestamp('2024-01-01', tz='UTC')]
                if len(df) >= 100:
                    market_data[symbol] = df.sort_index()
        except:
            pass

    print(f"加载: {len(market_data)} 只股票", flush=True)
    return market_data


def get_trading_dates(market_data):
    all_dates = sorted(set(idx.normalize() for df in market_data.values() for idx in df.index))
    print(f"交易日: {all_dates[0].date()} ~ {all_dates[-1].date()}", flush=True)
    return all_dates


def run_backtest():
    BUY_AMOUNT = 1000

    print("加载数据...", flush=True)
    market_data = load_market_data()
    trading_dates = get_trading_dates(market_data)

    strategy_classes = [
        ('v1', SEPAStrategy), ('v1_plus', SEPAPlusStrategy), ('v_oneil', ONeilStrategy),
        ('v_ryan', RyanStrategy), ('v_kell', KellStrategy), ('v_kullamaggi', KullamaggiStrategy),
        ('v_zanger', ZangerStrategy), ('v_stine', StineStrategy), ('v_weinstein', WeinsteinStrategy),
    ]

    trades = []
    pending = {}  # {symbol: {'date': buy_date, 'shares': shares, 'avg_price': avg_price, 'half_sold': False}}
    date_idx = {d: i for i, d in enumerate(trading_dates)}

    print("开始回测...", flush=True)

    for i, date in enumerate(trading_dates):
        if i % 100 == 0:
            print(f"进度: {i}/{len(trading_dates)}", flush=True)

        # 跳过前面需要历史数据的部分
        if i < 200:
            continue

        # 收集当天的买入信号
        buy_signals = set()

        for strat_id, strat_class in strategy_classes:
            if strat_id not in strategies_config:
                continue

            cfg = strategies_config[strat_id]
            clean_cfg = {k: v for k, v in cfg.items() if not isinstance(v, dict)}

            for symbol, df in market_data.items():
                df_slice = df[df.index <= date]
                if len(df_slice) < 200:
                    continue

                try:
                    strat = strat_class(clean_cfg, {symbol: df_slice}, live_mode=False)
                    strat.positions = {}
                    sig = strat._check_entry(symbol, df_slice, date)
                    if sig and sig.data.get("direction") == 'buy':
                        buy_signals.add(symbol)
                except:
                    pass

        # 买入信号 - 次日执行
        if i + 1 < len(trading_dates):
            next_date = trading_dates[i + 1]

            for symbol in buy_signals:
                if symbol in pending:
                    continue

                df = market_data.get(symbol)
                if df is not None:
                    next_data = df[df.index <= next_date]
                    if not next_data.empty:
                        buy_price = float(next_data['close'].iloc[-1])
                        if buy_price > 0:
                            pending[symbol] = {
                                'date': next_date,
                                'price': buy_price,
                                'shares': BUY_AMOUNT / buy_price,
                                'half_sold': False,  # 是否已经卖出一半
                            }

        # 检查持仓的止损止盈
        to_close = []
        for symbol, p in list(pending.items()):
            df = market_data.get(symbol)
            if df is None:
                continue

            # 获取当天的价格
            current_data = df[df.index <= date]
            if current_data.empty:
                continue

            current_price = float(current_data['close'].iloc[-1])
            buy_price = p['price']
            shares = p['shares']
            half_sold = p.get('half_sold', False)

            # 计算涨跌幅
            pct_change = (current_price / buy_price - 1) * 100

            # 止盈: +20% 清仓，+10% 卖一半
            if pct_change >= 20:
                # 全部卖出
                pnl = (current_price - buy_price) * shares
                pnl_pct = pct_change
                trades.append({
                    'symbol': symbol,
                    'buy_date': p['date'].date(),
                    'sell_date': date.date(),
                    'buy_price': round(buy_price, 2),
                    'sell_price': round(current_price, 2),
                    'shares': round(shares, 4),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': '止盈20%',
                })
                to_close.append(symbol)
            elif pct_change >= 10 and not half_sold:
                # 卖出一半
                sell_shares = shares / 2
                pnl = (current_price - buy_price) * sell_shares
                pnl_pct = (current_price / buy_price - 1) * 100
                trades.append({
                    'symbol': symbol,
                    'buy_date': p['date'].date(),
                    'sell_date': date.date(),
                    'buy_price': round(buy_price, 2),
                    'sell_price': round(current_price, 2),
                    'shares': round(sell_shares, 4),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': '止盈10%卖一半',
                })
                # 更新持仓
                pending[symbol] = {
                    'date': p['date'],
                    'price': buy_price,
                    'shares': shares / 2,
                    'half_sold': True,
                }
            # 止损: -10% 清仓，-5% 卖一半
            elif pct_change <= -10:
                # 全部卖出
                pnl = (current_price - buy_price) * shares
                pnl_pct = pct_change
                trades.append({
                    'symbol': symbol,
                    'buy_date': p['date'].date(),
                    'sell_date': date.date(),
                    'buy_price': round(buy_price, 2),
                    'sell_price': round(current_price, 2),
                    'shares': round(shares, 4),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': '止损10%',
                })
                to_close.append(symbol)
            elif pct_change <= -5 and not half_sold:
                # 卖出一半
                sell_shares = shares / 2
                pnl = (current_price - buy_price) * sell_shares
                pnl_pct = (current_price / buy_price - 1) * 100
                trades.append({
                    'symbol': symbol,
                    'buy_date': p['date'].date(),
                    'sell_date': date.date(),
                    'buy_price': round(buy_price, 2),
                    'sell_price': round(current_price, 2),
                    'shares': round(sell_shares, 4),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': '止损5%卖一半',
                })
                # 更新持仓
                pending[symbol] = {
                    'date': p['date'],
                    'price': buy_price,
                    'shares': shares / 2,
                    'half_sold': True,
                }

        for symbol in to_close:
            if symbol in pending:
                del pending[symbol]

    # 分析结果
    if not trades:
        print("无交易")
        return

    df = pd.DataFrame(trades)

    print("\n" + "="*60)
    print("次日开盘买卖策略回测结果（带止损止盈）")
    print("="*60)
    print(f"参数: 每次买入 $1000")
    print(f"止损: -5%卖一半, -10%清仓")
    print(f"止盈: +10%卖一半, +20%清仓")
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

    # 按退出原因统计
    print(f"\n按退出原因:")
    exit_stats = df.groupby('exit_reason').agg({
        'pnl': ['count', 'sum', 'mean'],
        'pnl_pct': 'mean'
    })
    exit_stats.columns = ['次数', '总收益', '平均收益', '平均收益率%']
    print(exit_stats.to_string())

    # 按月统计
    df['month'] = pd.to_datetime(df['sell_date']).dt.to_period('M')
    print(f"\n按月:")
    monthly = df.groupby('month').agg({'pnl': ['count', 'sum'], 'pnl_pct': 'mean'})
    monthly.columns = ['次数', '总收益', '收益率%']
    print(monthly.tail(15).to_string())

    # 保存
    Path('output/v_nextday_stoploss').mkdir(parents=True, exist_ok=True)
    df.to_csv('output/v_nextday_stoploss/trades.csv', index=False)
    print("\n已保存到 output/v_nextday_stoploss/trades.csv")


if __name__ == '__main__':
    run_backtest()
