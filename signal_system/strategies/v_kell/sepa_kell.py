"""
strategies/v_kell/sepa_kell.py — Kell VCP 2.0

继承 SEPAStrategy 全部逻辑，参数通过 config.yaml 的 strategies.v_kell 段传入。
核心差异：放量 3x，突破≥1.5%，RS≥80，止损 8%。
注：无 EPS≥50% 基本面筛选（缺乏数据源）。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy


class KellStrategy(SEPAStrategy):
    strategy_id = "v_kell"
    strategy_name = "Kell VCP 2.0"
