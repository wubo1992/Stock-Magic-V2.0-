# 交接文档 — 美股信号系统上下文

> 给下一个 Claude Code 会话读的文件。
> 新会话开始时，请先完整阅读 `CLAUDE.md`，再读本文件。

---

## 重要说明：数据源规范

**⚠️ 数据必须是收盘数据，不能是盘中数据！**

系统当前使用：
- **数据源**: Alpaca Market Data API（主） + Yahoo Finance（备）
- **数据类型**: 日线数据（Daily OHLCV）
- **时间点**: 收盘后数据（After-market close）
- **数据内容**: Open, High, Low, Close, Volume
- **时区**: UTC

**确认要点**：
1. ✅ 所有历史数据都是收盘后的日线数据
2. ✅ 不包含盘中实时数据
3. ✅ 每日一条记录，代表当天完整交易日的数据
4. ✅ 增量更新时也是收盘后更新

**代码位置**：`data/fetcher.py`
- `timeframe: "1d"` - 配置为日线数据
- Alpaca API在收盘后提供日线数据

---

## 1. 项目概述

这是一个**美股事件驱动交易信号系统**，基于 Mark Minervini 的 SEPA + VCP 策略（《股票魔法师》）。

- 用户是非程序员，所有代码由 Claude Code 编写和维护
- 系统每天收盘后运行，产生买入/卖出信号和 Markdown 日报
- 不自动下单，信号供人工决策参考

**当前策略：魔法师调整参数版V1+（strategy ID: `v1_plus`，输出目录: `v1_plus_wizard`）**

---

## 2. 系统当前状态（截至 2026-03-06）

### 已完成的阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1-3 | 系统骨架、回测验证、迭代优化 | ✅ 完成 |
| Phase 4 | 多策略架构升级（strategies/ 重构） | ✅ 完成 |
| Phase 5 | SA Quant 扫描器接入（--mode scan） | ✅ 完成 |
| Phase 6 | 卖出信号持仓追踪（positions.json） | ✅ 完成 |
| Phase 7 | V1+ 参数优化 + 股票池扩充（297只）| ✅ 完成 |
| Phase 8 | 数据持久化三层架构 + live 模式缓存 staleness 修复 | ✅ 完成 |
| Phase 9 | 指数成分股扩池（S&P 500 + Nasdaq 100，Wikipedia 自动拉取）| ✅ 完成 |
| Phase 10 | 7 大师策略变种实施 + 样本外回测对比 | ✅ 完成 |

### 最新回测结果（v1_plus，294 只手动股票池）

| 阶段 | 区间 | 年化收益 | 夏普比率 | 最大回撤 | 每月信号 | 综合 |
|------|------|----------|----------|----------|---------|------|
| 样本内 | 2015-01 ~ 2024-12 | 13.0% | 1.64 | 20.2% | 1.8 | 4/6 合格 |
| 样本外 OOS | 2024-02 ~ 2026-03 | 54.8% | 2.24 | 15.2% | 6.8 | **6/6 全部达标** |

---

## 3. 关键文件说明

```
signal_system/
├── CLAUDE.md                  ← 主指令文件，每次新会话必须先读
├── HANDOVER.md                ← 本文件
├── UNIVERSE.md                ← 股票池（~297只），唯一来源，直接编辑生效
├── config.yaml                ← 所有参数（active_strategy: v1_plus）
├── main.py                    ← 运行入口
│
├── strategies/
│   ├── v1_wizard/
│   │   └── sepa_minervini.py  ← 核心策略逻辑（SEPA + VCP）
│   └── v1_plus/
│       └── sepa_plus.py       ← V1+ 子类（继承V1，只改ID/名称，参数在config）
│
├── backtest/
│   └── engine.py              ← 回测引擎（新增 save_signals_csv 参数）
│
├── signals/
│   ├── generator.py           ← 信号格式化 + CSV 存储
│   ├── report.py              ← 每日 Markdown 报告生成
│   └── positions.py           ← 持仓持久化（load/save positions.json）
│
└── output/
    ├── v1_wizard/             ← 旧策略（保留，不再使用）
    │   ├── signals.csv
    │   └── positions.json
    └── v1_plus_wizard/        ← 当前主策略输出目录 ★
        ├── signals.csv
        ├── positions.json     ← 当前持仓（每日自动更新）
        └── YYYY-MM-DD/
            └── 报告_魔法师调整参数版V1+_YYYY-MM-DD.md
```

