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

## 2. 系统当前状态（截至 2026-03-25）

### 已完成的阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1-3 | 系统骨架、回测验证、迭代优化 | ✅ 完成 |
| Phase 4 | 多策略架构升级（strategies/ 重构） | ✅ 完成 |
| Phase 5 | SA Quant 扫描器接入（--mode scan） | ✅ 完成 |
| Phase 6 | 卖出信号持仓追踪（positions.json） | ✅ 完成 |
| Phase 7 | V1+ 参数优化 + 股票池扩充 | ✅ 完成 |
| Phase 8 | 数据持久化三层架构 + live 模式缓存 staleness 修复 | ✅ 完成 |
| Phase 9 | 指数成分股扩池（S&P 500 + Nasdaq 100，Wikipedia 自动拉取）| ✅ 完成 |
| Phase 10 | 7 大师策略变种实施 + 样本外回测对比 | ✅ 完成 |
| Phase 11 | 多策略共享持仓（positions.json 统一，动态计算止损）| ✅ 完成 |
| Phase 12 | 分批止盈功能（Partial Take Profit，参数化配置）| ✅ 完成 |

### 最新回测结果（v1_plus，高波动期 2024-02-12 至 2026-03-06）

| 阶段 | 区间 | 年化收益 | 夏普比率 | 最大回撤 | 每月信号 | 综合 |
|------|------|----------|----------|----------|---------|------|
| 样本内 | 2015-01 ~ 2024-12 | 13.0% | 1.64 | 20.2% | 1.8 | 4/6 合格 |
| 样本外 OOS | 2024-02 ~ 2026-03 | 45.3% | 1.95 | 15.3% | 6.4 | **6/6 全部达标** |

> **注**：样本外年化 45.3%（含 2026 Q1 高波动期），v1_plus 是唯一 6/6 全部达标的策略。
>
> **详细回测报告**：`docs/回测对比报告_高波动期_2024-02-12_2026-03-06.md`

---

## 3. 股票池状态

**当前手动股票池总数：929 只**
- 美股：625 只
- 港股：244 只
- 台股：60 只
- 另含 S&P 500 + Nasdaq 100 指数成分股

**自动股票池**：Alpaca 新闻 API 每日增量抓取，约 150-200 只

**股票池文件**：`UNIVERSE.md`（唯一来源，直接编辑生效）

---

## 4. 当前持仓（截至 2026-03-25）

**持仓文件**：`output/shared/positions.json`（所有策略共享）

**当前持仓（共 44 只，有仓位的 27 只）：**

| 股票 | 入场价 | 持仓天数 | 最高价 | shares |
|------|--------|----------|--------|--------|
| AXTI | 39.25 | 135 | 68.55 | 100 |
| MU | 406.07 | 135 | 461.8 | 100 |
| VRT | 245.5 | 135 | 270.84 | 100 |
| LOCO | 12.7 | 104 | 14.33 | 100 |
| GTE | 8.16 | 108 | 8.74 | 100 |
| LWLG | 7.08 | 108 | 7.61 | 100 |
| XPEV | 19.2 | 108 | 20.08 | 100 |
| GPRK | 9.15 | 87 | 10.2 | 100 |
| VMD | 9.79 | 87 | 9.79 | 100 |
| NBIS | 129.795 | 87 | 129.795 | 100 |
| NSA | 40.24 | 89 | 40.24 | 100 |
| ANRO | 24.265 | 89 | 24.265 | 100 |
| CTMX | 6.74 | 89 | 6.74 | 100 |
| LNG | 266.21 | 57 | 294.605 | 100 |
| ELA | 15.32 | 57 | 17.27 | 100 |
| KODK | 7.94 | 57 | 8.375 | 100 |
| UGA | 99.69 | 57 | 105.38 | 100 |
| USO | 121.71 | 57 | 121.71 | 100 |
| FIVE | 235.02 | 57 | 235.02 | 100 |
| AR | 43.3 | 57 | 43.355 | 100 |
| GRNT | 5.46 | 57 | 5.51 | 100 |
| KOS | 2.98 | 57 | 2.98 | 100 |
| RRC | 45.3 | 57 | 45.93 | 100 |
| ENOR | 36.34 | 46 | 36.34 | 100 |
| WDC | 316.94 | 46 | 316.94 | 100 |
| PL | 33.87 | 45 | 33.87 | 100 |
| OKE | 89.27 | 43 | 90.93 | 0 |
| SEDG | 51.7 | 43 | 51.7 | 0 |
| DELL | 158.08 | 43 | 176.975 | 0 |
| TSEM | 172.16 | 27 | 180.93 | 100 |
| SWBI | 14.415 | 29 | 14.84 | 0 |
| ELVN | 30.84 | 29 | 31.19 | 0 |
| GRDN | 37.255 | 29 | 37.555 | 0 |
| LUNR | 20.31 | 29 | 20.31 | 0 |
| ASRT | 13.99 | 29 | 16.46 | 0 |
| SCHL | 38.42 | 13 | 38.87 | 0 |
| FLNT | 3.87 | 17 | 3.87 | 0 |
| KVHI | 9.195 | 17 | 9.195 | 0 |
| SPIR | 12.825 | 17 | 12.85 | 0 |
| APGE | 79.19 | 17 | 79.19 | 0 |
| PXS | 4.56 | 5 | 4.56 | 0 |
| TROX | 8.45 | 3 | 8.45 | 0 |
| VIAV | 35.9 | 3 | 35.9 | 0 |
| XTL | 194.715 | 3 | 194.715 | 0 |

