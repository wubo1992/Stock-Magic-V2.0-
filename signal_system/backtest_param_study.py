"""
backtest_param_study.py — 参数研究脚本（快速版）
策略：先用 2024-2026 OOS 数据研究参数，全量验证用最优配置跑 2020-2026
"""
import re, yaml, json, sys
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

with open("config.yaml") as f:
    config = yaml.safe_load(f)

from strategies.registry import get_strategy
from data.fetcher import fetch
from backtest.engine import Trade, _ensure_utc, _get_close
from events import EventQueue

INITIAL_CAPITAL = 50_000.0
POSITION_SIZE   = 1_500.0

# ── 测试区间 ──────────────────────────────────────────────────────────
# OOS 研究区间（2024-2026，短周期快速迭代）
OOS_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
OOS_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)
# 全量验证区间
FULL_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
FULL_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)

# ── 基线参数 ────────────────────────────────────────────────────────
BASE_CFG = {
    'sma_long': 150, 'trend_lookback': 30, 'pivot_lookback': 30,
    'min_breakout_pct': 0.005, 'volume_mult': 1.5,
    'rsi_max': 85, 'adx_threshold': 35, 'market_filter': False,
    'spy_bear_stop_loss': 0.05, 'stop_loss_pct': 0.07,
    'trailing_stop_pct': 0.18, 'time_stop_days': 30, 'time_stop_min_gain': 0.05,
}

# ── 牛市调整参数 ────────────────────────────────────────────────────
ADJUSTED_CFG = {
    **BASE_CFG,
    'trend_lookback': 15, 'adx_threshold': 25, 'rsi_max': 90,
    'trailing_stop_pct': 0.25, 'time_stop_days': 45, 'volume_mult': 1.2,
}

# ── 控制变量测试表 ────────────────────────────────────────────────────
VARIABLE_TESTS = {
    'trend_lookback':   [10, 15, 20, 25, 30, 40],
    'adx_threshold':    [20, 25, 30, 35],
    'rsi_max':          [80, 85, 90, 95, 100],
    'trailing_stop_pct':[0.12, 0.15, 0.18, 0.22, 0.25, 0.30],
    'time_stop_days':   [20, 30, 45, 60, 90],
    'volume_mult':      [1.0, 1.2, 1.5, 2.0],
}


