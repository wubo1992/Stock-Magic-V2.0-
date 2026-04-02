"""
backtest_bullbear.py — 牛熊自适应策略回测对比
"""
import re, yaml, json, sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, '.')

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
print(f"[股票池] {len(us_stocks)} 只")

with open("config.yaml") as f:
    config = yaml.safe_load(f)

from data.fetcher import fetch
from backtest.engine import Trade, _ensure_utc, _get_close
from events import EventQueue
from strategies.registry import get_strategy

INITIAL_CAPITAL = 50_000.0
POSITION_SIZE   = 1_500.0

FULL_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
FULL_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)
OOS_START  = datetime(2024, 1, 1, tzinfo=timezone.utc)
OOS_END    = datetime(2026, 3, 27, tzinfo=timezone.utc)


class QuickEngine:
    WARMUP_DAYS = 300

    def __init__(self, cfg, symbols, start, end):
        self.cfg = cfg
        self.symbols = symbols
        self.start = _ensure_utc(start)
        self.end = _ensure_utc(end)

    def run(self):
        total = (self.end - self.start).days + self.WARMUP_DAYS
        md = fetch(self.symbols, history_days=total, end_date=self.end)
        if not md: raise RuntimeError("no data")
        for bm, syms in [("SPY",["SPY"]),("ASHR",["ASHR"]),("EWT",["EWT"])]:
            if bm not in md:
                d = fetch(syms, history_days=total, end_date=self.end)
                if d and bm in d: md[bm] = d[bm]

        ref = next(iter(md.values())).index
        if ref.tzinfo is None: ref = ref.tz_localize("UTC")
        days = ref[(ref >= self.start) & (ref <= self.end)]

        strategy_cls = get_strategy(self.cfg.get('_strategy_id', 'v_weinstein_adx'))
        strategy = strategy_cls(self.cfg, md)
        queue = EventQueue()

        sliced = {}
        for sym, df in md.items():
            idx = df.index
            if idx.tzinfo is None:
                df = df.copy()
                df.index = idx.tz_localize("UTC")
            sliced[sym] = df

        open_t, all_t = {}, []
        cash = float(INITIAL_CAPITAL)
        active = {}
        records = []

        for date in days:
            dt = date.to_pydatetime()
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

            pv = 0.0
            for sym, pos in active.items():
                df = sliced.get(sym)
                if df is not None:
                    mask = df.index <= dt
                    if mask.sum() >= 1:
                        pv += float(df["close"][mask].iloc[-1]) * pos['shares']
            records.append({'date': dt, 'equity': cash + pv})

            for sig in strategy.run_date(dt, queue):
                sym, dir_ = sig.symbol, sig.data["direction"]
                if dir_ == "buy" and sym not in open_t:
                    ep = _get_close(md, sym, dt, strategy)
                    if not ep: continue
                    while cash < POSITION_SIZE and active:
                        def key(item):
                            s, p = item
                            cv = float(sliced[s]["close"].loc[sliced[s].index <= dt].iloc[-1]) * p['shares']
                            return ((cv - p['cost']) / p['cost'],
                                    (dt.date() - _ensure_utc(p['entry_date']).date()).days)
                        w = min(active.items(), key=key)[0]
                        p2 = active[w]
                        xp = float(sliced[w]["close"].loc[sliced[w].index <= dt].iloc[-1])
                        cash += p2['cost'] + (xp - p2['entry_price']) * p2['shares']
                        if w in open_t:
                            t = open_t.pop(w); t.close(dt, xp, "rebal")
                        del active[w]
                    if cash < POSITION_SIZE: continue
                    sh = POSITION_SIZE / ep
                    active[sym] = {'shares': sh, 'cost': POSITION_SIZE, 'entry_price': ep, 'entry_date': dt}
                    cash -= POSITION_SIZE
                    t = Trade(symbol=sym, entry_date=dt, entry_price=ep,
                               entry_reason=sig.data.get("reason",""))
                    open_t[sym] = t; all_t.append(t)
                elif dir_ == "sell" and sym in open_t:
                    xp = _get_close(md, sym, dt, strategy)
                    if not xp: continue
                    t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                    if sym in active:
                        p2 = active.pop(sym)
                        cash += POSITION_SIZE + (xp - t.entry_price) * p2['shares']

        for sym, t in list(open_t.items()):
            xp = _get_close(md, sym, self.end, strategy)
            if xp:
                t.close(self.end, xp, "end")
                if sym in active:
                    p2 = active.pop(sym)
                    cash += POSITION_SIZE + (xp - t.entry_price) * p2['shares']

        if records: records[-1] = {'date': records[-1]['date'], 'equity': cash}
        equity = pd.Series([r['equity'] for r in records])
        closed = [t for t in all_t if t.is_closed]
        m, eq = self._metrics(closed, equity)
        return m, equity

    def _metrics(self, closed, equity):
        if not closed or len(equity) == 0: return {}
        tr = float(equity.iloc[-1] / equity.iloc[0] - 1)
        yrs = (self.end - self.start).days / 365.25
        ann = (1+tr)**(1/yrs)-1 if yrs > 0 else 0
        wins = [t for t in closed if t.pnl_pct > 0]
        losses = [t for t in closed if t.pnl_pct <= 0]
        wr = len(wins)/len(closed)
        aw = np.mean([t.pnl_pct for t in wins]) if wins else 0
        al = abs(np.mean([t.pnl_pct for t in losses])) if losses else 1
        plr = (aw*len(wins))/(al*len(losses)) if losses else 0
        cmax = equity.cummax(); dd = (equity-cmax)/cmax; mdd = abs(dd.min())
        dr = equity.pct_change().dropna()
        sharpe = (dr.mean()*252)/(dr.std()*np.sqrt(252)) if dr.std()>0 else 0
        monthly = defaultdict(int)
        for t in closed: monthly[t.entry_date.strftime("%Y-%m")[:7]] += 1
        spm = np.mean(list(monthly.values())) if monthly else 0
        return {'tr':tr*100,'ann':ann*100,'mdd':mdd*100,'sharpe':sharpe,
                'wr':wr*100,'plr':plr,'spm':spm,'n':len(closed)}, equity

    def run_all(self, label):
        m, eq = self.run()
        print(f"\n  【{label}】")
        print(f"    总收益 {m['tr']:>+6.1f}%  年化 {m['ann']:>+6.1f}%  "
              f"回撤 {m['mdd']:>5.1f}%  夏普 {m['sharpe']:>5.2f}  "
              f"胜率 {m['wr']:>5.1f}%  盈亏比 {m['plr']:>5.2f}  "
              f"月均 {m['spm']:>4.1f}信号  n={m['n']}")
        return m, eq