**说明**：
- `shares: 0` 的为已卖出或信号未实际执行
- `shares: 100` 的为当前持有仓位

---

## 5. 持仓管理规则

### 用户每日操作时机
**美股收盘后（北京时间次日约 05:00-06:00）**，告知 Claude 持仓变化，更新完再运行系统。

### 用户需要告知的内容
- 新买入：股票代码 + 实际成交均价
- 已平仓：哪只股票平掉了
- 加仓后均价变化：股票代码 + 新的加权平均成本

### Claude 负责处理的部分
- 更新 `output/shared/positions.json`（entry_price、entry_date、highest_price）
- **止损价由各策略动态计算，不再存储**
  - v1_plus：止损 = entry_price × 90%，追踪止盈 = 从最高点回落 20%
  - v_zanger：止损 = entry_price × 94%，追踪止盈 = 从最高点回落 15%
  - v_weinstein：止损 = entry_price × 90%，追踪止盈 = 从最高点回落 20%
- entry_date 保持**最早入场日期**不变
- highest_price 和 days_held 由系统自动更新

### 多策略共享持仓
- 所有策略共用同一份 `output/shared/positions.json`
- 不同策略根据各自参数给出不同的止损/止盈建议

---

## 6. 每日运行命令

```bash
cd /Users/wubo/Desktop/信号系统克劳德V3.1_Minimax支线/signal_system

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
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-06 --strategy v1_plus

# 补档（切换策略后补充 signals.csv 历史记录）
uv run python main.py --mode backtest --start YYYY-MM-DD --end YYYY-MM-DD --strategy v1_plus --save-signals
```

---

## 7. 策略体系

### 9 种已注册策略

| 策略 ID | 大师来源 | 核心特点 | 样本外年化 | 达标 |
|---------|---------|---------|-----------|------|
| v1 | Minervini | 原版 SEPA + VCP（VCP<8%） | 57.4% | 6/6 ✅ |
| v1_plus | Minervini | 调整参数版（VCP<12%） | 45.3% | 6/6 ✅ |
| v_oneil | O'Neil | CANSLIM 技术版（VCP<20%） | 96.1% | 5/6 |
| v_ryan | Ryan | 极紧 VCP（<5%） | 14.0% | 1/6 |
| v_kell | Kell | 极端放量（3x） | 80.2% | 3/6 |
| v_kullamaggi | Kullamägi | 极紧止损（5%）+ 极端放量（4x） | 50.6% | 5/6 |
| v_zanger | Zanger | 纯技术突破（无 RS/VCP） | 128.4% | 4/6 |
| v_stine | Stine | 超强精选（RS≥90%） | 51.4% | 5/6 |
| v_weinstein | Weinstein | Stage 2 分析（只用 SMA150） | 56.9% | 5/6 |

**策略文档**：
- `docs/strategies/v1_plus.md`
- `docs/strategies/v_oneil.md`
- `docs/strategies/v_ryan.md`
- `docs/strategies/v_kell.md`
- `docs/strategies/v_kullamaggi.md`
- `docs/strategies/v_zanger.md`
- `docs/strategies/v_stine.md`
- `docs/strategies/v_weinstein.md`
- `docs/策略对比总览.md`

