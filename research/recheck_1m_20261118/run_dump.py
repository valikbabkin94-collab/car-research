import json,os,gzip,collections,subprocess,hashlib,datetime as dt
from pathlib import Path
import numpy as np
from market import Quotes,month_list,day_list,save,sha,M,H,DAY
from minute_engine import replay,funding_cash,DEN
B=Path('research/recheck_1m_20261118');I=B/'inputs'
def main():
 shard=int(os.environ['SHARD']);out=B/f'dump_shard{shard}';out.mkdir(exist_ok=True,parents=True);a=[r for r in json.load((I/'DUMP_FROZEN_SIGNALS.json').open())if r['status']=='CLOSED'];cs=json.load((I/'DUMP_FROZEN_CONTROLS.json').open());cm={r['source_id']:r for r in cs};sy=sorted(set(r['symbol']for r in a));owned=[s for n,s in enumerate(sy)if n%4==shard];quotes=Quotes('work/market');existing=set((Path('work/market')/'m1').glob('*'));fund=json.load((I/'DUMP_PUBLIC_FUNDING.json').open());manifest=[];rows=[];controls=[];errors=[]
 for n,s in enumerate(owned):
  aa=[r for r in a if r['symbol']==s];cc=[r for r in cs if r['symbol']==s and r['status']=='CLOSED'];windows=[(int(r['entry_ms']),int(r['entry_ms'])+72*H)for r in aa+cc];periods=set()
  for x,y in windows:
   for mo in month_list(x,y):
    if mo<'2026-11':periods.add(('monthly',mo))
    else:
     for day in day_list(max(x,1793491200000),y):periods.add(('daily',day))
  for kind,period in sorted(periods):
   try:rec=quotes.fetch(s,period,kind);manifest.append(dict(symbol=s,**rec))
   except Exception as e:errors.append(dict(symbol=s,period=period,kind=kind,error=type(e).__name__+':'+str(e)[:200]))
  q=quotes.load(s);q=q[(q[:,0]>=min(x for x,y in windows))&(q[:,0]<max(y for x,y in windows))]if len(q)else q
  ff=np.array(sorted(fund['rows'].get(s,[])),float).reshape(-1,2)
  def run(r):
   v=replay(q,r)
   if v['status']=='CLOSED':
    sens=replay(q,r,optimistic_entry_minute=True,delayed_new_BE=True);v['sensitivity_entryTP_delayedBE_R']=sens.get('R');v['funding_R']=None;v['funding_known']=False
    if len(ff):
     cash,count=funding_cash(q,v,ff[:,0],ff[:,1]);v['funding_R']=cash;v['funding_payments']=count;start=v['entry_ms'];end=v['exit_ms'];lo=np.searchsorted(ff[:,0],start,side='right')-1;hi=np.searchsorted(ff[:,0],end,side='right');stamps=ff[max(0,lo):min(len(ff),hi+1),0];v['funding_known']=bool(lo>=0 and fund['coverage_start']<=start and end<=fund['coverage_end']and start-ff[lo,0]<=9*H and end-ff[max(lo,hi-1),0]<=9*H and(np.diff(stamps)<=9*H).all())
    v['R_with_known_funding']=v['R']+(v['funding_R']or 0);v['funding_unknown_stress_R']=0. if v['funding_known']else(v['exit_ms']-v['entry_ms'])/(8*H)*.0001/DEN
   return v
  for r in aa:
   v=run(r);rows.append(dict(id=r['id'],symbol=s,signal_ms=r['signal_ms'],selected=r['selected'],original_R=r['R'],original_entry=r['entry'],**v));c=cm[r['id']]
   cv=run(c)if c['status']=='CLOSED'else dict(status='ORIGINAL_NOFILL',R=0.,funding_R=0.,funding_known=True,events=[])
   controls.append(dict(source_id=r['id'],symbol=s,signal_ms=r['signal_ms'],control_signal_ms=c['signal_ms'],original_control_R=c['R'],**cv))
  # Save completed symbols so a later failure does not lose prior replay results.
  for name,data in [('ACTUAL_ROWS.jsonl.gz',rows),('CONTROL_ROWS.jsonl.gz',controls)]:
   (out/name).write_bytes(gzip.compress(('\n'.join(json.dumps(r,allow_nan=False)for r in data)+'\n').encode(),mtime=0))
  quotes.cache={}
  print('SYMBOL_DONE',shard,n+1,'/',len(owned),s,'actual',len(rows),flush=True)
 for name,data in [('ACTUAL_ROWS.jsonl.gz',rows),('CONTROL_ROWS.jsonl.gz',controls)]:
  (out/name).write_bytes(gzip.compress(('\n'.join(json.dumps(r,allow_nan=False)for r in data)+'\n').encode(),mtime=0))
 newcache=Path('new_market_cache');newcache.mkdir(exist_ok=True)
 for path in (Path('work/market')/'m1').glob('*'):
  if path not in existing and path.is_file():
   import shutil
   shutil.copy2(path,newcache/path.name)
 save(out/'SOURCES.json',manifest);save(out/'SOURCE_ERRORS.json',errors);save(out/'INPUT_SHA256.json',{p.name:sha(p.read_bytes())for p in I.glob('*')if p.is_file()});save(out/'CHECKPOINT.json',dict(status='COMPLETE_WITH_EXPLICIT_GAPS',shard=shard,n_original=len(rows),statuses=dict(collections.Counter(r['status']for r in rows)),source_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),changed_signal_rules=False,changed_entry_reference=False,live_changes=0))
if __name__=='__main__':main()
