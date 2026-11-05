"""Create a dashboard-ready SQLite database for selected years (default: 1401-1404)."""
import argparse
import sqlite3
import tempfile
from decimal import Decimal
from pathlib import Path
from pharma_common import DEFAULT_INPUT, COMPANY, PRODUCT, FACT, Extractor, ddl, VIEW, ANNUAL_VIEW, INDEXES

def adapt(v):
    # sqlite NUMERIC affinity stores whole values as integers where possible.
    if isinstance(v,Decimal):
        if v==v.to_integral_value() and -(2**63)<=v<2**63: return int(v)
        return str(v)
    return v

def insert(conn,table,cols,rows):
    conn.executemany(f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})',
                     ([adapt(v) for v in row] for row in rows))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default=DEFAULT_INPUT)
    p.add_argument('--output',default='pharma_1401_1404.sqlite')
    p.add_argument('--years',nargs='+',type=int,default=[1401,1402,1403,1404])
    args=p.parse_args()
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError(f'Refusing to overwrite {output}')
    ex=Extractor(args.input,args.years,output.parent/(output.stem+'_audit'))
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        staged=Path(tmp)/'ready.sqlite'
        conn=sqlite3.connect(staged)
        try:
            conn.execute('PRAGMA foreign_keys=OFF')
            conn.executescript(ddl(False))
            with conn:
                batch=[]
                for row in ex.rows():
                    batch.append(row)
                    if len(batch)>=5000:
                        insert(conn,'fact_sales',FACT,batch);batch=[]
                if batch: insert(conn,'fact_sales',FACT,batch)
                insert(conn,'dim_company',COMPANY,([cid,n] for n,cid in ex.companies.items()))
                insert(conn,'dim_product',PRODUCT,([pid,*k] for k,pid in ex.products.items()))
            conn.execute('PRAGMA foreign_keys=ON')
            if conn.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Foreign-key validation failed')
            conn.executescript(INDEXES+'\n'+VIEW+'\n'+ANNUAL_VIEW)
            for y,stats in ex.report['years'].items():
                count,units,value=conn.execute('SELECT COUNT(*),SUM(units_sold),SUM(sales_consumer_rial) FROM fact_sales WHERE year=?',(int(y),)).fetchone()
                if count!=stats['rows'] or abs(Decimal(str(units))-stats['units_sold'])>Decimal('0.01'):
                    raise ValueError(f'Row or quantity reconciliation failed for {y}')
                # SQLite aggregates fractional numbers in binary floating point.
                difference=abs(Decimal(str(value))-stats['sales_consumer_rial'])
                tolerance=max(Decimal('1'),abs(stats['sales_consumer_rial'])*Decimal('1e-12'))
                if difference>tolerance: raise ValueError(f'Value reconciliation failed for {y}: {difference}')
                stats['sqlite_value_rounding_difference_rial']=difference
            if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Integrity check failed')
            conn.execute('ANALYZE');conn.commit()
        finally: conn.close()
        staged.replace(output)
    ex.write_report()
    print(f'SQLite database: {output}',flush=True)

if __name__=='__main__': main()
