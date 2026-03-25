"""
strategies/v_weinstein_adx/weinstein_adx_strategy.py — Weinstein Stage 2 + ADX 增强版

在 Weinstein Stage 2 策略基础上，增加两个买入条件：
  1. 收盘价 > 50日最高价（确认价格处于上升趋势）
  2. ADX(14) > 25（确认趋势强度足够）

继承 WeinsteinStrategy，复用出场逻辑和持仓追踪。

对应 config.yaml 的 strategies.v_weinstein_adx 段。
"""

import numpy as np
import pandas as pd

from events import SignalEvent
from strategies.v_weinstein.weinstein_strategy import WeinsteinStrategy


class WeinsteinADXStrategy(WeinsteinStrategy):
    strategy_id = "v_weinstein_adx"
    strategy_name = "Weinstein Stage 2 + ADX 增强"

    def _check_entry(self, symbol, df, date):
        # 数据不足时跳过（继承父类需求 + ADX 需要额外数据）
        need = max(self.sma_long + self.trend_lookback, 50 + 14)
        if len(df) < need:
            return None

        close_series = df["close"]
        current = float(close_series.iloc[-1])

        # ── 1. 继承 Weinstein Stage 2 条件 ──────────────────────────
        # (复用父类的 SMA150 上升、价格在 SMA150 上方、突破整理区、放量)

        # 1a. SMA150 上升趋势确认
        sma150 = close_series.rolling(self.sma_long).mean()
        sma_now = float(sma150.iloc[-1])
        sma_past = float(sma150.iloc[-self.trend_lookback])
        if sma_now <= sma_past:
            return None

        # 1b. 价格在 SMA150 上方
        if current <= sma_now:
            return None

        # 1c. 突破近期整理区最高价
        pivot = float(close_series.iloc[-(self.pivot_lookback + 1):-1].max())
        if current <= pivot * (1 + self.min_breakout_pct):
            return None

        # 1d. 放量确认
        avg_vol = float(df["volume"].iloc[-21:-1].mean())
        if avg_vol == 0:
            return None
        vol_ratio = float(df["volume"].iloc[-1]) / avg_vol
        if vol_ratio < self.volume_mult:
            return None

        # ── 2. 新增条件：收盘价 > 50日最高价 ─────────────────────────
        high_50 = float(close_series.iloc[-50:].max())
        if current <= high_50:
            return None

        # ── 3. 新增条件：ADX(14) > 25 ───────────────────────────────
        adx_value = self._calc_adx(df, period=14)
        if adx_value <= 25:
            return None

        # ── 信号生成 ─────────────────────────────────────────────────
        breakout_pct = (current - pivot) / pivot
        strength = 4  # ADX 确认，趋势强度更高，提升到 4 星
        stop_loss = round(current * (1 - self.stop_loss_pct), 2)
        reason = (
            f"[Stage2] SMA{self.sma_long}({sma_now:.0f})上升{self.trend_lookback}天 | "
            f"[突破] 超{self.pivot_lookback}日整理区高点${pivot:.2f}，幅度+{breakout_pct*100:.1f}% | "
            f"[50日高点] 收于50日最高${high_50:.2f} | "
            f"[ADX] {adx_value:.1f}>25，趋势确认 | "
            f"[量能] {vol_ratio:.1f}x均量"
        )
        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )
        # 自动建立持仓记录
        if symbol not in self.positions:
            from strategies.v1_wizard.sepa_minervini import Position
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=current,
                entry_date=date,
                highest_price=current,
            )
        return signal

    def _calc_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ADX（平均趋向指数）。

        ADX 衡量趋势强度，不考虑趋势方向。
        规则：
          - ADX < 20：市场无趋势
          - ADX 20-25：趋势较弱
          - ADX > 25：趋势确认
          - ADX > 40：强趋势
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range (TR)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        tr.iloc[0] = high.iloc[0] - low.iloc[0]

        # Directional Movement (+DM, -DM)
        up = high - high.shift()
        down = low.shift() - low
        plus_dm = ((up > down) & (up > 0)) * up
        minus_dm = ((down > up) & (down > 0)) * down

        # Wilder 平滑（使用 ewm，等价于 EMA with alpha=1/period）
        atr = tr.ewm(alpha=1 / period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr

        # DX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)

        # ADX = DX 的平滑
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()

        return float(adx.iloc[-1])