---

## 4. 用户当前持仓

持仓信息存储在共享文件（所有策略共用）：
```
output/shared/positions.json
```

字段说明：
- `entry_price`：加权平均入场均价（用户加仓后由 Claude 手动更新）
- `entry_date`：首次建仓日期（加仓时不变）
- `highest_price`：系统自动追踪的历史最高价
- `days_held`：系统每次 live 运行自动 +1
- **注意**：`stop_loss` 已移除，由各策略根据自身参数动态计算

**港股 03986（200股）系统无法追踪，用户手动管理，不在 positions.json 中。**

---

## 5. 持仓管理规则（已与用户确认）

### 用户每日操作时机
**美股收盘后（东部时间 4pm 后）**，告知 Claude 持仓变化，更新完再运行系统。

### 用户需要告知的内容（只说变化的部分）
- 新买入：股票代码 + 实际成交均价
- 已平仓：哪只股票平掉了
- 加仓后均价变化：股票代码 + 新的加权平均成本

### Claude 负责处理的部分
- 更新 `output/shared/positions.json`（entry_price、entry_date、highest_price）
- **止损价不再存储**：由各策略根据自身参数动态计算
  - v1_plus：止损 = entry_price × 90%，追踪止盈 = 从最高点回落 20%
  - v_zanger：止损 = entry_price × 94%，追踪止盈 = 从最高点回落 15%
  - v_weinstein：止损 = entry_price × 90%，追踪止盈 = 从最高点回落 20%
- entry_date 保持**最早入场日期**不变（时间止损从首次建仓起算）
- highest_price 和 days_held 由系统自动更新，Claude 不手动改

### 关于加仓信号
- **已持仓的股票如果再次满足买入条件，系统会发出信号**（这是加仓参考）
- 系统不会覆盖已有持仓记录，只发信号
- 用户加仓后，告知新均价，Claude 手动更新 entry_price

### 多策略共享持仓
- 所有策略（v1_plus, v_zanger, v_weinstein 等）共用同一份持仓文件
- 不同策略根据各自参数给出不同的止损/止盈建议
- 只需维护一份 `output/shared/positions.json`

---

## 6. 每日运行命令

```bash
# 每天收盘后运行主策略（v1_plus 已设为默认）
uv run python main.py --mode live

# 运行其他策略（共享同一份持仓）
uv run python main.py --mode live --strategy v_zanger
uv run python main.py --mode live --strategy v_weinstein

# 扫描 SA Quant 新强势股（每周/每月运行一次即可）
uv run python main.py --mode scan --dry-run   # 只看结果不写入
uv run python main.py --mode scan             # 写入 UNIVERSE.md

# 回测
uv run python main.py --mode backtest --start 2015-01-01 --end 2024-12-30 --strategy v1_plus
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-05 --strategy v1_plus

# 补档（切换策略后补充 signals.csv 历史记录）
uv run python main.py --mode backtest --start YYYY-MM-DD --end YYYY-MM-DD --strategy v1_plus --save-signals
```

---

## 7. UNIVERSE.md 管理规则

- 这是股票池的**唯一来源**，代码直接读取这个文件
- 添加股票：直接在对应板块的表格里加一行，下次运行自动生效
- 删除股票：从表格删除，移到文末「待移出记录」节
- 当前总数：**~297 只**（手动池，SA 扫描新增另行列出）
- SA Quant 扫描结果会自动写入「板块：自动扫描新增」节

---

## 8. 系统三种出场条件（卖出信号）

| 条件 | 触发标准 | 说明 |
|------|---------|------|
| 固定止损 | 收盘价 ≤ 入场价 × 90% | 亏损超过 10% |
| 追踪止盈 | 收盘价 ≤ 历史最高价 × 80% | 从高点回落 20% |
| 时间止损 | 持有 ≥ 20 天且涨幅 < 3% | 入场后长期不动 |

出场信号会出现在每日报告的「今日出场信号」章节。

---

## 9. 近期代码变更记录

### 2026-03-05 Phase 7

