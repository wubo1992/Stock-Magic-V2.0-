"""
update_universe_sp500.py
将 S&P 500 + Nasdaq 100 全部静态写入 UNIVERSE.md
"""
import json
import time
import urllib.request
import ssl

# 禁用 SSL 验证（某些环境需要）
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 获取 S&P 500 和 Nasdaq 100 symbols
with open("data/index_cache.json") as f:
    cache = json.load(f)

sp500_syms = set(cache["sp500"]["symbols"])
ndx100_syms = set(cache["nasdaq100"]["symbols"])
all_syms = sorted(sp500_syms | ndx100_syms)

print(f"S&P 500: {len(sp500_syms)}")
print(f"Nasdaq 100: {len(ndx100_syms)}")
print(f"去重后: {len(all_syms)}")

# 从 Wikipedia 获取公司名称
def fetch_wiki_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        html = resp.read().decode("utf-8")
    # 简单解析：提取 Symbol 和 Security 列
    import re
    # 找表格行
    pattern = re.compile(r'<td[^>]*><a[^>]*title="([^"]+)"[^>]*>([^<]+)</a></td>\s*<td[^>]*>([^<]+)</td>')
    # 实际 Wikipedia 页面格式更复杂，用更简单的方式
    # 提取 <tr> 中的 <td> 内容
    rows = re.findall(r'<tr>\s*<td>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>', html)
    result = {}
    for symbol, name in rows:
        sym = symbol.strip().replace(".", "-")  # BRK.B -> BRK-B
        name = name.strip()
        if sym and name:
            result[sym] = name
    return result

def fetch_wiki_nasdaq100():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        html = resp.read().decode("utf-8")
    import re
    # 提取 Nasdaq 100 成分股表格
    rows = re.findall(r'<tr>\s*<td[^>]*>(?:<a[^>]*>)?([A-Z^<]+)(?:</a>)?</td>\s*<td[^>]*>([^<]+)</td>', html)
    result = {}
    for symbol, name in rows:
        sym = symbol.strip().replace(".", "-")
        name = name.strip()
        if sym and name and len(sym) <= 5:
            result[sym] = name
    return result

print("Fetching S&P 500 company names from Wikipedia...")
try:
    sp500_names = fetch_wiki_sp500()
    print(f"  S&P 500: got {len(sp500_names)} names")
except Exception as e:
    print(f"  S&P 500 fetch failed: {e}")
    sp500_names = {}

print("Fetching Nasdaq 100 company names from Wikipedia...")
try:
    ndx100_names = fetch_wiki_nasdaq100()
    print(f"  Nasdaq 100: got {len(ndx100_names)} names")
except Exception as e:
    print(f"  Nasdaq 100 fetch failed: {e}")
    ndx100_names = {}

# 合并名称映射
name_map = {}
name_map.update(sp500_names)
name_map.update(ndx100_names)
print(f"Total names collected: {len(name_map)}")

