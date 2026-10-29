"""
data/rs_rating.py — O'Neil / CAN SLIM 相对强度评级（RS Rating, 1-99）

背景：
- 观察清单（第二层信号）原本没有 RS 数据，需要现算
- O'Neil 的 IBD 相对强度评级算法：把过去 12 个月拆成 4 个季度，
  近季权重最高（0.4），其余三个季度各 0.2，加权得到 RS Score，
  再在全体股票池内排名换算成 1-99 分。

公式（Schwag / IBD 标准做法）：
    Q1 = 近 3 月涨幅   × 0.4
    Q2 = 4-6 月涨幅    × 0.2
    Q3 = 7-9 月涨幅    × 0.2
    Q4 = 10-12 月涨幅  × 0.2
    RS Score = Q1 + Q2 + Q3 + Q4
    RS Rating = RS Score 在池内的百分位 → 1..99

与策略内部 RS% 的区别：
- 策略内部 RS%（sepa_minervini.py 的 _check_rs）是对标 SPY 的超额收益百分位
- 这里是原始涨幅加权排名，与 O'Neil 原书口径一致
- 两者都是 0-100/1-99 的相对排名，报告里分列显示，不互相覆盖
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 12 个月 ≈ 252 个交易日，分成 4 个季度各 63 天
QUARTER_DAYS = 63
LOOKBACK_DAYS = QUARTER_DAYS * 4  # 252

# 各季度权重：近季最重要
QUARTER_WEIGHTS = (0.4, 0.2, 0.2, 0.2)

# 报告里用的完整列名。不要用简写——「RS%」和「RS评级」看起来像同一个东西，
# 实际是两套口径（见 data/rs_relative.py 的对比表），列名必须自己就能说明白。
RS_RATING_LABEL = "RS评级（O'Neil CAN SLIM 全市场排名 1-99）"

# ── 拆股识别阈值 ────────────────────────────────────────────────
# 数据源给的是未复权价，拆股当天会出现一个机械跳空，把历史涨幅凭空放大。
# 判据 = 跳空够大 + 当天几乎没有日内波动。
# 只看跳空会误伤暴涨暴跌；加上"日内振幅几乎为零"这一条，
# 机械事件和真实行情就分得很干净（SLN 2026-10-19 振幅 0.2%，同月两次真实
# 暴涨振幅 18~20%，全部被正确排除）。
SPLIT_GAP = 0.25        # 日间跳空 ≥ 25%
SPLIT_MAX_RANGE = 0.02  # 当日 (high-low)/close ≤ 2%
SPLIT_RATIO_MIN = 0.10  # 合理拆股区间：1:10 正向拆股 ~ 10:1 反向拆股
SPLIT_RATIO_MAX = 10.0
MAX_SPLITS_IN_WINDOW = 2  # 一年内超过 2 次 = 数据在两个价源之间来回跳，不是真拆股
SPLIT_HOLD_DAYS = 5      # 拆股后观察几天，确认价格稳在新水平


def _close_series(df: pd.DataFrame) -> np.ndarray:
    """取收盘价数组，统一兼容 close / Close 两种列名。"""
    for col in ("close", "Close"):
        if col in df.columns:
            s = df[col].dropna()
            if len(s):
                return s.to_numpy(dtype=float)
    return np.array([])


def _ohlc_arrays(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """取对齐的 close/high/low 三条数组，取不到返回 None。"""
    names = {}
    for want in ("close", "high", "low"):
        for col in (want, want.capitalize()):
            if col in df.columns:
                names[want] = col
                break
        else:
            return None

    sub = df[[names["close"], names["high"], names["low"]]].dropna()
    if sub.empty:
        return None
    return (
        sub[names["close"]].to_numpy(dtype=float),
        sub[names["high"]].to_numpy(dtype=float),
        sub[names["low"]].to_numpy(dtype=float),
    )


def _detect_splits(
    close: np.ndarray, high: np.ndarray, low: np.ndarray, start: int
) -> list[tuple[int, float]] | None:
    """
    在 [start, len) 区间内识别拆股，返回 [(下标, ratio)]；
    价格数据无法解释时返回 None（调用方据此放弃该股票）。

    判据见模块顶部的三个条件：跳空 ≥ SPLIT_GAP、当日振幅 ≤ SPLIT_MAX_RANGE、
    之后 SPLIT_HOLD_DAYS 天价格稳在新水平。
    """
    splits: list[tuple[int, float]] = []
    for i in range(start + 1, len(close)):
        prev, cur = close[i - 1], close[i]
        if prev <= 0 or cur <= 0:
            continue
        ratio = cur / prev
        if 1 - SPLIT_GAP < ratio < 1 + SPLIT_GAP:
            continue  # 涨跌幅不到 25%，正常波动
        day_range = (high[i] - low[i]) / cur
        if day_range > SPLIT_MAX_RANGE:
            continue  # 有真实日内波动 → 是行情不是拆股
        # 拆股后价格会稳在新的水平上；若几天内就跳回原水平，
        # 说明只是那一天的坏数据，不能当成拆股（AEMD 2025-09-24 就是这种）
        after = close[i + 1: i + 1 + SPLIT_HOLD_DAYS]
        if len(after) >= 2:
            ref = float(np.median(after))
            if not (0.75 * cur <= ref <= 1.33 * cur):
                continue
        if not (SPLIT_RATIO_MIN <= ratio <= SPLIT_RATIO_MAX):
            return None  # 超出合理拆股区间，数据本身不可信
        splits.append((i, ratio))
        if len(splits) > MAX_SPLITS_IN_WINDOW:
            return None  # 反复跳变 = 两个价源在交替，不是真拆股
    return splits


def _split_adjusted_close(df: pd.DataFrame) -> np.ndarray | None:
    """
    返回拆股回溯调整后的收盘价；价格数据无法解释时返回 None。

    调整方式：若第 i 天相对第 i-1 天跳空 ratio 倍（且符合拆股特征），
    就把 i 之前的所有收盘价乘以 ratio，让整条曲线接回连续。
    乘完之后 close[i-1] × ratio 恰好等于 close[i]，跳空被精确抹平。
    """
    arrays = _ohlc_arrays(df)
    if arrays is None:
        return None
    close, high, low = arrays
    n = len(close)
    if n <= LOOKBACK_DAYS:
        return None

    start = n - 1 - LOOKBACK_DAYS
    splits = _detect_splits(close, high, low, start)
    if splits is None:
        return None

    adjusted = close.copy()
    for i, ratio in splits:
        adjusted[:i] *= ratio
    return adjusted


def split_factor_since(df: pd.DataFrame, since) -> float | None:
    """
    返回 since 之后所有拆股 ratio 的乘积；数据无法解释时返回 None。

    用途：把「加入日收盘价」换算到今天的价格基准，否则拿拆股前的旧价
    跟拆股后的新价相除，涨跌幅会连方向都反（SLN 实际 -40.7% 显示成 +33.8%）。
    乘完之后两端同基准，相除才有意义。
    """
    arrays = _ohlc_arrays(df)
    if arrays is None:
        return None
    close, high, low = arrays

    since_ts = pd.to_datetime(since)
    if df.index.tz is not None and since_ts.tzinfo is None:
        since_ts = since_ts.tz_localize(df.index.tz)
    elif df.index.tz is None and since_ts.tzinfo is not None:
        since_ts = since_ts.tz_localize(None)

    pos = int(df.index.searchsorted(since_ts))
    pos = max(0, min(pos, len(close) - 1))

    splits = _detect_splits(close, high, low, pos)
    if splits is None:
        return None

    factor = 1.0
    for _, ratio in splits:
        factor *= ratio
    return factor


def compute_rs_ratings(market_data: dict[str, pd.DataFrame]) -> dict[str, int]:
    """
    对整个 market_data 股票池计算 O'Neil RS Rating（1-99）。

    参数:
        market_data: {ticker: 日线 DataFrame}，需含 close 列且至少 252 行

    返回:
        {ticker: rating 1-99}；数据不足 252 天、或价格数据不可信的股票不出现在结果里
    """
    scores: dict[str, float] = {}

    for sym, df in market_data.items():
        if df is None:
            continue
        close = _split_adjusted_close(df)
        if close is None or len(close) <= LOOKBACK_DAYS:
            continue

        end = len(close) - 1
        # 各季度起点（end - 63 / -126 / -189 / -252）
        try:
            q1 = close[end] / close[end - QUARTER_DAYS] - 1
            q2 = close[end - QUARTER_DAYS] / close[end - 2 * QUARTER_DAYS] - 1
            q3 = close[end - 2 * QUARTER_DAYS] / close[end - 3 * QUARTER_DAYS] - 1
            q4 = close[end - 3 * QUARTER_DAYS] / close[end - LOOKBACK_DAYS] - 1
        except (IndexError, ZeroDivisionError):
            continue

        if not all(np.isfinite([q1, q2, q3, q4])):
            continue

        scores[sym] = (
            q1 * QUARTER_WEIGHTS[0]
            + q2 * QUARTER_WEIGHTS[1]
            + q3 * QUARTER_WEIGHTS[2]
            + q4 * QUARTER_WEIGHTS[3]
        )

    if not scores:
        return {}

    # RS Score → 百分位 → 1..99
    values = np.array(list(scores.values()), dtype=float)
    ratings: dict[str, int] = {}
    for sym, score in scores.items():
        pctile = float(np.mean(values <= score) * 100)
        ratings[sym] = max(1, min(99, round(pctile)))
    return ratings