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

## 当前手动池总数：517 只（含 S&P 500 503 只 + Nasdaq 100 101 只，去重后 517 只）

---

## 板块一：科技巨头（Mag 7）

| AAPL | Apple | 消费电子 + 服务生态 |
| MSFT | Microsoft | 云计算(Azure) + AI(Copilot) |
| NVDA | NVIDIA | AI芯片霸主，数据中心GPU |
| GOOGL | Alphabet | 搜索广告 + 云(GCP) + AI |
| TSLA | Tesla | 电动车 + 储能 + FSD |
| AMZN | Amazon | 电商 + 云计算(AWS) |
| META | Meta | 社交媒体 + 广告 + AI |

---

## 板块二：成长股（其他）

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

| LITE | Lumentum | 光收发器+激光，数据中心AI互连 |
| AAOI | Applied Optoelectronics | 高速光模块，AI数据中心 |
| MTSI | MACOM Technology Solutions | 光模块驱动芯片，高速互连 |
| AXTI | AXT Inc | 砷化镓/磷化铟基板，光电子器件材料 |
| GLW | Corning | 光纤光缆+特种玻璃，AI数据中心互连 |

---

## 板块五：清洁能源 / 核能

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

| AEM | Agnico Eagle Mines | 大型高质量金矿，低成本生产 |
| WPM | Wheaton Precious Metals | 贵金属流媒体(Streaming)模式，低风险 |
| RGLD | Royal Gold | 黄金Royalty/流媒体，稳定现金流 |
| AGI | Alamos Gold | 中型成长矿，多国矿山 |

---

## 板块八：医疗健康

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

| CB | Chubb | 全球最大财产险，巴菲特持仓 |
| TRV | Travelers Companies | 美国大型商业财险 |
| AFL | Aflac | 补充健康险，日本市场龙头 |
| MCO | Moody's | 信用评级+风险数据，强定价权 |
| SPGI | S&P Global | 评级+指数+数据，垄断性商业模式 |
| V | Visa | 全球支付网络，轻资产高利润 |
| MA | Mastercard | 全球支付网络，Visa竞争对手 |

---

## 板块十一：银行 / 投行

| JPM | JPMorgan Chase | 全球最大投资银行，综合金融 |
| BAC | Bank of America | 美国第二大商业银行 |
| GS | Goldman Sachs | 顶级投行，财富管理+交易 |
| MS | Morgan Stanley | 投行+财富管理，机构业务 |
| AXP | American Express | 高端信用卡，高净值客群 |

---

## 板块十二：科技平台（非半导体）

| ORCL | Oracle | 云数据库转型，AI基础设施受益 |
| CRM | Salesforce | 企业CRM龙头，AI Agent(Agentforce) |
| NFLX | Netflix | 流媒体盈利拐点，广告层增长 |

---

## 板块十三：工业 / 国防

| GE | GE Aerospace | 商用+军用航空发动机，高景气 |
| CAT | Caterpillar | 建筑/矿山设备，基建周期 |
| RTX | RTX Corporation | 国防(导弹)+航空发动机(普惠) |
| UPS | United Parcel Service | 全球快递物流 |
| HON | Honeywell | 工业自动化+航空电子+楼宇系统 |
| VRT | Vertiv Holdings | 数据中心电源/散热基础设施，AI算力支撑 |

---

## 板块十四：电信 / 基础设施

| T | AT&T | 美国大型电信，高股息，去杠杆中 |
| AMT | American Tower | 通信铁塔REIT，5G升级+全球扩张 |

---

## 板块十五：SaaS / 云软件

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

| PYPL | PayPal | 在线支付，Venmo+Braintree，转型中 |
| FIS | Fidelity National Information Services | 金融科技基础设施，银行+零售支付 |
| FISV | Fiserv | 支付处理+金融科技，Clover POS |
| XYZ | Block (Square) | 小微商家支付+现金应用(CashApp) |

---

## 板块十七：医疗器械 / 大型制药补充

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

| BABA | Alibaba Group | 中国电商+云计算(阿里云)，港股+美股双挂牌 |
| BIDU | Baidu | 中国搜索引擎+AI(文心一言)+自动驾驶 |
| JD | JD.com | 中国自营电商+物流，3C家电强项 |
| SE | Sea Limited | 东南亚电商(Shopee)+游戏(Garena)+金融 |
| PDD | PDD Holdings | 拼多多+Temu，极低价电商全球扩张 |

