# 美股 SEPA + VCP 交易信号系统

基于 Mark Minervini《股票魔法师》中 **SEPA + VCP** 策略的美股交易信号扫描工具。

每天收盘后运行，自动扫描 ~300 只股票，输出买入/卖出信号和 Markdown 日报，供人工决策参考。**系统不自动下单。**

---

## 核心功能

- **买入信号**：趋势模板 + 相对强度 + VCP 形态 + 放量突破四层过滤
- **卖出信号**：固定止损（-10%）/ 追踪止盈（从高点-20%）/ 时间止损（20天无涨幅）
- **每日报告**：Markdown 格式，逐条解读每个信号的触发原因
- **回测引擎**：支持样本内/样本外分割验证，输出年化收益/夏普/最大回撤等指标
- **多策略架构**：可扩展，新策略只需新建子包，无需改框架代码

---

## 当前策略：魔法师调整参数版 V1+

| 指标 | 样本内（2015-2024） | 样本外 OOS（2024-2026） |
|------|:---:|:---:|
| 年化收益 | 13.0% | **54.8%** |
| 夏普比率 | 1.64 | **2.24** |
| 最大回撤 | 20.2% | **15.2%** |
| 每月信号 | 1.8 | **6.8** |
| 综合评级 | 4/6 | **6/6 ✅** |

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