class QuickBacktestEngine:
    """精简回测引擎（去掉冗余日志，专为参数研究设计）"""

    WARMUP_DAYS = 300

    def __init__(self, strategy_cfg, symbols, start_date, end_date):
        self.strategy_cfg = strategy_cfg
        self.symbols = symbols
        self.start_date = _ensure_utc(start_date)
        self.end_date = _ensure_utc(end_date)

    def run(self):
        total_days = (self.end_date - self.start_date).days + self.WARMUP_DAYS
        market_data = fetch(self.symbols, history_days=total_days, end_date=self.end_date)
        if not market_data:
            raise RuntimeError("无法获取数据")

        for benchmark, syms in [("SPY", ["SPY"]), ("ASHR", ["ASHR"]), ("EWT", ["EWT"])]:
            if benchmark not in market_data:
                data = fetch(syms, history_days=total_days, end_date=self.end_date)
                if data and benchmark in data:
                    market_data[benchmark] = data[benchmark]

        ref_df = next(iter(market_data.values()))
        ref_index = ref_df.index
        if ref_index.tzinfo is None:
            ref_index = ref_index.tz_localize("UTC")

        trading_days = ref_index[
            (ref_index >= self.start_date) & (ref_index <= self.end_date)
        ]

        from strategies.v_weinstein_adx.weinstein_adx_strategy import WeinsteinADXStrategy
        strategy = WeinsteinADXStrategy(self.strategy_cfg, market_data)
        queue = EventQueue()

        open_trades: dict[str, Trade] = {}
        all_trades: list[Trade] = []
        cash = float(INITIAL_CAPITAL)
        active_positions: dict[str, dict] = {}
        daily_records: list[dict] = []

        sliced_data: dict[str, pd.DataFrame] = {}
        for sym, df in market_data.items():
            idx = df.index
            if idx.tzinfo is None:
                df = df.copy()
                df.index = idx.tz_localize("UTC")
            sliced_data[sym] = df

        for date in trading_days:
            dt = date.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            pos_value = 0.0
            for sym, pos in active_positions.items():
                df = sliced_data.get(sym)
                if df is not None:
                    mask = df.index <= dt
                    if mask.sum() >= 1:
                        pos_value += float(df["close"][mask].iloc[-1]) * pos['shares']
            daily_records.append({'date': dt, 'cash': cash, 'equity': cash + pos_value})

            signals = strategy.run_date(dt, queue)
            for sig in signals:
                symbol, direction = sig.symbol, sig.data["direction"]
                if direction == "buy" and symbol not in open_trades:
                    entry_price = _get_close(market_data, symbol, dt, strategy)
                    if entry_price is None:
                        continue
                    while cash < POSITION_SIZE and active_positions:
                        def sort_key(item):
                            sym_, pos = item
                            cv = float(sliced_data[sym_]["close"].loc[sliced_data[sym_].index <= dt].iloc[-1]) * pos['shares']
                            pnl_pct = (cv - pos['cost']) / pos['cost']
                            days_held = (dt.date() - _ensure_utc(pos['entry_date']).date()).days
                            return (pnl_pct, days_held)
                        worst = min(active_positions.items(), key=sort_key)[0]
                        pos = active_positions[worst]
                        ep = float(sliced_data[worst]["close"].loc[sliced_data[worst].index <= dt].iloc[-1])
                        cash += pos['cost'] + (ep - pos['entry_price']) * pos['shares']
                        if worst in open_trades:
                            t = open_trades.pop(worst)
                            t.close(dt, ep, "rebalance")
                        del active_positions[worst]
                    if cash < POSITION_SIZE:
                        continue
                    shares = POSITION_SIZE / entry_price
                    active_positions[symbol] = {'shares': shares, 'cost': POSITION_SIZE, 'entry_price': entry_price, 'entry_date': dt}
                    cash -= POSITION_SIZE
                    trade = Trade(symbol=symbol, entry_date=dt, entry_price=entry_price, entry_reason=sig.data.get("reason",""))
                    open_trades[symbol] = trade
                    all_trades.append(trade)
                elif direction == "sell" and symbol in open_trades:
                    exit_price = _get_close(market_data, symbol, dt, strategy)
                    if exit_price is None:
                        continue
                    trade = open_trades.pop(symbol)
                    trade.close(dt, exit_price, sig.data.get("reason",""))
                    if symbol in active_positions:
                        pos = active_positions.pop(symbol)
                        cash += POSITION_SIZE + (exit_price - trade.entry_price) * pos['shares']

        # 强制平仓
        for symbol, trade in list(open_trades.items()):
            ep = _get_close(market_data, symbol, self.end_date, strategy)
            if ep:
                trade.close(self.end_date, ep, "end")
                if symbol in active_positions:
                    pos = active_positions.pop(symbol)
                    cash += POSITION_SIZE + (ep - trade.entry_price) * pos['shares']

        if daily_records:
            daily_records[-1] = {'date': daily_records[-1]['date'], 'cash': cash, 'equity': cash}

        equity = pd.Series([r['equity'] for r in daily_records])
        closed = [t for t in all_trades if t.is_closed]

        return self._metrics(closed, equity)

    def _metrics(self, closed, equity):
        if not closed or len(equity) == 0:
            return {}
        tr = float(equity.iloc[-1] / equity.iloc[0] - 1)
        yrs = (self.end_date - self.start_date).days / 365.25
        ann = (1 + tr) ** (1 / yrs) - 1 if yrs > 0 else 0
        wins = [t for t in closed if t.pnl_pct > 0]
        losses = [t for t in closed if t.pnl_pct <= 0]
        wr = len(wins) / len(closed)
        avg_w = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_l = abs(np.mean([t.pnl_pct for t in losses])) if losses else 1
        plr = (avg_w * len(wins)) / (avg_l * len(losses)) if losses else 0
        cmax = equity.cummax()
        dd = (equity - cmax) / cmax
        mdd = abs(dd.min())
        dr = equity.pct_change().dropna()
        sharpe = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
        monthly = defaultdict(int)
        for t in closed:
            monthly[t.entry_date.strftime("%Y-%m")[:7]] += 1
        spm = np.mean(list(monthly.values())) if monthly else 0

        return {
            'tr': tr * 100, 'ann': ann * 100, 'mdd': mdd * 100,
            'sharpe': sharpe, 'wr': wr * 100, 'plr': plr,
            'spm': spm, 'n': len(closed),
        }


