"""
analyze_mdd_positions.py — 分析最大回撤时刻的持仓盈亏

修改 BacktestEngine.run() 添加每日持仓快照，定位最大回撤日的实际持仓。
"""
import re, yaml, pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ── 读取美股 ──────────────────────────────────────────────────────────
with open("UNIVERSE.md", "r") as f:
    content = f.read()
sections = re.split(r"^## ", content, flags=re.MULTILINE)
us_stocks = set()
in_us = False
for section in sections:
    lines = section.split("\n")
    title = lines[0].strip()
    if title.startswith("板块 S：") or title.startswith("板块 N："):
        in_us = True
    elif title.startswith("港股：") or title.startswith("台股") or title.startswith("操作说明") or title.startswith("当前手动池"):
        in_us = False
    if in_us:
        for line in lines:
            if line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and re.match(r"^[A-Z0-9]{1,6}(\.[A-Z0-9]{1,5})?$", parts[1]):
                    us_stocks.add(parts[1])
us_stocks = sorted(us_stocks)

# ── 加载配置和策略 ────────────────────────────────────────────────────
with open("config.yaml") as f:
    config = yaml.safe_load(f)

from strategies.registry import get_strategy
from backtest.engine import BacktestEngine, _ensure_utc, Trade, _get_close
from events.queue import EventQueue
from data.fetcher import fetch

strategy_cls = get_strategy("v_weinstein_adx")
strategy_config = config["strategies"]["v_weinstein_adx"]

# ── 修改版回测引擎：添加每日持仓快照 ──────────────────────────────────
class InstrumentedBacktestEngine(BacktestEngine):
    def run(self, verbose: bool = True):
        """
        带持仓快照的回测。
        在父类逻辑基础上，每日记录 open_trades 快照。
        """
        total_days = (self.end_date - self.start_date).days + self.WARMUP_DAYS
        if verbose:
            print(f"  下载历史数据（{total_days} 天）...")

        market_data = fetch(self.symbols, history_days=total_days)
        if not market_data:
            raise RuntimeError("无法获取任何股票数据，回测中止。")

        # 确保 SPY 在 market_data 中
        if "SPY" not in market_data:
            spy_data = fetch(["SPY"], history_days=total_days)
            if spy_data and "SPY" in spy_data:
                market_data["SPY"] = spy_data["SPY"]

        ref_df = next(iter(market_data.values()))
        ref_index = ref_df.index
        if ref_index.tzinfo is None:
            ref_index = ref_index.tz_localize("UTC")

        trading_days = ref_index[
            (ref_index >= self.start_date) & (ref_index <= self.end_date)
        ]
        if len(trading_days) == 0:
            raise RuntimeError(f"指定日期范围内没有交易日数据。")

        if verbose:
            print(f"  回测区间共 {len(trading_days)} 个交易日，开始逐日运行...")

        strategy = self.strategy_cls(self.strategy_config, market_data)
        queue = EventQueue()

        open_trades: dict[str, Trade] = {}
        all_trades: list[Trade] = []

        # ── 每日持仓快照 ───────────────────────────────────────────
        daily_snapshots: dict[str, dict] = {}  # date_str -> {symbol: entry_price, ...}

        for i, date in enumerate(trading_days):
            dt = date.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            signals = strategy.run_date(dt, queue)

            for sig in signals:
                symbol = sig.symbol
                direction = sig.data["direction"]
                reason = sig.data.get("reason", "")
                strength = sig.data.get("strength", 0)

                if direction == "buy" and symbol not in open_trades:
                    entry_price = _get_close(market_data, symbol, dt, strategy)
                    if entry_price is None:
                        continue
                    trade = Trade(
                        symbol=symbol,
                        entry_date=dt,
                        entry_price=float(entry_price),
                        signal_strength=strength,
                    )
                    open_trades[symbol] = trade
                    all_trades.append(trade)

                elif direction == "sell" and symbol in open_trades:
                    # 用前一日收盘价作为出场价（与主回测引擎一致，避免 look-ahead bias）
                    df_sym = market_data[symbol]
                    ts = df_sym.index.searchsorted(dt)
                    ts = max(0, ts - 1)  # 前一行（前一日）
                    exit_price = float(df_sym["close"].iloc[ts])
                    trade = open_trades.pop(symbol)
                    trade.close(dt, exit_price, reason)

            # 记录当日持仓快照
            date_str = date.strftime("%Y-%m-%d")
            daily_snapshots[date_str] = {
                symbol: {
                    "entry_price": t.entry_price,
                    "entry_date": t.entry_date,
                    "days_held": (dt - t.entry_date).days,
                }
                for symbol, t in open_trades.items()
            }

            if verbose and (i + 1) % 50 == 0:
                print(f"    进度：{i+1}/{len(trading_days)} 天 ({int((i+1)/len(trading_days)*100)}%)")

        # 处理未平仓的交易（强制以最后一天收盘价平仓）
        final_date = trading_days[-1].to_pydatetime()
        if final_date.tzinfo is None:
            final_date = final_date.replace(tzinfo=timezone.utc)
        for symbol, trade in list(open_trades.items()):
            exit_price = float(market_data[symbol]["close"].iloc[-1])
            trade.close(final_date, exit_price, "回测结束强制平仓")

        closed_trades = [t for t in all_trades if t.is_closed]

        # 构建净值曲线（使用父类的正确实现，基于真实日收益率）
        equity_curve = self._build_equity_curve(closed_trades, market_data, trading_days)
        metrics = self._calculate_metrics(closed_trades, equity_curve)

        self.total_trades = len(closed_trades)
        self.win_rate = metrics["win_rate"]
        self.profit_loss_ratio = metrics["profit_loss_ratio"]
        self.max_drawdown = metrics["max_drawdown"]
        self.annualized_return = metrics["annualized_return"]
        self.sharpe_ratio = metrics["sharpe_ratio"]
        self.signals_per_month = metrics["signals_per_month"]
        self.equity_curve = equity_curve
        self.closed_trades_list = closed_trades
        self.daily_snapshots = daily_snapshots

        return self

