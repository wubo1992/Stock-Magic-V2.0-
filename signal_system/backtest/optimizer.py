"""
backtest/optimizer.py — 参数优化引擎

职责：
  1. 从 UNIVERSE.md 提取股票列表
  2. 定义策略参数搜索空间
  3. 并行运行多次回测采样参数组合
  4. 样本内筛选 + 样本外验证，返回最优参数

使用方式：
    from backtest.optimizer import optimize
    champion = optimize(
        strategy_id="v1_plus",
        n_trials=100,
        in_sample_start=datetime(2020, 1, 1),
        in_sample_end=datetime(2022, 12, 31),
        oos_start=datetime(2024, 1, 1),
        oos_end=datetime(2026, 3, 27),
    )
"""

from __future__ import annotations

import json
import math
import os
import random
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from backtest.engine import BacktestEngine, BacktestResult
from strategies.registry import STRATEGY_REGISTRY

# ────────────────────────────────────────────────────────────────
# 工作目录切换（必须放在最前面）
# ────────────────────────────────────────────────────────────────

PROJECT_ROOT = "/Users/wubo/Desktop/信号系统克劳德V3.1_Minimax支线/signal_system"
os.chdir(PROJECT_ROOT)

# ────────────────────────────────────────────────────────────────
# 参数搜索空间
# ────────────────────────────────────────────────────────────────

PARAM_RANGES: dict[str, dict[str, list[Any]]] = {
    "v1_plus": {
        "stop_loss_pct":       [0.07, 0.08, 0.10, 0.12],
        "trailing_stop_pct":   [0.15, 0.18, 0.20, 0.22, 0.25],
        "time_stop_days":      [15, 21, 25, 30],
        "rs_min_percentile":   [65, 70, 75, 80],
        "vcp_final_range_pct":[0.08, 0.10, 0.12, 0.15],
        "volume_mult":         [1.3, 1.5, 1.8, 2.0],
        "min_breakout_pct":    [0.003, 0.005, 0.008, 0.010],
    },
    "v_oneil": {
        "stop_loss_pct":       [0.05, 0.07, 0.08, 0.10],
        "trailing_stop_pct":   [0.15, 0.18, 0.20, 0.22],
        "time_stop_days":      [15, 21, 25, 30],
        "rs_min_percentile":   [75, 80, 85],
        "vcp_final_range_pct": [0.15, 0.20, 0.25],
        "volume_mult":         [1.5, 1.8, 2.0],
        "min_breakout_pct":    [0.003, 0.005, 0.008],
    },
    "v_eps_v2": {
        "stop_loss_pct":       [0.08, 0.10, 0.12, 0.15],
        "trailing_stop_pct":   [0.15, 0.18, 0.20, 0.22, 0.25],
        "time_stop_days":      [21, 30, 40, 60],
        "eps_quarters_required": [2, 3, 4],
    },
}

# 分批止盈（Partial Take Profit）配置
PTP_LEVELS: list[Any] = [
    None,  # 不使用分批止盈
    [{"pct": 0.10, "exit_pct": 0.30}, {"pct": 0.20, "exit_pct": 0.50}],
    [{"pct": 0.15, "exit_pct": 0.40}, {"pct": 0.25, "exit_pct": 0.60}],
    [{"pct": 0.08, "exit_pct": 0.25}, {"pct": 0.15, "exit_pct": 0.50}, {"pct": 0.25, "exit_pct": 0.75}],
]

# ────────────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────────────

def load_universe() -> list[str]:
    """
    从 UNIVERSE.md 提取所有美股 ticker 列表。

    返回：
        按字母排序的去重 ticker 列表（仅美股，1-5 个大写字母）。
    """
    universe_path = Path(PROJECT_ROOT) / "UNIVERSE.md"
    text = universe_path.read_text(encoding="utf-8")

    # 匹配表格行：| TICKER | ...（第一列是 ticker）
    pattern = re.compile(r"^\|\s*([A-Z]{1,5})\s*\|", re.MULTILINE)
    tickers: set[str] = set()
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            tickers.add(m.group(1))

    # 过滤明显非股票代码的词
    exclude = {"CODE", "TICKER", "股票", "公司", "简介", "备注", "信号", "强度", "止损"}
    tickers = {t for t in tickers if t not in exclude and len(t) <= 5}

    return sorted(tickers)