def show(name, m):
    if not m:
        print(f"  {name:<30} 无数据")
        return
    print(f"  {name:<30} 收益:{m['tr']:>+6.1f}%  年化:{m['ann']:>+6.1f}%  "
          f"回撤:{m['mdd']:>5.1f}%  夏普:{m['sharpe']:>5.2f}  "
          f"胜率:{m['wr']:>5.1f}%  盈亏比:{m['plr']:>5.2f}  月均:{m['spm']:>4.1f}信号  n={m['n']}")


# ═══════════════════════════════════════════════════════════════════════
# Step 1: OOS 基线 vs 调整后
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  【Step 1】2024-2026 OOS 快速研究")
print("═"*72)

print("\n  基线参数 (v_weinstein_adx):")
m_base = QuickBacktestEngine(BASE_CFG, us_stocks, OOS_START, OOS_END).run()
show("  基线", m_base)

print("\n  牛市调整参数 (trend_lookback=15, ADX>25, RSI<90, 追踪25%, 时间45d, 量1.2x):")
m_adj = QuickBacktestEngine(ADJUSTED_CFG, us_stocks, OOS_START, OOS_END).run()
show("  调整后", m_adj)

# ═══════════════════════════════════════════════════════════════════════
# Step 2: 控制变量法（逐参数测试）
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  【Step 2】控制变量法 — OOS 2024-2026")
print("═"*72)

best_by_var = {}

for var, values in VARIABLE_TESTS.items():
    print(f"\n  ▶ {var}")
    best_val, best_m = None, None
    for v in values:
        cfg = {**BASE_CFG, var: v}
        m = QuickBacktestEngine(cfg, us_stocks, OOS_START, OOS_END).run()
        label = f"{var}={v}"
        marker = " ◀ 基线" if v == BASE_CFG[var] else ""
        show(f"    {label}{marker}", m)
        if m and (best_m is None or m['ann'] > best_m['ann']):
            best_val, best_m = v, m
    if best_val is not None:
        print(f"    → 最优值: {best_val} (年化 {best_m['ann']:+.1f}%)")
        best_by_var[var] = best_val

# ═══════════════════════════════════════════════════════════════════════
# Step 3: 最优配置汇总
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  【Step 3】各参数最优值汇总")
print("═"*72)

optimal_cfg = {**BASE_CFG}
for var, val in best_by_var.items():
    optimal_cfg[var] = val
    print(f"  {var:<22} 基线={BASE_CFG[var]:<8} → 最优={val}")

# ═══════════════════════════════════════════════════════════════════════
# Step 4: 全量 2020-2026 验证（只跑最优配置 + 对比）
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  【Step 4】全量验证 2020-2026 — 最优配置 vs 基线")
print("═"*72)

print("\n  [基线] 2020-2026:")
m_full_base = QuickBacktestEngine(BASE_CFG, us_stocks, FULL_START, FULL_END).run()
show("  基线", m_full_base)

print("\n  [最优配置] 2020-2026:")
m_full_opt = QuickBacktestEngine(optimal_cfg, us_stocks, FULL_START, FULL_END).run()
show("  最优配置", m_full_opt)

print("\n  [牛市调整] 2020-2026:")
m_full_adj = QuickBacktestEngine(ADJUSTED_CFG, us_stocks, FULL_START, FULL_END).run()
show("  牛市调整", m_full_adj)

# ── 保存结果 ──────────────────────────────────────────────────────────
summary = {
    'baseline': m_full_base,
    'adjusted': m_full_adj,
    'optimal': m_full_opt,
    'best_by_var': best_by_var,
}
with open('/tmp/param_study_results.json', 'w') as f:
    json.dump(summary, f, indent=2, default=str)

print("\n  结果已保存至 /tmp/param_study_results.json")
