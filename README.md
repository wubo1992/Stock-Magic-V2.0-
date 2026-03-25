# 美股事件驱动交易信号系统

> 基于 Mark Minervini SEPA + VCP 策略的多策略交易信号系统
> 支持 **9 种大师策略变种**的回测对比与实盘运行

每天收盘后运行，自动扫描 ~300 只股票，输出买入/卖出信号和 Markdown 日报，供人工决策参考。**系统不自动下单。**

---

## 🏆 最新回测表现（样本外 2024-02-12 至 2026-03-06，517 天）

| 策略 | 年化收益 | 夏普比率 | 最大回撤 | 胜率 | 信号/月 | 达标 |
|------|---------|---------|---------|------|---------|------|
| **v_zanger** | **128.4%** | **4.42** | 12.0% | 39.8% | 13.1 | 4/6 |
| **v_oneil** | **96.1%** | 2.62 | 18.3% | 37.0% | 5.9 | 5/6 |
| **v_kell** | **80.2%** | 1.90 | 29.4% | 18.2% | 0.9 | 3/6 |
| **v1** | 57.4% | 2.10 | 17.2% | 45.5% | 2.2 | **6/6** |
| **v1_plus** | 45.3% | 1.95 | 15.3% | 43.7% | 6.4 | **6/6** |

**完整回测报告**：`docs/回测对比报告_高波动期_2024-02-12_2026-03-06.md`

---

## 📚 9 种策略变种

| 策略 ID | 大师来源 | 核心特点 | 文档 |
|---------|---------|---------|------|
| v1 | Minervini | 原版 SEPA + VCP | - |
| v1_plus | Minervini | 调整参数版（VCP<12%） | [文档](docs/strategies/v1_plus.md) |
| v_oneil | O'Neil | CANSLIM 技术版（VCP<20%） | [文档](docs/strategies/v_oneil.md) |
| v_ryan | Ryan | 极紧 VCP（<5%） | [文档](docs/strategies/v_ryan.md) |
| v_kell | Kell | 极端放量（3x） | [文档](docs/strategies/v_kell.md) |
| v_kullamaggi | Kullamägi | 极紧止损（5%）+ 极端放量（4x） | [文档](docs/strategies/v_kullamaggi.md) |
| v_zanger | Zanger | 纯技术突破（无 RS/VCP） | [文档](docs/strategies/v_zanger.md) |
| v_stine | Stine | 超强精选（RS≥90%） | [文档](docs/strategies/v_stine.md) |
| v_weinstein | Weinstein | Stage 2 分析（只用 SMA150） | [文档](docs/strategies/v_weinstein.md) |

**策略对比总览**：`docs/策略对比总览.md`

---

## 核心功能

- **买入信号**：趋势模板 + 相对强度 + VCP 形态 + 放量突破四层过滤
- **卖出信号**：固定止损（-10%）/ 追踪止盈（从高点-20%）/ 时间止损（20天无涨幅）
- **每日报告**：Markdown 格式，逐条解读每个信号的触发原因
- **回测引擎**：支持样本内/样本外分割验证，输出年化收益/夏普/最大回撤等指标
- **多策略架构**：可扩展，新策略只需新建子包，无需改框架代码
- **持仓追踪**：自动追踪止损、止盈、时间止损等出场条件
- **数据持久化**：本地缓存历史数据，增量更新，减少网络请求

---

## 快速开始

**环境要求：** Python 3.13 + [uv](https://github.com/astral-sh/uv)

```bash
# 安装依赖
uv sync

# 配置 API Key（复制模板后填入 Alpaca Key）
cp .env.example .env

# 运行实盘模式（收盘后执行）
uv run python main.py --mode live

# 运行回测
uv run python main.py --mode backtest --start 2024-02-12 --end 2026-03-05 --strategy v1_plus
```

---

## 项目结构

```
signal_system/
├── main.py              ← 运行入口
├── config.yaml          ← 所有参数（策略参数、出场条件等）
├── UNIVERSE.md          ← 股票池（~297 只，直接编辑生效）
├── strategies/
│   ├── v1_wizard/       ← 魔法师策略 V1（原版）
│   └── v1_plus/         ← 魔法师策略 V1+（当前主策略）
├── backtest/            ← 回测引擎
├── signals/             ← 信号生成 + 报告 + 持仓追踪
└── data/                ← 数据获取 + 缓存
```

---

## 策略逻辑（V1+）

```
第一层：趋势模板
  收盘价 > SMA50 > SMA150 > SMA200，SMA200 上升，距52周低点+25%以上

第二层：相对强度
  过去12个月涨幅在全部监控股中排名前 30%

第三层：VCP 形态 + 突破入场
  ≥2 次振幅递减回调，末端箱体 <12%，放量（>1.5x 均量）突破30日高点
```

---

## 配置说明

所有参数通过 `config.yaml` 调整，无需改代码：

```yaml
active_strategy: v1_plus

strategies:
  v1_plus:
    vcp_final_range_pct: 0.12   # VCP 末端箱体（核心参数）
    rs_min_percentile: 70       # 相对强度门槛
    stop_loss_pct: 0.10         # 固定止损
    trailing_stop_pct: 0.20     # 追踪止盈
    time_stop_days: 20          # 时间止损天数
```

---

## 数据来源

- **行情数据**：[Alpaca IEX](https://alpaca.markets/) 免费版（Yahoo Finance 备用）
- **股票筛选**：[Seeking Alpha Quant Rating](https://seekingalpha.com/screeners/quant-ratings) API（`--mode scan`）

需要在 `.env` 中填写 Alpaca API Key（免费注册可得）。

---

## 免责声明

本系统仅供学习和研究用途，所有输出均为技术信号，**不构成投资建议**。使用者自行承担投资决策风险。
