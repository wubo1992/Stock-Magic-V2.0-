"""
strategies/v_adx50/adx50_strategy.py — ADX50 动量突破策略

买入条件：收盘价 > 50日最高价 且 ADX(14) > 25
止损：亏损 -10%
止盈：盈利 +20%
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from events import EventQueue, SignalEvent
from strategies.base import StrategyBase


@dataclass
class Position:
    """持仓记录"""
    symbol: str
    entry_price: float
    entry_date: datetime
    highest_price: float
    days_held: int = 0
    shares: float = 100.0


class ADX50Strategy(StrategyBase):
    strategy_id = "v_adx50"
    strategy_name = "ADX50 动量突破策略"

    def __init__(
        self,
        strategy_config: dict,
        market_data: dict[str, pd.DataFrame],
        live_mode: bool = False,
    ) -> None:
        super().__init__(strategy_config, market_data)
        self.live_mode = live_mode
        self.positions: dict[str, Position] = {}

        self.high_lookback = self.cfg.get("high_lookback", 50)
        self.adx_period = self.cfg.get("adx_period", 14)
        self.adx_threshold = self.cfg.get("adx_threshold", 25)
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.10)
        self.take_profit_pct = self.cfg.get("take_profit_pct", 0.20)

    def run_date(self, date: datetime, queue: EventQueue) -> list[SignalEvent]:
        signals = []
        # 1. 出场检查
        exit_signals = self._check_exits(date)
        for sig in exit_signals:
            queue.put(sig)
            signals.append(sig)

        # 2. 入场扫描
        for symbol, df in self.market_data.items():
            df_to_date = self._slice_to_date(df, date)
            min_rows = self.high_lookback + self.adx_period + 10
            if len(df_to_date) < min_rows:
                continue
            signal = self._check_entry(symbol, df_to_date, date)
            if signal:
                queue.put(signal)
                signals.append(signal)

        return signals

    def _check_exits(self, date: datetime) -> list[SignalEvent]:
        signals = []
        for symbol, pos in list(self.positions.items()):
            df = self.market_data.get(symbol)
            if df is None:
                continue
            # 用前一日收盘价判断出场（避免 look-ahead bias）
            df_to_prev = self._slice_to_date(df, date)
            if len(df_to_prev) < 2:
                continue
            prev_close = float(df_to_prev["close"].iloc[-2])  # 前一日收盘
            if pos.entry_price <= 0:
                continue
            gain_pct = (prev_close - pos.entry_price) / pos.entry_price

            if gain_pct <= -self.stop_loss_pct or gain_pct >= self.take_profit_pct:
                direction = "sell"
                strength = 3
                if gain_pct >= self.take_profit_pct:
                    reason = f"[止盈] 收益率+{gain_pct*100:.1f}%（阈值+{self.take_profit_pct*100:.0f}%）"
                else:
                    reason = f"[止损] 亏损{gain_pct*100:.1f}%（阈值-{self.stop_loss_pct*100:.0f}%）"
                signal = SignalEvent.create(
                    symbol=symbol,
                    timestamp=date,
                    direction=direction,
                    strength=strength,
                    reason=reason,
                )
                signals.append(signal)
                del self.positions[symbol]
        return signals

    def _check_entry(self, symbol: str, df: pd.DataFrame, date: datetime):
        # 已在持仓中则跳过（防止重复入场）
        if symbol in self.positions:
            return None

        close_series = df["close"]
        high_series = df["high"]

        # 计算 ADX(14) — 纯 pandas 实现
        adx_value = self._compute_adx(df, self.adx_period)
        if adx_value is None:
            return None
        if adx_value <= self.adx_threshold:
            return None

        # 50日最高价（排除今天）
        highs = high_series.iloc[:-1]
        if len(highs) < self.high_lookback:
            return None
        high_50 = float(highs.iloc[-self.high_lookback:].dropna().max())
        current_close = float(close_series.iloc[-1])
        if current_close <= high_50:
            return None

        # 计算突破幅度
        breakout_pct = (current_close - high_50) / high_50

        stop_loss = round(current_close * (1 - self.stop_loss_pct), 2)
        strength = 3
        reason = (
            f"[ADX50] 收盘价${current_close:.2f}突破{self.high_lookback}日高点${high_50:.2f}，"
            f"幅度+{breakout_pct*100:.1f}% | "
            f"[ADX{self.adx_period}]={adx_value:.1f}>{self.adx_threshold}"
        )
        signal = SignalEvent.create(
            symbol=symbol,
            timestamp=date,
            direction="buy",
            strength=strength,
            reason=reason,
            stop_loss=stop_loss,
        )
        # 建立持仓记录
        self.positions[symbol] = Position(
            symbol=symbol,
            entry_price=current_close,
            entry_date=date,
            highest_price=current_close,
        )
        return signal

    def _slice_to_date(self, df: pd.DataFrame, date: datetime) -> pd.DataFrame:
        """返回 date 当天之前的所有数据（包含 date 当天）"""
        mask = df.index <= date
        return df[mask]

    def _compute_adx(self, df: pd.DataFrame, period: int = 14) -> float | None:
        """
        纯 pandas 计算 ADX(period)。

        返回当前最新的 ADX 值，若数据不足或全为 NaN 则返回 None。
        使用 Wilder's smoothing 原版递推：
          smoothed[period-1] = SMA(period)
          smoothed[n] = smoothed[n-1] + (new_value - smoothed[n-1]) / period
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        # Wilder's smoothing — 严格递推实现
        def wilder_smooth(series: pd.Series, period: int) -> pd.Series:
            result = pd.Series(index=series.index, dtype=float)
            # 前 period-1 个为 NaN（数据不足）
            result.iloc[:period - 1] = float("nan")
            # 第 period 个取简单均值作为起点
            result.iloc[period - 1] = series.iloc[:period].mean()
            # 之后每步递推
            for i in range(period, len(series)):
                result.iloc[i] = (
                    result.iloc[i - 1] + (series.iloc[i] - result.iloc[i - 1]) / period
                )
            return result

        tr_smooth = wilder_smooth(tr, period)
        plus_dm_smooth = wilder_smooth(plus_dm, period)
        minus_dm_smooth = wilder_smooth(minus_dm, period)

        # Directional Indicators
        plus_di = (plus_dm_smooth / tr_smooth).where(tr_smooth > 0, 0.0) * 100
        minus_di = (minus_dm_smooth / tr_smooth).where(tr_smooth > 0, 0.0) * 100

        # DX
        di_sum = plus_di + minus_di
        dx = (abs(plus_di - minus_di) / di_sum).where(di_sum > 0, 0.0) * 100

        # ADX = Wilder smoothed DX
        adx_series = wilder_smooth(dx, period)
        adx_value = adx_series.iloc[-1]

        if pd.isna(adx_value):
            return None
        return float(adx_value)
