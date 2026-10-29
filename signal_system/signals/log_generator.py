"""
signals/log_generator.py — 全策略信号汇总日志生成器

每次 live test 后自动生成/更新 SIGNALS_LOG.md，
按日期记录所有策略的买入和卖出信号，方便复盘和业绩复核。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from data.rs_parse import resolve_rs_percentile
from data.rs_rating import RS_RATING_LABEL
from data.rs_relative import RS_RELATIVE_LABEL
from universe.us_market import display_name
from data.sector_cache import get_sector
from strategies.registry import list_strategies


OUTPUT_DIR = Path(__file__).parent.parent / "output"
SIGNALS_LOG_FILE = OUTPUT_DIR / "SIGNALS_LOG.md"

# 不进跨策略汇总表的策略。
# ADX50 单日常触发 50+ 条且几乎全是 3★，会把汇总表刷成噪音墙，
# 用户明确表示不关心它。策略自己的日报仍然正常生成。
EXCLUDED_STRATEGIES = {"v_adx50"}

# 汇总表列 = 注册表里的 strategy_id（即 output/ 下的目录名）。
# 从 registry 动态推导，日后新增策略无需改这里。
ALL_STRATEGIES = [
    info["strategy_id"]
    for info in list_strategies()
    if info["id"] not in EXCLUDED_STRATEGIES
]


def load_signals_from_csv(strategy_id: str, date_str: str) -> tuple[list[dict], list[dict]]:
    """
    从策略的 signals.csv 加载指定日期的买入和卖出信号。

    返回: (buy_signals, sell_signals)
    """
    csv_path = OUTPUT_DIR / strategy_id / "signals.csv"
    if not csv_path.exists():
        return [], []

    buy_signals = []
    sell_signals = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 解析表头
        header = lines[0].strip().split(",") if lines else []

        for line in lines[1:]:
            parts = line.strip().split(",")
            if len(parts) < 4:
                continue

            signal_date = parts[0]
            if signal_date != date_str:
                continue

            symbol = parts[1]
            direction = parts[2]
            strength = parts[3] if len(parts) > 3 else "3"
            reason = parts[4] if len(parts) > 4 else ""
            stop_loss = parts[5] if len(parts) > 5 else ""

            signal = {
                "symbol": symbol,
                "strength": strength,
                "reason": reason,
                "stop_loss": stop_loss,
            }

            if direction == "买入":
                buy_signals.append(signal)
            elif direction == "卖出":
                sell_signals.append(signal)

    except Exception as e:
        print(f"[信号日志] 读取 {strategy_id} 信号失败: {e}")

    return buy_signals, sell_signals


def extract_breakout_info(reason: str) -> tuple[str, str]:
    """从信号原因中提取突破幅度和放量倍数"""
    breakout_pct = "-"
    volume_ratio = "-"

    if "+" in reason and "%" in reason:
        # 提取突破幅度
        import re
        match = re.search(r"\+(\d+\.?\d*)%", reason)
        if match:
            breakout_pct = f"+{match.group(1)}%"

    if "倍" in reason or "x" in reason.lower():
        # 提取放量倍数
        import re
        match = re.search(r"(\d+\.?\d*)\s*[倍xX]", reason)
        if match:
            volume_ratio = f"{match.group(1)}x"

    return breakout_pct, volume_ratio


def _rs_str(symbol: str, rs_ratings: dict[str, int] | None) -> str:
    """O'Neil RS Rating（1-99），无数据时显示 '—'。"""
    if not rs_ratings:
        return "—"
    val = rs_ratings.get(symbol)
    return str(val) if val is not None else "—"


