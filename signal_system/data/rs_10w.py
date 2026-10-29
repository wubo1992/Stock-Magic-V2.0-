"""
data/rs_10w.py — 10 周（50 个交易日）相对强度

公式（IBD 标准价格乘数比）：
    R_10W(t)    = close(t) / close(t-50) - 1           ← 50 日简单收益率
    RS-10W(t)   = (1 + R_10W(ticker)) / (1 + R_10W(SPY))   ← 价格乘数比

含义（IBD 标准解读）：
    - 1.00x = 股票与 SPY 完全同步
    - 1.50x = 股票 10 周涨幅是 SPY 的 1.5 倍
    - 2.00x = 股票价格在过去 10 周内是 SPY 的 2 倍（同期）
    - 0.50x = 股票价格在过去 10 周内是 SPY 的一半
    - 1.00x 上下 = 跑赢/跑输大市

注意：
    - 这是价格乘数比（price multiplier ratio），不是简单收益比 (R_stock/R_spy)
    - 当 SPY 涨幅很小（接近 0）时，本公式数值稳定，不会像收益比那样爆炸
      例如 SPY 涨 0.1%、股票涨 10%：
      - 简单收益比：0.10 / 0.001 = 100x（无意义）
      - IBD 价格比：1.10 / 1.001 = 1.099x（合理）
    - 当股票和 SPY 同步时（涨幅相同），永远 = 1.00x

基准固定为 SPY（不管港股台股，因为用户只问"对比标普"）。
"""

from __future__ import annotations

from datetime import timezone

import pandas as pd

BENCHMARK = "SPY"
LOOKBACK = 50  # 10 周 × 5 交易日


def _slice_to_date(df: pd.DataFrame, date) -> pd.DataFrame:
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    idx = df.index
    if idx.tzinfo is None:
        idx = idx.tz_localize("UTC")
        df = df.copy()
        df.index = idx
    return df[df.index <= date]


def compute_rs_10w(
    symbol: str,
    market_data: dict[str, pd.DataFrame],
    date,
) -> float | None:
    """
    RS-10W = (1 + 股票 50 日收益) / (1 + SPY 50 日收益)
          = (股票现价 / 50 日前价) / (SPY 现价 / 50 日前价)

    Returns
    -------
    float | None
        价格乘数比（如 1.50 表示股票价格涨幅是同期 SPY 的 1.5 倍）。
        数据不足或股票/SPY 任一缺失时返回 None。
    """
    spy_df = market_data.get(BENCHMARK)
    if spy_df is None:
        return None

    spy_sliced = _slice_to_date(spy_df, date)
    if len(spy_sliced) < LOOKBACK:
        return None
    spy_now = float(spy_sliced["close"].iloc[-1])
    spy_then = float(spy_sliced["close"].iloc[-LOOKBACK])
    if spy_then <= 0:
        return None
    # 价格乘数（不是收益），例如 SPY 从 100 → 110 = 1.10
    spy_mult = spy_now / spy_then

    df = market_data.get(symbol)
    if df is None:
        return None
    sliced = _slice_to_date(df, date)
    if len(sliced) < LOOKBACK:
        return None
    stock_now = float(sliced["close"].iloc[-1])
    stock_then = float(sliced["close"].iloc[-LOOKBACK])
    if stock_then <= 0:
        return None
    stock_mult = stock_now / stock_then

    # SPY 价格乘数 ≤ 0 时无意义（不可能，因为价格总是正数）
    if spy_mult <= 0:
        return None

    return stock_mult / spy_mult
