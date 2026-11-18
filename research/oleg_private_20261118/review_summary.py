"""Final reporting review only: zero new market simulations or price requests."""
import json,gzip,hashlib,os,subprocess,collections,shutil
from pathlib import Path
from policies import preflight
from market import save,H
B=Path('research/oleg_private_20261118');I=B/'inputs'
def load(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.load(p.open())
def fh(rows):return hashlib.sha256(json.dumps([r for r in rows if r['status']in['CLOSED','NOFILL']],sort_keys=True).encode()).hexdigest()
def main():
 roots=list(Path('verified_source').rglob('verified_rows/ACTUAL.json.gz'));assert len(roots)==1;root=roots[0].parent;a=load(root/'ACTUAL.json.gz');c=load(root/'CONTROL.json.gz');claims=load(root/'CLAIMS.json.gz');plans={s['post_key']:s for s in load(I/'PLANS.json.gz')};stats={s['channel']:s for s in load(I/'DATA_INVENTORY.json')};before=(fh(a),fh(c));changes=[]
 for role,rr in [('actual',a),('control',c)]:
  for r in rr:
   error=preflight(plans[r['post_key']],r['policy'])
   if error and r['status']!=error:
    assert r.get('net_R')is None,'PREFLIGHT_WOULD_CHANGE_EXECUTED_PNL';changes.append(dict(role=role,post_key=r['post_key'],policy=r['policy'],old_status=r['status'],new_status=error));r.update(pre_review_status=r['status'],status=error)
 assert before==(fh(a),fh(c)),'EXECUTED_FINANCIAL_OUTCOME_CHANGED'
 dest=Path('review_results/all_shard0');dest.mkdir(parents=True,exist_ok=True);out=B/'final_rows';out.mkdir(parents=True,exist_ok=True)
 for name,data in [('ACTUAL.json.gz',a),('CONTROL.json.gz',c),('CLAIMS.json.gz',claims)]:
  data=gzip.compress(json.dumps(data,allow_nan=False,separators=(',',':')).encode(),mtime=0);(dest/name).write_bytes(data);(out/name).write_bytes(data)
 save(out/'METADATA_ELIGIBILITY_REVIEW.json',changes);save(out/'FINANCIAL_IDENTITY.json',dict(actual_before_after_sha256=before[0],control_before_after_sha256=before[1],all_executed_outcomes_unchanged=True,new_market_simulations=0,role_filters_before_quote_lookup=True,censored_H2_last40_not_promoted=True))
 os.environ['RESULTS_ROOT']='review_results';os.environ['OUTPUT_STAGE']='completed';import finalize;finalize.main();final=B/'completed';by={(r['post_key'],r['policy']):r for r in a if r['channel']=='OLEG'};pairrows=[]
 for x,y in [('O0','O3'),('O0','O4'),('O3','O5'),('O4','AUTHOR')]:
  for period in['H1','H2','LAST40','FULL']:
   for subset in['ALL','TWO_AUTHOR_TP_ONLY']:
    rows=[];st=stats['OLEG']
    for key,s in plans.items():
     if s['channel']!='OLEG'or subset=='TWO_AUTHOR_TP_ONLY'and len(s['targets'])!=2:continue
     t=s['available_ms']
     if not(period=='FULL'or period=='H1'and t<st['midpoint']or period=='H2'and t>=st['midpoint']or period=='LAST40'and t>=st['last40']):continue
     u=by.get((key,x));v=by.get((key,y))
     if not u or not v or u.get('net_R')is None or v.get('net_R')is None:continue
     if period=='H1'and any(r.get('exit_ms',0)>=st['midpoint']or r['status']=='NOFILL'and r.get('intent_expiry_ms',0)>=st['midpoint']for r in[u,v]):continue
     rows.append((u,v))
    ar=sum(r['net_R']for r,s in rows);br=sum(s['net_R']for r,s in rows);pairrows.append(dict(policy_A=x,policy_B=y,period=period,subset=subset,n_common_known=len(rows),A_netR=ar,B_netR=br,B_minus_A_R=br-ar,includes_NOFILL_zero=True,author_risk_normalization_each_policy=True,live_replication_claim=False))
 save(final/'MATCHED_OLEG_POLICY_COMPARISON.json',pairrows);save(final/'SOURCE_CONFORMANCE_CHECKPOINT.json',load(root/'CHECKPOINT.json'));save(final/'FINAL_REVIEW_CHECKPOINT.json',dict(status='COMPLETE',primary_run=44270512713,conformance_run=44271797197,policy_rows=len(a),control_rows=len(c),metadata_corrections=len(changes),new_market_simulations=0,financial_hashes_preserved=True,code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),live_changes=0))
 if(root/'CONFORMANCE_LOG.json').exists():shutil.copy(root/'CONFORMANCE_LOG.json',final/'CONFORMANCE_LOG.json')
if __name__=='__main__':main()
