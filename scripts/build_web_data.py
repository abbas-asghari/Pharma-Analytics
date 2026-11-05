"""Build the annual browser database from the complete cleaned SQLite source.
No monthly comparisons are offered: monthly detail remains in the source DB.
"""
import argparse, gzip, json, shutil, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=ROOT.parent/'pharma_pipeline/pharma_1401_1404.sqlite')
args = parser.parse_args()
target = ROOT/'docs/data/dashboard.sqlite'
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    raise SystemExit('Output exists; choose a clean build directory or remove this generated file first.')
c = sqlite3.connect(target)
c.execute('ATTACH DATABASE ? AS src', (str(args.source.resolve()),))
c.executescript('''
CREATE TABLE dim_company AS SELECT * FROM src.dim_company;
CREATE UNIQUE INDEX company_pk ON dim_company(company_id);
CREATE TABLE dim_product AS SELECT product_id,irc,generic_name,brand_name_fa,brand_name_en,
 atc_code,atc_l1,is_otc,origin FROM src.dim_product;
CREATE UNIQUE INDEX product_pk ON dim_product(product_id);
CREATE TABLE fact_sales AS SELECT year,product_id,supplier_id,distributor_id,
 SUM(units_sold) AS units_sold,SUM(sales_consumer_rial) AS sales_consumer_rial,
 COUNT(*) AS source_rows,
 SUM(CASE WHEN units_sold IS NULL THEN 1 ELSE 0 END) AS missing_volume_rows,
 SUM(CASE WHEN sales_consumer_rial IS NULL THEN 1 ELSE 0 END) AS missing_value_rows
 FROM src.fact_sales GROUP BY year,product_id,supplier_id,distributor_id;
CREATE INDEX fact_year ON fact_sales(year);
CREATE INDEX fact_supplier ON fact_sales(supplier_id,year);
CREATE INDEX fact_distributor ON fact_sales(distributor_id,year);
CREATE VIEW v_sales_dashboard AS SELECT f.*,p.irc,p.generic_name,p.brand_name_fa,p.brand_name_en,
 p.atc_code,p.atc_l1,p.is_otc,p.origin,s.company_name AS supplier_name,d.company_name AS distributor_name
 FROM fact_sales f JOIN dim_product p USING(product_id)
 LEFT JOIN dim_company s ON s.company_id=f.supplier_id
 LEFT JOIN dim_company d ON d.company_id=f.distributor_id;
''')
expected=c.execute('SELECT year,COUNT(*),SUM(units_sold),SUM(sales_consumer_rial) FROM src.fact_sales GROUP BY year').fetchall()
actual=c.execute('SELECT year,SUM(source_rows),SUM(units_sold),SUM(sales_consumer_rial) FROM fact_sales GROUP BY year').fetchall()
for a,b in zip(expected,actual):
    assert a[:3]==b[:3], (a,b)
    assert abs(a[3]-b[3]) <= max(10,abs(a[3])*1e-12), (a,b)
assert len(expected)==len(actual)==4
assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
count=c.execute('SELECT COUNT(*) FROM fact_sales').fetchone()[0]
c.commit()
c.execute('DETACH DATABASE src')
c.execute('VACUUM')
c.close()
with target.open('rb') as src,gzip.open(str(target)+'.gz','wb',compresslevel=9) as dst:
    shutil.copyfileobj(src,dst)
metadata={'years':[r[0] for r in actual],'source_rows':sum(r[1] for r in actual),
 'browser_rows':count,'aggregation':'year, product version, supplier, distributor',
 'value_basis':'consumer price; IRR','month_in_source':1403,
 'checks':{'integrity':'ok','source_totals_match':True},
 'totals':[dict(zip(['year','source_rows','volume','value_rial'],r)) for r in actual]}
(target.parent/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(metadata),flush=True)
print('Compressed bytes:',Path(str(target)+'.gz').stat().st_size)
