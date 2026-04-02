"""
backtest_1500_rebalance.py — 固定金额 + 仓位再平衡回测

- 每笔买入 $1500（从 $1000 上调）
- 资金不足时：优先卖出收益最低的持仓，收益相同则卖出持仓最久的
- 利润再投资
"""
import re, yaml, json, pickle, sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '.')

# ── 读取美股 ──────────────────────────────────────────────────────────
us_stocks_set = set()
with open("UNIVERSE.md") as f:
    content = f.read()
for section in re.split(r"^## ", content, flags=re.MULTILINE):
    lines = section.split("\n")
    title = lines[0].strip()
    in_us = title.startswith("板块 S：") or title.startswith("板块 N：")
    if in_us:
        for line in lines:
            if line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and re.match(r"^[A-Z0-9]{1,6}(\.[A-Z0-9]{1,5})?$", parts[1]):
                    us_stocks_set.add(parts[1])
us_stocks = sorted(us_stocks_set)
print(f"[股票池] 美股共 {len(us_stocks)} 只")

# ── 加载配置和策略 ────────────────────────────────────────────────────
with open("config.yaml") as f:
    config = yaml.safe_load(f)

from strategies.registry import get_strategy
from backtest.engine import BacktestEngine, Trade, _ensure_utc, _get_close
from data.fetcher import fetch

strategy_cls = get_strategy("v_weinstein_adx")
strategy_config = config["strategies"]["v_weinstein_adx"]

# ── 固定金额参数 ──────────────────────────────────────────────────────
INITIAL_CAPITAL = 50_000.0
POSITION_SIZE   = 1_500.0    # 从 $1000 调到 $1500

print(f"[参数] 初始本金=${INITIAL_CAPITAL:,.0f}，每笔=${POSITION_SIZE:,.0f}")

