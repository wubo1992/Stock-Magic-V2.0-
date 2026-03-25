"""
strategies/v_eps/eps_strategy.py — EPS 基本面因子策略

继承 SEPAStrategy（复用技术分析逻辑、出场逻辑、持仓追踪），
在 _check_entry 中添加 EPS 增长筛选条件：

筛选顺序：
  1. EPS 增长检查（新增基本面过滤）
  2. 趋势模板检查（8条件）
  3. 相对强度 RS 排名
  4. VCP 形态识别
  5. 枢轴点突破
  6. 量能确认

EPS 条件：
  - 过去 N 个季度 EPS 数据
  - 同比（YoY）增长：当前季度 > 去年同期
  - 环比（QoQ）增长：连续季度递增

对应 config.yaml 的 strategies.v_eps 段。
"""

from events import SignalEvent
from strategies.v1_wizard.sepa_minervini import Position, SEPAStrategy
from data.fundamentals import check_eps_filter


class EPSStrategy(SEPAStrategy):
    """EPS 基本面因子策略"""

    strategy_id = "v_eps"
    strategy_name = "EPS 基本面策略"

    def _check_entry(self, symbol, df, date):
        # 1. 首先执行技术分析（SEPA 条件）
        # 先做技术筛选，可以过滤掉大部分股票，减少 EPS API 调用
        template_ok, template_msg = self._check_trend_template(df)
        if not template_ok:
            return None
        rs_ok, rs_value = self._check_rs(symbol, df, date)
        if not rs_ok:
            return None
        vcp_ok, vcp_msg = self._check_vcp(df)
        if not vcp_ok:
            return None
        breakout_ok, breakout_pct, pivot_price = self._check_breakout(df)
        if not breakout_ok:
            return None
        vol_ok, vol_ratio = self._check_volume(df)
        if not vol_ok:
            return None

        # 2. 技术条件全部通过后，检查 EPS 增长（基本面过滤）
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
            # EPS 筛选未通过，返回 None（不产生信号）
            return None

        # 3. 全部通过，计算信号强度
        strength = self._score_signal(breakout_pct, vol_ratio, rs_value)
        close = float(df["close"].iloc[-1])
        stop_loss = round(close * (1 - self.stop_loss_pct), 2)

        # 组装触发原因（包含 EPS 信息）
        reason = (
            f"[EPS] {eps_reason} | "
            f"[趋势] {template_msg} | "
            f"[RS] 相对强度排名{rs_value:.0f}% | "
            f"[VCP] {vcp_msg} | "
            f"[突破] 超过{self.pivot_lookback}日高点${pivot_price:.2f}，幅度+{breakout_pct*100:.1f}% | "
            f"[量能] 成交量{vol_ratio:.1f}倍均量"
        )

        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )

        # 自动建立持仓记录
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=close,
                entry_date=date,
                highest_price=close,
            )

        return signal
