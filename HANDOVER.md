# 交接文档 — 美股信号系统上下文

> 给下一个 Claude Code 会话读的文件。
> 新会话开始时，请先完整阅读 `CLAUDE.md`，再读本文件。

---

## 1. 项目概述

这是一个**美股事件驱动交易信号系统**，基于 Mark Minervini 的 SEPA + VCP 策略（《股票魔法师》）。

- 用户是非程序员，所有代码由 Claude Code 编写和维护
- 系统每天收盘后运行，产生买入/卖出信号和 Markdown 日报
- 不自动下单，信号供人工决策参考

**当前策略：魔法师调整参数版V1+（strategy ID: `v1_plus`，输出目录: `v1_plus_wizard`）**

---

## 2. 系统当前状态（截至 2026-03-05）

### 已完成的阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1-3 | 系统骨架、回测验证、迭代优化 | ✅ 完成 |
| Phase 4 | 多策略架构升级（strategies/ 重构） | ✅ 完成 |
| Phase 5 | SA Quant 扫描器接入（--mode scan） | ✅ 完成 |
| Phase 6 | 卖出信号持仓追踪（positions.json） | ✅ 完成 |
| Phase 7 | V1+ 参数优化 + 股票池扩充（297只）| ✅ 完成 |

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

持仓信息存储在：
```
output/v1_plus_wizard/positions.json
```

字段说明：
- `entry_price`：加权平均入场均价（用户加仓后由 Claude 手动更新）
- `entry_date`：首次建仓日期（加仓时不变）
- `highest_price`：系统自动追踪的历史最高价
- `stop_loss`：entry_price × 90%（由 Claude 计算并写入）
- `days_held`：系统每次 live 运行自动 +1

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
- 根据用户提供的均价，计算止损价（均价 × 90%）
- 更新 `output/v1_plus_wizard/positions.json`（entry_price、stop_loss）
- entry_date 保持**最早入场日期**不变（时间止损从首次建仓起算）
- highest_price 和 days_held 由系统自动更新，Claude 不手动改

### 关于加仓信号
- **已持仓的股票如果再次满足买入条件，系统会发出信号**（这是加仓参考）
- 系统不会覆盖已有持仓记录，只发信号
- 用户加仓后，告知新均价，Claude 手动更新 entry_price 和 stop_loss

---

## 6. 每日运行命令

```bash
# 每天收盘后运行（v1_plus 已设为默认，无需加 --strategy）
uv run python main.py --mode live

# 或显式指定
uv run python main.py --mode live --strategy v1_plus

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

## 9. 近期代码变更记录（2026-03-05，Phase 7）

### 新增策略：`strategies/v1_plus/sepa_plus.py`
`SEPAPlusStrategy` 继承 `SEPAStrategy`，只覆盖 `strategy_id = "v1_plus_wizard"` 和 `strategy_name`。参数在 `config.yaml` 的 `strategies.v1_plus:` 段独立配置。

**关键参数变化（相对 v1）**：`vcp_final_range_pct: 0.08 → 0.12`（放宽VCP末端箱体，经控制变量测试效果最佳）

### 修复：`strategies/v1_wizard/sepa_minervini.py`（live_mode bug）
新增 `live_mode: bool = False` 参数。实盘模式传 `True` 时不自动创建 Position，避免干扰 positions.json 的人工管理流程。回测模式保持默认 `False`，自动创建 Position 供出场逻辑使用。

### 增强：`backtest/engine.py`（--save-signals 补档）
`BacktestEngine.__init__()` 新增 `save_signals_csv: bool = False` 和 `strategy_id: str = ""`。当 `save_signals_csv=True` 时，回测中每产生一个买入信号就同步写入对应策略的 `signals.csv`，用于切换策略后的历史信号补档。

### 增强：`main.py`
- argparse 新增 `--save-signals` flag（传给 `BacktestEngine`）
- `run_live()` 调用时传入 `live_mode=True`

### 修改：`config.yaml`
- `active_strategy: v1` → `active_strategy: v1_plus`
- 新增完整 `v1_plus:` 策略配置段

### 修改：`UNIVERSE.md`
股票池 186 → ~297 只，新增 10 个板块（板块十五至二十四）：SaaS/云软件、支付金融科技、医疗器械/制药、工业/国防、消费/零售、银行/金融、大宗商品/材料、亚太/新兴市场、REIT、成长股+通信。

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

## 11. 已知限制 / 待解决事项

| 事项 | 说明 |
|------|------|
| 港股追踪 | 系统只支持美股，港股 03986 用户手动管理 |
| SA Quant 403 | SA API 有时被 Cloudflare 拦截，用户可手动截图告知 Claude |
| 样本内年化偏低 | v1_plus 样本内（2015-2024）年化 13%（略低于 15% 及格线），因包含2018/2020/2022三次熊市。OOS 牛市期表现优异（54.8%），符合 Minervini 趋势策略特性 |
| 信号频率（样本内）| 样本内 1.8/月，样本外 6.8/月；差异因市场周期，不是过拟合 |
| 加仓后均价更新 | 加仓后用户需告知新均价，Claude 手动更新 positions.json |

---

*文件生成时间：2026-03-05*
*下一个会话接手时，请确认 `output/v1_plus_wizard/positions.json` 内容与用户最新持仓一致。*
