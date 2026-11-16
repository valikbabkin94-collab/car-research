"""Continue only unfinished saved policy cases, never rerun any closed trade."""
import sys,json,time,datetime as dt,copy,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from run import LAB,OUT,I,CUTOFF,read,gz,render,jobs_for,collect_jobs
from market import Quotes,sha,save,M,DAY
from engine import simulate
from quality_review import gate

def unfinished(r):return r['policy']in ['P1','P2','P3']and r['status']in ['CENSORED_NEEDS_EXTENSION','DATA_GAP_HOLD_NEEDS_EXTENSION']and r.get('needed_from_ms',CUTOFF)<CUTOFF

def main():
 rawfile=OUT/'RAW_POLICY_TRADES_BEFORE_QUALITY.json.gz';rows=read(rawfile);original=copy.deepcopy(rows);gz(OUT/'RAW_POLICY_TRADES_BEFORE_CONTINUATION.json.gz',original);gz(OUT/'QUALIFIED_TRADES_BEFORE_CONTINUATION.json.gz',read(OUT/'ALL_POLICY_TRADES.json.gz'));oldquality=read(OUT/'QUALITY_REVIEW.json');save(OUT/'QUALITY_REVIEW_BEFORE_CONTINUATION.json',oldquality)
 signals={s['post_key']:s for s in read(I/'SIGNALS_WITH_UPDATES.json.gz')};q=Quotes('work/market');receipts=read(OUT/'ALL_SOURCE_RECEIPTS.json');probed={(r['symbol'],r['period'],r['kind'])for r in receipts};deadline=time.monotonic()+10*60;pending=[i for i,r in enumerate(rows)if unfinished(r)];initial=set(pending);calls=0;rounds=0;engine_sha=sha((LAB/'engine.py').read_bytes())
 for i in pending:assert rows[i]['engine_sha']==engine_sha
 while pending and time.monotonic()<deadline:
  jobs=[]
  for i in pending:
   r=rows[i];t=r['needed_from_ms'];d=dt.datetime.fromtimestamp(t/1000,dt.timezone.utc);monthend=(d.replace(day=28)+dt.timedelta(days=4)).replace(day=1,hour=0,minute=0,second=0,microsecond=0);end=min(CUTOFF,int(monthend.timestamp()*1000));jobs+=jobs_for(r['symbol'],t,end)
  jobs=sorted(set(jobs)-probed)
  if not jobs:break
  new=collect_jobs(q,jobs,deadline);receipts+=new;probed.update((r['symbol'],r['period'],r['kind'])for r in new);q.cache.clear();rounds+=1
  for i in pending:
   old=rows[i];s=signals[old['post_key']];fresh=simulate(q.load(old['symbol']),s,old['policy'],CUTOFF);calls+=1
   meta={k:old[k]for k in ['channel','post_key','pub','symbol','policy','engine_sha','input_sha','edited_visible','edited_update_n']if k in old};fresh.update(meta,continued_from_saved_unfinished=True);rows[i]=fresh
  pending=[i for i in pending if unfinished(rows[i])]
  print('CONTINUED',rounds,'pending',len(pending),'new_probes',len(new),flush=True)
 # Exhaustion exactly at the snapshot is censoring, not a request for future data.
 for r in rows:
  if r['policy']in ['P1','P2','P3']and r['status']=='CENSORED_NEEDS_EXTENSION'and r.get('needed_from_ms',0)>=CUTOFF:r['status']='CENSORED_ASOF'
 for i,(old,new)in enumerate(zip(original,rows)):
  if old['status']=='TRADE':assert old==new,'CLOSED_CASE_CHANGED'
  if old['policy']in ['P4','P5']:assert old==new,'LEGACY_REPLAYED'
 gz(rawfile,rows);qualified=gate(rows);render(qualified,list(signals.values()),receipts);save(OUT/'ALL_SOURCE_RECEIPTS.json',receipts)
 save(OUT/'CONTINUATION_CHECKPOINT.json',dict(initial_unfinished_policy_cases=len(initial),continued_simulator_calls=calls,rounds=rounds,newly_closed_cases=sum(original[i]['status']!='TRADE'and rows[i]['status']=='TRADE'for i in initial),remaining_unfinished_cases=len(pending),closed_trade_equality='PASS_ALL_EXISTING_CLOSED_ROWS_UNCHANGED',legacy_equality='PASS_NO_P4_P5_REPLAY',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),selection='ONLY_PREEXISTING_UNFINISHED_NO_RETURN_SELECTION',next='Only source gaps, friend handle and new prospective observations'))
 save(OUT/'QUALITY_REVIEW.json',dict(criterion=oldquality['criterion'],before_quality_sha256=sha(rawfile.read_bytes()),changed_closed_rows=sum(a['status']!=b['status']for a,b in zip(rows,qualified)),implementation='same_sign_independent_gate_after_continuing_only_unfinished',previous_quality_code_sha=oldquality['code_sha']))
 ck=read(LAB/'CHECKPOINT.json');ck.update(quality_review_completed=True,continuation_completed=True,existing_closed_and_legacy_unchanged=True);save(LAB/'CHECKPOINT.json',ck)
if __name__=='__main__':main()
