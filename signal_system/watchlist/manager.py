"""
watchlist/manager.py — 观察清单的增删改查

数据格式（output/shared/watchlist.json）— schema v2：
{
  "stocks": {
    "OABI": {
      "added_date": "2026-08-20",
      "first_seen_price": 3.54,
      "first_seen_volume_ratio": 14.1,
      "first_seen_strength": 5,            # ← v2 新增：首次被发现时的信号强度（1-5）
      "max_strength_seen": 5,              # ← v2 新增：历史最高信号强度
      "trigger_strategy": "v_zanger",      # 首次触发它的策略
      "trigger_reason": "突破30日高点...",
      "strategies_covered": ["v_zanger", "v1_plus"],  # ← v2 新增：覆盖过的策略列表
      "consensus_count": 2,                # ← v2 新增：覆盖过的策略数（多策略共识强度）
      "appearances": 2,
      "history": [
        {"date": "2026-08-20", "price": 3.54, "volume_ratio": 14.1, "strategy": "v_zanger", "strength": 5},
        {"date": "2026-08-25", "price": 4.10, "volume_ratio": 8.2, "strategy": "v1_plus", "strength": 4}
      ]
    }
  },
  "last_updated": "2026-08-20T09:42:00",
  "schema_version": 2
}
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"
WATCHLIST_FILE = OUTPUT_DIR / "shared" / "watchlist.json"

# 默认加入门槛（可被 add_stocks_from_records 参数覆盖）
DEFAULT_MIN_VOLUME_RATIO = 2.0

# 提取触发原因里的量比数值
# 例子: "[量比] 14.1倍均量" -> 14.1
#      "量比3.2倍均量"        -> 3.2
#      "[量比] 3.0倍均量（严格3x）" -> 3.0
_VOLUME_RATIO_RE = re.compile(r"量比[^\d]*?(\d+\.?\d*)倍")


def _ensure_file() -> None:
    """确保 watchlist.json 存在；不存在则初始化为空清单。"""
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not WATCHLIST_FILE.exists():
        _write_empty()


def _write_empty() -> None:
    """写入空的初始 watchlist 结构。"""
    initial = {
        "stocks": {},
        "last_updated": None,
        "schema_version": 2,
    }
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(initial, f, ensure_ascii=False, indent=2)


def load_watchlist() -> dict:
    """
    加载 watchlist。

    返回：
        dict，结构如模块顶部注释所示。
        如果文件不存在或损坏，返回空结构（不抛异常）。
    """
    _ensure_file()
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"stocks": {}, "last_updated": None, "schema_version": 2}

    # 兼容旧/损坏的结构
    if "stocks" not in data or not isinstance(data["stocks"], dict):
        data["stocks"] = {}
    return data


def save_watchlist(watchlist: dict) -> None:
    """保存 watchlist 到 JSON。"""
    _ensure_file()
    watchlist["last_updated"] = datetime.now(tz=timezone.utc).isoformat()
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def get_watchlist_symbols() -> list[str]:
    """返回 watchlist 中所有股票代码（按加入时间排序）。"""
    watchlist = load_watchlist()
    return list(watchlist["stocks"].keys())


def _extract_volume_ratio(reason: str) -> float | None:
    """
    从信号触发的中文文本里提取量比数值。
    解析失败返回 None（视为不符合门槛）。
    """
    if not reason:
        return None
    m = _VOLUME_RATIO_RE.search(reason)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def add_stocks_from_records(
    records: list[dict],
    strategy_id: str = "",
    min_volume_ratio: float = DEFAULT_MIN_VOLUME_RATIO,
) -> list[str]:
    """
    从单次策略运行的信号记录中，提取量比 ≥ 阈值的"买入"信号，加入 watchlist。

    参数：
        records:          signals/generator.process_signals 返回的记录列表
        strategy_id:      触发该信号的策略 ID（用于追踪来源）
        min_volume_ratio: 最低量比（默认 3.0x）

    返回：
        本次新增（或重新出现）的股票代码列表（去重）。

    副作用（schema v2 增强）：
        - 记录每只股票的首次信号强度（first_seen_strength）
        - 持续累加历史最高信号强度（max_strength_seen）
        - 记录覆盖过的策略列表（strategies_covered）—— 多策略同时看上是强信号
        - 维护 consensus_count（去重后的策略数）
        - history 每条记录额外保存 strength 字段
    """
    if not records:
        return []

    watchlist = load_watchlist()
    stocks = watchlist["stocks"]
    today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    newly_added: list[str] = []

    for rec in records:
        # 只关心"买入"信号
        if rec.get("信号") != "买入":
            continue

        symbol = rec.get("股票")
        if not symbol:
            continue

        reason = rec.get("触发原因", "")
        vol_ratio = _extract_volume_ratio(reason)
        if vol_ratio is None or vol_ratio < min_volume_ratio:
            continue

        # 解析信号强度（1-5 星）
        try:
            strength = int(rec.get("强度(1-5)", 0) or 0)
        except (ValueError, TypeError):
            strength = 0

        # 解析入场价（从止损字段反推不靠谱，直接从触发文本拿"突破$xx"等可能也错）
        # 退而求其次：暂存"首次价"，后续每次分析时再覆盖
        price = None
        # 尝试从 reason 文本里提取 "$123.45" 价格
        price_match = re.search(r"\$([0-9]+\.[0-9]+)", reason)
        if price_match:
            try:
                price = float(price_match.group(1))
            except ValueError:
                pass

        # 加入或更新
        if symbol not in stocks:
            covered = [strategy_id] if strategy_id else []
            stocks[symbol] = {
                "added_date": today_str,
                "first_seen_price": price,
                "first_seen_volume_ratio": vol_ratio,
                "first_seen_strength": strength,
                "max_strength_seen": strength,
                "trigger_strategy": strategy_id,
                "trigger_reason": reason,
                "strategies_covered": covered,
                "consensus_count": len(covered),
                "appearances": 1,
                "history": [
                    {
                        "date": today_str,
                        "price": price,
                        "volume_ratio": vol_ratio,
                        "strength": strength,
                        "strategy": strategy_id,
                    }
                ],
            }
            newly_added.append(symbol)
        else:
            # 已存在 → 增加出现次数 + 追加历史 + 更新强度/策略覆盖
            entry = stocks[symbol]
            entry["appearances"] = entry.get("appearances", 1) + 1
            entry.setdefault("history", []).append(
                {
                    "date": today_str,
                    "price": price,
                    "volume_ratio": vol_ratio,
                    "strength": strength,
                    "strategy": strategy_id,
                }
            )
            # 更新历史最高强度
            cur_max = entry.get("max_strength_seen", 0)
            if strength > cur_max:
                entry["max_strength_seen"] = strength
            # 更新策略覆盖（多策略共识）
            if strategy_id:
                covered = entry.setdefault("strategies_covered", [])
                if strategy_id not in covered:
                    covered.append(strategy_id)
                    entry["consensus_count"] = len(covered)

    save_watchlist(watchlist)
    return newly_added


def remove_stock(symbol: str) -> bool:
    """手动从 watchlist 中移除一只股票。返回是否真的移除了。"""
    watchlist = load_watchlist()
    if symbol in watchlist["stocks"]:
        del watchlist["stocks"][symbol]
        save_watchlist(watchlist)
        return True
    return False