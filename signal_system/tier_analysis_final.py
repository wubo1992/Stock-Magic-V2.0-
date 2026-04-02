"""
tier_analysis_final.py — 各层级真实回测数据
"""
import sys, yaml, re
import numpy as np
from datetime import datetime, timezone
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

md = fetch(us_stocks, history_days=(END_FULL-START_FULL).days+300, end_date=END_FULL)
for bm, syms in [("SPY",["SPY"]),("ASHR",["ASHR"]),("EWT",["EWT"])]:
    if bm not in md:
        d = fetch(syms, history_days=(END_FULL-START_FULL).days+300, end_date=END_FULL)
        if d and bm in d: md[bm] = d[bm]

ref = next(iter(md.values())).index
if ref.tzinfo is None: ref = ref.tz_localize("UTC")
days = ref[(ref >= START_FULL) & (ref <= END_FULL)]

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

cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'
strategy_cls = get_strategy('v_weinstein_adx')
strategy = strategy_cls(cfg, md)
queue = EventQueue()

open_t, all_trades = {}, []
cash = float(50000)
active = {}

for date in days:
    dt = date.to_pydatetime()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    for sig in strategy.run_date(dt, queue):
        sym, dir_ = sig.symbol, sig.data["direction"]
        if dir_ == "buy" and sym not in open_t and sym not in active:
            ep = _get_close(md, sym, dt, strategy)
            if not ep or cash < 2000: continue
            shares = 2000 / ep
            reason = sig.data.get("reason","")
            tier = tier_classify(reason)
            active[sym] = {'shares': shares, 'tier': tier, 'entry_price': ep}
            cash -= 2000
            t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=reason)
            open_t[sym] = t; all_trades.append({'trade': t, 'tier': tier, 'entry_date': dt})
        elif dir_ == "sell" and sym in open_t:
            xp = _get_close(md, sym, dt, strategy)
            if not xp: continue
            t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
            if sym in active: cash += 2000 + (xp-t.entry_price)*active.pop(sym)['shares']

for sym, t in list(open_t.items()):
    xp = _get_close(md, sym, END_FULL, strategy)
    if xp:
        t.close(END_FULL, xp, "end")
        if sym in active: active.pop(sym)

closed = [x for x in all_trades if x['trade'].is_closed]
print(f"总交易: {len(closed)}笔\n")

def stats(trades_list, yrs):
    c = [x['trade'] for x in trades_list]
    wins = [t for t in c if t.pnl_pct > 0]
    losses = [t for t in c if t.pnl_pct <= 0]
    wr = len(wins)/len(c)*100 if c else 0
    aw = np.mean([t.pnl_pct for t in wins])*100 if wins else 0
    al = abs(np.mean([t.pnl_pct for t in losses]))*100 if losses else 0
    plr = aw/al if al > 0 else 0
    total = sum(t.pnl_pct for t in c)*100
    ann = total/yrs
    # 简化夏普: (E[R]/sigma), E[R] ~ (wr*aw - (1-wr)*al)/100
    e_ret = (wr/100*aw/100 - (100-wr)/100*al/100)
    e_s = e_ret/(al/100) if al > 0 else 0
    return {'n': len(c), 'wr': wr, 'plr': plr, 'aw': aw, 'al': al, 'total': total, 'ann': ann, 'e_s': e_s}

for period_name, yr_start, yr_end, yrs in [
    ('全量 2016-2026', 2016, 2026, 10.2),
    ('IS 2016-2023', 2016, 2023, 8.0),
    ('OOS 2024-2026', 2024, 2026, 2.2)
]:
    print(f"{'='*75}")
    print(f"  {period_name}")
    print(f"{'='*75}")
    header = f"  {'层级':<8} {'交易数':>6} {'胜率':>7} {'盈亏比':>7} {'均盈':>7} {'均亏':>7} {'总收益':>9} {'年化':>7} {'估算夏普':>9}"
    print(header)
    print(f"  {'-'*68}")

    period_closed = [x for x in closed if yr_start <= x['entry_date'].year <= yr_end]

    for tier in ['A级', 'C级', 'D级']:
        tier_trades = [x for x in period_closed if x['tier'] == tier]
        s = stats(tier_trades, yrs)
        if s['n'] > 0:
            print(f"  {tier:<8} {s['n']:>6d} {s['wr']:>6.1f}% {s['plr']:>7.2f} {s['aw']:>+6.1f}% {s['al']:>-6.1f}% {s['total']:>+8.1f}% {s['ann']:>+6.1f}% {s['e_s']:>9.2f}")

    s_all = stats(period_closed, yrs)
    print(f"  {'整体':<8} {s_all['n']:>6d} {s_all['wr']:>6.1f}% {s_all['plr']:>7.2f} {s_all['aw']:>+6.1f}% {s_all['al']:>-6.1f}% {s_all['total']:>+8.1f}% {s_all['ann']:>+6.1f}% {s_all['e_s']:>9.2f}")
    print()

print("注: 估算夏普 = (胜率*均盈 - 败率*均亏) / 均亏 (简化估计)")
print("    最大回撤: 需真实净值曲线, 此处暂无法提供")
print("Done")