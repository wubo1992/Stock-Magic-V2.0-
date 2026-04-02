"""
tier_real_backtest.py — 用真实净值曲线计算各层级的夏普和最大回撤
思路：只跑一次回测，记录每笔交易属于哪个层级，然后计算各层级的真实净值曲线
"""
import sys, yaml, re, pickle
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, '.')

from data.fetcher import fetch
from backtest.engine import Trade
from events import EventQueue
from strategies.registry import get_strategy

START_FULL = datetime(2016, 1, 1, tzinfo=timezone.utc)
END_FULL   = datetime(2026, 3, 27, tzinfo=timezone.utc)

us_stocks_set = set()
with open("UNIVERSE.md") as f:
    for section in re.split(r"^## ", f.read(), flags=re.MULTILINE):
        lines = section.split("\n")
        if lines[0].strip().startswith("板块 S：") or lines[0].strip().startswith("板块 N："):
            for line in lines:
                if line.startswith("|"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and re.match(r"^[A-Z0-9]{1,6}(\.[A-Z0-9]{1,5})?$", parts[1]):
                        us_stocks_set.add(parts[1])

with open("config.yaml") as f:
    config = yaml.safe_load(f)

md = fetch(sorted(us_stocks_set), history_days=(END_FULL-START_FULL).days+300, end_date=END_FULL)
for bm, syms in [("SPY",["SPY"]),("ASHR",["ASHR"]),("EWT",["EWT"])]:
    if bm not in md:
        d = fetch(syms, history_days=(END_FULL-START_FULL).days+300, end_date=END_FULL)
        if d and bm in d: md[bm] = d[bm]

ref = next(iter(md.values())).index
if ref.tzinfo is None: ref = ref.tz_localize("UTC")

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
    pos = min(pos, len(df)-1)
    if pos < 0: return None
    return float(df["close"].iloc[pos])

def tier_classify(reason):
    m = re.search(r'\[ADX\]\s*([\d.]+)', reason)
    m2 = re.search(r'\[量能\]\s*([\d.]+)x', reason)
    m3 = re.search(r'幅度\+([\d.]+)%', reason)
    adx = float(m.group(1)) if m else 0
    vol = float(m2.group(1)) if m2 else 0
    bo = float(m3.group(1)) if m3 else 0
    if adx >= 40 or bo >= 10: return 'A级'
    if adx >= 30 and vol >= 2.0: return 'C级'
    return 'D级'

# ── 单次回测，记录每笔交易属于哪个层级 ──────────────────────────────────────
print("运行回测，记录层级...")
days = ref[(ref >= START_FULL) & (ref <= END_FULL)]

cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'
strategy_cls = get_strategy('v_weinstein_adx')
strategy = strategy_cls(cfg, md)
queue = EventQueue()

open_t, all_trades = {}, []
cash = float(50000)
active = {}

# 记录：每个层级的每日净值贡献
tier_equity = {'A级': [], 'C级': [], 'D级': []}
tier_open_value = {'A级': {}, 'C级': {}, 'D级': {}}
tier_closed = {'A级': [], 'C级': [], 'D级': []}

INITIAL = 50000.0
POS = 2000.0

for date in days:
    dt = date.to_pydatetime()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

    # 每日各层级持仓市值
    tier_vals = {}
    for tier in ['A级', 'C级', 'D级']:
        tier_vals[tier] = 0.0
        for sym, pos in tier_open_value[tier].items():
            df = sliced.get(sym)
            if df is not None:
                mask = df.index <= dt
                if mask.sum() >= 1:
                    price = float(df["close"][mask].iloc[-1])
                    shares = tier_open_value[tier][sym]['shares']
                    tier_vals[tier] += price * shares

    # 记录当日各层级总市值（含现金分配）
    for tier in ['A级', 'C级', 'D级']:
        # 各层级现金分配按持仓市值比例
        tier_equity[tier].append({'date': dt, 'pos_value': tier_vals[tier]})

    for sig in strategy.run_date(dt, queue):
        sym, dir_ = sig.symbol, sig.data["direction"]
        reason = sig.data.get("reason","")
        t_tier = tier_classify(reason)

        if dir_ == "buy" and sym not in open_t and sym not in active:
            ep = _get_close(md, sym, dt, strategy)
            if not ep or cash < POS: continue
            shares = POS / ep
            active[sym] = {'shares': shares, 'tier': t_tier}
            tier_open_value[t_tier][sym] = {'shares': shares, 'entry_price': ep}
            cash -= POS
            t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=reason)
            open_t[sym] = t; all_trades.append({'trade': t, 'tier': t_tier, 'entry_price': ep, 'shares': shares, 'entry_date': dt})

        elif dir_ == "sell" and sym in open_t:
            xp = _get_close(md, sym, dt, strategy)
            if not xp: continue
            t = open_t.pop(sym); t.close(dt, xp, reason)
            if sym in active:
                pos = active.pop(sym)
                t_tier = pos['tier']
                tier_closed[t_tier].append({'trade': t, 'pnl': (xp-t.entry_price)*pos['shares'], 'cost': POS})
                if sym in tier_open_value[t_tier]:
                    del tier_open_value[t_tier][sym]
                cash += POS + (xp - t.entry_price) * pos['shares']

