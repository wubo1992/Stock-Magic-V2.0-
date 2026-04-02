"""
backtest_us500.py — 用完整美股池（515只）跑回测

用法：
    uv run python backtest_us500.py
"""
import re
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

# ── 1. 读取 UNIVERSE.md，提取美股（S&P 500 + Nasdaq 100）───────────────
universe_path = Path(__file__).parent / "UNIVERSE.md"
with open(universe_path, "r", encoding="utf-8") as f:
    content = f.read()

sections = re.split(r"^## ", content, flags=re.MULTILINE)
us_stocks = set()
in_us_section = False

for section in sections:
    lines = section.split("\n")
    title = lines[0].strip()

    if title.startswith("板块 S：") or title.startswith("板块 N："):
        in_us_section = True
    elif (title.startswith("港股：") or title.startswith("台股") or
          title.startswith("操作说明") or title.startswith("当前手动池")):
        in_us_section = False

    if in_us_section:
        for line in lines:
            if line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    ticker = parts[1]
                    if re.match(r"^[A-Z0-9]{1,6}(\.[A-Z0-9]{1,5})?$", ticker):
                        us_stocks.add(ticker)

us_stocks = sorted(us_stocks)
print(f"[股票池] 美股共 {len(us_stocks)} 只（S&P 500 + Nasdaq 100）")

# ── 2. 加载配置和策略 ──────────────────────────────────────────────────
config_path = Path(__file__).parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

from strategies.registry import get_strategy

strategy_id = "v_weinstein_adx"
strategy_cls = get_strategy(strategy_id)
strategy_config = config["strategies"][strategy_id]
print(f"[策略] {strategy_cls.strategy_name}")
print(f"[参数] {strategy_config.get('description', '')}")

# ── 3. 运行回测 ──────────────────────────────────────────────────────────
from backtest.engine import BacktestEngine

start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
end_date   = datetime(2026, 3, 27, tzinfo=timezone.utc)

engine = BacktestEngine(
    config=config,
    strategy_cls=strategy_cls,
    strategy_config=strategy_config,
    symbols=us_stocks,
    start_date=start_date,
    end_date=end_date,
    strategy_id=strategy_id,
)

print(f"[回测] {start_date.date()} ~ {end_date.date()}，{len(us_stocks)} 只股票")
result = engine.run(verbose=True)
result.print_report(strategy_name=strategy_cls.strategy_name)

# 保存报告
from pathlib import Path
strategy_id_str = strategy_cls.strategy_id
report_dir = Path("output") / strategy_id_str / "backtest"
report_dir.mkdir(parents=True, exist_ok=True)
report_path = report_dir / f"回测报告_全段_美股池_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.md"

import io
_buffer = io.StringIO()
# 简单保存
report_path.write_text(f"# {strategy_cls.strategy_name} — 美股515只回测报告\n\n", encoding="utf-8")
print(f"[报告] 已保存：{report_path}")
