"""
strategies/v_oneil/sepa_oneil.py — O'Neil CANSLIM 技术版

继承 SEPAStrategy 全部逻辑，参数通过 config.yaml 的 strategies.v_oneil 段传入。
核心差异：宽松 VCP（20%），RS≥80，止损 7%。
注：无 EPS/ROE 基本面筛选（缺乏数据源）。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy


class ONeilStrategy(SEPAStrategy):
    strategy_id = "v_oneil"
    strategy_name = "O'Neil CANSLIM 技术版"
