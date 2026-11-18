"""Restore pinned P1-P3 source semantics; reuse every unaffected completed outcome."""
import json,gzip,collections,datetime as dt,os,subprocess,copy
from pathlib import Path
import numpy as np
from market import Quotes,Funding,save,month_list,day_list,M,H,DAY
from policies import plan,translated_control,ASOF
from engine import simulate
from run import normalize_funding_rows
B=Path('research/oleg_private_20261118');I=B/'inputs'
def load(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.load(p.open())
def money(r,q,fd,fund,sy):
 if r.get('status')=='NOFILL':r.update(net_R=0.,funding_R=0.,funding_known=True);return r
 if r.get('status')!='CLOSED':r['net_R']=None;return r
 ff=normalize_funding_rows(fd.get('rows',[]));ft=np.array([x['ts']for x in ff]);known=fund.known(sy,r['entry_ms'],r['exit_ms']);cash=0.
 for x in ff[np.searchsorted(ft,r['entry_ms'],side='left'):np.searchsorted(ft,r['exit_ms'],side='right')]:
  t=x['ts'];rate=x['rate'];payer=r['side']*rate>0
  if t==r['entry_ms']and not payer:continue
  k=np.searchsorted(q[:,0],t,side='left')-1
  if k<0 or t-q[k,0]>M:known=False;continue
  left=1-sum(e['fraction']for e in r['events']if e['time_ms']<t or(e['time_ms']==t and not payer));cash-=r['side']*max(0,left)*rate*q[k,4]/r['entry']/r['risk_denominator']
 r['funding_R']=float(cash);r['funding_known']=bool(known);r['net_R']=r['price_R']+float(cash);r['funding_stress_R']=0. if known else(r['exit_ms']-r['entry_ms'])/(8*H)*.0001/r['risk_denominator'];turn=1+sum(e['fraction']*e['price']/r['entry']for e in r['events']);r['fee_R']=.00055*turn/r['risk_denominator'];r['slip_R']=max(0,r['execution_cost_R']-r['fee_R']);r['net_R_adverse']=r['net_R']-r['funding_stress_R']-r['fee_R']-r['slip_R'];return r

def main():
 a=[];c=[];claims=[]
 for p in Path('original_results').glob('*_shard*'):
  a+=load(p/'ACTUAL.json.gz');c+=load(p/'CONTROL.json.gz');claims+=load(p/'CLAIMS.json.gz')
 oleg_before=json.dumps([[r for r in a if r['channel']=='OLEG'],[r for r in c if r['channel']=='OLEG']],sort_keys=True)
 plans={s['post_key']:s for s in load(I/'PLANS.json.gz')};assert len(a)==len(c)==len(plans)*7
 ref={r['post_key']:r['entry']for r in a if r['channel']!='OLEG'and r['policy']=='P1'and r.get('entry')};log=[];todo=[]
 for role,rs in [('actual',a),('control',c)]:
  for ix,r in enumerate(rs):
   s=plans[r['post_key']]
   if s['channel']=='OLEG'or s['kind']!='STRUCTURED'or r['policy']not in['P1','P2','AUTHOR']:continue
   price=ref.get(r['post_key']);side=1 if s['side']=='LONG'else-1
   stale=price is not None and any(side*(t-price)<=0 for t in s['targets'])
   if stale and r['policy']in['P1','AUTHOR']and r.get('entry'):
    log.append(dict(post_key=r['post_key'],policy=r['policy'],role=role,reason='ORIGINAL_ALL_TARGETS_GATE',old_status=r['status'],old_netR=r.get('net_R'),new_status='REJECTED_STALE_AUTHOR_TARGETS_SOURCE_GATE'));r.update(counterfactual_pre_gate_net_R=r.get('net_R'),status='REJECTED_STALE_AUTHOR_TARGETS_SOURCE_GATE',net_R=None,events_counterfactual=True);continue
   if any(e.get('kind')=='BE'for e in r.get('events',[])):todo.append((role,ix,r,s))
 qio=Quotes('work/market');fund=Funding('source','work/funding');syms=sorted(set(r['symbol']for role,ix,r,s in todo));errors=[]
 for sy in syms:
  jobs=[j for j in todo if j[2]['symbol']==sy];lo=min(min(s['available_ms'],r.get('control_available_ms')or s['available_ms'])for role,ix,r,s in jobs)-25*H
  for mo in month_list(lo,ASOF):
   periods=[(mo,'monthly')]if mo<'2026-11'else[(d,'daily')for d in day_list(max(lo,1793491200000),ASOF)]
   for per,kind in periods:
    try:qio.fetch(sy,per,kind)
    except Exception as e:errors.append(dict(symbol=sy,period=per,error=type(e).__name__))
   t=int(dt.datetime.fromisoformat(mo+'-01').replace(tzinfo=dt.timezone.utc).timestamp()*1000);end=int((dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).replace(day=28)+dt.timedelta(days=4)).replace(day=1).timestamp()*1000)
   if not fund.known(sy,t,min(ASOF,end)):
    try:fund.extend_month(sy,mo,complete_month=mo<'2026-11')
    except Exception:pass
  q=qio.load(sy)
  for role,ix,old,s in jobs:
   ss=s
   if role=='control':ss,error=translated_control(s,old['control_available_ms'],q,q)
   else:error=None
   p,err=plan(ss,old['policy'],q,role=='control')if error is None else(None,error)
   new=dict(status=err,net_R=None,events=[])if err else money(simulate(q,p,ASOF),q,fund.get(sy),fund,sy);common={k:v for k,v in old.items()if k in['channel','post_key','policy','pub','available_ms','kind','symbol','side','risk_signature_pct','edit_delay_ms','intent_expiry_ms','control_available_ms']};row=dict(common,**new);(a if role=='actual'else c)[ix]=row;log.append(dict(post_key=old['post_key'],policy=old['policy'],role=role,reason='SOURCE_BE_EXACT_ENTRY_NOT_FEE_BUFFER',old_status=old['status'],old_netR=old.get('net_R'),new_status=new['status'],new_netR=new.get('net_R')))
  qio.cache={};print('AUDITED_SYMBOL',sy,flush=True)
 assert oleg_before==json.dumps([[r for r in a if r['channel']=='OLEG'],[r for r in c if r['channel']=='OLEG']],sort_keys=True),'OLEG_OUTCOME_CHANGED'
 out=B/'verified_rows';out.mkdir(parents=True,exist_ok=True)
 for n,v in [('ACTUAL.json.gz',a),('CONTROL.json.gz',c),('CLAIMS.json.gz',claims)]: (out/n).write_bytes(gzip.compress(json.dumps(v,allow_nan=False,separators=(',',':')).encode(),mtime=0))
 save(out/'CONFORMANCE_LOG.json',log);save(out/'ERRORS.json',errors);save(out/'CHECKPOINT.json',dict(status='SOURCE_CONFORMANCE_COMPLETE',source_run=44270512713,actual_rows=len(a),control_rows=len(c),replayed_BE_cases=len(todo),static_gate_reclassified=sum(x['reason']=='ORIGINAL_ALL_TARGETS_GATE'for x in log),all_OLEG_outcomes_unchanged=True,unaffected_outcomes_reused=True,code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
 # Existing aggregator consumes the corrected case matrix; no new strategy search.
 import shutil
 d=Path('corrected_results/all_shard0');d.mkdir(parents=True,exist_ok=True)
 for n in['ACTUAL.json.gz','CONTROL.json.gz','CLAIMS.json.gz']:shutil.copy2(out/n,d/n)
 os.environ['RESULTS_ROOT']='corrected_results';os.environ['OUTPUT_STAGE']='verified_final';import finalize;finalize.main()
if __name__=='__main__':main()
