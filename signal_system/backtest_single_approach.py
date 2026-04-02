"""
backtest_single_approach.py — 单个方案回测（可并行）
用法: uv run python backtest_single_approach.py <approach> <output_json>
approach: baseline | tiered | atr | compound
"""
import sys, yaml, pickle, json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import re
import time as time_module

sys.path.insert(0, '.')

APPROACH = sys.argv[1] if len(sys.argv) > 1 else "baseline"
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/approach_{APPROACH}_result.json"

INITIAL_CAPITAL = 50_000.0
POSITION_SIZE   = 2_000.0
START_FULL = datetime(2016, 1, 1, tzinfo=timezone.utc)
END_FULL   = datetime(2026, 3, 27, tzinfo=timezone.utc)
START_OOS  = datetime(2024, 1, 1, tzinfo=timezone.utc)

def log(msg):
    print(msg, flush=True)

log(f"[{APPROACH}] 启动...")

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

total_days = (END_FULL - START_FULL).days + 300
log(f"[{APPROACH}] 加载数据...")
md = fetch(us_stocks, history_days=total_days, end_date=END_FULL)
if not md: raise RuntimeError("no data")
for bm, syms in [("SPY",["SPY"]),("ASHR",["ASHR"]),("EWT",["EWT"])]:
    if bm not in md:
        d = fetch(syms, history_days=total_days, end_date=END_FULL)
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

# ── 预计算ATR（向量化） ─────────────────────────────────────────────
log(f"[{APPROACH}] 预计算ATR...")
atr_cache = {}
for sym, df in sliced.items():
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    tr[1:] = np.maximum(high[1:] - low[1:],
                 np.maximum(np.abs(high[1:] - close[:-1]),
                            np.abs(low[1:] - close[:-1])))
    period = 14
    alpha = 1.0 / period
    atr = np.zeros(n)
    atr[0] = tr[0]
    for i in range(1, n):
        atr[i] = alpha * tr[i] + (1 - alpha) * atr[i-1]
    atr_cache[sym] = pd.Series(atr, index=df.index)
log(f"[{APPROACH}] ATR预计算完成: {len(atr_cache)} 只")

# SPY
spy_df = pickle.load(open(Path("data/cache/SPY.pkl"), 'rb'))
spy_df.index = spy_df.index.tz_localize(None)
spy_mask = (spy_df.index >= START_FULL.replace(tzinfo=None)) & (spy_df.index <= END_FULL.replace(tzinfo=None))
spy_prices = spy_df['close'][spy_mask]
spy_equity = spy_prices / spy_prices.iloc[0]
spy_equity.index = spy_equity.index.tz_localize(None)

days_full = ref[(ref >= START_FULL) & (ref <= END_FULL)]
days_oos  = ref[(ref >= START_OOS)  & (ref <= END_FULL)]

cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'

# ── ATR查找 ──────────────────────────────────────────────────────────
def get_atr(sym, date):
    atr_series = atr_cache.get(sym)
    if atr_series is None: return None
    idx = atr_series.index
    pos = idx.searchsorted(date)
    pos = min(pos, len(atr_series) - 1)
    pos = max(pos, 0)
    return float(atr_series.iloc[pos])

# ── 信号强度解析 ────────────────────────────────────────────────────
def parse_signal(sig):
    reason = sig.data.get("reason", "")
    adx_m = re.search(r'\[ADX\]\s*([\d.]+)', reason)
    adx_val = float(adx_m.group(1)) if adx_m else 0
    vol_m = re.search(r'\[量能\]\s*([\d.]+)x', reason)
    vol_ratio = float(vol_m.group(1)) if vol_m else 0
    return adx_val, vol_ratio

