"""
analyze_trades.py — 交易级别深度分析
分析951笔历史交易，回答：哪些维度的筛选条件真正提高了胜率？
"""
import sys, yaml, pickle, json, re
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, '.')

from data.fetcher import fetch
from backtest.engine import Trade
from events import EventQueue
from strategies.registry import get_strategy

START = datetime(2016, 1, 1, tzinfo=timezone.utc)
END   = datetime(2026, 3, 27, tzinfo=timezone.utc)

# ── 加载数据 ────────────────────────────────────────────────────────
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

total_days = (END - START).days + 300
md = fetch(us_stocks, history_days=total_days, end_date=END)
for bm, syms in [("SPY",["SPY"]),("ASHR",["ASHR"]),("EWT",["EWT"])]:
    if bm not in md:
        d = fetch(syms, history_days=total_days, end_date=END)
        if d and bm in d: md[bm] = d[bm]

ref = next(iter(md.values())).index
if ref.tzinfo is None: ref = ref.tz_localize("UTC")
days = ref[(ref >= START) & (ref <= END)]

cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'

sliced = {}
for sym, df in md.items():
    idx = df.index
    if idx.tzinfo is None:
        df = df.copy()
        df.index = idx.tz_localize("UTC")
    sliced[sym] = df

def _get_close(md, sym, dt, strategy):
    df = md.get(sym)
    if df is None: return None
    idx = df.index
    if idx.tzinfo is None: idx = idx.tz_localize("UTC")
    pos = idx.searchsorted(dt)
    if pos >= len(df): pos = len(df) - 1
    if pos < 0: return None
    return float(df["close"].iloc[pos])

# ── 运行回测收集交易 ───────────────────────────────────────────────
print("运行回测收集交易...")
strategy_cls = get_strategy('v_weinstein_adx')
strategy = strategy_cls(cfg, md)
queue = EventQueue()

open_t, all_t = {}, []
cash = float(50000)
active = {}

for date in days:
    dt = date.to_pydatetime()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    for sig in strategy.run_date(dt, queue):
        sym, dir_ = sig.symbol, sig.data["direction"]
        if dir_ == "buy" and sym not in open_t and sym not in active:
            ep = _get_close(md, sym, dt, strategy)
            if not ep: continue
            if cash < 2000: continue
            shares = 2000 / ep
            active[sym] = {'shares': shares, 'cost': 2000}
            cash -= 2000
            t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=sig.data.get("reason",""))
            open_t[sym] = t; all_t.append(t)
        elif dir_ == "sell" and sym in open_t:
            xp = _get_close(md, sym, dt, strategy)
            if not xp: continue
            t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
            if sym in active:
                p2 = active.pop(sym)
                cash += 2000 + (xp - t.entry_price) * p2['shares']

for sym, t in list(open_t.items()):
    xp = _get_close(md, sym, END, strategy)
    if xp:
        t.close(END, xp, "end")
        if sym in active:
            active.pop(sym)

# ── 解析信号维度 ───────────────────────────────────────────────────
def parse_trade(t):
    """从交易reason中解析关键维度"""
    reason = t.entry_reason
    result = {}

    # ADX
    m = re.search(r'\[ADX\]\s*([\d.]+)>', reason)
    result['adx'] = float(m.group(1)) if m else 0

    # RSI
    m = re.search(r'\[RSI\]\s*([\d.]+)<', reason)
    result['rsi'] = float(m.group(1)) if m else 0

    # Volume ratio
    m = re.search(r'\[量能\]\s*([\d.]+)x', reason)
    result['vol_ratio'] = float(m.group(1)) if m else 0

    # Breakout %
    m = re.search(r'幅度\+([\d.]+)%', reason)
    result['breakout_pct'] = float(m.group(1)) if m else 0

    # SMA
    m = re.search(r'SMA(\d+)', reason)
    result['sma'] = int(m.group(1)) if m else 0

    # Trend direction
    result['is_bear'] = '熊市止损' in reason or '熊市' in reason

    result['pnl_pct'] = t.pnl_pct
    result['is_win'] = t.pnl_pct > 0
    result['days_held'] = t.days_held if hasattr(t, 'days_held') else 0

    return result

