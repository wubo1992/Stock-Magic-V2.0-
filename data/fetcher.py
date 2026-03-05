"""
data/fetcher.py — 数据获取模块

职责：给定股票代码列表，获取日线 OHLCV 历史数据。

数据来源优先级：
1. 本地缓存（data/cache/）——最快，优先使用
2. Alpaca Market Data API——主要来源，批量下载，无限流问题
3. Yahoo Finance v8 API——备用来源，有时会被限流（403）

数据格式：pandas DataFrame，列名统一为小写 (open, high, low, close, volume)
         索引为 UTC 时区的 DatetimeIndex
"""

import os
import pickle
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests


# ─── 路径 ──────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ─── Yahoo Finance 备用接口 ────────────────────────────────────────
_YF_API = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


# ══════════════════════════════════════════════════════════════════
# 公开接口
# ══════════════════════════════════════════════════════════════════

def fetch(symbols: list[str], history_days: int) -> dict[str, pd.DataFrame]:
    """
    获取多只股票的日线历史数据。

    参数：
        symbols:       股票代码列表，如 ["AAPL", "NVDA"]
        history_days:  往前拉多少天的数据

    返回：
        {symbol: DataFrame}，DataFrame 列：open, high, low, close, volume
    """
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=history_days)

    result: dict[str, pd.DataFrame] = {}
    need_download: list[str] = []

    # 先检查缓存
    for symbol in symbols:
        cached = _load_cache(symbol, start_date, end_date)
        if cached is not None:
            result[symbol] = cached
        else:
            need_download.append(symbol)

    if not need_download:
        print(f"[数据] 全部 {len(result)} 只股票命中缓存")
        return result

    print(f"[数据] 缓存命中 {len(result)} 只，需下载 {len(need_download)} 只")

    # 优先用 Alpaca 批量下载
    alpaca_result = _fetch_via_alpaca(need_download, start_date, end_date)
    for symbol, df in alpaca_result.items():
        result[symbol] = df
        _save_cache(symbol, df)

    # 还有剩余的，用 Yahoo Finance 逐只下载
    still_missing = [s for s in need_download if s not in alpaca_result]
    if still_missing:
        print(f"[数据] Alpaca 未覆盖 {len(still_missing)} 只，尝试 Yahoo Finance...")
        yahoo_result = _fetch_via_yahoo(still_missing, start_date, end_date, history_days)
        for symbol, df in yahoo_result.items():
            result[symbol] = df
            _save_cache(symbol, df)

    print(f"[数据] 成功获取 {len(result)}/{len(symbols)} 只股票的数据")
    return result


def clear_cache(symbol: str | None = None) -> None:
    """清除缓存。不指定 symbol 则清除全部。"""
    if symbol:
        f = CACHE_DIR / f"{symbol}.pkl"
        if f.exists():
            f.unlink()
            print(f"[数据] 已清除 {symbol} 的缓存")
    else:
        for f in CACHE_DIR.glob("*.pkl"):
            f.unlink()
        print("[数据] 已清除所有缓存")


# ══════════════════════════════════════════════════════════════════
# 缓存读写
# ══════════════════════════════════════════════════════════════════

def _load_cache(
    symbol: str, start_date: datetime, end_date: datetime
) -> pd.DataFrame | None:
    """
    读取缓存。满足以下两个条件才视为有效：
    1. 最新数据在 3 天内（覆盖周末）
    2. 缓存的第一条数据不晚于需要的起始日期（允许 30 天误差）
    """
    cache_file = CACHE_DIR / f"{symbol}.pkl"
    if not cache_file.exists():
        return None

    with open(cache_file, "rb") as f:
        cached: pd.DataFrame = pickle.load(f)

    last = cached.index[-1]
    first = cached.index[0]
    if last.tzinfo is None:
        last = last.tz_localize("UTC")
    if first.tzinfo is None:
        first = first.tz_localize("UTC")

    fresh = (end_date - last).days <= 3
    covers = first <= (start_date + timedelta(days=30))

    return cached if (fresh and covers) else None


def _save_cache(symbol: str, df: pd.DataFrame) -> None:
    cache_file = CACHE_DIR / f"{symbol}.pkl"
    with open(cache_file, "wb") as f:
        pickle.dump(df, f)


# ══════════════════════════════════════════════════════════════════
# Alpaca Market Data API（主要来源）
# ══════════════════════════════════════════════════════════════════

def _fetch_via_alpaca(
    symbols: list[str], start_date: datetime, end_date: datetime
) -> dict[str, pd.DataFrame]:
    """
    用 Alpaca Historical Data API 批量下载多只股票的日线数据。

    优点：专为程序化访问设计，无限流，批量下载一次请求拿所有数据。
    需要：.env 文件中配置 ALPACA_API_KEY 和 ALPACA_SECRET_KEY。
    """
    api_key = os.environ.get("ALPACA_API_KEY", "")
    secret_key = os.environ.get("ALPACA_SECRET_KEY", "")

    if not api_key or not secret_key:
        print("[数据] 未配置 Alpaca API Key，跳过 Alpaca 下载")
        return {}

    try:
        from alpaca.data.historical import StockHistoricalDataClient
    except ImportError:
        print("[数据] alpaca-py 未安装，跳过 Alpaca 下载")
        return {}

    # Alpaca 每次最多请求 1000 只，分批处理
    BATCH = 200
    result: dict[str, pd.DataFrame] = {}
    client = StockHistoricalDataClient(api_key, secret_key)

    for i in range(0, len(symbols), BATCH):
        batch = symbols[i: i + BATCH]
        batch_result = _alpaca_fetch_batch(
            client, batch, start_date, end_date, set()
        )
        result.update(batch_result)

    if result:
        print(f"[数据] Alpaca 成功下载 {len(result)}/{len(symbols)} 只")
    return result


