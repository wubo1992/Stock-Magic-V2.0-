"""
watchlist/report.py — 第二层观察清单分析 → 每日 Markdown 报告落盘

为什么独立成文件：
- watchlist 分析是「第二层信号」（用户优先级 ≥ 第一层 9 策略信号）
- 原始 print_watchlist_report 仅打印到控制台，无法历史归档
- 本模块将第二层输出落盘到 Markdown，路径：output/shared/watchlist_daily/{YYYY-MM-DD}/...
- 之后 livetest 每次会调用此模块，文件永久保留
"""

from datetime import date, datetime, timezone
from pathlib import Path

from data.rs_rating import RS_RATING_LABEL
from data.rs_relative import RS_RELATIVE_LABEL
from data.sector_cache import get_sector
from universe.us_market import display_name
from watchlist.analyzer import (
    DEFAULT_CROSSBACK_SIGNAL_VOLUME_THRESHOLD,
    DEFAULT_MAX_DAYS_SINCE_CROSSBACK,
    filter_crossback_signals,
)

# 两套 RS 口径的表头（写全称，避免「RS%」和「RS评级」被当成同一个东西）
RS_HEADER = f"| {RS_RATING_LABEL} | {RS_RELATIVE_LABEL} |"
RS_SEPARATOR = "|------|------|"


def _days_since_crossback(crossback_date_str: str | None) -> str:
    """计算穿回日距今。"""
    if not crossback_date_str:
        return "—"
    try:
        cb_d = datetime.strptime(crossback_date_str, "%Y-%m-%d").date()
        return f"{(date.today() - cb_d).days}天"
    except (ValueError, TypeError):
        return "—"


def _days_in_wl(days: int | None) -> str:
    """在册天数格式化。"""
    if days is None:
        return "—"
    return f"{days}天"


def _days_pair(d1, d2) -> tuple[str, str]:
    """两个天数字段统一格式化。"""
    s1 = f"{d1}天" if d1 is not None else "—"
    s2 = f"{d2}天" if d2 is not None else "—"
    return s1, s2


def _fmt_pct(val, plus_sign: bool = True) -> str:
    """百分号格式化：None/缺失→'—'。"""
    if val is None:
        return "—"
    fmt = f"{val:+.1f}%" if plus_sign else f"{val:.1f}%"
    return fmt


def _fmt_price(val) -> str:
    if val is None:
        return "—"
    return f"${val:.2f}"


def _rs_str(sym: str, rs_ratings: dict[str, int] | None) -> str:
    """O'Neil RS Rating（1-99），无数据时显示 '—'。"""
    if not rs_ratings:
        return "—"
    val = rs_ratings.get(sym)
    return str(val) if val is not None else "—"


def _rs_relative_str(sym: str, rs_relative: dict[str, float] | None) -> str:
    """策略内部 RS%（对标基准 ETF 的超额收益百分位 0-100），无数据时显示 '—'。"""
    if not rs_relative:
        return "—"
    val = rs_relative.get(sym)
    return f"{val:.0f}" if val is not None else "—"


def _status_str(a: dict) -> str:
    """组装状态标签（与 print_watchlist_report 一致）。"""
    tags = []
    if a["ema10_crossback_today"]:
        tags.append("✅今日收EMA10")
    if a["reversal_extension_alert"] == "strong":
        tags.append("🔻Kell强延伸")
    elif a["reversal_extension_alert"] == "warning":
        tags.append("⚡Kell延伸")
    if a.get("recovery_status") == "reversal_extension":
        tags.append("🔻历史EXT")
    elif a.get("recovery_status") == "ema_crossback":
        tags.append("✅历史CB")
    if a.get("pullback_state") == "deep":
        tags.append("🔻深度回踩")
    elif a.get("pullback_state") == "starting":
        tags.append("↘️回踩中")
    if not tags:
        tags.append("✓正常")
    return ",".join(tags)