trades_data = [parse_trade(t) for t in all_t if t.is_closed]
print(f"共 {len(trades_data)} 笔交易")

# ── 逐维度分析 ────────────────────────────────────────────────────
print("\n" + "="*70)
print("  交易级别深度分析")
print("="*70)

def analyze_dimension(data, dim_name, bins=None, is_categorical=False):
    """分析单一维度对胜率/盈亏比的影响"""
    if is_categorical:
        groups = {}
        for item in data:
            key = str(item.get(dim_name, 'NA'))
            groups.setdefault(key, []).append(item)
    else:
        if bins is None:
            bins = [0, 25, 30, 35, 40, 100]
        labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]
        groups = {l: [] for l in labels}
        for item in data:
            val = item.get(dim_name, 0)
            for i in range(len(bins)-1):
                if bins[i] <= val < bins[i+1]:
                    groups[labels[i]].append(item)
                    break

    print(f"\n【{dim_name}】")
    print(f"  {'区间':<15} {'交易数':>6} {'胜率':>7} {'平均盈利':>9} {'平均亏损':>9} {'盈亏比':>7} {'总收益':>9}")
    print(f"  {'-'*62}")

    results = {}
    for label, items in sorted(groups.items()):
        if not items: continue
        wins = [x['pnl_pct'] for x in items if x['is_win']]
        losses = [x['pnl_pct'] for x in items if not x['is_win']]
        wr = len(wins) / len(items) * 100 if items else 0
        avg_win = np.mean(wins) * 100 if wins else 0
        avg_loss = abs(np.mean(losses)) * 100 if losses else 0
        plr = avg_win / avg_loss if avg_loss > 0 else 0
        total = np.sum([x['pnl_pct'] for x in items]) * 100
        results[label] = {'n': len(items), 'wr': wr, 'avg_win': avg_win, 'avg_loss': avg_loss, 'plr': plr, 'total': total}
        print(f"  {label:<15} {len(items):>6d} {wr:>6.1f}% {avg_win:>+8.1f}% {avg_loss:>-8.1f}% {plr:>7.2f} {total:>+8.1f}%")
    return results

# 1. ADX
adx_results = analyze_dimension(trades_data, 'adx', bins=[0, 25, 30, 35, 40, 100])

# 2. Volume Ratio
vol_results = analyze_dimension(trades_data, 'vol_ratio', bins=[0, 2.0, 2.5, 3.0, 10.0])

# 3. Breakout %
bo_results = analyze_dimension(trades_data, 'breakout_pct', bins=[0, 2, 5, 10, 100])

# 4. RSI
rsi_results = analyze_dimension(trades_data, 'rsi', bins=[0, 30, 40, 50, 60, 100])

# 5. 持仓天数
print(f"\n【持仓天数】")
print(f"  {'区间':<15} {'交易数':>6} {'胜率':>7} {'平均盈利':>9} {'平均亏损':>9} {'盈亏比':>7} {'总收益':>9}")
print(f"  {'-'*62}")
day_groups = {}
for item in trades_data:
    d = item.get('days_held', 0)
    if d <= 5: key = "1-5天"
    elif d <= 10: key = "6-10天"
    elif d <= 20: key = "11-20天"
    elif d <= 30: key = "21-30天"
    else: key = "30天+"
    day_groups.setdefault(key, []).append(item)

day_order = ["1-5天", "6-10天", "11-20天", "21-30天", "30天+"]
for label in day_order:
    items = day_groups.get(label, [])
    if not items: continue
    wins = [x['pnl_pct'] for x in items if x['is_win']]
    losses = [x['pnl_pct'] for x in items if not x['is_win']]
    wr = len(wins) / len(items) * 100 if items else 0
    avg_win = np.mean(wins) * 100 if wins else 0
    avg_loss = abs(np.mean(losses)) * 100 if losses else 0
    plr = avg_win / avg_loss if avg_loss > 0 else 0
    total = np.sum([x['pnl_pct'] for x in items]) * 100
    print(f"  {label:<15} {len(items):>6d} {wr:>6.1f}% {avg_win:>+8.1f}% {avg_loss:>-8.1f}% {plr:>7.2f} {total:>+8.1f}%")

# 6. 强势组合
print(f"\n【组合维度分析】")
print("  找出最佳维度组合（同时满足多个条件的交集）")

