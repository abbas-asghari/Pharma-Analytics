"""Compare the SQL actually used in the browser with the complete source DB."""
import argparse, json, math, sqlite3, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
queries=json.loads(subprocess.check_output(['node','-e',"process.stdout.write(JSON.stringify(require('./docs/queries.js').QUERY_DEFS))"],cwd=ROOT,text=True))
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=ROOT.parent/'pharma_pipeline/pharma_1401_1404.sqlite')
args=parser.parse_args()
source=sqlite3.connect(args.source)
web=sqlite3.connect(ROOT/'docs/data/dashboard.sqlite')
adapter='''WITH source_dashboard AS (SELECT v.*,1 AS source_rows,
 CASE WHEN units_sold IS NULL THEN 1 ELSE 0 END AS missing_volume_rows,
 CASE WHEN sales_consumer_rial IS NULL THEN 1 ELSE 0 END AS missing_value_rows
 FROM v_sales_dashboard v), filtered AS'''
base={'base':1401,'target':1402,'supplier':0,'distributor':0,'atc':'','otc':-1,'origin':'','search':'','pattern':'%%'}
supplier=web.execute('SELECT supplier_id FROM fact_sales WHERE year=1402 GROUP BY supplier_id ORDER BY SUM(sales_consumer_rial) DESC LIMIT 1').fetchone()[0]
distributor=web.execute('SELECT distributor_id FROM fact_sales WHERE year=1402 GROUP BY distributor_id ORDER BY SUM(units_sold) DESC LIMIT 1').fetchone()[0]
cases=[{}, {'supplier':supplier},{'distributor':distributor},{'atc':'?'},{'otc':1},
 {'origin':'وارداتی','atc':'L'}, {'base':1403,'target':1404},
 {'search':'AMOXICILLIN','pattern':'%AMOXICILLIN%'},{'search':'NO_MATCH_999','pattern':'%NO_MATCH_999%'}]
report=[]
for patch in cases:
    params=base|patch
    for key,sql in queries.items():
        source_sql=sql.replace('WITH filtered AS',adapter,1).replace('SELECT * FROM v_sales_dashboard WHERE','SELECT * FROM source_dashboard WHERE',1)
        expected=source.execute(source_sql,params).fetchall()
        actual=web.execute(sql,params).fetchall()
        assert len(actual)==len(expected),(key,params,'length')
        for a,b in zip(actual,expected):
            for av,bv in zip(a,b):
                if isinstance(av,(float,int)) and isinstance(bv,(float,int)):
                    assert math.isclose(av,bv,rel_tol=1e-11,abs_tol=10),(key,av,bv)
                else: assert av==bv,(key,av,bv)
    report.append({'filters':patch,'queries_verified':list(queries)})
# ATC partitions must add back to annual totals, including Unknown.
totals={r[0]:r[1:3] for r in web.execute(queries['totals'],base)}
cats=web.execute(queries['atc'],base).fetchall()
for year,(value,volume) in totals.items():
    assert math.isclose(sum(r[2] for r in cats if r[0]==year),value,rel_tol=1e-12)
    assert sum(r[3] for r in cats if r[0]==year)==volume
# Independent rankings: the amount/volume tables reuse exactly the same row order.
for key,role,metric in [('suppliers','supplier','sales_consumer_rial'),('distributors','distributor','units_sold')]:
    expected=[r[0] for r in source.execute(f'SELECT {role}_id FROM fact_sales WHERE year=1402 GROUP BY {role}_id ORDER BY SUM({metric}) DESC,{role}_id LIMIT 10')]
    assert [r[0] for r in web.execute(queries[key],base)]==expected
assert web.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
out={'status':'passed','filter_scenarios':report,'annual_partitions':'passed','top10_order':'passed','integrity':'ok','postgres_restore_tested':False}
(ROOT/'evidence/validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
# Rebuild the reader-friendly download files without changing browser queries.
from build_query_downloads import build
build()
print(f'Passed: {len(cases)*len(queries)} source-vs-browser query comparisons, annual partitions, independent top-10 rankings, integrity.')
