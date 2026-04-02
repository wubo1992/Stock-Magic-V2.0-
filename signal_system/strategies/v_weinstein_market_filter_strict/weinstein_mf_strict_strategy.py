"""
strategies/v_weinstein_market_filter_strict/weinstein_mf_strict_strategy.py — 市场过滤+严格放量版

在 v_weinstein_market_filter 基础上增强放量要求：
1. 市场环境过滤：SPY < SMA150 时禁止新买入
2. 更严格的放量标准：3x 均量（原来 2.5x）
3. 固定止损 10% + 涨超 20% 卖一半 + 追踪止盈 20%
"""

from events import SignalEvent
from strategies.v_weinstein.weinstein_strategy import WeinsteinStrategy


class PositionMFStrict:
    """市场过滤严格版持仓记录"""
    symbol: str
    entry_price: float
    entry_date: any
    highest_price: float
    days_held: int = 0
    shares: float = 0.0
    half_sold: bool = False
    first_tp_price: float = 0.0

    def __init__(
        self,
        symbol: str,
        entry_price: float,
        entry_date: any,
        highest_price: float,
        days_held: int = 0,
        shares: float = 0.0,
        half_sold: bool = False,
        first_tp_price: float = 0.0,
    ) -> None:
        self.symbol = symbol
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.highest_price = highest_price
        self.days_held = days_held
        self.shares = shares
        self.half_sold = half_sold
        self.first_tp_price = first_tp_price