def load_config() -> dict:
    """加载 config.yaml 并返回完整配置字典。"""
    config_path = Path(PROJECT_ROOT) / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def random_config(strategy_id: str) -> dict:
    """
    从策略参数空间随机采样一组参数。

    参数：
        strategy_id: 策略 ID（如 "v1_plus"）

    返回：
        参数字典（可直接合并到 strategy_config）
    """
    ranges = PARAM_RANGES.get(strategy_id, {})
    config: dict[str, Any] = {}

    for param, values in ranges.items():
        config[param] = random.choice(values)

    # 随机决定是否加 PTP（仅 V1+ 和 O'Neil 支持）
    if strategy_id in ("v1_plus", "v_oneil"):
        if random.random() < 0.4:  # 40% 概率加 PTP
            config["partial_take_profit"] = random.choice(PTP_LEVELS[1:])  # 不选 None
        else:
            config["partial_take_profit"] = None

    return config


# ────────────────────────────────────────────────────────────────
# Worker 函数（模块顶层，可 pickle）
# ────────────────────────────────────────────────────────────────

def _run_trial_worker(
    trial_id: int,
    strategy_id: str,
    trial_params: dict,
    symbols: list[str],
    in_sample_start: datetime,
    in_sample_end: datetime,
    oos_start: datetime,
    oos_end: datetime,
    project_root: str,
) -> dict[str, Any]:
    """
    单次试验的 worker 函数（在子进程中执行）。

    返回：
        包含样本内/样本外指标的字典，异常时返回 sharpe=-999。
    """
    try:
        # 切换到项目根目录（子进程中需要重新设置）
        os.chdir(project_root)

        import yaml
        from backtest.engine import BacktestEngine
        from strategies.registry import STRATEGY_REGISTRY

        with open("config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        strategy_cls = STRATEGY_REGISTRY[strategy_id]
        base_config = config["strategies"].get(strategy_id, {}).copy()

        # 合并随机采样的参数
        for k, v in trial_params.items():
            base_config[k] = v

        # ── 样本内回测 ──────────────────────────────────────────
        engine_is = BacktestEngine(
            config=config,
            strategy_cls=strategy_cls,
            strategy_config=base_config,
            symbols=symbols,
            start_date=in_sample_start,
            end_date=in_sample_end,
            save_signals_csv=False,
            strategy_id=strategy_id,
            position_size=1500,
            initial_capital=50_000.0,
        )
        result_is = engine_is.run(verbose=False)

        # 过滤无效结果
        if (
            result_is.sharpe_ratio == 0
            or math.isnan(result_is.sharpe_ratio)
            or result_is.total_trades < 5
        ):
            return _make_failed_result(trial_id, trial_params)

        # ── 样本外回测 ──────────────────────────────────────────
        engine_oos = BacktestEngine(
            config=config,
            strategy_cls=strategy_cls,
            strategy_config=base_config,
            symbols=symbols,
            start_date=oos_start,
            end_date=oos_end,
            save_signals_csv=False,
            strategy_id=strategy_id,
            position_size=1500,
            initial_capital=50_000.0,
        )
        result_oos = engine_oos.run(verbose=False)

        if (
            result_oos.sharpe_ratio == 0
            or math.isnan(result_oos.sharpe_ratio)
        ):
            return _make_failed_result(trial_id, trial_params)

        return {
            "trial_id": trial_id,
            "params": trial_params,
            "in_sample_sharpe": result_is.sharpe_ratio,
            "in_sample_annualized_return": result_is.annualized_return,
            "in_sample_win_rate": result_is.win_rate,
            "in_sample_plr": result_is.profit_loss_ratio,
            "in_sample_max_dd": result_is.max_drawdown,
            "in_sample_signals_per_month": result_is.signals_per_month,
            "in_sample_total_trades": result_is.total_trades,
            "oos_sharpe": result_oos.sharpe_ratio,
            "oos_annualized_return": result_oos.annualized_return,
            "oos_win_rate": result_oos.win_rate,
            "oos_plr": result_oos.profit_loss_ratio,
            "oos_max_dd": result_oos.max_drawdown,
            "oos_signals_per_month": result_oos.signals_per_month,
            "oos_total_trades": result_oos.total_trades,
            "success": True,
        }

    except Exception as e:
        # 任何异常都记录为失败，不崩掉整个优化
        return _make_failed_result(trial_id, trial_params, error=str(e))


def _make_failed_result(
    trial_id: int,
    params: dict,
    error: str = "",
) -> dict[str, Any]:
    """构造失败结果的哨兵值。"""
    return {
        "trial_id": trial_id,
        "params": params,
        "in_sample_sharpe": -999.0,
        "in_sample_annualized_return": 0.0,
        "in_sample_win_rate": 0.0,
        "in_sample_plr": 0.0,
        "in_sample_max_dd": 0.0,
        "in_sample_signals_per_month": 0.0,
        "in_sample_total_trades": 0,
        "oos_sharpe": -999.0,
        "oos_annualized_return": 0.0,
        "oos_win_rate": 0.0,
        "oos_plr": 0.0,
        "oos_max_dd": 0.0,
        "oos_signals_per_month": 0.0,
        "oos_total_trades": 0,
        "success": False,
        "error": error,
    }


# ────────────────────────────────────────────────────────────────
# 主优化函数
# ────────────────────────────────────────────────────────────────

def run_trial(
    strategy_id: str,
    config_dict: dict,
    symbols: list[str],
    start_date: datetime,
    end_date: datetime,
) -> dict[str, Any]:
    """
    运行一次回测试验，返回指标字典。

    参数：
        strategy_id: 策略 ID
        config_dict: 参数字典（直接合并到 strategy_config）
        symbols: 股票列表
        start_date: 回测开始日期
        end_date: 回测结束日期

    返回：
        {
            "sharpe": float,
            "annualized_return": float,
            "win_rate": float,
            "profit_loss_ratio": float,
            "max_drawdown": float,
            "signals_per_month": float,
            "total_trades": int,
            "params": {...}
        }
    """
    import yaml
    from backtest.engine import BacktestEngine
    from strategies.registry import STRATEGY_REGISTRY

    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    strategy_cls = STRATEGY_REGISTRY[strategy_id]
    base_config = config["strategies"].get(strategy_id, {}).copy()

    for k, v in config_dict.items():
        base_config[k] = v

    engine = BacktestEngine(
        config=config,
        strategy_cls=strategy_cls,
        strategy_config=base_config,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        save_signals_csv=False,
        strategy_id=strategy_id,
        position_size=1500,
        initial_capital=50_000.0,
    )
    result = engine.run(verbose=False)

    if (
        result.sharpe_ratio == 0
        or math.isnan(result.sharpe_ratio)
        or result.total_trades < 3
    ):
        raise ValueError(f"Trial returned invalid result: sharpe={result.sharpe_ratio}, trades={result.total_trades}")

    return {
        "sharpe": result.sharpe_ratio,
        "annualized_return": result.annualized_return,
        "win_rate": result.win_rate,
        "profit_loss_ratio": result.profit_loss_ratio,
        "max_drawdown": result.max_drawdown,
        "signals_per_month": result.signals_per_month,
        "total_trades": result.total_trades,
        "params": config_dict,
    }


def optimize(
    strategy_id: str,
    n_trials: int,
    in_sample_start: datetime,
    in_sample_end: datetime,
    oos_start: datetime,
    oos_end: datetime,
    n_workers: int | None = None,
    output_dir: str = "output/optimization",
) -> dict[str, Any]:
    """
    主优化函数：随机搜索 + 样本外验证。

    流程：
      1. 在样本内运行 n_trials 次随机参数搜索
      2. 选取样本内夏普前 20 的参数组合
      3. 在样本外验证这 20 个
      4. 返回样本外夏普最高的参数组合（champion）

    参数：
        strategy_id: 策略 ID（如 "v1_plus"）
        n_trials: 总试验次数
        in_sample_start: 样本内开始日期
        in_sample_end: 样本内结束日期
        oos_start: 样本外开始日期
        oos_end: 样本外结束日期
        n_workers: 并行进程数（默认=CPU核心数）
        output_dir: 结果 CSV 保存目录

    返回：
        champion 参数字典（可直接用于 BacktestEngine）
    """
    if strategy_id not in PARAM_RANGES:
        raise ValueError(
            f"未知策略 '{strategy_id}'。"
            f"支持的策略：{list(PARAM_RANGES.keys())}"
        )

    # 加载股票池
    symbols = load_universe()
    print(f"  加载股票池：{len(symbols)} 只")

    # 确保输出目录存在
    output_path = Path(PROJECT_ROOT) / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # ── 阶段 1：样本内随机搜索（顺序执行，避免 OOM）────────────
    print(f"\n  【阶段 1】样本内随机搜索：{n_trials} 次试验")
    print(f"  区间：{in_sample_start.date()} ~ {in_sample_end.date()}")

    # 打开 CSV 文件，先写表头
    csv_path = output_path / f"{strategy_id}_trials.csv"
    _write_csv_header(csv_path)

    all_results: list[dict[str, Any]] = []
    trial_counter = 0

    for trial_id in range(n_trials):
        params = random_config(strategy_id)
        result = _run_trial_worker(
            trial_id,
            strategy_id,
            params,
            symbols,
            in_sample_start,
            in_sample_end,
            oos_start,
            oos_end,
            PROJECT_ROOT,
        )
        all_results.append(result)
        trial_counter += 1

        # 每次试验完成立即追加写入 CSV
        _append_trial_csv(result, csv_path)

        # 打印进度（sample in 的 sharpe 作为参考）
        is_sharpe = result.get("in_sample_sharpe", -999)
        status = "✅" if is_sharpe > -100 else "❌"
        pct = min(100, int(trial_counter / n_trials * 100))
        print(f"    [{status}] {trial_counter}/{n_trials} ({pct}%) | IS Sharpe: {is_sharpe:.2f}")

    # 过滤失败试验
    valid_is = [r for r in all_results if r["in_sample_sharpe"] > -100]
    print(f"\n  有效试验：{len(valid_is)} / {n_trials}")

    if len(valid_is) < 5:
        raise RuntimeError(f"有效试验太少（{len(valid_is)}），无法继续优化。")

    # ── 阶段 2：取样本内前 20 ─────────────────────────────────
    top20 = sorted(valid_is, key=lambda x: x["in_sample_sharpe"], reverse=True)[:20]
    print(f"\n  【阶段 2】样本外验证：Top {len(top20)} 参数组合")
    print(f"  区间：{oos_start.date()} ~ {oos_end.date()}")

    # ── 阶段 3：样本外验证（已在 _run_trial_worker 中完成）───

    # ── 阶段 4：找 champion ─────────────────────────────────────
    valid_oos = [r for r in top20 if r["oos_sharpe"] > -100]
    if not valid_oos:
        raise RuntimeError("所有 Top20 参数在样本外均失败。")

    champion = max(valid_oos, key=lambda x: x["oos_sharpe"])

    # ── 保存全部结果到 CSV（已在每 trial 后实时写入）──────────

    # ── 打印 champion ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  CHAMPION 配置（样本外夏普：{champion['oos_sharpe']:.2f}）")
    print("=" * 60)
    for k, v in champion["params"].items():
        print(f"    {k:<30} {v}")
    print()
    print(f"  样本内夏普：{champion['in_sample_sharpe']:.2f}  |  "
          f"样本外夏普：{champion['oos_sharpe']:.2f}")
    print(f"  样本内年化：{champion['in_sample_annualized_return']*100:.1f}%  |  "
          f"样本外年化：{champion['oos_annualized_return']*100:.1f}%")
    print(f"  样本内胜率：{champion['in_sample_win_rate']*100:.1f}%  |  "
          f"样本外胜率：{champion['oos_win_rate']*100:.1f}%")
    print(f"  样本内盈亏比：{champion['in_sample_plr']:.2f}  |  "
          f"样本外盈亏比：{champion['oos_plr']:.2f}")
    print(f"  样本内最大回撤：{champion['in_sample_max_dd']*100:.1f}%  |  "
          f"样本外最大回撤：{champion['oos_max_dd']*100:.1f}%")
    print(f"  样本内信号/月：{champion['in_sample_signals_per_month']:.1f}  |  "
          f"样本外信号/月：{champion['oos_signals_per_month']:.1f}")
    print("=" * 60)

    return champion["params"]


def _write_csv_header(path: Path) -> None:
    """写入 CSV 表头（仅调用一次）"""
    header = (
        "trial_id,params_json,in_sample_sharpe,in_sample_annualized_return,"
        "in_sample_win_rate,in_sample_plr,in_sample_max_dd,"
        "in_sample_signals_per_month,in_sample_total_trades,"
        "oos_sharpe,oos_annualized_return,oos_win_rate,oos_plr,"
        "oos_max_dd,oos_signals_per_month,oos_total_trades,success,error\n"
    )
    path.write_text(header, encoding="utf-8")


def _append_trial_csv(result: dict[str, Any], path: Path) -> None:
    """追加单条试验结果到 CSV 文件"""
    row = (
        f"{result['trial_id']},"
        f"{json.dumps(result['params'], ensure_ascii=False)},"
        f"{result['in_sample_sharpe']},"
        f"{result['in_sample_annualized_return']},"
        f"{result['in_sample_win_rate']},"
        f"{result['in_sample_plr']},"
        f"{result['in_sample_max_dd']},"
        f"{result['in_sample_signals_per_month']},"
        f"{result['in_sample_total_trades']},"
        f"{result['oos_sharpe']},"
        f"{result['oos_annualized_return']},"
        f"{result['oos_win_rate']},"
        f"{result['oos_plr']},"
        f"{result['oos_max_dd']},"
        f"{result['oos_signals_per_month']},"
        f"{result['oos_total_trades']},"
        f"{result['success']},"
        f"{result.get('error', '')}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(row)


def _save_trials_csv(results: list[dict[str, Any]], path: Path) -> None:
    """将试验结果列表保存为 CSV。"""
    rows = []
    for r in results:
        rows.append({
            "trial_id": r["trial_id"],
            "params_json": json.dumps(r["params"], ensure_ascii=False),
            "in_sample_sharpe": r["in_sample_sharpe"],
            "in_sample_annualized_return": r["in_sample_annualized_return"],
            "in_sample_win_rate": r["in_sample_win_rate"],
            "in_sample_plr": r["in_sample_plr"],
            "in_sample_max_dd": r["in_sample_max_dd"],
            "in_sample_signals_per_month": r["in_sample_signals_per_month"],
            "in_sample_total_trades": r["in_sample_total_trades"],
            "oos_sharpe": r["oos_sharpe"],
            "oos_annualized_return": r["oos_annualized_return"],
            "oos_win_rate": r["oos_win_rate"],
            "oos_plr": r["oos_plr"],
            "oos_max_dd": r["oos_max_dd"],
            "oos_signals_per_month": r["oos_signals_per_month"],
            "oos_total_trades": r["oos_total_trades"],
            "success": r["success"],
        })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8")


# ────────────────────────────────────────────────────────────────
# 测试入口
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timezone

    print("\n" + "#" * 60)
    print("# 参数优化引擎测试（5 trials）")
    print("#" * 60)

    # 样本内：2020-01-01 ~ 2022-12-31（牛市+震荡）
    # 样本外：2024-01-01 ~ 2026-03-27（当前）
    in_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    in_end   = datetime(2022, 12, 31, tzinfo=timezone.utc)
    oos_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    oos_end   = datetime(2026, 3, 27, tzinfo=timezone.utc)

    # 先运行 5 次快速试验（单进程，用于验证代码正确性）
    print("\n运行 5 次快速试验（单进程模式）...")

    symbols = load_universe()
    print(f"股票池加载完成：{len(symbols)} 只\n")

    for i in range(5):
        trial_id = i + 1
        params = random_config("v1_plus")
        print(f"\n--- Trial {trial_id}/{5} ---")
        print(f"参数：{params}")

        try:
            result = run_trial(
                strategy_id="v1_plus",
                config_dict=params,
                symbols=symbols,
                start_date=in_start,
                end_date=in_end,
            )
            print(f"  夏普：{result['sharpe']:.2f}  |  "
                  f"年化：{result['annualized_return']*100:.1f}%  |  "
                  f"胜率：{result['win_rate']*100:.1f}%  |  "
                  f"盈亏比：{result['profit_loss_ratio']:.2f}  |  "
                  f"最大回撤：{result['max_drawdown']*100:.1f}%  |  "
                  f"信号/月：{result['signals_per_month']:.1f}  |  "
                  f"交易数：{result['total_trades']}")
        except Exception as e:
            print(f"  试验失败：{e}")

    print("\n\n所有试验完成。")
