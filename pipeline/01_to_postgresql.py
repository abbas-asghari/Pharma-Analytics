"""Create a self-contained PostgreSQL SQL import file (server not required)."""
import argparse
import shutil
import tempfile
from pathlib import Path
from pharma_common import DEFAULT_INPUT, COMPANY, PRODUCT, FACT, Extractor, ddl, VIEW, ANNUAL_VIEW, INDEXES

def copy_value(v):
    if v is None: return r'\N'
    if isinstance(v,bool): return 't' if v else 'f'
    return str(v).replace('\\','\\\\').replace('\t',r'\t').replace('\n',r'\n').replace('\r',r'\r')

def record(f,row): f.write('\t'.join(copy_value(v) for v in row)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default=DEFAULT_INPUT)
    p.add_argument('--output',default='pharma_1401_1404.sql')
    p.add_argument('--schema',default='pharma')
    p.add_argument('--years',nargs='+',type=int,default=[1401,1402,1403,1404])
    args=p.parse_args()
    import re
    if not re.fullmatch(r'[a-z_][a-z0-9_]*',args.schema): p.error('Schema must be a simple lowercase identifier')
    output=Path(args.output).resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError(f'Refusing to overwrite {output}')
    ex=Extractor(args.input,args.years,output.parent/(output.stem+'_audit'))
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        facts=Path(tmp)/'facts.tsv'
        with facts.open('w',encoding='utf-8',newline='\n') as f:
            for row in ex.rows(): record(f,row)
        staged=Path(tmp)/'ready.sql'
        with staged.open('w',encoding='utf-8',newline='\n') as f:
            f.write('-- Generated from the supplied Excel workbook. Amounts are IRR.\n')
            f.write('-- Annual totals have month=NULL; this does not imply full-year coverage.\n')
            f.write(f'BEGIN;\nCREATE SCHEMA {args.schema};\nSET search_path TO {args.schema}, public;\n')
            f.write(ddl(True)+'\n')
            f.write('COPY dim_company ('+','.join(COMPANY)+') FROM stdin;\n')
            for name,cid in ex.companies.items(): record(f,[cid,name])
            f.write('\\.\nCOPY dim_product ('+','.join(PRODUCT)+') FROM stdin;\n')
            for key,pid in ex.products.items(): record(f,[pid,*key])
            f.write('\\.\nCOPY fact_sales ('+','.join(FACT)+') FROM stdin;\n')
            with facts.open(encoding='utf-8') as src: shutil.copyfileobj(src,f)
            f.write('\\.\n'+INDEXES+'\n'+VIEW+'\n'+ANNUAL_VIEW+'\nCOMMIT;\nANALYZE;\n')
        staged.replace(output)
    ex.write_report()
    print(f'PostgreSQL SQL file: {output}',flush=True)

if __name__=='__main__': main()