def _alpaca_fetch_batch(
    client,
    symbols: list[str],
    start_date: datetime,
    end_date: datetime,
    bad_symbols: set[str],
) -> dict[str, pd.DataFrame]:
    """
    Alpaca 单批次下载，遇到 "invalid symbol" 自动剔除并重试（最多剔除 10 个）。
    """
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    # 尝试导入 DataFeed（用于指定免费 IEX 数据源）
    try:
        from alpaca.data.enums import DataFeed
        feed = DataFeed.IEX
    except (ImportError, AttributeError):
        feed = "iex"

    clean = [s for s in symbols if s not in bad_symbols]
    if not clean:
        return {}

    try:
        req = StockBarsRequest(
            symbol_or_symbols=clean,
            timeframe=TimeFrame.Day,
            start=start_date.replace(tzinfo=None),
            end=end_date.replace(tzinfo=None),
            adjustment="all",
            feed=feed,   # IEX = 免费数据源；SIP 需付费订阅
        )
        bars = client.get_stock_bars(req)
        raw_df = bars.df  # MultiIndex: (symbol, timestamp)

        if raw_df.empty:
            return {}

        result: dict[str, pd.DataFrame] = {}
        for sym in raw_df.index.get_level_values("symbol").unique():
            sym_df = raw_df.xs(sym, level="symbol").copy()
            keep = [c for c in ["open", "high", "low", "close", "volume"] if c in sym_df.columns]
            sym_df = sym_df[keep]
            if sym_df.index.tzinfo is None:
                sym_df.index = sym_df.index.tz_localize("UTC")
            sym_df = sym_df.dropna()
            sym_df = sym_df[sym_df["volume"] > 0]
            if not sym_df.empty:
                result[sym] = sym_df
        return result

    except Exception as e:
        err_str = str(e)
        # 尝试从错误信息中提取无效 symbol，例如 {"message":"invalid symbol: BRK-B"}
        m = re.search(r"invalid symbol[:\s]+([A-Z0-9./\-]+)", err_str, re.IGNORECASE)
        if m and len(bad_symbols) < 10:
            bad_sym = m.group(1).strip('",}')
            print(f"[数据] Alpaca 跳过无效代码：{bad_sym}")
            bad_symbols.add(bad_sym)
            return _alpaca_fetch_batch(client, symbols, start_date, end_date, bad_symbols)
        else:
            print(f"[数据] Alpaca 批次失败：{e}")
            return {}


# ══════════════════════════════════════════════════════════════════
# Yahoo Finance v8 API（备用来源）
# ══════════════════════════════════════════════════════════════════

def _fetch_via_yahoo(
    symbols: list[str],
    start_date: datetime,
    end_date: datetime,
    history_days: int,
) -> dict[str, pd.DataFrame]:
    """逐只从 Yahoo Finance 下载，每只之间等待 2 秒防限流。"""
    result: dict[str, pd.DataFrame] = {}
    session = requests.Session()
    session.headers.update(_HEADERS)

    for symbol in symbols:
        time.sleep(2)
        df = _yahoo_download_one(symbol, history_days, session)
        if df is not None and not df.empty:
            result[symbol] = df
        else:
            print(f"[数据] 警告：{symbol} 无法获取数据，已跳过")

    return result


def _yahoo_download_one(
    symbol: str, history_days: int, session: requests.Session
) -> pd.DataFrame | None:
    """单只股票的 Yahoo Finance 下载，最多重试 3 次。"""
    print(f"[数据] Yahoo 下载 {symbol}...")
    for attempt in range(3):
        if attempt > 0:
            wait = 15 * attempt
            print(f"[数据]   重试中，等待 {wait}s...")
            time.sleep(wait)
        try:
            url = _YF_API.format(symbol=symbol)
            params = {"interval": "1d", "range": _days_to_range(history_days)}
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code == 403:
                print(f"[数据]   {symbol} 被限流（403）")
                continue
            resp.raise_for_status()
            df = _parse_yahoo_response(resp.json())
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[数据]   {symbol} 第 {attempt+1} 次失败：{e}")
    return None


def _parse_yahoo_response(data: dict) -> pd.DataFrame | None:
    chart = data.get("chart", {})
    if chart.get("error"):
        return None
    results = chart.get("result")
    if not results:
        return None
    result = results[0]
    timestamps = result.get("timestamp", [])
    if not timestamps:
        return None
    quotes = result["indicators"]["quote"][0]
    adjclose_list = result["indicators"].get("adjclose", [{}])
    adjclose = adjclose_list[0].get("adjclose") if adjclose_list else None
    df = pd.DataFrame(
        {
            "open":   quotes.get("open", []),
            "high":   quotes.get("high", []),
            "low":    quotes.get("low", []),
            "close":  adjclose if adjclose else quotes.get("close", []),
            "volume": quotes.get("volume", []),
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True),
    )
    df.index.name = "date"
    df = df.dropna()
    df = df[df["volume"] > 0]
    return df


def _days_to_range(history_days: int) -> str:
    if history_days <= 5:      return "5d"
    if history_days <= 30:     return "1mo"
    if history_days <= 90:     return "3mo"
    if history_days <= 180:    return "6mo"
    if history_days <= 365:    return "1y"
    if history_days <= 730:    return "2y"
    if history_days <= 1825:   return "5y"
    return "10y"
