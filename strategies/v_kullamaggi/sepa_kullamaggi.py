"""
strategies/v_kullamaggi/sepa_kullamaggi.py — Kullamägi VCP 变种

继承 SEPAStrategy 全部逻辑，参数通过 config.yaml 的 strategies.v_kullamaggi 段传入。
核心差异：止损 5%（最紧），放量 4x（极端），追踪止损 12%，时间止损 15 天。
注：Episodic Pivot 入场未实现（需要财报超预期数据，缺乏数据源）。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy


class KullamaggiStrategy(SEPAStrategy):
    strategy_id = "v_kullamaggi"
    strategy_name = "Kullamägi VCP 变种"
