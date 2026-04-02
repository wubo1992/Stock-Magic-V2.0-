"""
strategies/v_adx50/adx50_strategy.py — ADX50 动量突破策略

买入条件：收盘价 > 50日最高价 且 ADX(14) > 25 且 RS 排名 >= 70%
止损：亏损 -10%
止盈：盈利 +20%
"""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
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
        # RS 计算缓存：{date_key: {market: {"scores": np.array, "symbols": list}}}
        self._rs_cache: dict[str, dict[str, dict] | None] = {}
        # ADX 缓存：{date_key: {symbol: adx_value}}
        self._adx_cache: dict[str, dict[str, float | None]] = {}

        # 固定 RS 股票池：只用 UNIVERSE.md 中的股票，避免每日浮动影响百分位
        try:
            from universe.manager import _read_universe_md
            self._universe_symbols: set[str] = set(_read_universe_md())
        except Exception:
            self._universe_symbols: set[str] = set()

        self.high_lookback = self.cfg.get("high_lookback", 50)
        self.adx_period = self.cfg.get("adx_period", 14)
        self.adx_threshold = self.cfg.get("adx_threshold", 25)
        self.stop_loss_pct = self.cfg.get("stop_loss_pct", 0.10)
        self.take_profit_pct = self.cfg.get("take_profit_pct", 0.20)
        self.rs_min_percentile = self.cfg.get("rs_min_percentile", 70)

    def run_date(self, date: datetime, queue: EventQueue) -> list[SignalEvent]:
        signals = []
        # 1. 出场检查
        exit_signals = self._check_exits(date)
        for sig in exit_signals:
            queue.put(sig)
            signals.append(sig)

        # 2. 每天批量计算所有股票的 ADX，缓存起来供入仓扫描使用
        date_key = date.date()
        if date_key not in self._adx_cache:
            self._adx_cache[date_key] = {}
            for symbol, df in self.market_data.items():
                df_sliced = self._slice_to_date(df, date)
                if len(df_sliced) < self.high_lookback + self.adx_period + 10:
                    self._adx_cache[date_key][symbol] = None
                else:
                    self._adx_cache[date_key][symbol] = self._compute_adx(df_sliced, self.adx_period)

        # 3. 入场扫描
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

        # 从缓存中取个股 ADX（每天按股票批量算好一次）
        date_key = date.date()
        adx_value = self._adx_cache.get(date_key, {}).get(symbol)
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

        # RS 过滤：相对强度排名
        rs_ok, rs_value = self._check_rs(symbol, df, date)
        if not rs_ok:
            return None

        # 计算突破幅度
        breakout_pct = (current_close - high_50) / high_50

        stop_loss = round(current_close * (1 - self.stop_loss_pct), 2)
        strength = 3
        reason = (
            f"[ADX50] 收盘价${current_close:.2f}突破{self.high_lookback}日高点${high_50:.2f}，"
            f"幅度+{breakout_pct*100:.1f}% | "
            f"[ADX{self.adx_period}]={adx_value:.1f}>{self.adx_threshold} | "
            f"[RS] 排名{rs_value:.0f}%"
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

    def _get_market(self, symbol: str) -> str:
        """根据股票代码判断所在市场。"""
        if symbol.endswith(".HK"):
            return "HK"
        elif symbol.endswith(".TW"):
            return "TW"
        else:
            return "US"

    def _check_rs(self, symbol: str, df: pd.DataFrame, date: datetime):
        """
        分市场RS评分 + 分市场各自排名。

        每个市场各自用基准ETF计算RS分数，然后在该市场内部排名百分位。
        美股基准：SPY；港股基准：ASHR；台股基准：EWT。
        """
        BENCHMARK_FOR_MARKET = {"US": "SPY", "HK": "ASHR", "TW": "EWT"}
        date_key = date.date()

        market = self._get_market(symbol)

        # 初始化每天的缓存结构
        if date_key not in self._rs_cache:
            self._rs_cache[date_key] = {}

        market_cache = self._rs_cache[date_key]

        def period_return(sliced_df, periods):
            if sliced_df is None or len(sliced_df) < periods:
                return np.nan
            return float(sliced_df["close"].iloc[-1] / sliced_df["close"].iloc[-periods] - 1)

        # 该市场尚未缓存 → 一次性计算整个市场的RS分数
        if market not in market_cache:
            bench_sym = BENCHMARK_FOR_MARKET[market]
            bench_df = self.market_data.get(bench_sym)
            if bench_df is None:
                # 无基准ETF → fallback到池内排名
                return self._check_rs_legacy(symbol, df, date)

            bench_sliced = self._slice_to_date(bench_df, date)
            b252 = period_return(bench_sliced, 252)
            b126 = period_return(bench_sliced, 126)
            b60  = period_return(bench_sliced, 60)

            if any(np.isnan(x) or x == 0 for x in [b252, b126, b60]):
                return self._check_rs_legacy(symbol, df, date)

            scores = {}  # {symbol: rs_score}
            for sym, other_df in self.market_data.items():
                if self._get_market(sym) != market:
                    continue
                s = self._slice_to_date(other_df, date)
                s252 = period_return(s, 252)
                s126 = period_return(s, 126)
                s60  = period_return(s, 60)
                if any(np.isnan(x) for x in [s252, s126, s60]):
                    continue
                scores[sym] = (0.4 * (s252 / b252 - 1) +
                               0.3 * (s126 / b126 - 1) +
                               0.3 * (s60  / b60  - 1))

            if len(scores) < 2:
                market_cache[market] = {}
                return True, 50.0

            market_cache[market] = scores

        scores = market_cache[market]

        # 当前股票不在该市场 → 跳过
        if symbol not in scores:
            return False, 0.0

        rs_score = scores[symbol]
        # 只用 UNIVERSE.md 固定池计算百分位，避免每日股票数量波动影响排名
        universe_scores = [v for k, v in scores.items() if k in self._universe_symbols]
        if not universe_scores:
            universe_scores = list(scores.values())
        rs_percentile = float(np.mean([s <= rs_score for s in universe_scores]) * 100)
        # 美股 top 30%，港股台股放宽到 top 50%
        threshold = 70 if market == "US" else 50
        return rs_percentile >= threshold, rs_percentile

    def _check_rs_legacy(self, symbol: str, df: pd.DataFrame, date: datetime):
        """原来的RS计算方式（池内排名），仅作 fallback。"""
        lookback = min(252, len(df))
        if lookback < 20:
            return False, 0.0
        this_return = float(df["close"].iloc[-1] / df["close"].iloc[-lookback] - 1)
        date_key = date.date()
        if date_key not in self._rs_cache:
            self._rs_cache[date_key] = {}
        if "legacy" not in self._rs_cache[date_key]:
            all_returns = []
            for sym, other_df in self.market_data.items():
                if sym in ("SPY", "ASHR", "EWT"):
                    continue
                sliced = self._slice_to_date(other_df, date)
                if len(sliced) < lookback:
                    continue
                ret = float(sliced["close"].iloc[-1] / sliced["close"].iloc[-lookback] - 1)
                all_returns.append(ret)
            if len(all_returns) < 2:
                self._rs_cache[date_key]["legacy"] = None
            else:
                self._rs_cache[date_key]["legacy"] = np.array(all_returns)
        cached = self._rs_cache[date_key].get("legacy")
        if cached is None or len(cached) < 2:
            return True, 50.0
        rs_percentile = float(np.mean(cached <= this_return) * 100)
        market = self._get_market(symbol)
        threshold = 70 if market == "US" else 50
        return rs_percentile >= threshold, rs_percentile

    def _compute_adx(self, df: pd.DataFrame, period: int = 14) -> float | None:
        """
        纯 pandas 计算 ADX(period)。

        返回当前最新的 ADX 值，若数据不足或全为 NaN 则返回 None。
        使用 EWM 近似 Wilder smoothing（alpha = 1/period，业界标准近似）。
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

        # Wilder's smoothing via EWM（业界标准近似）
        alpha = 1.0 / period
        tr_smooth = tr.ewm(alpha=alpha, adjust=False).mean()
        plus_dm_smooth = plus_dm.ewm(alpha=alpha, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(alpha=alpha, adjust=False).mean()

        # Directional Indicators
        plus_di = (plus_dm_smooth / tr_smooth).where(tr_smooth > 0, 0.0) * 100
        minus_di = (minus_dm_smooth / tr_smooth).where(tr_smooth > 0, 0.0) * 100

        # DX
        di_sum = plus_di + minus_di
        dx = (abs(plus_di - minus_di) / di_sum).where(di_sum > 0, 0.0) * 100

        # ADX = Wilder smoothed DX
        adx_series = dx.ewm(alpha=alpha, adjust=False).mean()
        adx_value = adx_series.iloc[-1]

        if pd.isna(adx_value):
            return None
        return float(adx_value)
