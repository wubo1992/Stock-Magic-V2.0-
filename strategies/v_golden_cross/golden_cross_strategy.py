"""
strategies/v_golden_cross/golden_cross_strategy.py — 金叉死叉策略V1（Hybrid：直接买入 + 回调买入）

基于 10EMA / 20EMA 的经典均线交叉策略：
- 金叉形成 + 价格在 EMA20 附近（7%以内）→ 直接买入
- 金叉形成 + 价格已大涨 → 等待回落买入（回调买入）
- 死叉卖出
- 附加：固定止盈20%、止损8%、追踪止盈20%、时间止损

策略 ID：v_golden_cross
输出文件夹：output/v_golden_cross/
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from events import EventQueue, SignalEvent
from strategies.base import StrategyBase


@dataclass
class Position:
    symbol: str
    entry_date: datetime
    entry_price: float
    highest_price: float
    days_held: int = 0


@dataclass
class PullbackWatch:
    symbol: str
    golden_cross_date: datetime
    golden_cross_price: float
    ema20_at_cross: float


class GoldenCrossStrategy(StrategyBase):
    strategy_id = "v_golden_cross"
    strategy_name = "金叉死叉策略V1"

    def __init__(
        self,
        strategy_config: dict,
        market_data: dict[str, pd.DataFrame],
        live_mode: bool = False,
    ) -> None:
        super().__init__(strategy_config, market_data)
        self.live_mode = live_mode
        self.positions: dict[str, Position] = {}
        self.pullback_watch: dict[str, PullbackWatch] = {}

        self.fast_ema = self.cfg.get("fast_ema", 10)
        self.slow_ema = self.cfg.get("slow_ema", 20)
        self.volume_mult = self.cfg.get("volume_mult", 1.5)
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.08)
        self.take_profit_pct = self.cfg.get("take_profit_pct", 0.20)
        self.trailing_stop_pct = self.cfg.get("trailing_stop_pct", 0.20)
        self.time_stop_days = self.cfg.get("time_stop_days", 20)
        self.time_stop_min_gain = self.cfg.get("time_stop_min_gain", 0.03)
        self.pullback_tolerance = self.cfg.get("pullback_tolerance", 0.03)
        self.pullback_max_days = self.cfg.get("pullback_max_days", 15)
        self.immediate_buy_threshold = self.cfg.get("immediate_buy_ema_distance", 0.07)

    def run_date(self, date: datetime, queue: EventQueue) -> list[SignalEvent]:
        signals = []

        exit_signals = self._check_exits(date)
        for sig in exit_signals:
            queue.put(sig)
            signals.append(sig)

        pullback_signals = self._check_pullback_entries(date)
        for sig in pullback_signals:
            queue.put(sig)
            signals.append(sig)

        for symbol, df in self.market_data.items():
            df_to_date = self._slice_to_date(df, date)
            min_rows = self.slow_ema + 30
            if len(df_to_date) < min_rows:
                continue
            if symbol not in self.positions and symbol not in self.pullback_watch:
                direct_signals = self._check_golden_cross_watch(symbol, df_to_date, date)
                for sig in direct_signals:
                    queue.put(sig)
                    signals.append(sig)

        return signals

    def _check_golden_cross_watch(self, symbol: str, df: pd.DataFrame, date: datetime) -> list[SignalEvent]:
        close = df["close"]
        volume = df["volume"]

        # 计算 EMA 系列
        ema_fast = close.ewm(span=self.fast_ema, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_ema, adjust=False).mean()

        if len(ema_fast) < 2 or len(ema_slow) < 2:
            return []

        # 用收盘价重新计算当日 EMA（金叉当天就能检测，不需要次日）
        # EMA_N = alpha * price_N + (1-alpha) * EMA_{N-1}
        alpha_fast = 2 / (self.fast_ema + 1)
        alpha_slow = 2 / (self.slow_ema + 1)

        # 前日 EMA（EMA 系列倒数第2个值）
        ema_fast_prev = float(ema_fast.iloc[-2])
        ema_slow_prev = float(ema_slow.iloc[-2])

        # 当日 EMA：用收盘价直接算（不依赖 ewm 序列的最后一个值）
        current_price = float(close.iloc[-1])
        ema_fast_curr = alpha_fast * current_price + (1 - alpha_fast) * ema_fast_prev
        ema_slow_curr = alpha_slow * current_price + (1 - alpha_slow) * ema_slow_prev

        # 金叉条件：前日快线<=慢线，当日快线>慢线
        if not (ema_fast_prev <= ema_slow_prev and ema_fast_curr > ema_slow_curr):
            return []

        vol_current = float(volume.iloc[-1])
        vol_ma = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = vol_current / vol_ma if vol_ma > 0 else 0
        if vol_ratio < self.volume_mult:
            return []

        ema20_current = ema_slow_curr
        ema20_distance = abs(current_price - ema20_current) / ema20_current

        # Hybrid 第一层：价格已在 EMA20 附近 → 直接买入
        if ema20_distance <= self.immediate_buy_threshold:
            strength = self._score_signal(ema_fast_curr, ema20_current, vol_ratio)
            stop_loss = round(ema20_current * (1 - self.stop_loss_pct), 2)
            reason = (
                f"[金叉直接买入] 10EMA上穿20EMA | "
                f"[量能] {vol_ratio:.1f}倍均量 | "
                f"[价格] ${current_price:.2f} / EMA20=${ema20_current:.2f}（偏离{ema20_distance*100:.1f}%）"
            )
            signal = SignalEvent.create(
                symbol=symbol,
                timestamp=date,
                direction="buy",
                strength=strength,
                reason=reason,
                stop_loss=stop_loss,
            )
            if not self.live_mode and symbol not in self.positions:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    entry_date=date,
                    entry_price=current_price,
                    highest_price=current_price,
                )
            return [signal]

        # Hybrid 第二层：价格已大涨 → 加入回调监控
        self.pullback_watch[symbol] = PullbackWatch(
            symbol=symbol,
            golden_cross_date=date,
            golden_cross_price=current_price,
            ema20_at_cross=ema20_current,
        )
        return []

    def _check_pullback_entries(self, date: datetime) -> list[SignalEvent]:
        signals = []
        to_remove = []

        for symbol, watch in self.pullback_watch.items():
            df = self.market_data.get(symbol)
            if df is None:
                to_remove.append(symbol)
                continue

            df_to_date = self._slice_to_date(df, date)
            if df_to_date.empty or len(df_to_date) < 2:
                continue

            close = df_to_date["close"]
            volume = df_to_date["volume"]
            ema_slow = close.ewm(span=self.slow_ema, adjust=False).mean()

            current_price = float(close.iloc[-1])
            ema20_current = float(ema_slow.iloc[-1])
            pullback_pct = (watch.golden_cross_price - current_price) / watch.golden_cross_price
            days_waited = (date - watch.golden_cross_date).days

            if pullback_pct >= self.pullback_tolerance:
                vol_current = float(volume.iloc[-1])
                vol_ma = float(volume.rolling(20).mean().iloc[-1])
                vol_ratio = vol_current / vol_ma if vol_ma > 0 else 0

                strength = self._score_signal(
                    float(close.ewm(span=self.fast_ema, adjust=False).mean().iloc[-1]),
                    ema20_current,
                    vol_ratio,
                )

                stop_loss = round(ema20_current * (1 - self.stop_loss_pct), 2)

                reason = (
                    f"[回调买入] 金叉后{days_waited}天回落{pullback_pct*100:.1f}%至${current_price:.2f} | "
                    f"[金叉价] ${watch.golden_cross_price:.2f} | [量能] {vol_ratio:.1f}倍均量"
                )

                signal = SignalEvent.create(
                    symbol=symbol,
                    timestamp=date,
                    direction="buy",
                    strength=strength,
                    reason=reason,
                    stop_loss=stop_loss,
                )
                signals.append(signal)

                if not self.live_mode and symbol not in self.positions:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        entry_date=date,
                        entry_price=current_price,
                        highest_price=current_price,
                    )

                to_remove.append(symbol)
                continue

            if days_waited > self.pullback_max_days:
                to_remove.append(symbol)

        for symbol in to_remove:
            self.pullback_watch.pop(symbol, None)

        return signals

    def _check_exits(self, date: datetime) -> list[SignalEvent]:
        signals = []
        to_close = []

        for symbol, pos in self.positions.items():
            df = self.market_data.get(symbol)
            if df is None:
                continue
            df_to_date = self._slice_to_date(df, date)
            if df_to_date.empty:
                continue

            current_price = float(df_to_date["close"].iloc[-1])
            pos.days_held += 1

            if current_price > pos.highest_price:
                pos.highest_price = current_price

            pnl_pct = (current_price / pos.entry_price - 1) * 100
            exit_reason = None

            close = df_to_date["close"]
            ema_fast_series = close.ewm(span=self.fast_ema, adjust=False).mean()
            ema_slow_series = close.ewm(span=self.slow_ema, adjust=False).mean()
            is_death_cross = False
            if len(ema_fast_series) >= 2 and len(ema_slow_series) >= 2:
                ema_fast_prev = float(ema_fast_series.iloc[-2])
                ema_slow_prev = float(ema_slow_series.iloc[-2])
                ema_fast_curr = float(ema_fast_series.iloc[-1])
                ema_slow_curr = float(ema_slow_series.iloc[-1])
                is_death_cross = ema_fast_prev >= ema_slow_prev and ema_fast_curr < ema_slow_curr

            if current_price <= pos.entry_price * (1 - self.stop_loss_pct):
                exit_reason = f"止损8%：当前${current_price:.2f}，亏损{pnl_pct:.1f}%"
            elif pnl_pct >= self.take_profit_pct * 100:
                exit_reason = f"固定止盈20%：盈利{pnl_pct:.1f}%"
            elif is_death_cross:
                exit_reason = f"死叉出场：10EMA下穿20EMA，盈利{pnl_pct:.1f}%"
            elif pos.highest_price > pos.entry_price:
                trailing_stop = pos.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop:
                    gain_pct = (pos.highest_price / pos.entry_price - 1) * 100
                    exit_reason = f"追踪止盈20%：最高${pos.highest_price:.2f}(+{gain_pct:.1f}%)，当前${current_price:.2f}"
            elif pos.days_held >= self.time_stop_days and pnl_pct < self.time_stop_min_gain * 100:
                exit_reason = f"时间止损：持仓{pos.days_held}天，盈利仅{pnl_pct:.1f}%"

            if exit_reason:
                sig = SignalEvent.create(
                    symbol=symbol,
                    timestamp=date,
                    direction="sell",
                    strength=3,
                    reason=exit_reason,
                    stop_loss=None,
                )
                signals.append(sig)
                to_close.append(symbol)

        for symbol in to_close:
            del self.positions[symbol]

        return signals

    def _score_signal(
        self,
        ema_fast: float,
        ema_slow: float,
        vol_ratio: float,
    ) -> int:
        ema_gap = (ema_fast - ema_slow) / ema_slow * 100
        score = 3
        if ema_gap > 1.0 and vol_ratio >= 2.0:
            score = 5
        elif ema_gap > 0.5 and vol_ratio >= 1.5:
            score = 4
        return score

    def get_open_positions(self) -> dict:
        return dict(self.positions)

    def _slice_to_date(self, df: pd.DataFrame, date: datetime) -> pd.DataFrame:
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        idx = df.index
        if idx.tzinfo is None:
            idx = idx.tz_localize("UTC")
            df = df.copy()
            df.index = idx
        # 使用 date + 1 day 包含完整当前交易日（UTC 00:00 + 1天 = 次日 00:00
        # 因此 index 条目如 "2026-01-05 04:00:00+00:00" 会被包含进来）
        from datetime import timedelta
        cutoff = date + timedelta(days=1)
        return df[df.index < cutoff]
