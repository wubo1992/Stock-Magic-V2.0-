"""
universe/us_market.py — 美股全市场普通股名单

用途：给 RS 相对强度评级提供**稳定的分母**。
项目自己的股票池是「手动池 ∪ 指数池 ∪ Alpaca 新闻池」，每天都在漂
（新闻池每次运行会多几只），用它当分母的话，同一只股票的 RS 会因为
分母变了而变，跨日不可比。所以 RS 单独用一份全市场名单。

数据来源：Nasdaq Trader SymDir（免费、无需 API Key、每日更新）
  - nasdaqlisted.txt  纳斯达克 + NYSE + NYSE American + NYSE Arca 的挂牌证券
  - otherlisted.txt   其他交易所挂牌的证券（字段名是 ACT Symbol 而非 Symbol）
  两个文件合计约 1.3 万条挂牌记录，筛出普通股约 5200 只。

筛选规则分两套，因为两个文件的 Security Name 写法不一样（这是踩过的坑）：

  nasdaqlisted.txt —— 名称一定带证券类型后缀，"Visa Inc. Common Stock"
    所以用白名单：名称里必须出现普通股特征词才保留。外资公司在美上市写的是
    Ordinary Shares（Amer Sports / Similarweb / Clarivate…），两种都要认。

  otherlisted.txt —— NYSE 大盘股名称经常**不带**后缀，只有 "Visa Inc."
    "Altria Group, Inc." "AT&T Inc."。用白名单会把这些蓝筹全误杀掉
    （实测 586 只 NYSE 股因此丢失）。所以改用黑名单 + 代码形态判断：
      代码含 $ . _ → 优先股系列（T$C）/ 权证（NE.W）/ rights，直接丢
      名称含非普通股特征词 → 丢

  两个文件都先过 Test Issue=N、ETF=N。名称里的排除词覆盖
  权证 / rights / 票据 / 优先股 / 存托凭证 / 次级债 / 公司债 / ETN /
  封闭式基金 / 收益型信托 / 有限合伙（MLP）/ REIT 单位。

已知缺口：SymDir 本身不全，CTRA / AVB / EQR / WBD / HOLX 这类 NYSE
  普通股查不到。所以调用方（main.py）会把项目股票池并进 RS 分母，
  保证每只要出报告的股票都有 RS。

ETF 名单：同一个 SymDir 文件里有 ETF=Y 列，筛出约 5800 只 ETF，
  和股票名单**一次下载、一份缓存**（cache 的 "etfs" 键）。用途是
  在报告里把 ETF 单独标出来（display_name()）——ETF 是一篮子资产的
  份额，不能像个股那样建仓，混在一起容易误操作。

下载可靠性（2026-10-26 加固）：Nasdaq Trader 会被 Incapsula 拦截，
  而且拦截时返回 **HTTP 200 + HTML**（不是 4xx），raise_for_status()
  查不出来。所以这里同时校验「内容确实是 SymDir 文本」和「行数够多」，
  并且**两个文件都拿到才返回结果**——只拿到一半会把 5144 只的股票池
  写成 1957 只。任一文件失败就返回 None，让调用方回退旧缓存。

缓存策略：本地 JSON，7 天过期；网络失败回退到旧缓存。
缓存文件：data/us_market_cache.json
"""

import json
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import requests

CACHE_FILE = Path(__file__).parent.parent / "data" / "us_market_cache.json"
CACHE_MAX_AGE_DAYS = 7

# ETF 名单的进程内缓存，避免报告逐行调 is_etf() 时反复读文件/联网
_ETF_MEMO: set[str] | None = None