# 已知常用股票名称（备用，覆盖率高的）
FALLBACK_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "AMZN": "Amazon", "META": "Meta", "BRK-B": "Berkshire Hathaway",
    "AVGO": "Broadcom", "XOM": "Exxon Mobil", "UNH": "UnitedHealth", "LLY": "Eli Lilly",
    "JPM": "JPMorgan Chase", "V": "Visa", "MA": "Mastercard", "JNJ": "Johnson & Johnson",
    "PG": "Procter & Gamble", "HD": "Home Depot", "ABBV": "AbbVie", "MRK": "Merck",
    "BAC": "Bank of America", "KO": "Coca-Cola", "PEP": "PepsiCo", "COST": "Costco",
    "WMT": "Walmart", "MCD": "McDonald's", "CSCO": "Cisco", "ACN": "Accenture",
    "TMO": "Thermo Fisher", "ABT": "Abbott Labs", "DHR": "Danaher", "MUFG": "Mitsubishi UFG",
    "IBM": "IBM", "DIS": "Walt Disney", "NFLX": "Netflix", "INTC": "Intel",
    "AMD": "AMD", "QCOM": "Qualcomm", "TXN": "Texas Instruments", "AMAT": "Applied Materials",
    "NOW": "ServiceNow", "CRM": "Salesforce", "ADBE": "Adobe", "PYPL": "PayPal",
    "UBER": "Uber", "LYFT": "Lyft", "SNOW": "Snowflake", "DDOG": "Datadog",
    "TEAM": "Atlassian", "NET": "Cloudflare", "CRWD": "CrowdStrike", "ZS": "Zscaler",
    "OKTA": "Okta", "PANW": "Palo Alto Networks", "FTNT": "Fortinet", "MDB": "MongoDB",
    "DOCU": "DocuSign", "TWLO": "Twilio", "SPLK": "Splunk", "ANSS": "ANSYS",
    "CDNS": "Cadence Design", "SNPS": "Synopsys", "INTU": "Intuit", "ADP": "ADP",
    "PAYX": "Paychex", "ISRG": "Intuitive Surgical", "DXCM": "Dexcom", "IDXX": "IDEXX",
    "REGN": "Regeneron", "VRTX": "Vertex", "MRNA": "Moderna", "BIIB": "Biogen",
    "GILD": "Gilead", "AMGN": "Amgen", "BMY": "Bristol-Myers", "PFE": "Pfizer",
    "CVS": "CVS Health", "UNH": "UnitedHealth", "CI": "Cigna", "HUM": "Humana",
    "BDX": "Becton Dickinson", "SYK": "Stryker", "BSX": "Boston Scientific",
    "EW": "Edwards Lifesciences", "STE": "STERIS", "ZBH": "Zimmer Biomet",
    "RMD": "ResMed", "IQV": "IQVIA", "MTD": "Mettler-Toledo",
}

# 填充缺失的名称
filled = 0
for sym in all_syms:
    if sym not in name_map:
        name = FALLBACK_NAMES.get(sym, sym)
        name_map[sym] = name
        filled += 1

print(f"Fallback names used: {filled}")

# 读取现有 UNIVERSE.md
with open("UNIVERSE.md", "r") as f:
    content = f.read()

# 找到现有板块结束位置（在 "## 操作说明" 之前插入）
insert_marker = "## 操作说明"
idx = content.find(insert_marker)
if idx == -1:
    print("WARNING: insert marker not found!")

# 构建新的 S&P 500 + Nasdaq 100 板块内容
# 先按 S&P 500 和 Nasdaq 100 分开标记
sp500_list = sorted(sp500_syms)
ndx100_list = sorted(ndx100_syms)

new_content = []

# 板块：S&P 500
new_content.append("## 板块 S：标普 500 成分股（静态写入，Wikipedia 定期更新）\n")
new_content.append("| 代码 | 公司 | 简介 |")
new_content.append("|------|------|------|")
for sym in sp500_list:
    name = name_map.get(sym, sym)
    new_content.append(f"| {sym} | {name} | S&P 500 成分股 |")

new_content.append("")

# 板块：Nasdaq 100
new_content.append("## 板块 N：纳斯达克 100 成分股（静态写入，Wikipedia 定期更新）\n")
new_content.append("| 代码 | 公司 | 简介 |")
new_content.append("|------|------|------|")
# 只写 Nasdaq 独有的（非 S&P 500 的）
ndx_only = sorted(ndx100_syms - sp500_syms)
for sym in ndx_only:
    name = name_map.get(sym, sym)
    new_content.append(f"| {sym} | {name} | Nasdaq 100 成分股 |")

new_content.append("")

# 更新文件头部的总数
header_old = "## 当前手动池总数：929 只（含美股625 + 港股244 + 台股60，S&P 500 + Nasdaq 100，去重后）"
header_new = f"## 当前手动池总数：{len(all_syms)} 只（含 S&P 500 {len(sp500_syms)} 只 + Nasdaq 100 {len(ndx100_syms)} 只，去重后 {len(all_syms)} 只）"

new_text = content[:idx]
new_text = new_text.replace(header_old, header_new)

# 在操作说明前插入新板块
new_text += "\n".join(new_content)
new_text += "\n" + content[idx:]

with open("UNIVERSE.md", "w") as f:
    f.write(new_text)

print(f"\n完成！已写入 {len(sp500_list)} 只 S&P 500 + {len(ndx_only)} 只 Nasdaq 100 独有股票")
print(f"文件已保存：UNIVERSE.md")