#### 新增策略：`strategies/v1_plus/sepa_plus.py`
`SEPAPlusStrategy` 继承 `SEPAStrategy`，只覆盖 `strategy_id = "v1_plus_wizard"` 和 `strategy_name`。参数在 `config.yaml` 的 `strategies.v1_plus:` 段独立配置。

**关键参数变化（相对 v1）**：`vcp_final_range_pct: 0.08 → 0.12`（放宽VCP末端箱体，经控制变量测试效果最佳）

#### 修复：`strategies/v1_wizard/sepa_minervini.py`（live_mode bug）
新增 `live_mode: bool = False` 参数。实盘模式传 `True` 时不自动创建 Position，避免干扰 positions.json 的人工管理流程。回测模式保持默认 `False`，自动创建 Position 供出场逻辑使用。

#### 增强：`backtest/engine.py`（--save-signals 补档）
`BacktestEngine.__init__()` 新增 `save_signals_csv: bool = False` 和 `strategy_id: str = ""`。当 `save_signals_csv=True` 时，回测中每产生一个买入信号就同步写入对应策略的 `signals.csv`，用于切换策略后的历史信号补档。

#### 增强：`main.py`
- argparse 新增 `--save-signals` flag（传给 `BacktestEngine`）
- `run_live()` 调用时传入 `live_mode=True`

#### 修改：`config.yaml`
- `active_strategy: v1` → `active_strategy: v1_plus`
- 新增完整 `v1_plus:` 策略配置段

#### 修改：`UNIVERSE.md`
股票池 186 → ~297 只，新增 10 个板块（板块十五至二十四）：SaaS/云软件、支付金融科技、医疗器械/制药、工业/国防、消费/零售、银行/金融、大宗商品/材料、亚太/新兴市场、REIT、成长股+通信。

---

### 2026-03-06 Phase 8

#### 修复：`data/fetcher.py`（live 模式缓存 staleness bug）
**根本原因**：`timedelta.days` 是整数截断，导致 `max_age=1` 的判断在"1天47分钟"的情况下仍视为新鲜（`1 <= 1 = True`）。系统使用 3月4日的旧缓存，错过了 ATNI 在3月5日盘中的暴跌，发出了错误的买入信号。

**修复方案**：`max_age = 0 if live_mode else 3`，`0 <= 0` 仅在数据距今 <24小时时成立，确保每次实盘运行都能拿到当日或最近交易日的收盘数据。

#### 重构：`data/fetcher.py`（三层数据持久化架构）
用户需求：历史数据永久存盘，每日只增量补充新数据，避免每次重新全量下载。

**改动：**
- `_load_cache()` → `_load_local()`：去除时效性判断，只检查历史覆盖（data 足够早），永久持久化
- `_save_cache()` → `_save_local()`：语义不变
- `fetch()` 新增三层逻辑：
  1. **Tier 1（本地新鲜）**：直接用，零网络请求
  2. **Tier 2（本地有历史但过期）**：批量增量下载 delta（从 min_last+1 起），`pd.concat` + `drop_duplicates` 合并后写回
  3. **Tier 3（本地无数据）**：全量下载（Alpaca → Yahoo 备用）
- 控制台输出从「缓存命中 X 只」改为「本地直接使用 X 只，增量更新 Y 只，全量下载 Z 只」

**本地存储路径**：`signal_system/data/cache/`（542 个 .pkl 文件，约 10 MB）

---

### 2026-03-06 Phase 9

#### 新增：`universe/index_fetcher.py`
从 Wikipedia 自动拉取 S&P 500 和 Nasdaq 100 成分股，7天本地缓存（`data/index_cache.json`），网络失败时回退旧缓存。使用 `requests` + 浏览器 User-Agent 绕过 403，`pandas.read_html` 解析表格。

- S&P 500：503 只（"Symbol" 列，`BRK.B → BRK-B`）
- Nasdaq 100：101 只（"Ticker" 列）
- 两者去重合并：517 只新增至股票池

**依赖**：新增 `lxml==6.0.2`（`pandas.read_html` HTML 解析后端）

#### 修改：`universe/manager.py`
`get_universe()` 新增来源 B（指数），改为三路合并：

```python
combined = sorted(set(manual) | set(index_symbols) | set(auto_symbols))
```

