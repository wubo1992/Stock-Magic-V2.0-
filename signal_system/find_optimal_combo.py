"""
find_optimal_combo.py — 找最优维度组合
"""
import sys, yaml, pickle, re
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

def parse_trade(t):
    reason = t.entry_reason
    result = {}
    m = re.search(r'\[ADX\]\s*([\d.]+)>', reason)
    result['adx'] = float(m.group(1)) if m else 0
    m = re.search(r'\[RSI\]\s*([\d.]+)<', reason)
    result['rsi'] = float(m.group(1)) if m else 0
    m = re.search(r'\[量能\]\s*([\d.]+)x', reason)
    result['vol_ratio'] = float(m.group(1)) if m else 0
    m = re.search(r'幅度\+([\d.]+)%', reason)
    result['breakout_pct'] = float(m.group(1)) if m else 0
    result['pnl_pct'] = t.pnl_pct
    result['is_win'] = t.pnl_pct > 0
    return result

trades_data = [parse_trade(t) for t in all_t if t.is_closed]
print(f"共 {len(trades_data)} 笔交易\n")

# 穷举所有维度组合
print("="*75)
print("  穷举最优维度组合")
print("="*75)
print(f"{'ADX≥':>5} {'量≥':>5} {'突破≥':>7} {'交易数':>6} {'胜率':>7} {'盈亏比':>7} {'年均':>8} {'总收益':>9}")
print("-"*55)

results = []
for adx in [30, 35, 40, 50]:
    for vol in [2.0, 2.5, 3.0, 4.0]:
        for bo in [2, 5, 10, 15]:
            filtered = [t for t in trades_data
                       if t['adx'] >= adx
                       and t['vol_ratio'] >= vol
                       and t['breakout_pct'] >= bo]
            if len(filtered) < 15: continue
            wins = [x['pnl_pct'] for x in filtered if x['is_win']]
            losses = [x['pnl_pct'] for x in filtered if not x['is_win']]
            wr = len(wins) / len(filtered) * 100
            avg_win = np.mean(wins) * 100 if wins else 0
            avg_loss = abs(np.mean(losses)) * 100 if losses else 0
            plr = avg_win / avg_loss if avg_loss > 0 else 0
            total = np.sum([x['pnl_pct'] for x in filtered]) * 100
            ann = total / 10.0
            results.append({
                'adx': adx, 'vol': vol, 'bo': bo,
                'n': len(filtered), 'wr': wr, 'plr': plr,
                'total': total, 'ann': ann,
                'avg_win': avg_win, 'avg_loss': avg_loss
            })

# 按多个维度排序：胜率>盈亏比>交易数
results.sort(key=lambda x: (x['wr'], x['plr'], x['n']), reverse=True)

print("\n【按胜率排序 TOP 20】")
for r in results[:20]:
    print(f"  ADX≥{r['adx']:<3} 量≥{r['vol']:<4} 突破≥{r['bo']:<4} {r['n']:>5}笔 胜率{r['wr']:>5.1f}% 盈亏比{r['plr']:>5.2f} 年均{r['ann']:>+7.1f}% 总收益{r['total']:>+8.1f}%")

# 按盈亏比排序
print("\n【按盈亏比排序 TOP 15】")
results.sort(key=lambda x: (x['plr'], x['wr'], x['n']), reverse=True)
for r in results[:15]:
    print(f"  ADX≥{r['adx']:<3} 量≥{r['vol']:<4} 突破≥{r['bo']:<4} {r['n']:>5}笔 胜率{r['wr']:>5.1f}% 盈亏比{r['plr']:>5.2f} 年均{r['ann']:>+7.1f}% 总收益{r['total']:>+8.1f}%")

# 找"综合最优"：在交易数>50的前提下找最好
print("\n【交易数>80的最优组合】")
filtered2 = [r for r in results if r['n'] >= 80]
filtered2.sort(key=lambda x: (x['wr'], x['plr']), reverse=True)
for r in filtered2[:10]:
    print(f"  ADX≥{r['adx']:<3} 量≥{r['vol']:<4} 突破≥{r['bo']:<4} {r['n']:>5}笔 胜率{r['wr']:>5.1f}% 盈亏比{r['plr']:>5.2f} 年均{r['ann']:>+7.1f}% 总收益{r['total']:>+8.1f}%")

# 基准
all_wins = [x for x in trades_data if x['is_win']]
baseline_wr = len(all_wins) / len(trades_data) * 100
baseline_plr = (np.mean([x['pnl_pct'] for x in all_wins]) * len(all_wins)) / (abs(np.mean([x['pnl_pct'] for x in trades_data if not x['is_win']])) * len([x for x in trades_data if not x['is_win']]))
print(f"\n基准: 胜率{baseline_wr:.1f}%, 盈亏比{baseline_plr:.2f}, {len(trades_data)}笔")

print("\n✅ 分析完成")