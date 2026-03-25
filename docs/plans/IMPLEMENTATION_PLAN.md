# 实施计划 — 事件驱动 SEPA 交易信号系统

> 本文档记录完整的建设计划，每次中断后从这里继续。
> 当前进度：Phase 0 已完成，即将开始 Phase 1。

---

## 已确认的策略参数（Phase 0 产出）

### 策略：Minervini SEPA（趋势模板 + 枢轴点突破）

**进场条件（11 条，全部满足才买入）**

| # | 条件 | 参数名 | 默认值 |
|---|------|--------|--------|
| 1 | 收盘价 > SMA50 | `sma_short` | 50 |
| 2 | 收盘价 > SMA150 | `sma_mid` | 150 |
| 3 | 收盘价 > SMA200 | `sma_long` | 200 |
| 4 | SMA50 > SMA150 > SMA200（多头排列） | — | — |
| 5 | SMA150 > SMA200 | — | — |
| 6 | SMA200 当前值 > 20交易日前的值 | `trend_lookback` | 20 |
| 7 | 收盘价 ≥ 52周低点 × 1.25 | `low_52w_mult` | 1.25 |
| 8 | 收盘价 ≥ 52周高点 × 0.75 | `high_52w_mult` | 0.75 |
| 9 | RS（相对强度）≥ 70 百分位 | `rs_min_percentile` | 70 |
| 10 | 收盘价突破过去30天局部高点，幅度 > 0.5% | `pivot_lookback: 30`, `min_breakout_pct: 0.005` | — |
| 11 | 当日成交量 ≥ 20日均量 × 1.5 | `volume_mult` | 1.5 |

**出场条件（满足任一即出场）**

| 类型 | 规则 | 参数 |
|------|------|------|
| 固定止损 | 收盘价跌破入场价 × (1 - 10%) | `stop_loss_pct: 0.10` |
| 追踪止盈 | 从持仓最高价回落超过 20% | `trailing_stop_pct: 0.20` |
| 时间止损 | 持仓 > 20天且盈利不足 3% | `time_stop_days: 20`, `time_stop_min_gain: 0.03` |

**股票池方案**

- 来源 A（自动）：Alpaca 新闻 API；首次抓取过去 365 天，之后每天滚动更新前1天；超过 365 天未被提及的自动移出
- 来源 B（手动）：`config.yaml` 中的 `manual_universe` 列表，用户手动维护 Barron's 看到的股票
- 合并规则：两个列表取并集，去重

---

## 项目目录结构（最终形态）

```
事件驱动克劳德/
├── CLAUDE.md                     ← 主指令（已存在）
├── SYSTEM_SPEC.md                ← 系统说明（已存在）
├── STRATEGY_PROTOCOL.md          ← 策略协议（已存在）
│
├── docs/
│   └── plans/
│       └── IMPLEMENTATION_PLAN.md ← 本文件
│
└── signal_system/                ← 所有代码在这里
    ├── config.yaml               ← 所有参数（Step 1）
    ├── main.py                   ← CLI 入口（最后写）
    │
    ├── universe/
    │   ├── __init__.py
    │   ├── alpaca_fetcher.py     ← Alpaca 新闻 API（Step 2b）
    │   └── manager.py            ← 合并 A+B 列表，管理缓存（Step 2b）
    │
    ├── data/
    │   ├── __init__.py
    │   └── fetcher.py            ← yfinance 历史数据获取（Step 2）
    │
    ├── events/
    │   ├── __init__.py
    │   ├── base.py               ← 事件基类（Step 3）
    │   └── queue.py              ← 事件总线（Step 3）
    │
    ├── strategy/
    │   ├── __init__.py
    │   └── sepa_minervini.py     ← SEPA 策略逻辑（Step 4）
    │
    ├── signals/
    │   ├── __init__.py
    │   └── generator.py          ← 信号生成 + 格式化输出（Step 5）
    │
    ├── backtest/
    │   ├── __init__.py
    │   └── engine.py             ← 回测引擎（Phase 2）
    │
    └── output/
        └── signals.csv           ← 自动生成，不提交
```

---

## Phase 1 建设步骤（当前阶段）

### Step 1：项目骨架 + 配置文件
**状态：未开始**

