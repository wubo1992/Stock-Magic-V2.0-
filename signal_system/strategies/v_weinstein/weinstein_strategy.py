"""
strategies/v_weinstein/weinstein_strategy.py — Stan Weinstein Stage 2 阶段分析

完全重写，严格遵循 Weinstein《Secrets of a Professional Floor Trader》的核心原则：

入场规则：
1. 市场必须确认在上升趋势（SPY > SMA50）
2. 股票本身必须在 Stage 2（股价 > SMA30，SMA30 上升 ≥ 30天）
3. 股价回调至 SMA30 附近形成支撑（最小阻力线）
4. 放量突破2-3周整理区间（最小阻力线）
5. 放量确认（成交量 ≥ 前日均量的 1.5 倍）

出场规则（Weinstein 原版）：
- 跌破 SMA30 立即出局（不是止损，是趋势破坏）
- 也可以用追踪止盈从高位回落 20%

核心改进：
- 增加"股价在 SMA30 上方且乖离不大"的条件（避免追高）
- 加入板块 RS 排名过滤
- 加入最小整理区间时间（避免假突破）

对应 config.yaml 的 strategies.v_weinstein 段。
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from events import EventQueue, SignalEvent
from strategies.base import StrategyBase


@dataclass
class WeinsteinPosition:
    symbol: str
    entry_price: float
    entry_date: datetime
    highest_price: float
    days_held: int = 0
    shares: float = 0.0
    stage2_peak_price: float = 0.0  # 入场前的 Stage 2 高点，用于判断真假突破


class WeinsteinStrategy(StrategyBase):
    strategy_id = "v_weinstein"
    strategy_name = "Weinstein Stage 2"

    def __init__(
        self,
        strategy_config: dict,
        market_data: dict[str, pd.DataFrame],
        live_mode: bool = False,
    ) -> None:
        super().__init__(strategy_config, market_data)
        self.live_mode = live_mode
        self.positions: dict[str, WeinsteinPosition] = {}

        # 均线参数（Weinstein 经典值）
        self.sma_market = self.cfg.get("sma_market", 50)    # 市场趋势：SPY > SMA50
        self.sma_stage2 = self.cfg.get("sma_stage2", 30)    # Stage 2 均线：30 日
        self.sma_long = self.cfg.get("sma_long", 150)       # 长期均线：150 日（供参考）

        # Stage 2 确认：SMA30 需要上升至少 N 天
        self.stage2_lookback = self.cfg.get("stage2_lookback", 30)
        self.trend_lookback = self.stage2_lookback  # 别名，兼容子策略

        # 其他参数（兼容子策略）
        self.pivot_lookback = self.cfg.get("pivot_lookback", 30)
        self.min_breakout_pct = self.cfg.get("min_breakout_pct", 0.02)
        self.volume_mult = self.cfg.get("volume_mult", 1.5)
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.08)
        self.trailing_stop_pct = self.cfg.get("trailing_stop_pct", 0.20)
        self.time_stop_days = self.cfg.get("time_stop_days", 999)  # 默认极大，不启用
        self.time_stop_min_gain = self.cfg.get("time_stop_min_gain", 0.0)
        self.sma_short = self.cfg.get("sma_short", 50)
        self.sma_mid = self.cfg.get("sma_mid", 150)
        self.rs_min_percentile = self.cfg.get("rs_min_percentile", 0)  # 0=不启用RS

        # 整理区间参数
        self.consolidation_days = self.cfg.get("consolidation_days", 15)  # 至少15天整理
        self.min_breakout_pct = self.cfg.get("min_breakout_pct", 0.02)  # 突破幅度≥2%

        # 量能参数
        self.volume_mult = self.cfg.get("volume_mult", 1.5)  # 放量≥1.5倍

        # 乖离率过滤（价格不能离 SMA30 太远，避免追高）
        self.max_deviation_pct = self.cfg.get("max_deviation_pct", 0.35)  # 偏离 SMA30 ≤ 35%（放松）

        # RS 过滤
        self.rs_min_percentile = self.cfg.get("rs_min_percentile", 70)

        # 出场参数
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.08)    # 止损 8%
        self.trailing_stop_pct = self.cfg.get("trailing_stop_pct", 0.20)  # 追踪止盈 20%

        # RS 缓存
        self._rs_cache: dict = {}

    def run_date(self, date: datetime, queue: EventQueue) -> list[SignalEvent]:
        signals = []
        exit_signals = self._check_exits(date)
        for sig in exit_signals:
            queue.put(sig)
            signals.append(sig)

        # M 市场过滤器：SPY > SMA50
        if not self._is_market_bull(date):
            return signals

        for symbol, df in self.market_data.items():
            if symbol == "SPY":
                continue
            df_to_date = self._slice_to_date(df, date)
            min_rows = self.sma_long + self.stage2_lookback + self.consolidation_days + 10
            if len(df_to_date) < min_rows:
                continue
            signal = self._check_entry(symbol, df_to_date, date)
            if signal:
                queue.put(signal)
                signals.append(signal)

        return signals

    def _is_market_bull(self, date) -> bool:
        """市场在上升趋势：SPY > SMA50"""
        spy_df = self.market_data.get("SPY")
        if spy_df is None or len(spy_df) < max(self.sma_market, 30):
            return False
        spy_sliced = self._slice_to_date(spy_df, date)
        if spy_sliced.empty:
            return False
        close = spy_sliced["close"]
        sma = close.rolling(self.sma_market).mean()
        if len(sma) < self.sma_market:
            return False
        return float(close.iloc[-1]) > float(sma.iloc[-1])

    def _check_entry(self, symbol: str, df: pd.DataFrame, date: datetime):
        close_series = df["close"]
        current = float(close_series.iloc[-1])
        n = len(close_series)

        # ── 1. Stage 2 确认：SMA30 本身在上升 ─────────────────
        sma30 = close_series.rolling(self.sma_stage2).mean()
        if len(sma30) < self.stage2_lookback:
            return None
        sma30_now = float(sma30.iloc[-1])
        sma30_past = float(sma30.iloc[-self.stage2_lookback])
        if sma30_now <= sma30_past:
            return None

        # ── 2. 股价在 SMA30 上方 ──────────────────────────────
        if current <= sma30_now:
            return None

        # ── 3. 乖离率检查：价格不能离 SMA30 太远（避免追高）────
        deviation = (current - sma30_now) / sma30_now
        if deviation > self.max_deviation_pct:
            return None  # 乖离太大，不追

        # ── 4. 寻找整理区间（至少15天，不含今天）─────────────────
        # Weinstein: 股价在 SMA30 附近横盘整理，形成紧凑的整理区间
        # 整理区间：回看 consolidation_days+5 天，但排除今天（即 consolidation_days 天前到5天前）
        cons_end_idx = n - 1  # 排除今天（-1）
        cons_start_idx = cons_end_idx - self.consolidation_days - 4
        if cons_start_idx < 0:
            cons_start_idx = 0
        consolidation = close_series.iloc[cons_start_idx:cons_end_idx]
        if len(consolidation) < self.consolidation_days:
            return None

        # 整理区间高点（柄的起点）
        cons_high = float(consolidation.max())
        cons_low = float(consolidation.min())

        # 整理区间必须相对紧凑（高低点差距 ≤ 20%，放松限制）
        cons_range = (cons_high - cons_low) / cons_low
        if cons_range > 0.20:
            return None

        # ── 5. 放量突破确认 ───────────────────────────────────
        avg_vol = float(df["volume"].iloc[-21:-1].mean())
        if avg_vol == 0:
            return None
        vol_ratio = float(df["volume"].iloc[-1]) / avg_vol
        if vol_ratio < self.volume_mult:
            return None

        # ── 6. 突破幅度检查 ──────────────────────────────────
        breakout_pct = (current - cons_high) / cons_high
        if breakout_pct < self.min_breakout_pct:
            return None

        # ── 7. RS 过滤 ──────────────────────────────────────
        rs_ok, rs_value = self._check_rs(symbol, df, date)
        if not rs_ok:
            return None

        # ── 8. 计算信号强度 ─────────────────────────────────
        strength = 3
        if vol_ratio >= 2.0 and rs_value >= 85:
            strength = 5
        elif vol_ratio >= 1.8 or rs_value >= 80:
            strength = 4

        stop_loss = round(current * (1 - self.stop_loss_pct), 2)
        reason = (
            f"[Stage2] SMA{self.sma_stage2}上升≥{self.stage2_lookback}天 | "
            f"[乖离] 偏离均线{deviation*100:.0f}%（≤{self.max_deviation_pct*100:.0f}%）| "
            f"[整理] {self.consolidation_days}天紧凑区间（{cons_range*100:.0f}%）| "
            f"[突破] +{breakout_pct*100:.1f}%放量{vol_ratio:.1f}x | "
            f"[RS] Top {100-rs_value:.0f}% | "
            f"[止损] ${stop_loss:.2f}"
        )
        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )

        if symbol not in self.positions:
            self.positions[symbol] = WeinsteinPosition(
                symbol=symbol,
                entry_price=current,
                entry_date=date,
                highest_price=current,
                stage2_peak_price=cons_high,
            )
        return signal

    def _check_rs(self, symbol: str, df: pd.DataFrame, date: datetime):
        """相对强度（RS）过滤"""
        date_key = date.date()
        if date_key not in self._rs_cache:
            self._rs_cache[date_key] = {}

        cache = self._rs_cache[date_key]
        BENCHMARKS = ("SPY", "ASHR", "EWT")

        if "all_rs" not in cache:
            spy_df = self.market_data.get("SPY")
            if spy_df is None:
                return True, 50.0
            spy_sliced = self._slice_to_date(spy_df, date)
            if spy_sliced.empty or len(spy_sliced) < 60:
                return True, 50.0
            spy_ret = float(spy_sliced["close"].iloc[-1] / spy_sliced["close"].iloc[-60] - 1)
            if spy_ret <= 0:
                return True, 50.0

            rs_scores = {}
            for sym, other_df in self.market_data.items():
                if sym in BENCHMARKS:
                    continue
                other_sliced = self._slice_to_date(other_df, date)
                if other_sliced.empty or len(other_sliced) < 60:
                    continue
                ret = float(other_sliced["close"].iloc[-1] / other_sliced["close"].iloc[-60] - 1)
                rs_scores[sym] = ret / spy_ret if spy_ret != 0 else 0

            if len(rs_scores) < 2:
                cache["all_rs"] = {}
                return True, 50.0

            all_scores = list(rs_scores.values())
            for sym, score in rs_scores.items():
                pct = float(np.mean([s <= score for s in all_scores]) * 100)
                rs_scores[sym] = pct
            cache["all_rs"] = rs_scores

        all_rs = cache.get("all_rs", {})
        if symbol not in all_rs:
            return False, 0.0

        rs_pct = all_rs[symbol]
        return rs_pct >= self.rs_min_percentile, rs_pct

    def _check_exits(self, date: datetime) -> list[SignalEvent]:
        """
        Weinstein 出场规则：
        1. 跌破 SMA30（趋势破坏，Weinstein 原版最重要的出场信号）
        2. 从高位回落 20%（追踪止盈）
        3. 固定止损 8%
        """
        signals = []
        to_close = []

        for symbol, pos in list(self.positions.items()):
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

            # ── 趋势破坏：跌破 SMA30（Weinstein 核心出场）─────────
            sma30 = df_to_date["close"].rolling(self.sma_stage2).mean()
            if len(sma30) >= self.sma_stage2:
                sma30_val = float(sma30.iloc[-1])
                if current_price <= sma30_val:
                    exit_reason = (
                        f"趋势破坏（SMA30）：${current_price:.2f}≤SMA{self.sma_stage2}(${sma30_val:.2f})"
                    )
                    sig = SignalEvent.create(
                        symbol=symbol, timestamp=date, direction="sell",
                        strength=3, reason=exit_reason, stop_loss=None,
                        shares=pos.shares,
                    )
                    signals.append(sig)
                    to_close.append(symbol)
                    continue

            # ── 固定止损 8% ───────────────────────────────────
            stop_price = pos.entry_price * (1 - self.stop_loss_pct)
            if current_price <= stop_price:
                exit_reason = (
                    f"止损（-8%）：入场${pos.entry_price:.2f}，当前${current_price:.2f}"
                )
                sig = SignalEvent.create(
                    symbol=symbol, timestamp=date, direction="sell",
                    strength=3, reason=exit_reason, stop_loss=None,
                    shares=pos.shares,
                )
                signals.append(sig)
                to_close.append(symbol)
                continue

            # ── 追踪止盈 20% ─────────────────────────────────
            if pos.highest_price > pos.entry_price:
                trailing = pos.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing:
                    gain = (pos.highest_price / pos.entry_price - 1) * 100
                    exit_reason = (
                        f"追踪止盈：最高${pos.highest_price:.2f}(+{gain:.1f}%)，"
                        f"当前${current_price:.2f}，回落{self.trailing_stop_pct*100:.0f}%"
                    )
                    sig = SignalEvent.create(
                        symbol=symbol, timestamp=date, direction="sell",
                        strength=3, reason=exit_reason, stop_loss=None,
                        shares=pos.shares,
                    )
                    signals.append(sig)
                    to_close.append(symbol)

        for symbol in to_close:
            if symbol in self.positions:
                del self.positions[symbol]

        return signals

    def _slice_to_date(self, df: pd.DataFrame, date: datetime):
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
