"""
strategies/v_ryan/sepa_ryan.py — Ryan 精简 CANSLIM

继承 SEPAStrategy 全部逻辑，参数通过 config.yaml 的 strategies.v_ryan 段传入。
核心差异：极紧 VCP（5%），RS≥80，止损 8%，追踪止损 15%。
注：无小市值过滤（缺少市值数据）。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy


class RyanStrategy(SEPAStrategy):
    strategy_id = "v_ryan"
    strategy_name = "Ryan 精简 CANSLIM"
