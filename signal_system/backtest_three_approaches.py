"""
backtest_three_approaches.py — 三个改进方案对照实验（优化版：预计算ATR）

方案A: 三档位仓位（强$3000/中$2000/弱$1000）
方案B: ATR动态止损（强势股2ATR，弱势股1ATR）
方案C: 部分复利+三档仓位（每盈利20%，仓位增加$500，上限$4000）
基准: 固定$2000仓位

两个回测周期:
  - 全量: 2016-01-01 至 2026-03-27
  - OOS:  2024-01-01 至 2026-03-27
"""
import sys, yaml, pickle, matplotlib, json
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import re

sys.path.insert(0, '.')

# ── 加载股票池 ────────────────────────────────────────────────────────
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

with open("config.yaml") as f:
    config = yaml.safe_load(f)

from data.fetcher import fetch
from backtest.engine import Trade, _ensure_utc, _get_close
from events import EventQueue
from strategies.registry import get_strategy

INITIAL_CAPITAL = 50_000.0
POSITION_SIZE   = 2_000.0
START_FULL = datetime(2016, 1, 1, tzinfo=timezone.utc)
END_FULL   = datetime(2026, 3, 27, tzinfo=timezone.utc)
START_OOS  = datetime(2024, 1, 1, tzinfo=timezone.utc)
END_OOS    = END_FULL

# ── 加载数据 ────────────────────────────────────────────────────────
total_days = (END_FULL - START_FULL).days + 300
print("[数据] 加载股票池...")
md = fetch(us_stocks, history_days=total_days, end_date=END_FULL)
if not md: raise RuntimeError("no data")
for bm, syms in [("SPY",["SPY"]),("ASHR",["ASHR"]),("EWT",["EWT"])]:
    if bm not in md:
        d = fetch(syms, history_days=total_days, end_date=END_FULL)
        if d and bm in d: md[bm] = d[bm]

ref = next(iter(md.values())).index
if ref.tzinfo is None: ref = ref.tz_localize("UTC")

# 时区处理
sliced = {}
for sym, df in md.items():
    idx = df.index
    if idx.tzinfo is None:
        df = df.copy()
        df.index = idx.tz_localize("UTC")
    sliced[sym] = df

