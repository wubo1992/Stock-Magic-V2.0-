"""
watchlist/analyzer.py — 观察清单分析器

对 watchlist 中的每只股票，计算以下状态：
1. EMA10 crossback（重新站上 EMA10）
   - 昨天收 < EMA10（曾跌破），今天收 >= EMA10（涨回来）→ 动量恢复信号
   - 今天是 crossback 状态的，标记为 ✅ 收回

2. Reversal Extension（按 Oliver Kell "Cycle of Price Action" 原始定义）
   - Kell 框架第一阶段——底部阶段（capitulation / 心态转变信号）
   - "Price becomes extended below the 10 EMA into a higher-timeframe support level"
   - 价格大幅延伸到 10 EMA 下方，中间有"空气"
   - 量化：(close - EMA10) / EMA10 × 100（负值 = 在 EMA10 下方延伸）
   - ≤ -5%  warning（轻度延伸，潜在反转区）
   - ≤ -10% strong（深度延伸，capitulation 区）

3. Peak tracking + pullback（用于"突破-回踩-再突破"策略）
   - peak_price_since_added：从加入 watchlist 起到今天的历史最高价
   - pullback_from_peak_pct：从峰值回撤的百分比
   - 策略意图：等回踩到位（通常 -10%~-25%）后再次突破时买入

4. Historical dip+recovery analysis（自加入 watchlist 起）
   - 自 added_date 起追踪：是否曾跌破 EMA10 → 当前是否已站回
   - 分三组：
     * "ema_crossback"        跌破后已涨回 EMA10 上方
     * "reversal_extension"   跌破后仍在 EMA10 下方（Kell 底部阶段）
     * "never_dipped"         自加入后从未跌破
   - 关键指标：
     * price_change_since_added_pct   现价相对加入日收盘的累计变化
     * deepest_dip_date / deepest_dip_pct / deepest_dip_close  历史最深跌破
     * crossback_date / crossback_volume_ratio   上穿日及其量比
     * recovery_from_bottom_pct        从最深底部到今天的反弹幅度
     * days_added_to_deepest_dip       加入到最深底的天数
     * days_deepest_dip_to_now         最深底到今天的天数

分析结果示例：
{
  "OABI": {
    "current_price": 3.50,
    "ema10": 3.30,
    "ma20": 3.10,
    "above_ema10": True,
    "ema10_crossback_today": False,
    "reversal_extension_pct": -8.5,
    "is_reversal_extension": True,
    "reversal_extension_alert": "warning",
    "peak_price_since_added": 3.95,
    "pullback_from_peak_pct": -11.4,
    "added_date": "2026-08-18",
    "days_in_watchlist": 3,
    "price_change_pct": -1.1,
    "price_change_since_added_pct": 5.2,
    "close_on_added_date": 3.33,
    "recovery_status": "reversal_extension",
    "first_dip_date": "2026-08-19",
    "deepest_dip_date": "2026-08-19",
    "deepest_dip_pct": -8.5,
    "deepest_dip_close": 3.02,
    "crossback_date": null,
    "crossback_volume_ratio": null,
    "recovery_from_bottom_pct": 15.9,
    "days_added_to_deepest_dip": 1,
    "days_deepest_dip_to_now": 2,
    "available": True,
  }
}
"""

from datetime import date, datetime, timezone

import pandas as pd

from watchlist.manager import load_watchlist, save_watchlist
from data.rs_rating import split_factor_since
from universe.us_market import display_name

# 默认阈值（按 Kell 定义：close 相对 EMA10 向下延伸的百分比）
DEFAULT_REVERSAL_EXTENSION_THRESHOLD_PCT = 5.0
DEFAULT_STRONG_REVERSAL_EXTENSION_THRESHOLD_PCT = 10.0

# 回撤参考阈值（用于状态提示）
PULLBACK_MODERATE_PCT = 10.0   # 回撤 ≥10%：回踩开始，值得关注
PULLBACK_DEEP_PCT = 25.0       # 回撤 ≥25%：深度回踩，可能破位

# Crossback 信号阈值：自加入日起曾跌破 EMA10 → 已涨回 → 且穿回日成交量 ≥ 此倍数均量
# 即"放量穿回"才是信号，纯缩量穿回不触发
DEFAULT_CROSSBACK_SIGNAL_VOLUME_THRESHOLD = 1.0

# Crossback 信号新鲜度阈值：穿回日距今超过此天数视为过期（行情已走完，不再算作新信号）
# 设 7 天 = 一周交易日内的穿回才被视为可行动信号
DEFAULT_MAX_DAYS_SINCE_CROSSBACK = 7


def _compute_indicators(df: pd.DataFrame) -> dict | None:
    """
    从单只股票的日线 DataFrame 计算 EMA10、MA20 和今日状态。
    要求 df 至少有 22 行（MA20 需要 20 天历史 + 今天 + 昨天）。
    """
    if df is None or len(df) < 22:
        return None

    closes = df["close"].astype(float)
    volumes = df["volume"].astype(float)

    ema10 = closes.ewm(span=10, adjust=False).mean()
    ma20 = closes.rolling(window=20).mean()

    today_close = float(closes.iloc[-1])
    yesterday_close = float(closes.iloc[-2])
    today_ema10 = float(ema10.iloc[-1])
    yesterday_ema10 = float(ema10.iloc[-2])
    today_ma20 = float(ma20.iloc[-1])

    avg_vol_20 = float(volumes.iloc[-21:-1].mean())
    today_vol = float(volumes.iloc[-1])
    vol_ratio = today_vol / avg_vol_20 if avg_vol_20 > 0 else 0.0

    return {
        "close": today_close,
        "prev_close": yesterday_close,
        "ema10": today_ema10,
        "prev_ema10": yesterday_ema10,
        "ma20": today_ma20,
        "volume_ratio": vol_ratio,
    }


