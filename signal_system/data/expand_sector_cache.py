"""
扩展 sector_cache：补充 Nasdaq 100 + 港股 + 其他代码
"""
import json
import re
import urllib.request
from pathlib import Path

CACHE_PATH = Path(__file__).parent / "sector_cache.json"


def fetch_nasdaq100():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    text = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

    # 找 GICS sector 表格
    tables = re.findall(r"<table[^>]*>(.*?)</table>", text, re.DOTALL)
    result = {}
    for t in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.DOTALL)
        if len(rows) < 50:
            continue
        # 检查表头是否含 GICS
        header = re.sub(r"<[^>]+>", "", rows[0]) if rows else ""
        if "GICS" not in header and "Sector" not in header:
            continue
        for row in rows[1:]:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL)
            if len(cells) < 5:
                continue
            ticker = re.sub(r"<[^>]+>", "", cells[0]).strip()
            sector = re.sub(r"<[^>]+>", "", cells[4]).strip() if len(cells) > 4 else ""
            if ticker and sector and sector not in ("", "—"):
                result[ticker] = {"sector": sector, "sub_industry": "", "source": "nasdaq100_wiki"}
    return result


def main():
    with open(CACHE_PATH) as f:
        cache = json.load(f)

    print("[扩展] 拉取 Nasdaq 100...")
    ndx = fetch_nasdaq100()
    print(f"[扩展] 获取 {len(ndx)} 只")

    added = 0
    for t, info in ndx.items():
        if t not in cache:
            cache[t] = info
            added += 1
    print(f"[扩展] 新增 {added} 只 Nasdaq 100 标的")

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"[扩展] 缓存总数: {len(cache)}")
    from collections import Counter
    sectors = Counter(v["sector"] for v in cache.values())
    print("[扩展] 板块分布:")
    for s, n in sectors.most_common(15):
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()