"""
backtest_mu.py — MU单只股票回测脚本（临时用，不修改UNIVERSE.md）

用法：
    uv run python backtest_mu.py

回测参数：
    股票：MU（美光）
    策略：v_kell（Oliver Kell VCP 2.0）
    区间：2020-07-27 至 2026-03-11（使用本地缓存数据）
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import pickle
import yaml
import pandas as pd
import numpy as np
from strategies.registry import get_strategy
from events import EventQueue


def load_cache(symbol: str, cache_dir: Path) -> pd.DataFrame | None:
    """直接从pkl加载缓存，统一列名大小写。"""
    pkl_path = cache_dir / f"{symbol}.pkl"
    if not pkl_path.exists():
        return None
    with open(pkl_path, 'rb') as f:
        df = pickle.load(f)
    df.columns = df.columns.str.lower()
    return df


def run_backtest(
    strategy_cls,
    strategy_config: dict,
    market_data: dict[str, pd.DataFrame],
    start_date: datetime,
    end_date: datetime,
    target_symbol: str,
    verbose: bool = True,
):
    """简单回测循环，参考 engine.py 的逻辑。"""
    # 确定交易日
    ref_df = next(iter(market_data.values()))
    ref_index = ref_df.index
    if ref_index.tzinfo is None:
        ref_index = ref_index.tz_localize("UTC")

    trading_days = ref_index[
        (ref_index >= start_date) & (ref_index <= end_date)
    ].to_pydatetime()

    if len(trading_days) == 0:
        raise RuntimeError("指定日期范围内没有交易日")

    if verbose:
        print(f"  交易日：{len(trading_days)} 天")
        print(f"  首个交易日：{trading_days[0].date()}，最后交易日：{trading_days[-1].date()}")

    # 初始化策略
    strategy = strategy_cls(strategy_config, market_data)
    queue = EventQueue()

    # 交易记录
    open_trades = {}  # symbol -> {entry_date, entry_price, strength}
    all_trades = []   # 已平仓的交易

    WARMUP = 252  # 预热天数

    for i, date in enumerate(trading_days):
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        # 跳过预热期
        if i < WARMUP:
            continue

        # 运行策略
        signals = strategy.run_date(date, queue)

        for sig in signals:
            sym = sig.symbol
            direction = sig.data.get("direction", "")
            reason = sig.data.get("reason", "")
            strength = sig.data.get("strength", 0)

            if direction == "buy" and sym not in open_trades:
                # 开仓
                df_sym = market_data[sym]
                idx_list = df_sym.index.tolist()
                if date in idx_list:
                    entry_price = float(df_sym.loc[date, "close"])
                else:
                    entry_price = float(df_sym.iloc[df_sym.index <= date]["close"].iloc[-1])

                open_trades[sym] = {
                    "entry_date": date,
                    "entry_price": entry_price,
                    "strength": strength,
                    "reason": reason,
                }
                if verbose:
                    print(f"  [买入] {sym} @ ${entry_price:.2f} on {date.date()} | {reason[:60]}")

            elif direction == "sell" and sym in open_trades:
                # 平仓
                trade = open_trades.pop(sym)
                df_sym = market_data[sym]
                if date in df_sym.index:
                    exit_price = float(df_sym.loc[date, "close"])
                else:
                    exit_price = float(df_sym.iloc[df_sym.index <= date]["close"].iloc[-1])

                pnl_pct = exit_price / trade["entry_price"] - 1
                all_trades.append({
                    "symbol": sym,
                    "entry_date": trade["entry_date"],
                    "exit_date": date,
                    "entry_price": trade["entry_price"],
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct,
                    "exit_reason": reason,
                    "strength": trade["strength"],
                })
                if verbose:
                    sign = "+" if pnl_pct >= 0 else ""
                    print(f"  [卖出] {sym} @ ${exit_price:.2f} on {date.date()} | {sign}{pnl_pct*100:.1f}% | {reason[:40]}")

    # 回测结束时强制平仓
    for sym, trade_info in open_trades.items():
        df_sym = market_data.get(sym)
        if df_sym is None:
            continue
        last_date = df_sym.index[-1]
        if last_date.tzinfo is None:
            last_date = last_date.tz_localize("UTC")
        exit_price = float(df_sym.iloc[-1]["close"])
        pnl_pct = exit_price / trade_info["entry_price"] - 1
        all_trades.append({
            "symbol": sym,
            "entry_date": trade_info["entry_date"],
            "exit_date": last_date.to_pydatetime(),
            "entry_price": trade_info["entry_price"],
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "exit_reason": "回测结束强制平仓",
            "strength": trade_info["strength"],
        })

    # 过滤只保留目标股票的交易
    filtered_trades = [t for t in all_trades if t["symbol"] == target_symbol]
    return filtered_trades


def print_report(trades, start_date, end_date, strategy_name):
    """打印回测报告。"""
    sep = "═" * 60

    print(f"\n{sep}")
    print(f"  回测报告 — {strategy_name}")
    print(f"  测试区间：{start_date.date()} 至 {end_date.date()}")
    print(f"  股票：TSM（台积电）")
    print(sep)

    if not trades:
        print("  ⚠️  无交易记录")
        print(sep)
        return

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    win_rate = len(wins) / len(trades) if trades else 0
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    total_return = np.prod([1 + t["pnl_pct"] for t in trades]) - 1
    years = (end_date - start_date).days / 365.25
    annualized = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    equity = [1.0]
    for t in trades:
        equity.append(equity[-1] * (1 + t["pnl_pct"]))
    equity = np.array(equity)
    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max
    max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0

    returns = [t["pnl_pct"] for t in trades]
    if len(returns) > 1:
        sharpe = (np.mean(returns) - 0.04/252) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    else:
        sharpe = 0

    months = years * 12
    signals_per_month = len(trades) / months if months > 0 else 0

    win_pass = "✓" if win_rate >= 0.40 else "✗"
    plr_pass = "✓" if profit_loss_ratio >= 1.5 else "✗"
    mdd_pass = "✓" if max_drawdown <= 0.25 else "✗"
    freq_pass = "✓" if 0.5 <= signals_per_month <= 10 else "✗"
    ar_pass = "✓" if annualized >= 0.15 else "✗"
    sr_pass = "✓" if sharpe >= 1.0 else "✗"

    passes = sum([
        win_rate >= 0.40,
        profit_loss_ratio >= 1.5,
        max_drawdown <= 0.25,
        0.5 <= signals_per_month <= 10,
        annualized >= 0.15,
        sharpe >= 1.0,
    ])

    print(f"\n  总交易笔数：{len(trades)} 笔（{len(wins)}胜 / {len(losses)}负）")
    print(f"  {'指标':<18} {'数值':>10}   {'及格线':>10}  {'状态'}")
    print(f"  {'-'*48}")
    print(f"  {'胜率':<18} {win_rate*100:>9.1f}%   {'> 40%':>10}   {win_pass}")
    print(f"  {'盈亏比':<17} {profit_loss_ratio:>10.2f}   {'> 1.5':>10}   {plr_pass}")
    print(f"  {'最大回撤':<16} {max_drawdown*100:>9.1f}%   {'< 25%':>10}   {mdd_pass}")
    print(f"  {'每月信号数':<15} {signals_per_month:>10.1f}   {'0.5~10':>10}   {freq_pass}")
    print(f"  {'年化收益':<16} {annualized*100:>9.2f}%   {'> 15%':>10}   {ar_pass}")
    print(f"  {'夏普比率':<16} {sharpe:>10.2f}   {'> 1.0':>10}   {sr_pass}")
    print(f"  {'-'*48}")
    print(f"  综合评级：{passes}/6 项达标")

    if wins:
        print(f"\n  盈利笔数：{len(wins)} 笔，平均盈利 {avg_win*100:.1f}%")
    if losses:
        print(f"  亏损笔数：{len(losses)} 笔，平均亏损 {avg_loss*100:.1f}%")

    print(f"\n  【交易明细】")
    print(f"  {'买入日':<12} {'卖出日':<12} {'买入价':>8} {'卖出价':>8} {'盈亏':>8}")
    print(f"  {'-'*50}")
    for t in sorted(trades, key=lambda x: x["entry_date"]):
        sign = "+" if t["pnl_pct"] >= 0 else ""
        print(f"  {t['entry_date'].strftime('%Y-%m-%d'):<12} "
              f"{t['exit_date'].strftime('%Y-%m-%d'):<12} "
              f"${t['entry_price']:>7.2f} "
              f"${t['exit_price']:>7.2f} "
              f"{sign}{t['pnl_pct']*100:>6.1f}%")

    print(sep)

    if passes >= 5:
        verdict = "合格 ✓"
    elif passes >= 3:
        verdict = "需要优化"
    else:
        verdict = "不合格 ✗"
    print(f"\n  【结论】{verdict}（{passes}/6 项达标）")

    return {
        "total_trades": len(trades),
        "win_rate": win_rate,
        "profit_loss_ratio": profit_loss_ratio,
        "max_drawdown": max_drawdown,
        "annualized": annualized,
        "sharpe": sharpe,
        "signals_per_month": signals_per_month,
        "passes": passes,
    }


def main():
    target_symbol = "TSM"
    strategy_id = "v_golden_cross"
    start_str = "2020-07-27"
    end_str = "2026-03-11"

    # 用于RS计算的陪跑股票（市场代表性股票）
    companion_symbols = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "AMD", "INTC", "TSLA"]

    print("=" * 60)
    print(f"MU 单股票回测 — 金叉死叉策略V1")
    print(f"区间：{start_str} 至 {end_str}（本地缓存）")
    print("=" * 60)

    # 加载配置
    config_path = ROOT / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    strategy_config = config["strategies"][strategy_id]
    strategy_name = strategy_config.get("name", strategy_id)
    strategy_config = dict(strategy_config)  # 复制，避免污染原配置

    strategy_cls = get_strategy(strategy_id)

    # 加载缓存
    cache_dir = ROOT / "data" / "cache"
    start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    market_data = {}

    # 加载MU
    df_mu = load_cache(target_symbol, cache_dir)
    if df_mu is None:
        print(f"[错误] 找不到 {target_symbol} 缓存")
        sys.exit(1)
    if df_mu.index.tzinfo is None:
        df_mu.index = df_mu.index.tz_localize("UTC")
    df_mu = df_mu[(df_mu.index >= start_date) & (df_mu.index <= end_date)]
    market_data[target_symbol] = df_mu
    print(f"\n[数据] {target_symbol}：{len(df_mu)} 个交易日")

    # 运行回测
    trades = run_backtest(
        strategy_cls=strategy_cls,
        strategy_config=strategy_config,
        market_data=market_data,
        start_date=start_date,
        end_date=end_date,
        target_symbol=target_symbol,
        verbose=True,
    )

    # 打印报告
    stats = print_report(trades, start_date, end_date, f"{strategy_name}（TSM）")

    if stats is None:
        stats = {
            "total_trades": 0,
            "win_rate": 0,
            "profit_loss_ratio": 0,
            "max_drawdown": 0,
            "annualized": 0,
            "sharpe": 0,
            "signals_per_month": 0,
            "passes": 0,
        }

    # 保存报告
    report_path = ROOT / "output" / "backtest_mu.md"
    report_path.parent.mkdir(exist_ok=True)

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    lines = [
        f"# TSM 回测报告 — {strategy_name}",
        "",
        f"> 区间：{start_str} 至 {end_str}",
        f"> 股票：TSM（台积电）",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 绩效指标",
        "",
        "| 指标 | 数值 | 及格线 | 状态 |",
        "|------|------|--------|------|",
        f"| 胜率 | {stats['win_rate']*100:.1f}% | > 40% | {'✓' if stats['win_rate'] >= 0.40 else '✗'} |",
        f"| 盈亏比 | {stats['profit_loss_ratio']:.2f} | > 1.5 | {'✓' if stats['profit_loss_ratio'] >= 1.5 else '✗'} |",
        f"| 最大回撤 | {stats['max_drawdown']*100:.1f}% | < 25% | {'✓' if stats['max_drawdown'] <= 0.25 else '✗'} |",
        f"| 每月信号 | {stats['signals_per_month']:.1f} | 0.5~10 | {'✓' if 0.5 <= stats['signals_per_month'] <= 10 else '✗'} |",
        f"| 年化收益 | {stats['annualized']*100:.1f}% | > 15% | {'✓' if stats['annualized'] >= 0.15 else '✗'} |",
        f"| 夏普比率 | {stats['sharpe']:.2f} | > 1.0 | {'✓' if stats['sharpe'] >= 1.0 else '✗'} |",
        "",
        f"**综合评级：{stats['passes']}/6 项达标**",
        "",
        "## 交易明细",
        "",
        "| 买入日 | 卖出日 | 买入价 | 卖出价 | 盈亏 |",
        "|--------|--------|--------|--------|------|",
    ]
    for t in sorted(trades, key=lambda x: x["entry_date"]):
        sign = "+" if t["pnl_pct"] >= 0 else ""
        lines.append(
            f"| {t['entry_date'].strftime('%Y-%m-%d')} | "
            f"{t['exit_date'].strftime('%Y-%m-%d')} | "
            f"${t['entry_price']:.2f} | ${t['exit_price']:.2f} | "
            f"{sign}{t['pnl_pct']*100:.1f}% |"
        )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n报告已保存：{report_path}")


if __name__ == "__main__":
    main()
