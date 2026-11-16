"""Resume saved archive collection; never redo completed scenario results."""
import argparse,concurrent.futures as cf,datetime as dt,json,time
from pathlib import Path
import history as h

def repair(root):
 root=Path(root);audit=json.loads((root/'SOURCE_AUDIT.json').read_text());symbols=audit['symbols'];out=root/'h1';out.mkdir(exist_ok=True);http=h.HTTP(root);started=time.monotonic();done=[]
 def one(sym):
  target=out/(sym+'.json.gz');d=h.gzread(target) if target.exists() else dict(symbol=sym,bars=[],sources=[],absent_months=[],errors=[])
  if target.exists() and not d['errors']:return d
  months=[e['month'] for e in d['errors']] if target.exists() else ['2026-07','2026-08','2026-09','2026-10'];d['errors']=[]
  for month in sorted(set(months)):
   try:
    bars,receipt=h.candle_month(http,sym,month,'1h');old={b[0]:b for b in d['bars']}
    for b in bars:
     if h.WARM<=b[0]<h.END:
      if b[0] in old and old[b[0]]!=b:raise ValueError('CONFLICTING_REPAIRED_CANDLE')
      old[b[0]]=b
    d['bars']=sorted(old.values());d['sources'].append(receipt)
   except h.urllib.error.HTTPError as e:
    if e.code==404:d['absent_months'].append(month)
    else:d['errors'].append(dict(month=month,error='HTTP_'+str(e.code)))
   except Exception as e:d['errors'].append(dict(month=month,error=type(e).__name__+': '+str(e)))
  h.gzwrite(target,d);return d
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  for offset in range(0,len(symbols),4):
   if time.monotonic()-started>3000:raise RuntimeError('BOUNDED_RESUME_PAUSE')
   for d in pool.map(one,symbols[offset:offset+4]):done.append(dict(symbol=d['symbol'],rows=len(d['bars']),errors=d['errors'],absent_months=d['absent_months']))
   h.write(root/'COLLECTION_CHECKPOINT.json',dict(completed=len(done),total=len(symbols),symbols=done,mode='REUSE_COMPLETE_RETRY_ERRORS_OR_MISSING_ONLY'))
 h.write(root/'H1_MANIFEST.json',dict(archive_catalog_size=len(symbols),symbols=done,files={str(p.relative_to(root)):h.digest(p.read_bytes()) for p in out.glob('*.gz')}))

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default='results/s1-s3-history');a=p.parse_args();root=Path(a.out)
 if not (root/'S1_RESULTS.json').exists() or not (root/'S3_RESULTS.json').exists():
  repair(root);frames,index,ranks=h.make_ranks(root)
  if not (root/'S1_RESULTS.json').exists():h.s1(root,index,ranks)
  else:print('S1 complete: reused, no PnL rerun')
  if not (root/'S3_RESULTS.json').exists():h.s3(root,frames,index,ranks)
  else:print('S3 complete: reused, no PnL rerun')
 else:print('S1/S3 complete: collection and PnL not repeated')
 h.report(root)
if __name__=='__main__':main()
