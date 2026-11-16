"""Read public payment certificates; create legacy metadata view for audit only."""
import argparse,gzip,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)/'research_data/round3_20261115/funding_inputs_43722362909';out.mkdir(parents=True,exist_ok=True)
for file in (Path(a.source)/'symbols').glob('*.json.gz'):
 d=json.load(gzip.open(file,'rt'));complete=any(lo<=1698796800000 and hi>=1793491200000 for lo,hi in d['coverage']);record={'symbol':d['symbol'],'monthly_complete':complete,'rows':d['rows'],'coverage':d['coverage'],'note':'certificate view only, not full current-month funding proof'};(out/file.name).write_bytes(gzip.compress(json.dumps(record).encode()))