# ── 预计算所有股票的ATR(14)时间序列 ──────────────────────────────────
print("[数据] 预计算ATR(14)...")
atr_cache = {}
for sym, df in sliced.items():
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        h_l = high[i] - low[i]
        h_c = abs(high[i] - close[i-1])
        l_c = abs(low[i] - close[i-1])
        tr[i] = max(h_l, h_c, l_c)
    # Wilder平滑 ATR
    period = 14
    atr = np.zeros(n)
    atr[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        atr[i] = alpha * tr[i] + (1 - alpha) * atr[i-1]
    # 转为Series，索引与df一致
    atr_series = pd.Series(atr, index=df.index)
    atr_cache[sym] = atr_series
print(f"[数据] ATR预计算完成: {len(atr_cache)} 只股票")

# SPY
spy_df = pickle.load(open(Path("data/cache/SPY.pkl"), 'rb'))
spy_df.index = spy_df.index.tz_localize(None)
spy_mask = (spy_df.index >= START_FULL.replace(tzinfo=None)) & (spy_df.index <= END_FULL.replace(tzinfo=None))
spy_prices = spy_df['close'][spy_mask]
spy_equity = spy_prices / spy_prices.iloc[0]
spy_equity.index = spy_equity.index.tz_localize(None)

# ── 辅助函数 ────────────────────────────────────────────────────────
def get_atr(sym, date, lookback=14):
    """获取指定日期的ATR值（当日或前一天）"""
    atr_series = atr_cache.get(sym)
    if atr_series is None:
        return None
    idx = atr_series.index
    if idx.tzinfo is not None:
        if hasattr(date, 'tzinfo') and date.tzinfo is None:
            date = date.replace(tzinfo=idx.tzinfo)
        elif hasattr(date, 'tzinfo') and date.tzinfo is not None and idx.tzinfo is None:
            date = date.tz_localize(None)
    # searchsorted
    pos = idx.searchsorted(date)
    if pos >= len(atr_series):
        pos = len(atr_series) - 1
    if pos < 0:
        pos = 0
    return float(atr_series.iloc[pos])

def parse_signal_strength(sig):
    """从信号reason中解析ADX和量能，判断信号强度"""
    reason = sig.data.get("reason", "")
    adx_match = re.search(r'\[ADX\]\s*([\d.]+)', reason)
    adx_val = float(adx_match.group(1)) if adx_match else 0
    vol_match = re.search(r'\[量能\]\s*([\d.]+)x', reason)
    vol_ratio = float(vol_match.group(1)) if vol_match else 0
    return adx_val, vol_ratio

def run_backtest(cfg, days, sliced, mode="baseline",
                 pos_size_base=2000,
                 compound_step=0, compound_cap=4000,
                 atr_mode=False):
    """
    mode: baseline | tiered_pos | atr_stop | compound_tiered
    """
    strategy_cls = get_strategy('v_weinstein_adx')
    strategy = strategy_cls(cfg, md)
    queue = EventQueue()

    open_t, all_t = {}, []
    cash = float(INITIAL_CAPITAL)
    active = {}
    records = []
    rebal_count = 0

    current_pos_size = float(pos_size_base)
    high_water_mark = float(INITIAL_CAPITAL)
    trailing_state = {}

    for date in days:
        dt = date.to_pydatetime()
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

        # ── 方案C: 每盈利compound_step就增加仓位 ──
        if compound_step > 0:
            pv = 0.0
            for sym, pos in list(active.items()):
                df = sliced.get(sym)
                if df is not None:
                    mask = df.index <= dt
                    if mask.sum() >= 1:
                        cur_price = float(df["close"][mask].iloc[-1])
                        pv += cur_price * pos['shares']
            equity_now = cash + pv
            if equity_now > high_water_mark * (1 + compound_step):
                increment = pos_size_base * 0.25
                new_size = min(current_pos_size + increment, compound_cap)
                if new_size > current_pos_size:
                    current_pos_size = new_size
                    high_water_mark = equity_now

        # ── 每日持仓市值 ──
        pv = 0.0
        for sym, pos in list(active.items()):
            df = sliced.get(sym)
            if df is not None:
                mask = df.index <= dt
                if mask.sum() >= 1:
                    cur_price = float(df["close"][mask].iloc[-1])
                    pv += cur_price * pos['shares']
        equity = cash + pv
        util = pv / equity * 100 if equity > 0 else 0
        records.append({'date': dt, 'cash': cash, 'pos_value': pv, 'equity': equity, 'num_pos': len(active), 'util': util})

        for sig in strategy.run_date(dt, queue):
            sym, dir_ = sig.symbol, sig.data["direction"]

            if dir_ == "buy" and sym not in open_t and sym not in active:
                ep = _get_close(md, sym, dt, strategy)
                if not ep: continue

                if mode == "tiered_pos" or mode == "compound_tiered":
                    adx_val, vol_ratio = parse_signal_strength(sig)
                    if adx_val > 35 and vol_ratio >= 2.5:
                        pos_size = pos_size_base * 1.5
                    elif adx_val > 30:
                        pos_size = pos_size_base
                    else:
                        pos_size = pos_size_base * 0.5
                else:
                    pos_size = pos_size_base

                pos_size = min(pos_size, current_pos_size if compound_step > 0 else pos_size)

                if cash < pos_size: continue
                shares = pos_size / ep

                if atr_mode:
                    atr_val = get_atr(sym, dt)
                    adx_val, _ = parse_signal_strength(sig)
                    is_strong = adx_val > 35
                    trailing_state[sym] = {
                        'atr': atr_val if atr_val else 0,
                        'is_strong': is_strong,
                        'entry_price': ep,
                        'highest_since_entry': ep
                    }

                active[sym] = {'shares': shares, 'cost': pos_size, 'entry_price': ep, 'entry_date': dt, 'highest_price': ep}
                cash -= pos_size
                t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=sig.data.get("reason",""))
                open_t[sym] = t; all_t.append(t)

            elif dir_ == "sell" and sym in open_t:
                xp = _get_close(md, sym, dt, strategy)
                if not xp: continue
                t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                if sym in active:
                    p2 = active.pop(sym)
                    cash += p2['cost'] + (xp - t.entry_price) * p2['shares']
                if sym in trailing_state:
                    del trailing_state[sym]

        # ── ATR动态止损出场 ──
        if atr_mode:
            to_close = []
            for sym, pos in list(active.items()):
                df = sliced.get(sym)
                if df is None: continue
                mask = df.index <= dt
                if mask.sum() < 1: continue
                current_price = float(df["close"][mask].iloc[-1])

                state = trailing_state.get(sym)
                if state is None: continue

                if current_price > pos['highest_price']:
                    pos['highest_price'] = current_price

                if state['is_strong']:
                    stop_mult = 2.0  # 强势股 2ATR
                else:
                    stop_mult = 1.0  # 弱势股 1ATR

                atr_val = state['atr']
                trailing_stop = pos['highest_price'] * (1 - stop_mult * atr_val / pos['highest_price'])

                if current_price <= trailing_stop and trailing_stop > 0:
                    xp = current_price
                    if xp > 0:
                        t = open_t.pop(sym)
                        t.close(dt, xp, f"ATR止损: 最高{pos['highest_price']:.2f}, 当前{xp:.2f}, {stop_mult}ATR止损位{trailing_stop:.2f}")
                        p2 = active.pop(sym)
                        cash += p2['cost'] + (xp - t.entry_price) * p2['shares']
                    del trailing_state[sym]

    # 强制平仓
    for sym, t in list(open_t.items()):
        xp = _get_close(md, sym, END_FULL, strategy)
        if xp:
            t.close(END_FULL, xp, "end")
            if sym in active:
                p2 = active.pop(sym)
                cash += p2['cost'] + (xp - t.entry_price) * p2['shares']

    if records:
        records[-1] = {'date': records[-1]['date'], 'cash': cash, 'pos_value': 0, 'equity': cash, 'num_pos': 0, 'util': 0}

    dates = pd.to_datetime([r['date'] for r in records]).tz_localize(None)
    equity_series = pd.Series([r['equity'] for r in records], index=dates)
    util_series = pd.Series([r['util'] for r in records], index=dates)
    pos_series = pd.Series([r['num_pos'] for r in records], index=dates)

    return equity_series, util_series, pos_series, all_t, records

