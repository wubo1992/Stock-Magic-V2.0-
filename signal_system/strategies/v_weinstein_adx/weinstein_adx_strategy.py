"""
strategies/v_weinstein_adx/weinstein_adx_strategy.py — Weinstein Stage 2 + ADX 增强版

在 Weinstein Stage 2 策略基础上，增加：
  1. ADX(14) > 35（确认趋势强度足够）
  2. RSI(14) < 85（避免过度超买）
  3. 熊市止损加强：SPY 低于 SMA150 时入场，止损收紧到 5%（默认 7%）

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

    def _is_spy_bear(self, date) -> bool:
        """判断 SPY 是否处于熊市环境（低于 SMA150）。"""
        spy_df = self.market_data.get("SPY")
        if spy_df is None or len(spy_df) < 150:
            return False
        spy_close = spy_df["close"]
        spy_sma150 = spy_close.rolling(150).mean()
        spy_ts = spy_df.index.searchsorted(date)
        spy_ts = min(spy_ts, len(spy_df) - 1)
        if spy_ts < 149:
            return False
        spy_current = float(spy_close.iloc[spy_ts])
        spy_sma_val = float(spy_sma150.iloc[spy_ts])
        return spy_current <= spy_sma_val

    def _effective_stop_loss(self, date) -> float:
        """返回当日有效止损比例：熊市时收紧到 spy_bear_stop_loss。"""
        spy_bear_stop = self.cfg.get("spy_bear_stop_loss")
        if spy_bear_stop is not None and self._is_spy_bear(date):
            return spy_bear_stop
        return self.stop_loss_pct

    def _check_entry(self, symbol, df, date):
        # 数据不足时跳过（继承父类需求 + ADX 需要额外数据）
        need = max(self.sma_long + self.trend_lookback, 20 + 14)
        if len(df) < need:
            return None

        close_series = df["close"]
        current = float(close_series.iloc[-1])

        # ── 1. 继承 Weinstein Stage 2 条件 ──────────────────────────
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

        # ── 2. 收盘价 > 20 EMA（短期趋势确认）──────────────────────
        ema_20 = close_series.ewm(span=20, adjust=False).mean().iloc[-1]
        if current <= ema_20:
            return None

        # ── 3. RSI(14) <= rsi_max（避免过度超买）────────────
        rsi_max = self.cfg.get("rsi_max", 80)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs))
        rsi_14 = float(rsi_14.iloc[-1])
        if rsi_14 > rsi_max:
            return None

        # ── 4. ADX(14) > adx_threshold（趋势强度确认）────────
        adx_threshold = self.cfg.get("adx_threshold", 30)
        adx_value = self._calc_adx(df, period=14)
        if adx_value <= adx_threshold:
            return None

        # ── 5. 市场整体趋势过滤：SPY 在 SMA200 上方才入场（可选）──
        market_filter_enabled = self.cfg.get("market_filter", False)
        spy_sma_val = None
        if market_filter_enabled:
            spy_df = self.market_data.get("SPY")
            if spy_df is not None and len(spy_df) >= 200:
                spy_close = spy_df["close"]
                spy_sma200 = spy_close.rolling(200).mean()
                spy_ts = spy_df.index.searchsorted(date)
                spy_ts = min(spy_ts, len(spy_df) - 1)
                if spy_ts >= 199:
                    spy_current = float(spy_close.iloc[spy_ts])
                    spy_sma_val = float(spy_sma200.iloc[spy_ts])
                    if spy_current <= spy_sma_val:
                        return None

        # ── 熊市检测（影响止损，不影响是否入场）────────────
        spy_in_bear = self._is_spy_bear(date)
        effective_sl = self._effective_stop_loss(date)

        # ── 信号生成 ─────────────────────────────────────────────────
        breakout_pct = (current - pivot) / pivot
        strength = 4
        stop_loss = round(current * (1 - effective_sl), 2)
        spy_info = ""
        if market_filter_enabled and spy_sma_val is not None:
            spy_info = f"[SPY市场过滤] SPY>{spy_sma_val:.0f}均线 | "
        bear_info = ""
        if spy_in_bear:
            bear_info = f"[熊市止损收紧] SPY<SMA150，止损{self.stop_loss_pct*100:.0f}%→{effective_sl*100:.0f}% | "
        reason = (
            f"[Stage2] SMA{self.sma_long}({sma_now:.0f})上升{self.trend_lookback}天 | "
            f"[突破] 超{self.pivot_lookback}日整理区高点${pivot:.2f}，幅度+{breakout_pct*100:.1f}% | "
            f"[20EMA] 收于20EMA${ema_20:.2f}上方 | "
            f"[RSI] {rsi_14:.1f}<{rsi_max}，无超买 | "
            f"[ADX] {adx_value:.1f}>{adx_threshold}，趋势确认 | "
            f"{spy_info}{bear_info}[量能] {vol_ratio:.1f}x均量"
        )
        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )
        # 自动建立持仓记录，熊市入场时打标记
        if symbol not in self.positions:
            from strategies.v1_wizard.sepa_minervini import Position
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=current,
                entry_date=date,
                highest_price=current,
                bear_market=spy_in_bear,
            )
        return signal

    def _check_exits(self, date):
        """
        出场检查：熊市入场的持仓使用更紧的止损（5% vs 7%）。
        复用了 SEPAStrategy 的标准出场逻辑（固定止损→追踪止盈→时间止损），
        仅把固定止损的比例替换为 _effective_stop_loss() 的结果。
        """
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

            current_gain = (current_price / pos.entry_price - 1)
            exit_reason = None

            # ── 固定止损检查（使用熊市收紧止损）────────────────────
            effective_sl = self._effective_stop_loss(pos.entry_date)
            fixed_stop = pos.entry_price * (1 - effective_sl)
            if current_price <= fixed_stop:
                shares_to_sell = pos.shares if pos.shares > 0 else "全仓"
                exit_reason = (
                    f"触发止损：入场${pos.entry_price:.2f}，当前${current_price:.2f}，"
                    f"跌幅{(current_price/pos.entry_price-1)*100:.1f}%"
                    + (f" [熊市{effective_sl*100:.0f}%止损]" if pos.bear_market else "")
                )
                sig = SignalEvent.create(
                    symbol=symbol, timestamp=date, direction="sell",
                    strength=3, reason=exit_reason, stop_loss=None,
                    shares=pos.shares,
                )
                signals.append(sig)
                to_close.append(symbol)
                continue

            # ── 追踪止盈检查（不变）──────────────────────────────
            if pos.highest_price > pos.entry_price:
                trailing_stop = pos.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop:
                    gain = (pos.highest_price / pos.entry_price - 1) * 100
                    shares_to_sell = pos.shares if pos.shares > 0 else "全仓"
                    exit_reason = (
                        f"追踪止盈：最高${pos.highest_price:.2f}（+{gain:.1f}%），"
                        f"当前${current_price:.2f}，从最高点回落{self.trailing_stop_pct*100:.0f}%"
                    )
                    sig = SignalEvent.create(
                        symbol=symbol, timestamp=date, direction="sell",
                        strength=3, reason=exit_reason, stop_loss=None,
                        shares=pos.shares,
                    )
                    signals.append(sig)
                    to_close.append(symbol)
                    continue

            # ── 时间止损检查（不变）──────────────────────────────
            if pos.days_held >= self.time_stop_days:
                if current_gain < self.time_stop_min_gain:
                    shares_to_sell = pos.shares if pos.shares > 0 else "全仓"
                    exit_reason = (
                        f"时间止损：持仓{pos.days_held}天，盈利仅{current_gain*100:.1f}%"
                    )
                    sig = SignalEvent.create(
                        symbol=symbol, timestamp=date, direction="sell",
                        strength=3, reason=exit_reason, stop_loss=None,
                        shares=pos.shares,
                    )
                    signals.append(sig)
                    to_close.append(symbol)

        # 清理已完全卖出的持仓
        for symbol in to_close:
            if symbol in self.positions:
                del self.positions[symbol]

        return signals

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