要做的事：
1. 创建 `signal_system/` 及所有子目录
2. 创建所有 `__init__.py`（空文件，让 Python 认识这些目录）
3. 创建 `config.yaml`，写入所有已确认的参数
4. 创建 `requirements.txt`，列出所有依赖

依赖清单：
```
yfinance>=0.2.40      # 股票历史数据
alpaca-trade-api>=3.0 # 或 alpaca-py，用于新闻 API
pandas>=2.0           # 数据处理
numpy>=1.26           # 数值计算
pyyaml>=6.0           # 读取 config.yaml
requests>=2.31        # HTTP 请求
```

完成标志：`python -c "import yfinance, pandas, yaml"` 不报错

---

### Step 2：数据获取模块（`data/fetcher.py`）
**状态：未开始**

要做的事：
- `DataFetcher` 类，接受股票代码列表 + 天数
- 调用 `yfinance` 下载日线 OHLCV 数据（开盘、最高、最低、收盘、成交量）
- 本地缓存：已下载的数据存到 `data/cache/`，避免重复请求

关键函数：
```python
def fetch(symbols: list[str], history_days: int) -> dict[str, pd.DataFrame]
```

完成标志：运行后打印 AAPL 最近 5 条数据，格式正确

---

### Step 2b：股票池模块（`universe/`）
**状态：未开始**

要做的事：

**`alpaca_fetcher.py`**
- 连接 Alpaca 新闻 API（需要免费账号，申请地址：alpaca.markets）
- `fetch_initial(lookback_days=365)`：首次运行，抓取过去1年
- `fetch_incremental()`：后续运行，只抓昨天的新闻
- 从新闻的 `symbols` 字段直接拿股票代码（不需要文本解析）

**`manager.py`**
- 读取 `config.yaml` 中的 `manual_universe`
- 读取/写入缓存文件 `data/universe_cache.json`
- 格式：`{"NVDA": {"last_mentioned": "2026-03-03"}, ...}`
- 过滤：移除超过 `max_age_days`（365天）未被提及的股票
- `get_universe() -> list[str]`：返回 A ∪ B 的并集

**注意**：Alpaca 免费账号需要申请 API Key。如果用户尚未申请，`alpaca_fetcher.py` 应优雅降级——打印提示，只使用手动列表继续运行，不崩溃。

完成标志：`manager.get_universe()` 返回包含手动列表的股票代码列表

---

### Step 3：事件总线（`events/`）
**状态：未开始**

要做的事：

**`base.py`** — 定义事件类型
```python
class EventType(Enum):
    BAR = "bar"           # 新的K线数据到来
    SIGNAL = "signal"     # 策略产生信号
    ORDER = "order"       # （预留，Phase 3用）

class Event:
    type: EventType
    data: dict
    timestamp: datetime
```

**`queue.py`** — 事件总线
```python
class EventQueue:
    def put(event: Event)
    def get() -> Event
    def empty() -> bool
```

这是整个系统的"神经中枢"。数据模块往里放 BAR 事件，策略模块从里面取，处理完放 SIGNAL 事件，信号模块再取出来输出。

完成标志：能创建一个 BAR 事件放入队列，再取出来，数据完整

---

### Step 4：SEPA 策略模块（`strategy/sepa_minervini.py`）
**状态：未开始**

要做的事：
- `SEPAStrategy` 类，从事件队列接收 BAR 事件
- 针对每条 BAR 数据，计算所有指标：SMA50/150/200，52周高低点，RS排名
- 检查 11 个进场条件
- 检查 3 个出场条件（需要维护持仓状态）
- 生成 SIGNAL 事件，包含：信号类型、强度、触发原因、止损价

关键设计：策略类不知道自己是在回测还是实盘，它只从事件队列取事件、往队列放事件。

完成标志：给定一段 NVDA 历史数据，能正确识别出至少一个买入信号

---

### Step 5：信号输出模块（`signals/generator.py`）
**状态：未开始**

要做的事：
- 从事件队列接收 SIGNAL 事件
- 格式化输出表格（如 SYSTEM_SPEC.md 中的格式）
- 打印到控制台（如果 `config.yaml` 中 `print_to_console: true`）
- 追加写入 `output/signals.csv`（如果 `save_to_csv: true`）

