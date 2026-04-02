"""
backtest_fixed_dollar.py — 固定金额 ($1000) 仓位回测

每次买入固定投入 $1000，利润再投资，模拟真实账户交易。
"""
import re, yaml, sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, '.')

# ── 读取美股 ──────────────────────────────────────────────────────────
us_stocks_set = set()
with open("UNIVERSE.md") as f:
    content = f.read()
for section in re.split(r"^## ", content, flags=re.MULTILINE):
    lines = section.split("\n")
    title = lines[0].strip()
    in_us = title.startswith("板块 S：") or title.startswith("板块 N：")
    if in_us:
        for line in lines:
            if line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and re.match(r"^[A-Z0-9]{1,6}(\.[A-Z0-9]{1,5})?$", parts[1]):
                    us_stocks_set.add(parts[1])
us_stocks = sorted(us_stocks_set)
print(f"[股票池] 美股共 {len(us_stocks)} 只")

# ── 加载配置和策略 ────────────────────────────────────────────────────
with open("config.yaml") as f:
    config = yaml.safe_load(f)

from strategies.registry import get_strategy
from backtest.engine import BacktestEngine, Trade, _get_close

strategy_cls = get_strategy("v_weinstein_adx")
strategy_config = config["strategies"]["v_weinstein_adx"]

# ── 固定金额参数 ────────────────────────────────────────────────────
INITIAL_CAPITAL = 10_000.0   # 初始本金 $10,000
POSITION_SIZE = 1_000.0      # 每笔投入 $1,000

# ── 运行回测 ──────────────────────────────────────────────────────────
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

print(f"[回测] 共 {len(result.trades)} 笔交易")

# ── 用固定金额模型重建净值曲线 ────────────────────────────────────────
market_data = engine.market_data if hasattr(engine, 'market_data') else None

def build_fixed_dollar_equity(trades, market_data, trading_days):
    """
    固定金额 ($1000) 仓位模型：
    - 初始本金 $10,000
    - 每笔交易固定投入 $1,000
    - 利润再投资，亏算减少可用资金
    - 每日组合净值 = 可用资金 + 所有持仓当前市值
    """
    # 预处理
    sliced_data = {}
    for sym, df in market_data.items():
        idx = df.index
        if idx.tzinfo is None:
            df = df.copy()
            df.index = idx.tz_localize("UTC")
        sliced_data[sym] = df

    # 净值序列
    equity = pd.Series(index=pd.DatetimeIndex(trading_days), dtype=float)
    cash = INITIAL_CAPITAL
    active_positions = {}  # symbol -> {shares, entry_price, entry_date}

    for i, date in enumerate(trading_days):
        dt = date.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # ── 1. 处理当日新买入（从 cash 扣除 $1000）────────────────
        for trade in trades:
            entry = _ensure_utc(trade.entry_date)
            if entry.date() == dt.date():
                if trade.symbol not in active_positions:
                    shares = POSITION_SIZE / trade.entry_price
                    active_positions[trade.symbol] = {
                        'shares': shares,
                        'entry_price': trade.entry_price,
                        'cost': POSITION_SIZE,
                    }
                    cash -= POSITION_SIZE

        # ── 2. 处理当日卖出（平仓后资金回现金）──────────────────
        for trade in trades:
            exit_dt = _ensure_utc(trade.exit_date) if trade.exit_date else None
            if exit_dt and exit_dt.date() == dt.date() and trade.symbol in active_positions:
                pos = active_positions[trade.symbol]
                pnl = (trade.exit_price - trade.entry_price) * pos['shares']
                cash += POSITION_SIZE + pnl  # 拿回本金 + 盈亏
                del active_positions[trade.symbol]

        # ── 3. 计算当日组合总值 ────────────────────────────────
        pos_value = 0.0
        for sym, pos in active_positions.items():
            df = sliced_data.get(sym)
            if df is not None:
                mask = df.index <= dt
                if mask.sum() >= 1:
                    current_price = float(df["close"][mask].iloc[-1])
                    pos_value += current_price * pos['shares']

        equity.iloc[i] = cash + pos_value

    return equity

# ── 计算绩效指标 ────────────────────────────────────────────────────
equity = build_fixed_dollar_equity(result.trades, engine.market_data, engine._trading_days)
trading_days = engine._trading_days

# 最大回撤
cumulative_max = equity.cummax()
drawdown = (equity - cumulative_max) / cumulative_max
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()

# 年化收益
total_return = equity.iloc[-1] / equity.iloc[0] - 1
years = (trading_days[-1] - trading_days[0]).days / 365.25
annualized = (1 + total_return) ** (1 / years) - 1

# 夏普比率（无风险利率 4%）
daily_returns = equity.pct_change().dropna()
sharpe = (daily_returns.mean() * 252 - 0.04) / (daily_returns.std() * np.sqrt(252))

# 胜率
wins = sum(1 for t in result.trades if t.pnl_pct > 0)
losses = sum(1 for t in result.trades if t.pnl_pct <= 0)
win_rate = wins / len(result.trades) if result.trades else 0

# 盈亏比
avg_win = np.mean([t.pnl_pct for t in result.trades if t.pnl_pct > 0]) if wins else 0
avg_loss = abs(np.mean([t.pnl_pct for t in result.trades if t.pnl_pct <= 0])) if losses else 1
profit_loss_ratio = (avg_win * wins) / (avg_loss * losses) if (avg_loss * losses) > 0 else 0

# 每月信号数
monthly = defaultdict(int)
for t in result.trades:
    monthly[t.entry_date.strftime("%Y-%m")] += 1
signals_per_month = np.mean(list(monthly.values()))

print(f"""
{'='*60}
  固定金额回测报告（$1000/笔，初始本金 ${INITIAL_CAPITAL:,.0f}）
  测试区间：{trading_days[0].date()} ~ {trading_days[-1].date()}
{'='*60}
  初始本金              ${INITIAL_CAPITAL:,.0f}
  最终净值              ${equity.iloc[-1]:,.2f}
  总收益                {total_return*100:+.1f}%
  年化收益              {annualized*100:+.1f}%
  最大回撤              {max_dd*100:.1f}%（{max_dd_date.date()}）
  夏普比率              {sharpe:.2f}
  胜率                  {win_rate*100:.1f}%（{wins}胜/{losses}负）
  盈亏比                {profit_loss_ratio:.2f}
  每月信号数            {signals_per_month:.1f}
  总交易笔数            {len(result.trades)}
{'='*60}
""")

# ── 按月统计 ──────────────────────────────────────────────────────────
print("各月净值：")
print(f"{'月份':<10} {'净值':>12} {'月收益':>8}")
print("-" * 35)
prev_month = None
for i, date in enumerate(trading_days):
    month = date.strftime("%Y-%m")
    if month != prev_month:
        print(f"{month:<10} ${equity.iloc[i]:>12,.2f}  {'—':>8}")
        prev_month = month

def _ensure_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
