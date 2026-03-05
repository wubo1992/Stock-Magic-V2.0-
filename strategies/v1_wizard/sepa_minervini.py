"""
strategies/v1_wizard/sepa_minervini.py — 魔法师策略V1

基于 Mark Minervini《股票魔法师》中的 SEPA + VCP 策略：
- 趋势模板：8个条件（均线排列 + 52周高低点过滤）
- 相对强度（RS）过滤：只选市场表现前30%的股票
- VCP 形态识别：波动收缩形态检测
- 枢轴点突破：价格突破近期高点 + 成交量放大确认
- 出场管理：固定止损 + 追踪止盈 + 时间止损

策略 ID：v1（注册表中的键）
输出文件夹：output/v1_wizard/
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from events import EventQueue, SignalEvent
from strategies.base import StrategyBase


@dataclass
class Position:
    symbol: str
    entry_price: float
    entry_date: datetime
    highest_price: float
    stop_loss: float
    days_held: int = 0


class SEPAStrategy(StrategyBase):
    strategy_id = "v1_wizard"
    strategy_name = "魔法师策略V1"

    def __init__(
        self,
        strategy_config: dict,
        market_data: dict[str, pd.DataFrame],
        live_mode: bool = False,
    ) -> None:
        super().__init__(strategy_config, market_data)
        self.live_mode = live_mode
        self.positions: dict[str, Position] = {}

        self.sma_short = self.cfg.get("sma_short", 50)
        self.sma_mid = self.cfg.get("sma_mid", 150)
        self.sma_long = self.cfg.get("sma_long", 200)
        self.trend_lookback = self.cfg.get("trend_lookback", 20)
        self.low_52w_mult = self.cfg.get("low_52w_mult", 1.25)
        self.high_52w_mult = self.cfg.get("high_52w_mult", 0.75)
        self.rs_min_percentile = self.cfg.get("rs_min_percentile", 70)
        self.pivot_lookback = self.cfg.get("pivot_lookback", 30)
        self.min_breakout_pct = self.cfg.get("min_breakout_pct", 0.005)
        self.volume_mult = self.cfg.get("volume_mult", 1.5)
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.10)
        self.trailing_stop_pct = self.cfg.get("trailing_stop_pct", 0.20)
        self.time_stop_days = self.cfg.get("time_stop_days", 20)
        self.time_stop_min_gain = self.cfg.get("time_stop_min_gain", 0.03)
        self.vcp_lookback = self.cfg.get("vcp_lookback", 50)
        self.vcp_min_contractions = self.cfg.get("vcp_min_contractions", 2)
        self.vcp_final_range_pct = self.cfg.get("vcp_final_range_pct", 0.08)

    def run_date(self, date: datetime, queue: EventQueue) -> list[SignalEvent]:
        signals = []
        exit_signals = self._check_exits(date)
        for sig in exit_signals:
            queue.put(sig)
            signals.append(sig)

        for symbol, df in self.market_data.items():
            df_to_date = self._slice_to_date(df, date)
            min_rows = self.sma_long + self.pivot_lookback + 10
            if len(df_to_date) < min_rows:
                continue
            signal = self._check_entry(symbol, df_to_date, date)
            if signal:
                queue.put(signal)
                signals.append(signal)

        return signals

    def _check_entry(self, symbol, df, date):
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

        strength = self._score_signal(breakout_pct, vol_ratio, rs_value)
        close = float(df["close"].iloc[-1])
        stop_loss = round(close * (1 - self.stop_loss_pct), 2)
        reason = (
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
        # 回测模式：自动建立持仓记录，供止损/止盈逻辑使用
        # 实盘模式：持仓由用户手动告知，不自动创建
        if not self.live_mode and symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=close,
                entry_date=date,
                highest_price=close,
                stop_loss=stop_loss,
            )
        return signal

    def _check_exits(self, date):
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
            exit_reason = None
            fixed_stop = pos.entry_price * (1 - self.stop_loss_pct)
            if current_price <= fixed_stop:
                exit_reason = (
                    f"触发止损：入场${pos.entry_price:.2f}，当前${current_price:.2f}，"
                    f"跌幅{(current_price/pos.entry_price-1)*100:.1f}%"
                )
            elif pos.highest_price > pos.entry_price:
                trailing_stop = pos.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop:
                    gain = (pos.highest_price / pos.entry_price - 1) * 100
                    exit_reason = (
                        f"追踪止盈：最高${pos.highest_price:.2f}（+{gain:.1f}%），"
                        f"当前${current_price:.2f}，从最高点回落{self.trailing_stop_pct*100:.0f}%"
                    )
            elif pos.days_held >= self.time_stop_days:
                current_gain = current_price / pos.entry_price - 1
                if current_gain < self.time_stop_min_gain:
                    exit_reason = (
                        f"时间止损：持仓{pos.days_held}天，盈利仅{current_gain*100:.1f}%"
                    )
            if exit_reason:
                sig = SignalEvent.create(
                    symbol=symbol, timestamp=date, direction="sell",
                    strength=3, reason=exit_reason, stop_loss=None,
                )
                signals.append(sig)
                to_close.append(symbol)
        for symbol in to_close:
            del self.positions[symbol]
        return signals

    def _check_trend_template(self, df):
        close = df["close"]
        n = len(close)
        sma50 = float(close.rolling(self.sma_short).mean().iloc[-1])
        sma150 = float(close.rolling(self.sma_mid).mean().iloc[-1])
        sma200 = float(close.rolling(self.sma_long).mean().iloc[-1])
        sma200_20ago = float(close.rolling(self.sma_long).mean().iloc[-1 - self.trend_lookback])
        current_close = float(close.iloc[-1])
        lookback_52w = min(252, n)
        high_52w = float(close.iloc[-lookback_52w:].max())
        low_52w = float(close.iloc[-lookback_52w:].min())

        if current_close <= sma50:
            return False, f"价格{current_close:.2f} <= SMA50({sma50:.2f})"
        if current_close <= sma150:
            return False, f"价格{current_close:.2f} <= SMA150({sma150:.2f})"
        if current_close <= sma200:
            return False, f"价格{current_close:.2f} <= SMA200({sma200:.2f})"
        if not (sma50 > sma150 > sma200):
            return False, "均线未多头排列"
        if sma150 <= sma200:
            return False, f"SMA150({sma150:.2f}) <= SMA200({sma200:.2f})"
        if sma200 <= sma200_20ago:
            return False, "SMA200近期未上升"
        if current_close < low_52w * self.low_52w_mult:
            return False, "价格未距52周低点25%以上"
        if current_close < high_52w * self.high_52w_mult:
            return False, "价格距52周高点超过25%"

        pct_from_low = (current_close / low_52w - 1) * 100
        pct_from_high = (current_close / high_52w - 1) * 100
        return True, (
            f"SMA50({sma50:.0f})>SMA150({sma150:.0f})>SMA200({sma200:.0f})，"
            f"SMA200上升中，距52W低点+{pct_from_low:.0f}%，距52W高点{pct_from_high:.0f}%"
        )

    def _check_rs(self, symbol, df, date):
        lookback = min(252, len(df))
        if lookback < 20:
            return False, 0.0
        this_return = float(df["close"].iloc[-1] / df["close"].iloc[-lookback] - 1)
        all_returns = []
        for sym, other_df in self.market_data.items():
            other_sliced = self._slice_to_date(other_df, date)
            if len(other_sliced) < lookback:
                continue
            ret = float(other_sliced["close"].iloc[-1] / other_sliced["close"].iloc[-lookback] - 1)
            all_returns.append(ret)
        if len(all_returns) < 2:
            return True, 50.0
        rs_percentile = float(np.mean([r <= this_return for r in all_returns]) * 100)
        return rs_percentile >= self.rs_min_percentile, rs_percentile

    def _check_vcp(self, df):
        lookback = self.vcp_lookback
        min_c = self.vcp_min_contractions
        swing_n = 3
        if len(df) < lookback + swing_n + 5:
            return False, "数据不足，跳过VCP检测"
        base = df.iloc[-(lookback + 1):-1]
        close = base["close"].to_numpy(dtype=float)
        volume = base["volume"].to_numpy(dtype=float)
        price_ref = float(close.mean())
        if price_ref <= 0:
            return False, "价格数据异常"
        highs = [
            i for i in range(swing_n, len(close) - swing_n)
            if all(close[i] >= close[i - j] for j in range(1, swing_n + 1))
            and all(close[i] >= close[i + j] for j in range(1, swing_n + 1))
        ]
        lows = [
            i for i in range(swing_n, len(close) - swing_n)
            if all(close[i] <= close[i - j] for j in range(1, swing_n + 1))
            and all(close[i] <= close[i + j] for j in range(1, swing_n + 1))
        ]
        if len(lows) < min_c or len(highs) < min_c:
            return False, f"收缩次数不足（找到{len(lows)}次，需≥{min_c}次）"
        contractions = []
        for low_idx in lows:
            preceding_highs = [h for h in highs if h < low_idx]
            if not preceding_highs:
                continue
            high_idx = preceding_highs[-1]
            depth = (close[high_idx] - close[low_idx]) / close[high_idx]
            seg_vol = volume[high_idx: low_idx + 1]
            avg_vol = float(seg_vol.mean()) if len(seg_vol) > 0 else 0.0
            contractions.append({"depth": depth, "avg_vol": avg_vol})
        if len(contractions) < min_c:
            return False, f"有效收缩次数不足（需≥{min_c}次）"
        recent = contractions[-min_c:]
        depths = [c["depth"] for c in recent]
        vols = [c["avg_vol"] for c in recent]
        if depths[-1] >= depths[0]:
            return False, f"回调幅度未收缩（{depths[0]*100:.0f}%→{depths[-1]*100:.0f}%）"
        if vols[0] > 0 and vols[-1] >= vols[0]:
            return False, "收缩期量能未递减"
        tail = min(10, max(3, len(close) // 5))
        tail_high = float(close[-tail:].max())
        tail_low = float(close[-tail:].min())
        tail_range = (tail_high - tail_low) / price_ref
        if tail_range > self.vcp_final_range_pct:
            return False, (
                f"末端收缩不够紧（箱体{tail_range*100:.1f}%，需<{self.vcp_final_range_pct*100:.0f}%）"
            )
        depth_str = "→".join(f"{d*100:.0f}%" for d in depths)
        return True, f"VCP{len(recent)}T：回调{depth_str}，量能收缩，末端{tail_range*100:.1f}%箱体"

    def _check_breakout(self, df):
        close = df["close"]
        if len(close) < self.pivot_lookback + 1:
            return False, 0.0, 0.0
        current_close = float(close.iloc[-1])
        pivot = float(close.iloc[-(self.pivot_lookback + 1):-1].max())
        breakout_pct = (current_close - pivot) / pivot
        if breakout_pct > self.min_breakout_pct:
            return True, breakout_pct, pivot
        return False, breakout_pct, pivot

    def _check_volume(self, df):
        volume = df["volume"]
        if len(volume) < 21:
            return False, 0.0
        current_vol = float(volume.iloc[-1])
        avg_vol_20 = float(volume.iloc[-21:-1].mean())
        if avg_vol_20 <= 0:
            return False, 0.0
        ratio = current_vol / avg_vol_20
        return ratio >= self.volume_mult, ratio

    def _score_signal(self, breakout_pct, vol_ratio, rs_percentile):
        score = 3
        if vol_ratio >= 2.0 and breakout_pct > 0.015:
            score = 5
        elif vol_ratio >= 1.8 or breakout_pct > 0.010:
            score = 4
        if rs_percentile >= 90:
            score = min(5, score + 1)
        return score

    def _slice_to_date(self, df, date):
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        idx = df.index
        if idx.tzinfo is None:
            idx = idx.tz_localize("UTC")
            df = df.copy()
            df.index = idx
        return df[df.index <= date]

    def get_open_positions(self):
        return dict(self.positions)
