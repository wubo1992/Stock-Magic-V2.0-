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
from data.rs_10w import compute_rs_10w
from data.rs_10d import compute_rs_10d


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

        # 父类 reason 中已有标准化的 [量比] X.X倍均量 块，用正则提取
        # 修复前：原代码用 split('[')[-1].split(']')[0] 错切最后一个标签，常输出"止损/RS"等错误值
        import re
        vol_match = re.search(r"\[量比\]\s*([\d.]+)倍均量", Weinstein_reason)
        if vol_match:
            vol_ratio_str = f"{vol_match.group(1)}倍均量"
        else:
            # 兜底：父类 reason 不含 [量比] 时的回退表达
            vol_ratio_str = "达标"

        rs_10w = compute_rs_10w(symbol, self.market_data, date)
        rs_10w_str = f"{rs_10w:.2f}x" if rs_10w is not None else "—"
        rs_10d = compute_rs_10d(symbol, self.market_data, date)
        rs_10d_str = f"{rs_10d:.2f}x" if rs_10d is not None else "—"

        reason = (
            f"[EPS] {eps_reason} | "
            f"[Stage2] SMA{self.sma_long}上升{self.trend_lookback}天 | "
            f"[量比] {vol_ratio_str} | "
            f"[RS10D] {rs_10d_str} | "
            f"[RS10W] {rs_10w_str}"
        )

        return SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=signal.data["strength"], reason=reason, stop_loss=stop_loss,
        )
