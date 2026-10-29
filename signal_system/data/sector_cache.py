"""
data/sector_cache.py — 板块缓存读取接口
"""
import json
from pathlib import Path

CACHE_PATH = Path(__file__).parent / "sector_cache.json"

# 加载一次，进程内复用
_cache = None


def _load():
    global _cache
    if _cache is None:
        if CACHE_PATH.exists():
            with open(CACHE_PATH) as f:
                _cache = json.load(f)
        else:
            _cache = {}
    return _cache


def get_sector(ticker: str) -> str:
    """返回 ticker 所属 GICS 板块；未知返回 'N/A'"""
    cache = _load()
    # 处理 BRK.B / BF.B 这类 Wikipedia 写成 BRK-B 的情况
    for k in (ticker, ticker.replace(".", "-")):
        if k in cache:
            return cache[k]["sector"]
    return "N/A"


def get_sub_industry(ticker: str) -> str:
    cache = _load()
    for k in (ticker, ticker.replace(".", "-")):
        if k in cache:
            return cache[k].get("sub_industry", "")
    return ""


def get_stats() -> dict:
    """返回缓存统计信息"""
    cache = _load()
    from collections import Counter
    sectors = Counter(v["sector"] for v in cache.values())
    return {"total": len(cache), "by_sector": dict(sectors)}