class WeinsteinMFStrictStrategy(WeinsteinStrategy):
    strategy_id = "v_weinstein_mf_strict"
    strategy_name = "Weinstein 市场过滤+严格放量"

    def __init__(
        self,
        strategy_config: dict,
        market_data: dict,
        live_mode: bool = False,
    ) -> None:
        super().__init__(strategy_config, market_data, live_mode)
        self.positions: dict[str, PositionMFStrict] = {}

        self.profit_take_level = self.cfg.get("profit_take_level", 0.20)
        self.trailing_stop_pct = self.cfg.get("trailing_stop_pct", 0.20)
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.10)
        # 严格的放量倍数（默认 3x）
        self.volume_mult_strict = self.cfg.get("volume_mult_strict", 3.0)

    def _is_market_bearish(self, date) -> bool:
        """判断市场是否处于熊市环境：SPY <= SMA150"""
        spy_df = self.market_data.get("SPY")
        if spy_df is None or len(spy_df) < 150:
            return False
        spy_close = spy_df["close"]
        spy_sma150 = spy_close.rolling(150).mean()
        spy_ts = spy_df.index.searchsorted(date)
        spy_ts = min(spy_ts, len(spy_df) - 1)
        if spy_ts < 150:
            return False
        spy_current = float(spy_close.iloc[spy_ts])
        spy_sma_val = float(spy_sma150.iloc[spy_ts])
        return spy_current <= spy_sma_val

    def _check_entry(self, symbol, df, date):
        """入场逻辑：市场过滤 + 严格放量 + RS 过滤"""
        # ── 市场环境检查 ─────────────────────────────────
        if self._is_market_bearish(date):
            return None

        # ── 数据不足检查 ─────────────────────────────────
        need = self.sma_long + self.trend_lookback
        if len(df) < need:
            return None

        close_series = df["close"]
        current = float(close_series.iloc[-1])

        # ── 1. SMA150 上升趋势确认 ───────────────────────
        sma150 = close_series.rolling(self.sma_long).mean()
        sma_now = float(sma150.iloc[-1])
        sma_past = float(sma150.iloc[-self.trend_lookback])
        if sma_now <= sma_past:
            return None

        # ── 2. 价格在 SMA150 上方 ──────────────────────
        if current <= sma_now:
            return None

        # ── 3. 突破近期整理区最高价 ─────────────────────
        pivot = float(close_series.iloc[-(self.pivot_lookback + 1):-1].max())
        if current <= pivot * (1 + self.min_breakout_pct):
            return None

        # ── 4. 严格放量确认（3x）─────────────────────────
        avg_vol = float(df["volume"].iloc[-21:-1].mean())
        if avg_vol == 0:
            return None
        vol_ratio = float(df["volume"].iloc[-1]) / avg_vol
        if vol_ratio < self.volume_mult_strict:
            return None

        # ── RS 过滤 ──────────────────────────────────────
        rs_ok, rs_value = self._check_rs(symbol, df, date)
        threshold = self.cfg.get("rs_min_percentile", 90)
        if not rs_ok:
            return None

        breakout_pct = (current - pivot) / pivot
        stop_loss = round(current * (1 - self.stop_loss_pct), 2)
        reason = (
            f"[市场过滤+严格放量] SMA{self.sma_long}上升{self.trend_lookback}天 | "
            f"[突破] 超{self.pivot_lookback}日整理区高点${pivot:.2f}，"
            f"幅度+{breakout_pct*100:.1f}% | "
            f"[放量] {vol_ratio:.1f}x均量（严格3x）"
        )
        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=4, reason=reason, stop_loss=stop_loss,
        )

        if symbol not in self.positions:
            self.positions[symbol] = PositionMFStrict(
                symbol=symbol,
                entry_price=current,
                entry_date=date,
                highest_price=current,
            )
        return signal

    def _check_rs(self, symbol, df, date):
        """使用可配置的 rs_min_percentile 阈值"""
        rs_ok, rs_value = super()._check_rs(symbol, df, date)
        threshold = self.cfg.get("rs_min_percentile", 90)
        return rs_value >= threshold, rs_value

    def _check_exits(self, date):
        """出场逻辑：固定止损 10% + 涨超 20% 卖一半 + 追踪止盈 20%"""
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

            current_gain = (current_price / pos.entry_price - 1)

            # 1. 固定止损 10%
            fixed_stop = pos.entry_price * (1 - self.stop_loss_pct)
            if current_price <= fixed_stop:
                exit_reason = (
                    f"触发止损：入场${pos.entry_price:.2f}，当前${current_price:.2f}，"
                    f"跌幅{(current_price/pos.entry_price-1)*100:.1f}%"
                )
                sig = SignalEvent.create(
                    symbol=symbol, timestamp=date, direction="sell",
                    strength=3, reason=exit_reason, stop_loss=None,
                    shares=pos.shares,
                )
                signals.append(sig)
                to_close.append(symbol)
                continue

            # 2. 追踪止盈（已卖出一半时）
            trailing_stop = pos.highest_price * (1 - self.trailing_stop_pct)
            if current_price <= trailing_stop and getattr(pos, 'half_sold', False):
                gain = (pos.highest_price / pos.entry_price - 1) * 100
                exit_reason = (
                    f"追踪止盈（半仓）：最高${pos.highest_price:.2f}（+{gain:.1f}%），"
                    f"当前${current_price:.2f}，从最高点回落{self.trailing_stop_pct*100:.0f}%"
                )
                remaining_shares = pos.shares / 2 if pos.shares > 0 else "半仓"
                sig = SignalEvent.create(
                    symbol=symbol, timestamp=date, direction="sell",
                    strength=3, reason=exit_reason, stop_loss=None,
                    shares=remaining_shares,
                )
                signals.append(sig)
                to_close.append(symbol)
                continue

            # 3. 涨超 20% 时卖出一半
            if not getattr(pos, 'half_sold', False) and current_gain >= self.profit_take_level:
                pos.half_sold = True
                pos.first_tp_price = getattr(pos, 'first_tp_price', 0.0) or current_price
                gain = current_gain * 100
                exit_reason = (
                    f"分批止盈（卖出一半）：入场${pos.entry_price:.2f}，"
                    f"当前${current_price:.2f}（+{gain:.1f}%）"
                )
                half_shares = pos.shares / 2 if pos.shares > 0 else "半仓"
                sig = SignalEvent.create(
                    symbol=symbol, timestamp=date, direction="sell",
                    strength=3, reason=exit_reason, stop_loss=None,
                    shares=half_shares,
                )
                signals.append(sig)

        for symbol in to_close:
            if symbol in self.positions:
                del self.positions[symbol]

        return signals
