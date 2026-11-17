"""Two gated phases, immutable event artifacts, no order interfaces."""
import os,json,hashlib,subprocess,gzip
from pathlib import Path
import numpy as np
from hedge import *
B=Path('research/pf_hedged_20261117')
def main():
 phase=os.environ['MODEL_PHASE'];shard=int(os.environ['MODEL_SHARD']);folder=Path('paths')/f'shard{shard}';z=np.load(folder/'PATHS.npz',allow_pickle=False);es=json.load(open(folder/'INPUTS.json'));sp=json.load(open(folder/'SPLITS.json'));lo,mid,tail,hi=sp;d=Data();out=B/f'{phase}_shard{shard}';out.mkdir(parents=True,exist_ok=True);rows=[];nulls=[];baseline=[];audit=json.load(open(folder/'PARENT_CONTROL_REPRODUCTION.json'))
 save(out/'RECOVERED_PATH_CHECKPOINT.json',dict(status='RECOVERED_WITHOUT_RESIMULATION',source_run=44171887648,n=len(es),parent_checks=len(audit),max_old_control_netR_error=max([x['max_old_netR_error']or 0 for x in audit],default=0),path_sha256=hashlib.sha256((folder/'PATHS.npz').read_bytes()).hexdigest()))
 for i,(e,r)in enumerate(zip(es,z['actual'])):
  t=e['entry_ms'];assert t%F==0,'PF_ENTRY_NOT_5M_ALIGNED';part='H1'if lo<=t<=mid-72*H else'H2'if mid<=t<hi else'PURGE';l40=tail<=t<hi
  if phase=='train'and part!='H1':continue
  if phase.startswith('test')and part=='H1':continue
  common=dict(key=e['key'],symbol=e['symbol'],entry_ms=t,exit_ms=int(r[7])if r[0]==1 else None,split=part,last40=l40)
  s=short(d,e,r)
  baseline.append(dict(common,variant='NO_HEDGE',status='VALID'if s else'SHORT_DATA_GAP',**(dict(s,netR=s['short_R'],long_R=0.,long_fee_R=0.,long_funding_R=0.,n_members=0,funding_known=s['short_funding_known'],unknown_funding_stress_R=s['short_unknown_stress_R'])if s else{})))
  actual={k:evaluate(d,e,r,k)for k in['PUMP','ALT','BTC']}
  # Crossing H1 boundary cannot contribute to H1 selection, even when short was purged correctly.
  for k,v in actual.items():
   if part=='H1'and v.get('hedge_exit_close',0)>mid:v['status']='PURGE_HEDGE_CROSS_SPLIT'
  cs=np.full((6,200),np.nan)
  if phase.startswith('test')and(part=='H2'or l40)and r[0]==1:
   for c,cr in enumerate(z['controls'][i]):
    if cr[0]!=1:continue
    ce=dict(e,entry_ms=int(cr[31]),entry=float(cr[32]));cv={k:evaluate(d,ce,cr,k)for k in['PUMP','ALT','BTC']}
    for v,code in enumerate(CODES):
     q=scaled(cv[['PUMP','ALT','BTC'][v//2]],.5 if v%2==0 else 1.)
     if q['status']=='VALID':cs[v,c]=q['netR']
   # Hedge does not silently move random times with unavailable data.
  for v,code in enumerate(CODES):
   q=scaled(actual[['PUMP','ALT','BTC'][v//2]],.5 if v%2==0 else 1.);rows.append(dict(common,variant=code,**q));nulls.append(cs[v])
  if len(d.baskets)>20000:d.baskets.clear()
  if i%40==0:print('MODEL',phase,shard,i,'/',len(es),flush=True)
 with gzip.open(out/'ACTUAL_ROWS.jsonl.gz','wt')as f:
  for r in rows+baseline:f.write(json.dumps(finite(r),allow_nan=False)+'\n')
 np.savez_compressed(out/'CONTROL200.npz',netR=np.array(nulls),keys=np.array([r['key']for r in rows],dtype='S64'),variants=np.array([r['variant']for r in rows],dtype='S20'))
 save(out/'METRICS.json',{c:metrics([r for r in rows+baseline if r['variant']==c])for c in CODES+['NO_HEDGE']})
 save(out/'CHECKPOINT.json',dict(status='COMPLETE',phase=phase,shard=shard,code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),rows=len(rows),baseline_rows=len(baseline),source_run=44171887648,short_parameters_changed=False,live_changes=0))
if __name__=='__main__':main()
