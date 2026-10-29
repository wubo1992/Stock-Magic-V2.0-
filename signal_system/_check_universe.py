#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from universe import manager
from universe.index_fetcher import get_index_symbols

# Get SP500 and Nasdaq100
sp500 = set(get_index_symbols(['sp500']))
nasdaq100 = set(get_index_symbols(['nasdaq100']))
index_only = sp500 | nasdaq100

print(f'S&P 500: {len(sp500)} 只')
print(f'Nasdaq 100: {len(nasdaq100)} 只')
print(f'合计（去重）: {len(index_only)} 只')

# 281 signal stocks
signals = ['ABSI', 'ACEL', 'ADM', 'AGL', 'AIQ', 'AKAM', 'ALAI', 'ALNT', 'AMN', 'ANRO', 'APGE', 'APLY', 'AR', 'ARCT', 'ARDT', 'ARKQ', 'ARMK', 'ASML', 'ASPN', 'ASRT', 'ATOM', 'ATRO', 'BB', 'BCRX', 'BEN', 'BG', 'BHE', 'BKR', 'BKSY', 'BLBD', 'BVS', 'BW', 'BWA', 'BWEN', 'BYD', 'CALY', 'CBOE', 'CDNA', 'CGNX', 'CGTL', 'CHGG', 'CMPS', 'CNC', 'CNEQ', 'COLD', 'CORZ', 'CRAK', 'CRBU', 'CSCO', 'CSX', 'CTMX', 'CTRI', 'CVGI', 'CVS', 'CWB', 'DAC', 'DARE', 'DDI', 'DELL', 'DGXX', 'DINO', 'DOC', 'DOCN', 'DTI', 'DVA', 'DWAS', 'DXYZ', 'EDSA', 'EES', 'EIS', 'ELA', 'ELMD', 'ELVN', 'EME', 'ENOR', 'ENPH', 'ERIC', 'ESE', 'ESTA', 'ET', 'ETON', 'ETR', 'EVC', 'EVRG', 'EWBC', 'F', 'FBCG', 'FBRX', 'FCFS', 'FEPI', 'FGI', 'FIVE', 'FLEX', 'FLNC', 'FLNT', 'FLYW', 'FNKO', 'FOX', 'FOXA', 'FRD', 'FRT', 'FTNT', 'GCTS', 'GDC', 'GDS', 'GHRS', 'GLBS', 'GLW', 'GNK', 'GNRC', 'GPRK', 'GRDN', 'GRNT', 'GSAT', 'GSBC', 'GTE', 'GWW', 'HLIO', 'HLIT', 'HPE', 'HST', 'HUT', 'HWM', 'HXL', 'ICLN', 'IDGT', 'IEX', 'IFF', 'IFRX', 'IGPT', 'IMKTA', 'IMPP', 'INR', 'INVE', 'IPI', 'ISTR', 'JAZZ', 'JBHT', 'JD', 'KFRC', 'KINS', 'KMT', 'KN', 'KNX', 'KODK', 'KOS', 'KTCC', 'KVHI', 'L', 'LFUS', 'LNG', 'LOCO', 'LRN', 'LSTR', 'LUNR', 'LWLG', 'LYB', 'MAR', 'MASS', 'MDGL', 'MGM', 'MNST', 'MO', 'MOV', 'MPC', 'MRAM', 'MRVI', 'MRVL', 'MSGM', 'MTCH', 'MU', 'MXL', 'NBIS', 'NEE', 'NI', 'NSA', 'NTR', 'NTRS', 'NVGS', 'NVTS', 'NYT', 'OCGN', 'OIH', 'OKE', 'OPTX', 'ORMP', 'OSS', 'OXY', 'PACS', 'PANL', 'PDC', 'PFG', 'PGEN', 'PL', 'PRPO', 'PSLV', 'PSX', 'PXS', 'QTUM', 'QUIK', 'RDCM', 'RDN', 'RDNW', 'RDZN', 'REG', 'REMX', 'RFIL', 'ROK', 'ROMA', 'RRC', 'RVI', 'RXT', 'SANM', 'SATL', 'SBUX', 'SCHL', 'SEDG', 'SFD', 'SGU', 'SII', 'SILA', 'SILJ', 'SIRI', 'SITM', 'SKM', 'SLDE', 'SNA', 'SPIR', 'SRPT', 'STT', 'STX', 'SWBI', 'SYNA', 'TBLA', 'TDIV', 'TECK', 'TERN', 'TGT', 'TGTX', 'TH', 'THM', 'TK', 'TRFK', 'TRGP', 'TRN', 'TROX', 'TRVI', 'TSEM', 'TWIN', 'TXN', 'UGA', 'UI', 'UNP', 'URG', 'USO', 'UTHR', 'UTI', 'VCYT', 'VIAV', 'VIK', 'VMD', 'VMI', 'VTR', 'VTRS', 'WATT', 'WDC', 'WEAT', 'WES', 'WH', 'WOLF', 'WSC', 'WST', 'WT', 'XFOR', 'XLK', 'XNTK', 'XPER', 'XSD', 'XTL', 'ZNTL', 'ZVRA']

signals_set = set(signals)
not_in_index = sorted(signals_set - index_only)
in_index = sorted(signals_set & index_only)

print(f'\n总共信号股票: {len(signals_set)}')
print(f'属于S&P500或Nasdaq100: {len(in_index)}')
print(f'不属于S&P500或Nasdaq100: {len(not_in_index)}')

print(f'\n========== 不属于S&P500或Nasdaq100的股票 ({len(not_in_index)}只) ==========')
for s in not_in_index:
    print(s)

print(f'\n========== 属于S&P500或Nasdaq100的股票 ({len(in_index)}只) ==========')
for s in in_index:
    print(s)