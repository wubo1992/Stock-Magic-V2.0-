"""
strategies/v_nextday/nextday_strategy.py — 次日开盘买卖策略

策略逻辑：
1. 收集所有现有策略的买入信号
2. 第二天开盘买入（$1000/只股票）
3. 持有1个交易日后，第二天开盘立刻卖出
4. 计算单日收益

这是一个独立的回测策略，用于验证"次日开盘买卖"的有效性。
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List
import pandas as pd
import numpy as np

from events import EventQueue, SignalEvent
from strategies.base import StrategyBase


class NextDayStrategy(StrategyBase):
    """
    次日开盘买卖策略

    规则：
    - 收集所有其他策略的买入信号
    - 第二天开盘买入（$1000/只）
    - 持有一天后，第二天开盘卖出
    - 计算收益
    """
    strategy_id = "v_nextday"
    strategy_name = "次日开盘买卖策略"

    # 每次买入金额 ($1000)
    BUY_AMOUNT = 1000

    def __init__(
        self,
        strategy_config: dict,
        market_data: dict[str, pd.DataFrame],
        live_mode: bool = False,
        all_strategies: list = None,  # 传入所有其他策略实例
    ) -> None:
        super().__init__(strategy_config, market_data)
        self.live_mode = live_mode
        self.all_strategies = all_strategies or []

        # 交易记录
        self.trades: List[dict] = []  # {'symbol': str, 'buy_date': datetime, 'sell_date': datetime, 'buy_price': float, 'sell_price': float, 'shares': float, 'pnl': float, 'pnl_pct': float}
        self.pending_entries: Dict[str, dict] = {}  # 等待次日买入的信号

    def run_date(self, date: datetime, queue: EventQueue) -> list[SignalEvent]:
        """逐日运行策略"""
        signals = []

        # 1. 检查是否有持仓需要卖出（持有一天后第二天开盘卖出）
        to_close = []
        for symbol, pending in list(self.pending_entries.items()):
            buy_date = pending['buy_date']
            # 检查是否持有一天了
            if self._is_next_trading_day(buy_date, date):
                # 卖出
                df = self.market_data.get(symbol)
                if df is not None:
                    df_to_date = self._slice_to_date(df, date)
                    if not df_to_date.empty:
                        sell_price = float(df_to_date['open'].iloc[0])  # 开盘卖出
                        buy_price = pending['buy_price']
                        shares = pending['shares']
                        pnl = (sell_price - buy_price) * shares
                        pnl_pct = (sell_price / buy_price - 1) * 100

                        trade = {
                            'symbol': symbol,
                            'buy_date': buy_date,
                            'sell_date': date,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'shares': shares,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'reason': pending.get('reason', '')
                        }
                        self.trades.append(trade)

                        # 生成卖出信号
                        sig = SignalEvent.create(
                            symbol=symbol, timestamp=date, direction="sell",
                            strength=3, reason=f"次日开盘卖出: 买入${buy_price:.2f}->卖出${sell_price:.2f} ({pnl_pct:+.2f}%)",
                            stop_loss=None,
                        )
                        signals.append(sig)
                        to_close.append(symbol)

        # 清理已卖出的
        for symbol in to_close:
            del self.pending_entries[symbol]

        # 2. 收集所有策略的买入信号
        buy_signals = []
        for strategy in self.all_strategies:
            # 临时设置持仓为空，避免重复
            original_positions = dict(strategy.positions)
            strategy.positions = {}

            # 运行策略获取信号
            sigs = strategy.run_date(date, queue)

            # 筛选买入信号
            for sig in sigs:
                if sig.direction == "buy" and sig.symbol not in self.pending_entries:
                    buy_signals.append(sig)

            # 恢复持仓
            strategy.positions = original_positions

        # 3. 记录买入信号，等待次日开盘买入
        for sig in buy_signals:
            df = self.market_data.get(sig.symbol)
            if df is not None:
                df_to_date = self._slice_to_date(df, date)
                if not df_to_date.empty:
                    # 记录信号，等待次日开盘买入
                    self.pending_entries[sig.symbol] = {
                        'buy_date': date,
                        'buy_price': float(df_to_date['open'].iloc[0]),  # 开盘价作为买入价
                        'shares': self.BUY_AMOUNT / float(df_to_date['open'].iloc[0]),
                        'reason': sig.reason,
                        'strength': sig.strength,
                    }

        # 4. 第二天开盘执行买入
        for symbol, pending in list(self.pending_entries.items()):
            buy_date = pending['buy_date']
            if self._is_next_trading_day(buy_date, date):
                # 执行买入
                df = self.market_data.get(symbol)
                if df is not None:
                    df_to_date = self._slice_to_date(df, date)
                    if not df_to_date.empty:
                        buy_price = float(df_to_date['open'].iloc[0])
                        shares = self.BUY_AMOUNT / buy_price

                        # 更新pending中的买入价和股数（使用实际开盘价）
                        pending['buy_price'] = buy_price
                        pending['shares'] = shares
                        pending['buy_date'] = date  # 更新实际买入日期

                        # 生成买入信号
                        sig = SignalEvent.create(
                            symbol=symbol, timestamp=date, direction="buy",
                            strength=pending.get('strength', 3),
                            reason=f"次日开盘买入: ${self.BUY_AMOUNT} @ ${buy_price:.2f}",
                            stop_loss=None,
                            shares=shares,
                        )
                        signals.append(sig)

        return signals

    def _is_next_trading_day(self, buy_date: datetime, current_date: datetime) -> bool:
        """判断是否是买入后的下一个交易日"""
        if buy_date.tzinfo is None:
            buy_date = buy_date.replace(tzinfo=timezone.utc)
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=timezone.utc)

        buy_date_only = buy_date.date()
        current_date_only = current_date.date()

        # 简单判断：至少过了一天
        return current_date_only > buy_date_only

    def _slice_to_date(self, df, date):
        """切片数据到指定日期"""
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        idx = df.index
        if idx.tzinfo is None:
            idx = idx.tz_localize("UTC")
            df = df.copy()
            df.index = idx
        return df[df.index <= date]

    def get_trades(self) -> List[dict]:
        """返回所有交易记录"""
        return self.trades

    def get_summary(self) -> dict:
        """返回策略汇总"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'total_pnl': 0,
            }

        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]

        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trades) * 100,
            'avg_pnl': np.mean([t['pnl'] for t in self.trades]),
            'avg_pnl_pct': np.mean([t['pnl_pct'] for t in self.trades]),
            'total_pnl': sum([t['pnl'] for t in self.trades]),
            'max_win': max([t['pnl'] for t in self.trades]) if wins else 0,
            'max_loss': min([t['pnl'] for t in self.trades]) if losses else 0,
        }

    def get_open_positions(self):
        """返回当前持仓"""
        return {symbol: {'shares': v['shares'], 'entry_price': v['buy_price']}
                for symbol, v in self.pending_entries.items()}
