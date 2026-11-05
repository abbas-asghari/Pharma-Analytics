"""Streaming, reproducible Excel extraction; no source workbook modifications."""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
import openpyxl

DEFAULT_INPUT = r'C:\Users\Abbas\Desktop\Task\1405\month 8\13\Lyan\1401-1404.xlsx'
COMPANY = ['company_id', 'company_name']
PRODUCT = ['product_id','irc','generic_code','generic_name','substance_name',
           'brand_name_fa','brand_name_en','atc_code','atc_l1','is_otc','is_biologic',
           'is_licensed','manufacturer_country','brand_owner_country','origin',
           'registration_type','units_per_pack']
FACT = ['sales_id','year','month','product_id','distributor_id','supplier_id',
        'brand_owner_id','manufacturer_id','manufacturer_label_extra','packs_sold',
        'units_sold','sales_consumer_rial','sales_to_pharmacy_rial',
        'sales_to_distributor_rial','price_consumer_rial','price_pharmacy_rial',
        'price_distributor_rial','source_sheet','source_row','quality_flags']
NUMERIC = {'packs_sold','units_sold','sales_consumer_rial','sales_to_pharmacy_rial',
           'sales_to_distributor_rial','price_consumer_rial','price_pharmacy_rial',
           'price_distributor_rial','units_per_pack'}
IDS = {'company_id','product_id','sales_id','distributor_id','supplier_id',
       'brand_owner_id','manufacturer_id','year','month'}
BOOLS = {'is_otc','is_biologic','is_licensed'}
MONTHS = {s:i for i,s in enumerate('فروردین اردیبهشت خرداد تیر مرداد شهریور مهر آبان آذر دی بهمن اسفند'.split(),1)}
TRANSLATE = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩يك', '01234567890123456789یک')

def clean(v):
    if v is None: return None
    if isinstance(v,float) and v.is_integer(): v=int(v)
    s=unicodedata.normalize('NFKC',str(v)).translate(TRANSLATE)
    s=re.sub(r'[\u200b\u200c\u200d\ufeff\u00a0]', ' ',s)
    s=' '.join(s.split())
    return None if s.lower() in ('','-','null','none','nan') else s

def number(v):
    s=clean(v)
    if s is None: return None
    s=s.replace(',','').replace('٬','').replace('٫','.')
    d=Decimal(s)
    if not d.is_finite(): raise ValueError('nonfinite number')
    return d

def identifier(v):
    s=clean(v)
    if s and re.fullmatch(r'\d+\.0+',s): s=s.split('.')[0]
    return s

def flag(v):
    s=clean(v)
    if s is None: return None
    if s.lower() in ('1','1.0','true','yes','بله'): return True
    if s.lower() in ('0','0.0','false','no','خیر'): return False
    raise ValueError('unrecognized boolean')

ALIASES = {
 'distributor':['نام شرکت پخش'], 'supplier':['نام شرکت تامین کننده'],
 'brand_owner':['نام صاحب برند','صاحب نام تجاری'],
 'manufacturer':['نام شرکت تولید کننده','شرکت تولید کننده'],
 'manufacturer_label_extra':['نام لاتین شرکت تولید کننده'],
 'irc':['کد IRC محصول','IRC'], 'generic_code':['کد ژنریک'],
 'generic_name':['نام ژنریک'],'substance_name':['نام لاتین فهرست'],
 'brand_name_fa':['نام برند'],'brand_name_en':['نام لاتین برند'],
 'atc_code':['کد ATC'],'is_otc':['OTC'],'is_biologic':['بیولوژیک'],
 'is_licensed':['تحت لیسانس'],'manufacturer_country':['کشور تولید کننده'],
 'brand_owner_country':['کشور صاحب نام تجاری'],
 'origin':['تولیدی/وارداتی','تولیدی/ وارداتی'],
 'registration_type':['ثبتی/فوریتی'], 'units_per_pack':['تعداد در بسته'],
 'packs_sold':['تعداد فروش (بسته)','(تعداد فروش(بسته'],
 'units_sold':['فروش عددی'],
 'sales_consumer_rial':['فروش ریالی ( مبتنی بر قیمت مصرف کننده)',
                         'فروش ریالی ( مبتنی بر قیمت فروش به مصرف کننده)'],
 'sales_to_pharmacy_rial':['فروش ریالی ( مبتنی بر قیمت فروش به داروخانه)'],
 'sales_to_distributor_rial':['فروش ریالی ( مبتنی بر قیمت فروش به پخش)'],
 'price_consumer_rial':['قیمت فروش به مصرف کننده (ریال)'],
 'price_pharmacy_rial':['قیمت پخش به داروخانه (ریال)'],
 'price_distributor_rial':['قیمت تامین کننده به پخش (ریال)'], 'month':['ماه']}