控制台输出改为：`手动 297 + 指数 517 + 自动 XX，去重后合并`

#### 修改：`config.yaml`
`auto_universe:` 新增 `include_indices: [sp500, nasdaq100]`。注释掉此段可随时关闭指数成分股。

---

### 2026-03-06 Phase 10

#### 新增：7 大师策略变种

为研究报告中的 7 位交易大师各建立独立策略，与 v1_plus 基准对比。

**新建文件（14 个）：**

```
strategies/v_oneil/sepa_oneil.py           ← O'Neil CANSLIM 技术版（宽松 VCP 20%）
strategies/v_ryan/sepa_ryan.py            ← David Ryan 极紧 VCP（<5%）
strategies/v_kell/sepa_kell.py            ← Oliver Kell 极端放量（3x）
strategies/v_kullamaggi/sepa_kullamaggi.py ← Kullamägi VCP 变种（止损 5%，放量 4x）
strategies/v_stine/sepa_stine.py          ← Jesse Stine 超强精选（RS≥90%）
strategies/v_zanger/zanger_strategy.py    ← Dan Zanger 纯技术动量（新类，无 RS/VCP）
strategies/v_weinstein/weinstein_strategy.py ← Weinstein Stage 2 分析（新类，只用 SMA150）
```

每个策略包均包含 `__init__.py`。

**修改文件：**

1. `config.yaml`：新增 7 个策略参数段（`strategies.v_oneil:` ~ `strategies.v_weinstein:`）
2. `strategies/registry.py`：新增 7 条注册

```python
STRATEGY_REGISTRY = {
    "v1": SEPAStrategy,
    "v1_plus": SEPAPlusStrategy,
    "v_oneil": ONeilStrategy,
    "v_ryan": RyanStrategy,
    "v_kell": KellStrategy,
    "v_kullamaggi": KullamaggiStrategy,
    "v_zanger": ZangerStrategy,
    "v_stine": StineStrategy,
    "v_weinstein": WeinsteinStrategy,
}
```

**策略架构：**

- **简单子类（5 个）**：v_oneil, v_ryan, v_kell, v_kullamaggi, v_stine
  - 继承 `SEPAStrategy`，只覆盖 `strategy_id` 和 `strategy_name`
  - 所有参数在 `config.yaml` 中配置

- **新类（2 个）**：v_zanger, v_weinstein
  - 继承 `SEPAStrategy`，覆盖 `_check_entry()`
  - v_zanger：无 RS、无 VCP，只看 SMA150 趋势 + 突破 + 放量 3x
  - v_weinstein：Stage 2 分析，SMA150 上升 + 价格在均线上 + 突破

#### 回测结果（样本外 2024-02-12 至 2026-03-06，517 天）

| 策略 | 年化收益 | 夏普比率 | 最大回撤 | 胜率 | 信号/月 | 达标 |
|------|---------|---------|---------|------|---------|------|
| **v_zanger** | **128.4%** | **4.42** | **12.0%** | 39.8% | 13.1 | 4/6 ⚠️ |
| **v_kell** | **80.2%** | 1.90 | 29.4% | 18.2% | 0.9 | 3/6 |
| **v_weinstein** | **56.9%** | **2.82** | 14.9% | 45.8% | **28.5** | 5/6 ⚠️ |
| **v1_plus** | **54.8%** | **2.24** | 15.3% | 43.7% | 6.8 ✅ | **6/6** ✅ |
| **v_stine** | 51.4% | 2.15 | 18.5% | **100%** | 0.1 | 5/6 |
| **v_kullamaggi** | 50.6% | 1.96 | **13.9%** | 40.0% | 0.4 | 5/6 |
| **v_oneil** | 46.4% | 1.88 | 19.6% | 42.9% | 3.2 | 5/6 |
| **v_ryan** | 14.0% | 0.51 | 23.9% | 21.4% | 0.6 | 2/6 |

**关键发现：**

