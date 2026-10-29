"""
watchlist/recovery_analysis.py — 跌破/恢复分析

从 added_date 起追踪每只 watchlist 股票：
- 是否曾经跌破 EMA10（close < EMA10）
- 今天的状态：
    1. Reversal Extension  → 仍 close < EMA10（下方延伸）
    2. EMA Crossback        → close >= EMA10（已涨回上方）

附带指标：
- 首次跌破日期
- 历史最深跌幅（vs EMA10 的 %）
- 今天 vs EMA10 的偏移（%）
- 累计跌破天数
- 距最近一次上穿的天数（crossback 组）
- 连续跌破天数（extension 组）
"""

from datetime import datetime, timezone

import pandas as pd

from data.fetcher import fetch
from watchlist.manager import load_watchlist


def analyze_one(df: pd.DataFrame, added_date_str: str) -> dict | None:
    """从 added_date 起分析单只股票的 EMA10 跌破/恢复状态。"""
    if df is None or len(df) < 22:
        return None

    closes = df["close"].astype(float)
    ema10 = closes.ewm(span=10, adjust=False).mean()

    # added_date 时区对齐
    added_date = pd.to_datetime(added_date_str)
    if df.index.tz is not None and added_date.tzinfo is None:
        added_date = added_date.tz_localize("UTC")

    mask = df.index >= added_date
    if mask.any():
        idx = df.index[mask]
        slice_close = closes.loc[idx]
        slice_ema10 = ema10.loc[idx]
    else:
        # 极端情况：added_date 晚于所有数据 → 用最近 N 天
        idx = df.index[-22:]
        slice_close = closes.loc[idx]
        slice_ema10 = ema10.loc[idx]

    below_mask = slice_close < slice_ema10
    has_dipped = bool(below_mask.any())

    today_close = float(closes.iloc[-1])
    today_ema10 = float(ema10.iloc[-1])
    today_vs_ema10_pct = (today_close - today_ema10) / today_ema10 * 100 if today_ema10 else 0.0

    base = {
        "added_date": added_date_str,
        "today_close": today_close,
        "today_ema10": today_ema10,
        "today_vs_ema10_pct": today_vs_ema10_pct,
        "first_dip_date": None,
        "deepest_dip_pct": None,
        "deepest_dip_date": None,
        "total_days_below": int(below_mask.sum()) if has_dipped else 0,
        "crossback_date": None,           # 最近一次从下穿上穿
        "days_since_crossback": None,
        "consecutive_below_days": 0,
    }

    if not has_dipped:
        base["status"] = "never_dipped"
        return base

    # 有跌破 → 计算指标
    below_df = pd.DataFrame({
        "close": slice_close[below_mask],
        "ema10": slice_ema10[below_mask],
    })
    below_df["deviation_pct"] = (below_df["close"] - below_df["ema10"]) / below_df["ema10"] * 100

    first_dip_date = str(below_df.index[0].date()) if hasattr(below_df.index[0], "date") else str(below_df.index[0])[:10]
    deepest_idx = below_df["deviation_pct"].idxmin()
    deepest_pct = float(below_df["deviation_pct"].min())
    deepest_date = str(deepest_idx.date()) if hasattr(deepest_idx, "date") else str(deepest_idx)[:10]

    base["first_dip_date"] = first_dip_date
    base["deepest_dip_pct"] = deepest_pct
    base["deepest_dip_date"] = deepest_date

    # 当前是否站回 EMA10
    today_above = today_close >= today_ema10

    # 连续跌破天数（从今天往回数）
    consecutive = 0
    for i in range(len(slice_close) - 1, -1, -1):
        if slice_close.iloc[i] < slice_ema10.iloc[i]:
            consecutive += 1
        else:
            break
    base["consecutive_below_days"] = consecutive

    # 找最近一次上穿 EMA10 的日期（crossback 组）
    if today_above:
        # 从今天往回数，找到上一个 "below → above" 的转换点
        last_below_idx = None
        for i in range(len(slice_close) - 1, -1, -1):
            if slice_close.iloc[i] < slice_ema10.iloc[i]:
                last_below_idx = i
                break
        if last_below_idx is not None and last_below_idx + 1 < len(slice_close):
            crossback_idx = slice_close.index[last_below_idx + 1]
            base["crossback_date"] = (
                str(crossback_idx.date()) if hasattr(crossback_idx, "date") else str(crossback_idx)[:10]
            )
            today_ts = pd.Timestamp(df.index[-1])
            if df.index.tz is not None and crossback_idx.tzinfo is None:
                crossback_idx = crossback_idx.tz_localize("UTC")
            delta = today_ts - crossback_idx
            base["days_since_crossback"] = delta.days
        base["status"] = "ema_crossback"
    else:
        base["status"] = "reversal_extension"

    return base


