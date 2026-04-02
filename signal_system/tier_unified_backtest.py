"""
tier_unified_backtest.py — 统一回测：三层同时运行，按层级分配仓位
仓位分配：A级 ×2.0，C级 ×1.0，D级 ×0.5
分别追踪每个层级的独立净值曲线
"""
import sys, yaml, re, json
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

POS_BASE = 2000
INITIAL_CAPITAL = 50000.0
YRS = (END_FULL - START_FULL).days / 365.25

# 仓位倍数
POS_MULT = {'A级': 2.0, 'C级': 1.0, 'D级': 0.5}

# 各层级初始资金分配（按权重）
# A级分配50%，C级30%，D级20%（资金按层级分配）
INITIAL_ALLOC = {'A级': INITIAL_CAPITAL * 0.50, 'C级': INITIAL_CAPITAL * 0.30, 'D级': INITIAL_CAPITAL * 0.20}

# 追踪各层级独立净值
tier_state = {}
for tier in ['A级', 'C级', 'D级']:
    tier_state[tier] = {
        'cash': INITIAL_ALLOC[tier],
        'active': {},       # symbol -> {shares, cost, entry_price}
        'open_trades': {}, # symbol -> Trade
        'all_trades': [],
        'daily': [],       # {date, equity, pos_value}
    }

cfg = config['strategies']['v_weinstein_adx'].copy()
cfg['_strategy_id'] = 'v_weinstein_adx'
strategy_cls = get_strategy('v_weinstein_adx')
strategy = strategy_cls(cfg, md)
queue = EventQueue()

print(f"统一回测: {len(days)} 个交易日, {YRS:.1f}年")
print(f"初始分配: A级${INITIAL_ALLOC['A级']:.0f}, C级${INITIAL_ALLOC['C级']:.0f}, D级${INITIAL_ALLOC['D级']:.0f}\n")

for date in days:
    dt = date.to_pydatetime()
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)

    # 记录每日各层级市值
    for tier in ['A级', 'C级', 'D级']:
        pos_value = 0.0
        for sym, pos in list(tier_state[tier]['active'].items()):
            df = sliced.get(sym)
            if df is not None:
                mask = df.index <= dt
                if mask.sum() >= 1:
                    price = float(df["close"][mask].iloc[-1])
                    pos_value += price * pos['shares']
        equity = tier_state[tier]['cash'] + pos_value
        tier_state[tier]['daily'].append({'date': dt, 'equity': equity, 'pos_value': pos_value})

    # 处理信号
    for sig in strategy.run_date(dt, queue):
        sym, dir_ = sig.symbol, sig.data["direction"]
        reason = sig.data.get("reason", "")
        tier = tier_classify(reason)

        if dir_ == "buy":
            # 检查是否已在任何层级的持仓中
            already_open = any(sym in tier_state[t]['active'] for t in ['A级', 'C级', 'D级'])
            if already_open:
                continue

            pos_size = POS_BASE * POS_MULT[tier]
            if tier_state[tier]['cash'] < pos_size:
                continue

            ep = _get_close(md, sym, dt, strategy)
            if not ep: continue

            shares = pos_size / ep
            tier_state[tier]['active'][sym] = {'shares': shares, 'cost': pos_size, 'entry_price': ep}
            tier_state[tier]['cash'] -= pos_size

            t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=reason)
            tier_state[tier]['open_trades'][sym] = t
            tier_state[tier]['all_trades'].append(t)

        elif dir_ == "sell":
            # 在各层级中查找是否持仓
            for t_tier in ['A级', 'C级', 'D级']:
                if sym in tier_state[t_tier]['open_trades']:
                    xp = _get_close(md, sym, dt, strategy)
                    if not xp: continue

                    t = tier_state[t_tier]['open_trades'].pop(sym)
                    t.close(dt, xp, sig.data.get("reason", ""))

                    if sym in tier_state[t_tier]['active']:
                        p2 = tier_state[t_tier]['active'].pop(sym)
                        cash_return = POS_BASE * POS_MULT[t_tier] + (xp - t.entry_price) * p2['shares']
                        tier_state[t_tier]['cash'] += cash_return
                    break

# 强制平仓
for tier in ['A级', 'C级', 'D级']:
    for sym, t in list(tier_state[tier]['open_trades'].items()):
        xp = _get_close(md, sym, END_FULL, strategy)
        if xp:
            t.close(END_FULL, xp, "end")
            if sym in tier_state[tier]['active']:
                p2 = tier_state[tier]['active'].pop(sym)
                cash_return = POS_BASE * POS_MULT[tier] + (xp - t.entry_price) * p2['shares']
                tier_state[tier]['cash'] += cash_return

    # 最后一天记录
    if tier_state[tier]['daily']:
        tier_state[tier]['daily'][-1] = {'date': tier_state[tier]['daily'][-1]['date'], 'pos_value': 0, 'equity': tier_state[tier]['cash']}

