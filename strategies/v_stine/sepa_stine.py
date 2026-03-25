"""
strategies/v_stine/sepa_stine.py — Stine 超强精选（无内部人数据版）

继承 SEPAStrategy 全部逻辑，参数通过 config.yaml 的 strategies.v_stine 段传入。
核心差异：RS≥90（Top 10%），极紧 VCP（5%），放量 3x，止损 8%。
注：内部人士买入（SEC Form 4）条件缺失，缺少此核心过滤器，信号质量低于原策略。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy


class StineStrategy(SEPAStrategy):
    strategy_id = "v_stine"
    strategy_name = "Stine 超强精选（无内部人数据版）"