完成标志：运行后在控制台看到格式正确的信号表，同时 CSV 文件有对应记录

---

### Step 6：main.py CLI 入口
**状态：未开始**

要做的事：
- 解析命令行参数：`--mode [backtest|live]`，`--start`，`--end`
- 读取 `config.yaml`
- 初始化所有模块，连接事件队列
- 协调整个流水线运行

**回测模式**：按时间顺序逐条喂历史数据到事件队列
**实盘模式**：只喂最新一天的数据

完成标志：
```bash
# 两个命令都能无错误运行
python main.py --mode live
python main.py --mode backtest --start 2023-01-01 --end 2023-12-31
```

---

## Phase 2 回测引擎（Step 6 之后）

**状态：已完成**

### 实现内容（`backtest/engine.py`）

**核心数据结构：**
- `Trade` dataclass：记录一笔完整交易（symbol、买入日期/价格、卖出日期/价格、盈亏百分比、出场原因）
- `BacktestResult` dataclass：回测结果容器，包含所有 Trade 记录 + 汇总指标 + 净值曲线

**BacktestEngine 工作流程：**
1. 下载历史数据（测试区间 + 300天预热，供 SMA200 计算）
2. 逐日调用 `SEPAStrategy.run_date()`，收集产生的 buy/sell 信号
3. buy 信号 → 新建 Trade，记录当日收盘价为入场价
4. sell 信号 → 关闭对应 Trade，记录当日收盘价为出场价
5. 回测结束时仍未平仓的头寸以最后一日收盘价**强制平仓**（标注原因）
6. 构建每日净值曲线（等权重持仓：当日活跃头寸日收益率的均值）
7. 从净值曲线计算最大回撤、年化收益、夏普比率

**计算的 6 项指标：**
| 指标 | 及格线 | 计算方法 |
|------|--------|---------|
| 胜率 | > 40% | 盈利笔数 / 总笔数 |
| 盈亏比 | > 1.5 | 平均盈利 / 平均亏损（绝对值） |
| 最大回撤 | < 25% | `(equity - equity.cummax()) / cummax` 的最小值 |
| 每月信号数 | 2~10 | 总交易笔数 / 总月数 |
| 年化收益 | > 15% | `(总收益 + 1)^(365.25/天数) - 1` |
| 夏普比率 | > 1.0 | 日收益均值 / 日收益标准差 × √252（假设无风险利率=0） |

**`--split` 参数：**
- 自动将测试区间按 2:1 拆分为样本内（前2/3）和样本外 OOS（后1/3）
- 分别独立运行两次回测，分别打印报告
- 目的：验证策略不是过拟合（样本内表现好但 OOS 失效）

```bash
# 完整测试（推荐按 STRATEGY_PROTOCOL.md 要求使用的区间）
uv run python main.py --mode backtest --start 2019-01-01 --end 2024-12-31 --split

# 单段测试
uv run python main.py --mode backtest --start 2025-01-01 --end 2025-12-31
```

### RS 数据泄漏修复（Phase 2 准备工作）

回测引擎正式运行前，发现并修复了策略中的一个数据泄漏 bug：

**问题**：`_check_rs()` 在计算相对强度排名时，对比其他股票用的是 `other_df["close"].iloc[-1]`，
在回测中这会拿到**完整历史数据的最后一价**（未来数据），而非当前回测日期的价格。

**修复**：给 `_check_rs()` 增加 `date` 参数，对每只对比股票先调用 `_slice_to_date(other_df, date)` 截断到当前日期，再计算收益率。

**影响**：不修复的话，回测中的 RS 排名会用到未来数据，导致回测结果虚高（看起来比实际好）。

### 2025 年实测结果（5只股票）

```
股票池：AAPL, MSFT, NVDA, META, GOOGL
测试区间：2025-01-01 至 2025-12-31

总交易笔数：3 笔
胜率：33.3%       最大回撤：10.7%   每月信号：0.3
盈亏比：1.32      年化收益：7.4%    夏普比率：0.44

交易记录：
  META   2025-06-27 → 2025-10-31  $732.54 → $647.82   -11.6%（止损出场）
  NVDA   2025-10-28 → 2025-11-20  $201.02 → $180.63   -10.1%（止损出场）
  GOOGL  2025-10-29 → 2025-12-31  $274.39 → $313.85   +14.4%（回测结束强制平仓）
```

