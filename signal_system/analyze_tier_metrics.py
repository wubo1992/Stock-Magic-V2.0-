"""
analyze_tier_metrics.py — 各层级夏普和最大回撤
思路：从一次全量回测中，按层级分离每日持仓，计算各层级独立净值曲线
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
START_IS   = datetime(2016, 1, 1, tzinfo=timezone.utc)
END_IS     = datetime(2023, 12, 31, tzinfo=timezone.utc)
START_OOS  = datetime(2024, 1, 1, tzinfo=timezone.utc)

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

def tier3(trade):
    if trade['adx']>=40 or trade['bo']>=10: return 'A级'
    if trade['adx']>=30 and trade['vol']>=2.0: return 'C级'
    return 'D级'

# ── 收集所有层级交易 ─────────────────────────────────────────────────
print("收集全量交易...")
cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'
strategy_cls = get_strategy('v_weinstein_adx')

all_days = ref[(ref >= START_FULL) & (ref <= END_FULL)]
strategy = strategy_cls(cfg, md)
queue = EventQueue()

open_t, all_trades = {}, []
cash = float(50000)
active = {}

for date in all_days:
    dt = date.to_pydatetime()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    for sig in strategy.run_date(dt, queue):
        sym, dir_ = sig.symbol, sig.data["direction"]
        if dir_ == "buy" and sym not in open_t and sym not in active:
            ep = _get_close(md, sym, dt, strategy)
            if not ep or cash < 2000: continue
            shares = 2000 / ep
            reason = sig.data.get("reason","")
            m = re.search(r'\[ADX\]\s*([\d.]+)', reason)
            m2 = re.search(r'\[量能\]\s*([\d.]+)x', reason)
            m3 = re.search(r'幅度\+([\d.]+)%', reason)
            parsed = {
                'adx': float(m.group(1)) if m else 0,
                'vol': float(m2.group(1)) if m2 else 0,
                'bo': float(m3.group(1)) if m3 else 0,
            }
            tier = tier3(parsed)
            active[sym] = {'shares': shares, 'cost': 2000, 'tier': tier, 'entry_price': ep, 'entry_date': dt}
            cash -= 2000
            t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=reason)
            open_t[sym] = t; all_trades.append({'trade': t, 'tier': tier, 'entry_price': ep, 'shares': shares, 'entry_date': dt})
        elif dir_ == "sell" and sym in open_t:
            xp = _get_close(md, sym, dt, strategy)
            if not xp: continue
            t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
            if sym in active:
                p2 = active.pop(sym)
                cash += 2000 + (xp - t.entry_price) * p2['shares']

for sym, t in list(open_t.items()):
    xp = _get_close(md, sym, END_FULL, strategy)
    if xp:
        t.close(END_FULL, xp, "end")
        if sym in active: active.pop(sym)

# ── 计算各层级净值曲线 ────────────────────────────────────────────────
print("计算各层级净值...")
days_is = ref[(ref >= START_IS) & (ref <= END_IS)]
days_oos = ref[(ref >= START_OOS) & (ref <= END_FULL)]

def compute_tier_equity(days, tier_filter=None):
    """跑一次回测，返回指定层级的净值序列"""
    INITIAL = 50000.0
    POS = 2000.0
    cfg2 = config['strategies']['v_weinstein_adx'].copy()
    cfg2['_strategy_id'] = 'v_weinstein_adx'
    s = strategy_cls(cfg2, md)
    q = EventQueue()
    open_pos, all_t = {}, []
    cash = float(INITIAL)
    active_pos = {}
    records = []

    for date in days:
        dt = date.to_pydatetime()
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

        # 每日持仓市值
        pv = 0.0
        for sym, pos in list(active_pos.items()):
            df = sliced.get(sym)
            if df is not None:
                mask = df.index <= dt
                if mask.sum() >= 1:
                    cur_price = float(df["close"][mask].iloc[-1])
                    pv += cur_price * pos['shares']
        equity = cash + pv
        util = pv / equity * 100 if equity > 0 else 0
        records.append({'date': dt, 'cash': cash, 'pos_value': pv, 'equity': equity, 'util': util})

        for sig in s.run_date(dt, q):
            sym, dir_ = sig.symbol, sig.data["direction"]
            if dir_ == "buy" and sym not in open_pos and sym not in active_pos:
                ep = _get_close(md, sym, dt, s)
                if not ep: continue
                if cash < POS: continue
                shares = POS / ep
                reason = sig.data.get("reason","")
                m = re.search(r'\[ADX\]\s*([\d.]+)', reason)
                m2 = re.search(r'\[量能\]\s*([\d.]+)x', reason)
                m3 = re.search(r'幅度\+([\d.]+)%', reason)
                parsed = {'adx': float(m.group(1)) if m else 0, 'vol': float(m2.group(1)) if m2 else 0, 'bo': float(m3.group(1)) if m3 else 0}
                tier = tier3(parsed)
                if tier_filter and tier != tier_filter: continue
                active_pos[sym] = {'shares': shares, 'cost': POS, 'tier': tier}
                cash -= POS
                t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=reason)
                open_pos[sym] = t; all_t.append(t)
            elif dir_ == "sell" and sym in open_pos:
                xp = _get_close(md, sym, dt, s)
                if not xp: continue
                t = open_pos.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                if sym in active_pos:
                    p2 = active_pos.pop(sym)
                    cash += POS + (xp - t.entry_price) * p2['shares']

    for sym, t in list(open_pos.items()):
        xp = _get_close(md, sym, END_FULL, s)
        if xp:
            t.close(END_FULL, xp, "end")
            if sym in active_pos: active_pos.pop(sym)

    if records:
        records[-1] = {'date': records[-1]['date'], 'cash': cash, 'pos_value': 0, 'equity': cash, 'util': 0}

    dates = pd.to_datetime([r['date'] for r in records]).tz_localize(None)
    eq = pd.Series([r['equity'] for r in records], index=dates)
    return eq, all_t

def calc_metrics(eq, trades, yrs):
    closed = [t for t in trades if t.is_closed]
    if eq.empty or len(eq) < 2: return None
    tr = (eq.iloc[-1]/eq.iloc[0]-1)*100
    cmax = eq.cummax(); dd = (eq-cmax)/cmax; mdd = abs(dd.min())*100
    dr = eq.pct_change().dropna()
    sharpe = (dr.mean()*252)/(dr.std()*np.sqrt(252)) if dr.std()>0 else 0
    wins = [t for t in closed if t.pnl_pct>0]
    losses = [t for t in closed if t.pnl_pct<=0]
    wr = len(wins)/len(closed)*100 if closed else 0
    aw = np.mean([t.pnl_pct for t in wins])*100 if wins else 0
    al = abs(np.mean([t.pnl_pct for t in losses]))*100 if losses else 0
    plr = aw/al if al>0 else 0
    ann = tr/yrs
    return {'tr': tr, 'ann': ann, 'mdd': mdd, 'sharpe': sharpe, 'wr': wr, 'plr': plr, 'n': len(closed)}

print("\n=== IS (2016-2023) ===")
for tier, days, yrs in [('IS', days_is, 8), ('OOS', days_oos, 2.25)]:
    print(f"\n--- {tier} ---")
    for t_name, t_filter in [('A级', 'A级'), ('C级', 'C级'), ('D级', 'D级'), ('全量', None)]:
        eq, trades = compute_tier_equity(days, tier_filter=t_filter)
        m = calc_metrics(eq, trades, yrs)
        if m:
            print(f"  {t_name}: n={m['n']:>4d} 胜率{m['wr']:>5.1f}% 盈亏比{m['plr']:>5.2f} 年化{m['ann']:>+6.1f}% 最大回撤{m['mdd']:>5.1f}% 夏普{m['sharpe']:>5.2f}")

print("\n✅ 完成")