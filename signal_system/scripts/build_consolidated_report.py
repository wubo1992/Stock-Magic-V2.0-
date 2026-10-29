"""
scripts/build_consolidated_report.py — 解析 v6 日志，重建 REPORT.md

新格式：
  - RS10W 显示为比值（X.XXx），不再是百分位（0-100）
  - 比值 = 股票过去 10 周涨幅 / SPY 过去 10 周涨幅
  - 1.0x = 与SPY同步，2.0x = 股票涨幅是SPY的2倍

用法：
    uv run python scripts/build_consolidated_report.py
"""
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"


def _latest_log() -> tuple[Path, Path]:
    """找最新的 live_YYYYMMDD 目录，返回 (log_path, out_path)。"""
    dated = sorted([d for d in LOGS_DIR.iterdir() if d.is_dir() and d.name.startswith("live_")])
    if not dated:
        raise FileNotFoundError(f"在 {LOGS_DIR} 下没找到 live_YYYYMMDD 目录")
    latest = dated[-1]
    # 取目录里第一个 all_strategies*.log
    logs = sorted(latest.glob("all_strategies*.log"))
    if not logs:
        raise FileNotFoundError(f"在 {latest} 下没找到 all_strategies*.log")
    return logs[-1], latest / "REPORT.md"


LOG, OUT = _latest_log()


# ── 策略ID → 显示名映射（与 v6 日志里的 ▶ 策略：xxx 对应）─────────
STRATEGY_NAMES = {
    "v1": "v1",
    "v1_plus": "v1_plus",
    "v_zanger": "v_zanger",
    "v_weinstein": "v_weinstein",
    "v_eps": "v_eps",
    "v_eps_v2": "v_eps_v2",
    "v_eps_v1_plus": "v_eps_v1_plus",
    "v_adx50": "v_adx50",
    "v_weinstein_mf_strict": "v_weinstein_mf_strict",
}


def parse_log() -> tuple[list[dict], list[dict]]:
    """
    解析 v7 日志，返回 (买入信号列表, 出场信号列表)。
    每个信号是个 dict，含 strategy/date/symbol/strength/price/reason。
    """
    text = LOG.read_text(encoding="utf-8")

    # 按策略切片
    blocks = re.split(r"▶ 策略：(\S+)", text)
    # blocks[0] 是开头介绍，之后 [name, body, name, body, ...]
    buys, sells = [], []
    for i in range(1, len(blocks), 2):
        strat = blocks[i]
        body = blocks[i + 1] if i + 1 < len(blocks) else ""

        # 找买入段
        m_buy = re.search(r"【买入信号】共 (\d+) 个\s*\n[^\n]+\n[-]+\n(.+?)(?=\n=|\n【)", body, re.DOTALL)
        if m_buy:
            for line in m_buy.group(2).splitlines():
                parsed = _parse_signal_line(line)
                if parsed:
                    parsed["strategy"] = strat
                    buys.append(parsed)

        # 找出场段
        m_sell = re.search(r"【出场信号】共 (\d+) 个\s*\n[^\n]+\n[-]+\n(.+?)(?=\n=|\n【)", body, re.DOTALL)
        if m_sell:
            for line in m_sell.group(2).splitlines():
                parsed = _parse_sell_line(line)
                if parsed:
                    parsed["strategy"] = strat
                    sells.append(parsed)

    return buys, sells


_SIGNAL_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(\S+)\s+([★☆]+)\s+(\$[\d.]+)\s+(.+)$"
)


def _parse_signal_line(line: str) -> dict | None:
    """'2026-08-06   JAZZ     ★★★★★    $235.28    REASON' → dict"""
    m = _SIGNAL_RE.match(line.strip())
    if not m:
        return None
    return {
        "date": m.group(1),
        "symbol": m.group(2),
        "strength": m.group(3),
        "stop": m.group(4),
        "reason": m.group(5),
    }


_SELL_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(\S+)\s+(\S+)\s+(.+)$"
)


