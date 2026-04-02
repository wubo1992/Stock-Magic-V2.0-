"""
plot_equity_curve.py — Weinstein 牛市灵敏捕捉版 收益曲线 & 资金使用率（正确版）
资金使用率 = 持股数 × $2000 / 当日总资本（而非初始本金）
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

PROJECT = Path("/Users/wubo/Desktop/信号系统克劳德V3.1_Minimax支线/signal_system")
sys.path.insert(0, str(PROJECT))

from main import load_config, resolve_strategy, _read_universe_md
from backtest.engine import BacktestEngine


def run_and_plot():
    config = load_config(str(PROJECT / "config.yaml"))
    strategy_cls, strategy_id, strategy_name, strategy_config = resolve_strategy(config, "v_weinstein_bull_sensitive")

    start_date = datetime(2016, 1, 1, tzinfo=timezone.utc)
    end_date   = datetime(2026, 3, 27, tzinfo=timezone.utc)

    symbols = _read_universe_md()
    if not symbols:
        print("[错误] 找不到股票池")
        return

    print("运行回测中...")
    engine = BacktestEngine(
        config,
        strategy_cls=strategy_cls,
        strategy_config=strategy_config,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        save_signals_csv=False,
        strategy_id=strategy_id,
        position_size=2000.0,
        initial_capital=50000.0,
    )
    result = engine.run(verbose=False)

    equity: pd.Series = result.equity_curve  # datetime index → portfolio value

    # ── 重建每日持仓数和资金使用率（正确公式）─────────────────
    trades = [t for t in result.trades if t.is_closed]

    trading_dates = equity.index.tolist()
    daily_pos = {d: 0 for d in trading_dates}

    for t in trades:
        ed = t.entry_date.replace(tzinfo=None) if t.entry_date.tzinfo else t.entry_date
        xd = t.exit_date.replace(tzinfo=None) if t.exit_date.tzinfo else t.exit_date
        for d in trading_dates:
            d_naive = d.replace(tzinfo=None) if d.tzinfo else d
            if ed <= d_naive <= xd:
                daily_pos[d] += 1

    daily_df = pd.DataFrame({'date': list(daily_pos.keys()), 'positions': list(daily_pos.values())})
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    daily_df = daily_df.sort_values('date').reset_index(drop=True)

    # 用 equity（当日总资本）来计算资金使用率
    equity_vals = equity.values  # 当日总资本
    equity_idx = equity.index.to_list()

    usage_list = []
    pos_list = []
    for i, d in enumerate(daily_df['date']):
        # 找到 equity 中对应的日期
        d_naive = d.replace(tzinfo=None) if d.tzinfo else d
        # 找到最接近的 equity index
        closest_idx = 0
        min_diff = float('inf')
        for j, ed in enumerate(equity_idx):
            ed_naive = ed.replace(tzinfo=None) if ed.tzinfo else ed
            diff = abs((ed_naive - d_naive).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_idx = j
        current_capital = equity_vals[closest_idx]
        pos = daily_df.iloc[i]['positions']
        usage = pos * 2000 / current_capital if current_capital > 0 else 0
        usage_list.append(usage)
        pos_list.append(pos)

    daily_df['capital_usage'] = usage_list
    daily_df['positions'] = pos_list
    daily_df = daily_df.set_index('date')

    peak_pos = daily_df['positions'].max()
    peak_cap = daily_df['capital_usage'].max()
    avg_cap = daily_df['capital_usage'].mean()
    avg_pos = daily_df['positions'].mean()

    print(f"峰值持仓：{peak_pos} 股")
    print(f"峰值资金使用率：{peak_cap:.1%}")
    print(f"平均资金使用率：{avg_cap:.1%}")
    print(f"平均持仓：{avg_pos:.1f} 股")

    # ── 绑图 ────────────────────────────────────────────────
    equity_df = equity.reset_index()
    equity_df.columns = ['date', 'value']
    equity_df['date'] = pd.to_datetime(equity_df['date'])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 9),
                                    gridspec_kw={'height_ratios': [2.5, 1]})

    # 图1：收益曲线
    ax1.plot(equity_df['date'], equity_df['value'],
             color='#1976D2', linewidth=1.2, label='Portfolio Value')
    ax1.fill_between(equity_df['date'], equity_df['value'],
                     alpha=0.12, color='#1976D2')
    ax1.axhline(y=50000, color='gray', linestyle='--',
                linewidth=0.8, alpha=0.7, label='Initial $50,000')
    final_val = equity_df['value'].iloc[-1]
    final_date = equity_df['date'].iloc[-1]
    ax1.annotate(f'${final_val:,.0f}',
                 xy=(final_date, final_val),
                 xytext=(5, 0), textcoords='offset points',
                 fontsize=9, color='#1976D2')
    ax1.set_ylabel('Portfolio Value ($)', fontsize=11)
    ax1.set_title(f'{strategy_name}\nEquity Curve & Capital Utilization — 2016-01 to 2026-03',
                  fontsize=13, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.25)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))

    # 图2：资金使用率（正确公式）
    cap_clipped = daily_df['capital_usage'].clip(upper=1.5)
    ax2.fill_between(daily_df.index, cap_clipped,
                     alpha=0.35, color='#FF9800', label='Capital Utilization')
    ax2.plot(daily_df.index, cap_clipped,
             color='#FF9800', linewidth=0.5)
    ax2.axhline(y=1.0, color='#4CAF50', linestyle='--',
                linewidth=1.0, alpha=0.9, label='100% Utilization (No Leverage)')
    ax2.axhline(y=peak_cap, color='#F44336', linestyle='--',
                linewidth=0.8, alpha=0.8, label=f'Peak {peak_cap:.0%}')
    ax2.set_ylabel('Capital Utilization', fontsize=11)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.set_ylim(0, min(1.5, peak_cap * 1.15))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.25)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_major_locator(mdates.YearLocator(1))

    plt.tight_layout()

    out_dir = PROJECT / "output" / strategy_id / "backtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "equity_curve_2016_2026.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"\n图片已保存：{out_path}")
    plt.close()


if __name__ == "__main__":
    run_and_plot()
