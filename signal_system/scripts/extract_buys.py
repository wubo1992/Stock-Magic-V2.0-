"""
scripts/extract_buys.py — 提取每日买入信号（含 RS/SPY + 板块 + 板块内排名）

用法：
    uv run python scripts/extract_buys.py <YYYY-MM-DD>
    uv run python scripts/extract_buys.py              # 默认今天

输出列：
    代码 | 日期 | 价格 | 量倍数 | RS/SPY | 板块 | 板块排名 | 策略
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.rs_spy import calc_rs_spy_batch
from data.sector_cache import get_sector


def parse_buys(date_str: str) -> dict[str, list[tuple[str, str]]]:
    """从 output/<strategy>/<date>/ 目录的 Markdown 报告里解析买入信号"""
    base = ROOT / "output"
    all_buys = {}
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name == "shared":
            continue
        today = d / date_str
        if not today.exists():
            continue
        report = next(iter(today.glob("*.md")), None)
        if not report:
            continue
        matches = re.findall(r"今日新增\*\* — 买入 (\S+)\s+(★+☆?)", report.read_text())
        if matches:
            all_buys[d.name] = matches
    return all_buys


def build_table(date_str: str, window: int = 50) -> None:
    all_buys = parse_buys(date_str)
    if not all_buys:
        print(f"未找到 {date_str} 的任何信号报告")
        return

    unique = set()
    for items in all_buys.values():
        unique.update([t for t, _ in items])

    # 量倍数 + RS/SPY + 板块
    rows = []
    for t in unique:
        try:
            df = pd.read_pickle(ROOT / f"data/cache/{t}.pkl")
        except FileNotFoundError:
            continue
        if len(df) < 20:
            continue
        lv = df["volume"].iloc[-1]
        av = df["volume"].tail(20).mean()
        m = lv / av if av > 0 else 0
        rows.append({
            "ticker": t,
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "close": float(df["close"].iloc[-1]),
            "vol_mult": m,
            "sector": get_sector(t),
        })

    if not rows:
        print("无有效数据")
        return

    # 批量算 RS/SPY
    rs_map = calc_rs_spy_batch([r["ticker"] for r in rows], window=window)
    for r in rows:
        r["rs_spy"] = rs_map.get(r["ticker"])

    # 板块内按量倍数排名（rank 1 = 板块内最强）
    df = pd.DataFrame(rows)
    df["sector_rank"] = (
        df.groupby("sector")["vol_mult"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

    # 总排序：量倍数降序
    df = df.sort_values("vol_mult", ascending=False).reset_index(drop=True)

    # 策略映射
    ts_map = {t: [s for s in all_buys if any(t == tk for tk, _ in all_buys[s])] for t in unique}

    # 打印
    print(f"\n{'='*120}")
    print(f"日期：{date_str}　|　信号总数：{len(df)}　|　RS 窗口：{window} 个交易日（{window/5:.0f} 周）")
    print(f"{'='*120}")
    header = f'{"代码":<7}{"价格":>9}{"量倍数":>8}{"RS/SPY":>9}  {"板块":<28}{"排名":>5}  策略'
    print(header)
    print("-" * 120)
    for _, r in df.iterrows():
        rs = f"{r.rs_spy:.2f}" if r.rs_spy is not None and not pd.isna(r.rs_spy) else "N/A"
        sector = r.sector if r.sector != "N/A" else "(未分类)"
        rank = f"{int(r.sector_rank)}/{len(df[df.sector==r.sector])}"
        strats = ",".join(ts_map.get(r.ticker, []))
        print(
            f'{r.ticker:<7}{r.close:>9.2f}{r.vol_mult:>8.2f}x{rs:>9}  {sector:<28}{rank:>5}  {strats}'
        )

    # 多策略共识
    consensus = [(t, len(ts_map.get(t, []))) for t in unique if len(ts_map.get(t, [])) >= 2]
    if consensus:
        consensus.sort(key=lambda x: -x[1])
        print(f"\n多策略共识（≥2）：{', '.join(f'{t}({n})' for t, n in consensus)}")

    # 板块分布
    from collections import Counter
    sec_dist = Counter(r["sector"] for r in rows if r["sector"] != "N/A")
    if sec_dist:
        print("\n板块分布：")
        for s, n in sec_dist.most_common():
            print(f"  {s}: {n}")

    # 策略分布
    print(
        "\n策略分布："
        + " / ".join(
            f"{s}={len(items)}"
            for s, items in sorted(all_buys.items(), key=lambda x: -len(x[1]))
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取每日买入信号（含 RS/SPY + 板块）")
    parser.add_argument("date", nargs="?", default=None, help="日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--window", "-w", type=int, default=50,
                        help="RS 窗口（交易日数，默认 50 = 10 周）")
    args = parser.parse_args()
    date = args.date or pd.Timestamp.now().strftime("%Y-%m-%d")
    build_table(date, window=args.window)