# 维度组合分析
best_combos = []

for adx_thresh in [30, 35, 40]:
    for vol_thresh in [2.0, 2.5, 3.0]:
        for bo_thresh in [2, 5, 10]:
            filtered = [t for t in trades_data
                       if t['adx'] >= adx_thresh
                       and t['vol_ratio'] >= vol_thresh
                       and t['breakout_pct'] >= bo_thresh]
            if len(filtered) < 20: continue
            wins = [x['pnl_pct'] for x in filtered if x['is_win']]
            losses = [x['pnl_pct'] for x in filtered if not x['is_win']]
            wr = len(wins) / len(filtered) * 100
            avg_win = np.mean(wins) * 100 if wins else 0
            avg_loss = abs(np.mean(losses)) * 100 if losses else 0
            plr = avg_win / avg_loss if avg_loss > 0 else 0
            total = np.sum([x['pnl_pct'] for x in filtered]) * 100
            ann_est = total / 10.0  # 10年
            best_combos.append({
                'adx': adx_thresh, 'vol': vol_thresh, 'bo': bo_thresh,
                'n': len(filtered), 'wr': wr, 'plr': plr, 'total': total, 'ann': ann_est,
                'avg_win': avg_win, 'avg_loss': avg_loss
            })

# 排序：按夏普（简化用总收益/交易数/胜率）
best_combos.sort(key=lambda x: (x['wr'], x['plr'], -x['n']), reverse=True)

print(f"\n  {'ADX≥':>5} {'量≥':>5} {'突破≥':>6} {'交易数':>6} {'胜率':>6} {'盈亏比':>7} {'年均':>7} {'总收益':>8}")
print(f"  {'-'*50}")
for c in best_combos[:15]:
    print(f"  {c['adx']:>5.0f} {c['vol']:>5.1f} {c['bo']:>5.0f}% {c['n']:>6d} {c['wr']:>5.1f}% {c['plr']:>7.2f} {c['ann']:>+6.1f}% {c['total']:>+7.1f}%")

# ── 结论 ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("  关键发现")
print("="*70)

# 计算基础胜率
all_wins = [x for x in trades_data if x['is_win']]
all_losses = [x for x in trades_data if not x['is_win']]
baseline_wr = len(all_wins) / len(trades_data) * 100
baseline_plr = (np.mean([x['pnl_pct'] for x in all_wins]) * len(all_wins)) / (abs(np.mean([x['pnl_pct'] for x in all_losses])) * len(all_losses)) if all_losses else 0

print(f"\n基准（所有交易）：胜率 {baseline_wr:.1f}%，盈亏比 {baseline_plr:.2f}，共 {len(trades_data)} 笔")

# ADX维度最强区间
best_adx = max(adx_results.items(), key=lambda x: x[1]['wr'])
print(f"\nADX维度：ADX≥{best_adx[0].split('-')[0]} 胜率{best_adx[1]['wr']:.1f}%，盈亏比{best_adx[1]['plr']:.2f}（{'+' if best_adx[1]['wr'] > baseline_wr else ''}{best_adx[1]['wr']-baseline_wr:.1f}%）")

# Vol维度最强区间
best_vol = max(vol_results.items(), key=lambda x: x[1]['wr'])
print(f"量能维度：{best_vol[0]} 胜率{best_vol[1]['wr']:.1f}%，盈亏比{best_vol[1]['plr']:.2f}（{'+' if best_vol[1]['wr'] > baseline_wr else ''}{best_vol[1]['wr']-baseline_wr:.1f}%）")

# 找出最优组合
if best_combos:
    b = best_combos[0]
    print(f"\n最优组合：ADX≥{b['adx']} + 量≥{b['vol']}x + 突破≥{b['bo']}%")
    print(f"  交易数 {b['n']}，胜率 {b['wr']:.1f}%，盈亏比 {b['plr']:.2f}，年均 {b['ann']:+.1f}%")
    print(f"  相比基准：胜率{'+' if b['wr'] > baseline_wr else ''}{b['wr']-baseline_wr:.1f}%，盈亏比{'+' if b['plr'] > baseline_plr else ''}{b['plr']-baseline_plr:.2f}")

print("\n✅ 分析完成")