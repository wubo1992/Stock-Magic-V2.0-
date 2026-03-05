"""
strategies/v1_plus/sepa_plus.py — 魔法师调整参数版V1+

继承 V1 所有策略逻辑，仅修改注册 ID 和名称。
参数通过 config.yaml 的 strategies.v1_plus 段传入，用于参数调优实验。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy


class SEPAPlusStrategy(SEPAStrategy):
    strategy_id = "v1_plus_wizard"
    strategy_name = "魔法师调整参数版V1+"