def _parse_sell_line(line: str) -> dict | None:
    """'2026-08-06   AMIX     （请填写持仓数）       [止损] 亏损-82.3%' → dict"""
    m = _SELL_RE.match(line.strip())
    if not m:
        return None
    return {
        "date": m.group(1),
        "symbol": m.group(2),
        "shares": m.group(3),
        "reason": m.group(4),
    }


# ── reason 解析工具 ─────────────────────────────────────────────

def _extract(reason: str, key: str) -> str:
    """从 '[趋势] ... | [RS] ... | [VCP] ...' 取出 [key] 后面的内容"""
    parts = reason.split(" | ")
    for p in parts:
        p = p.strip()
        if p.startswith(key):
            return p[len(key):].strip()
    return ""


def _extract_number(text: str) -> str:
    """提取第一个数字串"""
    m = re.search(r"[\d.]+", text)
    return m.group() if m else ""


def parse_features(buy: dict) -> dict:
    """从 reason 提取特征字段。"""
    reason = buy["reason"]

    # [量比] X.X倍均量
    vol_m = re.search(r"\[量比\]\s*([\d.]+)倍均量", reason)
    vol = f"{vol_m.group(1)}x" if vol_m else "—"

    # [RS] ... 排名X% / RS=X
    rs_m = re.search(r"\[RS\]\s*[^[]*?(\d+)\s*%?", reason)
    # 兼容 "相对强度排名85%" 和 "RS=85"
    rs_m2 = re.search(r"\[RS\]\s*(?:相对强度排名|RS=)\s*(\d+)\s*%?", reason)
    rs = f"RS={rs_m2.group(1)}" if rs_m2 else "—"

    # [RS10D] X.XXx
    rs10d_m = re.search(r"\[RS10D\]\s*([\d.]+x|—)", reason)
    rs10d = rs10d_m.group(1) if rs10d_m else "—"

    # [RS10W] X.XXx
    rs10w_m = re.search(r"\[RS10W\]\s*([\d.]+x|—)", reason)
    rs10w = rs10w_m.group(1) if rs10w_m else "—"

    return {"vol": vol, "rs": rs, "rs10d": rs10d, "rs10w": rs10w, "reason": reason}


# ── 渲染 REPORT.md ─────────────────────────────────────────────

