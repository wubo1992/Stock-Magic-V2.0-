"""
strategies/v_eps_v1_plus/eps_v1_plus_strategy.py — EPS V1 Plus 策略

继承 SEPAPlusStrategy（v1_plus 调整参数框架），添加 EPS 基本面过滤：

筛选顺序：
  1. SEPAPlusStrategy._check_entry（SEPA + VCP 技术分析）
  2. EPS 增长检查（基本面过滤）

对应 config.yaml 的 strategies.v_eps_v1_plus 段。
"""

from events import SignalEvent
from strategies.v1_plus.sepa_plus import SEPAPlusStrategy
from data.fundamentals import check_eps_filter


class EPSV1PlusStrategy(SEPAPlusStrategy):
    """EPS V1 Plus 策略：v1_plus 技术框架 + EPS 基本面过滤"""

    strategy_id = "v_eps_v1_plus"
    strategy_name = "EPS V1 Plus"

    def _check_entry(self, symbol, df, date):
        # 1. 执行 SEPAPlusStrategy 技术分析（继承自 V1 的完整 SEPA + VCP 检查）
        signal_or_none = super()._check_entry(symbol, df, date)
        if signal_or_none is None:
            return None

        signal = signal_or_none

        # 2. 技术条件通过后，检查 EPS 增长（基本面过滤）
        eps_quarters = self.cfg.get("eps_quarters_required", 3)
        eps_yoy = self.cfg.get("eps_yoy_required", True)
        eps_qoq = self.cfg.get("eps_qoq_required", True)

        eps_passed, eps_reason = check_eps_filter(
            symbol,
            quarters=eps_quarters,
            require_yoy=eps_yoy,
            require_qoq=eps_qoq
        )

        if not eps_passed:
            return None

        # 3. 全部通过，组装增强信号
        close = float(df["close"].iloc[-1])
        stop_loss = round(close * (1 - self.stop_loss_pct), 2)
        sep_reason = signal.data.get("reason", "")

        reason = (
            f"[EPS] {eps_reason} | "
            f"{sep_reason}"
        )

        enhanced_signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=signal.data["strength"], reason=reason, stop_loss=stop_loss,
        )
        return enhanced_signal