# ── 自定义回测引擎（带再平衡）────────────────────────────────────────
class RebalanceBacktestEngine(BacktestEngine):
    """
    扩展 BacktestEngine：
    - 每笔买入 $1500
    - 现金不足时，先卖出收益最低的持仓（收益相同则持仓最久）
    """

    def run(self, verbose=True):
        total_days = (self.end_date - self.start_date).days + self.WARMUP_DAYS
        if verbose:
            print(f"  下载历史数据（{total_days} 天）...")

        market_data = fetch(self.symbols, history_days=total_days, end_date=self.end_date)
        if not market_data:
            raise RuntimeError("无法获取任何股票数据，回测中止。")

        # 确保基准 ETF 在 market_data 中
        for benchmark, syms in [("SPY", ["SPY"]), ("ASHR", ["ASHR"]), ("EWT", ["EWT"])]:
            if benchmark not in market_data:
                data = fetch(syms, history_days=total_days, end_date=self.end_date)
                if data and benchmark in data:
                    market_data[benchmark] = data[benchmark]

        ref_df = next(iter(market_data.values()))
        ref_index = ref_df.index
        if ref_index.tzinfo is None:
            ref_index = ref_index.tz_localize("UTC")

        trading_days = ref_index[
            (ref_index >= self.start_date) & (ref_index <= self.end_date)
        ]

        if verbose:
            print(f"  回测区间共 {len(trading_days)} 个交易日，开始逐日运行...")

        if getattr(self.strategy_cls, "strategy_id", None) == "v_trend_collection":
            from strategies.registry import STRATEGY_REGISTRY
            all_strategies = []
            for sid, cls in STRATEGY_REGISTRY.items():
                if sid not in ("v_adx50", "v_trend_collection"):
                    all_strategies.append(cls(self.strategy_config, market_data))
            strategy = self.strategy_cls(
                self.strategy_config, market_data, all_strategies=all_strategies
            )
        else:
            strategy = self.strategy_cls(self.strategy_config, market_data)

        from events import EventQueue
        queue = EventQueue()

        open_trades: dict[str, Trade] = {}
        all_trades: list[Trade] = []
        cash = float(self.initial_capital)
        active_positions: dict[str, dict] = {}  # symbol -> {shares, cost, entry_price, entry_date}

        # 每日记录（用于重建净值曲线）
        daily_records: list[dict] = []  # {date, cash, num_positions, pos_value, equity}

        # 预处理 market_data（tz-aware）
        sliced_data: dict[str, pd.DataFrame] = {}
        for sym, df in market_data.items():
            idx = df.index
            if idx.tzinfo is None:
                df = df.copy()
                df.index = idx.tz_localize("UTC")
            sliced_data[sym] = df

        rebalance_log = []

        for i, date in enumerate(trading_days):
            dt = date.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_date = dt.date()

            # ── 记录当日开盘前状态（用于净值曲线）───────────────────────
            pos_value = 0.0
            for sym, pos in active_positions.items():
                df = sliced_data.get(sym)
                if df is not None:
                    mask = df.index <= dt
                    if mask.sum() >= 1:
                        cur_price = float(df["close"][mask].iloc[-1])
                        pos_value += cur_price * pos['shares']

            daily_records.append({
                'date': dt,
                'cash': cash,
                'num_positions': len(active_positions),
                'pos_value': pos_value,
                'equity': cash + pos_value,
            })

            signals = strategy.run_date(dt, queue)

            for sig in signals:
                symbol = sig.symbol
                direction = sig.data["direction"]
                reason = sig.data.get("reason", "")
                strength = sig.data.get("strength", 0)

                if direction == "buy" and symbol not in open_trades:
                    entry_price = _get_close(market_data, symbol, dt, strategy)
                    if entry_price is None:
                        continue

                    needed = POSITION_SIZE

                    # ── 现金不足时：再平衡 ──────────────────────────────
                    while cash < needed and active_positions:
                        # 找出收益最低的持仓（收益相同则持仓最久）
                        def sort_key(item):
                            sym_, pos = item
                            current_value = float(sliced_data[sym_]["close"].loc[
                                sliced_data[sym_].index <= dt
                            ].iloc[-1]) * pos['shares']
                            pnl_pct = (current_value - pos['cost']) / pos['cost']
                            days_held = (dt.date() - _ensure_utc(pos['entry_date']).date()).days
                            return (pnl_pct, days_held)  # 收益低先卖，收益相同则持仓久先卖

                        worst_sym = min(active_positions.items(), key=sort_key)[0]
                        pos = active_positions[worst_sym]

                        # 当日收盘价平仓
                        df_sym = sliced_data[worst_sym]
                        mask = df_sym.index <= dt
                        exit_price = float(df_sym["close"][mask].iloc[-1])
                        pnl = (exit_price - pos['entry_price']) * pos['shares']
                        cash += pos['cost'] + pnl

                        rebalance_log.append({
                            'date': dt_date,
                            'symbol': worst_sym,
                            'entry_date': _ensure_utc(pos['entry_date']).date(),
                            'exit_date': dt_date,
                            'pnl_pct': pnl / pos['cost'],
                            'reason': 'rebalance_cash_short'
                        })

                        # 同步关闭 Trade 记录
                        if worst_sym in open_trades:
                            trade = open_trades.pop(worst_sym)
                            trade.close(dt, exit_price, "rebalance_cash_short")

                        del active_positions[worst_sym]

                    if cash < needed:
                        # 仍然不够，跳过此信号
                        if verbose:
                            print(f"  [WARN] {dt_date} 现金${cash:.0f}不足${needed:.0f}，跳过 {symbol}")
                        continue

                    # 执行买入
                    shares = POSITION_SIZE / entry_price
                    active_positions[symbol] = {
                        'shares': shares,
                        'cost': POSITION_SIZE,
                        'entry_price': entry_price,
                        'entry_date': dt,
                    }
                    cash -= POSITION_SIZE

                    trade = Trade(
                        symbol=symbol,
                        entry_date=dt,
                        entry_price=entry_price,
                        signal_strength=strength,
                        entry_reason=reason,
                    )
                    open_trades[symbol] = trade
                    all_trades.append(trade)

                elif direction == "sell" and symbol in open_trades:
                    exit_price = _get_close(market_data, symbol, dt, strategy)
                    if exit_price is None:
                        continue
                    trade = open_trades.pop(symbol)
                    trade.close(dt, exit_price, reason)

                    if symbol in active_positions:
                        pos = active_positions.pop(symbol)
                        pnl = (exit_price - trade.entry_price) * pos['shares']
                        cash += POSITION_SIZE + pnl

            # 进度
            if verbose and (i + 1) % 50 == 0:
                print(f"    进度：{i+1}/{len(trading_days)} 天")

        # 回测结束时未平仓：强制平仓
        for symbol, trade in list(open_trades.items()):
            exit_price = _get_close(market_data, symbol, self.end_date, strategy)
            if exit_price is not None:
                trade.close(self.end_date, exit_price, "回测结束强制平仓")
                pos = active_positions.pop(symbol)
                pnl = (exit_price - trade.entry_price) * pos['shares']
                cash += POSITION_SIZE + pnl

        # 更新最后一天的净值（回测结束，所有仓位已平）
        if len(daily_records) > 0:
            daily_records[-1] = {
                'date': daily_records[-1]['date'],
                'cash': cash,
                'num_positions': len(active_positions),
                'pos_value': 0.0,
                'equity': cash,
            }

        # ── 构建净值曲线（使用每日记录）────────────────────────────────
        equity_vals = [r['equity'] for r in daily_records]
        daily_position_counts = [r['num_positions'] for r in daily_records]

        equity = pd.Series(equity_vals, index=pd.DatetimeIndex([r['date'] for r in daily_records]))

        max_positions = max(daily_position_counts) if daily_position_counts else 0
        avg_positions = float(np.mean(daily_position_counts)) if daily_position_counts else 0.0
        peak_used = max_positions * POSITION_SIZE
        capital_usage_pct = round(peak_used / INITIAL_CAPITAL * 100, 1)

        # ── 计算指标 ───────────────────────────────────────────────────
        closed_trades = [t for t in all_trades if t.is_closed]
        metrics = self._calculate_metrics(closed_trades, equity)

        # ── 绩效报告 ───────────────────────────────────────────────────
        total_days_range = (self.end_date - self.start_date).days
        years = total_days_range / 365.25
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
        annualized = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        wins = [t for t in closed_trades if t.pnl_pct > 0]
        losses = [t for t in closed_trades if t.pnl_pct <= 0]
        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        avg_win_pct = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss_pct = abs(np.mean([t.pnl_pct for t in losses])) if losses else 1
        pl_ratio = (avg_win_pct * len(wins)) / (avg_loss_pct * len(losses)) if losses and len(losses) > 0 else 0

        cumulative_max = equity.cummax()
        drawdown = (equity - cumulative_max) / cumulative_max
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()

        daily_rets = equity.pct_change().dropna()
        sharpe = (daily_rets.mean() * 252 - 0.0) / (daily_rets.std() * np.sqrt(252)) if daily_rets.std() > 0 else 0

        monthly = defaultdict(int)
        for t in closed_trades:
            monthly[t.entry_date.strftime("%Y-%m")[:7]] += 1
        signals_per_month = np.mean(list(monthly.values())) if monthly else 0

        print(f"""
{'='*60}
  固定金额 $1500 + 再平衡回测报告
  测试区间：{self.start_date.date()} ~ {self.end_date.date()}
{'='*60}
  初始本金              ${INITIAL_CAPITAL:,.0f}
  每笔买入               ${POSITION_SIZE:,.0f}
  最终净值               ${equity.iloc[-1]:,.2f}
  总收益                 {total_return*100:+.1f}%
  年化收益               {annualized*100:+.1f}%
  最大回撤               {max_dd*100:.1f}%（{max_dd_date.date()}）
  夏普比率               {sharpe:.2f}
  胜率                   {win_rate*100:.1f}%（{len(wins)}胜/{len(losses)}负）
  盈亏比                 {pl_ratio:.2f}
  每月信号数             {signals_per_month:.1f}
  总交易笔数             {len(closed_trades)}
  峰值持仓               {max_positions} 股
  平均持仓               {avg_positions:.1f} 股
  资金使用峰值           {capital_usage_pct:.1f}%
  再平衡次数             {len(rebalance_log)}
{'='*60}
""")

        # 再平衡明细
        if rebalance_log:
            print(f"[再平衡明细] 共 {len(rebalance_log)} 次")
            print(f"{'日期':<12} {'股票':<8} {'买入日':<12} {'收益%':>8} {'原因'}")
            for r in rebalance_log[:20]:
                print(f"{str(r['date']):<12} {r['symbol']:<8} {str(r['entry_date']):<12} {r['pnl_pct']*100:>7.1f}%  {r['reason']}")
            if len(rebalance_log) > 20:
                print(f"  ... 还有 {len(rebalance_log)-20} 次")

        # ── 保存净值曲线 ──────────────────────────────────────────────
        records = []
        for i, d in enumerate(trading_days):
            records.append({
                'date': d.strftime('%Y-%m-%d'),
                'equity': float(equity.iloc[i]),
                'positions': daily_position_counts[i],
                'util_rate': round(daily_position_counts[i] * POSITION_SIZE / INITIAL_CAPITAL * 100, 1)
            })
        with open('/tmp/equity_1500_rebalance.json', 'w') as f:
            json.dump(records, f)

        return equity, closed_trades, {
            'max_positions': max_positions,
            'avg_positions': avg_positions,
            'capital_usage_pct': capital_usage_pct,
            'rebalance_count': len(rebalance_log),
            'win_rate': win_rate,
            'pl_ratio': pl_ratio,
            'annualized': annualized,
            'sharpe': sharpe,
            'max_dd': max_dd,
        }


# ── 运行回测（2020-2026）──────────────────────────────────────────────
engine = RebalanceBacktestEngine(
    config=config,
    strategy_cls=strategy_cls,
    strategy_config=strategy_config,
    symbols=us_stocks,
    start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2026, 3, 27, tzinfo=timezone.utc),
    strategy_id="v_weinstein_adx",
    position_size=POSITION_SIZE,
    initial_capital=INITIAL_CAPITAL,
)

equity, trades, metrics = engine.run(verbose=True)
print(f"\n[完成] 净值曲线已保存至 /tmp/equity_1500_rebalance.json")
