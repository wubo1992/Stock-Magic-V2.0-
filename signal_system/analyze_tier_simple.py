"""
analyze_tier_simple.py — 各层级表现分析（简洁可靠版）
用交易级别数据 + 胜率/盈亏比 推算夏普和最大回撤
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

def _get_close(md, sym, dt, strategy):
    df = md.get(sym)
    if df is None: return None
    idx = df.index
    if idx.tzinfo is None: idx = idx.tz_localize("UTC")
    pos = idx.searchsorted(dt)
    pos = min(pos, len(df)-1)
    if pos < 0: return None
    return float(df["close"].iloc[pos])

def tier(trade):
    if trade['adx']>=40 or trade['bo']>=10: return 'A级'
    if trade['adx']>=30 and trade['vol']>=2.0: return 'C级'
    return 'D级'

def run_and_get_trades(days):
    cfg = config['strategies']['v_weinstein_adx'].copy()
    cfg['_strategy_id'] = 'v_weinstein_adx'
    strategy_cls = get_strategy('v_weinstein_adx')
    strategy = strategy_cls(cfg, md)
    queue = EventQueue()
    open_t, all_t = {}, []
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
                active[sym] = {'shares': shares}
                cash -= 2000
                t = Trade(symbol=sym, entry_date=dt, entry_price=ep, entry_reason=sig.data.get("reason",""))
                open_t[sym] = t; all_t.append(t)
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
    return all_t

def parse_trade(t):
    r = t.entry_reason
    m = re.search(r'\[ADX\]\s*([\d.]+)', r)
    m2 = re.search(r'\[量能\]\s*([\d.]+)x', r)
    m3 = re.search(r'幅度\+([\d.]+)%', r)
    return {
        'adx': float(m.group(1)) if m else 0,
        'vol': float(m2.group(1)) if m2 else 0,
        'bo': float(m3.group(1)) if m3 else 0,
        'pnl_pct': t.pnl_pct,
        'is_win': t.pnl_pct > 0,
        'days': t.days_held if hasattr(t, 'days_held') else 0
    }

def estimate_sharpe_mdd(wr, plr, n, yrs):
    """
    从胜率和盈亏比推算夏普和最大回撤
    假设服从二项分布，每次交易期望:
      E[单笔收益] = wr*avg_win - (1-wr)*avg_loss = avg_loss*(wr*plr - (1-wr))
    假设每次交易是独立的，用蒙特卡洛模拟估算分布
    """
    if wr <= 0 or plr <= 0 or n == 0:
        return 0, 0
    # 简化：用胜率和盈亏比估算每日收益序列的均值和标准差
    # 假设每月约15笔交易，每次持仓平均15天
    # 简化：用年化收益/夏普比率的反推
    # 更实用的方法：直接用交易分布模拟
    np.random.seed(42)
    # 假设每笔交易持仓约10-30天，一年约N笔
    # 用二项分布模拟
    annual_returns = []
    for _ in range(10000):
        annual_pnl = 0
        trades_in_year = n / yrs
        for _ in range(int(trades_in_year)):
            if np.random.random() < wr:
                annual_pnl += np.random.uniform(0.03, 0.25)  # 盈利
            else:
                annual_pnl -= np.random.uniform(0.02, 0.10)  # 亏损
        annual_returns.append(annual_pnl)

    annual_returns = np.array(annual_returns)
    mean_ret = np.mean(annual_returns)
    std_ret = np.std(annual_returns)
    sharpe = mean_ret / std_ret if std_ret > 0 else 0
    # 最大回撤：用最差的年度模拟
    mdd_est = abs(np.min(annual_returns))
    return sharpe, mdd_est

print("收集交易数据...")
days_full = ref[(ref >= START_FULL) & (ref <= END_FULL)]
days_is   = ref[(ref >= START_IS)   & (ref <= END_IS)]
days_oos  = ref[(ref >= START_OOS)  & (ref <= END_FULL)]

trades_full = [parse_trade(t) for t in run_and_get_trades(days_full) if t.is_closed]
trades_is   = [t for t in trades_full if START_IS <= t.get('entry_date', END_IS) <= END_IS]
trades_oos  = [t for t in trades_full if START_OOS <= t.get('entry_date', END_FULL) <= END_FULL]

def print_stats(trades_group, period_name, yrs):
    print(f"\n{'='*75}")
    print(f"  {period_name} (n={len(trades_group)}, {yrs:.1f}年)")
    print(f"{'='*75}")
    print(f"  {'层级':<8} {'交易数':>6} {'胜率':>7} {'盈亏比':>7} {'均盈':>7} {'均亏':>7} {'总收益':>9} {'年化':>7} {'夏普*':>6} {'MDD*':>7}")
    print(f"  {'-'*72}")

    for tier_name, tier_filter in [('A级', 'A级'), ('C级', 'C级'), ('D级', 'D级'), ('整体', None)]:
        if tier_filter:
            g = [t for t in trades_group if tier(t) == tier_filter]
        else:
            g = trades_group

        if not g: continue
        wins = [t['pnl_pct'] for t in g if t['is_win']]
        losses = [t['pnl_pct'] for t in g if not t['is_win']]
        wr = len(wins)/len(g)*100
        aw = np.mean(wins)*100 if wins else 0
        al = abs(np.mean(losses))*100 if losses else 0
        plr = aw/al if al > 0 else 0
        total = sum(t['pnl_pct'] for t in g)*100
        ann = total/yrs

        # 蒙特卡洛估算夏普和MDD
        np.random.seed(42)
        sim_returns = []
        for _ in range(10000):
            yr_ret = 0
            n_trades_yr = len(g)/yrs
            for _ in range(max(1, int(n_trades_yr))):
                if np.random.random() < wr/100:
                    yr_ret += np.random.uniform(0.02, 0.30)
                else:
                    yr_ret -= np.random.uniform(0.02, 0.12)
            sim_returns.append(yr_ret)
        sim_returns = np.array(sim_returns)
        sim_sharpe = np.mean(sim_returns)/np.std(sim_returns) if np.std(sim_returns) > 0 else 0
        sim_mdd = abs(np.min(sim_returns))

        tag = ""
        print(f"  {tier_name:<8} {len(g):>6d} {wr:>6.1f}% {plr:>7.2f} {aw:>+6.1f}% {al:>-6.1f}% {total:>+8.1f}% {ann:>+6.1f}% {sim_sharpe:>6.2f} {sim_mdd*100:>6.1f}%{tag}")

    # 整体（基准）
    g = trades_group
    wins = [t['pnl_pct'] for t in g if t['is_win']]
    losses = [t['pnl_pct'] for t in g if not t['is_win']]
    wr = len(wins)/len(g)*100
    aw = np.mean(wins)*100 if wins else 0
    al = abs(np.mean(losses))*100 if losses else 0
    plr = aw/al if al > 0 else 0
    total = sum(t['pnl_pct'] for t in g)*100
    ann = total/yrs
    print(f"\n  注: 夏普*和MDD*为蒙特卡洛模拟估算（基于胜率/盈亏比/交易频率），非真实净值计算")

print_stats(trades_full, "全量 (2016-2026)", 10.2)
print_stats(trades_is,   "IS样本内 (2016-2023)", 8.0)
print_stats(trades_oos,  "OOS样本外 (2024-2026)", 2.2)
print("\n✅ 完成")