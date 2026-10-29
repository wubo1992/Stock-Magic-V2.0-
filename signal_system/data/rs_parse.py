"""
data/rs_parse.py — 从信号「触发原因」字符串中提取 RS 相对强度百分位

为什么需要这个模块：
- 各策略都把 RS 写进「触发原因」，但格式有三种：
    v1_wizard/v1_plus_wizard/v_eps/v_eps_v1_plus: "[RS] 相对强度排名79%"
    v_adx50:                                        "[RS] 排名92%"
    v_weinstein:                                    "[RS] RS=85"  或  "[RS] Top 12%"
- 报告层要单独展示 RS，必须从这段文本里解析出来
- 多个报告模块都要用，抽成公共函数避免重复正则
"""

import re

# 按优先级尝试；第一种覆盖项目里绝大多数策略
_PATTERNS = (
    re.compile(r"\[RS\]\s*(?:相对强度排名|排名|Top|RS\s*=)\s*(\d+)"),
    re.compile(r"\[RS\]\s*(\d+)"),
)


def extract_rs_percentile(reason: str) -> int | None:
    """
    从「触发原因」中提取 RS 百分位（0-100）。

    返回 int，无 RS 字段时返回 None（调用方显示 "—"）。
    """
    if not reason:
        return None
    for pattern in _PATTERNS:
        m = pattern.search(reason)
        if m:
            return int(m.group(1))
    return None


def resolve_rs_percentile(
    reason: str,
    symbol: str,
    rs_relative: dict[str, float] | None = None,
) -> int | None:
    """
    取「策略内部口径」的 RS 百分位，两级来源：

    1. 优先用策略自己算出来的值（从「触发原因」里解析）——
       那是策略在**自己的**股票池里跑出来的，最贴近该策略的判断。
    2. 策略没算 RS（例如 v_zanger 不做 RS 检查）时，退回
       data/rs_relative.py 对固定股票池算出的统一值。

    两级用的是同一套公式（0.4×252日 + 0.3×126日 + 0.3×60日，对标基准 ETF），
    只是排名分母可能略有不同，所以数值接近、不冲突。

    为什么不干脆只用第 2 级：策略自算值能反映该策略实际用的股票池；
    为什么不干脆只用第 1 级：v_zanger 这类策略根本不写 RS，报告里整列都是「—」，
    用户看不出是「没数据」还是「格式没认出来」。
    """
    parsed = extract_rs_percentile(reason)
    if parsed is not None:
        return parsed
    if rs_relative:
        val = rs_relative.get(symbol)
        if val is not None:
            return int(round(val))
    return None