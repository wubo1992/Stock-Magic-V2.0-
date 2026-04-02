"""Quick test for optimizer.py - writes to output file"""
import sys
sys.path.insert(0, ".")
from backtest.optimizer import run_trial, load_universe, random_config
from datetime import datetime, timezone
import random
import io

# Capture output to file
output = io.StringIO()
random.seed(42)

symbols = load_universe()
print("Universe:", len(symbols), "stocks\n", file=output)

for i in range(5):
    params = random_config("v1_plus")
    print(f"Trial {i+1}: stop_loss={params.get('stop_loss_pct')}, trailing_stop={params.get('trailing_stop_pct')}, time_stop={params.get('time_stop_days')}, rs={params.get('rs_min_percentile')}, vcp={params.get('vcp_final_range_pct')}, vol={params.get('volume_mult')}, breakout={params.get('min_breakout_pct')}", file=output)
    try:
        r = run_trial("v1_plus", params, symbols,
                       datetime(2020, 1, 1, tzinfo=timezone.utc),
                       datetime(2022, 12, 31, tzinfo=timezone.utc))
        print(f"  Sharpe={r['sharpe']:.2f} Ann={r['annualized_return']*100:.1f}% WR={r['win_rate']*100:.1f}% PLR={r['profit_loss_ratio']:.2f} DD={r['max_drawdown']*100:.1f}% Signals/mo={r['signals_per_month']:.1f} Trades={r['total_trades']}", file=output)
    except Exception as e:
        print(f"  FAILED: {e}", file=output)
    print(file=output)

print("All done!", file=output)

# Write to file
with open("test_optimizer_output.txt", "w") as f:
    f.write(output.getvalue())

print("Output written to test_optimizer_output.txt")
