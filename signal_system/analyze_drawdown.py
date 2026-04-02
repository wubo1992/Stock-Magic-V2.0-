"""
analyze_drawdown.py — 分析最大回撤时刻的持仓情况
"""
import re, yaml, pickle
from datetime import datetime, timezone
from pathlib import Path

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
print(f"美股: {len(us_stocks)} 只")

# ── 加载配置和策略 ────────────────────────────────────────────────────
with open("config.yaml") as f:
    config = yaml.safe_load(f)

from strategies.registry import get_strategy
from backtest.engine import BacktestEngine

strategy_cls = get_strategy("v_weinstein_adx")
strategy_config = config["strategies"]["v_weinstein_adx"]

# ── 运行回测（verbose=False）────────────────────────────────────────────
engine = BacktestEngine(
    config=config,
    strategy_cls=strategy_cls,
    strategy_config=strategy_config,
    symbols=us_stocks,
    start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
    strategy_id="v_weinstein_adx",
)

result = engine.run(verbose=False)

# ── 找到最大回撤点 ────────────────────────────────────────────────────
equity = result.equity_curve  # pandas Series: date -> equity
if equity is None or len(equity) == 0:
    print("No equity curve data")
    exit()

# 计算回撤序列
cumulative_max = equity.cummax()
drawdown = (equity - cumulative_max) / cumulative_max
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()

print(f"\n最大回撤: {max_dd*100:.1f}% 发生在 {max_dd_date.date()}")
print(f"当日净值: {equity.loc[max_dd_date]:.4f}")
print(f"历史最高净值: {cumulative_max.loc[max_dd_date]:.4f}")

# ── 找到最大回撤前后的已平仓交易 ─────────────────────────────────────
closed = result.closed_trades
print(f"\n截止到 {max_dd_date.date()}，已平仓交易: {len(closed)} 笔")

# ── 重建逐日持仓（open_trades 在每日迭代中产生，需要重新跑一次抓持仓）─────
# engine 里 open_trades 是内部变量，需要用 instrumented 方式重跑
# 最简单的方法：修改策略，记录每天的 open_trades
# 但这里我们没有这个数据，所以分析已平仓交易中在最大回撤点附近的交易

# 找出在最大回撤点之前买入、之后卖出的交易（跨越大回撤期）
print("\n跨越最大回撤期的交易（在回撤前开仓，回撤期间或之后平仓）：")
print(f"{'股票':<6} {'买入日':<12} {'卖出日':<12} {'买入价':>8} {'卖出价':>8} {'盈亏':>8}")

crossing_trades = []
for t in closed:
    entry_date = t.entry_date
    exit_date = t.exit_date
    if entry_date <= max_dd_date <= exit_date:
        pnl_pct = (t.exit_price - t.entry_price) / t.entry_price * 100
        crossing_trades.append(t)
        print(f"{t.symbol:<6} {str(entry_date.date()):<12} {str(exit_date.date()):<12} ${t.entry_price:>7.2f} ${t.exit_price:>7.2f} {pnl_pct:>+7.1f}%")

print(f"\n共 {len(crossing_trades)} 笔跨越最大回撤点的交易")

# ── 分析最大回撤期间（回撤开始到最低点）的市场环境 ──────────────────
# 找到回撤开始点（、回撤前净值创新高的日期）
peak_date = cumulative_max.loc[:max_dd_date].idxmax()
print(f"\n回撤起始日: {peak_date.date()} (净值 {equity.loc[peak_date]:.4f})")
print(f"回撤最低日: {max_dd_date.date()} (净值 {equity.loc[max_dd_date]:.4f})")
print(f"回撤持续: {(max_dd_date - peak_date).days} 天")

# 保存结果供后续分析
with open("/tmp/drawdown_analysis.pkl", "wb") as f:
    pickle.dump({
        "max_dd": max_dd,
        "max_dd_date": max_dd_date,
        "peak_date": peak_date,
        "equity": equity,
        "drawdown": drawdown,
        "closed_trades": closed,
    }, f)
print("\n数据已保存到 /tmp/drawdown_analysis.pkl")