def _compute_recovery(
    df: pd.DataFrame,
    added_date_str: str | None,
    today_close: float,
    today_ema10: float,
) -> dict:
    """
    从 added_date 起追踪 EMA10 跌破/恢复事件。

    返回字段：
        status                       "ema_crossback" / "reversal_extension" / "never_dipped"
        first_dip_date               第一次跌破 EMA10 的日期
        deepest_dip_date             最深跌破 EMA10 的日期
        deepest_dip_pct              最深跌幅（vs EMA10 的 %，负数）
        deepest_dip_close            最深当天的收盘价
        crossback_date               最近一次从下方上穿 EMA10 的日期（若有）
        crossback_volume_ratio       上穿当天的量比（成交量 / 20日均量）
        price_change_since_added_pct 现价相对加入日收盘的累计变化 %
        close_on_added_date          加入日（最近一根 bar）的收盘价
        recovery_from_bottom_pct     现价相对最深底收盘的反弹 %（仅 extension 组）
        days_added_to_deepest_dip    加入 → 最深底 的天数
        days_deepest_dip_to_now      最深底 → 今天 的天数
    """
    default = {
        "status": "never_dipped",
        "first_dip_date": None,
        "deepest_dip_date": None,
        "deepest_dip_pct": None,
        "deepest_dip_close": None,
        "crossback_date": None,
        "crossback_volume_ratio": None,
        "price_change_since_added_pct": None,
        "close_on_added_date": None,
        "recovery_from_bottom_pct": None,
        "days_added_to_deepest_dip": None,
        "days_deepest_dip_to_now": None,
    }

    if df is None or len(df) < 22 or not added_date_str:
        return default

    closes = df["close"].astype(float)
    volumes = df["volume"].astype(float)
    ema10 = closes.ewm(span=10, adjust=False).mean()
    avg_vol_20 = volumes.rolling(window=20).mean()
    vol_ratio = volumes / avg_vol_20

    added_date = pd.to_datetime(added_date_str)
    if df.index.tz is not None and added_date.tzinfo is None:
        added_date = added_date.tz_localize("UTC")

    mask = df.index >= added_date
    if mask.any():
        idx = df.index[mask]
        close_on_added = float(closes.loc[idx[0]])
        slice_close = closes.loc[idx]
        slice_ema10 = ema10.loc[idx]
        slice_vol_ratio = vol_ratio.loc[idx]
    else:
        # 数据还没覆盖到加入日（含今天刚加入的情况）
        # 不应回退到加入日之前的历史数据——那不属于"自加入起追踪"的范围
        return default

    if close_on_added and close_on_added > 0:
        # 加入日收盘和今天收盘必须落在同一价格基准上，否则反向拆股会让
        # 涨跌幅连方向都反（SLN 实际 -40.7% 曾显示成 +33.8%）
        split_factor = split_factor_since(df, added_date_str)
        if split_factor is None:
            price_change_since_added_pct = None  # 价格数据不可信，宁可不显示
        else:
            base = close_on_added * split_factor
            price_change_since_added_pct = (today_close - base) / base * 100
            close_on_added = base
    else:
        price_change_since_added_pct = None

    below_mask = slice_close < slice_ema10
    has_dipped = bool(below_mask.any())

    result = dict(default)
    result["price_change_since_added_pct"] = price_change_since_added_pct
    result["close_on_added_date"] = close_on_added

    if not has_dipped:
        result["status"] = "never_dipped"
        return result

    # 有跌破 → 计算所有指标
    below_df = pd.DataFrame({
        "close": slice_close[below_mask],
        "ema10": slice_ema10[below_mask],
    })
    below_df["deviation_pct"] = (below_df["close"] - below_df["ema10"]) / below_df["ema10"] * 100

    first_dip_ts = below_df.index[0]
    deepest_ts = below_df["deviation_pct"].idxmin()
    deepest_pct = float(below_df["deviation_pct"].min())
    deepest_close = float(below_df.loc[deepest_ts, "close"])

    result["first_dip_date"] = (
        str(first_dip_ts.date()) if hasattr(first_dip_ts, "date") else str(first_dip_ts)[:10]
    )
    result["deepest_dip_date"] = (
        str(deepest_ts.date()) if hasattr(deepest_ts, "date") else str(deepest_ts)[:10]
    )
    result["deepest_dip_pct"] = deepest_pct
    result["deepest_dip_close"] = deepest_close

    # 时间相关
    today_ts = df.index[-1]
    try:
        result["days_added_to_deepest_dip"] = (deepest_ts - added_date).days
    except Exception:
        result["days_added_to_deepest_dip"] = None
    try:
        result["days_deepest_dip_to_now"] = (today_ts - deepest_ts).days
    except Exception:
        result["days_deepest_dip_to_now"] = None

    today_above = today_close >= today_ema10

    if today_above:
        # 从今天往回数，找到 "最后一天 below" → 它的下一天就是 crossback 日期
        last_below_pos = None
        for i in range(len(slice_close) - 1, -1, -1):
            if slice_close.iloc[i] < slice_ema10.iloc[i]:
                last_below_pos = i
                break
        if last_below_pos is not None and last_below_pos + 1 < len(slice_close):
            crossback_ts = slice_close.index[last_below_pos + 1]
            result["crossback_date"] = (
                str(crossback_ts.date()) if hasattr(crossback_ts, "date") else str(crossback_ts)[:10]
            )
            if crossback_ts in slice_vol_ratio.index:
                vr = slice_vol_ratio.loc[crossback_ts]
                result["crossback_volume_ratio"] = float(vr) if pd.notna(vr) else None
        result["status"] = "ema_crossback"
    else:
        # 仍在下方 → 计算从最深底到现在的反弹
        if deepest_close > 0:
            result["recovery_from_bottom_pct"] = (today_close - deepest_close) / deepest_close * 100
        result["status"] = "reversal_extension"

    return result