def sql_type(c, postgres):
    if c in IDS: return 'BIGINT' if postgres else 'INTEGER'
    if c in BOOLS: return 'BOOLEAN' if postgres else 'INTEGER'
    if c in NUMERIC: return 'NUMERIC' # SQLite uses integer/real affinity.
    return 'TEXT'

def ddl(postgres):
    stmts=[]
    for name,cols in [('dim_company',COMPANY),('dim_product',PRODUCT),('fact_sales',FACT)]:
        defs=[f'{c} {sql_type(c,postgres)}'+(' PRIMARY KEY' if i==0 else '') for i,c in enumerate(cols)]
        if name=='dim_company': defs.append('UNIQUE(company_name)')
        if name=='fact_sales':
            defs += ['FOREIGN KEY(product_id) REFERENCES dim_product(product_id)']
            defs += [f'FOREIGN KEY({c}) REFERENCES dim_company(company_id)' for c in ['distributor_id','supplier_id','brand_owner_id','manufacturer_id']]
            defs += ['CHECK(year BETWEEN 1300 AND 1500)','CHECK(month IS NULL OR month BETWEEN 1 AND 12)', 'UNIQUE(source_sheet,source_row)']
        stmts.append(f'CREATE TABLE {name} ('+',\n'.join(defs)+');')
    return '\n'.join(stmts)

VIEW = '''CREATE VIEW v_sales_dashboard AS
SELECT f.*, p.irc, p.generic_code, p.generic_name, p.substance_name,
 p.brand_name_fa,p.brand_name_en,p.atc_code,p.atc_l1,p.is_otc,
 p.is_biologic,p.is_licensed,p.origin,p.registration_type,p.units_per_pack,
 p.manufacturer_country,p.brand_owner_country,
 d.company_name AS distributor_name,s.company_name AS supplier_name,
 b.company_name AS brand_owner_name,m.company_name AS manufacturer_name
FROM fact_sales f JOIN dim_product p ON p.product_id=f.product_id
LEFT JOIN dim_company d ON d.company_id=f.distributor_id
LEFT JOIN dim_company s ON s.company_id=f.supplier_id
LEFT JOIN dim_company b ON b.company_id=f.brand_owner_id
LEFT JOIN dim_company m ON m.company_id=f.manufacturer_id;'''
ANNUAL_VIEW = '''CREATE VIEW v_sales_annual AS
SELECT year, product_id, distributor_id, supplier_id, brand_owner_id, manufacturer_id,
 manufacturer_label_extra,
 SUM(packs_sold) AS packs_sold, SUM(units_sold) AS units_sold,
 SUM(sales_consumer_rial) AS sales_consumer_rial,
 SUM(sales_to_pharmacy_rial) AS sales_to_pharmacy_rial,
 SUM(sales_to_distributor_rial) AS sales_to_distributor_rial,
 COUNT(*) AS source_row_count, COUNT(DISTINCT month) AS reported_month_count,
 SUM(CASE WHEN sales_consumer_rial IS NULL THEN 1 ELSE 0 END) AS missing_value_rows,
 SUM(CASE WHEN units_sold IS NULL THEN 1 ELSE 0 END) AS missing_volume_rows
FROM fact_sales
GROUP BY year,product_id,distributor_id,supplier_id,brand_owner_id,manufacturer_id,manufacturer_label_extra;'''
INDEXES = '''CREATE INDEX ix_sales_year_month ON fact_sales(year,month);
CREATE INDEX ix_sales_year_supplier ON fact_sales(year,supplier_id);
CREATE INDEX ix_sales_year_distributor ON fact_sales(year,distributor_id);
CREATE INDEX ix_sales_product ON fact_sales(product_id);
CREATE INDEX ix_product_irc ON dim_product(irc);
CREATE INDEX ix_product_atc ON dim_product(atc_l1);'''

