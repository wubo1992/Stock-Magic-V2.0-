"""
strategies/v_weinstein/weinstein_strategy.py — Weinstein Stage 2 阶段分析

继承 SEPAStrategy（复用出场逻辑、持仓追踪、工具方法），
只覆盖 _check_entry，实现 Weinstein Stage 2 入场（无 RS 过滤，无 VCP）：
  1. SMA150（≈30 周均线）本身在上升至少 trend_lookback 天（Stage 2 确认）
  2. 今日收盘价 > SMA150（价格在均线上方）
  3. 今日突破过去 N 日整理区高点
  4. 成交量 ≥ 1.5 倍 20 日均量（放量确认）

对应 config.yaml 的 strategies.v_weinstein 段。
"""

from events import SignalEvent
from strategies.v1_wizard.sepa_minervini import Position, SEPAStrategy


class WeinsteinStrategy(SEPAStrategy):
    strategy_id = "v_weinstein"
    strategy_name = "Weinstein Stage 2 分析"

    def _check_entry(self, symbol, df, date):
        # 数据不足时跳过（sma_long 150 + trend_lookback 30 = 180 行以上）
        need = self.sma_long + self.trend_lookback
        if len(df) < need:
            return None

        close_series = df["close"]
        current = float(close_series.iloc[-1])

        # 1. 计算 SMA150（≈30 周均线）
        sma150 = close_series.rolling(self.sma_long).mean()
        sma_now = float(sma150.iloc[-1])
        sma_past = float(sma150.iloc[-self.trend_lookback])

        # Stage 2 确认：SMA150 当前值 > trend_lookback 天前的值
        if sma_now <= sma_past:
            return None

        # 2. 价格必须在 SMA150 之上
        if current <= sma_now:
            return None

        # 3. 突破近期整理区最高价（排除今天）
        pivot = float(close_series.iloc[-(self.pivot_lookback + 1):-1].max())
        if current <= pivot * (1 + self.min_breakout_pct):
            return None

        # 4. 放量确认（成交量 >= volume_mult × 20 日均量）
        avg_vol = float(df["volume"].iloc[-21:-1].mean())
        if avg_vol == 0:
            return None
        vol_ratio = float(df["volume"].iloc[-1]) / avg_vol
        if vol_ratio < self.volume_mult:
            return None

        breakout_pct = (current - pivot) / pivot
        strength = 3  # Weinstein 策略默认 3 星（纯趋势跟随，无 RS/VCP 加分）
        stop_loss = round(current * (1 - self.stop_loss_pct), 2)
        reason = (
            f"[Stage2] SMA{self.sma_long}({sma_now:.0f})上升{self.trend_lookback}天 | "
            f"[突破] 超{self.pivot_lookback}日整理区高点${pivot:.2f}，"
            f"幅度+{breakout_pct*100:.1f}% | "
            f"[量能] {vol_ratio:.1f}x均量"
        )
        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )
        if not self.live_mode and symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=current,
                entry_date=date,
                highest_price=current,
            )
        return signal