**主要结论：以 5 只大盘股测试，最大瓶颈是信号太少（每月 0.3 个），统计意义不足。**
SEPA 策略设计用于更大的成长股池（数十只），而非 5 只成熟大盘股。
需要扩大股票池才能得到有意义的统计结果。

测试区间（按 STRATEGY_PROTOCOL.md 要求，待扩大股票池后正式运行）：
- 样本内：2019-01-01 至 2022-12-31（牛市 + 新冠暴跌 + 熊市）
- 样本外（OOS）：2023-01-01 至 2024-12-31（考试用，不调参数）

---

## Phase 3 优化（Phase 2 完成后）

候选优化方向（等看到回测结果后再决定）：
1. 加入 VCP 形态自动识别（波动收缩次数检测）
2. 加入市场整体趋势过滤（如标普500在200日均线上方才允许买入）
3. 调整 RS 排名阈值或回看周期
4. 加入盈利加速出场（若盈利超过20%，改用更紧的追踪止损）

---

## 当前进度

- [x] Phase 0：策略研究确认（SEPA + Minervini）
- [x] 股票池方案确认（Alpaca API + 手动列表）
- [x] 全部策略参数确认
- [x] Phase 1 Step 1：项目骨架 + config.yaml + requirements.txt
- [x] Phase 1 Step 2：数据获取模块（直接调用 Yahoo Finance v8 API）
- [x] Phase 1 Step 2b：股票池模块（Alpaca 新闻 + 手动列表并集）
- [x] Phase 1 Step 3：事件总线（BarEvent / SignalEvent / EventQueue）
- [x] Phase 1 Step 4：SEPA 策略模块（11个进场条件 + 3个出场条件）
- [x] Phase 1 Step 5：信号输出模块（控制台表格 + CSV）
- [x] Phase 1 Step 6：main.py CLI 入口（`--mode live/backtest`）
- [x] **Phase 2：回测引擎 + 回测报告**（`backtest/engine.py`，`--split` 样本内/外）
- [ ] Phase 3：优化迭代  ← 下一步

---

## 重要技术决策记录

### 数据获取：不使用 yfinance，直接调用 Yahoo Finance v8 API

**原因**：yfinance 1.x 需要先获取 cookie/crumb 令牌，这个步骤频繁触发 429 限流。
直接调用 `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d`
更稳定，不需要 cookie 认证，只需要简单的 User-Agent header。

**关键代码**：`data/fetcher.py` 中的 `_download_from_api()` 函数。

### Alpaca 新闻 API 数据结构

Alpaca `NewsSet` 的数据在 `news_set.data['news']`（不是 `news_set.news`）。

### 回测净值曲线：等权重持仓法

**问题**：回测引擎需要每日净值曲线来计算最大回撤和夏普比率，但系统没有仓位管理（不知道每笔买入用多少钱）。

**决策**：使用**等权重法**——每天的组合日收益率 = 当日所有活跃持仓的日收益率均值；无持仓的交易日收益率 = 0（即现金不产生收益）。

**原因**：这是在没有仓位管理的情况下最透明、最无偏的方法。每个持仓被视为"等额投入"，不做任何仓位权重假设。

**局限**：真实交易中，信号同时出现时无法每个都买相同金额；这个数字仅用于横向比较不同参数配置，而非精确预测实际收益。

### RS 数据泄漏修复

见 Phase 2 章节的详细记录。关键：在事件驱动回测中，每次调用 `_slice_to_date(df, current_date)` 前都需要意识到对比数据是否也做了截断，否则会悄无声息地用到未来数据。

---

## 每次新会话开始时的恢复步骤

1. 读取本文件（`docs/plans/IMPLEMENTATION_PLAN.md`），找到"当前进度"中第一个未完成项
2. 读取 `CLAUDE.md`、`SYSTEM_SPEC.md`、`STRATEGY_PROTOCOL.md`
3. 检查 `signal_system/` 目录下已有哪些文件
4. 从上次中断的步骤继续，不重复已完成的工作

---

*最后更新：2026-03-03（Phase 2 完成）*