def compute_metrics(equity_series, all_t, records, spy_eq=None):
    closed = [t for t in all_t if t.is_closed]
    tr = float(equity_series.iloc[-1] / equity_series.iloc[0] - 1)
    yrs = (END_FULL - START_FULL).days / 365.25
    ann = (1+tr)**(1/yrs)-1 if yrs > 0 else 0
    wins = [t for t in closed if t.pnl_pct > 0]
    losses = [t for t in closed if t.pnl_pct <= 0]
    wr = len(wins)/len(closed) if closed else 0
    aw = np.mean([t.pnl_pct for t in wins]) if wins else 0
    al = abs(np.mean([t.pnl_pct for t in losses])) if losses else 1
    plr = (aw*len(wins))/(al*len(losses)) if losses else 0
    cmax = equity_series.cummax(); dd = (equity_series-cmax)/cmax; mdd = abs(dd.min())
    dr = equity_series.pct_change().dropna()
    sharpe = (dr.mean()*252)/(dr.std()*np.sqrt(252)) if dr.std()>0 else 0
    monthly = {}
    for r in records:
        key = r['date'].strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + 1
    spm = np.mean(list(monthly.values())) if monthly else 0
    avg_util = np.mean([r['util'] for r in records]) if records else 0
    avg_pos = np.mean([r['num_pos'] for r in records]) if records else 0

    return {
        'tr': tr * 100,
        'ann': ann * 100,
        'mdd': mdd * 100,
        'sharpe': sharpe,
        'wr': wr * 100,
        'plr': plr,
        'spm': spm,
        'n': len(closed),
        'avg_util': avg_util,
        'avg_pos': avg_pos,
        'final_equity': equity_series.iloc[-1],
        'equity_series': equity_series,
    }