def _compute_peak_since(
    df: pd.DataFrame,
    since_date_str: str,
    fallback_recent_days: int = 5,
) -> float | None:
    """
    从 df 中取 since_date 之后（含）所有交易日的最高价（high 列 max）。
    用于追踪"自加入 watchlist 以来的历史峰值"。

    降级策略：
        如果 since_date 之后没有数据（典型情况：今天才加入，但 fetcher
        还没拉到今天的 bar → df 末日期 < since_date），则用最近
        `fallback_recent_days` 个交易日作为替代窗口。
    """
    if df is None or df.empty or "high" not in df.columns:
        return None

    try:
        since = pd.to_datetime(since_date_str)
    except (ValueError, TypeError):
        return None

    # df 的 index 应该是 DatetimeIndex（fetcher 通常这么返回，且带 UTC tz）
    if not isinstance(df.index, pd.DatetimeIndex):
        # 退而求其次：用日期列
        if "date" in df.columns:
            mask = pd.to_datetime(df["date"]) >= since
            subset = df.loc[mask, "high"] if mask.any() else df["high"].tail(fallback_recent_days)
        else:
            return None
    else:
        # 关键修复：df.index 通常带 UTC tz，要让 since 也带相同 tz
        if df.index.tz is not None and since.tzinfo is None:
            since = since.tz_localize('UTC')
        mask = df.index >= since
        # 数据延迟（added_date 比最新一根 bar 还晚）→ 用最近 N 天代替
        if mask.any():
            subset = df.loc[mask, "high"]
        else:
            subset = df["high"].tail(fallback_recent_days)

    if subset.empty:
        return None
    return float(subset.max())


