"""
tier_full_metrics.py — 三层分级回测：真实净值曲线 → 夏普+最大回撤
分别跑A级(×2.0仓)、C级(×1.0仓)、D级(×0.5仓)三个独立回测
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

def run_tier_backtest(tier_filter, pos_mult, initial_capital=50000, base_pos=2000):
    """
    只交易指定层级的信号，应用仓位倍数
    tier_filter: 'A级', 'C级', 'D级', 或 None (所有层级)
    pos_mult: 仓位倍数
    """
    POSITION = base_pos * pos_mult
    cfg = config['strategies']['v_weinstein_adx'].copy()
    cfg['_strategy_id'] = 'v_weinstein_adx'
    strategy_cls = get_strategy('v_weinstein_adx')
    strategy = strategy_cls(cfg, md)
    queue = EventQueue()

    open_t, all_t = {}, []
    cash = float(initial_capital)
    active = {}
    records = []

    for date in days:
        dt = date.to_pydatetime()
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

        # 每日持仓市值
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
        records.append({'date': dt, 'cash': cash, 'pos_value': pv, 'equity': equity, 'util': util, 'num_pos': len(active)})

        for sig in strategy.run_date(dt, queue):
            sym, dir_ = sig.symbol, sig.data["direction"]
            reason = sig.data.get("reason","")

            if tier_filter and tier_classify(reason) != tier_filter:
                continue

            if dir_ == "buy" and sym not in open_t and sym not in active:
                ep = _get_close(md, sym, dt, strategy)
                if not ep: continue
                if cash < POSITION: continue
                shares = POSITION / ep
                active[sym] = {'shares': shares, 'cost': POSITION, 'entry_price': ep}
                cash -= POSITION
                t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=reason)
                open_t[sym] = t; all_t.append(t)
            elif dir_ == "sell" and sym in open_t:
                xp = _get_close(md, sym, dt, strategy)
                if not xp: continue
                t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                if sym in active:
                    p2 = active.pop(sym)
                    cash += POSITION + (xp - t.entry_price) * p2['shares']

    # 强制平仓
    for sym, t in list(open_t.items()):
        xp = _get_close(md, sym, END_FULL, strategy)
        if xp:
            t.close(END_FULL, xp, "end")
            if sym in active:
                p2 = active.pop(sym)
                cash += POSITION + (xp - t.entry_price) * p2['shares']

    if records:
        records[-1] = {'date': records[-1]['date'], 'cash': cash, 'pos_value': 0, 'equity': cash, 'util': 0, 'num_pos': 0}

    dates = pd.to_datetime([r['date'] for r in records]).tz_localize(None)
    equity_series = pd.Series([r['equity'] for r in records], index=dates)
    util_series = pd.Series([r['util'] for r in records], index=dates)
    pos_series = pd.Series([r['num_pos'] for r in records], index=dates)

    return equity_series, util_series, pos_series, all_t, records

def calc_metrics(eq, all_t, yrs):
    closed = [t for t in all_t if t.is_closed]
    if eq.empty or len(eq) < 2:
        return None
    tr = (eq.iloc[-1] / eq.iloc[0] - 1) * 100
    ann = (1 + tr/100) ** (1/yrs) - 1
    ann = ann * 100
    cmax = eq.cummax()
    dd = (eq - cmax) / cmax * 100
    mdd = abs(dd.min())
    dr = eq.pct_change().dropna()
    sharpe = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
    wins = [t for t in closed if t.pnl_pct > 0]
    losses = [t for t in closed if t.pnl_pct <= 0]
    wr = len(wins) / len(closed) * 100 if closed else 0
    aw = np.mean([t.pnl_pct for t in wins]) * 100 if wins else 0
    al = abs(np.mean([t.pnl_pct for t in losses])) * 100 if losses else 0
    plr = aw / al if al > 0 else 0
    avg_util = dr.shape[0]  # placeholder
    return {
        'tr': tr, 'ann': ann, 'mdd': mdd, 'sharpe': sharpe,
        'wr': wr, 'plr': plr, 'aw': aw, 'al': al,
        'n': len(closed), 'avg_util': avg_util,
        'equity': eq
    }

yrs_full = (END_FULL - START_FULL).days / 365.25

print(f"分层回测 — 初始资金 $50,000, 基准仓位 $2,000")
print(f"回测区间: {START_FULL.year}-{START_FULL.month:02d} 至 {END_FULL.year}-{END_FULL.month:02d} ({yrs_full:.1f}年)\n")

results = {}

for tier_name, filter_tier, pos_mult in [
    ('A级 (×2.0仓)', 'A级', 2.0),
    ('C级 (×1.0仓)', 'C级', 1.0),
    ('D级 (×0.5仓)', 'D级', 0.5),
    ('全量基准 ($2000)', None, 1.0),
]:
    print(f"[运行] {tier_name}...")
    eq, util, pos, trades, rec = run_tier_backtest(filter_tier, pos_mult)
    m = calc_metrics(eq, trades, yrs_full)
    results[tier_name] = m
    print(f"  {tier_name}: n={m['n']}笔 胜率{m['wr']:.1f}% 盈亏比{m['plr']:.2f} 总收益{m['tr']:+.1f}% 年化{m['ann']:+.1f}% 最大回撤{m['mdd']:.1f}% 夏普{m['sharpe']:.2f}")

# 打印最终表格
print(f"\n{'='*90}")
print(f"  三层分级回测结果 (2016-2026)")
print(f"{'='*90}")
print(f"  {'层级':<22} {'交易数':>7} {'胜率':>7} {'盈亏比':>7} {'均盈':>7} {'均亏':>7} {'总收益':>9} {'年化':>8} {'最大回撤':>9} {'夏普':>6}")
print(f"  {'-'*87}")

for tier_name, m in results.items():
    print(f"  {tier_name:<22} {m['n']:>7d} {m['wr']:>6.1f}% {m['plr']:>7.2f} {m['aw']:>+6.1f}% {m['al']:>-6.1f}% {m['tr']:>+8.1f}% {m['ann']:>+7.1f}% {m['mdd']:>8.1f}% {m['sharpe']:>6.2f}")

# 存结果
save = {}
for k, v in results.items():
    save[k] = {kk: vv for kk, vv in v.items() if kk != 'equity'}
    save[k]['equity_index'] = [str(x) for x in v['equity'].index]
    save[k]['equity_values'] = v['equity'].values.tolist()

with open('/tmp/tier_full_results.json', 'w') as f:
    import json
    json.dump(save, f, indent=2)
print(f"\n结果已保存: /tmp/tier_full_results.json")
print("Done")