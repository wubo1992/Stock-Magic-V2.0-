"""
data/fetch_finnhub_sectors.py — 用 Finnhub API 填充板块缓存

策略：
1. 读取现有 sector_cache.json（SP500 数据）
2. 对未在缓存中的 ticker，调用 Finnhub profile2 接口获取 sector
3. Finnhub 的 finnhubIndustry 较细，再映射到 GICS 11 大板块
4. 限流：60 calls/min，sleep 1.1s

用法：uv run python data/fetch_finnhub_sectors.py [ticker1 ticker2 ...]
"""
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

CACHE_PATH = Path(__file__).parent / "sector_cache.json"

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

# Finnhub industry → GICS 11 大板块 映射（人工整理，覆盖常见分类）
# 其他常见但前面未列出的 Finnhub industry → GICS 板块
GICS_EXTRA = {
    "Electrical Equipment": "Industrials",
    "Commercial Services & Supplies": "Industrials",
    "Consumer products": "Consumer Discretionary",
    "Communications": "Communication Services",
    "Textiles, Apparel & Luxury Goods": "Consumer Discretionary",
    "Diversified Consumer Services": "Consumer Discretionary",
    "Leisure Products": "Consumer Discretionary",
    "Automobiles": "Consumer Discretionary",
    "Trading Companies & Distributors": "Industrials",
    "Food Products": "Consumer Staples",
    "Airlines": "Industrials",
    "Building": "Industrials",
    "Auto Components": "Consumer Discretionary",
    "Industrial Conglomerates": "Industrials",
    "Packaging": "Materials",
}


def _to_gics(fh_industry: str) -> str:
    """Finnhub industry → GICS sector"""
    if not fh_industry or fh_industry == "N/A":
        return "N/A"
    return GICS_MAP.get(fh_industry) or GICS_EXTRA.get(fh_industry) or "Other"


GICS_MAP = {
    # Information Technology
    "Technology": "Information Technology",
    "Software": "Information Technology",
    "Semiconductors": "Information Technology",
    "Computer Hardware": "Information Technology",
    "IT Services": "Information Technology",
    "Electronics & Computer Distribution": "Information Technology",
    # Communication Services
    "Telecommunication": "Communication Services",
    "Media": "Communication Services",
    "Entertainment": "Communication Services",
    "Internet Content & Information": "Communication Services",
    # Consumer Discretionary
    "Retail": "Consumer Discretionary",
    "Hotels, Restaurants & Leisure": "Consumer Discretionary",
    "Auto - Manufacturers": "Consumer Discretionary",
    "Auto - Parts": "Consumer Discretionary",
    "Apparel": "Consumer Discretionary",
    "Household & Personal Products": "Consumer Discretionary",
    "Specialty Retail": "Consumer Discretionary",
    "Travel & Leisure": "Consumer Discretionary",
    # Consumer Staples
    "Beverages - Alcoholic": "Consumer Staples",
    "Beverages - Non-Alcoholic": "Consumer Staples",
    "Food Production": "Consumer Staples",
    "Tobacco": "Consumer Staples",
    "Household Products": "Consumer Staples",
    "Drug Retail": "Consumer Staples",
    "Grocery Stores": "Consumer Staples",
    "Food Distribution": "Consumer Staples",
    # Health Care
    "Health Care": "Health Care",
    "Pharmaceuticals": "Health Care",
    "Medical Devices": "Health Care",
    "Medical Instruments & Supplies": "Health Care",
    "Biotechnology": "Health Care",
    "Life Sciences Tools & Services": "Health Care",
    "Health Care Plans": "Health Care",
    "Drug Manufacturers": "Health Care",
    # Financials
    "Banking": "Financials",
    "Financial Services": "Financials",
    "Insurance": "Financials",
    "Capital Markets": "Financials",
    "Real Estate": "Financials",
    # Real Estate
    "REIT - Diversified": "Real Estate",
    "REIT - Residential": "Real Estate",
    "REIT - Office": "Real Estate",
    "REIT - Retail": "Real Estate",
    "REIT - Industrial": "Real Estate",
    "REIT - Healthcare": "Real Estate",
    "REIT - Specialty": "Real Estate",
    "Real Estate - Development": "Real Estate",
    "Real Estate - Services": "Real Estate",
    # Industrials
    "Aerospace & Defense": "Industrials",
    "Transportation": "Industrials",
    "Road & Rail": "Industrials",
    "Marine": "Industrials",
    "Air Freight & Logistics": "Industrials",
    "Construction": "Industrials",
    "Engineering & Construction": "Industrials",
    "Industrial Products": "Industrials",
    "Machinery": "Industrials",
    "Specialty Chemicals": "Industrials",
    "Transportation Infrastructure": "Industrials",
    "Waste Management": "Industrials",
    "Staffing & Employment Services": "Industrials",
    # Energy
    "Energy": "Energy",
    "Oil & Gas": "Energy",
    "Oil & Gas - E&P": "Energy",
    "Oil & Gas - Refining & Marketing": "Energy",
    "Oil & Gas - Services": "Energy",
    "Oil & Gas - Midstream": "Energy",
    "Uranium": "Energy",
    "Coal": "Energy",
    "Renewable Energy": "Energy",
    # Materials
    "Metals & Mining": "Materials",
    "Steel": "Materials",
    "Chemicals": "Materials",
    "Agricultural Inputs": "Materials",
    "Paper & Forest Products": "Materials",
    "Building Materials": "Materials",
    "Gold": "Materials",
    "Silver": "Materials",
    "Copper": "Materials",
    # Utilities
    "Utilities": "Utilities",
    "Utilities - Regulated": "Utilities",
    "Utilities - Renewable": "Utilities",
    "Utilities - Independent Power Producers": "Utilities",
    # 未匹配 → Other
    "Professional Services": "Industrials",
    "Consulting": "Industrials",
    "Advertising": "Communication Services",
    "Education": "Consumer Discretionary",
}


