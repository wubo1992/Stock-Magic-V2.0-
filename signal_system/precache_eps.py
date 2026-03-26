"""
precache_eps.py — EPS 数据预缓存脚本

在运行 v_eps_v2 完整回测之前，先批量填充 EPS 缓存，
避免回测过程中逐日调用 Alpha Vantage API（每天限制 25 次）。

用法：
    uv run python precache_eps.py

Alpha Vantage 免费版限制：5 次/分钟，25 次/天
本脚本会自动限速，分多天完成所有股票的 EPS 预缓存。
"""

import os
import sys
import time
import pickle
import requests
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

EPS_CACHE_DIR = Path(__file__).parent / "data" / "cache" / "eps"
EPS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _eps_cache_path(symbol: str) -> Path:
    return EPS_CACHE_DIR / f"{symbol}.pkl"


def _save_to_cache(symbol: str, eps_history: list) -> None:
    cache_path = _eps_cache_path(symbol)
    try:
        with open(cache_path, "wb") as f:
            pickle.dump({'eps_history': eps_history}, f)
        print(f"  [缓存] {symbol} 已保存 ({len(eps_history)} 季度)")
    except Exception as e:
        print(f"  [错误] {symbol} 缓存失败: {e}")


def _fetch_eps(symbol: str) -> list:
    """从 Alpha Vantage 获取 EPS 数据（带限速）"""
    params = {
        "function": "EARNINGS",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    resp = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  [错误] {symbol} HTTP {resp.status_code}")
        return []

    data = resp.json()

    if "quarterlyEarnings" not in data:
        msg = data.get('Note', data.get('Error Message', 'unknown'))
        print(f"  [跳过] {symbol}: {msg}")
        return []

    quarterly = data.get("quarterlyEarnings", [])
    if not quarterly:
        return []

    eps_history = []
    for item in quarterly:
        eps_str = item.get("reportedEPS")
        if eps_str is None or eps_str == "None":
            continue
        try:
            eps = float(eps_str)
            fiscal_date = item.get("fiscalDateEnding", "")
            eps_history.append((fiscal_date, eps))
        except (ValueError, TypeError):
            continue

    return eps_history


def get_backtest_universe() -> list:
    """从 UNIVERSE.md 读取股票池"""
    import re
    universe_path = Path(__file__).parent / "UNIVERSE.md"
    content = universe_path.read_text()
    # 匹配 | CODE | Name | ... 格式，提取股票代码
    HEADER_ROWS = {'CODE', 'STOCK', 'SYMBOL', 'TICKER'}
    symbols = []
    seen = set()
    for line in content.split('\n'):
        m = re.match(r'\|\s*([A-Z]{1,5})\s*\|', line)
        if m:
            code = m.group(1)
            if code not in HEADER_ROWS and code not in seen:
                seen.add(code)
                symbols.append(code)
    return symbols


def is_cache_valid(symbol: str) -> bool:
    """检查缓存是否有效（90天内）"""
    cache_path = _eps_cache_path(symbol)
    if not cache_path.exists():
        return False
    import datetime
    from datetime import timezone
    mtime = datetime.datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)
    age = datetime.datetime.now(tz=timezone.utc) - mtime
    return age.days < 90


def main():
    print("=" * 60)
    print("EPS 数据预缓存脚本")
    print("Alpha Vantage 免费版: 5次/分钟，25次/天")
    print("=" * 60)

    if not ALPHA_VANTAGE_API_KEY:
        print("[错误] 未配置 ALPHA_VANTAGE_API_KEY")
        return

    symbols = get_backtest_universe()
    print(f"股票池共 {len(symbols)} 只\n")

    # 统计需要缓存和已有缓存的
    need_cache = []
    already_cached = []
    for s in symbols:
        if is_cache_valid(s):
            already_cached.append(s)
        else:
            need_cache.append(s)

    print(f"已有有效缓存: {len(already_cached)} 只")
    print(f"需要获取:     {len(need_cache)} 只")

    if not need_cache:
        print("\n所有股票 EPS 已缓存完毕，直接运行回测即可！")
        return

    print(f"\n开始获取 EPS 数据（每天 25 次限制）...")
    print(f"预计需要 {(len(need_cache) + 24) // 25} 天完成\n")

    success = 0
    skipped = 0
    api_errors = 0

    for i, symbol in enumerate(need_cache):
        # 检查是否达到每日限制（通过尝试判断）
        # Alpha Vantage 返回 "Thank you" Note 表示已达限制

        print(f"[{i+1}/{len(need_cache)}] {symbol}...", end=" ")

        eps_history = _fetch_eps(symbol)

        if "Thank you" in str(eps_history) or eps_history == []:
            # API 频率限制，再检查一次
            # 重新尝试
            time.sleep(60)  # 等 1 分钟
            eps_history = _fetch_eps(symbol)

        if not eps_history or (isinstance(eps_history, list) and len(eps_history) == 0 and "Thank you" not in str(eps_history)):
            # 检查是否是无数据
            if "无" in str(eps_history) or "unknown" in str(eps_history):
                skipped += 1
            else:
                api_errors += 1
            time.sleep(15)  # 等 15 秒
            continue

        _save_to_cache(symbol, eps_history)
        success += 1

        # Alpha Vantage 免费版 5 次/分钟限速
        time.sleep(15)  # 12 次/分钟，留点余量

    print("\n" + "=" * 60)
    print(f"预缓存完成！")
    print(f"  成功: {success} 只")
    print(f"  跳过（无数据）: {skipped} 只")
    print(f"  API 错误: {api_errors} 只")
    print("=" * 60)
    print("\n现在可以运行完整回测：")
    print("uv run python main.py --mode backtest --start 2020-01-01 --end 2024-12-30 --strategy v_eps_v2")


if __name__ == "__main__":
    main()
