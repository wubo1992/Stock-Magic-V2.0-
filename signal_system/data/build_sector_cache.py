"""
data/build_sector_cache.py — 构建股票-板块映射缓存

数据源：Wikipedia SP500 列表（含 GICS Sector）
板块定义标准：GICS 11 大板块

输出：data/sector_cache.json — {ticker: {sector, sub_industry, source}, ...}
"""
import json
import re
import urllib.request
from pathlib import Path

CACHE_PATH = Path(__file__).parent / "sector_cache.json"


def fetch_sp500_with_sector():
    """从 Wikipedia 拉取 SP500 成分股 + GICS Sector"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    text = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    tables = re.findall(r"<table[^>]*>(.*?)</table>", text, re.DOTALL)

    result = {}
    for t in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.DOTALL)
        if len(rows) < 500:
            continue
        # 跳过表头
        for row in rows[1:]:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL)
            if len(cells) < 4:
                continue
            ticker = re.sub(r"<[^>]+>", "", cells[0]).strip()
            sector = re.sub(r"<[^>]+>", "", cells[2]).strip()
            sub_ind = re.sub(r"<[^>]+>", "", cells[3]).strip()
            if ticker and sector:
                # Wikipedia 的 ticker 把 . 替换成 -
                result[ticker] = {
                    "sector": sector,
                    "sub_industry": sub_ind,
                    "source": "sp500_wiki",
                }
        break
    return result


def main():
    print("[板块缓存] 从 Wikipedia 拉取 SP500 板块信息...")
    sector_map = fetch_sp500_with_sector()
    print(f"[板块缓存] 获取 {len(sector_map)} 只 SP500 成分股板块")

    # 加载已有缓存（保留手工或 yfinance 补充的）
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r") as f:
            existing = json.load(f)
        print(f"[板块缓存] 已有缓存 {len(existing)} 只，保留非 Wikipedia 来源")
        # 只保留非 wikipedia 来源的覆盖
        for t, info in existing.items():
            if info.get("source") != "sp500_wiki":
                sector_map[t] = info
    else:
        existing = {}

    with open(CACHE_PATH, "w") as f:
        json.dump(sector_map, f, ensure_ascii=False, indent=2)

    # 显示板块分布
    from collections import Counter
    sectors = Counter(v["sector"] for v in sector_map.values())
    print("[板块缓存] 板块分布:")
    for s, n in sectors.most_common():
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()