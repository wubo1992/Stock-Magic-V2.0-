"""
data/fetcher.py — 数据获取模块

职责：给定股票代码列表，获取日线 OHLCV 历史数据。

数据来源（三层优先级）：
1. 本地持久化存储（data/cache/）
   - 永久保存，无过期删除
   - 若数据足够新（实盘 ≤0天，回测 ≤3天）直接使用，零网络请求
2. 增量更新（本地有历史但不够新）
   - 只从最早的缺口日期起，批量下载 delta 数据，合并后写回本地
   - 例：本地数据到 3月4日，今天3月6日 → 只下载 3月5日~6日 两天的新数据
3. 全量下载（本地无数据或历史不足）
   - Alpaca Market Data API（主）→ Yahoo Finance v8（备）

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

def fetch(
    symbols: list[str], history_days: int, live_mode: bool = False
) -> dict[str, pd.DataFrame]:
    """
    获取多只股票的日线历史数据。

    三层策略：
    1. 本地数据足够新 → 直接使用，无网络请求
    2. 本地有历史但不够新 → 增量下载 delta，合并后写回
    3. 本地无数据或历史不足 → 全量下载

    参数：
        symbols:       股票代码列表，如 ["AAPL", "NVDA"]
        history_days:  往前拉多少天的数据
        live_mode:     实盘模式时设为 True，强制要求最新收盘数据（当天或上一交易日）
                       回测模式设为 False，允许 3 天缓存宽容（覆盖周末/节假日）

    返回：
        {symbol: DataFrame}，DataFrame 列：open, high, low, close, volume
    """
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=history_days)

    result: dict[str, pd.DataFrame] = {}
    need_full: list[str] = []                         # 无本地数据，全量下载
    need_update: list[tuple[str, pd.DataFrame]] = []  # 有本地数据但需增量更新

    # ── 第一步：三分类 ────────────────────────────────────────────
    for symbol in symbols:
        local = _load_local(symbol, start_date)
        if local is None:
            need_full.append(symbol)
        else:
            last = local.index[-1]
            if last.tzinfo is None:
                last = last.tz_localize("UTC")
            max_age = 0 if live_mode else 3
            if (end_date - last).days <= max_age:
                # Tier 1：本地数据足够新，直接使用
                result[symbol] = local
            else:
                # Tier 2：本地有历史，但需要增量补充
                need_update.append((symbol, local))

    print(
        f"[数据] 本地直接使用 {len(result)} 只，"
        f"增量更新 {len(need_update)} 只，"
        f"全量下载 {len(need_full)} 只"
    )

    # ── 第二步：全量下载 ──────────────────────────────────────────
    if need_full:
        alpaca_result = _fetch_via_alpaca(need_full, start_date, end_date)
        for symbol, df in alpaca_result.items():
            result[symbol] = df
            _save_local(symbol, df)

        still_missing = [s for s in need_full if s not in alpaca_result]
        if still_missing:
            print(f"[数据] Alpaca 未覆盖 {len(still_missing)} 只，尝试 Yahoo Finance...")
            yahoo_result = _fetch_via_yahoo(still_missing, start_date, end_date, history_days)
            for symbol, df in yahoo_result.items():
                result[symbol] = df
                _save_local(symbol, df)

    # ── 第三步：增量更新 ──────────────────────────────────────────
    if need_update:
        update_symbols = [s for s, _ in need_update]

        # 从所有待更新股票中取最早的 last_date，批量一次请求拿到所有 delta
        min_last = min(
            (df.index[-1].tz_localize("UTC") if df.index[-1].tzinfo is None else df.index[-1])
            for _, df in need_update
        )
        delta_start = min_last + timedelta(days=1)

        print(
            f"[数据] 增量下载 {len(update_symbols)} 只，"
            f"从 {delta_start.strftime('%Y-%m-%d')} 起"
        )

        new_data = _fetch_via_alpaca(update_symbols, delta_start, end_date)

        # Alpaca 不支持的股票（如 BRK-B、BF-B）走 Yahoo Finance 增量补充
        alpaca_missed = [s for s, _ in need_update if s not in new_data]
        if alpaca_missed:
            print(f"[数据] 增量更新：Alpaca 未覆盖 {len(alpaca_missed)} 只，尝试 Yahoo Finance...")
            yahoo_delta = _fetch_via_yahoo(alpaca_missed, delta_start, end_date, 30)
            new_data.update(yahoo_delta)

        for symbol, existing_df in need_update:
            new_rows = new_data.get(symbol)
            if new_rows is not None and not new_rows.empty:
                merged = pd.concat([existing_df, new_rows])
                merged = merged[~merged.index.duplicated(keep="last")]
                merged = merged.sort_index()
                result[symbol] = merged
                _save_local(symbol, merged)
            else:
                # delta 为空（节假日或 API 暂无数据），使用现有本地数据
                result[symbol] = existing_df

    print(f"[数据] 成功获取 {len(result)}/{len(symbols)} 只股票的数据")
    return result


def clear_cache(symbol: str | None = None) -> None:
    """清除本地持久化数据。不指定 symbol 则清除全部。"""
    if symbol:
        f = CACHE_DIR / f"{symbol}.pkl"
        if f.exists():
            f.unlink()
            print(f"[数据] 已清除 {symbol} 的本地数据")
    else:
        for f in CACHE_DIR.glob("*.pkl"):
            f.unlink()
        print("[数据] 已清除所有本地数据")


# ══════════════════════════════════════════════════════════════════
# 本地持久化读写（永久存储，不做时效性判断）
# ══════════════════════════════════════════════════════════════════

def _load_local(symbol: str, start_date: datetime) -> pd.DataFrame | None:
    """
    读取本地持久化数据。

    只做历史覆盖检查，不做时效性判断（时效由 fetch() 外层处理）：
    - 若本地数据的第一条不晚于所需起始日期（允许 30 天误差），则返回
    - 否则返回 None，触发全量下载
    """
    cache_file = CACHE_DIR / f"{symbol}.pkl"
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "rb") as f:
            df: pd.DataFrame = pickle.load(f)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    first = df.index[0]
    if first.tzinfo is None:
        first = first.tz_localize("UTC")

    # 检查历史覆盖：本地数据起始点不能比所需起点晚太多
    if first > start_date + timedelta(days=30):
        return None

    return df


def _save_local(symbol: str, df: pd.DataFrame) -> None:
    """将 DataFrame 写入本地持久化存储（覆盖旧文件）。"""
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
