"""
strategies/v_weinstein_adx/weinstein_adx_bullbear.py — 牛熊自适应版

在 WeinsteinADXStrategy 基础上增加：
  1. 市场环境检测：SPY > SMA150 → 牛市模式，SPY <= SMA150 → 熊市模式
  2. 牛市模式放宽 RSI 上限（<90）和 ADX 门槛（>25），缩短趋势确认期（20天）
  3. 熊市模式维持原参数（RSI<85, ADX>35, 确认30天）

对应 config.yaml 的 strategies.v_weinstein_bullbear 段。
"""

from events import SignalEvent
from strategies.v_weinstein_adx.weinstein_adx_strategy import WeinsteinADXStrategy


class WeinsteinADXBullBearStrategy(WeinsteinADXStrategy):
    strategy_id = "v_weinstein_bullbear"
    strategy_name = "Weinstein Stage 2 + ADX 牛熊自适应"

    def _is_spy_bull(self, date) -> bool:
        """判断 SPY 是否处于牛市环境（高于 SMA150 且 ADX > 20）。"""
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
        if spy_current <= spy_sma_val:
            return False
        # 额外确认：SPY 自身也有一定趋势强度（ADX > 20）
        spy_adx = self._calc_adx(spy_df.iloc[:spy_ts+1], period=14)
        return spy_adx > 20

    def _effective_params(self, date):
        """
        根据市场环境返回当日有效参数。
        牛市模式 → 放宽入场条件；熊市模式 → 收紧入场条件。
        """
        is_bull = self._is_spy_bull(date)

        # 趋势确认期：牛市短，熊市长
        trend_lookback = 20 if is_bull else self.cfg.get('trend_lookback_bear', 30)

        # RSI 上限：牛市宽松，熊市严格
        rsi_max = 90 if is_bull else self.cfg.get('rsi_max_bear', 85)

        # ADX 门槛：牛市降低，熊市保持
        adx_threshold = 25 if is_bull else self.cfg.get('adx_threshold_bear', 35)

        # 放量倍数：牛市降低门槛
        volume_mult = 1.2 if is_bull else self.cfg.get('volume_mult_bear', 1.5)

        return {
            'trend_lookback': trend_lookback,
            'rsi_max': rsi_max,
            'adx_threshold': adx_threshold,
            'volume_mult': volume_mult,
            'is_bull': is_bull,
        }

    def _check_entry(self, symbol, df, date):
        # 数据不足时跳过
        need = max(self.sma_long + 30, 20 + 14)  # 30天足够覆盖所有情况
        if len(df) < need:
            return None

        params = self._effective_params(date)
        close_series = df["close"]
        current = float(close_series.iloc[-1])

        # ── 1. SMA150 上升趋势确认 ─────────────────────────────
        sma150 = close_series.rolling(self.sma_long).mean()
        sma_now = float(sma150.iloc[-1])
        sma_past = float(sma150.iloc[-params['trend_lookback']])
        if sma_now <= sma_past:
            return None

        # ── 2. 当前价在 SMA150 上方 ─────────────────────────
        if current <= sma_now:
            return None

        # ── 3. 突破近期整理区最高价 ─────────────────────────
        pivot = float(close_series.iloc[-(self.pivot_lookback + 1):-1].max())
        if current <= pivot * (1 + self.min_breakout_pct):
            return None

        # ── 4. 放量确认 ─────────────────────────────────────
        avg_vol = float(df["volume"].iloc[-21:-1].mean())
        if avg_vol == 0:
            return None
        vol_ratio = float(df["volume"].iloc[-1]) / avg_vol
        if vol_ratio < params['volume_mult']:
            return None

        # ── 5. 收盘价 > 20 EMA（短期趋势确认）──────────────
        ema_20 = close_series.ewm(span=20, adjust=False).mean().iloc[-1]
        if current <= ema_20:
            return None

        # ── 6. RSI 过滤（牛熊不同）────────────────────────
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])
        if rsi_14 > params['rsi_max']:
            return None

        # ── 7. ADX 趋势确认（牛熊不同）─────────────────────
        adx_value = self._calc_adx(df, period=14)
        if adx_value <= params['adx_threshold']:
            return None

        # ── 信号生成 ─────────────────────────────────────────
        breakout_pct = (current - pivot) / pivot
        spy_in_bear = self._is_spy_bear(date)
        effective_sl = self._effective_stop_loss(date)
        strength = 4
        stop_loss = round(current * (1 - effective_sl), 2)

        mode_label = "【牛市模式】" if params['is_bull'] else "【熊市模式】"
        reason = (
            f"{mode_label}"
            f"[Stage2] SMA{self.sma_long}上升{params['trend_lookback']}天 | "
            f"[突破] 超{self.pivot_lookback}日整理区高点${pivot:.2f}，幅度+{breakout_pct*100:.1f}% | "
            f"[20EMA] 收于20EMA${ema_20:.2f}上方 | "
            f"[RSI] {rsi_14:.1f}<{params['rsi_max']} | "
            f"[ADX] {adx_value:.1f}>{params['adx_threshold']} | "
            f"[量能] {vol_ratio:.1f}x均量"
        )

        signal = SignalEvent.create(
            symbol=symbol, timestamp=date, direction="buy",
            strength=strength, reason=reason, stop_loss=stop_loss,
        )

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