---

## 板块二十三：房地产 / REIT

| PLD | Prologis | 全球最大工业物流REIT，电商仓储受益 |
| PSA | Public Storage | 美国最大自助仓储REIT |
| O | Realty Income | 零售净租赁REIT，月付股息 |
| EQR | Equity Residential | 美国大型公寓REIT，城市核心地段 |
| WY | Weyerhaeuser | 木材+木材产品REIT，住宅建设受益 |

---

## 板块二十四：成长股补充（近年高成长）

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



## 板块 S：标普 500 成分股（静态写入，Wikipedia 定期更新）

| 代码 | 公司 | 简介 |
|------|------|------|
| A | A | S&P 500 成分股 |
| AAPL | Apple | S&P 500 成分股 |
| ABBV | AbbVie | S&P 500 成分股 |
| ABNB | ABNB | S&P 500 成分股 |
| ABT | Abbott Labs | S&P 500 成分股 |
| ACGL | ACGL | S&P 500 成分股 |
| ACN | Accenture | S&P 500 成分股 |
| ADBE | Adobe | S&P 500 成分股 |
| ADI | ADI | S&P 500 成分股 |
| ADM | ADM | S&P 500 成分股 |
| ADP | ADP | S&P 500 成分股 |
| ADSK | ADSK | S&P 500 成分股 |
| AEE | AEE | S&P 500 成分股 |
| AEP | AEP | S&P 500 成分股 |
| AES | AES | S&P 500 成分股 |
| AFL | AFL | S&P 500 成分股 |
| AIG | AIG | S&P 500 成分股 |
| AIZ | AIZ | S&P 500 成分股 |
| AJG | AJG | S&P 500 成分股 |
| AKAM | AKAM | S&P 500 成分股 |
| ALB | ALB | S&P 500 成分股 |
| ALGN | ALGN | S&P 500 成分股 |
| ALL | ALL | S&P 500 成分股 |
| ALLE | ALLE | S&P 500 成分股 |
| AMAT | Applied Materials | S&P 500 成分股 |
| AMCR | AMCR | S&P 500 成分股 |
| AMD | AMD | S&P 500 成分股 |
| AME | AME | S&P 500 成分股 |
| AMGN | Amgen | S&P 500 成分股 |
| AMP | AMP | S&P 500 成分股 |
| AMT | AMT | S&P 500 成分股 |
| AMZN | Amazon | S&P 500 成分股 |
| ANET | ANET | S&P 500 成分股 |
| AON | AON | S&P 500 成分股 |
| AOS | AOS | S&P 500 成分股 |
| APA | APA | S&P 500 成分股 |
| APD | APD | S&P 500 成分股 |
| APH | APH | S&P 500 成分股 |
| APO | APO | S&P 500 成分股 |
| APP | APP | S&P 500 成分股 |
| APTV | APTV | S&P 500 成分股 |
| ARE | ARE | S&P 500 成分股 |
| ARES | ARES | S&P 500 成分股 |
| ATO | ATO | S&P 500 成分股 |
| AVB | AVB | S&P 500 成分股 |
| AVGO | Broadcom | S&P 500 成分股 |
| AVY | AVY | S&P 500 成分股 |
| AWK | AWK | S&P 500 成分股 |
| AXON | AXON | S&P 500 成分股 |
| AXP | AXP | S&P 500 成分股 |
| AZO | AZO | S&P 500 成分股 |
| BA | BA | S&P 500 成分股 |
| BAC | Bank of America | S&P 500 成分股 |
| BALL | BALL | S&P 500 成分股 |
| BAX | BAX | S&P 500 成分股 |
| BBY | BBY | S&P 500 成分股 |
| BDX | Becton Dickinson | S&P 500 成分股 |
| BEN | BEN | S&P 500 成分股 |
| BF-B | BF-B | S&P 500 成分股 |
| BG | BG | S&P 500 成分股 |
| BIIB | Biogen | S&P 500 成分股 |
| BK | BK | S&P 500 成分股 |
| BKNG | BKNG | S&P 500 成分股 |
| BKR | BKR | S&P 500 成分股 |
| BLDR | BLDR | S&P 500 成分股 |
| BLK | BLK | S&P 500 成分股 |
| BMY | Bristol-Myers | S&P 500 成分股 |
| BR | BR | S&P 500 成分股 |
| BRK-B | Berkshire Hathaway | S&P 500 成分股 |
| BRO | BRO | S&P 500 成分股 |
| BSX | Boston Scientific | S&P 500 成分股 |
| BX | BX | S&P 500 成分股 |
| BXP | BXP | S&P 500 成分股 |
| C | C | S&P 500 成分股 |
| CAG | CAG | S&P 500 成分股 |
| CAH | CAH | S&P 500 成分股 |
| CARR | CARR | S&P 500 成分股 |
| CAT | CAT | S&P 500 成分股 |
| CB | CB | S&P 500 成分股 |
| CBOE | CBOE | S&P 500 成分股 |
| CBRE | CBRE | S&P 500 成分股 |
| CCI | CCI | S&P 500 成分股 |
| CCL | CCL | S&P 500 成分股 |
| CDNS | Cadence Design | S&P 500 成分股 |
| CDW | CDW | S&P 500 成分股 |
| CEG | CEG | S&P 500 成分股 |
| CF | CF | S&P 500 成分股 |
| CFG | CFG | S&P 500 成分股 |
| CHD | CHD | S&P 500 成分股 |
| CHRW | CHRW | S&P 500 成分股 |
| CHTR | CHTR | S&P 500 成分股 |
| CI | Cigna | S&P 500 成分股 |
| CIEN | CIEN | S&P 500 成分股 |
| CINF | CINF | S&P 500 成分股 |
| CL | CL | S&P 500 成分股 |
| CLX | CLX | S&P 500 成分股 |
| CMCSA | CMCSA | S&P 500 成分股 |
| CME | CME | S&P 500 成分股 |
| CMG | CMG | S&P 500 成分股 |
| CMI | CMI | S&P 500 成分股 |
| CMS | CMS | S&P 500 成分股 |
| CNC | CNC | S&P 500 成分股 |
| CNP | CNP | S&P 500 成分股 |
| COF | COF | S&P 500 成分股 |
| COIN | COIN | S&P 500 成分股 |
| COO | COO | S&P 500 成分股 |
| COP | COP | S&P 500 成分股 |
| COR | COR | S&P 500 成分股 |
| COST | Costco | S&P 500 成分股 |
| CPAY | CPAY | S&P 500 成分股 |
| CPB | CPB | S&P 500 成分股 |
| CPRT | CPRT | S&P 500 成分股 |
| CPT | CPT | S&P 500 成分股 |
| CRH | CRH | S&P 500 成分股 |
| CRL | CRL | S&P 500 成分股 |
| CRM | Salesforce | S&P 500 成分股 |
| CRWD | CrowdStrike | S&P 500 成分股 |
| CSCO | Cisco | S&P 500 成分股 |
| CSGP | CSGP | S&P 500 成分股 |
| CSX | CSX | S&P 500 成分股 |
| CTAS | CTAS | S&P 500 成分股 |
| CTRA | CTRA | S&P 500 成分股 |
| CTSH | CTSH | S&P 500 成分股 |
| CTVA | CTVA | S&P 500 成分股 |
| CVNA | CVNA | S&P 500 成分股 |
| CVS | CVS Health | S&P 500 成分股 |
| CVX | CVX | S&P 500 成分股 |
| D | D | S&P 500 成分股 |
| DAL | DAL | S&P 500 成分股 |
| DASH | DASH | S&P 500 成分股 |
| DD | DD | S&P 500 成分股 |
| DDOG | Datadog | S&P 500 成分股 |
| DE | DE | S&P 500 成分股 |
| DECK | DECK | S&P 500 成分股 |
| DELL | DELL | S&P 500 成分股 |
| DG | DG | S&P 500 成分股 |
| DGX | DGX | S&P 500 成分股 |
| DHI | DHI | S&P 500 成分股 |
| DHR | Danaher | S&P 500 成分股 |
| DIS | Walt Disney | S&P 500 成分股 |
| DLR | DLR | S&P 500 成分股 |
| DLTR | DLTR | S&P 500 成分股 |
| DOC | DOC | S&P 500 成分股 |
| DOV | DOV | S&P 500 成分股 |
| DOW | DOW | S&P 500 成分股 |
| DPZ | DPZ | S&P 500 成分股 |
| DRI | DRI | S&P 500 成分股 |
| DTE | DTE | S&P 500 成分股 |
| DUK | DUK | S&P 500 成分股 |
| DVA | DVA | S&P 500 成分股 |
| DVN | DVN | S&P 500 成分股 |
| DXCM | Dexcom | S&P 500 成分股 |
| EA | EA | S&P 500 成分股 |
| EBAY | EBAY | S&P 500 成分股 |
| ECL | ECL | S&P 500 成分股 |
| ED | ED | S&P 500 成分股 |
| EFX | EFX | S&P 500 成分股 |
| EG | EG | S&P 500 成分股 |
| EIX | EIX | S&P 500 成分股 |
| EL | EL | S&P 500 成分股 |
| ELV | ELV | S&P 500 成分股 |
| EME | EME | S&P 500 成分股 |
| EMR | EMR | S&P 500 成分股 |
| EOG | EOG | S&P 500 成分股 |
| EPAM | EPAM | S&P 500 成分股 |
| EQIX | EQIX | S&P 500 成分股 |
| EQR | EQR | S&P 500 成分股 |
| EQT | EQT | S&P 500 成分股 |
| ERIE | ERIE | S&P 500 成分股 |
| ES | ES | S&P 500 成分股 |
| ESS | ESS | S&P 500 成分股 |
| ETN | ETN | S&P 500 成分股 |
| ETR | ETR | S&P 500 成分股 |
| EVRG | EVRG | S&P 500 成分股 |
| EW | Edwards Lifesciences | S&P 500 成分股 |
| EXC | EXC | S&P 500 成分股 |
| EXE | EXE | S&P 500 成分股 |
| EXPD | EXPD | S&P 500 成分股 |
| EXPE | EXPE | S&P 500 成分股 |
| EXR | EXR | S&P 500 成分股 |
| F | F | S&P 500 成分股 |
| FANG | FANG | S&P 500 成分股 |
| FAST | FAST | S&P 500 成分股 |
| FCX | FCX | S&P 500 成分股 |
| FDS | FDS | S&P 500 成分股 |
| FDX | FDX | S&P 500 成分股 |
| FE | FE | S&P 500 成分股 |
| FFIV | FFIV | S&P 500 成分股 |
| FICO | FICO | S&P 500 成分股 |
| FIS | FIS | S&P 500 成分股 |
| FISV | FISV | S&P 500 成分股 |
| FITB | FITB | S&P 500 成分股 |
| FIX | FIX | S&P 500 成分股 |
| FOX | FOX | S&P 500 成分股 |
| FOXA | FOXA | S&P 500 成分股 |
| FRT | FRT | S&P 500 成分股 |
| FSLR | FSLR | S&P 500 成分股 |
| FTNT | Fortinet | S&P 500 成分股 |
| FTV | FTV | S&P 500 成分股 |
| GD | GD | S&P 500 成分股 |
| GDDY | GDDY | S&P 500 成分股 |
| GE | GE | S&P 500 成分股 |
| GEHC | GEHC | S&P 500 成分股 |
| GEN | GEN | S&P 500 成分股 |
| GEV | GEV | S&P 500 成分股 |
| GILD | Gilead | S&P 500 成分股 |
| GIS | GIS | S&P 500 成分股 |
| GL | GL | S&P 500 成分股 |
| GLW | GLW | S&P 500 成分股 |
| GM | GM | S&P 500 成分股 |
| GNRC | GNRC | S&P 500 成分股 |
| GOOG | GOOG | S&P 500 成分股 |
| GOOGL | Alphabet | S&P 500 成分股 |
| GPC | GPC | S&P 500 成分股 |
| GPN | GPN | S&P 500 成分股 |
| GRMN | GRMN | S&P 500 成分股 |
| GS | GS | S&P 500 成分股 |
| GWW | GWW | S&P 500 成分股 |
| HAL | HAL | S&P 500 成分股 |
| HAS | HAS | S&P 500 成分股 |
| HBAN | HBAN | S&P 500 成分股 |
| HCA | HCA | S&P 500 成分股 |
| HD | Home Depot | S&P 500 成分股 |
| HIG | HIG | S&P 500 成分股 |
| HII | HII | S&P 500 成分股 |
| HLT | HLT | S&P 500 成分股 |
| HOLX | HOLX | S&P 500 成分股 |
| HON | HON | S&P 500 成分股 |
| HOOD | HOOD | S&P 500 成分股 |
| HPE | HPE | S&P 500 成分股 |
| HPQ | HPQ | S&P 500 成分股 |
| HRL | HRL | S&P 500 成分股 |
| HSIC | HSIC | S&P 500 成分股 |
| HST | HST | S&P 500 成分股 |
| HSY | HSY | S&P 500 成分股 |
| HUBB | HUBB | S&P 500 成分股 |
| HUM | Humana | S&P 500 成分股 |
| HWM | HWM | S&P 500 成分股 |
| IBKR | IBKR | S&P 500 成分股 |
| IBM | IBM | S&P 500 成分股 |
| ICE | ICE | S&P 500 成分股 |
| IDXX | IDEXX | S&P 500 成分股 |
| IEX | IEX | S&P 500 成分股 |
| IFF | IFF | S&P 500 成分股 |
| INCY | INCY | S&P 500 成分股 |
| INTC | Intel | S&P 500 成分股 |
| INTU | Intuit | S&P 500 成分股 |
| INVH | INVH | S&P 500 成分股 |
| IP | IP | S&P 500 成分股 |
| IQV | IQVIA | S&P 500 成分股 |
| IR | IR | S&P 500 成分股 |
| IRM | IRM | S&P 500 成分股 |
| ISRG | Intuitive Surgical | S&P 500 成分股 |
| IT | IT | S&P 500 成分股 |
| ITW | ITW | S&P 500 成分股 |
| IVZ | IVZ | S&P 500 成分股 |
| J | J | S&P 500 成分股 |
| JBHT | JBHT | S&P 500 成分股 |
| JBL | JBL | S&P 500 成分股 |
| JCI | JCI | S&P 500 成分股 |
| JKHY | JKHY | S&P 500 成分股 |
| JNJ | Johnson & Johnson | S&P 500 成分股 |
| JPM | JPMorgan Chase | S&P 500 成分股 |
| KDP | KDP | S&P 500 成分股 |
| KEY | KEY | S&P 500 成分股 |
| KEYS | KEYS | S&P 500 成分股 |
| KHC | KHC | S&P 500 成分股 |
| KIM | KIM | S&P 500 成分股 |
| KKR | KKR | S&P 500 成分股 |
| KLAC | KLAC | S&P 500 成分股 |
| KMB | KMB | S&P 500 成分股 |
| KMI | KMI | S&P 500 成分股 |
| KO | Coca-Cola | S&P 500 成分股 |
| KR | KR | S&P 500 成分股 |
| KVUE | KVUE | S&P 500 成分股 |
| L | L | S&P 500 成分股 |
| LDOS | LDOS | S&P 500 成分股 |
| LEN | LEN | S&P 500 成分股 |
| LH | LH | S&P 500 成分股 |
| LHX | LHX | S&P 500 成分股 |
| LII | LII | S&P 500 成分股 |
| LIN | LIN | S&P 500 成分股 |
| LLY | Eli Lilly | S&P 500 成分股 |
| LMT | LMT | S&P 500 成分股 |
| LNT | LNT | S&P 500 成分股 |
| LOW | LOW | S&P 500 成分股 |
| LRCX | LRCX | S&P 500 成分股 |
| LULU | LULU | S&P 500 成分股 |
| LUV | LUV | S&P 500 成分股 |
| LVS | LVS | S&P 500 成分股 |
| LW | LW | S&P 500 成分股 |
| LYB | LYB | S&P 500 成分股 |
| LYV | LYV | S&P 500 成分股 |
| MA | Mastercard | S&P 500 成分股 |
| MAA | MAA | S&P 500 成分股 |
| MAR | MAR | S&P 500 成分股 |
| MAS | MAS | S&P 500 成分股 |
| MCD | McDonald's | S&P 500 成分股 |
| MCHP | MCHP | S&P 500 成分股 |
| MCK | MCK | S&P 500 成分股 |
| MCO | MCO | S&P 500 成分股 |
| MDLZ | MDLZ | S&P 500 成分股 |
| MDT | MDT | S&P 500 成分股 |
| MET | MET | S&P 500 成分股 |
| META | Meta | S&P 500 成分股 |
| MGM | MGM | S&P 500 成分股 |
| MKC | MKC | S&P 500 成分股 |
| MLM | MLM | S&P 500 成分股 |
| MMM | MMM | S&P 500 成分股 |
| MNST | MNST | S&P 500 成分股 |
| MO | MO | S&P 500 成分股 |
| MOH | MOH | S&P 500 成分股 |
| MOS | MOS | S&P 500 成分股 |
| MPC | MPC | S&P 500 成分股 |
| MPWR | MPWR | S&P 500 成分股 |
| MRK | Merck | S&P 500 成分股 |
| MRNA | Moderna | S&P 500 成分股 |
| MRSH | MRSH | S&P 500 成分股 |
| MS | MS | S&P 500 成分股 |
| MSCI | MSCI | S&P 500 成分股 |
| MSFT | Microsoft | S&P 500 成分股 |
| MSI | MSI | S&P 500 成分股 |
| MTB | MTB | S&P 500 成分股 |
| MTCH | MTCH | S&P 500 成分股 |
| MTD | Mettler-Toledo | S&P 500 成分股 |
| MU | MU | S&P 500 成分股 |
| NCLH | NCLH | S&P 500 成分股 |
| NDAQ | NDAQ | S&P 500 成分股 |
| NDSN | NDSN | S&P 500 成分股 |
| NEE | NEE | S&P 500 成分股 |
| NEM | NEM | S&P 500 成分股 |
| NFLX | Netflix | S&P 500 成分股 |
| NI | NI | S&P 500 成分股 |
| NKE | NKE | S&P 500 成分股 |
| NOC | NOC | S&P 500 成分股 |
| NOW | ServiceNow | S&P 500 成分股 |
| NRG | NRG | S&P 500 成分股 |
| NSC | NSC | S&P 500 成分股 |
| NTAP | NTAP | S&P 500 成分股 |
| NTRS | NTRS | S&P 500 成分股 |
| NUE | NUE | S&P 500 成分股 |
| NVDA | NVIDIA | S&P 500 成分股 |
| NVR | NVR | S&P 500 成分股 |
| NWS | NWS | S&P 500 成分股 |
| NWSA | NWSA | S&P 500 成分股 |
| NXPI | NXPI | S&P 500 成分股 |
| O | O | S&P 500 成分股 |
| ODFL | ODFL | S&P 500 成分股 |
| OKE | OKE | S&P 500 成分股 |
| OMC | OMC | S&P 500 成分股 |
| ON | ON | S&P 500 成分股 |
| ORCL | ORCL | S&P 500 成分股 |
| ORLY | ORLY | S&P 500 成分股 |
| OTIS | OTIS | S&P 500 成分股 |
| OXY | OXY | S&P 500 成分股 |
| PANW | Palo Alto Networks | S&P 500 成分股 |
| PAYC | PAYC | S&P 500 成分股 |
| PAYX | Paychex | S&P 500 成分股 |
| PCAR | PCAR | S&P 500 成分股 |
| PCG | PCG | S&P 500 成分股 |
| PEG | PEG | S&P 500 成分股 |
| PEP | PepsiCo | S&P 500 成分股 |
| PFE | Pfizer | S&P 500 成分股 |
| PFG | PFG | S&P 500 成分股 |
| PG | Procter & Gamble | S&P 500 成分股 |
| PGR | PGR | S&P 500 成分股 |
| PH | PH | S&P 500 成分股 |
| PHM | PHM | S&P 500 成分股 |
| PKG | PKG | S&P 500 成分股 |
| PLD | PLD | S&P 500 成分股 |
| PLTR | PLTR | S&P 500 成分股 |
| PM | PM | S&P 500 成分股 |
| PNC | PNC | S&P 500 成分股 |
| PNR | PNR | S&P 500 成分股 |
| PNW | PNW | S&P 500 成分股 |
| PODD | PODD | S&P 500 成分股 |
| POOL | POOL | S&P 500 成分股 |
| PPG | PPG | S&P 500 成分股 |
| PPL | PPL | S&P 500 成分股 |
| PRU | PRU | S&P 500 成分股 |
| PSA | PSA | S&P 500 成分股 |
| PSKY | PSKY | S&P 500 成分股 |
| PSX | PSX | S&P 500 成分股 |
| PTC | PTC | S&P 500 成分股 |
| PWR | PWR | S&P 500 成分股 |
| PYPL | PayPal | S&P 500 成分股 |
| Q | Q | S&P 500 成分股 |
| QCOM | Qualcomm | S&P 500 成分股 |
| RCL | RCL | S&P 500 成分股 |
| REG | REG | S&P 500 成分股 |
| REGN | Regeneron | S&P 500 成分股 |
| RF | RF | S&P 500 成分股 |
| RJF | RJF | S&P 500 成分股 |
| RL | RL | S&P 500 成分股 |
| RMD | ResMed | S&P 500 成分股 |
| ROK | ROK | S&P 500 成分股 |
| ROL | ROL | S&P 500 成分股 |
| ROP | ROP | S&P 500 成分股 |
| ROST | ROST | S&P 500 成分股 |
| RSG | RSG | S&P 500 成分股 |
| RTX | RTX | S&P 500 成分股 |
| RVTY | RVTY | S&P 500 成分股 |
| SBAC | SBAC | S&P 500 成分股 |
| SBUX | SBUX | S&P 500 成分股 |
| SCHW | SCHW | S&P 500 成分股 |
| SHW | SHW | S&P 500 成分股 |
| SJM | SJM | S&P 500 成分股 |
| SLB | SLB | S&P 500 成分股 |
| SMCI | SMCI | S&P 500 成分股 |
| SNA | SNA | S&P 500 成分股 |
| SNDK | SNDK | S&P 500 成分股 |
| SNPS | Synopsys | S&P 500 成分股 |
| SO | SO | S&P 500 成分股 |
| SOLV | SOLV | S&P 500 成分股 |
| SPG | SPG | S&P 500 成分股 |
| SPGI | SPGI | S&P 500 成分股 |
| SRE | SRE | S&P 500 成分股 |
| STE | STERIS | S&P 500 成分股 |
| STLD | STLD | S&P 500 成分股 |
| STT | STT | S&P 500 成分股 |
| STX | STX | S&P 500 成分股 |
| STZ | STZ | S&P 500 成分股 |
| SW | SW | S&P 500 成分股 |
| SWK | SWK | S&P 500 成分股 |
| SWKS | SWKS | S&P 500 成分股 |
| SYF | SYF | S&P 500 成分股 |
| SYK | Stryker | S&P 500 成分股 |
| SYY | SYY | S&P 500 成分股 |
| T | T | S&P 500 成分股 |
| TAP | TAP | S&P 500 成分股 |
| TDG | TDG | S&P 500 成分股 |
| TDY | TDY | S&P 500 成分股 |
| TECH | TECH | S&P 500 成分股 |
| TEL | TEL | S&P 500 成分股 |
| TER | TER | S&P 500 成分股 |
| TFC | TFC | S&P 500 成分股 |
| TGT | TGT | S&P 500 成分股 |
| TJX | TJX | S&P 500 成分股 |
| TKO | TKO | S&P 500 成分股 |
| TMO | Thermo Fisher | S&P 500 成分股 |
| TMUS | TMUS | S&P 500 成分股 |
| TPL | TPL | S&P 500 成分股 |
| TPR | TPR | S&P 500 成分股 |
| TRGP | TRGP | S&P 500 成分股 |
| TRMB | TRMB | S&P 500 成分股 |
| TROW | TROW | S&P 500 成分股 |
| TRV | TRV | S&P 500 成分股 |
| TSCO | TSCO | S&P 500 成分股 |
| TSLA | Tesla | S&P 500 成分股 |
| TSN | TSN | S&P 500 成分股 |
| TT | TT | S&P 500 成分股 |
| TTD | TTD | S&P 500 成分股 |
| TTWO | TTWO | S&P 500 成分股 |
| TXN | Texas Instruments | S&P 500 成分股 |
| TXT | TXT | S&P 500 成分股 |
| TYL | TYL | S&P 500 成分股 |
| UAL | UAL | S&P 500 成分股 |
| UBER | Uber | S&P 500 成分股 |
| UDR | UDR | S&P 500 成分股 |
| UHS | UHS | S&P 500 成分股 |
| ULTA | ULTA | S&P 500 成分股 |
| UNH | UnitedHealth | S&P 500 成分股 |
| UNP | UNP | S&P 500 成分股 |
| UPS | UPS | S&P 500 成分股 |
| URI | URI | S&P 500 成分股 |
| USB | USB | S&P 500 成分股 |
| V | Visa | S&P 500 成分股 |
| VICI | VICI | S&P 500 成分股 |
| VLO | VLO | S&P 500 成分股 |
| VLTO | VLTO | S&P 500 成分股 |
| VMC | VMC | S&P 500 成分股 |
| VRSK | VRSK | S&P 500 成分股 |
| VRSN | VRSN | S&P 500 成分股 |
| VRTX | Vertex | S&P 500 成分股 |
| VST | VST | S&P 500 成分股 |
| VTR | VTR | S&P 500 成分股 |
| VTRS | VTRS | S&P 500 成分股 |
| VZ | VZ | S&P 500 成分股 |
| WAB | WAB | S&P 500 成分股 |
| WAT | WAT | S&P 500 成分股 |
| WBD | WBD | S&P 500 成分股 |
| WDAY | WDAY | S&P 500 成分股 |
| WDC | WDC | S&P 500 成分股 |
| WEC | WEC | S&P 500 成分股 |
| WELL | WELL | S&P 500 成分股 |
| WFC | WFC | S&P 500 成分股 |
| WM | WM | S&P 500 成分股 |
| WMB | WMB | S&P 500 成分股 |
| WMT | Walmart | S&P 500 成分股 |
| WRB | WRB | S&P 500 成分股 |
| WSM | WSM | S&P 500 成分股 |
| WST | WST | S&P 500 成分股 |
| WTW | WTW | S&P 500 成分股 |
| WY | WY | S&P 500 成分股 |
| WYNN | WYNN | S&P 500 成分股 |
| XEL | XEL | S&P 500 成分股 |
| XOM | Exxon Mobil | S&P 500 成分股 |
| XYL | XYL | S&P 500 成分股 |
| XYZ | XYZ | S&P 500 成分股 |
| YUM | YUM | S&P 500 成分股 |
| ZBH | Zimmer Biomet | S&P 500 成分股 |
| ZBRA | ZBRA | S&P 500 成分股 |
| ZTS | ZTS | S&P 500 成分股 |

