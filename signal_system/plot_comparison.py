"""
根据回测报告汇总指标模拟14策略收益曲线对比图
资金约束: $50000本金, $1500/笔
测试区间: 2026-01-01 至 2026-03-27
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import re

# 设置字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Backtest summary data (501 stocks pool, 2026-01-01 ~ 2026-03-27)
BACKTEST_DATA = {
    'v1 (SEPA Original)': {
        'annual_return': -0.5,
        'sharpe': -0.23,
        'max_drawdown': 0.6,
        'win_rate': 61.3,
        'profit_loss_ratio': 1.94,
        'signals_per_month': 11.1,
        'total_trades': 31,
        'passed': 3,
        'trades': [
            ('ON', '2026-01-28', '2026-02-27', 64.94, 66.52, 2.4),
            ('VTRS', '2026-02-04', '2026-03-04', 14.23, 14.59, 2.5),
            ('TER', '2026-01-28', '2026-03-06', 250.61, 272.97, 8.9),
            ('FANG', '2026-03-02', '2026-03-13', 177.88, 182.39, 2.5),
            ('ROST', '2026-03-04', '2026-03-17', 213.02, 209.27, -1.8),
            ('NOC', '2026-01-05', '2026-03-27', 608.81, 692.09, 13.7),
            ('LHX', '2026-01-08', '2026-03-27', 324.77, 349.39, 7.6),
            ('JNJ', '2026-01-14', '2026-03-27', 217.48, 239.33, 10.0),
            ('PSX', '2026-02-03', '2026-03-27', 146.81, 184.00, 25.3),
            ('VLO', '2026-03-02', '2026-03-27', 214.92, 248.15, 15.5),
        ]
    },
    'v1_plus': {
        'annual_return': -1.2,
        'sharpe': -0.43,
        'max_drawdown': 0.7,
        'win_rate': 66.7,
        'profit_loss_ratio': 1.67,
        'signals_per_month': 12.9,
        'total_trades': 36,
        'passed': 3,
        'trades': [
            ('TER', '2026-01-28', '2026-03-06', 250.61, 272.97, 8.9),
            ('JCI', '2026-02-04', '2026-03-06', 129.02, 132.00, 2.3),
            ('FCX', '2026-01-06', '2026-03-13', 56.01, 56.35, 0.6),
            ('FANG', '2026-03-02', '2026-03-13', 177.88, 182.39, 2.5),
            ('ROST', '2026-03-04', '2026-03-17', 213.02, 209.27, -1.8),
            ('NOC', '2026-01-05', '2026-03-27', 608.81, 692.09, 13.7),
            ('LHX', '2026-01-08', '2026-03-27', 324.77, 349.39, 7.6),
            ('JNJ', '2026-01-14', '2026-03-27', 217.48, 239.33, 10.0),
            ('PSX', '2026-02-03', '2026-03-27', 146.81, 184.00, 25.3),
            ('VLO', '2026-03-02', '2026-03-27', 214.92, 248.15, 15.5),
        ]
    },
    'v_oneil (O\'Neil)': {
        'annual_return': -2.5,
        'sharpe': -1.00,
        'max_drawdown': 0.7,
        'win_rate': 61.0,
        'profit_loss_ratio': 1.18,
        'signals_per_month': 14.7,
        'total_trades': 41,
        'passed': 2,
        'trades': [
            ('TER', '2026-01-28', '2026-03-06', 250.61, 272.97, 8.9),
            ('JCI', '2026-02-04', '2026-03-06', 129.02, 132.00, 2.3),
            ('FCX', '2026-01-06', '2026-03-13', 56.01, 56.35, 0.6),
            ('FANG', '2026-03-02', '2026-03-13', 177.88, 182.39, 2.5),
            ('ROST', '2026-03-04', '2026-03-17', 213.02, 209.27, -1.8),
            ('NOC', '2026-01-05', '2026-03-27', 608.81, 692.09, 13.7),
            ('LHX', '2026-01-08', '2026-03-27', 324.77, 349.39, 7.6),
            ('JNJ', '2026-01-14', '2026-03-27', 217.48, 239.33, 10.0),
            ('PSX', '2026-02-03', '2026-03-27', 146.81, 184.00, 25.3),
            ('VLO', '2026-03-02', '2026-03-27', 214.92, 248.15, 15.5),
        ]
    },
    'v_ryan': {
        'annual_return': 1.4,
        'sharpe': 1.35,
        'max_drawdown': 0.2,
        'win_rate': 37.5,
        'profit_loss_ratio': 3.89,
        'signals_per_month': 2.9,
        'total_trades': 8,
        'passed': 4,
        'trades': [
            ('GS', '2026-01-05', '2026-01-20', 943.99, 937.70, -0.7),
            ('F', '2026-01-08', '2026-01-20', 14.24, 13.14, -7.7),
            ('WMT', '2026-01-12', '2026-01-27', 117.74, 116.72, -0.9),
            ('MNST', '2026-01-20', '2026-02-03', 81.46, 81.98, 0.6),
            ('LMT', '2026-01-29', '2026-02-12', 618.46, 634.40, 2.6),
            ('MCK', '2026-02-05', '2026-02-20', 958.62, 946.89, -1.2),
            ('ROST', '2026-03-04', '2026-03-17', 213.02, 209.27, -1.8),
            ('PSX', '2026-02-03', '2026-03-27', 146.81, 184.00, 25.3),
        ]
    },
    'v_kell': {
        'annual_return': -0.5,
        'sharpe': -0.49,
        'max_drawdown': 0.2,
        'win_rate': 60.0,
        'profit_loss_ratio': 0.81,
        'signals_per_month': 1.8,
        'total_trades': 5,
        'passed': 2,
        'trades': [
            ('HAL', '2026-01-05', '2026-01-20', 31.78, 31.88, 0.3),
            ('F', '2026-01-08', '2026-01-20', 14.24, 13.14, -7.7),
            ('MCK', '2026-02-05', '2026-02-20', 958.62, 946.89, -1.2),
            ('LUV', '2026-01-29', '2026-02-25', 48.23, 49.67, 3.0),
            ('LHX', '2026-01-08', '2026-03-27', 324.77, 349.39, 7.6),
        ]
    },
    'v_kullamaggi': {
        'annual_return': 0.5,
        'sharpe': 0.56,
        'max_drawdown': 0.2,
        'win_rate': 50.0,
        'profit_loss_ratio': 5.49,
        'signals_per_month': 0.7,
        'total_trades': 2,
        'passed': 3,
        'trades': [
            ('MCK', '2026-02-05', '2026-02-17', 958.62, 945.38, -1.4),
            ('LHX', '2026-01-08', '2026-03-27', 324.77, 349.39, 7.6),
        ]
    },
    'v_zanger': {
        'annual_return': -1.1,
        'sharpe': -0.50,
        'max_drawdown': 0.8,
        'win_rate': 37.1,
        'profit_loss_ratio': 2.37,
        'signals_per_month': 12.5,
        'total_trades': 35,
        'passed': 2,
        'trades': [
            ('HSIC', '2026-02-24', '2026-03-03', 83.24, 80.19, -3.7),
            ('KEYS', '2026-02-24', '2026-03-03', 301.60, 302.40, 0.3),
            ('GNRC', '2026-02-11', '2026-03-05', 214.92, 219.06, 1.9),
            ('SJM', '2026-02-26', '2026-03-05', 115.94, 111.41, -3.9),
            ('TER', '2026-02-03', '2026-03-06', 283.08, 272.97, -3.6),
            ('TPR', '2026-02-05', '2026-03-06', 142.81, 144.15, 0.9),
            ('SLB', '2026-01-05', '2026-03-27', 43.59, 52.32, 20.0),
            ('LMT', '2026-01-06', '2026-03-27', 519.28, 627.32, 20.8),
            ('LHX', '2026-01-08', '2026-03-27', 324.77, 349.39, 7.6),
            ('DVN', '2026-02-03', '2026-03-27', 41.11, 51.32, 24.8),
        ]
    },
    'v_stine': {
        'annual_return': -0.8,
        'sharpe': -1.92,
        'max_drawdown': 0.3,
        'win_rate': 0.0,
        'profit_loss_ratio': 0.00,
        'signals_per_month': 1.1,
        'total_trades': 3,
        'passed': 1,
        'trades': [
            ('F', '2026-01-08', '2026-01-20', 14.24, 13.14, -7.7),
            ('WMT', '2026-01-12', '2026-01-27', 117.74, 116.72, -0.9),
            ('MCK', '2026-02-05', '2026-02-20', 958.62, 946.89, -1.2),
        ]
    },
    'v_weinstein': {
        'annual_return': 8.2,
        'sharpe': 0.93,
        'max_drawdown': 2.8,
        'win_rate': 56.2,
        'profit_loss_ratio': 1.12,
        'signals_per_month': 78.4,
        'total_trades': 219,
        'passed': 2,
        'trades': [
            ('MPC', '2026-03-02', '2026-03-27', 209.79, 248.34, 18.4),
            ('VLO', '2026-03-02', '2026-03-27', 214.92, 248.15, 15.5),
            ('PSX', '2026-03-05', '2026-03-27', 166.47, 184.00, 10.5),
            ('WM', '2026-03-05', '2026-03-27', 245.06, 226.52, -7.6),
            ('DOW', '2026-03-09', '2026-03-27', 34.33, 39.45, 14.9),
            ('LYB', '2026-03-12', '2026-03-27', 74.34, 77.73, 4.6),
            ('VTR', '2026-03-16', '2026-03-27', 87.75, 82.69, -5.8),
            ('DELL', '2026-03-20', '2026-03-27', 158.08, 175.88, 11.3),
            ('OKE', '2026-03-20', '2026-03-27', 89.27, 93.59, 4.8),
            ('HPE', '2026-03-25', '2026-03-27', 25.79, 25.07, -2.8),
        ]
    },
    'v_weinstein_adx': {
        'annual_return': 1.5,
        'sharpe': 0.22,
        'max_drawdown': 2.2,
        'win_rate': 50.9,
        'profit_loss_ratio': 1.18,
        'signals_per_month': 20.4,
        'total_trades': 57,
        'passed': 2,
        'trades': [
            ('TGT', '2026-03-03', '2026-03-19', 120.76, 114.47, -5.2),
            ('LMT', '2026-03-02', '2026-03-20', 676.79, 627.85, -7.2),
            ('ROST', '2026-03-04', '2026-03-25', 213.02, 216.04, 1.4),
            ('XOM', '2026-01-29', '2026-03-27', 139.47, 165.44, 18.6),
            ('TRGP', '2026-02-09', '2026-03-27', 217.80, 250.44, 15.0),
            ('KEYS', '2026-02-20', '2026-03-27', 243.62, 281.12, 15.4),
            ('VLO', '2026-03-02', '2026-03-27', 214.92, 248.15, 15.5),
            ('PSX', '2026-03-05', '2026-03-27', 166.47, 184.00, 10.5),
            ('OXY', '2026-03-09', '2026-03-27', 54.76, 64.36, 17.5),
            ('MPC', '2026-03-12', '2026-03-27', 230.09, 248.34, 7.9),
        ]
    },
    'v_eps': {
        'annual_return': -1.6,
        'sharpe': -0.61,
        'max_drawdown': 1.1,
        'win_rate': 50.0,
        'profit_loss_ratio': 0.68,
        'signals_per_month': 9.3,
        'total_trades': 26,
        'passed': 3,
        'trades': [
            ('PNC', '2026-02-05', '2026-02-27', 238.57, 212.17, -11.1),
            ('FDX', '2026-02-03', '2026-03-06', 352.03, 357.52, 1.6),
            ('VRTX', '2026-02-13', '2026-03-09', 491.57, 460.81, -6.3),
            ('GRMN', '2026-02-18', '2026-03-11', 236.93, 235.09, -0.8),
            ('FIX', '2026-02-19', '2026-03-12', 1373.87, 1373.85, -0.0),
            ('YUM', '2026-02-23', '2026-03-13', 166.47, 160.44, -3.6),
            ('MU', '2026-01-06', '2026-03-26', 343.51, 355.56, 3.5),
            ('WDC', '2026-03-17', '2026-03-26', 313.75, 273.34, -12.9),
            ('TPL', '2026-02-19', '2026-03-27', 486.01, 521.80, 7.4),
            ('DELL', '2026-03-20', '2026-03-27', 158.08, 175.88, 11.3),
        ]
    },
    'v_eps_v2': {
        'annual_return': -2.4,
        'sharpe': -0.61,
        'max_drawdown': 1.6,
        'win_rate': 50.0,
        'profit_loss_ratio': 0.68,
        'signals_per_month': 9.3,
        'total_trades': 26,
        'passed': 3,
        'trades': [
            ('PNC', '2026-02-05', '2026-02-27', 238.57, 212.17, -11.1),
            ('FDX', '2026-02-03', '2026-03-06', 352.03, 357.52, 1.6),
            ('VRTX', '2026-02-13', '2026-03-09', 491.57, 460.81, -6.3),
            ('GRMN', '2026-02-18', '2026-03-11', 236.93, 235.09, -0.8),
            ('FIX', '2026-02-19', '2026-03-12', 1373.87, 1373.85, -0.0),
            ('YUM', '2026-02-23', '2026-03-13', 166.47, 160.44, -3.6),
            ('MU', '2026-01-06', '2026-03-26', 343.51, 355.56, 3.5),
            ('WDC', '2026-03-17', '2026-03-26', 313.75, 273.34, -12.9),
            ('TPL', '2026-02-19', '2026-03-27', 486.01, 521.80, 7.4),
            ('DELL', '2026-03-20', '2026-03-27', 158.08, 175.88, 11.3),
        ]
    },
    'v_eps_v1_plus': {
        'annual_return': -0.1,
        'sharpe': -0.17,
        'max_drawdown': 0.1,
        'win_rate': 0.0,
        'profit_loss_ratio': 0.00,
        'signals_per_month': 0.4,
        'total_trades': 1,
        'passed': 1,
        'trades': [
            ('GS', '2026-01-05', '2026-01-20', 943.99, 937.70, -0.7),
        ]
    },
    'v_adx50': {
        'annual_return': -10.2,
        'sharpe': -1.01,
        'max_drawdown': 4.8,
        'win_rate': 34.5,
        'profit_loss_ratio': 1.55,
        'signals_per_month': 78.8,
        'total_trades': 220,
        'passed': 2,
        'trades': [
            ('WELL', '2026-02-17', '2026-03-27', 214.80, 195.54, -9.0),
            ('MPC', '2026-03-02', '2026-03-27', 209.79, 248.34, 18.4),
            ('TRGP', '2026-03-02', '2026-03-27', 239.47, 250.44, 4.6),
            ('PNW', '2026-03-04', '2026-03-27', 103.02, 98.52, -4.4),
            ('BG', '2026-03-12', '2026-03-27', 125.84, 125.80, -0.0),
            ('APA', '2026-03-13', '2026-03-27', 34.47, 42.81, 24.2),
            ('DELL', '2026-03-16', '2026-03-27', 156.60, 175.88, 12.3),
            ('FE', '2026-03-16', '2026-03-27', 51.77, 50.03, -3.4),
            ('VTR', '2026-03-16', '2026-03-27', 87.75, 82.69, -5.8),
            ('SNDK', '2026-03-17', '2026-03-27', 720.16, 602.66, -16.3),
        ]
    },
}

# 资金参数
INITIAL_CAPITAL = 50000  # $50000本金
POSITION_SIZE = 1500     # $1500/笔

def build_equity_curve_from_trades(trades, start_date='2026-01-01', end_date='2026-03-27'):
    """
    根据交易记录构建每日净值曲线
    trades: list of (symbol, entry_date, exit_date, entry_price, exit_price, pnl_pct)
    """
    # 生成所有交易日
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日

    # 按日期排序交易
    trades_sorted = sorted(trades, key=lambda x: x[1])

    # 构建每日净值
    equity = {start_date: INITIAL_CAPITAL}
    current_capital = INITIAL_CAPITAL

    # 用交易扩展净值
    for symbol, entry_date_str, exit_date_str, entry_price, exit_price, pnl_pct in trades_sorted:
        entry_date = pd.to_datetime(entry_date_str)
        exit_date = pd.to_datetime(exit_date_str)

        if entry_date > pd.to_datetime(end_date):
            break

        # 计算持仓期间的每日净值变化（简化处理）
        # 在入场日和出场日之间，假设线性变化
        entry_price = float(entry_price)
        exit_price = float(exit_price)

        # 持仓股数
        shares = POSITION_SIZE / entry_price
        pnl = (exit_price - entry_price) * shares

        # 在出场日更新净值
        exit_date_key = exit_date_str
        if exit_date_key not in equity:
            equity[exit_date_key] = current_capital
        equity[exit_date_key] = current_capital + pnl
        current_capital = equity[exit_date_key]

    # 最后一天净值
    equity[end_date] = current_capital

    return equity


def simulate_equity_curve(strategy_name, data, start_date='2026-01-01', end_date='2026-03-27'):
    """
    基于汇总指标模拟净值曲线（当交易数据不完整时使用）
    """
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    n_days = len(dates)

    annual_return = data['annual_return'] / 100
    sharpe = data['sharpe']
    max_dd = data['max_drawdown'] / 100

    # 计算日均收益和波动率
    years = n_days / 252
    total_return = (1 + annual_return) ** years - 1

    # 从夏普比率反推波动率
    if sharpe > 0 and annual_return > 0:
        daily_vol = annual_return / sharpe / np.sqrt(252)
    else:
        daily_vol = 0.02  # 默认波动率

    # 生成日收益率序列
    np.random.seed(42)  # 可重复
    daily_returns = np.random.normal(annual_return / 252, daily_vol, n_days)

    # 确保总收益接近目标
    actual_total_return = np.exp(np.sum(np.log(1 + daily_returns))) - 1

    # 调整使总收益匹配
    if abs(actual_total_return) > 0.001:
        adjustment = (1 + total_return) / (1 + actual_total_return)
        daily_returns = (1 + daily_returns) * adjustment - 1

    # 构建净值曲线
    equity = INITIAL_CAPITAL * np.cumprod(1 + daily_returns)
    equity = np.insert(equity, 0, INITIAL_CAPITAL)  # 插入初始值

    return dates, equity


def plot_all_strategies():
    """绘制所有策略的收益曲线对比图"""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 1, figsize=(16, 12))

    start_date = '2026-01-02'  # 第一个交易日
    end_date = '2026-03-27'
    dates = pd.date_range(start=start_date, end=end_date, freq='B')

    # 颜色映射
    colors = plt.cm.tab20(np.linspace(0, 1, 14))

    # ========== 图1: 所有策略对比 ==========
    ax1 = axes[0]

    for idx, (strategy_name, data) in enumerate(BACKTEST_DATA.items()):
        trades = data['trades']

        # 尝试从实际交易数据构建曲线
        equity = build_equity_curve_from_trades(trades, start_date, end_date)

        # 转换为Series
        dates_equity = pd.to_datetime(list(equity.keys()))
        values = list(equity.values())

        # 插值到每日
        equity_series = pd.Series(values, index=dates_equity).sort_index()
        equity_daily = equity_series.reindex(dates, method='ffill').fillna(INITIAL_CAPITAL)

        ax1.plot(equity_daily.index, equity_daily.values,
                label=f"{strategy_name} ({(values[-1]/INITIAL_CAPITAL-1)*100:.1f}%)",
                color=colors[idx], linewidth=1.5, alpha=0.8)

    # 初始资金线
    ax1.axhline(y=INITIAL_CAPITAL, color='black', linestyle='--', alpha=0.5, label='Initial $50,000')
    ax1.set_title('14 Strategies Equity Curve Comparison (2026-01-01 to 2026-03-27)\n$50,000 Capital, $1,500/Trade | 501 Stocks Pool', fontsize=14)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(loc='upper left', fontsize=7, ncol=2)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # ========== 图2: 综合评级排名 ==========
    ax2 = axes[1]

    # 准备数据
    strategies = list(BACKTEST_DATA.keys())
    passed = [BACKTEST_DATA[s]['passed'] for s in strategies]
    returns = [BACKTEST_DATA[s]['annual_return'] for s in strategies]
    sharpes = [BACKTEST_DATA[s]['sharpe'] for s in strategies]

    y_pos = np.arange(len(strategies))

    # 绘制达标数和收益
    bar_colors = ['green' if p >= 4 else 'orange' if p >= 3 else 'red' for p in passed]
    bars = ax2.barh(y_pos, passed, color=bar_colors, alpha=0.7)

    # 添加收益和夏普标注
    for i, (s, p, r, sh) in enumerate(zip(strategies, passed, returns, sharpes)):
        label = f"{r:+.1f}% | Sharpe{sh:+.2f}"
        ax2.text(p + 0.1, i, label, va='center', fontsize=9)

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([s.replace(' ', '\n') for s in strategies], fontsize=8)
    ax2.set_xlabel('Passed Items (out of 6)')
    ax2.set_title('Strategy Pass Rate (Green: 4+, Orange: 3, Red: <3) | Annual Return% & Sharpe Ratio', fontsize=11)
    ax2.set_xlim(0, 8)
    ax2.axvline(x=4, color='green', linestyle='--', alpha=0.5, label='Pass Line (4/6)')

    plt.tight_layout()

    # 保存图片
    output_path = '/Users/wubo/Desktop/信号系统克劳德V3.1_Minimax支线/strategies_comparison_2026_Q1.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")

    # 打印汇总表
    print("\n" + "="*110)
    print("501 Stocks Pool - 2026 Q1 (2026-01-01 to 2026-03-27) Backtest Summary")
    print("Capital: $50,000 | Position Size: $1,500/trade")
    print("="*110)
    print(f"{'Strategy':<22} {'Ann.Return':>12} {'Sharpe':>8} {'MaxDD':>10} {'WinRate':>8} {'P/L':>8} {'Sig/Mo':>8} {'Pass':>6}")
    print("-"*110)
    for strategy, data in sorted(BACKTEST_DATA.items(), key=lambda x: x[1]['passed'], reverse=True):
        print(f"{strategy:<22} {data['annual_return']:>+11.1f}% {data['sharpe']:>+7.2f} {data['max_drawdown']:>+9.1f}% {data['win_rate']:>+7.1f}% {data['profit_loss_ratio']:>+7.2f} {data['signals_per_month']:>+7.1f} {data['passed']:>5}/6")
    print("-"*110)

    return fig


if __name__ == '__main__':
    fig = plot_all_strategies()
    # plt.show()  # Commented out for batch processing
