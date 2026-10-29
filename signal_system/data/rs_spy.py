"""
data/rs_spy.py — 计算相对强度（RS vs SPY）

公式：RS = (1 + 股票N日收益) / (1 + SPY N日收益)
>1 表示跑赢 SPY，<1 表示跑输

默认使用 60 日（约 3 个月）窗口，符合中期动量
"""
import pandas as pd
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_WINDOW = 50  # 10 周 × 5 交易日 ≈ 10 周动量


def _spy_return(window: int = DEFAULT_WINDOW) -> float | None:
    spy_path = CACHE_DIR / "SPY.pkl"
    if not spy_path.exists():
        return None
    spy = pd.read_pickle(spy_path)
    if len(spy) < window + 1:
        return None
    return spy["close"].iloc[-1] / spy["close"].iloc[-window - 1] - 1


def calc_rs_spy(ticker: str, window: int = DEFAULT_WINDOW) -> float | None:
    """
    计算 ticker 的 RS/SPY。

    返回值含义：
        1.20 = 该股过去 60 日涨幅比 SPY 多 20%（即 SPY 涨 10%，该股涨 12%）
        0.80 = 跑输 SPY 20%
        None = 数据不足
    """
    spy_ret = _spy_return(window)
    if spy_ret is None:
        return None

    p = CACHE_DIR / f"{ticker}.pkl"
    if not p.exists():
        return None
    df = pd.read_pickle(p)
    if len(df) < window + 1:
        return None

    stock_ret = df["close"].iloc[-1] / df["close"].iloc[-window - 1] - 1
    # (1+stock) / (1+spy) → 比率
    return (1 + stock_ret) / (1 + spy_ret)


def calc_rs_spy_batch(tickers: list[str], window: int = DEFAULT_WINDOW) -> dict[str, float]:
    """批量计算，返回 {ticker: rs_spy or None}"""
    spy_ret = _spy_return(window)
    if spy_ret is None:
        return {t: None for t in tickers}
    spy_factor = 1 + spy_ret

    result = {}
    for t in tickers:
        p = CACHE_DIR / f"{t}.pkl"
        if not p.exists():
            result[t] = None
            continue
        df = pd.read_pickle(p)
        if len(df) < window + 1:
            result[t] = None
            continue
        stock_ret = df["close"].iloc[-1] / df["close"].iloc[-window - 1] - 1
        result[t] = (1 + stock_ret) / spy_factor
    return result