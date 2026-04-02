"""
strategies/registry.py — 策略注册表

添加新策略步骤：
    1. 在 strategies/ 下新建包：strategies/vN_xxx/
    2. 在包内实现继承 StrategyBase 的策略类
    3. 在下方 STRATEGY_REGISTRY 中添加一行：
           "vN": MyNewStrategy,
    4. 在 config.yaml 的 strategies: 下添加对应配置段

仅此而已，不需要改 main.py 或其他任何框架代码。
"""

from strategies.v1_wizard.sepa_minervini import SEPAStrategy
from strategies.v1_plus.sepa_plus import SEPAPlusStrategy
from strategies.v_oneil.sepa_oneil import ONeilStrategy
from strategies.v_ryan.sepa_ryan import RyanStrategy
from strategies.v_kell.sepa_kell import KellStrategy
from strategies.v_kullamaggi.sepa_kullamaggi import KullamaggiStrategy
from strategies.v_zanger.zanger_strategy import ZangerStrategy
from strategies.v_stine.sepa_stine import StineStrategy
from strategies.v_weinstein.weinstein_strategy import WeinsteinStrategy
from strategies.v_golden_cross.golden_cross_strategy import GoldenCrossStrategy

# key   = --strategy 参数的值（如 --strategy v1）
# value = 策略类（继承 StrategyBase）
STRATEGY_REGISTRY: dict[str, type] = {
    "v1": SEPAStrategy,
    "v1_plus": SEPAPlusStrategy,
    "v_oneil": ONeilStrategy,
    "v_ryan": RyanStrategy,
    "v_kell": KellStrategy,
    "v_kullamaggi": KullamaggiStrategy,
    "v_zanger": ZangerStrategy,
    "v_stine": StineStrategy,
    "v_weinstein": WeinsteinStrategy,
    "v_golden_cross": GoldenCrossStrategy,
}


def get_strategy(strategy_id: str) -> type:
    """
    根据 strategy_id 返回对应策略类。

    参数：
        strategy_id: 如 "v1"

    返回：
        策略类（未实例化）

    异常：
        ValueError: strategy_id 不在注册表中
    """
    if strategy_id not in STRATEGY_REGISTRY:
        available = list(STRATEGY_REGISTRY.keys())
        raise ValueError(
            f"未知策略 '{strategy_id}'。"
            f"可用策略：{available}。"
            f"请在 strategies/registry.py 的 STRATEGY_REGISTRY 中注册新策略。"
        )
    return STRATEGY_REGISTRY[strategy_id]


def list_strategies() -> list[dict]:
    """返回所有已注册策略的信息列表。"""
    result = []
    for sid, cls in STRATEGY_REGISTRY.items():
        result.append({
            "id": sid,
            "strategy_id": cls.strategy_id,
            "name": cls.strategy_name,
        })
    return result
