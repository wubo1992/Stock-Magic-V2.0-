"""
strategies/v_zanger/zanger_strategy.py — Zanger 纯技术动量策略

继承 SEPAStrategy（复用出场逻辑、持仓追踪、工具方法），
只覆盖 _check_entry，实现纯技术突破入场（无 RS 过滤，无 VCP）：
  1. 价格 > SMA150 且 SMA150 本身在上升
  2. 今日收盘突破过去 N 日最高价
  3. 成交量 ≥ 3 倍 20 日均量

对应 config.yaml 的 strategies.v_zanger 段。
"""

from events import SignalEvent
from strategies.v1_wizard.sepa_minervini import Position, SEPAStrategy


class ZangerStrategy(SEPAStrategy):
    strategy_id = "v_zanger"
    strategy_name = "Zanger 纯技术动量"

    def _check_entry(self, symbol, df, date):
        # 数据不足时跳过（sma_long 通常 150，trend_lookback 20，合计 170+ 行）
        need = self.sma_long + self.trend_lookback
        if len(df) < need:
            return None

        close_series = df["close"]
        current = float(close_series.iloc[-1])

        # 1. 计算 SMA150
        sma = close_series.rolling(self.sma_long).mean()
        sma_now = float(sma.iloc[-1])
        if current <= sma_now:
            return None  # 价格须在 SMA 之上

        # 2. SMA150 本身在上升（当前值 > trend_lookback 天前的值）
        sma_past = float(sma.iloc[-self.trend_lookback])
        if sma_now <= sma_past:
            return None

        # 3. 突破过去 N 日最高收盘价（排除今天）
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

        # 信号评分（3-5 星，放量越大 / 突破越强 → 评分越高）
        breakout_pct = (current - pivot) / pivot
        strength = 3
        if vol_ratio >= 5:
            strength += 1
        if breakout_pct >= 0.02:
            strength += 1

        stop_loss = round(current * (1 - self.stop_loss_pct), 2)
        reason = (
            f"[趋势] SMA{self.sma_long}({sma_now:.0f})上升中 | "
            f"[突破] 超过{self.pivot_lookback}日高点${pivot:.2f}，"
            f"幅度+{breakout_pct*100:.1f}% | "
            f"[量能] 成交量{vol_ratio:.1f}倍均量"
        )
        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )
        # 自动建立持仓记录，供止损/止盈逻辑使用
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=current,
                entry_date=date,
                highest_price=current,
            )
        return signal
