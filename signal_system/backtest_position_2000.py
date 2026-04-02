"""
backtest_position_2000.py — 仓位测试：$2000/笔 vs $1500/笔
使用优化后的 v_weinstein_adx 参数（ADX>25, 追踪15%, 量2.0x）
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
POSITION_SIZES = [1500, 2000, 2500, 3000]  # 测试多个仓位

OOS_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
OOS_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)
FULL_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
FULL_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)


class QuickEngine:
    WARMUP_DAYS = 300

    def __init__(self, cfg, symbols, start, end, pos_size):
        self.cfg = cfg
        self.symbols = symbols
        self.start = _ensure_utc(start)
        self.end = _ensure_utc(end)
        self.pos_size = pos_size

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
        rebal_count = 0

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
            records.append({'date': dt, 'equity': cash + pv, 'num_pos': len(active)})

            for sig in strategy.run_date(dt, queue):
                sym, dir_ = sig.symbol, sig.data["direction"]
                if dir_ == "buy" and sym not in open_t:
                    ep = _get_close(md, sym, dt, strategy)
                    if not ep: continue
                    while cash < self.pos_size and active:
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
                        rebal_count += 1
                    if cash < self.pos_size: continue
                    sh = self.pos_size / ep
                    active[sym] = {'shares': sh, 'cost': self.pos_size, 'entry_price': ep, 'entry_date': dt}
                    cash -= self.pos_size
                    t = Trade(symbol=sym, entry_date=dt, entry_price=ep,
                               entry_reason=sig.data.get("reason",""))
                    open_t[sym] = t; all_t.append(t)
                elif dir_ == "sell" and sym in open_t:
                    xp = _get_close(md, sym, dt, strategy)
                    if not xp: continue
                    t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                    if sym in active:
                        p2 = active.pop(sym)
                        cash += self.pos_size + (xp - t.entry_price) * p2['shares']

        for sym, t in list(open_t.items()):
            xp = _get_close(md, sym, self.end, strategy)
            if xp:
                t.close(self.end, xp, "end")
                if sym in active:
                    p2 = active.pop(sym)
                    cash += self.pos_size + (xp - t.entry_price) * p2['shares']

        if records: records[-1] = {'date': records[-1]['date'], 'equity': cash, 'num_pos': 0}
        equity = pd.Series([r['equity'] for r in records])
        pos_counts = [r['num_pos'] for r in records]
        closed = [t for t in all_t if t.is_closed]
        return self._metrics(closed, equity, pos_counts, rebal_count)

    def _metrics(self, closed, equity, pos_counts, rebal):
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
        mdd_idx = dd.idxmin()
        mdd_date = mdd_idx.date() if hasattr(mdd_idx, 'date') else str(mdd_idx)
        dr = equity.pct_change().dropna()
        sharpe = (dr.mean()*252)/(dr.std()*np.sqrt(252)) if dr.std()>0 else 0
        monthly = defaultdict(int)
        for t in closed: monthly[t.entry_date.strftime("%Y-%m")[:7]] += 1
        spm = np.mean(list(monthly.values())) if monthly else 0
        max_pos = max(pos_counts) if pos_counts else 0
        avg_pos = float(np.mean(pos_counts)) if pos_counts else 0.0
        avg_util = avg_pos * self.pos_size / INITIAL_CAPITAL * 100
        max_util = max_pos * self.pos_size / INITIAL_CAPITAL * 100
        return {
            'tr':tr*100,'ann':ann*100,'mdd':mdd*100,'mdd_date':mdd_date,
            'sharpe':sharpe,'wr':wr*100,'plr':plr,
            'spm':spm,'n':len(closed),
            'max_pos':max_pos,'avg_pos':avg_pos,
            'max_util':max_util,'avg_util':avg_util,
            'rebal':rebal,'equity':equity
        }

    def run_all(self, label):
        m = self.run()
        e = m['equity']
        del m['equity']
        print(f"\n  【{label}】")
        print(f"    总收益 {m['tr']:>+6.1f}%  年化 {m['ann']:>+6.1f}%  "
              f"回撤 {m['mdd']:>5.1f}%({m['mdd_date']})  夏普 {m['sharpe']:>5.2f}")
        print(f"    胜率 {m['wr']:>5.1f}%  盈亏比 {m['plr']:>5.2f}  "
              f"月均 {m['spm']:>4.1f}信号  n={m['n']}")
        print(f"    峰值持仓 {m['max_pos']}股  平均持仓 {m['avg_pos']:.1f}股  "
              f"资金峰值{m['max_util']:.0f}%  均值{m['avg_util']:.0f}%  再平衡{m['rebal']}次")
        return m, e


cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'

print("="*70)
print("  OOS 对比 (2024-2026) — 不同仓位")
print("="*70)

oos_results = {}
for ps in POSITION_SIZES:
    m, _ = QuickEngine(cfg, us_stocks, OOS_START, OOS_END, ps).run_all(f"$ {ps}/笔")
    oos_results[ps] = m

print("\n" + "="*70)
print("  全量验证 (2020-2026) — 不同仓位")
print("="*70)

full_results = {}
for ps in POSITION_SIZES:
    m, _ = QuickEngine(cfg, us_stocks, FULL_START, FULL_END, ps).run_all(f"$ {ps}/笔")
    full_results[ps] = m

# 汇总表格
print("\n" + "="*70)
print("  汇总")
print("="*70)

print(f"\n  {'仓位':>8} | {'年化':>7} {'回撤':>6} {'夏普':>6} | {'平均持仓':>8} {'峰值%':>6} | {'再平衡':>6}")
print(f"  {'-'*60}")
for ps in POSITION_SIZES:
    m = full_results[ps]
    print(f"  ${ps:>6}/笔 | {m['ann']:>+6.1f}% {m['mdd']:>5.1f}% {m['sharpe']:>6.2f} | "
          f"{m['avg_pos']:>7.1f}股 {m['max_util']:>5.0f}% | {m['rebal']:>6}次")

# 保存
with open('/tmp/position_study.json', 'w') as f:
    json.dump({str(k): v for k, v in full_results.items()}, f, indent=2, default=str)
print("\n  已保存: /tmp/position_study.json")