# ── 回测区间 ────────────────────────────────────────────────────────
days_full = ref[(ref >= START_FULL) & (ref <= END_FULL)]
days_oos  = ref[(ref >= START_OOS)  & (ref <= END_OOS)]

cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'

print("\n" + "="*70)
print("  三个改进方案对照实验 — 全量 2016-2026")
print("="*70)

results = {}

# ── 基准 ──
print("\n[基准] 固定$2000仓位...")
eq_baseline, _, _, trades_baseline, rec_baseline = run_backtest(cfg, days_full, sliced, mode="baseline")
m_baseline = compute_metrics(eq_baseline, trades_baseline, rec_baseline)
results['基准 ($2000固定)'] = m_baseline
print(f"  总收益 {m_baseline['tr']:+.1f}%  年化 {m_baseline['ann']:+.1f}%  回撤 {m_baseline['mdd']:.1f}%  夏普 {m_baseline['sharpe']:.2f}  胜率 {m_baseline['wr']:.1f}%  n={m_baseline['n']}")

# ── 方案A ──
print("\n[方案A] 三档位仓位...")
eq_a, _, _, trades_a, rec_a = run_backtest(cfg, days_full, sliced, mode="tiered_pos", pos_size_base=2000)
m_a = compute_metrics(eq_a, trades_a, rec_a)
results['方案A: 三档位仓位'] = m_a
print(f"  总收益 {m_a['tr']:+.1f}%  年化 {m_a['ann']:+.1f}%  回撤 {m_a['mdd']:.1f}%  夏普 {m_a['sharpe']:.2f}  胜率 {m_a['wr']:.1f}%  n={m_a['n']}")

# ── 方案B ──
print("\n[方案B] ATR动态止损...")
eq_b, _, _, trades_b, rec_b = run_backtest(cfg, days_full, sliced, mode="baseline", atr_mode=True)
m_b = compute_metrics(eq_b, trades_b, rec_b)
results['方案B: ATR动态止损'] = m_b
print(f"  总收益 {m_b['tr']:+.1f}%  年化 {m_b['ann']:+.1f}%  回撤 {m_b['mdd']:.1f}%  夏普 {m_b['sharpe']:.2f}  胜率 {m_b['wr']:.1f}%  n={m_b['n']}")

# ── 方案C ──
print("\n[方案C] 复利+三档仓位...")
eq_c, _, _, trades_c, rec_c = run_backtest(cfg, days_full, sliced, mode="compound_tiered",
    pos_size_base=2000, compound_step=0.20, compound_cap=4000)
m_c = compute_metrics(eq_c, trades_c, rec_c)
results['方案C: 复利+三档仓位'] = m_c
print(f"  总收益 {m_c['tr']:+.1f}%  年化 {m_c['ann']:+.1f}%  回撤 {m_c['mdd']:.1f}%  夏普 {m_c['sharpe']:.2f}  胜率 {m_c['wr']:.1f}%  n={m_c['n']}")

# ── 打印全量对照表 ──
print("\n" + "="*70)
print("  全量回测结果汇总 (2016-2026)")
print("="*70)
print(f"{'方案':<22} {'总收益':>8} {'年化':>7} {'最大回撤':>8} {'夏普':>6} {'胜率':>6} {'盈亏比':>7} {'月均':>6} {'交易数':>6} {'资金利用':>8}")
print("-" * 100)
for name, m in results.items():
    tag = "✅" if m['mdd'] <= 10 and m['ann'] >= 8 else ("⚠️" if m['mdd'] > 15 else "")
    print(f"  {name:<20} {m['tr']:>+7.1f}% {m['ann']:>+6.1f}% {m['mdd']:>7.1f}% {m['sharpe']:>6.2f} {m['wr']:>5.1f}% {m['plr']:>7.2f} {m['spm']:>6.1f} {m['n']:>6d} {m['avg_util']:>7.0f}% {tag}")

# ── OOS ──
print("\n" + "="*70)
print("  样本外回测 (OOS 2024-2026)")
print("="*70)

oos_results = {}

eq_b_o, _, _, trades_b_o, rec_b_o = run_backtest(cfg, days_oos, sliced, mode="baseline")
m_b_o = compute_metrics(eq_b_o, trades_b_o, rec_b_o)
oos_results['基准 ($2000固定)'] = m_b_o