def fetch_one(ticker: str) -> dict | None:
    """调用 Finnhub 获取单只股票 sector"""
    if not FINNHUB_KEY:
        print("[错误] FINNHUB_API_KEY 未设置")
        sys.exit(1)
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={FINNHUB_KEY}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        # Finnhub 对未知 ticker 返回空 dict
        if not data or "finnhubIndustry" not in data:
            return None
        return {
            "sector": _to_gics(data["finnhubIndustry"]),
            "sub_industry": data["finnhubIndustry"],
            "source": "finnhub",
        }
    except Exception as e:
        print(f"  {ticker} 异常: {e}")
        return None


def main(targets: list[str] | None = None):
    if not CACHE_PATH.exists():
        cache = {}
    else:
        with open(CACHE_PATH) as f:
            cache = json.load(f)

    # 默认：当前 output 目录里所有报告的 ticker
    if targets is None:
        targets = []
        output_dir = Path(__file__).parent.parent / "output"
        for d in output_dir.iterdir():
            if not d.is_dir() or d.name == "shared":
                continue
            for sub in d.iterdir():
                if not sub.is_dir():
                    continue
                for md in sub.glob("*.md"):
                    text = md.read_text()
                    import re
                    tickers = re.findall(r"今日新增\*\* — 买入 (\S+)", text)
                    targets.extend(tickers)
        targets = sorted(set(targets))

    # 只处理缓存里没有的
    to_fetch = [t for t in targets if t not in cache]
    print(f"[Finnhub] 总目标 {len(targets)} 只，缓存已有 {len(targets)-len(to_fetch)} 只，待获取 {len(to_fetch)} 只")

    if not to_fetch:
        print("[Finnhub] 无需获取")
        return

    added = 0
    for i, t in enumerate(to_fetch):
        info = fetch_one(t)
        if info:
            cache[t] = info
            added += 1
        if (i + 1) % 50 == 0:
            print(f"  进度 {i+1}/{len(to_fetch)}，新增 {added}")
            with open(CACHE_PATH, "w") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        time.sleep(1.1)  # 60 calls/min

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"[Finnhub] 新增 {added}/{len(to_fetch)} 只")
    print(f"[Finnhub] 缓存总数: {len(cache)}")

    # 板块分布
    from collections import Counter
    sectors = Counter(v["sector"] for v in cache.values())
    print("[Finnhub] 板块分布:")
    for s, n in sectors.most_common():
        print(f"  {s}: {n}")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    main(targets)