def _table_crossback_signals(
    analysis: dict[str, dict],
    volume_threshold: float,
    max_days: int,
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """📡 放量穿回 EMA10 信号表（核心输出，放在最前）。"""
    signals = filter_crossback_signals(analysis, volume_threshold, max_days)
    out = []
    out.append("## 📡 放量穿回 EMA10 信号（核心 · 第二层最重要）")
    out.append("")
    out.append(
        f"**口径**：自加入日起曾跌破 EMA10 → 当前已涨回 → 穿回日量比 ≥ "
        f"**{volume_threshold}×** 20日均量 → 穿回日距今 ≤ **{max_days} 天**。"
    )
    out.append("")
    out.append(f"**当前共 {len(signals)} 只**（按穿回日降序，最新穿回的排最前）。")
    out.append("")
    if not signals:
        out.append("> 今日无符合全部 4 条件的信号。")
        return "\n".join(out)

    out.append(
        f"| 股票 | 行业 {RS_HEADER} 现价 | 穿回日 | 距今 | 穿回量比 | 加入日 | 累计% | 首次跌破日 | 最深% |"
    )
    out.append("|------|------|------|------|------|--------|------|----------|------|--------|-------|------------|")
    for sym in signals:
        a = analysis[sym]
        cbr_str = f"{a.get('crossback_volume_ratio'):.1f}x" if a.get('crossback_volume_ratio') is not None else "—"
        out.append(
            f"| {display_name(sym)} | {get_sector(sym)} | {_rs_str(sym, rs_ratings)} | {_rs_relative_str(sym, rs_relative)} | "
            f"{_fmt_price(a['current_price'])} | "
            f"{a.get('crossback_date') or '—'} | "
            f"{_days_since_crossback(a.get('crossback_date'))} | "
            f"{cbr_str} | "
            f"{a.get('added_date') or '—'} | "
            f"{_fmt_pct(a.get('price_change_since_added_pct'))} | "
            f"{a.get('first_dip_date') or '—'} | "
            f"{_fmt_pct(a.get('deepest_dip_pct'))} |"
        )
    return "\n".join(out)


def _table_recovery_crossback(
    analysis: dict[str, dict],
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """✅ EMA Crossback 历史组（跌破后已站回）。"""
    group = [s for s in analysis if analysis[s].get("recovery_status") == "ema_crossback"]
    out = []
    out.append("")
    out.append(f"## ✅ EMA Crossback 历史组（跌破后已站回 EMA10，共 {len(group)} 只）")
    out.append("")
    if not group:
        out.append("> （无）")
        return "\n".join(out)
    out.append(
        f"| 股票 | 行业 {RS_HEADER} 现价 | 加入日收 | 累计% | 加入日 | 首次破 | 最深日 | 最深% | 穿回日 | 穿回量比 | 在册 | 入→底 | 底→今 |"
    )
    out.append("|------|------|------|------|------|---------|-------|--------|--------|--------|-------|--------|----------|------|-------|-------|")
    sorted_cb = sorted(
        group,
        key=lambda s: (
            analysis[s].get("days_deepest_dip_to_now") is None,
            analysis[s].get("days_deepest_dip_to_now", 999),
        ),
    )
    for sym in sorted_cb:
        a = analysis[sym]
        added_close = a.get("close_on_added_date")
        ac_str = _fmt_price(added_close)
        cbr_str = f"{a.get('crossback_volume_ratio'):.1f}x" if a.get('crossback_volume_ratio') is not None else "—"
        dipw = a.get("days_in_watchlist")
        d1 = a.get("days_added_to_deepest_dip")
        d2 = a.get("days_deepest_dip_to_now")
        dipw_str, d1_str = _days_pair(dipw, d1)
        _, d2_str = _days_pair(d2, d2)
        out.append(
            f"| {display_name(sym)} | {get_sector(sym)} | {_rs_str(sym, rs_ratings)} | {_rs_relative_str(sym, rs_relative)} | "
            f"{_fmt_price(a['current_price'])} | "
            f"{ac_str} | {_fmt_pct(a.get('price_change_since_added_pct'))} | "
            f"{a.get('added_date') or '—'} | "
            f"{a.get('first_dip_date') or '—'} | "
            f"{a.get('deepest_dip_date') or '—'} | "
            f"{_fmt_pct(a.get('deepest_dip_pct'))} | "
            f"{a.get('crossback_date') or '—'} | "
            f"{cbr_str} | "
            f"{dipw_str} | {d1_str} | {d2_str} |"
        )
    return "\n".join(out)


def _table_recovery_extension(
    analysis: dict[str, dict],
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """🔻 Reversal Extension 历史组（跌破后仍在 EMA10 下方）。"""
    group = [s for s in analysis if analysis[s].get("recovery_status") == "reversal_extension"]
    out = []
    out.append("")
    out.append(f"## 🔻 Reversal Extension 历史组（跌破后仍在 EMA10 下方，共 {len(group)} 只）")
    out.append("")
    if not group:
        out.append("> （无）")
        return "\n".join(out)
    out.append(
        f"| 股票 | 行业 {RS_HEADER} 现价 | 加入日收 | 累计% | 加入日 | 首次破 | 最深日 | 最深% | vs EMA10 | 从底反弹 | 在册 |"
    )
    out.append("|------|------|------|------|------|---------|-------|--------|--------|--------|-------|----------|----------|------|")
    sorted_ext = sorted(group, key=lambda s: analysis[s]["reversal_extension_pct"])
    for sym in sorted_ext:
        a = analysis[sym]
        added_close = a.get("close_on_added_date")
        ac_str = _fmt_price(added_close)
        rev_ext = a.get("reversal_extension_pct")
        dipw_str = _days_in_wl(a.get("days_in_watchlist"))
        out.append(
            f"| {display_name(sym)} | {get_sector(sym)} | {_rs_str(sym, rs_ratings)} | {_rs_relative_str(sym, rs_relative)} | "
            f"{_fmt_price(a['current_price'])} | "
            f"{ac_str} | {_fmt_pct(a.get('price_change_since_added_pct'))} | "
            f"{a.get('added_date') or '—'} | "
            f"{a.get('first_dip_date') or '—'} | "
            f"{a.get('deepest_dip_date') or '—'} | "
            f"{_fmt_pct(a.get('deepest_dip_pct'))} | "
            f"{_fmt_pct(rev_ext)} | "
            f"{_fmt_pct(a.get('recovery_from_bottom_pct'))} | "
            f"{dipw_str} |"
        )
    return "\n".join(out)


def _table_never_dipped(
    analysis: dict[str, dict],
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """✓ 从未跌破组。"""
    group = [s for s in analysis if analysis[s].get("recovery_status") == "never_dipped"]
    out = []
    out.append("")
    out.append(f"## ✓ 从未跌破 EMA10（{len(group)} 只）")
    out.append("")
    if not group:
        out.append("> （无）")
        return "\n".join(out)
    out.append(f"| 股票 {RS_HEADER} 累计% | 在册 |")
    out.append("|------|------|------|-------|------|")
    sorted_never = sorted(
        group,
        key=lambda s: -(analysis[s].get("price_change_since_added_pct") or 0),
    )
    for sym in sorted_never:
        a = analysis[sym]
        dipw_str = _days_in_wl(a.get("days_in_watchlist"))
        out.append(
            f"| {display_name(sym)} | {_rs_str(sym, rs_ratings)} | {_rs_relative_str(sym, rs_relative)} | "
            f"{_fmt_pct(a.get('price_change_since_added_pct'))} | {dipw_str} |"
        )
    return "\n".join(out)


def _table_pullback(
    analysis: dict[str, dict],
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """↘️ 回踩专区。"""
    pullback_starting = [s for s in analysis if analysis[s].get("pullback_state") == "starting"]
    pullback_deep = [s for s in analysis if analysis[s].get("pullback_state") == "deep"]
    out = []
    out.append("")
    out.append("## ↘️ 回踩专区（突破后回踩中，可关注二次突破机会）")
    out.append("")
    if not (pullback_starting or pullback_deep):
        out.append("> （无）")
        return "\n".join(out)
    out.append(f"| 股票 {RS_HEADER} 现价 | 峰值 | 回撤 | EMA10 | MA20 | 状态 |")
    out.append("|------|------|------|------|------|------|------|-------|------|")
    for sym in pullback_deep + pullback_starting:
        a = analysis[sym]
        if not a["available"]:
            continue
        state_icon = "🔻深度回踩" if a["pullback_state"] == "deep" else "↘️回踩中"
        out.append(
            f"| {display_name(sym)} | {_rs_str(sym, rs_ratings)} | {_rs_relative_str(sym, rs_relative)} | "
            f"{_fmt_price(a['current_price'])} | "
            f"{_fmt_price(a.get('peak_price_since_added'))} | "
            f"{_fmt_pct(a.get('pullback_from_peak_pct'))} | "
            f"${a['ema10']:.2f} | ${a['ma20']:.2f} | {state_icon} |"
        )
    return "\n".join(out)


def _table_full(
    analysis: dict[str, dict],
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """📊 全部观察清单（一行一只）。"""
    symbols = list(analysis.keys())
    out = []
    out.append("")
    out.append("## 📊 全部观察清单（一张表看全部）")
    out.append("")
    out.append("**列含义**：")
    out.append(
        f"- **{RS_RATING_LABEL}**：O'Neil CAN SLIM 原始涨幅加权排名。"
        "过去 12 个月按 63 个交易日切成 4 个季度，近 3 个月 ×0.4、4-6 月 ×0.2、7-9 月 ×0.2、10-12 月 ×0.2，"
        "加权得 RS Score，再在**美股全市场普通股**（约 6300 只）内换算成 1-99 的百分位。"
        "**不参照任何基准指数，只看绝对涨幅**；99 = 全市场最强，≥80 视为强势股。"
    )
    out.append(
        f"- **{RS_RELATIVE_LABEL}**：策略内部口径的对标基准超额收益排名。"
        "0.4×(个股 252 日涨幅÷基准 252 日涨幅−1) + 0.3×(126 日) + 0.3×(60 日)，"
        "再在 **UNIVERSE.md 固定股票池**内换算成 0-100 的百分位。"
        "基准 ETF：美股 SPY、港股 ASHR、台股 EWT。**回答的是「它比大盘强多少」**。"
    )
    out.append(
        "- **两个数字不是一回事**：大盘走弱时，一只「比大盘抗跌、但自己也跌了不少」的股票，"
        "RS% 会很高而 RS 评级很低。这是两个口径的设计差异，不是数据错误。"
    )
    out.append("- **入选日**：加入 watchlist 的日期")
    out.append("- **入选量比**：加入那天成交量 / 10日均量（即被扫到的原因）")
    out.append("- **加入后涨跌**：从入选日到现在的百分比变化")
    out.append("- **比 10 天均价**：现价相对 EMA10 的偏移（负值=在下方延伸）")
    out.append("- **涨回时量**：涨回那天成交量是平时几倍（>1=放量涨回，<1=缩量涨回）")
    out.append("- **入册到最低**：进清单到跌最狠那天的天数")
    out.append("- **从最低反弹**：从最深底部到今天的反弹幅度")
    out.append("")
    out.append(
        f"| 股票 | 行业 {RS_HEADER} 入选日 | 入选量比 | 现价 | 加入后涨跌 | EMA10 | MA20 | 比10天均价 | 在册 | 首次跌破 | 跌最狠那天 | 涨回那天 | 涨回时量 | 入→底 | 底→今 | 反弹 | 情况 |"
    )
    out.append("|------|------|------|------|------|--------|---------|------|-----------|-------|------|-----------|------|----------|------------|----------|-------|-------|------|------|")
    for sym in symbols:
        a = analysis[sym]
        if not a["available"]:
            days_str = f"{a.get('days_in_watchlist')}天" if a.get('days_in_watchlist') is not None else "—"
            out.append(
                f"| {display_name(sym)} | {get_sector(sym)} | {_rs_str(sym, rs_ratings)} | "
                f"{_rs_relative_str(sym, rs_relative)} | — | — | 数据缺失 | — | — | — | — | {days_str} | — | — | — | — | — | — | — | — | ⚠️ |"
            )
            continue
        rev_ext = a.get("reversal_extension_pct")
        cbr_str = f"{a.get('crossback_volume_ratio'):.1f}x" if a.get('crossback_volume_ratio') is not None else "—"
        first_vol_str = f"{a.get('first_seen_volume_ratio'):.1f}x" if a.get('first_seen_volume_ratio') is not None else "—"
        d1 = a.get("days_added_to_deepest_dip")
        d2 = a.get("days_deepest_dip_to_now")
        dipw_str = _days_in_wl(a.get("days_in_watchlist"))
        d1_str, d2_str = _days_pair(d1, d2)
        out.append(
            f"| {display_name(sym)} | {get_sector(sym)} | {_rs_str(sym, rs_ratings)} | "
            f"{_rs_relative_str(sym, rs_relative)} | "
            f"{a.get('added_date') or '—'} | {first_vol_str} | "
            f"{_fmt_price(a['current_price'])} | {_fmt_pct(a.get('price_change_since_added_pct'))} | "
            f"${a['ema10']:.2f} | ${a['ma20']:.2f} | {_fmt_pct(rev_ext)} | "
            f"{dipw_str} | "
            f"{a.get('first_dip_date') or '—'} | "
            f"{a.get('deepest_dip_date') or '—'} | "
            f"{a.get('crossback_date') or '—'} | "
            f"{cbr_str} | "
            f"{d1_str} | {d2_str} | "
            f"{_fmt_pct(a.get('recovery_from_bottom_pct'))} | "
            f"{_status_str(a)} |"
        )
    return "\n".join(out)


def generate_watchlist_daily_report(
    analysis: dict[str, dict],
    output_dir: str = "output/shared/watchlist_daily",
    volume_threshold: float = DEFAULT_CROSSBACK_SIGNAL_VOLUME_THRESHOLD,
    max_days: int = DEFAULT_MAX_DAYS_SINCE_CROSSBACK,
    rs_ratings: dict[str, int] | None = None,
    rs_relative: dict[str, float] | None = None,
) -> str:
    """
    把 watchlist 分析结果（第二层）写入 Markdown 每日报告。

    返回：报告文件的完整路径。
    """
    today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    target_dir = Path(output_dir) / today_str
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"报告_观察清单第二层_{today_str}.md"

    symbols = list(analysis.keys())
    available_count = sum(1 for a in analysis.values() if a["available"])
    crossback_today_count = sum(1 for a in analysis.values() if a["ema10_crossback_today"])
    rev_ext_now_count = sum(1 for a in analysis.values() if a["is_reversal_extension"])
    rev_ext_strong_count = sum(
        1 for a in analysis.values()
        if a["reversal_extension_alert"] == "strong"
    )
    pullback_starting_count = sum(
        1 for a in analysis.values() if a.get("pullback_state") == "starting"
    )
    pullback_deep_count = sum(
        1 for a in analysis.values() if a.get("pullback_state") == "deep"
    )
    cb_count = sum(1 for a in analysis.values() if a.get("recovery_status") == "ema_crossback")
    ext_count = sum(1 for a in analysis.values() if a.get("recovery_status") == "reversal_extension")
    never_count = sum(1 for a in analysis.values() if a.get("recovery_status") == "never_dipped")

    crossback_signals_count = len(
        filter_crossback_signals(analysis, volume_threshold, max_days)
    )

    lines: list[str] = []
    lines.append(f"# 观察清单第二层分析 — {today_str}")
    lines.append("")
    lines.append(
        f"> 生成时间：{datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}  "
    )
    lines.append(
        "> 范围：watchlist 中所有股票（含当天新增与历史观察）  "
    )
    lines.append(
        "> 阈值：穿回量比 ≥ "
        f"{volume_threshold}×，穿回日距今 ≤ {max_days} 天  "
    )
    lines.append(
        "> 协议：满足 ①自加入起曾跌破 EMA10  ②当前已站回  ③穿回日放量  "
        "④新鲜度过滤 —— 4 条件才算\"第二层穿回信号\"。"
    )
    lines.append(
        f"> **RS 两列口径（务必分清，两个数不是一回事）**：  "
    )
    lines.append(
        f"> 1. **{RS_RATING_LABEL}** —— O'Neil CAN SLIM 口径。  "
        "过去 12 个月按 63 个交易日切成 4 个季度，近 3 个月 ×0.4、4-6 月 ×0.2、"
        "7-9 月 ×0.2、10-12 月 ×0.2，加权得 RS Score，"
        "再在**美股全市场普通股（约 6300 只）**内换算成 1-99 的百分位。"
        "**不参照基准指数，只看绝对涨幅**；99 = 全市场最强，≥80 视为强势股。"
    )
    lines.append(
        f"> 2. **{RS_RELATIVE_LABEL}** —— 策略内部口径。  "
        "0.4×(个股 252 日涨幅÷基准 252 日涨幅−1) + 0.3×(126 日) + 0.3×(60 日)，"
        "再在 **UNIVERSE.md 固定股票池**内换算成 0-100 的百分位。"
        "基准 ETF：美股 SPY、港股 ASHR、台股 EWT。"
        "**回答的是「它比大盘强多少」**。"
    )
    lines.append(
        "> 两者关系：**第一个回答「它自己在全市场排第几」，第二个回答「它比大盘强多少」**。"
        "大盘走弱时，一只「比大盘抗跌但自己也跌了不少」的股票，"
        "RS% 会明显高于 RS 评级——这是设计差异，不是数据错误。"
    )
    lines.append("")
    lines.append("## 📋 摘要")
    lines.append("")
    lines.append("| 维度 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| **🎯 第二层穿回信号（放量）** | **{crossback_signals_count}** |")
    lines.append(f"| 观察清单股票总数 | {len(symbols)} |")
    lines.append(f"| 其中可用数据 | {available_count} |")
    lines.append(f"| 今日 EMA10 crossback | {crossback_today_count} |")
    lines.append(f"| Reversal Extension（Kell） | {rev_ext_now_count}（深度 {rev_ext_strong_count}）|")
    lines.append(f"| 回踩中 / 深度回踩 | {pullback_starting_count} / {pullback_deep_count} |")
    lines.append(f"| ✅ EMA Crossback 历史组 | {cb_count} |")
    lines.append(f"| 🔻 Reversal Extension 历史组 | {ext_count} |")
    lines.append(f"| ✓ 从未跌破 | {never_count} |")
    lines.append("")

    lines.append(_table_crossback_signals(analysis, volume_threshold, max_days, rs_ratings, rs_relative))
    lines.append(_table_recovery_crossback(analysis, rs_ratings, rs_relative))
    lines.append(_table_recovery_extension(analysis, rs_ratings, rs_relative))
    lines.append(_table_never_dipped(analysis, rs_ratings, rs_relative))
    lines.append(_table_pullback(analysis, rs_ratings, rs_relative))
    lines.append(_table_full(analysis, rs_ratings, rs_relative))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 操作提醒")
    lines.append("")
    lines.append("| 要点 | 说明 |")
    lines.append("|------|------|")
    lines.append("| 信号定位 | 第二层（watchlist 分析）优先级 **≥** 第一层（9 策略信号） |")
    lines.append("| 触发条件 | 满足 4 条件的穿回信号才有意义，缺一不算 |")
    lines.append("| 新鲜度 | 穿回日距今 > 7 天视为过期，不作为行动依据 |")
    lines.append("| 量能 | 穿回量比 < 1.0× 视为缩量，不算\"放量穿回\" |")
    lines.append("| 数据来源 | output/shared/watchlist.json + 今日 K 线 |")
    lines.append("")
    lines.append(f"*报告生成时间：{datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}*")

    target_file.write_text("\n".join(lines), encoding="utf-8")
    return str(target_file)
