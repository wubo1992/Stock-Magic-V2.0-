"""
run_optimization.py — 并行启动三个策略的参数优化

用法：
    uv run python run_optimization.py

优化三个策略（v1_plus, v_oneil, v_eps_v2），每个 200 次试验。
顺序执行，总耗时约 6-12 小时。
"""

import sys
sys.path.insert(0, ".")

from datetime import datetime, timezone
from pathlib import Path

from backtest.optimizer import optimize

PROJECT_ROOT = "/Users/wubo/Desktop/信号系统克劳德V3.1_Minimax支线/signal_system"

# 样本内：2020-01-01 ~ 2022-12-31
# 样本外：2024-01-01 ~ 2026-03-27
IN_START  = datetime(2020, 1, 1, tzinfo=timezone.utc)
IN_END    = datetime(2022, 12, 31, tzinfo=timezone.utc)
OOS_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
OOS_END   = datetime(2026, 3, 27, tzinfo=timezone.utc)

N_TRIALS = 200

STRATEGIES = ["v1_plus", "v_oneil", "v_eps_v2"]


def main():
    results = {}
    for sid in STRATEGIES:
        print(f"\n{'#' * 70}")
        print(f"# 策略：{sid}  |  试验次数：{N_TRIALS}  |  顺序执行")
        print(f"#{'#' * 70}")

        champion = optimize(
            strategy_id=sid,
            n_trials=N_TRIALS,
            in_sample_start=IN_START,
            in_sample_end=IN_END,
            oos_start=OOS_START,
            oos_end=OOS_END,
            output_dir="output/optimization",
        )
        results[sid] = champion
        print(f"\n✅ {sid} 优化完成")

    # ── 最终汇总 ────────────────────────────────────────────────
    print(f"\n\n{'=' * 70}")
    print("  三个策略优化完成 — 最终推荐")
    print(f"{'=' * 70}")

    for sid, cfg in results.items():
        print(f"\n  【{sid}】")
        for k, v in cfg.items():
            print(f"    {k:<30} {v}")

    print(f"\n{'=' * 70}")
    print("  全部完成！")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
