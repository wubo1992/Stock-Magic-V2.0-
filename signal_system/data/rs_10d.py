"""
data/rs_10d.py — 10 个交易日（≈ 2 周）相对强度

公式（IBD 标准价格乘数比，与 rs_10w.py 同样的形式）：
    R_10D(t)    = close(t) / close(t-10) - 1           ← 10 日简单收益率
    RS-10D(t)   = (1 + R_10D(ticker)) / (1 + R_10D(SPY))   ← 价格乘数比

含义（IBD 标准解读）：
    - 1.00x = 股票与 SPY 完全同步
    - 1.10x = 10 个交易日涨幅是 SPY 的 1.1 倍
    - 1.20x = 短期强动量（突破通常需要这种水平）
    - 0.90x = 10 个交易日跑输 SPY

为什么同时有 RS10W 和 RS10D？
    - RS10W（10 周/50 日）：看中期趋势，过滤"刚启动的偶然突破"
    - RS10D（2 周/10 日）：看近期动量，捕捉"刚启动的爆发股"
    - 两者差异大 → 刚启动（RS10D >> RS10W）
    - 两者都高 → 已强势运行一段时期

基准固定为 SPY（不管港股台股，因为用户只问"对比标普"）。
"""

from __future__ import annotations

from datetime import timezone

import pandas as pd

BENCHMARK = "SPY"
LOOKBACK = 10  # 10 个交易日 ≈ 2 周


def _slice_to_date(df: pd.DataFrame, date) -> pd.DataFrame:
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    idx = df.index
    if idx.tzinfo is None:
        idx = idx.tz_localize("UTC")
        df = df.copy()
        df.index = idx
    return df[df.index <= date]


def compute_rs_10d(
    symbol: str,
    market_data: dict[str, pd.DataFrame],
    date,
) -> float | None:
    """
    RS-10D = (1 + 股票 10 日收益) / (1 + SPY 10 日收益)
          = (股票现价 / 10 日前价) / (SPY 现价 / 10 日前价)

    Returns
    -------
    float | None
        价格乘数比（如 1.10 表示股票 10 日涨幅是 SPY 的 1.1 倍）。
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

    if spy_mult <= 0:
        return None

    return stock_mult / spy_mult
