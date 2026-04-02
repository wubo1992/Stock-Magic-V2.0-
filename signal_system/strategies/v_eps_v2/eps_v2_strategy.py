"""
strategies/v_eps_v2/eps_v2_strategy.py — Weinstein Stage 2 + EPS 基本面过滤

继承 WeinsteinStrategy（复用 Stage 2 技术分析框架），
在 _check_entry 中添加 EPS 增长筛选条件：

筛选顺序：
  1. Weinstein Stage 2 技术条件（SMA150 上升 + 突破整理区 + 放量）
  2. EPS 增长检查（基本面过滤）
     - 无 EPS 数据（Finnhub/Alpha Vantage 均无）→ 跳过，不出信号
     - 有 EPS 数据 → 正常筛选

对应 config.yaml 的 strategies.v_eps_v2 段。
"""

from events import SignalEvent
from strategies.v_weinstein.weinstein_strategy import WeinsteinStrategy
from data.fundamentals import check_eps_filter


class EPSV2Strategy(WeinsteinStrategy):
    """Weinstein Stage 2 + EPS 基本面策略"""

    strategy_id = "v_eps_v2"
    strategy_name = "Weinstein + EPS"

    def _check_entry(self, symbol, df, date):
        # 1. 执行 Weinstein Stage 2 技术分析
        signal_or_none = super()._check_entry(symbol, df, date)
        if signal_or_none is None:
            return None

        signal = signal_or_none

        # 2. Weinstein 技术条件通过后，检查 EPS 增长
        # check_eps_filter 内部会尝试从缓存/Finnhub/Alpha Vantage 获取数据
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
            # EPS 抓不到或筛选未通过，跳过
            return None

        # 3. 全部通过，组装信号
        close = float(df["close"].iloc[-1])
        stop_loss = round(close * (1 - self.stop_loss_pct), 2)
        Weinstein_reason = signal.data.get("reason", "")

        reason = (
            f"[EPS] {eps_reason} | "
            f"[Stage2] SMA{self.sma_long}上升{self.trend_lookback}天 | "
            f"[量能] {Weinstein_reason.split('[')[-1].split(']')[0] if '[' in Weinstein_reason else '达标'}"
        )

        return SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=signal.data["strength"], reason=reason, stop_loss=stop_loss,
        )