_URLS = {
    # nasdaq 上市的名称带类型后缀 → 白名单
    "nasdaqlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    # 其他交易所的名称常常只有公司名 → 黑名单
    "otherlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# 名称里出现就判定为「非普通股」，直接排除（两个文件共用）
_EXCLUDE = (
    "warrant", "right", "debenture", "preferred", "depositary",
    "notes due", "note due", "senior note", "subordinated",
    "corporate units", "etn due", " etn ",
    "closed end", "index fund", "fund of",
    # 封闭式基金 / 收益型信托 / REIT 单位 / MLP 的固定写法
    "beneficial interest", " income fund", " income trust", " trust",
    "limited partnership", "limited partner interests",
)

# 只给 otherlisted 用的额外排除：名称里的基金字样要连词匹配，
# 否则 Fundamental / Founder 之类会被误杀
_EXCLUDE_OTHER = (" fund", " funds")

# nasdaqlisted 专用白名单：名称里出现才算普通股
_EQUITY = (
    "common stock", "common shares", "common unit",
    "ordinary share", "shares of", "class a", "class b", "class c",
    # 外国公司在纽交所的登记股（ASML Holding N.V. - New York Registry Shares）
    "registry shares",
)


def get_us_common_stocks() -> list[str]:
    """
    获取美股全市场普通股代码列表，自动管理本地缓存。

    返回：
        排序去重后的 ticker 列表（约 5400 只）
    """
    cache = _load_cache()

    if _cache_fresh(cache):
        symbols = cache["symbols"]
        print(f"[股票池] 美股全市场：{len(symbols)} 只（本地缓存，{cache['updated_at']}）")
        return symbols

    result = _fetch_symdir()
    if result:
        symbols, etfs = result
        # 股票名单和 ETF 名单来自同一次下载，写进同一份缓存，
        # 免得 get_us_etfs() 之后又去下载一遍 SymDir
        _save_cache(symbols, etfs=sorted(etfs))
        print(f"[股票池] 美股全市场：{len(symbols)} 只（已更新缓存）")
        return symbols

    if "symbols" in cache:
        symbols = cache["symbols"]
        print(f"[股票池] 美股全市场：获取失败，使用旧缓存（{cache['updated_at']}），{len(symbols)} 只")
        return symbols

    print("[股票池] 美股全市场：获取失败且无本地缓存，RS 将退回项目股票池口径")
    return []


def get_us_etfs() -> set[str]:
    """
    获取美股 ETF 代码集合（用于在报告里把 ETF 与个股区分开）。

    ETF 和封闭式基金、ETN、SPAC 单位不同——不能当个股买卖。
    数据同样来自 SymDir 的 ETF=Y 标记，和股票名单共用一次下载、一份缓存。

    进程内做一次 memo：报告渲染会逐行调 is_etf()，
    没有 memo 的话每一行都会去问一次网络。
    """
    global _ETF_MEMO
    if _ETF_MEMO is not None:
        return _ETF_MEMO

    cache = _load_cache()
    if "etfs" in cache:
        _ETF_MEMO = set(cache["etfs"])
        return _ETF_MEMO

    result = _fetch_symdir()
    if result:
        symbols, etfs = result
        _save_cache(symbols, etfs=sorted(etfs))
        _ETF_MEMO = set(etfs)
        return _ETF_MEMO

    # 拿不到就返回空名单。**不写进缓存**——写了会让 ETF 标记整整 7 天失效
    # （下次跑还会当成"已知为空"直接跳过下载），下次运行自然重试。
    # 进程内的 memo 已经保证不会每一行都去撞一次被封的接口。
    _ETF_MEMO = set()
    return _ETF_MEMO


def is_etf(symbol: str) -> bool:
    """判断一个代码是否为 ETF（用于报告标记）。"""
    if not symbol:
        return False
    return symbol.upper() in get_us_etfs()


def display_name(symbol: str) -> str:
    """
    报告里显示的代码名：ETF 后面加 [ETF] 标记。

    ETF 和个股不是一回事——ETF 不能像个股那样按「买一只股票」的方式
    建仓（它是一篮子资产的份额，还会有溢价折价和分红除权）。
    混在一起看容易误操作，所以单独标出来。
    """
    if not symbol:
        return symbol
    return f"{symbol} [ETF]" if is_etf(symbol) else symbol


def _fetch_symdir() -> tuple[list[str], list[str]] | None:
    """
    一次下载 SymDir，同时得到普通股名单和 ETF 名单。

    两个文件**必须都拿到**才返回结果：只拿到一半会写坏缓存
    （实测 otherlisted 一次超时就把股票池从 5144 只缩成 1957 只）。
    任何一个文件失败就返回 None，让调用方回退到旧缓存。

    坑：被 WAF（Incapsula）拦截时返回的是 **HTTP 200 + 一段 HTML**，
    raise_for_status() 照样通过，但解析出来是空表——不校验内容就会把
    缓存清空。所以这里同时校验「确实是 SymDir 文本」和「行数够多」。
    """
    import csv

    symbols: set[str] = set()
    etfs: set[str] = set()

    for src, url in _URLS.items():
        rows = None
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=_HEADERS, timeout=30)
                resp.raise_for_status()
                if not resp.text.startswith("Symbol|"):
                    raise ValueError("返回内容不是 SymDir 文本（可能被 WAF 拦截）")
                # SymDir 是 | 分隔的，且第一行是文件头，需要跳过
                rows = list(csv.DictReader(StringIO(resp.text), delimiter="|"))[1:]
                if len(rows) < 1000:
                    raise ValueError(f"只解析到 {len(rows)} 行，明显不完整")
                break
            except Exception as e:
                rows = None
                print(
                    f"[股票池] Nasdaq Trader 请求失败（{url.rsplit('/', 1)[-1]}，"
                    f"第 {attempt + 1} 次）：{e}"
                )
                time.sleep(3)
        if rows is None:
            return None

        for r in rows:
            sym = _symbol_of(r)
            if not sym:
                continue
            if r.get("ETF") == "Y":
                etfs.add(sym.replace(".", "-"))
            elif _is_common_equity(sym, r, whitelist=src == "nasdaqlisted"):
                # BRK.B → BRK-B（Alpaca/Yahoo 用连字符）
                symbols.add(sym.replace(".", "-"))

    if not symbols:
        return None
    return sorted(symbols), sorted(etfs)


