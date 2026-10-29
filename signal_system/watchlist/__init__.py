"""
watchlist — 高量股票观察清单

每天跑完 live test 后，自动把量比 > 3x 的买入信号加入 watchlist。
每次跑 live test 时，同时分析 watchlist 里的股票：
- EMA10 crossback（跌破10日指数均线，动量减弱）
- Reversal extension（收盘价偏离MA20超过5%，超买预警）

数据落盘：output/shared/watchlist.json（所有策略共享）
"""

from watchlist.manager import (
    add_stocks_from_records,
    load_watchlist,
    save_watchlist,
    get_watchlist_symbols,
    WATCHLIST_FILE,
)
from watchlist.analyzer import (
    analyze_watchlist,
    print_watchlist_report,
)
from watchlist.report import (
    generate_watchlist_daily_report,
)

__all__ = [
    "add_stocks_from_records",
    "load_watchlist",
    "save_watchlist",
    "get_watchlist_symbols",
    "analyze_watchlist",
    "print_watchlist_report",
    "generate_watchlist_daily_report",
    "WATCHLIST_FILE",
]