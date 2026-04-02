# 股票池主清单 (UNIVERSE)

> **这是手动股票池的唯一来源。**
> 程序直接读取此文件，修改后下次运行自动生效，无需同步 `config.yaml`。
>
> - **用户**：直接在对应板块表格里增删行即可
> - **AI**：直接修改此文件（增删行），不需要改任何其他文件
> - 删除的股票请移到末尾「待移出记录」节（保留历史，但不计入股票池）
>
> **自动池**（Alpaca 新闻每日抓取，约 150-200 只）不在此文件，自动管理，查看命令：
> ```bash
> uv run python -c "import json; d=json.load(open('data/universe_cache.json')); print(f'自动池：{len(d)} 只'); print(' '.join(sorted(d.keys())))"
> ```

---

## 当前手动池总数：929 只（含美股625 + 港股244 + 台股60，S&P 500 + Nasdaq 100，去重后）

---

## 板块一：科技巨头（Mag 7）

| 代码 | 公司名 | 简介 |
|------|--------|------|
| AAPL | Apple | 消费电子 + 服务生态 |
| MSFT | Microsoft | 云计算(Azure) + AI(Copilot) |
| NVDA | NVIDIA | AI芯片霸主，数据中心GPU |
| GOOGL | Alphabet | 搜索广告 + 云(GCP) + AI |
| TSLA | Tesla | 电动车 + 储能 + FSD |
| AMZN | Amazon | 电商 + 云计算(AWS) |
| META | Meta | 社交媒体 + 广告 + AI |

---

## 板块二：成长股（其他）