# 计算各层级指标
def calc_metrics(tier_name, state):
    daily = state['daily']
    if not daily: return None

    eq_series = pd.Series([d['equity'] for d in daily],
                           index=pd.to_datetime([d['date'] for d in daily]).tz_localize(None))
    closed_trades = [t for t in state['all_trades'] if t.is_closed]

    tr = (eq_series.iloc[-1] / eq_series.iloc[0] - 1) * 100
    ann = (1 + tr/100) ** (1/YRS) - 1
    ann = ann * 100
    cmax = eq_series.cummax()
    dd = (eq_series - cmax) / cmax * 100
    mdd = abs(dd.min())
    dr = eq_series.pct_change().dropna()
    sharpe = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0

    wins = [t for t in closed_trades if t.pnl_pct > 0]
    losses = [t for t in closed_trades if t.pnl_pct <= 0]
    wr = len(wins) / len(closed_trades) * 100 if closed_trades else 0
    aw = np.mean([t.pnl_pct for t in wins]) * 100 if wins else 0
    al = abs(np.mean([t.pnl_pct for t in losses])) * 100 if losses else 0
    plr = aw / al if al > 0 else 0

    return {
        'tr': tr, 'ann': ann, 'mdd': mdd, 'sharpe': sharpe,
        'wr': wr, 'plr': plr, 'aw': aw, 'al': al,
        'n': len(closed_trades), 'equity': eq_series
    }

print("=" * 85)
print(f"  三层分级统一回测 (2016-2026) — 资金池分配制")
print("=" * 85)
print(f"  层级    初始资金   仓位    交易数   胜率    盈亏比   均盈     均亏     总收益    年化    最大回撤  夏普")
print(f"  {'-' * 80}")

results = {}
for tier in ['A级', 'C级', 'D级']:
    m = calc_metrics(tier, tier_state[tier])
    if m:
        results[tier] = m
        print(f"  {tier:<6} ${INITIAL_ALLOC[tier]/1000:.0f}k  ×{POS_MULT[tier]:.1f}   {m['n']:>4d}笔  {m['wr']:>5.1f}%  {m['plr']:>6.2f}  {m['aw']:>+6.1f}%  {m['al']:>-6.1f}%  {m['tr']:>+7.1f}%  {m['ann']:>+6.1f}%  {m['mdd']:>6.1f}%  {m['sharpe']:.2f}")

# 综合计算
all_closed = []
for tier in ['A级', 'C级', 'D级']:
    all_closed.extend([t for t in tier_state[tier]['all_trades'] if t.is_closed])

wins_all = [t for t in all_closed if t.pnl_pct > 0]
losses_all = [t for t in all_closed if t.pnl_pct <= 0]
wr_all = len(wins_all) / len(all_closed) * 100 if all_closed else 0
aw_all = np.mean([t.pnl_pct for t in wins_all]) * 100 if wins_all else 0
al_all = abs(np.mean([t.pnl_pct for t in losses_all])) * 100 if losses_all else 0
plr_all = aw_all / al_all if al_all > 0 else 0

# 综合净值曲线（所有层级资金之和）
combined_daily = {}
for tier in ['A级', 'C级', 'D级']:
    for d in tier_state[tier]['daily']:
        ts = d['date'].timestamp()
        combined_daily[ts] = combined_daily.get(ts, 0) + d['equity']

if combined_daily:
    combined_eq = pd.Series(sorted(combined_daily.values()),
                           index=pd.to_datetime([datetime.fromtimestamp(t) for t in sorted(combined_daily.keys())]).tz_localize(None))
    combined_tr = (combined_eq.iloc[-1] / combined_eq.iloc[0] - 1) * 100
    combined_ann = (1 + combined_tr/100) ** (1/YRS) - 1
    combined_ann = combined_ann * 100
    cmax = combined_eq.cummax()
    dd = (combined_eq - cmax) / cmax * 100
    combined_mdd = abs(dd.min())
    dr = combined_eq.pct_change().dropna()
    combined_sharpe = (dr.mean() * 252) / (dr.std() * np.sqrt(252)) if dr.std() > 0 else 0

    print(f"  {'合计':<6} $50k   --    {len(all_closed):>4d}笔  {wr_all:>5.1f}%  {plr_all:>6.2f}  {aw_all:>+6.1f}%  {al_all:>-6.1f}%  {combined_tr:>+7.1f}%  {combined_ann:>+6.1f}%  {combined_mdd:>6.1f}%  {combined_sharpe:.2f}")

print(f"\n  注: 各层级资金独立分配(A=50%,C=30%,D=20%), 仓位倍数按层级差异")
print(f"      交易互不竞争, 独立运作")
print("Done")

# 保存净值曲线用于绘图
with open('/tmp/tier_combined_eq.json', 'w') as f:
    json.dump({k: v.values.tolist() for k, v in {tier: results[tier]['equity'] for tier in results}.items()}, f)
print("净值曲线已保存")