def _symbol_of(row: dict) -> str:
    """nasdaqlisted 用 Symbol，otherlisted 用 ACT Symbol。"""
    return (row.get("Symbol") or row.get("ACT Symbol") or "").strip()


def _is_common_equity(sym: str, row: dict, *, whitelist: bool) -> bool:
    """
    判断一条挂牌记录是否是普通股。

    whitelist=True  用于 nasdaqlisted.txt——名称带类型后缀，必须命中特征词。
    whitelist=False 用于 otherlisted.txt——NYSE 蓝筹名称只有公司名，
                    只能靠排除词 + 代码形态判断（详见模块 docstring）。
    """
    if not sym or len(sym) > 6 or sym[0] in "$._":
        return False
    if row.get("Test Issue") == "Y" or row.get("ETF") == "Y":
        return False

    name = (row.get("Security Name") or "").lower()
    if any(bad in name for bad in _EXCLUDE):
        return False

    if not whitelist:
        # T$C（优先股系列）、NE.W（权证）——these are never common shares
        if any(c in sym for c in "$._"):
            return False
        if any(bad in name for bad in _EXCLUDE_OTHER):
            return False
        return True

    return any(k in name for k in _EQUITY) or name.endswith(" stock")


def _cache_fresh(cache: dict) -> bool:
    """判断缓存是否存在且未过期。"""
    if "symbols" not in cache:
        return False
    try:
        updated = datetime.strptime(cache.get("updated_at", ""), "%Y-%m-%d")
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


def _save_cache(symbols: list[str], etfs: list[str] | None = None) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbols": symbols,
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
    }
    if etfs is not None:
        payload["etfs"] = etfs
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)