def generate_daily_section(
    date_str: str,
    all_buy_signals: dict[str, list],
    all_sell_signals: dict[str, list],
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """生成某一天的信号汇总部分"""

    lines = []
    lines.append(f"## {date_str}")
    lines.append("")

    # 收集所有买入信号的股票
    buy_symbols = set()
    for signals in all_buy_signals.values():
        for sig in signals:
            buy_symbols.add(sig["symbol"])

    # 收集所有卖出信号的股票
    sell_symbols = set()
    for signals in all_sell_signals.values():
        for sig in signals:
            sell_symbols.add(sig["symbol"])

    # ========== 买入信号汇总表 ==========
    if buy_symbols:
        lines.append("### 买入信号汇总")
        lines.append("")
        header = (
            f"| 股票 | 行业 | {RS_RATING_LABEL} | {RS_RELATIVE_LABEL} | "
            + " | ".join(ALL_STRATEGIES)
            + " | 综合评分 |"
        )
        lines.append(header)
        separator = "|------|------|-----|--------|" + "|".join(["----"] * len(ALL_STRATEGIES)) + "|----|"
        lines.append(separator)

        for symbol in sorted(buy_symbols):
            count = 0
            max_stars = 0
            best_rs = None
            cells = []
            for strategy in ALL_STRATEGIES:
                signals = all_buy_signals.get(strategy, [])
                matched = [s for s in signals if s["symbol"] == symbol]
                if matched:
                    stars = matched[0]["strength"]
                    cells.append(stars)
                    count += 1
                    # 计算星星数
                    star_count = stars.count("★")
                    if star_count > max_stars:
                        max_stars = star_count
                    # 跨策略取最高 RS%
                    rs = resolve_rs_percentile(matched[0].get("reason", ""), symbol, rs_relative)
                    if rs is not None and (best_rs is None or rs > best_rs):
                        best_rs = rs
                else:
                    cells.append("-")
            rs_str = str(best_rs) if best_rs is not None else "—"
            rs_rating = (rs_ratings or {}).get(symbol)
            rs_rating_str = str(rs_rating) if rs_rating is not None else "—"
            lines.append(
                f"| **{display_name(symbol)}** | {get_sector(symbol)} | {rs_rating_str} | {rs_str} | "
                + " | ".join(cells)
                + f" | {count}策略 |"
            )

        lines.append("")

    # ========== 买入信号详情 ==========
    if buy_symbols:
        lines.append("### 买入信号详情")
        lines.append("")

        for symbol in sorted(buy_symbols):
            # 收集该股票在各策略的信号
            strategies_with_signal = []
            for strategy in ALL_STRATEGIES:
                signals = all_buy_signals.get(strategy, [])
                matched = [s for s in signals if s["symbol"] == symbol]
                if matched:
                    sig = matched[0]
                    breakout, vol = extract_breakout_info(sig["reason"])
                    rs = resolve_rs_percentile(sig.get("reason", ""), symbol, rs_relative)
                    strategies_with_signal.append({
                        "strategy": strategy,
                        "rs": rs if rs is not None else "—",
                        "strength": sig["strength"],
                        "breakout": breakout,
                        "volume": vol,
                        "stop_loss": sig["stop_loss"],
                    })

            if strategies_with_signal:
                lines.append(f"#### {display_name(symbol)} ({get_sector(symbol)})")
                lines.append("")
                lines.append(
                    f"| 策略 | {RS_RATING_LABEL} | {RS_RELATIVE_LABEL} | 强度 | 突破幅度 | 放量倍数 | 参考止损 |"
                )
                lines.append("|------|-----|--------|------|---------|---------|---------|")
                for s in strategies_with_signal:
                    lines.append(f"| {s['strategy']} | {_rs_str(symbol, rs_ratings)} | {s['rs']} | {s['strength']} | {s['breakout']} | {s['volume']} | {s['stop_loss']} |")
                lines.append("")

    # ========== 卖出信号汇总表 ==========
    if sell_symbols:
        lines.append("### 卖出信号汇总")
        lines.append("")

        header = "| 股票 | " + " | ".join(ALL_STRATEGIES) + " | 原因 |"
        lines.append(header)
        separator = "|------|" + "|".join(["----"] * len(ALL_STRATEGIES)) + "|----|"
        lines.append(separator)

        for symbol in sorted(sell_symbols):
            row = f"| **{display_name(symbol)}** |"
            reasons = []
            for strategy in ALL_STRATEGIES:
                signals = all_sell_signals.get(strategy, [])
                matched = [s for s in signals if s["symbol"] == symbol]
                if matched:
                    row += " 卖 |"
                    if matched[0]["reason"] not in reasons:
                        reasons.append(matched[0]["reason"])
                else:
                    row += " - |"
            # 简化原因
            reason_short = reasons[0] if reasons else ""
            if "止损" in reason_short and "跌幅" in reason_short:
                import re
                match = re.search(r"跌幅([-\d.]+%)", reason_short)
                if match:
                    reason_short = f"止损({match.group(1)})"
                else:
                    reason_short = "止损"
            elif "追踪止盈" in reason_short:
                reason_short = "追踪止盈"
            elif "时间止损" in reason_short:
                reason_short = "时间止损"
            # 触发原因里的分段符是「|」，直接放进 Markdown 表格会多出一列
            row += f" {reason_short.replace('|', '·')} |"
            lines.append(row)

        lines.append("")

    # ========== 卖出信号详情 ==========
    if sell_symbols:
        lines.append("### 卖出信号详情")
        lines.append("")
        lines.append("| 股票 | 策略 | 出场原因 | 入场价 | 当前价 |")
        lines.append("|------|------|---------|-------|-------|")

        for symbol in sorted(sell_symbols):
            for strategy in ALL_STRATEGIES:
                signals = all_sell_signals.get(strategy, [])
                matched = [s for s in signals if s["symbol"] == symbol]
                if matched:
                    sig = matched[0]
                    # 简化原因显示
                    reason = sig["reason"][:50] + "..." if len(sig["reason"]) > 50 else sig["reason"]
                    lines.append(f"| {display_name(symbol)} | {strategy} | {reason} | - | - |")

        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def update_signals_log(
    date_str: str | None = None,
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> None:
    """
    更新信号汇总日志。

    参数:
        date_str: 日期字符串，默认使用今天
        rs_ratings: {ticker: 1-99} 的 O'Neil RS Rating
        rs_relative: {ticker: 0-100} 的策略内部口径 RS%
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 加载所有策略的信号
    all_buy_signals: dict[str, list] = {}
    all_sell_signals: dict[str, list] = {}

    for strategy in ALL_STRATEGIES:
        buy, sell = load_signals_from_csv(strategy, date_str)
        if buy:
            all_buy_signals[strategy] = buy
        if sell:
            all_sell_signals[strategy] = sell

    # 如果没有任何信号，跳过
    if not all_buy_signals and not all_sell_signals:
        print(f"[信号日志] {date_str} 无信号，跳过更新")
        return

    # 生成新的一天部分
    new_section = generate_daily_section(date_str, all_buy_signals, all_sell_signals, rs_ratings, rs_relative)

    # 读取现有文件
    if SIGNALS_LOG_FILE.exists():
        with open(SIGNALS_LOG_FILE, "r", encoding="utf-8") as f:
            existing_content = f.read()
    else:
        existing_content = ""

    # 检查该日期是否已存在
    if f"## {date_str}" in existing_content:
        # 替换该日期的内容
        import re
        pattern = rf"## {date_str}\n.*?(?=\n## |\n\*文件生成|$)"
        existing_content = re.sub(pattern, new_section.rstrip("\n") + "\n", existing_content, flags=re.DOTALL)
        print(f"[信号日志] 更新 {date_str} 的信号记录")
    else:
        # 在文件头部（第一个 ## 之前）插入新内容
        if "## " in existing_content:
            # 找到第一个 ## 的位置
            first_section_pos = existing_content.find("## ")
            # 在第一个 ## 前插入新内容
            existing_content = (
                existing_content[:first_section_pos] +
                new_section + "\n" +
                existing_content[first_section_pos:]
            )
        else:
            # 文件为空或只有头部，追加新内容
            existing_content = existing_content.rstrip() + "\n\n" + new_section
        print(f"[信号日志] 添加 {date_str} 的信号记录")

    # 更新文件头部的生成时间
    header = f"""# 全策略信号汇总日志

> 自动生成，每次 live test 后更新
> 用于复盘和业绩复核
> 最后更新：{datetime.now().strftime("%Y-%m-%d %H:%M")}
> RS 两列口径（务必分清，两个数不是一回事）：
> 1. **{RS_RATING_LABEL}** —— O'Neil CAN SLIM 口径。12 个月按 63 个交易日切 4 季，近 3 月 ×0.4、4-6 月 ×0.2、7-9 月 ×0.2、10-12 月 ×0.2，在美股全市场（约 6300 只）内排名 1-99。**不参照基准，只看绝对涨幅**。
> 2. **{RS_RELATIVE_LABEL}** —— 策略内部口径。0.4×(个股 252 日涨幅÷基准 252 日涨幅−1) + 0.3×(126 日) + 0.3×(60 日)，在 UNIVERSE.md 固定池内排名 0-100。**回答「比大盘强多少」**。

---

"""
    # 移除旧头部
    if existing_content.startswith("# 全策略信号汇总日志"):
        # 找到第一个 --- 后面的内容
        import re
        match = re.search(r"^---\n+", existing_content, re.MULTILINE)
        if match:
            existing_content = existing_content[match.end():]

    # 写入文件
    with open(SIGNALS_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(header + existing_content)

    print(f"[信号日志] 已保存到 {SIGNALS_LOG_FILE}")


if __name__ == "__main__":
    # 手动测试
    update_signals_log()