# ── 回测函数 ─────────────────────────────────────────────────────────
def run_backtest(days, pos_size_base=2000, compound_step=0, compound_cap=4000, atr_mode=False):
    strategy_cls = get_strategy('v_weinstein_adx')
    strategy = strategy_cls(cfg, md)
    queue = EventQueue()

    open_t, all_t = {}, []
    cash = float(INITIAL_CAPITAL)
    active = {}
    records = []
    current_pos_size = float(pos_size_base)
    high_water_mark = float(INITIAL_CAPITAL)
    trailing_state = {}

    for i, date in enumerate(days):
        if i % 500 == 0:
            log(f"[{APPROACH}] 进度 {i}/{len(days)}...")
        dt = date.to_pydatetime()
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

        # 复利仓位更新
        if compound_step > 0:
            pv = sum(float(sliced[sym]["close"].loc[sliced[sym].index <= dt].iloc[-1]) * pos['shares']
                     for sym, pos in active.items() if sliced.get(sym) is not None)
            equity_now = cash + pv
            if equity_now > high_water_mark * (1 + compound_step):
                increment = pos_size_base * 0.25
                new_size = min(current_pos_size + increment, compound_cap)
                if new_size > current_pos_size:
                    current_pos_size = new_size
                    high_water_mark = equity_now

        # 每日持仓
        pv = 0.0
        for sym, pos in list(active.items()):
            df = sliced.get(sym)
            if df is not None:
                mask = df.index <= dt
                if mask.sum() >= 1:
                    pv += float(df["close"][mask].iloc[-1]) * pos['shares']
        equity = cash + pv
        util = pv / equity * 100 if equity > 0 else 0
        records.append({'date': dt, 'cash': cash, 'pos_value': pv, 'equity': equity, 'num_pos': len(active), 'util': util})

        for sig in strategy.run_date(dt, queue):
            sym, dir_ = sig.symbol, sig.data["direction"]
            if dir_ == "buy" and sym not in open_t and sym not in active:
                ep = _get_close(md, sym, dt, strategy)
                if not ep: continue

                if APPROACH in ("tiered", "compound"):
                    adx_val, vol_ratio = parse_signal(sig)
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
                    adx_val, _ = parse_signal(sig)
                    trailing_state[sym] = {
                        'atr': atr_val if atr_val else 0,
                        'is_strong': adx_val > 35,
                        'highest': ep
                    }

                active[sym] = {'shares': shares, 'cost': pos_size, 'entry_price': ep, 'highest_price': ep}
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
                trailing_state.pop(sym, None)

        # ATR止损
        if atr_mode:
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
                stop_mult = 2.0 if state['is_strong'] else 1.0
                atr_val = state['atr']
                if atr_val > 0:
                    ts = pos['highest_price'] * (1 - stop_mult * atr_val / pos['highest_price'])
                    if current_price <= ts:
                        xp = current_price
                        t = open_t.pop(sym)
                        t.close(dt, xp, f"ATR止损 {stop_mult}ATR")
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
    return (pd.Series([r['equity'] for r in records], index=dates),
            pd.Series([r['util'] for r in records], index=dates),
            pd.Series([r['num_pos'] for r in records], index=dates),
            all_t, records)

def compute_metrics(equity_series, all_t, records):
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
        'tr': tr * 100, 'ann': ann * 100, 'mdd': mdd * 100,
        'sharpe': sharpe, 'wr': wr * 100, 'plr': plr,
        'spm': spm, 'n': len(closed), 'avg_util': avg_util, 'avg_pos': avg_pos,
        'final_equity': equity_series.iloc[-1],
        'equity_series': equity_series.index.tolist(),
        'equity_values': equity_series.values.tolist(),
    }

# ── 运行 ─────────────────────────────────────────────────────────────
log(f"[{APPROACH}] 开始全量回测...")
if APPROACH == "baseline":
    eq, ut, ps, trades, rec = run_backtest(days_full)
elif APPROACH == "tiered":
    eq, ut, ps, trades, rec = run_backtest(days_full, pos_size_base=2000)
elif APPROACH == "atr":
    eq, ut, ps, trades, rec = run_backtest(days_full, atr_mode=True)
elif APPROACH == "compound":
    eq, ut, ps, trades, rec = run_backtest(days_full, pos_size_base=2000,
        compound_step=0.20, compound_cap=4000)
else:
    raise ValueError(f"Unknown approach: {APPROACH}")

m = compute_metrics(eq, trades, rec)
log(f"[{APPROACH}] 全量完成: {m['tr']:+.1f}% {m['ann']:+.1f}% {m['mdd']:.1f}% {m['sharpe']:.2f}")

log(f"[{APPROACH}] 开始OOS回测...")
if APPROACH == "baseline":
    eq_o, ut_o, ps_o, trades_o, rec_o = run_backtest(days_oos)
elif APPROACH == "tiered":
    eq_o, ut_o, ps_o, trades_o, rec_o = run_backtest(days_oos, pos_size_base=2000)
elif APPROACH == "atr":
    eq_o, ut_o, ps_o, trades_o, rec_o = run_backtest(days_oos, atr_mode=True)
elif APPROACH == "compound":
    eq_o, ut_o, ps_o, trades_o, rec_o = run_backtest(days_oos, pos_size_base=2000,
        compound_step=0.20, compound_cap=4000)

m_o = compute_metrics(eq_o, trades_o, rec_o)
log(f"[{APPROACH}] OOS完成: {m_o['tr']:+.1f}% {m_o['ann']:+.1f}% {m_o['mdd']:.1f}% {m_o['sharpe']:.2f}")

result = {'full': m, 'oos': m_o, 'approach': APPROACH}
with open(OUTPUT_FILE, 'w') as f:
    json.dump(result, f, indent=2, default=str)
log(f"[{APPROACH}] 结果已保存: {OUTPUT_FILE}")