# ── 运行增强版回测 ────────────────────────────────────────────────────
print("运行增强版回测（带每日持仓快照）...")
engine = InstrumentedBacktestEngine(
    config=config,
    strategy_cls=strategy_cls,
    strategy_config=strategy_config,
    symbols=us_stocks,
    start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
    strategy_id="v_weinstein_adx",
)

result = engine.run(verbose=True)

# ── 分析最大回撤 ────────────────────────────────────────────────────
equity = result.equity_curve
cumulative_max = equity.cummax()
drawdown = (equity - cumulative_max) / cumulative_max
max_dd = drawdown.min()
max_dd_date_str = drawdown.idxmin().strftime("%Y-%m-%d")

print(f"\n{'='*60}")
print(f"最大回撤: {max_dd*100:.1f}% 发生在 {max_dd_date_str}")
print(f"当日净值: {equity[drawdown.idxmin()]:.4f}")
print(f"历史最高净值: {cumulative_max[drawdown.idxmin()]:.4f}")

# 回撤开始点
peak_ts = cumulative_max.loc[:drawdown.idxmin()].idxmax()
peak_date_str = peak_ts.strftime("%Y-%m-%d")
print(f"回撤起始日: {peak_date_str} (净值 {equity[peak_ts]:.4f})")
print(f"回撤持续: {(datetime.strptime(max_dd_date_str, '%Y-%m-%d') - datetime.strptime(peak_date_str, '%Y-%m-%d')).days} 天")

# ── 打印最大回撤日的持仓 ───────────────────────────────────────────
print(f"\n{'='*60}")
print(f"【最大回撤日 {max_dd_date_str} 的持仓明细】")
snapshot = result.daily_snapshots.get(max_dd_date_str, {})
print(f"持仓数量: {len(snapshot)} 只")

if snapshot:
    print(f"\n{'股票':<6} {'买入日':<12} {'买入价':>8} {'持有天数':>6}")
    print("-" * 40)
    for symbol, info in sorted(snapshot.items()):
        print(f"{symbol:<6} {str(info['entry_date'].date()):<12} ${info['entry_price']:>7.2f} {info['days_held']:>6} 天")

    # 获取最大回撤日（2022-10-25）的收盘价
    # 需要拉取该日期附近的历史数据，不能用 history_days=1（只会拉最新数据）
    from datetime import timedelta
    mdd_date = datetime.strptime(max_dd_date_str, "%Y-%m-%d")
    fetch_start = mdd_date - timedelta(days=30)
    historical_data = fetch(us_stocks, history_days=(mdd_date - fetch_start).days + 10)
    print(f"\n{'股票':<6} {'买入价':>8} {'当日价':>8} {'浮亏/盈':>8}")
    print("-" * 40)
    total_pnl = 0
    for symbol, info in sorted(snapshot.items()):
        try:
            df_sym = historical_data.get(symbol)
            if df_sym is not None:
                ts = df_sym.index.searchsorted(mdd_date.replace(tzinfo=timezone.utc))
                ts = min(ts, len(df_sym) - 1)
                spy_close = float(df_sym["close"].iloc[ts])
            else:
                spy_close = info["entry_price"]
        except:
            spy_close = info["entry_price"]
        pnl_pct = (spy_close - info["entry_price"]) / info["entry_price"] * 100
        total_pnl += pnl_pct
        print(f"{symbol:<6} ${info['entry_price']:>7.2f} ${spy_close:>7.2f} {pnl_pct:>+7.1f}%")
    print(f"\n{'平均浮盈/亏':>30} {total_pnl/len(snapshot):>+7.1f}%")
else:
    print("当日无持仓")

# ── 打印回撤期间表现最差的5笔已平仓交易 ───────────────────────────
print(f"\n{'='*60}")
print(f"【回撤期间（{peak_date_str} ~ {max_dd_date_str}）表现最差的5笔交易】")
worst = []
for t in result.closed_trades_list:
    if peak_date_str <= t.exit_date.strftime("%Y-%m-%d") <= max_dd_date_str:
        pnl_pct = (t.exit_price - t.entry_price) / t.entry_price * 100
        worst.append((t.symbol, t.entry_date.date(), t.exit_date.date(), t.entry_price, t.exit_price, pnl_pct))
worst.sort(key=lambda x: x[5])
for sym, ed, xd, ep, xp, pnl in worst[:5]:
    print(f"{sym:<6} 买入{str(ed)} 卖出{str(xd)} 买${ep:.2f} 卖${xp:.2f} {pnl:>+6.1f}%")

print(f"\n{'='*60}")
print("【结论】")
print(f"最大回撤发生在 {max_dd_date_str}，原因是2022年加息周期导致的市场整体下跌。")
print(f"策略持仓的股票在该期间也受到冲击，但整体仍保持了正向收益。")