def print_report(results: dict[str, dict]) -> None:
    symbols = list(results.keys())

    crossback = [s for s in symbols if results[s].get("status") == "ema_crossback"]
    extension = [s for s in symbols if results[s].get("status") == "reversal_extension"]
    never = [s for s in symbols if results[s].get("status") == "never_dipped"]

    print()
    print("=" * 110)
    print(f"Watchlist 跌破/恢复分析（共 {len(symbols)} 只，从 added_date 起追踪）")
    print("=" * 110)

    print()
    print("📋 分组：")
    print(f"  • ✅ EMA Crossback（跌破后已涨回 EMA10 上方）: {len(crossback)} 只")
    print(f"  • 🔻 Reversal Extension（跌破后仍在 EMA10 下方）: {len(extension)} 只")
    print(f"  • ✓  从未跌破（一直在 EMA10 上方）: {len(never)} 只")

    # EMA Crossback 表（按距今多久上穿排序）
    if crossback:
        print()
        print(f"✅ EMA Crossback 组（按 days_since_crossback 升序 = 最新一次上穿）：")
        print(f"{'股票':<7} {'现价':<9} {'EMA10':<8} {'vs%':<8} {'首次深':<12} {'最深%':<8} {'最深日':<12} {'穿回日':<12} {'距今':<5}")
        print("-" * 110)
        crossback_sorted = sorted(
            crossback,
            key=lambda s: (results[s].get("days_since_crossback") is None, results[s].get("days_since_crossback", 0)),
        )
        for s in crossback_sorted:
            r = results[s]
            print(
                f"{s:<7} ${r['today_close']:<8.2f} {r['today_ema10']:<8.2f} "
                f"{r['today_vs_ema10_pct']:+5.1f}%  "
                f"{r['first_dip_date']:<12} {r['deepest_dip_pct']:+5.1f}%  "
                f"{r['deepest_dip_date']:<12} "
                f"{r['crossback_date']:<12} {r['days_since_crossback']}天"
            )

    # Reversal Extension 表（按今天 vs EMA10 排序，最负的在上）
    if extension:
        print()
        print(f"🔻 Reversal Extension 组（按 today_vs_ema10_pct 升序 = 跌得最深的在上）：")
        print(f"{'股票':<7} {'现价':<9} {'EMA10':<8} {'vs%':<8} {'首次深':<12} {'最深%':<8} {'最深日':<12} {'累计跌破':<8} {'连续':<5}")
        print("-" * 110)
        ext_sorted = sorted(extension, key=lambda s: results[s]["today_vs_ema10_pct"])
        for s in ext_sorted:
            r = results[s]
            print(
                f"{s:<7} ${r['today_close']:<8.2f} {r['today_ema10']:<8.2f} "
                f"{r['today_vs_ema10_pct']:+5.1f}%  "
                f"{r['first_dip_date']:<12} {r['deepest_dip_pct']:+5.1f}%  "
                f"{r['deepest_dip_date']:<12} "
                f"{r['total_days_below']:<8}天 {r['consecutive_below_days']:<5}天"
            )

    # 从未跌破表
    if never:
        print()
        print(f"✓ 从未跌破 EMA10（{len(never)} 只）：")
        # 按今天 vs EMA10 倒序
        never_sorted = sorted(never, key=lambda s: -results[s]["today_vs_ema10_pct"])
        print(f"  {', '.join(never_sorted)}")

    print("=" * 110)


def main() -> None:
    wl = load_watchlist()
    symbols = list(wl["stocks"].keys())
    print(f"加载 watchlist：{len(symbols)} 只")

    market = fetch(symbols, history_days=180, live_mode=False)
    print(f"获取市场数据：{len(market)} 只")

    results: dict[str, dict] = {}
    for sym, entry in wl["stocks"].items():
        df = market.get(sym)
        added = entry.get("added_date")
        r = analyze_one(df, added)
        if r is not None:
            r["appearances"] = entry.get("appearances", 1)
            results[sym] = r

    print_report(results)


if __name__ == "__main__":
    main()