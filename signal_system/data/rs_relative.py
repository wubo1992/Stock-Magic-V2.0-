"""
data/rs_relative.py — 「策略内部口径」的相对强度百分位

**这个模块和 data/rs_rating.py 是两套完全不同的口径，报告里会同时出现两个 RS 列。
这里把两者的区别一次写清楚，避免看报告时把两个数字搞混：**

| | 本模块：RS%（策略内部口径） | data/rs_rating.py：RS评级（O'Neil CAN SLIM） |
|---|---|---|
| 参照物 | 基准 ETF（美股 SPY / 港股 ASHR / 台股 EWT） | 无，只看绝对涨幅 |
| 算式 | 0.4×(个股252日涨幅÷基准252日涨幅−1) + 0.3×(126日) + 0.3×(60日) | 12 个月按 63 个交易日切 4 季：近季×0.4 + 4-6月×0.2 + 7-9月×0.2 + 10-12月×0.2 |
| 排名范围 | UNIVERSE.md 固定股票池 | 美股全市场普通股（约 6300 只） |
| 输出 | 0-100 的百分位 | 1-99 的分位评分 |
| 回答的问题 | **它比大盘强多少** | **它自己在全市场里排第几** |

大盘下跌的时候，两个数字会明显分开：一只股票「比大盘抗跌」但「自己也跌了不少」时，
RS% 会很高、RS评级却很低。这是设计如此，不是 bug。

本模块的公式与各策略内部使用的完全一致（见 strategies/v1_wizard/sepa_minervini.py
的 `_check_rs`），所以算出来的值和策略信号里写的 `[RS] 相对强度排名X%` 是同一个数。
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

# 各市场的基准 ETF（与 strategies/v1_wizard/sepa_minervini.py 的 BENCHMARK_FOR_MARKET 一致）
BENCHMARK_FOR_MARKET = {"US": "SPY", "HK": "ASHR", "TW": "EWT"}

# 报告里用的完整列名。不要用简写——「RS%」和「RS评级」看起来像同一个东西，
# 实际是两套口径，必须让列名自己就能说明白。
RS_RELATIVE_LABEL = "RS%（策略内部·对标基准ETF 0-100）"

# 打分窗口与权重：252 日 ×0.4 + 126 日 ×0.3 + 60 日 ×0.3
_PERIOD_WEIGHTS = ((252, 0.4), (126, 0.3), (60, 0.3))


def get_market(symbol: str) -> str:
    """按代码后缀判断市场：.HK → 港股，.TW → 台股，其余 → 美股。"""
    if symbol.endswith(".HK"):
        return "HK"
    if symbol.endswith(".TW"):
        return "TW"
    return "US"


def _slice_to_date(df: pd.DataFrame, date: datetime) -> pd.DataFrame:
    """截取 date 之前（含）的数据，和策略里的 _slice_to_date 保持一致。"""
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    idx = df.index
    if idx.tzinfo is None:
        idx = idx.tz_localize("UTC")
        df = df.copy()
        df.index = idx
    return df[df.index <= date]


def _period_return(sliced_df: pd.DataFrame | None, periods: int) -> float:
    """区间涨幅 = 末日收盘 ÷ 期初收盘 − 1。数据不够返回 nan。"""
    if sliced_df is None or len(sliced_df) < periods:
        return np.nan
    return float(sliced_df["close"].iloc[-1] / sliced_df["close"].iloc[-periods] - 1)


def compute_relative_strength_percentiles(
    market_data: dict[str, pd.DataFrame],
    pool_symbols: set[str] | None = None,
    as_of: datetime | None = None,
) -> dict[str, float]:
    """
    计算「策略内部口径」的相对强度百分位（0-100）。

    步骤（和策略内部一致）：
      1. 分市场取基准 ETF 的 252/126/60 日涨幅
      2. 每只股票算 0.4×(个股涨幅÷基准涨幅−1) + 0.3×(126日) + 0.3×(60日)
      3. 在固定股票池（UNIVERSE.md）内做百分位排名

    参数：
        market_data:  {代码: 日线 DataFrame}，需含基准 ETF（SPY / ASHR / EWT）
        pool_symbols: 排名用的固定股票池（UNIVERSE.md 里的代码集合）。
                       传 None 则用 market_data 全部股票排名。
        as_of:        计算截止时间，默认当前 UTC 时间。

    返回：
        {代码: 百分位 0-100}。没有足够数据的代码不出现在结果里。
    """
    if as_of is None:
        as_of = datetime.now(tz=timezone.utc)

    scores_by_market: dict[str, dict[str, float]] = {}

    for market, bench_sym in BENCHMARK_FOR_MARKET.items():
        bench_df = market_data.get(bench_sym)
        if bench_df is None:
            # 没有基准 ETF → 这个市场算不了
            continue

        bench_sliced = _slice_to_date(bench_df, as_of)
        bench_returns: dict[int, float] = {}
        for periods, _ in _PERIOD_WEIGHTS:
            r = _period_return(bench_sliced, periods)
            if np.isnan(r) or r == 0:
                bench_returns = {}
                break
            bench_returns[periods] = r
        if not bench_returns:
            continue

        scores: dict[str, float] = {}
        for symbol, df in market_data.items():
            if get_market(symbol) != market:
                continue
            sliced = _slice_to_date(df, as_of)
            score = 0.0
            usable = True
            for periods, weight in _PERIOD_WEIGHTS:
                r = _period_return(sliced, periods)
                if np.isnan(r):
                    usable = False
                    break
                score += weight * (r / bench_returns[periods] - 1)
            if usable:
                scores[symbol] = score

        if len(scores) < 2:
            continue
        scores_by_market[market] = scores

    # ── 百分位排名 ──
    result: dict[str, float] = {}
    for market, scores in scores_by_market.items():
        if pool_symbols:
            pool_scores = [v for k, v in scores.items() if k in pool_symbols]
        else:
            pool_scores = []
        if not pool_scores:
            pool_scores = list(scores.values())
        arr = np.asarray(pool_scores, dtype=float)
        for symbol, score in scores.items():
            # 和策略一致：分数小于等于自己的都算（含并列）
            result[symbol] = float(np.mean(arr <= score) * 100)

    return result
