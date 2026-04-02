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
from strategies.v_zanger.zanger_strategy import ZangerStrategy
from strategies.v_weinstein.weinstein_strategy import WeinsteinStrategy
from strategies.v_weinstein_adx.weinstein_adx_strategy import WeinsteinADXStrategy
from strategies.v_weinstein_adx.weinstein_adx_bullbear import WeinsteinADXBullBearStrategy
from strategies.v_eps.eps_strategy import EPSStrategy
from strategies.v_eps_v2.eps_v2_strategy import EPSV2Strategy
from strategies.v_eps_v1_plus.eps_v1_plus_strategy import EPSV1PlusStrategy
from strategies.v_adx50.adx50_strategy import ADX50Strategy
from strategies.v_weinstein_market_filter_strict.weinstein_mf_strict_strategy import WeinsteinMFStrictStrategy

# key   = --strategy 参数的值（如 --strategy v1）
# value = 策略类（继承 StrategyBase）
STRATEGY_REGISTRY: dict[str, type] = {
    "v1": SEPAStrategy,
    "v1_plus": SEPAPlusStrategy,
    "v_zanger": ZangerStrategy,
    "v_weinstein": WeinsteinStrategy,
    "v_weinstein_adx": WeinsteinADXStrategy,
    "v_weinstein_bullbear": WeinsteinADXBullBearStrategy,
    "v_eps": EPSStrategy,
    "v_eps_v2": EPSV2Strategy,
    "v_eps_v1_plus": EPSV1PlusStrategy,
    "v_adx50": ADX50Strategy,
    "v_weinstein_mf_strict": WeinsteinMFStrictStrategy,
}

# 策略分类映射：CLI key -> 类别
STRATEGY_CATEGORIES: dict[str, str] = {
    # 大师趋势
    "v1": "大师趋势",
    "v1_plus": "大师趋势",
    "v_zanger": "大师趋势",
    "v_weinstein": "大师趋势",
    "v_weinstein_adx": "大师趋势",
    "v_weinstein_bullbear": "大师趋势",
    # 结合EPS
    "v_eps": "结合EPS",
    "v_eps_v2": "结合EPS",
    "v_eps_v1_plus": "结合EPS",
    # 动量类
    "v_adx50": "动量类",
    # Weinstein 分支
    "v_weinstein_mf_strict": "大师改良",
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
            "category": STRATEGY_CATEGORIES.get(sid, "未分类"),
        })
    return result