print("="*68)
print("  OOS 回测 (2024-2026)")
print("="*68)

# 基线
base_cfg = config['strategies']['v_weinstein_adx'].copy()
base_cfg['_strategy_id'] = 'v_weinstein_adx'
m1, _ = QuickEngine(base_cfg, us_stocks, OOS_START, OOS_END).run_all("基线 (v_weinstein_adx)")

# 牛熊自适应
bb_cfg = config['strategies']['v_weinstein_bullbear'].copy()
bb_cfg['_strategy_id'] = 'v_weinstein_bullbear'
m2, eq2 = QuickEngine(bb_cfg, us_stocks, OOS_START, OOS_END).run_all("牛熊自适应 (v_weinstein_bullbear)")

print("\n" + "="*68)
print("  全量验证 (2020-2026)")
print("="*68)

m3, _ = QuickEngine(base_cfg, us_stocks, FULL_START, FULL_END).run_all("基线 (v_weinstein_adx)")
m4, eq4 = QuickEngine(bb_cfg, us_stocks, FULL_START, FULL_END).run_all("牛熊自适应 (v_weinstein_bullbear)")

# SPY 对比
import pickle
from pathlib import Path
spy_df = pickle.load(open(Path("data/cache/SPY.pkl"), 'rb'))
spy_df.index = spy_df.index.tz_localize(None)

for label, start, end in [("OOS 2024-2026", OOS_START, OOS_END), ("全量 2020-2026", FULL_START, FULL_END)]:
    mask = (spy_df.index >= start.replace(tzinfo=None)) & (spy_df.index <= end.replace(tzinfo=None))
    if mask.sum() >= 2:
        spy_ret = (float(spy_df['close'][mask].iloc[-1]) / float(spy_df['close'][mask].iloc[0]) - 1) * 100
        print(f"  SPY {label}: {spy_ret:+.1f}%")

print("\n  [说明] 牛市模式参数: RSI<90, ADX>25, SMA确认20天, 量1.2x")
print("  [说明] 熊市模式参数: RSI<85, ADX>35, SMA确认30天, 量1.5x")
print("  [说明] 牛市判定: SPY > SMA150 且 SPY ADX > 20")

# 保存结果
with open('/tmp/bullbear_result.json', 'w') as f:
    json.dump({
        'base_oos': {k:v for k,v in m1.items()}, 'bullbear_oos': {k:v for k,v in m2.items()},
        'base_full': {k:v for k,v in m3.items()}, 'bullbear_full': {k:v for k,v in m4.items()},
    }, f, indent=2, default=str)
print("\n  已保存: /tmp/bullbear_result.json")