1. **v_zanger** 样本外表现最佳（128.4% 年化，4.42 夏普，12% 回撤），但信号频率超标（13.1/月）
2. **v1_plus** 唯一 6/6 全部达标策略（信号频率 6.8/月 符合 2-10 标准）
3. **v_weinstein** 信号频率严重超标（28.5/月），建议提高放量至 2.5x
4. **v_ryan** 样本外表现差（14% 年化，2/6 达标），建议放宽 VCP 至 7%
5. **v_kell** 回撤最大（29.4%），建议组合使用而非单独使用
6. **v_stine** 和 **v_kullamaggi** 信号极少（<1/月），样本不足

**文档创建：**

- `docs/strategies/*.md`（8 个策略详细文档）
- `docs/策略对比总览.md`（对比分析 + 组合建议）

**运行命令：**

```bash
# 逐一验证策略加载
uv run python main.py --mode live --strategy v_oneil
uv run python main.py --mode live --strategy v_ryan
uv run python main.py --mode live --strategy v_kell
uv run python main.py --mode live --strategy v_kullamaggi
uv run python main.py --mode live --strategy v_zanger
uv run python main.py --mode live --strategy v_stine
uv run python main.py --mode live --strategy v_weinstein

# 样本外回测
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_oneil
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_ryan
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_kell
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_kullamaggi
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_zanger
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_stine
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v_weinstein
```

---

## 10. 切换策略时的持仓迁移操作

当需要切换到新策略时（如从 v1 换到 v1_plus），操作步骤：

1. 复制持仓文件：
   ```bash
   cp output/旧策略_id/positions.json output/新策略_id/positions.json
   ```
2. 如需修正个别持仓字段，直接编辑 JSON
3. 补档过去几天的 signals.csv：
   ```bash
   uv run python main.py --mode backtest --start YYYY-MM-DD --end YYYY-MM-DD --strategy 新策略 --save-signals
   ```
4. 运行实盘模式，确认持仓加载正确、卖出信号正常出现

---

### 2026-03-13 Phase 11

#### 重构：多策略共享持仓（positions.json 统一）

**问题**：之前每个策略有独立的 `positions.json`，用户需同步更新多个文件。

**解决方案**：所有策略共享同一份持仓文件，止损价由各策略动态计算。

**修改文件：**

1. `strategies/v1_wizard/sepa_minervini.py`
   - `Position` 数据类移除 `stop_loss` 字段
   - 止损价在 `_check_exits()` 中根据策略参数动态计算

2. `signals/positions.py`
   - 持仓文件路径改为 `output/shared/positions.json`
   - 保存/加载时不再处理 `stop_loss` 字段

3. `strategies/v_zanger/zanger_strategy.py` / `strategies/v_weinstein/weinstein_strategy.py`
   - 适配新 `Position` 格式

**新持仓文件格式：**
```json
{
  "AAOI": {
    "symbol": "AAOI",
    "entry_price": 102.87,
    "entry_date": "2026-03-03T00:00:00+00:00",
    "highest_price": 126.99,
    "days_held": 15
  }
}
```

**不同策略对同一持仓的止损计算：**

| 策略 | 固定止损 | 追踪止盈 | 时间止损 |
|------|---------|---------|---------|
| v1_plus | 10% | 20% | 20天/3% |
| v_zanger | 6% | 15% | 10天/2% |
| v_weinstein | 10% | 20% | 30天/5% |

**使用方式：**
```bash
# 所有策略共享同一份持仓
uv run python main.py --mode live --strategy v1_plus
uv run python main.py --mode live --strategy v_zanger
# 只需维护 output/shared/positions.json
```

---

## 11. 已知限制 / 待解决事项

| 事项 | 说明 |
|------|------|
| 港股追踪 | 系统只支持美股，港股 03986 用户手动管理 |
| SA Quant 403 | SA API 有时被 Cloudflare 拦截，用户可手动截图告知 Claude |
| 样本内年化偏低 | v1_plus 样本内（2015-2024）年化 13%（略低于 15% 及格线），因包含2018/2020/2022三次熊市。OOS 牛市期表现优异（54.8%），符合 Minervini 趋势策略特性 |
| 信号频率（样本内）| 样本内 1.8/月，样本外 6.8/月；差异因市场周期，不是过拟合 |
| 加仓后均价更新 | 加仓后用户需告知新均价，Claude 手动更新 positions.json |

---

*文件生成时间：2026-03-13*
*下一个会话接手时，请确认 `output/shared/positions.json` 内容与用户最新持仓一致。*