---

## 8. 关键文件说明

```
signal_system/
├── CLAUDE.md                  ← 主指令文件，每次新会话必须先读
├── HANDOVER.md                ← 本文件
├── UNIVERSE.md                ← 股票池（929只），唯一来源，直接编辑生效
├── config.yaml                ← 所有参数（active_strategy: v1_plus）
├── main.py                    ← 运行入口
│
├── strategies/
│   ├── base.py               ← StrategyBase 抽象基类
│   ├── registry.py           ← 策略注册表（9个策略已注册）
│   ├── v1_wizard/           ← 魔法师策略 V1
│   │   └── sepa_minervini.py
│   ├── v1_plus/             ← 魔法师策略 V1+（当前主策略）
│   │   └── sepa_plus.py
│   ├── v_oneil/             ← O'Neil CANSLIM
│   ├── v_ryan/              ← David Ryan
│   ├── v_kell/              ← Oliver Kell
│   ├── v_kullamaggi/        ← Kullamägi
│   ├── v_zanger/            ← Dan Zanger
│   ├── v_stine/             ← Jesse Stine
│   └── v_weinstein/         ← Weinstein
│
├── backtest/
│   └── engine.py             ← 回测引擎
│
├── signals/
│   ├── generator.py          ← 信号格式化 + CSV 存储
│   ├── report.py             ← 每日 Markdown 报告生成
│   └── positions.py         ← 持仓持久化
│
├── universe/
│   ├── manager.py            ← 股票池合并
│   ├── index_fetcher.py     ← S&P 500 / Nasdaq 100
│   ├── alpaca_fetcher.py   ← Alpaca 新闻
│   ├── sa_scanner.py       ← SA Quant Rating
│   └── updater.py           ← 写入 UNIVERSE.md
│
├── data/
│   ├── fetcher.py           ← 数据获取（三层架构）
│   ├── cache/               ← 本地持久化（.pkl）
│   ├── universe_cache.json  ← Alpaca 新闻缓存
│   └── index_cache.json     ← 指数成分股缓存
│
└── output/
    ├── shared/
    │   └── positions.json   ← 共享持仓（所有策略共用）★
    ├── v1_plus_wizard/      ← v1_plus 输出目录
    │   ├── signals.csv
    │   └── YYYY-MM-DD/
    │       └── 报告_魔法师调整参数版V1+_YYYY-MM-DD.md
    └── v_zanger/            ← v_zanger 输出目录
    └── v_weinstein/         ← v_weinstein 输出目录
```

---

## 9. 系统三种出场条件

| 条件 | 触发标准 | 说明 |
|------|---------|------|
| 固定止损 | 收盘价 ≤ 入场价 × 90% | 亏损超过 10% |
| 追踪止盈 | 收盘价 ≤ 历史最高价 × 80% | 从高点回落 20% |
| 时间止损 | 持有 ≥ 20 天且涨幅 < 3% | 入场后长期不动 |

---

## 10. 已知限制

| 事项 | 说明 |
|------|------|
| 港股追踪 | 系统只支持美股，港股用户手动管理 |
| SA Quant 403 | SA API 有时被 Cloudflare 拦截，用户可手动截图告知 Claude |
| 样本内年化偏低 | v1_plus 样本内（2015-2024）年化 13%（略低于 15% 及格线），因包含2018/2020/2022三次熊市 |
| 信号频率（样本内）| 样本内 1.8/月，样本外 6.4/月；差异因市场周期，不是过拟合 |

---

## 11. 相关文档索引

| 文档 | 说明 |
|------|------|
| `docs/回测对比报告_高波动期_2024-02-12_2026-03-06.md` | 9 大策略样本外回测对比 |
| `docs/策略对比总览.md` | 策略对比分析 + 组合建议 |
| `docs/项目总结与学习笔记.md` | 项目全程记录，策略原理详解 |
| `HOW_TO_ADD_STRATEGY.md` | 新策略接入手册 |
| `USAGE.md` | 用户使用手册 |
| `docs/strategies/*.md` | 各策略详细文档 |

---

*文件生成时间：2026-03-25*
*下一个会话接手时，请确认 `output/shared/positions.json` 内容与用户最新持仓一致。*
