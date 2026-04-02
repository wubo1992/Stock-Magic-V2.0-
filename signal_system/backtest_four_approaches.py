"""
backtest_four_approaches.py — 四个方向对照实验
方向1: 等权复利模型
方向2: Chandelier Exit (ATR追踪止盈)
方向3: 二次入场（回撤到均线确认）
方向4: 多策略组合（Weinstein + Zanger + RS强势）

使用优化后的 v_weinstein_adx 参数（ADX>25, 追踪15%, 量2.0x）
基准仓位: $2000/笔
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
POSITION_SIZE   = 2_000.0
OOS_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
OOS_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)
FULL_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
FULL_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)


# ════════════════════════════════════════════════════════════════════════
# 基础回测引擎（固定金额）
# ════════════════════════════════════════════════════════════════════════
class BaseEngine:
    WARMUP_DAYS = 300
    MAX_POSITIONS = 30  # 最大持仓上限

    def __init__(self, cfg, symbols, start, end, mode='fixed', **kwargs):
        self.cfg = cfg.copy()
        self.cfg['_strategy_id'] = 'v_weinstein_adx'
        self.symbols = symbols
        self.start = _ensure_utc(start)
        self.end = _ensure_utc(end)
        self.mode = mode  # 'fixed', 'compounding', 'chandelier', 'pullback', 'multi'
        self.pos_size = kwargs.get('pos_size', POSITION_SIZE)
        self.target_positions = kwargs.get('target_positions', 15)  # 等权复利用
        self.chandelier_mult = kwargs.get('chandelier_mult', 3.0)  # Chandelier ATR倍数
        self.pullback_max_pct = kwargs.get('pullback_max_pct', 0.08)  # 回撤8%内

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
        active = {}  # symbol -> {shares, cost, entry_price, entry_date, highest_price, atr_entry}
        records = []
        rebal_count = 0

        # 多策略模式
        if self.mode == 'multi':
            strat_zanger = get_strategy('v_zanger')(self.cfg, md)
            strat_rs = get_strategy('v1_plus')(self.cfg, md)

        for date in days:
            dt = date.to_pydatetime()
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

            # 逐日计算持仓市值
            pv = 0.0
            for sym, pos in active.items():
                df = sliced.get(sym)
                if df is not None:
                    mask = df.index <= dt
                    if mask.sum() >= 1:
                        cur_price = float(df["close"][mask].iloc[-1])
                        pv += cur_price * pos['shares']
            records.append({'date': dt, 'cash': cash, 'pos_value': pv, 'equity': cash + pv, 'num_pos': len(active)})

            # 多策略模式：同时运行三个策略
            if self.mode == 'multi':
                signals = strategy.run_date(dt, queue)
                signals += strat_zanger.run_date(dt, queue)
                signals += strat_rs.run_date(dt, queue)
            else:
                signals = strategy.run_date(dt, queue)

            for sig in signals:
                sym, dir_ = sig.symbol, sig.data["direction"]

                # ── 买入信号 ───────────────────────────────────────
                if dir_ == "buy" and sym not in open_t and sym not in active:
                    ep = _get_close(md, sym, dt, strategy)
                    if not ep: continue

                    # 等权复利：动态计算每笔金额
                    if self.mode == 'compounding':
                        total_equity = cash + pv
                        self.pos_size = total_equity / self.target_positions

                    # 现金不足则跳过（非再平衡，只是等待）
                    if cash < self.pos_size:
                        continue

                    shares = self.pos_size / ep
                    atr = self._get_atr(sliced.get(sym), dt, 14) if self.mode == 'chandelier' else 0

                    active[sym] = {
                        'shares': shares, 'cost': self.pos_size,
                        'entry_price': ep, 'entry_date': dt,
                        'highest_price': ep, 'atr_entry': atr,
                        'in_pullback': False,
                    }
                    cash -= self.pos_size

                    t = Trade(symbol=sym, entry_date=dt, entry_price=ep,
                               entry_reason=sig.data.get("reason",""))
                    open_t[sym] = t; all_t.append(t)

                # ── 卖出信号 ───────────────────────────────────────
                elif dir_ == "sell" and sym in open_t:
                    xp = _get_close(md, sym, dt, strategy)
                    if not xp: continue
                    t = open_t.pop(sym); t.close(dt, xp, sig.data.get("reason",""))
                    if sym in active:
                        p2 = active.pop(sym)
                        cash += self.pos_size + (xp - t.entry_price) * p2['shares']

            # ── 每日持仓状态更新（追踪止盈/止损）────────────────
            if self.mode in ('chandelier', 'pullback', 'fixed'):
                to_close = []
                for sym, pos in list(active.items()):
                    df = sliced.get(sym)
                    if df is None: continue
                    mask = df.index <= dt
                    if mask.sum() < 1: continue

                    cur_price = float(df["close"][mask].iloc[-1])
                    high_price = pos['highest_price']

                    if cur_price > high_price:
                        pos['highest_price'] = cur_price
                        if self.mode == 'chandelier':
                            pos['atr_entry'] = self._get_atr(df.iloc[:mask.sum()], dt, 14)

                    # ── Chandelier Exit ──────────────────────────────
                    if self.mode == 'chandelier':
                        chandelier_exit = pos['highest_price'] - self.chandelier_mult * pos['atr_entry']
                        if cur_price <= chandelier_exit and sym in open_t:
                            to_close.append((sym, cur_price, f"chandelier_exit({self.chandelier_mult}ATR)"))

                    # ── 二次入场检测（回撤到均线企稳）────────────
                    if self.mode == 'pullback':
                        sub_df = df.iloc[:mask.sum()]
                        ema20 = float(sub_df["close"].ewm(span=20, adjust=False).mean().iloc[-1])
                        pullback_pct = (cur_price - ema20) / ema20
                        adx = self._get_adx(sub_df, 14)
                        # 主动止损（固定7%）
                        stop_price = pos['entry_price'] * (1 - 0.07)
                        if cur_price <= stop_price and sym in open_t:
                            to_close.append((sym, cur_price, "stop_loss_7pct"))
                        # 追踪止盈（15%）
                        elif pos['highest_price'] * 0.85 >= cur_price and sym in open_t:
                            to_close.append((sym, cur_price, "trailing_stop_15pct"))

                for sym, xp, reason in to_close:
                    if sym in open_t:
                        t = open_t.pop(sym); t.close(dt, xp, reason)
                    if sym in active:
                        p2 = active.pop(sym)
                        cash += p2['cost'] + (xp - t.entry_price) * p2['shares']
                        rebal_count += 1

        # 强制平仓
        for sym, t in list(open_t.items()):
            xp = _get_close(md, sym, self.end, strategy)
            if xp:
                t.close(self.end, xp, "end")
                if sym in active:
                    p2 = active.pop(sym)
                    cash += self.pos_size + (xp - t.entry_price) * p2['shares']

        if records: records[-1] = {'date': records[-1]['date'], 'cash': cash, 'pos_value': 0, 'equity': cash, 'num_pos': 0}
        equity = pd.Series([r['equity'] for r in records])
        pos_counts = [r['num_pos'] for r in records]
        pos_values = [r['pos_value'] for r in records]
        closed = [t for t in all_t if t.is_closed]
        return self._metrics(closed, equity, pos_counts, rebal_count, pos_values)

    def _get_atr(self, df, dt, period=14):
        """计算指定日期的ATR"""
        if df is None or len(df) < period + 2: return 20.0
        mask = df.index <= dt
        if mask.sum() < period + 2: return 20.0
        sub = df.iloc[:mask.sum()]
        high = sub['high']
        low = sub['low']
        close = sub['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean().iloc[-1]
        return float(atr)

    def _get_adx(self, df, period=14):
        """计算ADX"""
        if df is None or len(df) < period * 3: return 20.0
        high, low, close = df['high'], df['low'], df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        up = high - high.shift()
        dn = low.shift() - low
        plus_dm = ((up > dn) & (up > 0)) * up
        minus_dm = ((dn > up) & (dn > 0)) * dn
        plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, adjust=False).mean().iloc[-1]
        return float(adx)

    def _metrics(self, closed, equity, pos_counts, rebal, pos_values=None):
        if not closed or len(equity) == 0: return {}
        tr = float(equity.iloc[-1] / equity.iloc[0] - 1)
        yrs = (self.end - self.start).days / 365.25
        ann = (1+tr)**(1/yrs)-1 if yrs > 0 else 0
        wins = [t for t in closed if t.pnl_pct > 0]
        losses = [t for t in closed if t.pnl_pct <= 0]
        wr = len(wins)/len(closed) if closed else 0
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
        # 资金利用率 = 持仓市值 / 当前总权益（每日计算后取平均）
        if pos_values and len(pos_values) == len(equity):
            daily_util = [pv / eq * 100 if eq > 0 else 0 for pv, eq in zip(pos_values, equity)]
            avg_util = float(np.mean(daily_util)) if daily_util else 0.0
        else:
            avg_util = avg_pos * self.pos_size / INITIAL_CAPITAL * 100
        return {
            'tr':tr*100,'ann':ann*100,'mdd':mdd*100,'mdd_date':str(mdd_date),
            'sharpe':sharpe,'wr':wr*100,'plr':plr,'spm':spm,'n':len(closed),
            'max_pos':max_pos,'avg_pos':avg_pos,'avg_util':avg_util,
            'rebal':rebal,'equity':equity
        }

    def run_all(self, label):
        m = self.run()
        e = m['equity']
        del m['equity']
        print(f"\n  【{label}】")
        print(f"    总收益 {m['tr']:>+6.1f}%  年化 {m['ann']:>+6.1f}%  "
              f"回撤 {m['mdd']:>5.1f}%  夏普 {m['sharpe']:>5.2f}")
        print(f"    胜率 {m['wr']:>5.1f}%  盈亏比 {m['plr']:>5.2f}  "
              f"月均 {m['spm']:>4.1f}信号  n={m['n']}")
        print(f"    平均持仓 {m['avg_pos']:.1f}股  平均资金利用 {m['avg_util']:.0f}%")
        return m, e


# ════════════════════════════════════════════════════════════════════════
# 主实验
# ════════════════════════════════════════════════════════════════════════
cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'

# ── OOS 实验 ──────────────────────────────────────────────────────────
print("="*72)
print("  【OOS 2024-2026】")
print("="*72)

configs = [
    ("基准 ($2000固定)",          "fixed",     {}),
    ("方向1: 等权复利",          "compounding", {'target_positions': 20}),
    ("方向2: Chandelier Exit",   "chandelier", {'chandelier_mult': 3.0}),
    ("方向3: 二次入场(均线)",     "pullback",   {}),
    ("方向4: 多策略组合",         "multi",      {}),
]

oos_results = {}
for label, mode, kw in configs:
    m, _ = BaseEngine(cfg, us_stocks, OOS_START, OOS_END, mode, **kw).run_all(label)
    oos_results[label] = m

# ── 全量实验 ──────────────────────────────────────────────────────────
print("\n" + "="*72)
print("  【全量 2020-2026】")
print("="*72)

full_results = {}
for label, mode, kw in configs:
    m, _ = BaseEngine(cfg, us_stocks, FULL_START, FULL_END, mode, **kw).run_all(label)
    full_results[label] = m

# ── 汇总 ──────────────────────────────────────────────────────────────
print("\n" + "="*72)
print("  【汇总】")
print("="*72)

short_labels = {c[0]: c[0] for c in configs}

print(f"\n  {'方案':<26} | {'年化':>7} {'回撤':>6} {'夏普':>6} | {'平均利用':>8} {'胜率':>6} | {'vs基准年化':>10}")
print(f"  {'-'*60}")

# 以基准为参照
base_full = full_results[configs[0][0]]
for label, _, _ in configs:
    m = full_results[label]
    diff = m['ann'] - base_full['ann']
    print(f"  {label:<26} | {m['ann']:>+6.1f}% {m['mdd']:>5.1f}% {m['sharpe']:>6.2f} | "
          f"{m['avg_util']:>7.0f}% {m['wr']:>5.1f}% | {diff:>+9.1f}%")

# SPY对比
import pickle
from pathlib import Path
spy_df = pickle.load(open(Path("data/cache/SPY.pkl"), 'rb'))
spy_df.index = spy_df.index.tz_localize(None)
for lbl, start, end in [("OOS 2024-2026", OOS_START, OOS_END), ("全量2020-2026", FULL_START, FULL_END)]:
    mask = (spy_df.index >= start.replace(tzinfo=None)) & (spy_df.index <= end.replace(tzinfo=None))
    if mask.sum() >= 2:
        spy_ret = (float(spy_df['close'][mask].iloc[-1]) / float(spy_df['close'][mask].iloc[0]) - 1) * 100
        print(f"  {'SPY ' + lbl:<26} |       —       —     —   |        —      —   | {spy_ret:>+9.1f}%")

# 保存
with open('/tmp/four_approaches_result.json', 'w') as f:
    json.dump({'oos': oos_results, 'full': full_results}, f, indent=2, default=str)
print("\n  已保存: /tmp/four_approaches_result.json")