def render_report(buys: list[dict], sells: list[dict]) -> str:
    today = "2026-08-06"

    # ── 1. 各策略统计
    strat_stats = defaultdict(lambda: {"buy": 0, "sell": 0})
    for b in buys:
        strat_stats[b["strategy"]]["buy"] += 1
    for s in sells:
        strat_stats[s["strategy"]]["sell"] += 1

    # ── 2. 共识买入（同 ticker ≥2 策略）
    ticker_to_strats = defaultdict(list)
    ticker_to_buy = {}
    for b in buys:
        ticker_to_strats[b["symbol"]].append(b["strategy"])
        # 一只 ticker 取第一条（最早出现的）
        if b["symbol"] not in ticker_to_buy:
            ticker_to_buy[b["symbol"]] = b

    consensus = sorted(
        [(t, len(ss)) for t, ss in ticker_to_strats.items() if len(ss) >= 2],
        key=lambda x: -x[1],
    )

    # ── 3. 全部买入信号（按策略+出现顺序）
    lines = []
    lines.append(f"# 全策略 Live 信号报告 — {today}（v8 新增 RS10D 短期动量）")
    lines.append("")
    lines.append("> 本次重跑：**新增 RS10D**（10 个交易日 ≈ 2 周相对强度）")
    lines.append("> **RS10D 公式**：R_10D(t) = close(t) / close(t-10) − 1；RS-10D = (1 + R_stock) / (1 + R_SPY)")
    lines.append("> **RS10W 公式**：R_10W(t) = close(t) / close(t-50) − 1；RS-10W = (1 + R_stock) / (1 + R_SPY)")
    lines.append("> - `1.00x` = 股票与 SPY 完全同步")
    lines.append("> - `1.50x` = 股票涨幅是 SPY 的 1.5 倍")
    lines.append("> - `2.00x` = 股票价格涨幅是 SPY 的 2 倍（罕见，需要极强动量）")
    lines.append("> - `0.50x` = 股票价格涨幅只有 SPY 的一半（弱势）")
    lines.append("")
    lines.append("**RS10D vs RS10W 配合使用：**")
    lines.append("- RS10D（10 日/2 周）：看**近期动量**，捕捉刚启动的爆发股")
    lines.append("- RS10W（50 日/10 周）：看**中期趋势**，过滤偶发突破")
    lines.append("- 两者都 > 1.00x → 中期+短期都在跑赢 SPY（强势股）")
    lines.append("- RS10D 远 > RS10W → 刚启动的爆发股（突破候选）")
    lines.append("- RS10W 远 > RS10D → 已强势运行，势头放缓（谨慎追高）")
    lines.append("")

    # 1. 统计
    lines.append("## 1. 各策略信号统计")
    lines.append("")
    lines.append("| 策略 | 买入 | 卖出 |")
    lines.append("|------|------|------|")
    total_buy, total_sell = 0, 0
    for strat in STRATEGY_NAMES:
        st = strat_stats.get(strat, {"buy": 0, "sell": 0})
        lines.append(f"| {strat} | {st['buy']} | {st['sell']} |")
        total_buy += st["buy"]
        total_sell += st["sell"]
    lines.append(f"| **合计** | **{total_buy}** | **{total_sell}** |")
    lines.append("")

    # 2. 共识
    lines.append("## 2. 共识买入（≥2 策略同时推荐）")
    lines.append("")
    if not consensus:
        lines.append("> 今日无共识买入。")
    else:
        lines.append("| 股票 | 共识 | 价格 | 量比 | RS | **RS10D** | **RS10W** | 涉及策略 |")
        lines.append("|------|------|------|------|-----|---------|---------|---------|")
        for t, n in consensus:
            b = ticker_to_buy[t]
            feat = parse_features(b)
            strats = ", ".join(ticker_to_strats[t])
            lines.append(
                f"| **{t}** | {n}/9 | {b['stop']} | {feat['vol']} | "
                f"**{feat['rs']}** | **{feat['rs10d']}** | **{feat['rs10w']}** | {strats} |"
            )
    lines.append("")

    # 3. 全部买入信号
    unique_tickers = sorted({b["symbol"] for b in buys})
    lines.append(f"## 3. 全部买入信号（{len(buys)} 条，去重 {len(unique_tickers)} 只）")
    lines.append("")
    lines.append("每条信号列出 **RS**（综合三段加权，0-100）、**RS10D**（10 日比值）、**RS10W**（10 周比值）、量比。")
    lines.append("- **RS 越大越强**：综合 252/126/60 日加权百分位")
    lines.append("- **RS10D 越大越强**：10 日内股票涨幅与 SPY 涨幅的比值（短期动量）")
    lines.append("- **RS10W 越大越强**：10 周内股票涨幅与 SPY 涨幅的比值（中期趋势）")
    lines.append("")
    lines.append("| # | 策略 | 股票 | 价格 | 量比 | **RS** | **RS10D** | **RS10W** | 特征摘要 |")
    lines.append("|---|------|------|------|------|--------|---------|---------|---------|")
    for i, b in enumerate(buys, 1):
        feat = parse_features(b)
        # 特征摘要：截断 reason 前 100 字符
        summary = feat["reason"][:110]
        if len(feat["reason"]) > 110:
            summary += "..."
        lines.append(
            f"| {i} | {b['strategy']} | **{b['symbol']}** | {b['stop']} | {feat['vol']} | "
            f"**{feat['rs']}** | **{feat['rs10d']}** | **{feat['rs10w']}** | {summary} |"
        )
    lines.append("")

    # 4. RS vs RS10D vs RS10W 说明
    lines.append("## 4. RS / RS10D / RS10W 对比")
    lines.append("")
    lines.append("| 指标 | 周期 | 公式 | 含义 |")
    lines.append("|------|------|------|------|")
    lines.append("| **RS** | 0.4×252日 + 0.3×126日 + 0.3×60日（加权）| 综合三段收益百分位（0-100）| 中长期相对强度**排名** |")
    lines.append("| **RS10D** | 10 个交易日（2 周）| **(1+R_stock) / (1+R_SPY)** | 近期**短期动量**比值（X.XXx）|")
    lines.append("| **RS10W** | 50 个交易日（10 周）| **(1+R_stock) / (1+R_SPY)** | 中期**趋势强度**比值（X.XXx）|")
    lines.append("")
    lines.append("**三者的核心区别：**")
    lines.append("- **RS（百分位 0-100）**：在 UNIVERSE 池内排第几，关注**相对排名**")
    lines.append("- **RS10D（比值 X.XXx，10 日）**：和标普 500 直接对比，捕捉**刚启动的爆发**")
    lines.append("- **RS10W（比值 X.XXx，10 周）**：和标普 500 直接对比，看**中期趋势强度**")
    lines.append("")
    lines.append("**RS10D / RS10W 数值示例（同步 = 1.00x，SPY 10 周涨 5% 时）：**")
    lines.append("| 股票涨幅 | SPY 涨幅 | RS | 解读 |")
    lines.append("|----------|----------|-----|------|")
    lines.append("| +10% | +10% | **1.00x** | 同步 |")
    lines.append("| +20% | +10% | **1.09x** | 跑赢一些 |")
    lines.append("| +50% | +10% | **1.36x** | 强 |")
    lines.append("| +100% | +10% | **1.82x** | 极强 |")
    lines.append("| +5% | +10% | **0.95x** | 跑输一些 |")
    lines.append("| 0% | +10% | **0.91x** | 弱势 |")
    lines.append("-10% | +10% | **0.82x** | 反向 |")
    lines.append("")
    lines.append("**为什么用价格乘数比而不是收益比（stock_gain / spy_gain）？**")
    lines.append("- 收益比在 SPY 接近 0 涨幅时会爆炸（例：SPY +0.1% / 股票 +10% → 100x，无意义）")
    lines.append("- 价格乘数比数值稳定，永远围绕 1.00x 波动（同步=1.00x），更直观")
    lines.append("- IBD RS Rating（1-99）用的就是这种乘数比思路")
    lines.append("")
    lines.append("**RS10D 与 RS10W 配合使用场景：**")
    lines.append("- 找**刚启动**爆发股：RS10D 高（如 >1.20x）+ RS10W 中等（如 1.05x）→ 突破候选")
    lines.append("- 找**已强势**主升股：RS10D 高 + RS10W 也高（>1.20x）→ 主升浪中（追高要慎）")
    lines.append("- 找**走弱**股票：RS10D < 1.00x 但 RS10W > 1.00x → 势头已失，避免")
    lines.append("- 找**反弹**股票：RS10D > 1.00x 但 RS10W < 1.00x → 弱势反弹，快进快出")
    lines.append("")
    lines.append("**统一基准**：")
    lines.append("- 美股：SPY")
    lines.append("- 港股：ASHR（暂未用）")
    lines.append("- 台股：EWT（暂未用）")
    lines.append("")
    lines.append("> v_zanger / v_eps_v2 原本不查综合 RS，现在**查 RS10D + RS10W**。")
    lines.append("> 其他 7 个策略 RS + RS10D + RS10W 都查。")
    lines.append("")

    # 5. 总览
    lines.append("## 5. 总览")
    lines.append("")
    lines.append(f"- 共识买入股票数: **{len(consensus)}**")
    lines.append(f"- 单策略买入股票数: {len([t for t in unique_tickers if len(ticker_to_strats[t]) == 1])}")
    lines.append(f"- 全部买入股票（去重）: **{len(unique_tickers)}**")
    lines.append(f"- 买入信号总数: **{len(buys)}**")
    lines.append(f"- 卖出信号总数: {len(sells)}")
    lines.append("")
    lines.append("*报告时间: 2026-08-06 16:25*")
    lines.append("*运行耗时: ~3 分钟（含数据下载）*")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    buys, sells = parse_log()
    print(f"解析到 {len(buys)} 个买入信号，{len(sells)} 个出场信号")

    content = render_report(buys, sells)
    OUT.write_text(content, encoding="utf-8")
    print(f"已生成：{OUT}")
    print(f"大小：{len(content)} 字符")