eq_a_o, _, _, trades_a_o, rec_a_o = run_backtest(cfg, days_oos, sliced, mode="tiered_pos", pos_size_base=2000)
m_a_o = compute_metrics(eq_a_o, trades_a_o, rec_a_o)
oos_results['方案A: 三档位仓位'] = m_a_o

eq_b_o, _, _, trades_b_o, rec_b_o = run_backtest(cfg, days_oos, sliced, mode="baseline", atr_mode=True)
m_b_o = compute_metrics(eq_b_o, trades_b_o, rec_b_o)
oos_results['方案B: ATR动态止损'] = m_b_o

eq_c_o, _, _, trades_c_o, rec_c_o = run_backtest(cfg, days_oos, sliced, mode="compound_tiered",
    pos_size_base=2000, compound_step=0.20, compound_cap=4000)
m_c_o = compute_metrics(eq_c_o, trades_c_o, rec_c_o)
oos_results['方案C: 复利+三档仓位'] = m_c_o

print(f"{'方案':<22} {'总收益':>8} {'年化':>7} {'最大回撤':>8} {'夏普':>6} {'胜率':>6} {'盈亏比':>7} {'月均':>6} {'交易数':>6} {'资金利用':>8}")
print("-" * 100)
for name, m in oos_results.items():
    print(f"  {name:<20} {m['tr']:>+7.1f}% {m['ann']:>+6.1f}% {m['mdd']:>7.1f}% {m['sharpe']:>6.2f} {m['wr']:>5.1f}% {m['plr']:>7.2f} {m['spm']:>6.1f} {m['n']:>6d} {m['avg_util']:>7.0f}%")

# ── 画图 ──
fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
fig.suptitle('Three Approaches Comparison: Full Backtest 2016-2026', fontsize=14)

ax1 = axes[0]
colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0']
labels = ['Baseline ($2000)', 'Approach A: Tiered Position',
          'Approach B: ATR Stop', 'Approach C: Compounding+Tiered']
for (name, m), color, label in zip(results.items(), colors, labels):
    ax1.plot(m['equity_series'].index,
             m['equity_series'] / INITIAL_CAPITAL,
             label=label, color=color, linewidth=1.5)
spy_eq_plt = spy_equity.loc[results['基准 ($2000固定)']['equity_series'].index[0]:
                             results['基准 ($2000固定)']['equity_series'].index[-1]]
spy_eq_plt = spy_eq_plt.reindex(results['基准 ($2000固定)']['equity_series'].index, method='ffill').fillna(1.0)
ax1.plot(results['基准 ($2000固定)']['equity_series'].index, spy_eq_plt,
         label='SPY', color='#FF5722', linewidth=1, alpha=0.8)
ax1.axhline(y=1, color='gray', linestyle='--', linewidth=0.8)
ax1.set_ylabel('Equity (Initial=1)')
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_title('Equity Curve Comparison')

ax2 = axes[1]
for (name, m), color in zip(results.items(), colors):
    eq = m['equity_series']
    cmax = eq.cummax(); dd = (cmax - eq) / cmax * 100
    ax2.fill_between(dd.index, 0, dd, alpha=0.25, color=color)
    ax2.plot(dd.index, dd, color=color, linewidth=0.8)
ax2.set_ylabel('Drawdown (%)')
ax2.set_xlabel('Date')
ax2.legend(loc='lower left', fontsize=8, labels=labels)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/tmp/three_approaches_comparison.png', dpi=150, bbox_inches='tight')
print(f"\n[图片] 已保存: /tmp/three_approaches_comparison.png")

# ── 保存结果 ──
save_data = {}
for name, m in results.items():
    save_data[name] = {k: v for k, v in m.items() if k != 'equity_series'}
for name, m in oos_results.items():
    save_data[f"OOS_{name}"] = {k: v for k, v in m.items() if k != 'equity_series'}

with open('/tmp/three_approaches_results.json', 'w') as f:
    json.dump(save_data, f, indent=2, default=str)
print("[数据] 已保存: /tmp/three_approaches_results.json")
print("\n✅ 实验完成")