def analyze_watchlist(
    market_data: dict[str, pd.DataFrame],
    threshold_pct: float = DEFAULT_REVERSAL_EXTENSION_THRESHOLD_PCT,
    strong_threshold_pct: float = DEFAULT_STRONG_REVERSAL_EXTENSION_THRESHOLD_PCT,
    rs_relative: dict[str, float] | None = None,
) -> dict[str, dict]:
    """
    分析 watchlist 中所有股票的 EMA10 crossback / Reversal extension / Peak-Pullback 状态。

    参数：
        rs_relative: {代码: 百分位 0-100}，策略内部口径的相对强度（对标基准 ETF）。
                     由 data/rs_relative.compute_relative_strength_percentiles() 算好传进来。

    副作用：
        会把每只股票的 peak_price_since_added 写回 watchlist.json（持续累加）。
    """
    rs_relative = rs_relative or {}
    watchlist = load_watchlist()
    today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    results: dict[str, dict] = {}
    dirty = False  # 标记是否需要写回 JSON

    for symbol, entry in watchlist["stocks"].items():
        df = market_data.get(symbol)
        added_date = entry.get("added_date")

        # 基础元数据
        base = {
            "available": False,
            "added_date": added_date,
            "days_in_watchlist": None,
            "first_seen_price": entry.get("first_seen_price"),
            "first_seen_volume_ratio": entry.get("first_seen_volume_ratio"),
            # ── v2 新增：信号强度 + 多策略覆盖 ──
            "first_seen_strength": entry.get("first_seen_strength"),
            "max_strength_seen": entry.get("max_strength_seen"),
            "strategies_covered": entry.get("strategies_covered", []),
            "consensus_count": entry.get("consensus_count", 0),
            "current_price": None,
            "price_change_pct": None,
            "price_change_since_added_pct": None,   # 现价相对加入日 close 的累计变化
            "close_on_added_date": None,             # 加入日 close
            "ema10": None,
            "above_ema10": None,
            "ema10_crossback_today": False,
            "ma20": None,
            "reversal_extension_pct": None,         # Kell 定义：close 相对 EMA10 的偏移（负值=下方延伸）
            "is_reversal_extension": False,          # 底部阶段的延伸信号
            "reversal_extension_alert": None,        # "warning" / "strong"
            "current_volume_ratio": None,
            # ── 相对强度：策略内部口径（对标基准 ETF），0-100 ──
            "rs_relative_pct": rs_relative.get(symbol),
            "peak_price_since_added": entry.get("peak_price_since_added"),
            "pullback_from_peak_pct": None,
            "pullback_state": None,  # None / "starting" (≥10%) / "deep" (≥25%)
            # ── Historical dip+recovery（自 added_date 起）──
            "recovery_status": "never_dipped",      # "ema_crossback" / "reversal_extension" / "never_dipped"
            "first_dip_date": None,
            "deepest_dip_date": None,
            "deepest_dip_pct": None,
            "deepest_dip_close": None,
            "crossback_date": None,
            "crossback_volume_ratio": None,
            "recovery_from_bottom_pct": None,
            "days_added_to_deepest_dip": None,
            "days_deepest_dip_to_now": None,
            "appearances": entry.get("appearances", 1),
        }

        # 计算在观察清单的天数
        if added_date:
            try:
                added = datetime.strptime(added_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                today_dt = datetime.strptime(today_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                base["days_in_watchlist"] = (today_dt - added).days
            except ValueError:
                pass

        # 数据缺失
        if df is None or len(df) < 22:
            results[symbol] = base
            continue

        ind = _compute_indicators(df)
        if ind is None:
            results[symbol] = base
            continue

        # ── Peak tracking：取 added_date 之后的最高价（high max）────────
        peak_from_data = _compute_peak_since(df, added_date) if added_date else None
        stored_peak = entry.get("peak_price_since_added")
        new_peak = None
        if peak_from_data is not None and stored_peak is not None:
            new_peak = max(peak_from_data, stored_peak)
        elif peak_from_data is not None:
            new_peak = peak_from_data
        elif stored_peak is not None:
            new_peak = stored_peak

        # 如果发现新的峰值，写回 watchlist
        if new_peak is not None and (stored_peak is None or new_peak > stored_peak + 1e-6):
            entry["peak_price_since_added"] = round(new_peak, 4)
            dirty = True

        # ── EMA10 crossback（重新站上 EMA10）──
        # 定义：昨天 close < EMA10（曾跌破），今天 close >= EMA10（涨回来）
        # 这是"cross back"的字面含义——从下方穿越回上方
        was_below = ind["prev_close"] < ind["prev_ema10"]
        now_above = ind["close"] >= ind["ema10"]
        crossback_today = was_below and now_above

        # ── Reversal Extension（Kell 原始定义：底部延伸，close 在 10 EMA 下方）──
        # Kell: "Price becomes extended below the 10 EMA into a higher-timeframe support level"
        # 量化：(close - EMA10) / EMA10 × 100
        #   负值 = close 在 EMA10 下方（越负越"extended below"）
        #   ≤ -threshold_pct        → warning  （轻度底部延伸）
        #   ≤ -strong_threshold_pct → strong   （深度底部延伸，可能已 capitulation）
        rev_ext_pct = (ind["close"] - ind["ema10"]) / ind["ema10"] * 100 if ind["ema10"] else 0.0
        if rev_ext_pct <= -strong_threshold_pct:
            rev_alert = "strong"
        elif rev_ext_pct <= -threshold_pct:
            rev_alert = "warning"
        else:
            rev_alert = None

        # ── Historical dip+recovery（自 added_date 起追踪）──
        recovery = _compute_recovery(df, added_date, ind["close"], ind["ema10"])

        # ── Pullback from peak ──
        pullback_pct = None
        pullback_state = None
        if new_peak and new_peak > 0:
            pullback_pct = (ind["close"] - new_peak) / new_peak * 100
            # pullback_pct ≤ 0 表示已经低于峰值
            # 注意：刚加入时 new_peak == current_price，pullback = 0
            if pullback_pct <= -PULLBACK_DEEP_PCT:
                pullback_state = "deep"
            elif pullback_pct <= -PULLBACK_MODERATE_PCT:
                pullback_state = "starting"

        # ── 累计变化（first_seen_price → 当前）──
        first_price = entry.get("first_seen_price")
        price_change_pct = None
        if first_price and first_price > 0:
            price_change_pct = (ind["close"] - first_price) / first_price * 100

        results[symbol] = {
            "available": True,
            "added_date": added_date,
            "days_in_watchlist": base["days_in_watchlist"],
            "first_seen_price": first_price,
            "first_seen_volume_ratio": entry.get("first_seen_volume_ratio"),
            # ── v2 新增：信号强度 + 多策略覆盖 ──
            "first_seen_strength": entry.get("first_seen_strength"),
            "max_strength_seen": entry.get("max_strength_seen"),
            "strategies_covered": entry.get("strategies_covered", []),
            "consensus_count": entry.get("consensus_count", 0),
            "current_price": ind["close"],
            "price_change_pct": price_change_pct,
            "price_change_since_added_pct": recovery["price_change_since_added_pct"],
            "close_on_added_date": recovery["close_on_added_date"],
            "ema10": ind["ema10"],
            "above_ema10": ind["close"] >= ind["ema10"],
            "ema10_crossback_today": crossback_today,
            "ma20": ind["ma20"],
            "reversal_extension_pct": rev_ext_pct,
            "is_reversal_extension": rev_alert is not None,
            "reversal_extension_alert": rev_alert,
            "current_volume_ratio": ind["volume_ratio"],
            # ── 相对强度：策略内部口径（对标基准 ETF），0-100 ──
            "rs_relative_pct": rs_relative.get(symbol),
            "peak_price_since_added": new_peak,
            "pullback_from_peak_pct": pullback_pct,
            "pullback_state": pullback_state,
            "recovery_status": recovery["status"],
            "first_dip_date": recovery["first_dip_date"],
            "deepest_dip_date": recovery["deepest_dip_date"],
            "deepest_dip_pct": recovery["deepest_dip_pct"],
            "deepest_dip_close": recovery["deepest_dip_close"],
            "crossback_date": recovery["crossback_date"],
            "crossback_volume_ratio": recovery["crossback_volume_ratio"],
            "recovery_from_bottom_pct": recovery["recovery_from_bottom_pct"],
            "days_added_to_deepest_dip": recovery["days_added_to_deepest_dip"],
            "days_deepest_dip_to_now": recovery["days_deepest_dip_to_now"],
            "appearances": entry.get("appearances", 1),
        }

    # 写回 JSON（仅在 peak 有更新时）
    if dirty:
        save_watchlist(watchlist)

    return results


def filter_crossback_signals(
    analysis: dict[str, dict],
    volume_threshold: float = DEFAULT_CROSSBACK_SIGNAL_VOLUME_THRESHOLD,
    max_days_since_crossback: int = DEFAULT_MAX_DAYS_SINCE_CROSSBACK,
) -> list[str]:
    """
    从 watchlist 分析结果中筛出"放量穿回 EMA10"信号。

    四条件：
      1. 自加入日起曾跌破 EMA10（recovery_status == "ema_crossback"）
      2. 当前已站回 EMA10 上方（同上）
      3. 穿回日成交量 ≥ volume_threshold × 20日均量（放量穿回）
      4. 穿回日距今 ≤ max_days_since_crossback 天（新鲜度过滤，超过则视为过期）

    返回：满足全部条件的股票代码列表（按穿回量比降序）。
    """
    out = []
    today = date.today()
    for sym, a in analysis.items():
        if not a.get("available"):
            continue
        if a.get("recovery_status") != "ema_crossback":
            continue
        cbr = a.get("crossback_volume_ratio")
        if cbr is None or cbr < volume_threshold:
            continue
        # 新鲜度过滤：穿回日距今超过 max_days_since_crossback 天视为过期
        cb_date_str = a.get("crossback_date")
        if cb_date_str and max_days_since_crossback is not None:
            try:
                cb_date = datetime.strptime(cb_date_str, "%Y-%m-%d").date()
                days_since = (today - cb_date).days
                if days_since > max_days_since_crossback:
                    continue
            except (ValueError, TypeError):
                # 日期解析失败 → 不参与新鲜度过滤（保留信号）
                pass
        out.append(sym)
    # 排序：穿回日降序（最新穿回的排最前），同一天再按量比降序。
    # 为什么按日期而不是量比：量比只说明「那天放了多少量」，日期才说明新鲜度——
    # 一周前放量穿回的票和昨天刚穿回的票，可操作性完全不同。
    # 用户 2026-10-29 明确要求：以后穿回 EMA10 信号按日期排序。
    def _sort_key(s: str):
        return (
            analysis[s].get("crossback_date") or "",
            analysis[s].get("crossback_volume_ratio") or 0,
        )

    out.sort(key=_sort_key, reverse=True)
    return out


def print_crossback_signals(
    analysis: dict[str, dict],
    volume_threshold: float = DEFAULT_CROSSBACK_SIGNAL_VOLUME_THRESHOLD,
    max_days_since_crossback: int = DEFAULT_MAX_DAYS_SINCE_CROSSBACK,
    rs_ratings: dict[str, int] | None = None,
) -> None:
    """打印放量穿回 EMA10 的信号清单（满足 4 条件，含新鲜度过滤）。"""
    signals = filter_crossback_signals(analysis, volume_threshold, max_days_since_crossback)
    print()
    print("=" * 162)
    print(
        f"📡 放量穿回 EMA10 信号（共 {len(signals)} 只，穿回日量比 ≥ {volume_threshold}x，穿回日距今 ≤ {max_days_since_crossback} 天）"
    )
    print(
        f"   条件：① 自加入日起曾跌破 EMA10  ② 当前已站回 EMA10 上方  ③ 穿回日成交量 ≥ "
        f"{volume_threshold}×20日均量  ④ 穿回日距今 ≤ {max_days_since_crossback} 天（新鲜度）"
    )
    print(
        "   RS 两列口径：RS评级 = O'Neil CAN SLIM 相对强度评级（1-99，美股全市场排名，看绝对涨幅）"
        "｜RS% = 策略内部口径（对标基准 ETF 的超额收益百分位 0-100，看比大盘强多少）"
    )
    print("=" * 162)
    if not signals:
        print("  （今日无符合全部 4 条件的信号）")
        return
    print(
        f"  {'股票':<12} {'RS评级':<7} {'RS%':<6} {'现价':<9} {'穿回日':<11} {'距今':<6} {'穿回量比':<10} "
        f"{'加入日':<11} {'累计%':<8} {'首次跌破日':<12} {'最深%':<8} {'情况'}"
    )
    print("  " + "-" * 132)
    for sym in signals:
        a = analysis[sym]
        cbr = a.get("crossback_volume_ratio")
        cbr_str = f"{cbr:.1f}x" if cbr is not None else "—"
        chg = a.get("price_change_since_added_pct")
        chg_str = f"{chg:+.1f}%" if chg is not None else "—"
        dip = a.get("deepest_dip_pct")
        dip_str = f"{dip:+.1f}%" if dip is not None else "—"
        # 计算穿回距今
        cb_date_str = a.get("crossback_date")
        days_since = "—"
        if cb_date_str:
            try:
                cb_d = datetime.strptime(cb_date_str, "%Y-%m-%d").date()
                days_since = f"{(date.today() - cb_d).days}天"
            except (ValueError, TypeError):
                pass
        # 两套 RS 口径
        rating = (rs_ratings or {}).get(sym)
        rating_str = str(rating) if rating is not None else "—"
        rel = a.get("rs_relative_pct")
        rel_str = f"{rel:.0f}" if rel is not None else "—"
        print(
            f"  {display_name(sym):<12} {rating_str:<7} {rel_str:<6} ${a['current_price']:<8.2f} "
            f"{(a.get('crossback_date') or '—'):<11} {days_since:<6} {cbr_str:<10} "
            f"{(a.get('added_date') or '—'):<11} {chg_str:<8} "
            f"{(a.get('first_dip_date') or '—'):<12} {dip_str:<8} "
            f"✅放量穿回EMA10"
        )


def print_watchlist_report(
    analysis: dict[str, dict],
    crossback_volume_threshold: float = DEFAULT_CROSSBACK_SIGNAL_VOLUME_THRESHOLD,
    crossback_max_days: int = DEFAULT_MAX_DAYS_SINCE_CROSSBACK,
    rs_ratings: dict[str, int] | None = None,
) -> None:
    """打印 watchlist 分析报告。"""
    if not analysis:
        print("\n[观察清单] 暂无内容")
        return

    symbols = list(analysis.keys())
    available_count = sum(1 for a in analysis.values() if a["available"])
    crossback_today = [s for s in symbols if analysis[s]["ema10_crossback_today"]]
    rev_ext_now = [s for s in symbols if analysis[s]["is_reversal_extension"]]
    rev_ext_strong = [s for s in rev_ext_now if analysis[s]["reversal_extension_alert"] == "strong"]
    pullback_starting = [s for s in symbols if analysis[s].get("pullback_state") == "starting"]
    pullback_deep = [s for s in symbols if analysis[s].get("pullback_state") == "deep"]

    # ── 自加入日起的跌破/恢复分组 ──
    recovery_crossback = [s for s in symbols if analysis[s].get("recovery_status") == "ema_crossback"]
    recovery_extension = [s for s in symbols if analysis[s].get("recovery_status") == "reversal_extension"]
    recovery_never = [s for s in symbols if analysis[s].get("recovery_status") == "never_dipped"]

    # 1️⃣ 放量穿回信号（最核心输出，放在最前面）
    print_crossback_signals(analysis, crossback_volume_threshold, crossback_max_days, rs_ratings)

    print()
    print("=" * 130)
    print(f"观察清单分析（共 {len(symbols)} 只，可用数据 {available_count} 只）")
    print("=" * 130)

    # 摘要
    print(f"\n📋 摘要：")
    print(f"  • 今日 EMA10 crossback（yesterday below → today above）: {len(crossback_today)} 只")
    print(f"  • 今日 Reversal Extension（Kell 定义：close 在 10 EMA 下方延伸 ≥5%）: {len(rev_ext_now)} 只")
    print(f"    其中 深度延伸（≤-10%）: {len(rev_ext_strong)} 只")
    print(f"  • 回踩中（从峰值 -10%以上）: {len(pullback_starting)} 只")
    print(f"    其中 深度回踩（≥-25%）: {len(pullback_deep)} 只")
    print()
    print(f"  ── 自加入日起的 EMA10 跌破/恢复分组 ──")
    print(f"  • ✅ EMA Crossback（跌破后已站回 EMA10 上方）: {len(recovery_crossback)} 只")
    print(f"  • 🔻 Reversal Extension（跌破后仍在 EMA10 下方）: {len(recovery_extension)} 只")
    print(f"  • ✓ 从未跌破（自加入后一直在 EMA10 上方）: {len(recovery_never)} 只")

    # ── EMA Crossback 历史组 ──
    if recovery_crossback:
        print()
        print(f"✅ EMA Crossback 组（自加入日起曾跌破 EMA10，当前已站回上方）")
        print(f"   按 days_in_watchlist / days_deepest_dip_to_now 排列")
        print()
        header = (
            f"  {'股票':<12} {'现价':<9} {'加入日收':<9} {'累计%':<8} {'加入日':<12} "
            f"{'首次破':<11} {'最深日':<11} {'最深%':<7} {'穿回日':<11} {'穿回量比':<9} "
            f"{'在册':<4} {'入→底':<5} {'底→今':<5}"
        )
        print(header)
        print("  " + "-" * 138)
        # 按"距今最近穿回"升序排序
        sorted_cb = sorted(
            recovery_crossback,
            key=lambda s: (
                analysis[s].get("days_deepest_dip_to_now") is None,
                analysis[s].get("days_deepest_dip_to_now", 999),
            ),
        )
        for sym in sorted_cb:
            a = analysis[sym]
            ad = a["added_date"] or "—"
            chg = a["price_change_since_added_pct"]
            chg_str = f"{chg:+.1f}%" if chg is not None else "—"
            added_close = a.get("close_on_added_date")
            ac_str = f"${added_close:.2f}" if added_close is not None else "—"
            cbr = a.get("crossback_volume_ratio")
            cbr_str = f"{cbr:.1f}x" if cbr is not None else "—"
            dipw = a["days_in_watchlist"]
            d1 = a.get("days_added_to_deepest_dip")
            d2 = a.get("days_deepest_dip_to_now")
            dipw_str = f"{dipw}天" if dipw is not None else "—"
            d1_str = f"{d1}天" if d1 is not None else "—"
            d2_str = f"{d2}天" if d2 is not None else "—"
            print(
                f"  {display_name(sym):<12} ${a['current_price']:<8.2f} {ac_str:<9} {chg_str:<8} {ad:<12} "
                f"{(a.get('first_dip_date') or '—'):<11} "
                f"{(a.get('deepest_dip_date') or '—'):<11} "
                f"{(a['deepest_dip_pct'] or 0):+5.1f}%  "
                f"{(a.get('crossback_date') or '—'):<11} {cbr_str:<9} "
                f"{dipw_str:<4} {d1_str:<5} {d2_str:<5}"
            )

    # ── Reversal Extension 历史组 ──
    if recovery_extension:
        print()
        print(f"🔻 Reversal Extension 组（自加入日起曾跌破 EMA10，当前仍在下方）")
        print(f"   按 today_vs_ema10 升序（跌得最深的在上）")
        print()
        header = (
            f"  {'股票':<12} {'现价':<9} {'加入日收':<9} {'累计%':<8} {'加入日':<12} "
            f"{'首次破':<11} {'最深日':<11} {'最深%':<7} {'vsEMA10':<8} {'从底反弹':<9} "
            f"{'在册':<4} {'入→底':<5} {'底→今':<5}"
        )
        print(header)
        print("  " + "-" * 138)
        # 按 today_vs_ema10 升序
        sorted_ext = sorted(
            recovery_extension,
            key=lambda s: analysis[s]["reversal_extension_pct"],
        )
        for sym in sorted_ext:
            a = analysis[sym]
            ad = a["added_date"] or "—"
            chg = a["price_change_since_added_pct"]
            chg_str = f"{chg:+.1f}%" if chg is not None else "—"
            added_close = a.get("close_on_added_date")
            ac_str = f"${added_close:.2f}" if added_close is not None else "—"
            reb = a.get("recovery_from_bottom_pct")
            reb_str = f"{reb:+.1f}%" if reb is not None else "—"
            dipw = a["days_in_watchlist"]
            d1 = a.get("days_added_to_deepest_dip")
            d2 = a.get("days_deepest_dip_to_now")
            dipw_str = f"{dipw}天" if dipw is not None else "—"
            d1_str = f"{d1}天" if d1 is not None else "—"
            d2_str = f"{d2}天" if d2 is not None else "—"
            print(
                f"  {display_name(sym):<12} ${a['current_price']:<8.2f} {ac_str:<9} {chg_str:<8} {ad:<12} "
                f"{(a.get('first_dip_date') or '—'):<11} "
                f"{(a.get('deepest_dip_date') or '—'):<11} "
                f"{(a['deepest_dip_pct'] or 0):+5.1f}%  "
                f"{a['reversal_extension_pct']:+5.1f}%  {reb_str:<9} "
                f"{dipw_str:<4} {d1_str:<5} {d2_str:<5}"
            )

    # ── 从未跌破组 ──
    if recovery_never:
        print()
        print(f"✓ 从未跌破 EMA10（{len(recovery_never)} 只）：")
        # 按累计%降序排列
        sorted_never = sorted(
            recovery_never,
            key=lambda s: -(analysis[s].get("price_change_since_added_pct") or 0),
        )
        for sym in sorted_never:
            a = analysis[sym]
            chg = a["price_change_since_added_pct"]
            chg_str = f"{chg:+.1f}%" if chg is not None else "—"
            dipw = a["days_in_watchlist"]
            dipw_str = f"{dipw}天" if dipw is not None else "—"
            print(f"   {display_name(sym):<12} 累计{chg_str}  在册{dipw_str}")

    # ── 回踩专区（保留原逻辑） ──
    if pullback_starting or pullback_deep:
        print()
        print(f"↘️ 回踩专区（突破后回踩中，可关注二次突破机会）：")
        for sym in pullback_deep + pullback_starting:
            a = analysis[sym]
            if not a["available"]:
                continue
            state_icon = "🔻" if a["pullback_state"] == "deep" else "↘️"
            print(
                f"  {display_name(sym):<12} 现价 ${a['current_price']:<7.2f}  "
                f"峰值 ${a['peak_price_since_added']:<7.2f}  "
                f"回撤 {a['pullback_from_peak_pct']:+.1f}%  "
                f"EMA10={a['ema10']:.2f} MA20={a['ma20']:.2f} {state_icon}"
            )

    # ── 完整列表 ──
    print()
    print(f"📊 全部观察清单（一张表看全部 {len(symbols)} 只）：")
    print(f"   表头说明：")
    print(f"     • 入选日      = 这只股票被加入 watchlist 的日期")
    print(f"     • 入选量比    = 入选当天成交量是10日均量的几倍（即当时为什么会被扫到）")
    print(f"     • 加入后涨跌  = 进观察清单那天到现在，涨了或跌了多少")
    print(f"     • 比10天均价  = 现在价格比最近10天平均价高了还是低了")
    print(f"     • 在册天数    = 这只股票在观察清单里待了几天")
    print(f"     • 首次跌破日  = 第一次跌到10天均价下方的日期")
    print(f"     • 跌最狠那天  = 自加入后跌得最低的那天")
    print(f"     • 涨回那天    = 重新涨回10天均价上方的日期（空=还没涨回来）")
    print(f"     • 涨回时量    = 涨回那天成交量是平时几倍（>1倍=放量涨回，<1倍=缩量涨回）")
    print(f"     • 入册到最低  = 进清单到跌最狠那天，中间过了几天")
    print(f"     • 最低到今天  = 从跌最狠那天到现在，过了几天")
    print(f"     • 从最低反弹  = 从跌最狠那天到现在，反弹了百分之多少")
    header = (
        f"{'股票':<12} {'入选日':<11} {'入选量比':<9} {'现在价格':<10} {'加入后涨跌':<11} "
        f"{'10天均价':<9} {'20天均价':<9} {'比10天均价':<10} {'在册几天':<8} "
        f"{'首次跌破日':<11} {'跌最狠那天':<11} {'涨回那天':<11} {'涨回时量':<9} "

        f"{'入册到最低':<9} {'最低到今天':<9} {'从最低反弹':<11} {'情况'}"
    )
    print(header)
    print("-" * 221)
    for sym in symbols:
        a = analysis[sym]
        if not a["available"]:
            days = a["days_in_watchlist"] if a["days_in_watchlist"] is not None else "—"
            print(f"{display_name(sym):<12} {'—':<11} {'—':<9} {'数据缺失':<10} {'—':<11} {'—':<9} {'—':<9} {'—':<10} {str(days):<8} {'—':<11} {'—':<11} {'—':<11} {'—':<9} {'—':<9} {'—':<9} {'—':<9} {'—':<11} ⚠️")
            continue

        # 状态标签
        status = []
        if a["ema10_crossback_today"]:
            status.append("✅今日收EMA10")
        if a["reversal_extension_alert"] == "strong":
            status.append("🔻Kell强延伸")
        elif a["reversal_extension_alert"] == "warning":
            status.append("⚡Kell延伸")
        if a["recovery_status"] == "reversal_extension":
            status.append("🔻历史EXT")
        elif a["recovery_status"] == "ema_crossback":
            status.append("✅历史CB")
        if a["pullback_state"] == "deep":
            status.append("🔻深度回踩")
        elif a["pullback_state"] == "starting":
            status.append("↘️回踩中")
        if not status:
            status.append("✓正常")
        status_str = ",".join(status)

        chg = a["price_change_since_added_pct"]
        chg_str = f"{chg:+.1f}%" if chg is not None else "—"
        rev_ext_str = f"{a['reversal_extension_pct']:+.1f}%" if a['reversal_extension_pct'] is not None else "—"
        reb = a.get("recovery_from_bottom_pct")
        reb_str = f"{reb:+.1f}%" if reb is not None else "—"
        days = a["days_in_watchlist"] if a["days_in_watchlist"] is not None else "—"
        cbr = a.get("crossback_volume_ratio")
        cbr_str = f"{cbr:.1f}x" if cbr is not None else "—"
        d1 = a.get("days_added_to_deepest_dip")
        d2 = a.get("days_deepest_dip_to_now")
        d1_str = f"{d1}天" if d1 is not None else "—"
        d2_str = f"{d2}天" if d2 is not None else "—"

        # 入选日和入选量比（从 watchlist.json 取）
        added_date_str = a.get("added_date") or "—"
        # first_seen_volume_ratio 在 analysis dict 里没存，从 manager 取
        # 这里直接走 entry 里的数据，通过 a 字典拿到（base 里有 first_seen_price，但没有 vol_ratio）
        # 简单办法：从 base 里拿，如果不在则显示 —
        first_vol_ratio = a.get("first_seen_volume_ratio")
        first_vol_str = f"{first_vol_ratio:.1f}x" if first_vol_ratio is not None else "—"


        print(
            f"{display_name(sym):<12} {added_date_str:<11} {first_vol_str:<9} ${a['current_price']:<8.2f} {chg_str:<8} "
            f"{a['ema10']:<8.2f} {a['ma20']:<8.2f} {rev_ext_str:<8} "
            f"{str(days):<4} {(a.get('first_dip_date') or '—'):<11} {(a.get('deepest_dip_date') or '—'):<11} "
            f"{(a.get('crossback_date') or '—'):<11} {cbr_str:<9} "
            f"{d1_str:<6} {d2_str:<6} {reb_str:<7} {status_str}"
        )
    print("=" * 195)