# 强制平仓
for sym, t in list(open_t.items()):
    xp = _get_close(md, sym, END_FULL, strategy)
    if xp:
        t.close(END_FULL, xp, "end")
        if sym in active:
            pos = active.pop(sym)
            tier_closed[pos['tier']].append({'trade': t, 'pnl': (xp-t.entry_price)*pos['shares'], 'cost': POS})
            if sym in tier_open_value[pos['tier']]:
                del tier_open_value[pos['tier']][sym]
            cash += POS + (xp - t.entry_price) * pos['shares']

# ── 分配现金给各层级 ─────────────────────────────────────────────────────────
# 各层级的资金分配 = 各层级平仓盈亏累计 / 总平仓盈亏 * 初始资金
tier_total_pnl = {}
for tier in ['A级', 'C级', 'D级']:
    tier_total_pnl[tier] = sum(x['pnl'] for x in tier_closed[tier])
    tier_closed[tier].append({'pnl': cash * (tier_total_pnl[tier] / sum(tier_total_pnl.values())) if sum(tier_total_pnl.values()) > 0 else cash/3})

# ── 计算各层级净值曲线 ───────────────────────────────────────────────────────
# 每个层级的净值 = 初始资金 + 累计平仓盈亏
tier_cum_pnl = {}
for tier in ['A级', 'C级', 'D级']:
    cum = 0.0
    records = []
    for entry in tier_equity[tier]:
        # 找到该层级最后一笔平仓
        cum += sum(x['pnl'] for x in tier_closed[tier] if x['trade'].entry_date <= entry['date'])
        records.append(cum + INITIAL)
    if records:
        dates = [r['date'] for r in tier_equity[tier]]
        eq = pd.Series(records, index=pd.to_datetime(dates).tz_localize(None))
        tier_cum_pnl[tier] = eq

# ── 计算指标 ─────────────────────────────────────────────────────────────
def calc_metrics(eq, closed_trades, yrs):
    if eq is None or eq.empty: return None
    tr = (eq.iloc[-1]/eq.iloc[0]-1)*100 if eq.iloc[0] != 0 else 0
    cmax = eq.cummax(); dd = (eq-cmax)/cmax; mdd = abs(dd.min())*100
    dr = eq.pct_change().dropna()
    sharpe = (dr.mean()*252)/(dr.std()*np.sqrt(252)) if dr.std()>0 else 0
    wins = [x['trade'].pnl_pct for x in closed_trades if x['trade'].pnl_pct > 0]
    losses = [x['trade'].pnl_pct for x in closed_trades if x['trade'].pnl_pct <= 0]
    wr = len(wins)/len(closed_trades)*100 if closed_trades else 0
    aw = np.mean(wins)*100 if wins else 0
    al = abs(np.mean(losses))*100 if losses else 0
    plr = aw/al if al>0 else 0
    return {'tr': tr, 'mdd': mdd, 'sharpe': sharpe, 'wr': wr, 'plr': plr, 'n': len(closed_trades)}

print(f"\n共 {len(all_trades)} 笔交易")
for tier in ['A级', 'C级', 'D级']:
    n = len(tier_closed[tier])
    print(f"  {tier}: {n}笔平仓")

print(f"\n总资金分配: A级={tier_total_pnl['A级']:.0f}, C级={tier_total_pnl['C级']:.0f}, D级={tier_total_pnl['D级']:.0f}")

print(f"\n{'层级':<8} {'交易数':>6} {'胜率':>7} {'盈亏比':>7} {'总收益':>9} {'年化':>7} {'最大回撤':>8} {'夏普':>6}")
print('-'*62)

for tier in ['A级', 'C级', 'D级']:
    closed = [x for x in tier_closed[tier] if hasattr(x['trade'], 'pnl_pct')]
    m = calc_metrics(tier_cum_pnl.get(tier), closed, 10.2)
    if m:
        print(f"{tier:<8} {m['n']:>6d} {m['wr']:>6.1f}% {m['plr']:>7.2f} {m['tr']:>+8.1f}% {m['tr']/10.2:>+6.1f}% {m['mdd']:>7.1f}% {m['sharpe']:>6.2f}")

print("\n✅ 完成")