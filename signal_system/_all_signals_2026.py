#!/usr/bin/env python3
import re

log_path = '/Users/wubo/Desktop/codes/信号系统克劳德V3.1_Minimax支线/signal_system/output/SIGNALS_LOG.md'

with open(log_path, 'r') as f:
    lines = f.readlines()

# Find all 2026 date sections
in_buy_section = False
current_date = None
all_signals = {}  # date -> list of (stock, max_strength, strategies)
current_date_signals = []

strategy_names = ['v1', 'v1_plus', 'v_oneil', 'v_ryan', 'v_kell', 'v_kullamaggi', 'v_zanger', 'v_stine', 'v_weinstein']

for line in lines:
    # New date section
    date_match = re.match(r'^## (2026-\d{2}-\d{2})', line)
    if date_match:
        # Save previous date's signals
        if current_date and current_date_signals:
            all_signals[current_date] = current_date_signals
        current_date = date_match.group(1)
        current_date_signals = []
        in_buy_section = False
        continue

    # Check for buy section start
    if '### 买入信号汇总' in line:
        in_buy_section = True
        continue

    # Check for sell section (end of buy section)
    if '### 卖出信号' in line or '### 出场信号' in line:
        in_buy_section = False
        continue

    # Parse buy signal rows
    if in_buy_section and '**' in line and '|' in line:
        parts = [p.strip() for p in line.split('|')]
        # parts[0] is empty, parts[1] is ticker (**TICKER**), parts[2-9] are strategies, parts[10] is score
        if len(parts) >= 11 and parts[1]:
            ticker_match = re.match(r'\*\*([A-Z]+)\*\*', parts[1])
            if ticker_match:
                ticker = ticker_match.group(1)
                strategies = []
                max_s = 0
                for j, sname in enumerate(strategy_names):
                    val = parts[2 + j].strip() if 2 + j < len(parts) else '-'
                    if val not in ['-', '', None]:
                        try:
                            s = int(val)
                            strategies.append(sname)
                            if s > max_s:
                                max_s = s
                        except:
                            pass
                if strategies:
                    current_date_signals.append((ticker, max_s, strategies))

# Save last date
if current_date and current_date_signals:
    all_signals[current_date] = current_date_signals

# Print all signals grouped by date
for date in sorted(all_signals.keys()):
    print(f'\n## {date}')
    stocks = all_signals[date]
    for stock, strength, strategies in stocks:
        print(f'  {stock} ★{strength} ({", ".join(strategies)})')

print(f'\n\n=== 2026年所有出现过的买入信号股票（去重）===')
all_stocks = set()
for date, stocks in sorted(all_signals.items()):
    for stock, _, _ in stocks:
        all_stocks.add(stock)

print(f'共 {len(all_stocks)} 只股票：')
for s in sorted(all_stocks):
    print(s)