## 板块 N：纳斯达克 100 成分股（静态写入，Wikipedia 定期更新）

| 代码 | 公司 | 简介 |
|------|------|------|
| ALNY | ALNY | Nasdaq 100 成分股 |
| ARM | ARM | Nasdaq 100 成分股 |
| ASML | ASML | Nasdaq 100 成分股 |
| CCEP | CCEP | Nasdaq 100 成分股 |
| FER | FER | Nasdaq 100 成分股 |
| INSM | Insmed Incorporated | Nasdaq 100 成分股 |
| MELI | MELI | Nasdaq 100 成分股 |
| MRVL | MRVL | Nasdaq 100 成分股 |
| MSTR | MSTR | Nasdaq 100 成分股 |
| PDD | PDD | Nasdaq 100 成分股 |
| SHOP | SHOP | Nasdaq 100 成分股 |
| TEAM | Atlassian | Nasdaq 100 成分股 |
| TRI | TRI | Nasdaq 100 成分股 |
| ZS | Zscaler | Nasdaq 100 成分股 |

## 操作说明

### 添加股票
直接在对应板块的表格末尾加一行：
```
```
保存后，下次运行程序时自动生效。

### 删除股票
把那一行从板块表格中删除，移到末尾「待移出记录」节（保留历史记录）。

### 添加新板块
