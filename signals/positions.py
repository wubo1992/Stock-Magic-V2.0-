"""
signals/positions.py — 持仓状态持久化

在两次 live 运行之间，将策略的持仓状态保存到 JSON 文件。
这样策略在下次运行时能继续追踪已持有仓位的出场条件
（固定止损 / 追踪止盈 / 时间止损）。

文件位置：output/{strategy_id}/positions.json

用户可以直接编辑此文件：
  - 删除某只股票的行 → 取消对该仓位的跟踪（你已手动平仓）
  - 修改 entry_price   → 调整为实际买入价（如果系统信号价和你的实际价不同）
  - 手动添加一行      → 跟踪你自己加仓或手动买入的股票
"""

import json
from datetime import datetime
from pathlib import Path

from strategies.v1_wizard.sepa_minervini import Position

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def _positions_file(strategy_id: str) -> Path:
    return OUTPUT_DIR / strategy_id / "positions.json"


def load_positions(strategy_id: str) -> dict[str, Position]:
    """
    从 positions.json 加载持仓。
    返回 {symbol: Position} 字典，供策略 _check_exits() 使用。
    """
    path = _positions_file(strategy_id)
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result: dict[str, Position] = {}
    for symbol, d in data.items():
        try:
            entry_date = datetime.fromisoformat(d["entry_date"])
            result[symbol] = Position(
                symbol=symbol,
                entry_price=float(d["entry_price"]),
                entry_date=entry_date,
                highest_price=float(d["highest_price"]),
                stop_loss=float(d["stop_loss"]),
                days_held=int(d.get("days_held", 0)),
            )
        except (KeyError, ValueError, TypeError):
            print(f"[持仓] 警告：{symbol} 数据格式错误，已跳过")

    return result


def save_positions(positions: dict[str, Position], strategy_id: str) -> None:
    """
    将策略当前持仓保存到 positions.json。
    每次 live 运行结束后调用，保存新买入 + 移除已出场仓位。
    """
    path = _positions_file(strategy_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        sym: {
            "symbol": pos.symbol,
            "entry_price": round(pos.entry_price, 4),
            "entry_date": pos.entry_date.isoformat(),
            "highest_price": round(pos.highest_price, 4),
            "stop_loss": round(pos.stop_loss, 4),
            "days_held": pos.days_held,
        }
        for sym, pos in positions.items()
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
