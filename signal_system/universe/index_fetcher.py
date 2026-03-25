"""
universe/index_fetcher.py — 指数成分股获取模块

支持的指数：
  - sp500:     标普500（约 500 只）
  - nasdaq100: 纳斯达克100（约 100 只）

数据来源：Wikipedia（免费，无需 API Key）
缓存策略：本地 JSON，永久缓存，不自动刷新
缓存文件：data/index_cache.json
"""

import json
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

CACHE_FILE = Path(__file__).parent.parent / "data" / "index_cache.json"
CACHE_MAX_AGE_DAYS = 9999   # 永久本地缓存，不再自动刷新

_URLS = {
    "sp500":     "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "nasdaq100": "https://en.wikipedia.org/wiki/Nasdaq-100",
}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
_TICKER_COLS = {
    "sp500":     "Symbol",
    "nasdaq100": "Ticker",
}


def get_index_symbols(indices: list[str]) -> list[str]:
    """
    获取指定指数成分股代码列表，自动管理本地永久缓存。

    参数：
        indices: 指数 ID 列表，支持 "sp500" / "nasdaq100"

    返回：
        去重排序后的股票代码列表
    """
    cache = _load_cache()
    result: list[str] = []

    for idx in indices:
        if _cache_fresh(cache, idx):
            symbols = cache[idx]["symbols"]
            print(f"[股票池] 指数 {idx}：{len(symbols)} 只（本地缓存）")
            result.extend(symbols)
        else:
            symbols = _fetch_index(idx)
            if symbols:
                cache[idx] = {
                    "symbols": symbols,
                    "updated_at": datetime.now().strftime("%Y-%m-%d"),
                }
                _save_cache(cache)
                print(f"[股票池] 指数 {idx}：{len(symbols)} 只（已更新缓存）")
                result.extend(symbols)
            elif idx in cache:
                # 网络失败时回退到旧缓存
                symbols = cache[idx]["symbols"]
                updated = cache[idx].get("updated_at", "未知")
                print(f"[股票池] 指数 {idx}：获取失败，使用旧缓存（{updated}），{len(symbols)} 只")
                result.extend(symbols)
            else:
                print(f"[股票池] 指数 {idx}：获取失败且无本地缓存，跳过")

    return sorted(set(result))


def _fetch_index(index_id: str) -> list[str]:
    """从 Wikipedia 下载指定指数的成分股列表。"""
    url = _URLS.get(index_id)
    ticker_col = _TICKER_COLS.get(index_id)
    if not url or not ticker_col:
        print(f"[股票池] 未知指数 ID：{index_id}")
        return []

    print(f"[股票池] 从 Wikipedia 下载 {index_id} 成分股...")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text), header=0)
    except Exception as e:
        print(f"[股票池] Wikipedia 请求失败 ({index_id})：{e}")
        return []

    for df in tables:
        if ticker_col in df.columns:
            raw = df[ticker_col].dropna().astype(str).tolist()
            # BRK.B → BRK-B（Alpaca 用连字符，Yahoo 用点）
            symbols = [s.strip().replace(".", "-") for s in raw]
            # 过滤非 ticker 字符串（只保留纯字母 + 连字符，1-10位）
            symbols = [
                s for s in symbols
                if 1 <= len(s) <= 10 and s.replace("-", "").isalpha()
            ]
            return sorted(set(symbols))

    print(f"[股票池] Wikipedia 页面未找到 '{ticker_col}' 列（{index_id}）")
    return []


def _cache_fresh(cache: dict, index_id: str) -> bool:
    """判断指定指数的缓存是否存在（永久缓存，永不过期）。"""
    if index_id not in cache:
        return False
    updated_str = cache[index_id].get("updated_at", "")
    try:
        updated = datetime.strptime(updated_str, "%Y-%m-%d")
        return (datetime.now() - updated).days <= CACHE_MAX_AGE_DAYS
    except ValueError:
        return False


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