| 代码 | 公司名 | 简介 |
|------|--------|------|
| AMD | Advanced Micro Devices | CPU/GPU，NVIDIA主要竞争者 |
| TSM | Taiwan Semiconductor | 全球最大晶圆代工，苹果/英伟达供应商 |
| PLTR | Palantir | 大数据/AI分析，政府+企业客户 |
| FN | Fabrinet | 光学器件精密制造，光模块供应链 |
| DY | Dycom Industries | 电信基础设施施工，5G建设受益 |
| MU | Micron Technology | DRAM/NAND内存，AI服务器需求拉动 |
| CRDO | Credo Technology | 高速互连芯片，数据中心AI网络 |
| APP | AppLovin | 移动广告技术平台，高成长 |
| TMUS | T-Mobile US | 美国最大5G运营商 |
| UBER | Uber | 网约车+外卖，盈利拐点 |
| RCL | Royal Caribbean | 邮轮龙头，消费复苏受益 |
| CCL | Carnival | 邮轮，周期性消费复苏标的 |
| OKTA | Okta | 身份认证云服务，零信任安全 |
| TWLO | Twilio | 云通信平台(API) |
| EAT | Brinker International | 餐饮连锁(Chili's)，成本管控改善 |
| CLS | Celestica | 电子制造服务，AI服务器组装 |
| AGX | Argan | 电力基础设施工程 |
| POWL | Powell Industries | 电气设备，数据中心/电网受益 |
| STRL | Sterling Infrastructure | 基础设施建设 |
| WLDN | Willdan Group | 能源效率工程服务 |
| ALL | Allstate | 财险龙头，保费涨价周期 |
| SYF | Synchrony Financial | 消费信贷，零售联名信用卡 |
| BRK.B | Berkshire Hathaway B | 巴菲特控股集团，多元化价值投资 |
| SKYW | SkyWest | 支线航空，区域航空复苏 |
| BLBD | Blue Bird | 电动校车，政府补贴受益 |
| CAAP | Corporacion America Airports | 新兴市场机场运营 |
| NEM | Newmont | 全球最大金矿公司 |
| CDE | Coeur Mining | 银金矿，贵金属小盘 |
| KGC | Kinross Gold | 加拿大中型金矿 |
| SSRM | SSR Mining | 加拿大多矿种矿业 |
| B | Barnes Group | 工业零部件，航空+工业 |
| TIGO | Millicom International | 拉美新兴市场电信 |
| W | Wayfair | 线上家居电商，周期性复苏标的 |
| PARR | Par Pacific | 炼油+便利店，特殊情况价值 |
| INCY | Incyte | 生物制药，JAK抑制剂(血液病) |
| TTMI | TTM Technologies | PCB制造，国防+数据中心 |
| VISN | VisionWave Technologies | 新兴科技小盘 |
| UNFI | United Natural Foods | 天然/有机食品分销 |
| MFC | Manulife Financial | 加拿大人寿保险巨头 |
| EZPW | EZCorp | 典当行+消费金融，特殊情况 |
| ARQT | Arcutis Biotherapeutics | 皮肤病生物制药 |
| CVSA | Companhia de Saneamento | 巴西水务公用事业 |
| PPC | Pilgrim's Pride | 美国最大鸡肉加工商 |

---

## 板块三：半导体（费城半导体指数 SOX）

| 代码 | 公司名 | 简介 |
|------|--------|------|
| AVGO | Broadcom | 网络芯片 + 软件，AI定制芯片(XPU) |
| ASML | ASML Holding | EUV光刻机垄断，半导体设备 |
| QCOM | Qualcomm | 手机基带芯片，汽车/IoT延伸 |
| INTC | Intel | PC/服务器CPU，转型阶段 |
| TXN | Texas Instruments | 模拟芯片，工业/汽车应用 |
| AMAT | Applied Materials | 半导体薄膜设备龙头 |
| ADI | Analog Devices | 高精度模拟芯片 |
| KLAC | KLA Corporation | 半导体检测设备 |
| LRCX | Lam Research | 刻蚀设备，存储芯片关键供应商 |
| ARM | ARM Holdings | CPU架构授权，AI芯片设计基础 |
| MRVL | Marvell Technology | 数据中心网络+存储芯片，AI受益 |
| NXPI | NXP Semiconductors | 汽车芯片龙头 |
| MCHP | Microchip Technology | 微控制器(MCU)，工业/汽车 |
| ON | onsemi | 电源芯片，电动车+新能源 |
| SWKS | Skyworks Solutions | 射频芯片，手机信号 |
| MPWR | Monolithic Power Systems | 高效电源管理芯片，AI服务器 |
| WDC | Western Digital | 硬盘+闪存，存储周期回升 |
| STM | STMicroelectronics | 欧洲半导体，汽车+工业 |
| TER | Teradyne | 半导体测试设备 |
| ENTG | Entegris | 半导体材料/化学品，先进制程 |
| RMBS | Rambus | 内存接口芯片，数据中心 |
| LSCC | Lattice Semiconductor | 低功耗FPGA，边缘AI |
| QRVO | Qorvo | 射频芯片，5G基站 |
| WOLF | Wolfspeed | 碳化硅(SiC)芯片，电动车功率器件 |
| COHR | Coherent | 光学+激光+化合物半导体 |

---

## 板块四：光模块

| 代码 | 公司名 | 简介 |
|------|--------|------|
| LITE | Lumentum | 光收发器+激光，数据中心AI互连 |
| AAOI | Applied Optoelectronics | 高速光模块，AI数据中心 |
| MTSI | MACOM Technology Solutions | 光模块驱动芯片，高速互连 |
| AXTI | AXT Inc | 砷化镓/磷化铟基板，光电子器件材料 |
| GLW | Corning | 光纤光缆+特种玻璃，AI数据中心互连 |

---

## 板块五：清洁能源 / 核能

| 代码 | 公司名 | 简介 |
|------|--------|------|
| CEG | Constellation Energy | 全美最大核能运营商，AI数据中心供电 |
| VST | Vistra Energy | 核能+天然气发电，德克萨斯电力 |
| TLN | Talen Energy | 核电站，AI数据中心直签协议 |
| GEV | GE Vernova | GE能源业务分拆，电网+风电 |
| BE | Bloom Energy | 固体氧化物燃料电池，清洁发电 |
| NEE | NextEra Energy | 全球最大可再生能源公司 |
| PWR | Quanta Services | 电力线路工程，电网升级受益 |
| CCJ | Cameco | 全球最大铀矿公司，核能燃料 |
| OKLO | Oklo | 小型模块化反应堆(SMR)，OpenAI支持 |
| NNE | Nano Nuclear Energy | 微型核反应堆，概念成长 |

---

## 板块六：传统能源（石油/天然气）

| 代码 | 公司名 | 简介 |
|------|--------|------|
| XOM | ExxonMobil | 美国最大石油公司 |
| CVX | Chevron | 美国第二大石油公司 |
| COP | ConocoPhillips | 美国最大独立油气勘探公司 |
| EOG | EOG Resources | 页岩油龙头，低成本高效率 |
| OXY | Occidental Petroleum | 石油+化工，巴菲特持仓 |
| FANG | Diamondback Energy | 二叠纪盆地页岩油，低成本 |
| MPC | Marathon Petroleum | 美国最大炼油商 |
| VLO | Valero Energy | 大型炼油+可再生燃料 |
| PSX | Phillips 66 | 炼油+化工+中游管道 |
| SLB | SLB (Schlumberger) | 全球最大油服公司 |
| TRMD | Teekay Tankers | 原油/成品油海运，航运周期 |

---

## 板块七：黄金 / 贵金属（流媒体/Royalty 模式）

> NEM、KGC、SSRM、CDE 这四只传统金矿股已归在"成长股"板块，此处仅列 Streaming/Royalty 模式的低风险矿业公司。

| 代码 | 公司名 | 简介 |
|------|--------|------|
| AEM | Agnico Eagle Mines | 大型高质量金矿，低成本生产 |
| WPM | Wheaton Precious Metals | 贵金属流媒体(Streaming)模式，低风险 |
| RGLD | Royal Gold | 黄金Royalty/流媒体，稳定现金流 |
| AGI | Alamos Gold | 中型成长矿，多国矿山 |

---

## 板块八：医疗健康

| 代码 | 公司名 | 简介 |
|------|--------|------|
| LLY | Eli Lilly | 减肥药(GLP-1)龙头，Mounjaro/Zepbound |
| UNH | UnitedHealth Group | 美国最大医疗保险公司 |
| ABBV | AbbVie | 生物制药，Humira专利到期后转型 |
| MRK | Merck | 制药巨头，Keytruda(癌症免疫) |
| ISRG | Intuitive Surgical | 达芬奇手术机器人垄断 |
| TMO | Thermo Fisher Scientific | 生命科学仪器+试剂，行业基础设施 |
| ABT | Abbott Laboratories | 医疗器械+诊断+营养品 |
| DHR | Danaher | 生命科学+水处理，精密工业 |
| BMY | Bristol-Myers Squibb | 大型肿瘤/血液病制药 |
| CVS | CVS Health | 药店+保险+诊所，垂直整合 |
| HCA | HCA Healthcare | 美国最大私立医院连锁 |
| VRTX | Vertex Pharmaceuticals | 囊性纤维化用药垄断，高利润率 |

---

## 板块九：防御性消费 / 零售

| 代码 | 公司名 | 简介 |
|------|--------|------|
| COST | Costco | 会员制仓储零售，强护城河 |
| WMT | Walmart | 大众消费零售+电商，防御性强 |
| PG | Procter & Gamble | 日用消费品，品牌矩阵（洗护/纸品） |
| KO | Coca-Cola | 软饮料，全球分销网络，经典防御股 |
| PEP | PepsiCo | 饮料+零食(Frito-Lay)，多元化消费 |
| MCD | McDonald's | 全球快餐连锁，特许经营轻资产 |
| HD | Home Depot | 家装建材零售龙头，地产周期受益 |
| NKE | Nike | 全球运动品牌，DTC转型中 |
| DIS | Walt Disney | 内容IP+流媒体(Disney+)+主题公园 |

---

## 板块十：保险 / 金融科技

| 代码 | 公司名 | 简介 |
|------|--------|------|
| CB | Chubb | 全球最大财产险，巴菲特持仓 |
| TRV | Travelers Companies | 美国大型商业财险 |
| AFL | Aflac | 补充健康险，日本市场龙头 |
| MCO | Moody's | 信用评级+风险数据，强定价权 |
| SPGI | S&P Global | 评级+指数+数据，垄断性商业模式 |
| V | Visa | 全球支付网络，轻资产高利润 |
| MA | Mastercard | 全球支付网络，Visa竞争对手 |

---

## 板块十一：银行 / 投行

| 代码 | 公司名 | 简介 |
|------|--------|------|
| JPM | JPMorgan Chase | 全球最大投资银行，综合金融 |
| BAC | Bank of America | 美国第二大商业银行 |
| GS | Goldman Sachs | 顶级投行，财富管理+交易 |
| MS | Morgan Stanley | 投行+财富管理，机构业务 |
| AXP | American Express | 高端信用卡，高净值客群 |

---

## 板块十二：科技平台（非半导体）

| 代码 | 公司名 | 简介 |
|------|--------|------|
| ORCL | Oracle | 云数据库转型，AI基础设施受益 |
| CRM | Salesforce | 企业CRM龙头，AI Agent(Agentforce) |
| NFLX | Netflix | 流媒体盈利拐点，广告层增长 |

---

## 板块十三：工业 / 国防

| 代码 | 公司名 | 简介 |
|------|--------|------|
| GE | GE Aerospace | 商用+军用航空发动机，高景气 |
| CAT | Caterpillar | 建筑/矿山设备，基建周期 |
| RTX | RTX Corporation | 国防(导弹)+航空发动机(普惠) |
| UPS | United Parcel Service | 全球快递物流 |
| HON | Honeywell | 工业自动化+航空电子+楼宇系统 |
| VRT | Vertiv Holdings | 数据中心电源/散热基础设施，AI算力支撑 |

---

## 板块十四：电信 / 基础设施

| 代码 | 公司名 | 简介 |
|------|--------|------|
| T | AT&T | 美国大型电信，高股息，去杠杆中 |
| AMT | American Tower | 通信铁塔REIT，5G升级+全球扩张 |

---

## 板块十五：SaaS / 云软件

| 代码 | 公司名 | 简介 |
|------|--------|------|
| ADBE | Adobe | 创意软件+数字媒体，订阅制转型完成 |
| NOW | ServiceNow | 企业工作流自动化，政府+大企业客户 |
| PANW | Palo Alto Networks | 网络安全平台，零信任架构 |
| CRWD | CrowdStrike | 终端安全，云原生 EDR 龙头 |
| DDOG | Datadog | 云监控可观测性平台，DevOps必备 |
| NET | Cloudflare | CDN+网络安全，边缘计算平台 |
| ZS | Zscaler | 零信任云安全，SASE架构 |
| VEEV | Veeva Systems | 生命科学行业云软件垄断 |
| WDAY | Workday | 企业HR+财务云软件 |
| TEAM | Atlassian | 软件协作工具(Jira/Confluence) |
| SNPS | Synopsys | EDA芯片设计软件，AI加速 |
| CDNS | Cadence Design Systems | EDA工具+仿真软件 |
| ANSS | ANSYS | 工程仿真软件，航空+汽车+半导体 |
| PAYC | Paycom Software | 中小企业HR薪资云软件 |
| HUBS | HubSpot | 中小企业CRM+营销自动化 |
| DOCU | DocuSign | 电子签名SaaS，法律+金融行业 |
| MDB | MongoDB | NoSQL数据库，云原生开发者优选 |
| ANET | Arista Networks | 数据中心高速网络交换机，AI基础设施 |
| TTD | The Trade Desk | 程序化广告技术平台 |
| SHOP | Shopify | 电商建站SaaS，中小商家首选 |
| FTNT | Fortinet | 网络安全设备+订阅，中小企业防火墙 |
| INTU | Intuit | 财务软件(TurboTax/QuickBooks)，消费+中小企业 |

---

## 板块十六：支付 / 金融科技补充

| 代码 | 公司名 | 简介 |
|------|--------|------|
| PYPL | PayPal | 在线支付，Venmo+Braintree，转型中 |
| FIS | Fidelity National Information Services | 金融科技基础设施，银行+零售支付 |
| FISV | Fiserv | 支付处理+金融科技，Clover POS |
| XYZ | Block (Square) | 小微商家支付+现金应用(CashApp) |

---

## 板块十七：医疗器械 / 大型制药补充

| 代码 | 公司名 | 简介 |
|------|--------|------|
| REGN | Regeneron Pharmaceuticals | 生物制药，Eylea+Dupixent双线增长 |
| GILD | Gilead Sciences | 抗病毒药物，HIV/肝炎/肿瘤 |
| AMGN | Amgen | 大型生物制药，减肥药进军 |
| BIIB | Biogen | 神经系统疾病，阿尔茨海默症新药 |
| PFE | Pfizer | 全球制药巨头，后疫情时代转型 |
| JNJ | Johnson & Johnson | 医疗器械+制药，分拆消费品部门 |
| SYK | Stryker | 骨科+神经外科医疗器械 |
| BSX | Boston Scientific | 心血管+内镜医疗器械 |
| EW | Edwards Lifesciences | 心脏瓣膜+血流动力学监测 |
| DXCM | Dexcom | 连续血糖监测仪，糖尿病管理 |
| IDXX | IDEXX Laboratories | 宠物诊断+检测，兽医行业必需 |
| ZBH | Zimmer Biomet | 关节置换植入物，骨科器械 |
| RMD | ResMed | 睡眠呼吸暂停设备+软件，CPAP龙头 |
| STE | STERIS | 医疗器械消毒+手术室服务 |
| IQV | IQVIA Holdings | 医药数据分析+临床研究服务 |

---

## 板块十八：工业 / 国防补充

| 代码 | 公司名 | 简介 |
|------|--------|------|
| LMT | Lockheed Martin | 全球最大国防承包商，F-35战机 |
| NOC | Northrop Grumman | 国防航空航天，B-21隐形轰炸机 |
| TDG | TransDigm Group | 航空零部件垄断，军民两用 |
| AXON | Axon Enterprise | 执法科技(泰瑟枪+执法摄像+云平台) |
| ROK | Rockwell Automation | 工业自动化，智能制造 |
| ETN | Eaton Corporation | 电气+液压，电网升级受益 |
| DE | Deere & Company | 农业机械+施工设备，精准农业 |
| FAST | Fastenal | 工业紧固件分销，供应链管理 |
| ITW | Illinois Tool Works | 工业多元化，汽车+建筑+食品设备 |
| PH | Parker Hannifin | 运动控制系统，航空+工业液压 |
| MMM | 3M | 工业多元化，黏合剂+安全产品 |
| CMI | Cummins Inc | 柴油+氢能发动机，重型设备动力 |
| WM | Waste Management | 美国最大固废处理+回收 |
| RSG | Republic Services | 固废处理，环保+可再生天然气 |

---

## 板块十九：消费 / 零售补充

| 代码 | 公司名 | 简介 |
|------|--------|------|
| SBUX | Starbucks | 全球咖啡连锁，中国市场复苏受关注 |
| CMG | Chipotle Mexican Grill | 快速休闲餐饮，数字化运营领先 |
| LOW | Lowe's Companies | 家装建材零售，HD主要竞争对手 |
| TGT | Target | 美国综合零售商，自有品牌+当日达 |
| DECK | Deckers Outdoor | UGG+HOKA品牌，运动鞋高成长 |
| YUM | Yum! Brands | 快餐连锁(KFC/Pizza Hut/Taco Bell)特许经营 |
| LULU | Lululemon Athletica | 高端运动服饰，瑜伽+男装扩张 |
| PHM | PulteGroup | 美国大型住宅建商，首购+改善型 |
| TOL | Toll Brothers | 豪华住宅建商，高端买家群体 |
| NVR | NVR Inc | 住宅建商，资产轻模式典范 |
| BKNG | Booking Holdings | 全球在线旅游OTA，Booking.com+Priceline |
| EXPE | Expedia Group | 在线旅游平台，Vrbo+Hotels.com |

---

## 板块二十：银行 / 多元金融补充

| 代码 | 公司名 | 简介 |
|------|--------|------|
| BLK | BlackRock | 全球最大资产管理公司，ETF(iShares)巨头 |
| SCHW | Charles Schwab | 美国最大折扣券商，资产托管 |
| CME | CME Group | 全球最大衍生品交易所，利率+商品期货 |
| ICE | Intercontinental Exchange | 证券交易所+金融数据，NYSE母公司 |
| MSCI | MSCI Inc | 股票指数+ESG评级，机构投资基础设施 |
| USB | U.S. Bancorp | 美国第五大商业银行，稳健运营 |
| WFC | Wells Fargo | 美国第四大银行，零售+抵押贷款 |
| C | Citigroup | 美国第三大银行，全球业务重组中 |
| NDAQ | Nasdaq Inc | 证券交易所+金融科技，数据业务高增长 |
| CBOE | CBOE Global Markets | 期权交易所，VIX指数发布方 |

---

## 板块二十一：大宗商品 / 材料 / 能源补充

| 代码 | 公司名 | 简介 |
|------|--------|------|
| FCX | Freeport-McMoRan | 全球最大铜矿，电动车+电网铜需求 |
| NUE | Nucor Corporation | 美国最大钢铁公司，电炉炼钢低成本 |
| CF | CF Industries | 全球最大氮肥生产商，农业+清洁氨 |
| MOS | The Mosaic Company | 钾肥+磷肥，农业大宗商品 |
| HAL | Halliburton | 油服公司，钻井+完井服务 |
| DVN | Devon Energy | 页岩油气，二叠纪盆地核心资产 |
| APA | APA Corporation | 石油+天然气勘探，北美+海外多元 |
| MRO | Marathon Oil | 石油勘探生产，北美页岩油 |
| X | United States Steel | 美国钢铁，汽车+建筑用钢 |
| AA | Alcoa Corporation | 全球铝业巨头，铝土矿到铝材一体化 |
| CLF | Cleveland-Cliffs | 美国最大平板钢材生产商，汽车供应链 |

---

## 板块二十二：亚太 / 新兴市场 ADR

| 代码 | 公司名 | 简介 |
|------|--------|------|
| BABA | Alibaba Group | 中国电商+云计算(阿里云)，港股+美股双挂牌 |
| BIDU | Baidu | 中国搜索引擎+AI(文心一言)+自动驾驶 |
| JD | JD.com | 中国自营电商+物流，3C家电强项 |
| SE | Sea Limited | 东南亚电商(Shopee)+游戏(Garena)+金融 |
| PDD | PDD Holdings | 拼多多+Temu，极低价电商全球扩张 |

---

## 板块二十三：房地产 / REIT

| 代码 | 公司名 | 简介 |
|------|--------|------|
| PLD | Prologis | 全球最大工业物流REIT，电商仓储受益 |
| PSA | Public Storage | 美国最大自助仓储REIT |
| O | Realty Income | 零售净租赁REIT，月付股息 |
| EQR | Equity Residential | 美国大型公寓REIT，城市核心地段 |
| WY | Weyerhaeuser | 木材+木材产品REIT，住宅建设受益 |

---

## 板块二十四：成长股补充（近年高成长）

| 代码 | 公司名 | 简介 |
|------|--------|------|
| CELH | Celsius Holdings | 功能饮料高成长，健身文化受益 |
| BILL | Bill.com | 中小企业应付/应收账款自动化 |
| ZM | Zoom Video Communications | 视频会议，企业版+电话系统转型 |
| DT | Dynatrace | 云可观测性+安全平台，全栈监控 |
| RBLX | Roblox | 游戏创作平台，青少年元宇宙社区 |
| SNOW | Snowflake | 云数据仓库，数据共享平台 |
| ALNY | Alnylam Pharmaceuticals | RNA干扰疗法(RNAi)，罕见病基因药 |
| CRSP | CRISPR Therapeutics | 基因编辑疗法，首个获批镰刀型细胞病 |
| MRNA | Moderna | mRNA技术平台，癌症疫苗+流感疫苈 |
| BMRN | BioMarin Pharmaceutical | 罕见病酶替代疗法，PKU+MPS治疗 |
| VZ | Verizon Communications | 美国第二大电信运营商，高股息防御 |
| CMCSA | Comcast | 有线宽带+NBC环球，内容+基础设施 |
| CHTR | Charter Communications | 美国第二大有线电视+宽带运营商 |

---



## 操作说明

### 添加股票
直接在对应板块的表格末尾加一行：
```
| TICKER | 公司名 | 一句话简介 |
```
保存后，下次运行程序时自动生效。

### 删除股票
把那一行从板块表格中删除，移到末尾「待移出记录」节（保留历史记录）。

### 添加新板块
在「待移出记录」节之前新增 `## 板块N：名称`，格式与现有板块一致。

### SA Quant 自动扫描（`--mode scan`）

运行以下命令，系统会自动查询候选股票的 SA Quant Rating，将 Strong Buy（≥ 4.5）的新股票写入**本文件末尾的「自动扫描新增」节**：

```bash
uv run python main.py --mode scan           # 扫描并写入 UNIVERSE.md
uv run python main.py --mode scan --dry-run # 只预览，不修改文件
```

自动新增的股票格式：
```
| 代码 | 公司名（可补充） | Strong Buy 4.85 | 2026-03-05 |
```

你可以随时把「自动扫描新增」节里的股票移到对应板块（把行复制过去，删掉此处即可）。

### 验证当前手动池
```bash
uv run python -c "
from universe.manager import _read_universe_md
symbols = _read_universe_md()
print(f'当前手动池：{len(symbols)} 只')
print(' '.join(symbols))
"
```

---

## 板块二十五：S&P 500 成分股

> S&P 500 成分股，来源：Wikipedia（永久静态写入，不动态抓取）
> 共 503 只，已与上方板块去重

| 代码 | 公司名 |
|------|--------|
| MMM | 3M |
| AOS | A. O. Smith |
| ABT | Abbott Laboratories |
| ABBV | AbbVie |
| ACN | Accenture |
| ADBE | Adobe Inc. |
| AMD | Advanced Micro Devices |
| AES | AES Corporation |
| AFL | Aflac |
| A | Agilent Technologies |
| APD | Air Products |
| ABNB | Airbnb |
| AKAM | Akamai Technologies |
| ALB | Albemarle Corporation |
| ARE | Alexandria Real Estate Equities |
| ALGN | Align Technology |
| ALLE | Allegion |
| LNT | Alliant Energy |
| ALL | Allstate |
| GOOGL | Alphabet Inc. (Class A) |
| GOOG | Alphabet Inc. (Class C) |
| MO | Altria |
| AMZN | Amazon |
| AMCR | Amcor |
| AEE | Ameren |
| AEP | American Electric Power |
| AXP | American Express |
| AIG | American International Group |
| AMT | American Tower |
| AWK | American Water Works |
| AMP | Ameriprise Financial |
| AME | Ametek |
| AMGN | Amgen |
| APH | Amphenol |
| ADI | Analog Devices |
| AON | Aon plc |
| APA | APA Corporation |
| APO | Apollo Global Management |
| AAPL | Apple Inc. |
| AMAT | Applied Materials |
| APP | AppLovin |
| APTV | Aptiv |
| ACGL | Arch Capital Group |
| ADM | Archer Daniels Midland |
| ARES | Ares Management |
| ANET | Arista Networks |
| AJG | Arthur J. Gallagher & Co. |
| AIZ | Assurant |
| T | AT&T |
| ATO | Atmos Energy |
| ADSK | Autodesk |
| ADP | Automatic Data Processing |
| AZO | AutoZone |
| AVB | AvalonBay Communities |
| AVY | Avery Dennison |
| AXON | Axon Enterprise |
| BKR | Baker Hughes |
| BALL | Ball Corporation |
| BAC | Bank of America |
| BAX | Baxter International |
| BDX | Becton Dickinson |
| BRK.B | Berkshire Hathaway |
| BBY | Best Buy |
| TECH | Bio-Techne |
| BIIB | Biogen |
| BLK | BlackRock |
| BX | Blackstone Inc. |
| XYZ | Block, Inc. |
| BK | BNY Mellon |
| BA | Boeing |
| BKNG | Booking Holdings |
| BSX | Boston Scientific |
| BMY | Bristol Myers Squibb |
| AVGO | Broadcom |
| BR | Broadridge Financial Solutions |
| BRO | Brown & Brown |
| BF.B | Brown–Forman |
| BLDR | Builders FirstSource |
| BG | Bunge Global |
| BXP | BXP, Inc. |
| CHRW | C.H. Robinson |
| CDNS | Cadence Design Systems |
| CPT | Camden Property Trust |
| CPB | Campbell's Company (The) |
| COF | Capital One |
| CAH | Cardinal Health |
| CCL | Carnival |
| CARR | Carrier Global |
| CVNA | Carvana |
| CAT | Caterpillar Inc. |
| CBOE | Cboe Global Markets |
| CBRE | CBRE Group |
| CDW | CDW Corporation |
| COR | Cencora |
| CNC | Centene Corporation |
| CNP | CenterPoint Energy |
| CF | CF Industries |
| CRL | Charles River Laboratories |
| SCHW | Charles Schwab Corporation |
| CHTR | Charter Communications |
| CVX | Chevron Corporation |
| CMG | Chipotle Mexican Grill |
| CB | Chubb Limited |
| CHD | Church & Dwight |
| CIEN | Ciena |
| CI | Cigna |
| CINF | Cincinnati Financial |
| CTAS | Cintas |
| CSCO | Cisco |
| C | Citigroup |
| CFG | Citizens Financial Group |
| CLX | Clorox |
| CME | CME Group |
| CMS | CMS Energy |
| KO | Coca-Cola Company (The) |
| CTSH | Cognizant |
| COIN | Coinbase |
| CL | Colgate-Palmolive |
| CMCSA | Comcast |
| FIX | Comfort Systems USA |
| CAG | Conagra Brands |
| COP | ConocoPhillips |
| ED | Consolidated Edison |
| STZ | Constellation Brands |
| CEG | Constellation Energy |
| COO | Cooper Companies (The) |
| CPRT | Copart |
| GLW | Corning Inc. |
| CPAY | Corpay |
| CTVA | Corteva |
| CSGP | CoStar Group |
| COST | Costco |
| CTRA | Coterra |
| CRH | CRH plc |
| CRWD | CrowdStrike |
| CCI | Crown Castle |
| CSX | CSX Corporation |
| CMI | Cummins |
| CVS | CVS Health |
| DHR | Danaher Corporation |
| DRI | Darden Restaurants |
| DDOG | Datadog |
| DVA | DaVita |
| DECK | Deckers Brands |
| DE | Deere & Company |
| DELL | Dell Technologies |
| DAL | Delta Air Lines |
| DVN | Devon Energy |
| DXCM | Dexcom |
| FANG | Diamondback Energy |
| DLR | Digital Realty |
| DG | Dollar General |
| DLTR | Dollar Tree |
| D | Dominion Energy |
| DPZ | Domino's |
| DASH | DoorDash |
| DOV | Dover Corporation |
| DOW | Dow Inc. |
| DHI | D. R. Horton |
| DTE | DTE Energy |
| DUK | Duke Energy |
| DD | DuPont |
| ETN | Eaton Corporation |
| EBAY | eBay Inc. |
| ECL | Ecolab |
| EIX | Edison International |
| EW | Edwards Lifesciences |
| EA | Electronic Arts |
| ELV | Elevance Health |
| EME | Emcor |
| EMR | Emerson Electric |
| ETR | Entergy |
| EOG | EOG Resources |
| EPAM | EPAM Systems |
| EQT | EQT Corporation |
| EFX | Equifax |
| EQIX | Equinix |
| EQR | Equity Residential |
| ERIE | Erie Indemnity |
| ESS | Essex Property Trust |
| EL | Estée Lauder Companies (The) |
| EG | Everest Group |
| EVRG | Evergy |
| ES | Eversource Energy |
| EXC | Exelon |
| EXE | Expand Energy |
| EXPE | Expedia Group |
| EXPD | Expeditors International |
| EXR | Extra Space Storage |
| XOM | ExxonMobil |
| FFIV | F5, Inc. |
| FDS | FactSet |
| FICO | Fair Isaac |
| FAST | Fastenal |
| FRT | Federal Realty Investment Trust |
| FDX | FedEx |
| FIS | Fidelity National Information Services |
| FITB | Fifth Third Bancorp |
| FSLR | First Solar |
| FE | FirstEnergy |
| FISV | Fiserv |
| F | Ford Motor Company |
| FTNT | Fortinet |
| FTV | Fortive |
| FOXA | Fox Corporation (Class A) |
| FOX | Fox Corporation (Class B) |
| BEN | Franklin Resources |
| FCX | Freeport-McMoRan |
| GRMN | Garmin |
| IT | Gartner |
| GE | GE Aerospace |
| GEHC | GE HealthCare |
| GEV | GE Vernova |
| GEN | Gen Digital |
| GNRC | Generac |
| GD | General Dynamics |
| GIS | General Mills |
| GM | General Motors |
| GPC | Genuine Parts Company |
| GILD | Gilead Sciences |
| GPN | Global Payments |
| GL | Globe Life |
| GDDY | GoDaddy |
| GS | Goldman Sachs |
| HAL | Halliburton |
| HIG | Hartford (The) |
| HAS | Hasbro |
| HCA | HCA Healthcare |
| DOC | Healthpeak Properties |
| HSIC | Henry Schein |
| HSY | Hershey Company (The) |
| HPE | Hewlett Packard Enterprise |
| HLT | Hilton Worldwide |
| HOLX | Hologic |
| HD | Home Depot (The) |
| HON | Honeywell |
| HRL | Hormel Foods |
| HST | Host Hotels & Resorts |
| HWM | Howmet Aerospace |
| HPQ | HP Inc. |
| HUBB | Hubbell Incorporated |
| HUM | Humana |
| HBAN | Huntington Bancshares |
| HII | Huntington Ingalls Industries |
| IBM | IBM |
| IEX | IDEX Corporation |
| IDXX | Idexx Laboratories |
| ITW | Illinois Tool Works |
| INCY | Incyte |
| IR | Ingersoll Rand |
| PODD | Insulet Corporation |
| INTC | Intel |
| IBKR | Interactive Brokers |
| ICE | Intercontinental Exchange |
| IFF | International Flavors & Fragrances |
| IP | International Paper |
| INTU | Intuit |
| ISRG | Intuitive Surgical |
| IVZ | Invesco |
| INVH | Invitation Homes |
| IQV | IQVIA |
| IRM | Iron Mountain |
| JBHT | J.B. Hunt |
| JBL | Jabil |
| JKHY | Jack Henry & Associates |
| J | Jacobs Solutions |
| JNJ | Johnson & Johnson |
| JCI | Johnson Controls |
| JPM | JPMorgan Chase |
| KVUE | Kenvue |
| KDP | Keurig Dr Pepper |
| KEY | KeyCorp |
| KEYS | Keysight Technologies |
| KMB | Kimberly-Clark |
| KIM | Kimco Realty |
| KMI | Kinder Morgan |
| KKR | KKR & Co. |
| KLAC | KLA Corporation |
| KHC | Kraft Heinz |
| KR | Kroger |
| LHX | L3Harris |
| LH | Labcorp |
| LRCX | Lam Research |
| LW | Lamb Weston |
| LVS | Las Vegas Sands |
| LDOS | Leidos |
| LEN | Lennar |
| LII | Lennox International |
| LLY | Lilly (Eli) |
| LIN | Linde plc |
| LYV | Live Nation Entertainment |
| LMT | Lockheed Martin |
| L | Loews Corporation |
| LOW | Lowe's |
| LULU | Lululemon Athletica |
| LYB | LyondellBasell |
| MTB | M&T Bank |
| MPC | Marathon Petroleum |
| MAR | Marriott International |
| MRSH | Marsh McLennan |
| MLM | Martin Marietta Materials |
| MAS | Masco |
| MA | Mastercard |
| MTCH | Match Group |
| MKC | McCormick & Company |
| MCD | McDonald's |
| MCK | McKesson Corporation |
| MDT | Medtronic |
| MRK | Merck & Co. |
| META | Meta Platforms |
| MET | MetLife |
| MTD | Mettler Toledo |
| MGM | MGM Resorts |
| MCHP | Microchip Technology |
| MU | Micron Technology |
| MSFT | Microsoft |
| MAA | Mid-America Apartment Communities |
| MRNA | Moderna |
| MOH | Molina Healthcare |
| TAP | Molson Coors Beverage Company |
| MDLZ | Mondelez International |
| MPWR | Monolithic Power Systems |
| MNST | Monster Beverage |
| MCO | Moody's Corporation |
| MS | Morgan Stanley |
| MOS | Mosaic Company (The) |
| MSI | Motorola Solutions |
| MSCI | MSCI Inc. |
| NDAQ | Nasdaq, Inc. |
| NTAP | NetApp |
| NFLX | Netflix |
| NEM | Newmont |
| NWSA | News Corp (Class A) |
| NWS | News Corp (Class B) |
| NEE | NextEra Energy |
| NKE | Nike, Inc. |
| NI | NiSource |
| NDSN | Nordson Corporation |
| NSC | Norfolk Southern |
| NTRS | Northern Trust |
| NOC | Northrop Grumman |
| NCLH | Norwegian Cruise Line Holdings |
| NRG | NRG Energy |
| NUE | Nucor |
| NVDA | Nvidia |
| NVR | NVR, Inc. |
| NXPI | NXP Semiconductors |
| ORLY | O'Reilly Automotive |
| OXY | Occidental Petroleum |
| ODFL | Old Dominion |
| OMC | Omnicom Group |
| ON | ON Semiconductor |
| OKE | Oneok |
| ORCL | Oracle Corporation |
| OTIS | Otis Worldwide |
| PCAR | Paccar |
| PKG | Packaging Corporation of America |
| PLTR | Palantir Technologies |
| PANW | Palo Alto Networks |
| PSKY | Paramount Skydance Corporation |
| PH | Parker Hannifin |
| PAYX | Paychex |
| PAYC | Paycom |
| PYPL | PayPal |
| PNR | Pentair |
| PEP | PepsiCo |
| PFE | Pfizer |
| PCG | PG&E Corporation |
| PM | Philip Morris International |
| PSX | Phillips 66 |
| PNW | Pinnacle West Capital |
| PNC | PNC Financial Services |
| POOL | Pool Corporation |
| PPG | PPG Industries |
| PPL | PPL Corporation |
| PFG | Principal Financial Group |
| PG | Procter & Gamble |
| PGR | Progressive Corporation |
| PLD | Prologis |
| PRU | Prudential Financial |
| PEG | Public Service Enterprise Group |
| PTC | PTC Inc. |
| PSA | Public Storage |
| PHM | PulteGroup |
| PWR | Quanta Services |
| QCOM | Qualcomm |
| DGX | Quest Diagnostics |
| Q | Qnity Electronics |
| RL | Ralph Lauren Corporation |
| RJF | Raymond James Financial |
| RTX | RTX Corporation |
| O | Realty Income |
| REG | Regency Centers |
| REGN | Regeneron Pharmaceuticals |
| RF | Regions Financial Corporation |
| RSG | Republic Services |
| RMD | ResMed |
| RVTY | Revvity |
| HOOD | Robinhood Markets |
| ROK | Rockwell Automation |
| ROL | Rollins, Inc. |
| ROP | Roper Technologies |
| ROST | Ross Stores |
| RCL | Royal Caribbean Group |
| SPGI | S&P Global |
| CRM | Salesforce |
| SNDK | Sandisk |
| SBAC | SBA Communications |
| SLB | Schlumberger |
| STX | Seagate Technology |
| SRE | Sempra |
| NOW | ServiceNow |
| SHW | Sherwin-Williams |
| SPG | Simon Property Group |
| SWKS | Skyworks Solutions |
| SJM | J.M. Smucker Company (The) |
| SW | Smurfit Westrock |
| SNA | Snap-on |
| SOLV | Solventum |
| SO | Southern Company |
| LUV | Southwest Airlines |
| SWK | Stanley Black & Decker |
| SBUX | Starbucks |
| STT | State Street Corporation |
| STLD | Steel Dynamics |
| STE | Steris |
| SYK | Stryker Corporation |
| SMCI | Supermicro |
| SYF | Synchrony Financial |
| SNPS | Synopsys |
| SYY | Sysco |
| TMUS | T-Mobile US |
| TROW | T. Rowe Price |
| TTWO | Take-Two Interactive |
| TPR | Tapestry, Inc. |
| TRGP | Targa Resources |
| TGT | Target Corporation |
| TEL | TE Connectivity |
| TDY | Teledyne Technologies |
| TER | Teradyne |
| TSLA | Tesla, Inc. |
| TXN | Texas Instruments |
| TPL | Texas Pacific Land Corporation |
| TXT | Textron |
| TMO | Thermo Fisher Scientific |
| TJX | TJX Companies |
| TKO | TKO Group Holdings |
| TTD | Trade Desk (The) |
| TSCO | Tractor Supply |
| TT | Trane Technologies |
| TDG | TransDigm Group |
| TRV | Travelers Companies (The) |
| TRMB | Trimble Inc. |
| TFC | Truist Financial |
| TYL | Tyler Technologies |
| TSN | Tyson Foods |
| USB | U.S. Bancorp |
| UBER | Uber |
| UDR | UDR, Inc. |
| ULTA | Ulta Beauty |
| UNP | Union Pacific Corporation |
| UAL | United Airlines Holdings |
| UPS | United Parcel Service |
| URI | United Rentals |
| UNH | UnitedHealth Group |
| UHS | Universal Health Services |
| VLO | Valero Energy |
| VTR | Ventas |
| VLTO | Veralto |
| VRSN | Verisign |
| VRSK | Verisk Analytics |
| VZ | Verizon |
| VRTX | Vertex Pharmaceuticals |
| VTRS | Viatris |
| VICI | Vici Properties |
| V | Visa Inc. |
| VST | Vistra Corp. |
| VMC | Vulcan Materials Company |
| WRB | W. R. Berkley Corporation |
| GWW | W. W. Grainger |
| WAB | Wabtec |
| WMT | Walmart |
| DIS | Walt Disney Company (The) |
| WBD | Warner Bros. Discovery |
| WM | Waste Management |
| WAT | Waters Corporation |
| WEC | WEC Energy Group |
| WFC | Wells Fargo |
| WELL | Welltower |
| WST | West Pharmaceutical Services |
| WDC | Western Digital |
| WY | Weyerhaeuser |
| WSM | Williams-Sonoma, Inc. |
| WMB | Williams Companies |
| WTW | Willis Towers Watson |
| WDAY | Workday, Inc. |
| WYNN | Wynn Resorts |
| XEL | Xcel Energy |
| XYL | Xylem Inc. |
| YUM | Yum! Brands |
| ZBRA | Zebra Technologies |
| ZBH | Zimmer Biomet |
| ZTS | Zoetis |

---

## 板块二十六：Nasdaq 100 成分股

> Nasdaq 100 成分股（不含 S&P 500 重叠部分），来源：Wikipedia
> 共 101 只

| 代码 | 公司名 |
|------|--------|
| ADBE | Adobe Inc. |
| AMD | Advanced Micro Devices |
| ABNB | Airbnb |
| ALNY | Alnylam Pharmaceuticals |
| GOOGL | Alphabet Inc. (Class A) |
| GOOG | Alphabet Inc. (Class C) |
| AMZN | Amazon |
| AEP | American Electric Power |
| AMGN | Amgen |
| ADI | Analog Devices |
| AAPL | Apple Inc. |
| AMAT | Applied Materials |
| APP | AppLovin |
| ARM | Arm Holdings |
| ASML | ASML Holding |
| TEAM | Atlassian |
| ADSK | Autodesk |
| ADP | Automatic Data Processing |
| AXON | Axon Enterprise |
| BKR | Baker Hughes |
| BKNG | Booking Holdings |
| AVGO | Broadcom |
| CDNS | Cadence Design Systems |
| CHTR | Charter Communications |
| CTAS | Cintas |
| CSCO | Cisco |
| CCEP | Coca-Cola Europacific Partners |
| CTSH | Cognizant |
| CMCSA | Comcast |
| CEG | Constellation Energy |
| CPRT | Copart |
| CSGP | CoStar Group |
| COST | Costco |
| CRWD | CrowdStrike |
| CSX | CSX Corporation |
| DDOG | Datadog |
| DXCM | DexCom |
| FANG | Diamondback Energy |
| DASH | DoorDash |
| EA | Electronic Arts |
| EXC | Exelon |
| FAST | Fastenal |
| FER | Ferrovial |
| FTNT | Fortinet |
| GEHC | GE HealthCare |
| GILD | Gilead Sciences |
| HON | Honeywell |
| IDXX | Idexx Laboratories |
| INSM | Insmed Incorporated |
| INTC | Intel |
| INTU | Intuit |
| ISRG | Intuitive Surgical |
| KDP | Keurig Dr Pepper |
| KLAC | KLA Corporation |
| KHC | Kraft Heinz |
| LRCX | Lam Research |
| LIN | Linde plc |
| MAR | Marriott International |
| MRVL | Marvell Technology |
| MELI | Mercado Libre |
| META | Meta Platforms |
| MCHP | Microchip Technology |
| MU | Micron Technology |
| MSFT | Microsoft |
| MSTR | MicroStrategy |
| MDLZ | Mondelez International |
| MPWR | Monolithic Power Systems |
| MNST | Monster Beverage |
| NFLX | Netflix, Inc. |
| NVDA | Nvidia |
| NXPI | NXP Semiconductors |
| ORLY | O'Reilly Automotive |
| ODFL | Old Dominion Freight Line |
| PCAR | Paccar |
| PLTR | Palantir Technologies |
| PANW | Palo Alto Networks |
| PAYX | Paychex |
| PYPL | PayPal |
| PDD | PDD Holdings |
| PEP | PepsiCo |
| QCOM | Qualcomm |
| REGN | Regeneron Pharmaceuticals |
| ROP | Roper Technologies |
| ROST | Ross Stores |
| STX | Seagate Technology |
| SHOP | Shopify |
| SBUX | Starbucks |
| SNPS | Synopsys |
| TMUS | T-Mobile US |
| TTWO | Take-Two Interactive |
| TSLA | Tesla, Inc. |
| TXN | Texas Instruments |
| TRI | Thomson Reuters |
| VRSK | Verisk Analytics |
| VRTX | Vertex Pharmaceuticals |
| WMT | Walmart |
| WBD | Warner Bros. Discovery |
| WDC | Western Digital |
| WDAY | Workday, Inc. |
| XEL | Xcel Energy |
| ZS | Zscaler |

---

## 板块：自动扫描新增

> 由 SA Quant 扫描程序自动添加（评分 ≥ 4.5 = Strong Buy）。
> 可以随时将此处的股票移至对应板块（把该行复制过去，删掉此处即可）。

| 代码 | 公司 | SA Quant | 加入日期 |
|------|------|----------|--------|
| CSTM | Constellium SE | Strong Buy | 2026-03-05 |
| BNPQY | BNP Paribas SA | Strong Buy | 2026-03-05 |
| ORLA | Orla Mining Ltd. | Strong Buy | 2026-03-05 |
| ECO | Okeanis Eco Tankers Corp. | Strong Buy | 2026-03-05 |
| AU | AngloGold Ashanti plc | Strong Buy | 2026-03-05 |
| FSM | Fortuna Mining Corp. | Strong Buy | 2026-03-05 |
| SHG | Shinhan Financial Group | Strong Buy | 2026-03-05 |
| BWMX | Betterware de México | Strong Buy | 2026-03-05 |
| GM | General Motors | Strong Buy | 2026-03-05 |
| BCS | Barclays PLC | Strong Buy | 2026-03-05 |
| MYRG | MYR Group Inc. | Strong Buy | 2026-03-05 |
| HMY | Harmony Gold Mining | Strong Buy | 2026-03-05 |
| DRH | DiamondRock Hospitality | Strong Buy | 2026-03-05 |
| NNGRY | NN Group N.V. | Strong Buy | 2026-03-05 |
| SEZL | Sezzle Inc. | Strong Buy | 2026-03-05 |
| DB | Deutsche Bank | Strong Buy | 2026-03-05 |
| SYM | Symbotic Inc. | Strong Buy | 2026-03-05 |
| ENVA | Enova International | Strong Buy | 2026-03-05 |
| JAZZ | Jazz Pharmaceuticals | Strong Buy | 2026-03-05 |
| NWG | NatWest Group plc | Strong Buy | 2026-03-05 |
| AUB | Atlantic Union Bankshares | Strong Buy | 2026-03-05 |
| GTY | Getty Realty Corp. | Strong Buy | 2026-03-05 |
| BAP | Credicorp Ltd. | Strong Buy | 2026-03-05 |
| SQM | Sociedad Química y Minera | Strong Buy | 2026-03-05 |
| KGS | Kodiak Gas Services | Strong Buy | 2026-03-05 |
| GLNCY | Glencore plc | Strong Buy | 2026-03-05 |
| CFG | Citizens Financial Group | Strong Buy | 2026-03-05 |
| HST | Host Hotels & Resorts | Strong Buy | 2026-03-05 |
| XHR | Xenia Hotels & Resorts | Strong Buy | 2026-03-05 |
| HRTG | Heritage Insurance Holdings | Strong Buy | 2026-03-05 |
| BTG | B2Gold Corp. | Strong Buy | 2026-03-05 |
| HASI | HA Sustainable Infrastructure Capital | Strong Buy | 2026-03-05 |
| NUTX | Nutex Health Inc. | Strong Buy | 2026-03-05 |
| HPE | Hewlett Packard Enterprise | Strong Buy | 2026-03-05 |
| TNL | Travel + Leisure Co. | Strong Buy | 2026-03-05 |
| INFU | InfuSystem Holdings | Strong Buy | 2026-03-05 |
| BAER | Bridger Aerospace Group | Strong Buy | 2026-03-05 |

---

## 港股

> 港股股票池（手动维护）。Yahoo Finance 数据源（格式如 0700.HK）。
> 代码格式：数字.HK（如 0700.HK、9988.HK）

### 恒生科技指数成分股

| 代码 | 名称 |
|------|------|
| 0700.HK | 腾讯控股 |
| 9988.HK | 阿里巴巴 |
| 3690.HK | 美团 |
| 9618.HK | 京东集团 |
| 1810.HK | 小米集团 |
| 9888.HK | 百度集团 |
| 2382.HK | 舜宇光学科技 |
| 9961.HK | 携程集团 |
| 9999.HK | 网易 |
| 1044.HK | 恒安国际 |
| 1211.HK | 比亚迪股份 |
| 2319.HK | 蒙牛乳业 |
| 6623.HK | 医脉通 |
| 6690.HK | 海尔智家 |
| 0966.HK | 金山软件 |
| 2688.HK | 安永 |
| 0635.HK | 中国软件国际 |
| 0256.HK | 冠君产业信托 |
| 0175.HK | 吉利汽车 |
| 0001.HK | 长和 |
| 0011.HK | 恒生银行 |
| 0016.HK | 新鸿基地产 |
| 0017.HK | 新世界发展 |
| 0066.HK | 港铁公司 |
| 0175.HK | 吉利 |
| 0688.HK | 中国海外发展 |
| 0823.HK | 领展房产基金 |
| 0868.HK | 信和置业 |
| 1038.HK | 长江基建集团 |
| 1044.HK | 恒安 |
| 1093.HK | 石药集团 |
| 1109.HK | 华润置地 |
| 1177.HK | 中国生物制药 |
| 1209.HK | 金隅集团 |
| 1211.HK | 比亚迪 |
| 1299.HK | 友邦保险 |
| 1347.HK | 华虹半导体 |
| 1355.HK | 龙光集团 |
| 1378.HK | 中国淀粉 |
| 1448.HK | 猪八戒 |
| 1515.HK | 华润医药 |
| 1559.HK | 穗高新 |
| 1755.HK | 融创中国 |
| 1810.HK | 小米 |
| 1876.HK | 百济神州 |
| 1900.HK | 中国儿童护理 |
| 1928.HK | 金沙中国 |
| 1966.HK | 中骏集团 |
| 2002.HK | 中信证券 |
| 2018.HK | 瑞声科技 |
| 2038.HK | 富智康 |
| 2068.HK | 中铝国际 |
| 2088.HK | 中国淀粉 |
| 2111.HK | 恒安集团 |
| 2130.HK | 中国联通 |
| 2150.HK | 奈雪的茶 |
| 2196.HK | 复星医药 |
| 2202.HK | 万科企业 |
| 2238.HK | 广汽集团 |
| 2282.HK | 敏华控股 |
| 2313.HK | 申洲国际 |
| 2319.HK | 蒙牛 |
| 2330.HK | 协合新能源 |
| 2338.HK | 潍柴动力 |
| 2342.HK | 京信通信 |
| 2355.HK | 宝龙地产 |
| 2388.HK | 中银香港 |
| 2600.HK | 中国铝业 |
| 2628.HK | 中国人寿 |
| 2688.HK | 安永 |
| 2698.HK | 魏桥创业 |
| 2700.HK | 金蝶国际 |
| 2727.HK | 上海医药 |
| 2777.HK | 富力地产 |
| 2866.HK | 中集集团 |
| 2883.HK | 中海油田服务 |
| 2912.HK | 恒安国际 |
| 2984.HK | 汇丰控股 |
| 3001.HK | 京东健康 |
| 3319.HK | 雅戈尔 |
| 3320.HK | 华润医药 |
| 3328.HK | 交通银行 |
| 3333.HK | 中国恒大 |
| 3345.HK | 中国飞鹤 |
| 3360.HK | 富士康 |
| 3377.HK | 远洋集团 |
| 3383.HK | 中国建筑 |
| 3606.HK | 福耀玻璃 |
| 3688.HK | 信义光能 |
| 3690.HK | 美团 |
| 3692.HK | 翰森制药 |
| 3709.HK | 宝龙商业 |
| 3725.HK | 上美股份 |
| 3796.HK | 融创服务 |
| 3818.HK | 中国动态 |
| 3888.HK | 金山云 |
| 3898.HK | 小鹏汽车 |
| 3900.HK | 绿城中国 |
| 3906.HK | 平安健康 |
| 3988.HK | 中国银行 |
| 4151.HK | 昭衍新药 |
| 4240.HK | 诺诚健华 |
| 4292.HK | 碧生源 |
| 4315.HK | 阿里健康 |
| 4385.HK | 迅雷网络 |
| 4411.HK | 乐享集团 |
| 4565.HK | 复宏汉霖 |
| 4680.HK | 泡泡玛特 |
| 4755.HK | 叮当健康 |
| 479.HK | 百胜中国 |
| 4988.HK | 森松国际 |
| 5515.HK | 中国铝业 |
| 5519.HK | 中国再保险 |
| 5575.HK | 微创医疗 |
| 5635.HK | 时代天使 |
| 5785.HK | 吉利 |
| 5964.HK | 欧舒丹 |
| 6030.HK | 中信建投 |
| 6055.HK | 中信银行 |
| 6098.HK | 平安好医生 |
| 6169.HK | 滔搏 |
| 6626.HK | 昊海生物 |
| 6628.HK | 泰格医药 |
| 6690.HK | 海尔智家 |
| 6818.HK | 中信银行 |
| 6969.HK | 创梦天地 |
| 6993.HK | 蓝光发展 |
| 8060.HK | 新东方 |
| 8095.HK | 中国联通 |
| 8215.HK | 第一视频 |
| 8257.HK | 亚信科技 |
| 8262.HK | 映客 |
| 8690.HK | 医思健康 |
| 8785.HK | 融创 |
| 8802.HK | 龙湖集团 |
| 8839.HK | 海底捞 |
| 9027.HK | 华南城 |
| 9127.HK | 时代天使 |
| 9225.HK | 阳光房地产 |
| 9281.HK | 旭辉永升服务 |
| 9399.HK | 新城悦服务 |
| 9513.HK | 拨康视光 |
| 9600.HK | 猫眼娱乐 |
| 9618.HK | 京东 |
| 9696.HK | 天齐锂业 |
| 9812.HK | 香港交易所 |
| 9868.HK | 时代天使 |
| 9886.HK | 百度 |
| 9889.HK | 中国中铁 |
| 9896.HK | 联想集团 |
| 9900.HK | 泡泡玛特 |
| 9922.HK | 银城生活服务 |
| 9933.HK | 创梦天地 |
| 9955.HK | 阳光纸业 |
| 9960.HK | 网易 |
| 9961.HK | 携程 |
| 9966.HK | 康宁杰瑞 |
| 9973.HK | 汇量科技 |
| 9983.HK | 建滔集团 |
| 9988.HK | 阿里巴巴 |
| 9999.HK | 网易 |
| 9968.HK | 京东健康 |
| 6099.HK | 招商银行 |
| 6837.HK | 海通证券 |
| 6913.HK | 植华 |
| 6928.HK | 天喔国际 |
| 9602.HK | 宝氪 |
| 0688.HK | 中国海外发展 |

### 国企股（H股）

| 代码 | 名称 |
|------|------|
| 0941.HK | 中国移动 |
| 0992.HK | 联想集团 |
| 1038.HK | 长江基建 |
| 1088.HK | 中国神华 |
| 1177.HK | 中国生物制药 |
| 1186.HK | 中国铁建 |
| 1211.HK | 比亚迪 |
| 1288.HK | 农业银行 |
| 1336.HK | 新华保险 |
| 1339.HK | 中国人民保险 |
| 1355.HK | 龙光集团 |
| 1398.HK | 工商银行 |
| 1608.HK | 维亚生物 |
| 1766.HK | 中国中车 |
| 1772.HK | 赣锋锂业 |
| 1789.HK | 福莱特玻璃 |
| 1800.HK | 中国交通建设 |
| 1818.HK | 招金矿业 |
| 1833.HK | 银泰黄金 |
| 1860.HK | 工商银行 |
| 1880.HK | 中国银行 |
| 1898.HK | 中煤能源 |
| 1919.HK | 中远海控 |
| 1988.HK | 民生银行 |
| 2008.HK | 熠华国际 |
| 2314.HK | 申洲国际 |
| 2329.HK | 国药控股 |
| 2601.HK | 中国太保 |
| 2607.HK | 招商局港口 |
| 2628.HK | 中国人寿 |
| 2727.HK | 上海医药 |
| 2883.HK | 中海油田服务 |
| 3328.HK | 交通银行 |
| 3688.HK | 信义光能 |
| 3988.HK | 中国银行 |
| 6098.HK | 平安好医生 |
| 6108.HK | 电讯盈科 |
| 6837.HK | 海通证券 |
| 6913.HK | 植华 |
| 8095.HK | 中国联通 |
| 9396.HK | 郑州银行 |
| 9668.HK | 民生银行 |
| 9969.HK | 诺诚健华 |

### 恒生指数成分股（HSI）

| 代码 | 名称 |
|------|------|
| 0001.HK | 长和 |
| 0002.HK | 中华电力 |
| 0003.HK | 香港中华煤气 |
| 0005.HK | 汇丰控股 |
| 0006.HK | 电能实业 |
| 0012.HK | 恒基兆业 |
| 0016.HK | 新鸿基地产 |
| 0027.HK | 银河娱乐 |
| 0066.HK | 港铁公司 |
| 0101.HK | 恒隆集团 |
| 0175.HK | 吉利汽车 |
| 0241.HK | 阿里健康 |
| 0267.HK | 招商局集团 |
| 0285.HK | 万洲国际 |
| 0288.HK | 双汇发展 |
| 0291.HK | 华润啤酒 |
| 0300.HK | 美的集团 |
| 0316.HK | 东方海外国际 |
| 0322.HK | 康师傅控股 |
| 0386.HK | 中国石化 |
| 0388.HK | 香港交易所 |
| 0669.HK | 创科实业 |
| 0688.HK | 中国海外发展 |
| 0700.HK | 腾讯控股 |
| 0762.HK | 中国联通 |
| 0823.HK | 领展房产基金 |
| 0836.HK | 华润电力 |
| 0857.HK | 中国石油 |
| 0868.HK | 信义光能 |
| 0881.HK | 中升控股 |
| 0883.HK | 中国海洋石油 |
| 0939.HK | 建设银行 |
| 0941.HK | 中国移动 |
| 0960.HK | 龙湖集团 |
| 0968.HK | 联想集团 |
| 0981.HK | 中芯国际 |
| 0992.HK | 联想集团 |
| 1024.HK | 快手 |
| 1038.HK | 长江基建 |
| 1044.HK | 恒安国际 |
| 1088.HK | 中国神华 |
| 1093.HK | 石药集团 |
| 1099.HK | 国药集团 |
| 1109.HK | 华润置地 |
| 1113.HK | 长江实业 |
| 1177.HK | 中国生物制药 |
| 1209.HK | 华润万象生活 |
| 1211.HK | 比亚迪 |
| 1299.HK | 友邦保险 |
| 1378.HK | 中国宏桥 |
| 1398.HK | 工商银行 |
| 1810.HK | 小米集团 |
| 1876.HK | 周大福 |
| 1928.HK | 金沙中国 |
| 1929.HK | 安踏体育 |
| 1997.HK | 九龙仓集团 |
| 2015.HK | 理想汽车 |
| 2020.HK | 申洲国际 |
| 2057.HK | 申洲国际 |
| 2269.HK | 药明生物 |
| 2313.HK | 申洲国际 |
| 2318.HK | 中国平安 |
| 2319.HK | 蒙牛乳业 |
| 2331.HK | 舜宇光学科技 |
| 2359.HK | 药明康德 |
| 2382.HK | 恒安国际 |
| 2388.HK | 浙商银行 |
| 2618.HK | 京东物流 |
| 2628.HK | 中国人寿 |
| 2688.HK | 新奥能源 |
| 2899.HK | 紫金矿业 |
| 3690.HK | 美团 |
| 3692.HK | 翰森制药 |
| 3968.HK | 招商银行 |
| 3988.HK | 中国银行 |
| 6618.HK | 京东健康 |
| 6690.HK | 海尔智家 |
| 6862.HK | 海底捞 |
| 9618.HK | 京东集团 |
| 9633.HK | 农夫山泉 |
| 9888.HK | 百度集团 |
| 9961.HK | 携程集团 |
| 9988.HK | 阿里巴巴 |
| 9992.HK | 泡泡玛特 |
| 9999.HK | 网易 |

### AI相关股

| 代码 | 名称 |
|------|------|
| 0700.HK | 腾讯控股 |
| 0988.HK | 百度集团 |
| 9999.HK | 网易 |
| 9961.HK | 携程集团 |
| 1810.HK | 小米集团 |
| 9618.HK | 京东集团 |
| 9988.HK | 阿里巴巴 |
| 3690.HK | 美团 |
| 2382.HK | 舜宇光学科技 |
| 1044.HK | 恒安国际 |
| 1211.HK | 比亚迪 |
| 0293.HK | 国泰航空 |
| 0669.HK | 创科实业 |
| 0788.HK | 中国铁塔 |
| 1347.HK | 华虹半导体 |
| 1818.HK | 招金矿业 |
| 2628.HK | 中国人寿 |
| 3328.HK | 交通银行 |
| 3688.HK | 信义光能 |
| 3988.HK | 中国银行 |
| 6108.HK | 电讯盈科 |
| 6837.HK | 海通证券 |
| 8095.HK | 中国联通 |
| 9696.HK | 天齐锂业 |
| 0912.HK | 恒安国际 |
| 0966.HK | 金山软件 |
| 0175.HK | 吉利汽车 |
| 1766.HK | 中国中车 |
| 1772.HK | 赣锋锂业 |
| 6098.HK | 平安好医生 |
| 6169.HK | 滔搏 |
| 0291.HK | 华润创业 |
| 0386.HK | 中国石油化工 |
| 2319.HK | 蒙牛乳业 |
| 0688.HK | 中国海外发展 |
| 0823.HK | 领展房产基金 |
| 0941.HK | 中国移动 |
| 0992.HK | 联想集团 |
| 1211.HK | 比亚迪 |
| 1299.HK | 友邦保险 |
| 1336.HK | 新华保险 |
| 1555.HK | 敏华控股 |
| 1755.HK | 融创中国 |
| 1880.HK | 中国银行 |
| 1919.HK | 中远海控 |
| 2196.HK | 复星医药 |
| 2202.HK | 万科企业 |
| 2238.HK | 广汽集团 |
| 2329.HK | 国药控股 |
| 2601.HK | 中国太保 |
| 2628.HK | 中国人寿 |
| 2698.HK | 魏桥创业 |
| 2912.HK | 恒安国际 |
| 2984.HK | 汇丰控股 |
| 3311.HK | 中国建筑 |
| 3688.HK | 信义光能 |
| 3690.HK | 美团 |
| 3692.HK | 翰森制药 |
| 3818.HK | 中国动态 |
| 3888.HK | 金山云 |
| 3900.HK | 绿城中国 |
| 3988.HK | 中国银行 |
| 4172.HK | 京东健康 |
| 4292.HK | 碧生源 |
| 6098.HK | 平安好医生 |
| 6108.HK | 电讯盈科 |
| 6169.HK | 滔搏 |
| 6618.HK | 京东健康 |
| 6837.HK | 海通证券 |
| 8285.HK | 久久集团 |
| 8785.HK | 融创 |
| 8802.HK | 龙湖集团 |
| 8818.HK | 弘阳地产 |
| 8839.HK | 海底捞 |
| 9399.HK | 新城悦服务 |
| 9600.HK | 猫眼娱乐 |
| 9688.HK | 百度 |
| 9812.HK | 香港交易所 |
| 9886.HK | 百度 |
| 9901.HK | 新东方 |
| 9988.HK | 阿里巴巴 |

### 红利股（高股息）

| 代码 | 名称 |
|------|------|
| 0001.HK | 长和 |
| 0002.HK | 中电控股 |
| 0003.HK | 香港中华煤气 |
| 0005.HK | 汇丰控股 |
| 0006.HK | 电能实业 |
| 0011.HK | 恒生银行 |
| 0066.HK | 港铁公司 |
| 0101.HK | 恒基兆业 |
| 0151.HK | 东亚银行 |
| 0293.HK | 国泰航空 |
| 0386.HK | 中国石油化工 |
| 0511.HK | 电视广播 |
| 0669.HK | 创科实业 |
| 0823.HK | 领展房产基金 |
| 0868.HK | 信和置业 |
| 0941.HK | 中国移动 |
| 0992.HK | 联想集团 |
| 1038.HK | 长江基建 |
| 1088.HK | 中国神华 |
| 1211.HK | 比亚迪 |
| 1288.HK | 农业银行 |
| 1336.HK | 新华保险 |
| 1398.HK | 工商银行 |
| 1555.HK | 敏华控股 |
| 1766.HK | 中国中车 |
| 1810.HK | 小米 |
| 1880.HK | 中国银行 |
| 1919.HK | 中远海控 |
| 1988.HK | 民生银行 |
| 2329.HK | 国药控股 |
| 2382.HK | 舜宇光学科技 |
| 2601.HK | 中国太保 |
| 2628.HK | 中国人寿 |
| 2698.HK | 魏桥创业 |
| 2908.HK | 特步国际 |
| 2912.HK | 恒安国际 |
| 2984.HK | 汇丰控股 |
| 3311.HK | 中国建筑 |
| 3688.HK | 信义光能 |
| 3818.HK | 中国动态 |
| 3900.HK | 绿城中国 |
| 3988.HK | 中国银行 |
| 6098.HK | 平安好医生 |
| 6108.HK | 电讯盈科 |
| 6837.HK | 海通证券 |
| 6913.HK | 植华 |
| 8095.HK | 中国联通 |
| 8285.HK | 久久集团 |
| 8818.HK | 弘阳地产 |
| 9399.HK | 新城悦服务 |
| 9696.HK | 天齐锂业 |
| 9812.HK | 香港交易所 |
| 9886.HK | 百度 |
| 9901.HK | 新东方 |

---

## 台股

> 台湾主要股票（TAIEX 加权指数核心成分股）。Yahoo Finance 数据源（格式如 2330.TW）。
> 代码格式：数字.TW（如 2330.TW、2454.TW）

| 代码 | 名称 | 简介 |
|------|------|------|
| 2330.TW | 台积电 | 全球最大晶圆代工厂，苹果/英伟达/AMD供应商，AI芯片核心制造 |
| 2454.TW | 联发科 | 全球第二大IC设计，智能手机AP市占前列，AIoT芯片 |
| 2317.TW | 鸿海 | 全球最大EMS代工厂，iPhone组装，电动车/AI服务器 |
| 2881.TW | 富邦金控 | 台湾最大金控之一，银行/保险/证券综合金融 |
| 2882.TW | 国泰金控 | 台湾最大金控，国泰人寿为旗舰，银行/保险 |
| 2891.TW | 中信金控 | 台湾主要金控，中国信托银行为旗舰 |
| 2886.TW | 兆丰金控 | 官股金控，兆丰银行为旗舰，外汇/国际贸易金融 |
| 1301.TW | 台塑 | 台湾最大石化集团，台塑四宝之首 |
| 1303.TW | 南亚 | 台塑集团，DRAM/化工/电子材料 |
| 1326.TW | 台化 | 台塑集团，芳香烃/塑料粒子 |
| 1308.TW | 台塑化 | 台塑集团，石油炼制/烯烃生产 |
| 2357.TW | 华硕 | 全球主板/显卡龙头，品牌PC/服务器 |
| 3045.TW | 广达 | 全球最大笔记型电脑代工厂，AI服务器/云端 |
| 3034.TW | 联咏科技 | 全球最大LCD驱动IC设计，TFT-LCD / AMOLED驱动 |
| 2379.TW | 瑞昱半导体 | 全球重要IC设计，WiFi/乙太网路/音讯芯片 |
| 8299.TW | 群联电子 | NAND Flash控制IC，存储方案 |
| 2308.TW | 台达电 | 全球电源供应器龙头，电动车充电/工业自动化/AI散热 |
| 2327.TW | 国巨 | 全球三大MLCC被动组件厂，AI服务器/车用电子 |
| 3037.TW | 欣兴电子 | 全球重要PCB/载板厂，ABF载板用于AI GPU |
| 2409.TW | 群创光电 | 面板双虎之一，TFT-LCD/触控模组 |
| 2344.TW | 友达光电 | 面板双虎之一，车用/工控面板 |
| 2408.TW | 南亚科 | DRAM制造，台塑集团，半导体记忆体 |
| 3443.TW | 创意电子 | 特殊IC设计服务，台积电体系，AI/HPC客製化芯片 |
| 2303.TW | 联电 | 全球第三大晶圆代工厂，成熟制程 |
| 3035.TW | 智原科技 | ASIC设计服务，AIoT/物联网芯片 |
| 5347.TW | 世界先进 | 8吋晶圆代工，电源管理/驱动IC |
| 3105.TW | 稳懋半导体 | 全球砷化镓PA龙头，射频元件，5G/AI手机 |
| 2455.TW | 全新光电 | 砷化镓磊晶片，射频/Power Amplifier |
| 8086.TW | 宏捷科 | 砷化镓代工，射频晶圆代工 |
| 2201.TW | 中华汽车 | 台湾汽车製造，CMC品牌，电动商用车 |
| 2801.TW | 彰银 | 彰化商业银行，地区银行 |

| 2880.TW | 华南金控 | 华南银行/保险/证券，金控 |

| 2892.TW | 第一金控 | 第一银行/保险/证券 |
| 5871.TW | 中租-KY | 台湾最大租赁公司，消费金融/企业融资 |
| 2615.TW | 万海航运 | 台湾第三大集装箱船公司，亚洲航线 |
| 2603.TW | 长荣海运 | 台湾第二大集装箱船公司，全球航线 |
| 2618.TW | 阳明海运 | 台湾国轮船队，货柜航运 |
| 2204.TW | 中华车 | 汽车製造（同2201） |
| 2345.TW | 智邦科技 | 乙太网路交换器/无线宽频，AI资料中心网路 |
| 2412.TW | 中华电信 | 台湾最大电信运营商，5G/固网 |
| 4904.TW | 远传电信 | 台湾第二大电信，5G/数位转型 |
| 2481.TW | 怡利电 | 车用显示器/抬头显示器 |
| 4564.TW | 精锐 | 精密机械/工具机 |
| 4966.TW | 趋势科技 | 全球资安软件公司，云端/终端安全 |
| 2609.TW | 阳明海运 | 货柜航运（同2618） |
| 2492.TW | 华新科 | 被动元件（电容/电阻），MLCC |
| 2701.TW | 万海 | 航运（同2615） |
| 2912.TW | 统一企业 | 食品/饮料/通路，统一超商持股 |
| 3005.TW | 神达 | 电子製造服务，服务器/储存 |
| 3532.TW | 台胜科 | 半导体硅晶圆材料 |
| 3702.TW | 大联大 | 电子组件通路，IC/半导体分销 |
| 6183.TW | 敦吉 | 车用电子/精密模具 |
| 6213.TW | 镱成 | 半导体封装测试 |
| 6770.TW | 镱利 | 连接器/精密组件 |
| 8011.TW | 镱通 | 网通设备 |
| 8081.TW | 镱嘉 | 网通/光通讯 |
| 8107.TW | 大众 | 电脑/週边设备 |
| 8200.TW | 镱科 | 电子材料/设备 |
| 8300.TW | 镱华 | 半导体设备 |
| 9802.TW | 镱华 | 电机/设备 |

---

## 美股 · 中概股（市值 > 100亿美元，在美国交易所上市）

> 美股中概股，筛选市值 > 100亿美元， NASDAQ / NYSE 上市。
> 手动添加，不依赖动态抓取。

| 代码 | 公司 | 简介 |
|------|------|------|
| PDD | 拼多多 | 电商平台，TEMU海外扩张，市值约 $1500亿 |
| BABA | 阿里巴巴 | 电商/云服务，市值约 $2000亿 |
| JD | 京东 | 电商/物流，市值约 $400亿 |
| NTES | 网易 | 游戏/互联网，市值约 $400亿 |
| TCOM | 携程 | 在线旅游，市值约 $300亿 |
| BIDU | 百度 | 搜索引擎/AI，市值约 $300亿 |
| LI | 理想汽车 | 新能源车，增程式SUV，市值约 $200亿 |
| BEKE | 贝壳找房 | 房地产平台，市值约 $150亿 |
| BILI | Bilibili | 视频/弹幕/游戏，市值约 $120亿 |
| NIO | 蔚来汽车 | 新能源车，电池租用BaaS，市值约 $120亿 |
| XPEV | 小鹏汽车 | 新能源车，NGP辅助驾驶，市值约 $120亿 |
| TME | 腾讯音乐 | 在线音乐/直播，市值约 $100亿 |
| KZ | Boss直聘 | 招聘平台，市值约 $100亿 |

---

## 待移出记录

> 从正式板块删除的股票放在这里。程序解析到此节时停止，以下股票**不计入**股票池。
> 格式：`| 代码 | 公司 | 移出日期 | 移出原因 |`

| 代码 | 公司 | 移出日期 | 移出原因 |
|------|------|---------|---------|
| *(暂无)* | | | |

---

*最后更新：2026-03-26（新增美股中概股13只：PDD/BABA/JD/NTES/TCOM/BIDU/LI/BEKE/BILI/NIO/XPEV/TME/KZ，市值均>100亿美元）*
*手动池总数：美股 638 + 港股 244 + 台股 60 = 942 只（去重后）*
*架构版本：Phase 9 启用（指数成分股已静态写入UNIVERSE.md，动态抓取已关闭）*
