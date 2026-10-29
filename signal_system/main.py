"""
main.py — 事件驱动交易信号系统入口

使用方法：
    # 实盘信号模式（分析今天的数据）
    uv run python main.py --mode live
    uv run python main.py --mode live --strategy v1

    # 回测模式（分析历史数据）
    uv run python main.py --mode backtest --start 2024-01-01 --end 2024-12-31
    uv run python main.py --mode backtest --start 2024-01-01 --end 2024-12-31 --strategy v1 --split

    # 股票池扫描模式（查询 SA Quant Rating，自动更新 UNIVERSE.md）
    uv run python main.py --mode scan
    uv run python main.py --mode scan --dry-run   # 只打印结果，不修改文件

参数：
    --mode:     运行模式，live / backtest / scan
    --strategy: 策略 ID（默认读 config.yaml 的 active_strategy，再 fallback "v1"）
    --start:    回测起始日期，格式 YYYY-MM-DD（仅 backtest 模式需要）
    --end:      回测结束日期，格式 YYYY-MM-DD（仅 backtest 模式需要）
    --split:    回测时自动拆分样本内/样本外
    --dry-run:  扫描模式下只打印，不写文件
    --config:   配置文件路径（默认 config.yaml）
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from backtest.engine import BacktestEngine
from data.fetcher import fetch
from data.rs_rating import compute_rs_ratings
from data.rs_relative import compute_relative_strength_percentiles
from events import EventQueue
from signals.generator import process_signals
from signals.log_generator import update_signals_log
from signals.positions import load_positions, save_positions
from signals.report import generate_daily_report
from strategies.registry import get_strategy
from universe.manager import get_universe, _read_universe_md
from universe.us_market import get_us_common_stocks
from universe.updater import run_scan
from watchlist import (
    add_stocks_from_records,
    analyze_watchlist,
    print_watchlist_report,
    generate_watchlist_daily_report,
)

# 加载 .env 文件（Alpaca API Key 等）
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=str(_env_path), override=True)


def load_config(config_path: str = "config.yaml") -> dict:
    """读取配置文件。"""
    path = Path(config_path)
    if not path.exists():
        print(f"[错误] 找不到配置文件：{config_path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_strategy(config: dict, strategy_arg: str | None) -> tuple[type, str, str, dict]:
    """
    解析策略参数，返回 (策略类, 策略注册表key, 策略folder_id, 策略配置)。

    优先级：--strategy 参数 > config.yaml active_strategy > 默认 "v1"
    """
    strategy_key = strategy_arg or config.get("active_strategy", "v1")
    strategy_cls = get_strategy(strategy_key)
    strategy_id = strategy_cls.strategy_id       # 如 "v1_wizard"（文件夹名）
    strategy_name = strategy_cls.strategy_name   # 如 "魔法师策略V1"

    # 从 strategies.{key} 读取策略参数
    strategies_cfg = config.get("strategies", {})
    strategy_config = strategies_cfg.get(strategy_key, {})

    return strategy_cls, strategy_id, strategy_name, strategy_config


def run_live(config: dict, strategy_arg: str | None) -> None:
    """
    实盘信号模式：分析今天的数据，输出当前是否有信号。

    这是每天收盘后运行的模式。
    """
    strategy_cls, strategy_id, strategy_name, strategy_config = resolve_strategy(config, strategy_arg)

    print("=" * 60)
    print(f"{strategy_name} 信号系统 — 实盘模式")
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Step 1: 获取股票池
    t0 = time.time()
    print("\n[步骤 1/3] 更新股票池...")
    symbols = get_universe(config)
    print(f"股票池共 {len(symbols)} 只")
    t1 = time.time()
    print(f"[耗时] 股票池获取: {t1-t0:.1f}秒")

    # Step 2: 下载历史数据
    t2 = time.time()
    print("\n[步骤 2/3] 下载历史数据...")
    history_days = config.get("data", {}).get("history_days", 504)
    # 下载范围 = 交易股票池 ∪ 美股全市场。策略只用前者（保持扫描速度），
    # RS 评级用后者（分母稳定，不会因为新闻池每天漂移而变）。
    # 一次下载、两处消费，不额外增加一轮网络请求。
    rs_symbols = set(get_us_common_stocks())
    market_data = fetch(sorted(set(symbols) | rs_symbols), history_days=history_days, live_mode=True)

    if not market_data:
        print("[错误] 未能获取任何股票数据，退出")
        sys.exit(1)

    # 拆成两份：策略视图（交易池）和 RS 视图（全市场）
    symbol_set = set(symbols)
    rs_market_data = market_data
    market_data = {s: d for s, d in market_data.items() if s in symbol_set}

    # 确保基准 ETF 在 market_data 中（用于分市场 RS 计算）
    for benchmark, syms in [("SPY", ["SPY"]), ("ASHR", ["ASHR"]), ("EWT", ["EWT"])]:
        if benchmark not in market_data:
            data = fetch(syms, history_days=history_days, live_mode=True)
            if data and benchmark in data:
                market_data[benchmark] = data[benchmark]
                rs_market_data.setdefault(benchmark, data[benchmark])

    # Step 3: 运行策略
    t3 = time.time()
    print(f"\n[步骤 3/3] 运行 {strategy_name}...")
    # v_trend_collection 需要所有趋势策略实例
    if strategy_id == "v_trend_collection":
        from strategies.registry import STRATEGY_REGISTRY
        all_strategies = []
        for sid, cls in STRATEGY_REGISTRY.items():
            if sid not in ("v_adx50", "v_trend_collection"):
                all_strategies.append(cls(strategy_config, market_data, live_mode=True))
        strategy = strategy_cls(strategy_config, market_data, live_mode=True, all_strategies=all_strategies)
    else:
        strategy = strategy_cls(strategy_config, market_data, live_mode=True)

    # 载入上次持仓（跨天追踪出场条件）
    if config.get("track_positions", True):
        saved_positions = load_positions(strategy_id)
        if saved_positions:
            strategy.positions = saved_positions
            print(f"[持仓] 已加载 {len(saved_positions)} 个持仓：{', '.join(saved_positions.keys())}")
        else:
            print("[持仓] 暂无持仓记录")
    else:
        print("[持仓] 持仓管理已禁用（config.yaml: track_positions=false），仅作为买入选股器使用")

    # 快照持仓引用：出场信号发出后策略会自动删除持仓，需在运行后恢复
    # （Position 对象是原地修改的，快照保存引用即可，days_held/highest_price 更新会同步体现）
    pre_run_snapshot = dict(strategy.positions)

    queue = EventQueue()
    today = datetime.now(tz=timezone.utc)
    strategy.run_date(today, queue)
    t4 = time.time()
    print(f"[耗时] 策略计算: {t4-t3:.1f}秒")

    # 恢复被出场信号自动删除的持仓
    # 用户手动告知平仓前，系统每日持续发出提醒信号
    for symbol, pos in pre_run_snapshot.items():
        if symbol not in strategy.positions:
            strategy.positions[symbol] = pos

    # 保存更新后的持仓（新买入已加入；已出场的保留，等待用户确认平仓）
    if config.get("track_positions", True):
        save_positions(strategy.positions, strategy_id)
        if strategy.positions:
            print(f"[持仓] 已保存 {len(strategy.positions)} 个持仓：{', '.join(strategy.positions.keys())}")

    # 输出信号
    records = process_signals(queue, config, strategy_id=strategy_id)
    if not records:
        print("\n今日无有效信号。")
        print("（SEPA 条件严格，无信号是正常的。有信号时才需要关注。）")

    # ── 观察清单更新（量比 >2x 的买入信号自动加入）────────────────
    added = add_stocks_from_records(records, strategy_id=strategy_id)
    if added:
        print(f"\n[观察清单] 新增 {len(added)} 只（量比 ≥2x）：{', '.join(added)}")

    # ── RS 评级：分母是美股全市场，不是交易股票池 ────────────────
    rs_ratings = compute_rs_ratings(rs_market_data)
    print(f"[RS] O'Neil RS 评级覆盖 {len(rs_ratings)} 只（美股全市场口径）")

    # ── 策略内部 RS%：分母是 UNIVERSE.md 固定池，对标基准 ETF ──────
    rs_relative = compute_relative_strength_percentiles(
        market_data, pool_symbols=set(_read_universe_md())
    )
    print(f"[RS] 策略内部 RS% 覆盖 {len(rs_relative)} 只（对标基准 ETF，固定池口径）")

    # ── 观察清单分析（EMA10 crossback + Reversal extension）────────
    print("\n[观察清单] 分析 watchlist 中的股票...")
    watchlist_analysis = analyze_watchlist(market_data, rs_relative=rs_relative)
    print_watchlist_report(watchlist_analysis, rs_ratings=rs_ratings)

    # ── 第二层：观察清单分析落盘（用户优先级 ≥ 第一层）──────────────
    try:
        wl_report_path = generate_watchlist_daily_report(
            watchlist_analysis, rs_ratings=rs_ratings, rs_relative=rs_relative
        )
        print(f"\n[观察清单报告（第二层）] 已生成：{wl_report_path}")
    except Exception as e:
        print(f"\n[观察清单报告（第二层）] 生成失败：{e}")

    # 生成每日 Markdown 报告（无论有无信号都生成）
    report_path = generate_daily_report(
        records,
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        rs_ratings=rs_ratings,
        rs_relative=rs_relative,
    )
    print(f"\n[报告] 今日报告：{report_path}")

    # 更新全策略信号汇总日志
    t5 = time.time()
    print("\n[信号日志] 更新全策略信号汇总...")
    update_signals_log(rs_ratings=rs_ratings, rs_relative=rs_relative)
    t6 = time.time()

    print(f"\n{'='*40}")
    print(f"[总耗时] 股票池: {t1-t0:.1f}秒 | 数据获取: {t3-t2:.1f}秒 | 策略计算: {t4-t3:.1f}秒 | 信号报告: {t6-t5:.1f}秒 | 合计: {t6-t0:.1f}秒")
    print(f"{'='*40}")


def run_backtest(
    config: dict,
    strategy_arg: str | None,
    start_str: str,
    end_str: str,
    split: bool = False,
    save_signals: bool = False,
    position_size: float = 1000.0,
    initial_capital: float = 50000.0,
) -> None:
    """
    回测模式：在历史数据上逐日运行策略，输出完整的性能报告。

    参数：
        split: 若为 True，自动将区间前 2/3 作为样本内，后 1/3 作为样本外，分别报告
    """
    strategy_cls, strategy_id, strategy_name, strategy_config = resolve_strategy(config, strategy_arg)

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as e:
        print(f"[错误] 日期格式不正确：{e}，请使用 YYYY-MM-DD")
        sys.exit(1)

    print("=" * 60)
    print(f"{strategy_name} 信号系统 — 回测模式")
    print(f"测试区间：{start_str} 至 {end_str}")
    print("=" * 60)

    # 使用手动股票池（回测不抓取新闻，从 UNIVERSE.md 读取）
    manual_symbols = _read_universe_md()
    if not manual_symbols:
        print("[错误] 回测模式找不到股票池，请检查 UNIVERSE.md 是否存在且包含股票")
        sys.exit(1)

    print(f"\n股票池：{manual_symbols}")

    if split:
        # 自动拆分：前 2/3 为样本内，后 1/3 为样本外
        total_days = (end_date - start_date).days
        split_point = start_date + timedelta(days=int(total_days * 2 / 3))
        split_str = split_point.strftime("%Y-%m-%d")

        print(f"\n[样本内] {start_str} 至 {split_str}")
        print(f"[样本外] {split_str} 至 {end_str}（考试数据，不调参数）\n")

        print("\n" + "─" * 60)
        print("运行样本内回测...")
        _run_single_backtest(
            config, strategy_cls, strategy_config, strategy_name,
            manual_symbols, start_date, split_point, "样本内",
            save_signals=save_signals,
            position_size=position_size,
            initial_capital=initial_capital,
        )

        print("\n" + "─" * 60)
        print("运行样本外回测（OOS）...")
        _run_single_backtest(
            config, strategy_cls, strategy_config, strategy_name,
            manual_symbols, split_point, end_date, "样本外 OOS ← 真正的考试",
            save_signals=save_signals,
            position_size=position_size,
            initial_capital=initial_capital,
        )
    else:
        _run_single_backtest(
            config, strategy_cls, strategy_config, strategy_name,
            manual_symbols, start_date, end_date,
            save_signals=save_signals,
            position_size=position_size,
            initial_capital=initial_capital,
        )


def _run_single_backtest(
    config: dict,
    strategy_cls: type,
    strategy_config: dict,
    strategy_name: str,
    symbols: list[str],
    start_date: datetime,
    end_date: datetime,
    label: str = "",
    save_signals: bool = False,
    position_size: float = 1000.0,
    initial_capital: float = 50000.0,
) -> None:
    """运行单段回测，打印报告并保存 Markdown 文件。"""
    try:
        engine = BacktestEngine(
            config,
            strategy_cls=strategy_cls,
            strategy_config=strategy_config,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            save_signals_csv=save_signals,
            strategy_id=strategy_cls.strategy_id if save_signals else "",
            position_size=position_size,
            initial_capital=initial_capital,
        )
        result = engine.run(verbose=True)
        result.print_report(label=label, strategy_name=strategy_name)

        # 保存 Markdown 报告到 output/{strategy_id}/backtest/
        strategy_id = strategy_cls.strategy_id
        start_str = start_date.strftime("%Y-%m-%d")
        end_str   = end_date.strftime("%Y-%m-%d")
        file_label = label.split()[0] if label else "全段"
        report_path = (
            Path("output") / strategy_id / "backtest"
            / f"回测报告_{file_label}_{start_str}_{end_str}.md"
        )
        result.save_report(report_path, label=label, strategy_name=strategy_name)
        print(f"  [报告] 已保存：{report_path}")
    except RuntimeError as e:
        print(f"[错误] {e}")


def run_scan_mode(config: dict, dry_run: bool = False) -> None:
    """
    股票池扫描模式：查询 Seeking Alpha Quant Rating，
    将 Strong Buy (≥ 4.5) 的新股票自动写入 UNIVERSE.md。
    """
    print("=" * 60)
    print("股票池扫描 — SA Quant Rating 扫描模式")
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if dry_run:
        print("（dry-run 模式：只打印结果，不修改文件）")
    print("=" * 60)

    added = run_scan(config, dry_run=dry_run)

    print("\n" + "=" * 60)
    if dry_run:
        print(f"扫描完成（dry-run）：发现 {added} 只 Strong Buy 候选股票")
    else:
        print(f"扫描完成：共新增 {added} 只股票到 UNIVERSE.md")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="多策略交易信号系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  uv run python main.py --mode live
  uv run python main.py --mode live --strategy v1
  uv run python main.py --mode backtest --start 2024-01-01 --end 2024-12-31 --strategy v1
  uv run python main.py --mode backtest --start 2024-01-01 --end 2024-12-31 --strategy v1 --split
  uv run python main.py --mode scan
  uv run python main.py --mode scan --dry-run
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["live", "backtest", "scan"],
        required=True,
        help="运行模式：live（实盘信号）/ backtest（历史回测）/ scan（SA 股票池扫描）",
    )
    parser.add_argument(
        "--strategy",
        default=None,
        help="策略 ID（如 v1）。未指定时使用 config.yaml 中的 active_strategy",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="回测起始日期（YYYY-MM-DD），仅 backtest 模式需要",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="回测结束日期（YYYY-MM-DD），仅 backtest 模式需要",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="回测时自动拆分为样本内（前2/3）和样本外OOS（后1/3），分别输出报告",
    )
    parser.add_argument(
        "--save-signals",
        action="store_true",
        dest="save_signals",
        help="回测时同时把买入信号追加写入 signals.csv（用于补档过去几天的信号历史）",
    )
    parser.add_argument(
        "--position-size",
        type=float,
        default=1000.0,
        dest="position_size",
        help="每次买入金额（美元），默认 1000",
    )
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=50000.0,
        dest="initial_capital",
        help="初始本金（美元），默认 50000",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="扫描模式：只打印发现的 Strong Buy 股票，不修改 UNIVERSE.md",
    )
    parser.add_argument(
        "--all-strategies",
        action="store_true",
        dest="all_strategies",
        help="live 模式：对所有已注册策略分别运行（默认行为；指定 --strategy 时不生效）",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径（默认 config.yaml）",
    )

    args = parser.parse_args()
    config = load_config(args.config)

    # ── live 模式约定：永远跑全部策略，--strategy 参数忽略 ──
    # 用户约定："跑Livetest = 所有策略"
    # --strategy 仅对 backtest 模式有意义（回测单策略）
    if args.mode == "live":
        if args.strategy and not args.all_strategies:
            print(f"[提示] live 模式默认跑全部策略，--strategy={args.strategy} 已忽略")
        from strategies.registry import STRATEGY_REGISTRY, STRATEGY_CATEGORIES
        strategy_keys = [k for k in STRATEGY_REGISTRY.keys() if k != "v_trend_collection"]

        # 按类别分组显示
        categories: dict[str, list[str]] = {}
        for k in strategy_keys:
            cat = STRATEGY_CATEGORIES.get(k, "未分类")
            categories.setdefault(cat, []).append(k)

        print(f"=" * 60)
        print(f"全策略实盘扫描（共 {len(strategy_keys)} 个策略）")
        for cat, keys in categories.items():
            print(f"  【{cat}】{keys}")
        print(f"=" * 60)

        # ── 共享数据下载（所有策略只下载一次）─────────────────────
        t0 = time.time()
        print("\n[共享步骤 1/2] 更新股票池...")
        symbols = get_universe(config)
        print(f"股票池共 {len(symbols)} 只")

        print("\n[共享步骤 2/2] 下载历史数据...")
        history_days = config.get("data", {}).get("history_days", 504)
        # 同 run_single_strategy：一次下载，策略用交易池，RS 用全市场
        rs_symbols = set(get_us_common_stocks())
        market_data = fetch(sorted(set(symbols) | rs_symbols), history_days=history_days, live_mode=True)
        if not market_data:
            print("[错误] 未能获取任何股票数据，退出")
            sys.exit(1)
        symbol_set = set(symbols)
        rs_market_data = market_data
        market_data = {s: d for s, d in market_data.items() if s in symbol_set}
        # 确保基准 ETF 在 market_data 中（用于分市场 RS 计算）
        for benchmark, syms in [("SPY", ["SPY"]), ("ASHR", ["ASHR"]), ("EWT", ["EWT"])]:
            if benchmark not in market_data:
                data = fetch(syms, history_days=history_days, live_mode=True)
                if data and benchmark in data:
                    market_data[benchmark] = data[benchmark]
                    rs_market_data.setdefault(benchmark, data[benchmark])
        print(f"[数据] 成功获取 {len(market_data)}/{len(symbols)} 只股票的数据（含基准 ETF）")
        t_data = time.time()
        print(f"[耗时] 共享数据获取: {t_data - t0:.1f}秒\n")

        # RS 评级分母 = 美股全市场（不是交易股票池），整个循环共用一份
        rs_ratings = compute_rs_ratings(rs_market_data)
        print(f"[RS] O'Neil RS 评级覆盖 {len(rs_ratings)} 只（美股全市场口径）")

        # 策略内部 RS%：分母 = UNIVERSE.md 固定池，对标基准 ETF
        rs_relative = compute_relative_strength_percentiles(
            market_data, pool_symbols=set(_read_universe_md())
        )
        print(f"[RS] 策略内部 RS% 覆盖 {len(rs_relative)} 只（对标基准 ETF，固定池口径）\n")

        # ── 每个策略依次运行（复用已下载的数据）──────────────────
        for sk in strategy_keys:
            print(f"\n{'━'*60}")
            print(f"▶ 策略：{sk}")
            print(f"{'━'*60}")

            t1 = time.time()
            strategy_cls, strategy_id, strategy_name, strategy_config = resolve_strategy(config, sk)
            cat = STRATEGY_CATEGORIES.get(sk, "未分类")
            print(f"{strategy_name}【{cat}】信号系统 — 实盘模式")
            print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print("=" * 60)

            # v_trend_collection 需要所有趋势策略实例
            if sk == "v_trend_collection":
                from strategies.registry import STRATEGY_REGISTRY
                all_strats = []
                for sid, cls in STRATEGY_REGISTRY.items():
                    if sid not in ("v_adx50", "v_trend_collection"):
                        all_strats.append(cls(strategy_config, market_data, live_mode=True))
                strategy = strategy_cls(strategy_config, market_data, live_mode=True, all_strategies=all_strats)
            else:
                strategy = strategy_cls(strategy_config, market_data, live_mode=True)

            if config.get("track_positions", True):
                saved_positions = load_positions(strategy_id)
                if saved_positions:
                    strategy.positions = saved_positions
                    print(f"[持仓] 已加载 {len(saved_positions)} 个持仓：{', '.join(saved_positions.keys())}")
                else:
                    print("[持仓] 暂无持仓记录")
            else:
                print("[持仓] 持仓管理已禁用（仅作为买入选股器使用）")

            pre_run_snapshot = dict(strategy.positions)
            queue = EventQueue()
            today = datetime.now(tz=timezone.utc)
            strategy.run_date(today, queue)
            t2 = time.time()
            print(f"[耗时] 策略计算: {t2-t1:.1f}秒")

            for symbol, pos in pre_run_snapshot.items():
                if symbol not in strategy.positions:
                    strategy.positions[symbol] = pos

            if config.get("track_positions", True):
                save_positions(strategy.positions, strategy_id)
                if strategy.positions:
                    print(f"[持仓] 已保存 {len(strategy.positions)} 个持仓：{', '.join(strategy.positions.keys())}")

            records = process_signals(queue, config, strategy_id=strategy_id)
            if not records:
                print("\n今日无有效信号。")
            else:
                print(f"\n共 {len(records)} 个信号")

            # ── 观察清单更新（量比 >3x 的买入信号自动加入）──────────
            added = add_stocks_from_records(records, strategy_id=strategy_id)
            if added:
                print(f"[观察清单] 新增 {len(added)} 只（量比 ≥3x）：{', '.join(added)}")

            report_path = generate_daily_report(
                records,
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                rs_ratings=rs_ratings,
                rs_relative=rs_relative,
            )
            print(f"[报告] 今日报告：{report_path}")
            t3 = time.time()
            print(f"[耗时] 信号+报告: {t3-t2:.1f}秒")

        # ── 全策略跑完后：分析 watchlist 状态 ────────────────────
        print("\n[观察清单] 分析 watchlist 中的股票...")
        watchlist_analysis = analyze_watchlist(market_data, rs_relative=rs_relative)
        print_watchlist_report(watchlist_analysis, rs_ratings=rs_ratings)

        # ── 第二层：观察清单分析落盘（用户优先级 ≥ 第一层）─────────
        try:
            wl_report_path = generate_watchlist_daily_report(
                watchlist_analysis, rs_ratings=rs_ratings, rs_relative=rs_relative
            )
            print(f"\n[观察清单报告（第二层）] 已生成：{wl_report_path}")
        except Exception as e:
            print(f"\n[观察清单报告（第二层）] 生成失败：{e}")

        print("\n" + "=" * 60)
        print("全部策略实盘扫描完成")
        print(f"数据获取耗时: {t_data - t0:.1f}秒")
        print(f"=" * 60)

        # 更新全策略信号汇总日志（一次性）
        print("\n[信号日志] 更新全策略信号汇总...")
        update_signals_log(rs_ratings=rs_ratings, rs_relative=rs_relative)
        return

    if args.mode == "live":
        run_live(config, args.strategy)
    elif args.mode == "backtest":
        if not args.start or not args.end:
            print("[错误] 回测模式必须指定 --start 和 --end")
            parser.print_help()
            sys.exit(1)
        run_backtest(config, args.strategy, args.start, args.end, split=args.split, save_signals=args.save_signals, position_size=args.position_size, initial_capital=args.initial_capital)
    elif args.mode == "scan":
        run_scan_mode(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
