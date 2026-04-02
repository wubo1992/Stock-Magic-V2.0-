"""
backtest_sharpe_focused.py — 夏普优先参数验证
ADX>25, 追踪止盈15%, 放量2.0x, SMA确认20天
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
from strategies.v_weinstein_adx.weinstein_adx_strategy import WeinsteinADXStrategy

INITIAL_CAPITAL = 50_000.0
POSITION_SIZE   = 1_500.0

# ── 夏普优先参数 ────────────────────────────────────────────────────
SHARPE_CFG = {
    'sma_long': 150,
    'trend_lookback': 20,      # ← 30→20
    'pivot_lookback': 30,
    'min_breakout_pct': 0.005,
    'volume_mult': 2.0,         # ← 1.5→2.0
    'rsi_max': 85,
    'adx_threshold': 25,       # ← 35→25
    'market_filter': False,
    'spy_bear_stop_loss': 0.05,
    'stop_loss_pct': 0.07,
    'trailing_stop_pct': 0.15,  # ← 18%→15%
    'time_stop_days': 30,
    'time_stop_min_gain': 0.05,
}

BASE_CFG = {
    'sma_long': 150, 'trend_lookback': 30, 'pivot_lookback': 30,
    'min_breakout_pct': 0.005, 'volume_mult': 1.5,
    'rsi_max': 85, 'adx_threshold': 35, 'market_filter': False,
    'spy_bear_stop_loss': 0.05, 'stop_loss_pct': 0.07,
    'trailing_stop_pct': 0.18, 'time_stop_days': 30, 'time_stop_min_gain': 0.05,
}

OOS_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
OOS_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)
FULL_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
FULL_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)


class QuickEngine:
    WARMUP_DAYS = 300

    def __init__(self, cfg, start, end, symbols):
        self.cfg = cfg
        self.start = _ensure_utc(start)
        self.end = _ensure_utc(end)
        self.symbols = symbols

    def run(self):
        total_days = (self.end - self.start).days + self.WARMUP_DAYS
        market_data = fetch(self.symbols, history_days=total_days, end_date=self.end)
        if not market_data:
            raise RuntimeError("无法获取数据")
        for bm, syms in [("SPY", ["SPY"]), ("ASHR", ["ASHR"]), ("EWT", ["EWT"])]:
            if bm not in market_data:
                d = fetch(syms, history_days=total_days, end_date=self.end)
                if d and bm in d:
                    market_data[bm] = d[bm]

        ref = next(iter(market_data.values())).index
        if ref.tzinfo is None:
            ref = ref.tz_localize("UTC")
        days = ref[(ref >= self.start) & (ref <= self.end)]

        strategy = WeinsteinADXStrategy(self.cfg, market_data)
        queue = EventQueue()

        sliced = {}
        for sym, df in market_data.items():
            idx = df.index
            if idx.tzinfo is None:
                df = df.copy()
                df.index = idx.tz_localize("UTC")
            sliced[sym] = df

        open_trades, all_trades = {}, []
        cash = float(INITIAL_CAPITAL)
        active = {}
        records = []

        for date in days:
            dt = date.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            pv = sum(float(sliced[s]["close"].loc[sliced[s].index <= dt].iloc[-1]) * active[s]['shares']
                     for s in active if sliced.get(s) is not None and (sliced[s].index <= dt).sum() >= 1)
            records.append({'date': dt, 'equity': cash + pv})

            for sig in strategy.run_date(dt, queue):
                sym, dir_ = sig.symbol, sig.data["direction"]
                if dir_ == "buy" and sym not in open_trades:
                    ep = _get_close(market_data, sym, dt, strategy)
                    if not ep: continue
                    while cash < POSITION_SIZE and active:
                        def key(item):
                            s, p = item
                            cv = float(sliced[s]["close"].loc[sliced[s].index <= dt].iloc[-1]) * p['shares']
                            return ((cv - p['cost']) / p['cost'],
                                    (dt.date() - _ensure_utc(p['entry_date']).date()).days)
                        w = min(active.items(), key=key)[0]
                        p = active[w]
                        xp = float(sliced[w]["close"].loc[sliced[w].index <= dt].iloc[-1])
                        cash += p['cost'] + (xp - p['entry_price']) * p['shares']
                        if w in open_trades:
                            t = open_trades.pop(w); t.close(dt, xp, "rebal")
                        del active[w]
                    if cash < POSITION_SIZE: continue
                    sh = POSITION_SIZE / ep
                    active[sym] = {'shares': sh, 'cost': POSITION_SIZE, 'entry_price': ep, 'entry_date': dt}
                    cash -= POSITION_SIZE
                    t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=sig.data.get("reason",""))
                    open_trades[sym] = t; all_trades.append(t)
                elif dir_ == "sell" and sym in open_trades:
                    xp = _get_close(market_data, sym, dt, strategy)
                    if not xp: continue
                    t = open_trades.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                    if sym in active:
                        p = active.pop(sym)
                        cash += POSITION_SIZE + (xp - t.entry_price) * p['shares']

        for sym, t in list(open_trades.items()):
            xp = _get_close(market_data, sym, self.end, strategy)
            if xp:
                t.close(self.end, xp, "end")
                if sym in active:
                    p = active.pop(sym)
                    cash += POSITION_SIZE + (xp - t.entry_price) * p['shares']

        if records:
            records[-1] = {'date': records[-1]['date'], 'equity': cash}
        equity = pd.Series([r['equity'] for r in records])
        closed = [t for t in all_trades if t.is_closed]
        return self._metrics(closed, equity)

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
                'wr':wr*100,'plr':plr,'spm':spm,'n':len(closed),
                'equity': equity}

    def run_all(self, label):
        m = self.run()
        e = m.get('equity')
        print(f"\n  【{label}】")
        print(f"    总收益 {m['tr']:>+6.1f}%  年化 {m['ann']:>+6.1f}%  回撤 {m['mdd']:>5.1f}%  夏普 {m['sharpe']:>5.2f}  胜率 {m['wr']:>5.1f}%  盈亏比 {m['plr']:>5.2f}  月均 {m['spm']:>4.1f}信号  n={m['n']}")
        return m

# ── OOS对比 ─────────────────────────────────────────────────────────
print("="*65)
print("  OOS 对比 (2024-2026)")
print("="*65)

base_oos = QuickEngine(BASE_CFG, OOS_START, OOS_END, us_stocks)
sharpe_oos = QuickEngine(SHARPE_CFG, OOS_START, OOS_END, us_stocks)
m1 = base_oos.run_all("基线参数")
m2 = sharpe_oos.run_all("夏普优先参数")

# ── 全量验证 ───────────────────────────────────────────────────────
print("\n" + "="*65)
print("  全量验证 (2020-2026)")
print("="*65)

base_full = QuickEngine(BASE_CFG, FULL_START, FULL_END, us_stocks)
sharpe_full = QuickEngine(SHARPE_CFG, FULL_START, FULL_END, us_stocks)
m3 = base_full.run_all("基线参数")
m4 = sharpe_full.run_all("夏普优先参数")

# ── SPY对比 ────────────────────────────────────────────────────────
import pickle
from pathlib import Path
spy_df = pickle.load(open(Path("data/cache/SPY.pkl"), 'rb'))
spy_df.index = spy_df.index.tz_localize(None)

for label, start, end in [("OOS 2024-2026", OOS_START, OOS_END), ("全量 2020-2026", FULL_START, FULL_END)]:
    mask = (spy_df.index >= start.replace(tzinfo=None)) & (spy_df.index <= end.replace(tzinfo=None))
    if mask.sum() >= 2:
        spy_ret = (float(spy_df['close'][mask].iloc[-1]) / float(spy_df['close'][mask].iloc[0]) - 1) * 100
        print(f"\n  SPY {label}: {spy_ret:+.1f}%")

# ── 保存结果 ────────────────────────────────────────────────────────
out = {'base_oos': {k:v for k,v in m1.items() if k!='equity'},
       'sharpe_oos': {k:v for k,v in m2.items() if k!='equity'},
       'base_full': {k:v for k,v in m3.items() if k!='equity'},
       'sharpe_full': {k:v for k,v in m4.items() if k!='equity'}}
with open('/tmp/sharpe_result.json','w') as f:
    json.dump(out, f, indent=2, default=str)
print("\n  已保存: /tmp/sharpe_result.json")