class Extractor:
    def __init__(self,path,years,report_dir):
        self.path=Path(path); self.years=years; self.report_dir=Path(report_dir)
        self.report_dir.mkdir(parents=True,exist_ok=True)
        self.companies={}; self.products={}
        self.report={'source':str(self.path.resolve()),'years':{},'headers':{},'issues':Counter()}

    def company(self,v):
        name=clean(v)
        if name is None: return None
        if name not in self.companies: self.companies[name]=len(self.companies)+1
        return self.companies[name]

    def rows(self):
        w=openpyxl.load_workbook(self.path,read_only=True,data_only=True)
        sid=0
        try:
            for year in self.years:
                s=w[str(year)]; it=iter(s.values); headers=next(it)
                self.report['headers'][str(year)]=list(headers)
                mapping={}
                for key,aliases in ALIASES.items():
                    matches=[i for i,h in enumerate(headers) if clean(h) in [clean(a) for a in aliases]]
                    if len(matches)>1: raise ValueError(f'Ambiguous columns: {year} {key}')
                    if matches: mapping[key]=matches[0]
                for required in ['irc','distributor','supplier','units_sold','sales_consumer_rial']:
                    if required not in mapping: raise ValueError(f'Missing {required} in {year}')
                stats={'rows':0,'blank_rows':0,'units_sold':Decimal(0),'sales_consumer_rial':Decimal(0),'months':Counter()}
                self.report['years'][str(year)]=stats
                for source_row,r in enumerate(it,2):
                    if not any(v is not None for v in r): stats['blank_rows']+=1; continue
                    raw={k:r[i] if i<len(r) else None for k,i in mapping.items()}
                    flags=[]; vals={}
                    for key in ALIASES:
                        v=raw.get(key)
                        try:
                            vals[key]=number(v) if key in NUMERIC else flag(v) if key in BOOLS else identifier(v) if key in ['irc','generic_code'] else clean(v)
                        except (InvalidOperation,ValueError):
                            raise ValueError(f'Invalid {key} at {year}!row {source_row}: {v!r}')
                    for key in ['irc','distributor','supplier','units_sold','sales_consumer_rial','atc_code','is_otc']:
                        if vals[key] is None: flags.append('missing_'+key)
                    atc=(vals['atc_code'] or '').upper().replace(' ','')
                    vals['atc_code']=atc or None
                    vals['atc_l1']=atc[0] if re.fullmatch(r'[ABCDGHJLMNPRSV][A-Z0-9]*',atc) else None
                    if atc and not vals['atc_l1']: flags.append('invalid_atc')
                    if vals['irc'] and (not vals['irc'].isdigit() or len(vals['irc'])!=16): flags.append('unusual_irc')
                    if vals['units_per_pack'] is not None and vals['units_per_pack']<=0: flags.append('nonpositive_pack_size')
                    for key in ['packs_sold','units_sold','sales_consumer_rial']:
                        if vals[key] is not None and vals[key]<0: flags.append('negative_'+key)
                    if all(vals[k] is not None for k in ['packs_sold','units_sold','units_per_pack']):
                        if abs(vals['packs_sold']*vals['units_per_pack']-vals['units_sold'])>Decimal('0.01'): flags.append('pack_unit_mismatch')
                    month=None
                    if 'month' in mapping:
                        month=MONTHS.get(vals['month'])
                        if month is None: raise ValueError(f'Unknown month at {year}:{source_row}: {vals["month"]}')
                    stats['months'][str(month)]+=1
                    key=tuple(vals.get(c) for c in PRODUCT[1:])
                    if key not in self.products: self.products[key]=len(self.products)+1
                    pid=self.products[key]
                    sid+=1; stats['rows']+=1
                    for c in ['units_sold','sales_consumer_rial']:
                        if vals[c] is not None: stats[c]+=vals[c]
                    for f in flags: self.report['issues'][f]+=1
                    fact=[sid,year,month,pid,*[self.company(vals[k]) for k in ['distributor','supplier','brand_owner','manufacturer']],
                          vals['manufacturer_label_extra'],*[vals[k] for k in FACT[9:17]],str(year),source_row,','.join(flags) or None]
                    yield fact
                    if stats['rows']%100000==0: print(f'{year}: {stats["rows"]:,} rows',flush=True)
                print(f'{year}: {stats["rows"]:,} rows complete',flush=True)
        finally: w.close()

    def write_report(self):
        self.report['company_count']=len(self.companies); self.report['product_version_count']=len(self.products)
        (self.report_dir/'quality_report.json').write_text(json.dumps(self.report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
