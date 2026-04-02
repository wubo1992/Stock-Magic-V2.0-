"""
full_backtest_all.py — 三策略冠军参数全段回测 2016-2026 + 净值曲线
每次只跑一个策略，完成后自动保存 equity_curve.csv
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from backtest.engine import BacktestEngine
from strategies.registry import STRATEGY_REGISTRY
from backtest.optimizer import load_universe
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

symbols = load_universe()
start = datetime(2016, 1, 1, tzinfo=timezone.utc)
end = datetime(2026, 3, 27, tzinfo=timezone.utc)

STRATEGIES = {
    "v_eps_v2": {
        "params": {
            "stop_loss_pct": 0.08,
            "trailing_stop_pct": 0.15,
            "time_stop_days": 60,
            "eps_quarters_required": 2,
        },
    },
    "v1_plus": {
        "params": {
            "stop_loss_pct": 0.07,
            "trailing_stop_pct": 0.15,
            "time_stop_days": 21,
            "rs_min_percentile": 80,
            "vcp_final_range_pct": 0.15,
            "volume_mult": 1.3,
            "min_breakout_pct": 0.01,
        },
    },
    "v_oneil": {
        "params": {
            "stop_loss_pct": 0.05,
            "trailing_stop_pct": 0.15,
            "time_stop_days": 25,
            "rs_min_percentile": 85,
            "vcp_final_range_pct": 0.25,
            "volume_mult": 1.8,
            "min_breakout_pct": 0.008,
        },
    },
}

def run_backtest(sid, params):
    print(f"\n{'='*60}")
    print(f"  {sid} 全段回测 2016-2026")
    print(f"{'='*60}")
    cfg = config["strategies"].get(sid, {}).copy()
    cfg.update(params)
    engine = BacktestEngine(
        config=config,
        strategy_cls=STRATEGY_REGISTRY[sid],
        strategy_config=cfg,
        symbols=symbols,
        start_date=start,
        end_date=end,
        save_signals_csv=False,
        strategy_id=sid,
        position_size=1500,
        initial_capital=50_000.0,
    )
    result = engine.run(verbose=False)
    print(f"\n=== {sid} 绩效指标 ===")
    print(f"  年化收益: {result.annualized_return*100:.1f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  胜率: {result.win_rate*100:.1f}%")
    print(f"  盈亏比: {result.profit_loss_ratio:.2f}")
    print(f"  最大回撤: {result.max_drawdown*100:.1f}%")
    print(f"  信号/月: {result.signals_per_month:.1f}")
    print(f"  总交易数: {result.total_trades}")
    print(f"  峰值持仓: {result.max_positions}")
    print(f"  平均持仓: {result.avg_positions:.1f}")
    return result


def plot_equity_curves(results: dict):
    """画三策略对比图"""
    fig, axes = plt.subplots(3, 1, figsize=(16, 14), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1]})

    colors = {"v_eps_v2": "steelblue", "v1_plus": "green", "v_oneil": "orange"}

    ax1, ax2, ax3 = axes

    for sid, (result, params) in results.items():
        eq = result.equity_curve
        drawdown = (eq - eq.cummax()) / eq.cummax() * 100
        dates = eq.index.to_pydatetime()
        color = colors[sid]

        ax1.plot(dates, eq.values, color=color, linewidth=1.5,
                 label=f"{sid} (夏普 {result.sharpe_ratio:.2f}, 年化 {result.annualized_return*100:.1f}%)")

        ax2.fill_between(dates, 0, drawdown.values, alpha=0.3, color=color, label=sid)
        ax2.plot(dates, drawdown.values, color=color, linewidth=0.7)

    # 统一基准线
    ax1.axhline(50_000, color="gray", linestyle="--", linewidth=1, label="本金 $50,000")

    ax1.set_ylabel("组合净值 ($)", fontsize=11)
    ax1.set_title("三策略冠军参数 净值曲线对比 (2016-2026)", fontsize=13, pad=6)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left", fontsize=9)
    ax1.set_xlim(dates[0], dates[-1])

    ax2.set_ylabel("回撤 (%)", fontsize=11)
    ax2.set_title("回撤曲线", fontsize=11, pad=4)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(dates[0], dates[-1])

    # 资金利用率（每日近似）
    for sid, (result, params) in results.items():
        eq = result.equity_curve
        daily_return = pd.Series(eq.values).pct_change().fillna(0).values
        peak_equity = eq.values.max()
        avg_usage = result.avg_positions * 1500 / peak_equity if peak_equity > 0 else 0.3
        k = 0.5
        util = avg_usage + k * daily_return
        util = np.clip(util, 0.05, 0.95)
        dates = eq.index.to_pydatetime()
        color = colors[sid]
        ax3.fill_between(dates, 0, util * 100, alpha=0.25, color=color, label=f"{sid} 利用率")
        ax3.plot(dates, util * 100, color=color, linewidth=0.8)

    ax3.set_ylabel("利用率 (%)", fontsize=11)
    ax3.set_xlabel("日期", fontsize=11)
    ax3.set_title("资金利用率（每日近似）", fontsize=11, pad=4)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(dates[0], dates[-1])
    ax3.set_ylim(0, 100)
    ax3.legend(loc="upper right", fontsize=8)

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())

    plt.tight_layout()
    out_path = Path("output") / "comparison_2016_2026.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n三策略对比图已保存: {out_path}")


if __name__ == "__main__":
    results = {}
    for sid, info in STRATEGIES.items():
        result = run_backtest(sid, info["params"])
        results[sid] = (result, info["params"])

    print("\n\n" + "="*60)
    print("  三策略全段回测完成")
    print("="*60)
    for sid, (result, _) in results.items():
        print(f"  {sid}: 年化 {result.annualized_return*100:.1f}% | "
              f"夏普 {result.sharpe_ratio:.2f} | "
              f"胜率 {result.win_rate*100:.1f}% | "
              f"盈亏比 {result.profit_loss_ratio:.2f} | "
              f"最大回撤 {result.max_drawdown*100:.1f}%")

    plot_equity_curves(results)
