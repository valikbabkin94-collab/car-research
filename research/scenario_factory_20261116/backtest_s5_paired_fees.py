"""Same saved research executions, paired fee accounting only.
Maker execution is NOT proven. No downloads, new signals or strategy fitting.
"""
import gzip,json
from pathlib import Path
import numpy as np
LAB=Path(__file__).parent

def main():
 cfg=json.loads((LAB/'EXPERIMENT_S5.json').read_text());source=[json.loads(x) for x in gzip.open(LAB/'inputs/PF_RESEARCH_EXECUTIONS.jsonl.gz','rt')];cash={r['id']:r for r in (json.loads(x) for x in gzip.open(LAB/'inputs/PF_RESEARCH_FUNDING.jsonl.gz','rt'))};out=LAB/'S5_RESULTS';out.mkdir(exist_ok=True);rows=[]
 for r in source:
  result={'id':r['id'],'symbol':r['symbol'],'signal_ms':r['signal_ms'],'exit_ms':r.get('exit_ms'),'selected':r['selected'],'status':r['status'],'fee_saving_R':None,'taker_net_R':None,'maker_assumed_net_R':None,'funding_known':False}
  if r['status']=='CLOSED':
   legs=1+sum(e['fraction']*e['price']/r['entry'] for e in r['events']);taker=cfg['taker_per_leg']*legs;maker=cfg['maker_per_leg']+sum(e['fraction']*e['price']/r['entry']*(cfg['maker_per_leg'] if e['kind'].startswith('TP') else cfg['taker_per_leg']) for e in r['events']);slip=cfg['slippage_per_leg']*legs;delta=(taker-maker)/cfg['R_denominator'];result['fee_saving_R']=delta;result['funding_known']=cash.get(r['id'],{}).get('funding_known') is True;result['taker_price_R']=(r['gross_return']-taker-slip)/cfg['R_denominator'];result['maker_assumed_price_R']=result['taker_price_R']+delta
   if result['funding_known']:result['taker_net_R']=result['taker_price_R']+cash[r['id']]['funding_cash_R'];result['maker_assumed_net_R']=result['taker_net_R']+delta
  rows.append(result)
 tables=[];controls=[];rng=np.random.default_rng(cfg['seed'])
 for cohort in cfg['cohorts']:
  chosen=rows if cohort=='RAW' else [r for r in rows if r['selected']]
  for period,start,end in [('H1',cfg['start_ms'],cfg['half_ms']),('H2',cfg['half_ms'],cfg['end_ms']),('TAIL40',cfg['tail_ms'],cfg['end_ms']),('FULL',cfg['start_ms'],cfg['end_ms'])]:
   group=[r for r in chosen if start<=r['signal_ms']<end];cross=sum(r['status']=='CLOSED' and r['exit_ms']>=end for r in group);closed=[r for r in group if r['status']=='CLOSED' and r['exit_ms']<end];known=sorted([r for r in closed if r['funding_known']],key=lambda x:(x['exit_ms'],x['id']))
   for model,key in [('TAKER_REFERENCE','taker_net_R'),('ASSUMED_MAKER_ENTRY_TP_ONLY','maker_assumed_net_R')]:
    values=np.array([r[key] for r in known]);gain=float(values[values>0].sum());loss=float(-values[values<0].sum());eq=np.cumsum(values);dd=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq)) if len(values) else None
    tables.append({'cohort':cohort,'period':period,'model':model,'opportunities':len(group),'closed_contained':len(closed),'cross_boundary_closed':cross,'net_known_n':len(known),'unknown_funding_n':len(closed)-len(known),'nofill':sum(r['status']=='NOFILL' for r in group),'censored':sum(r['status']=='RIGHT_CENSORED' for r in group),'net_R_covered':float(values.sum()),'PF_covered':gain/loss if loss else None,'WR_percent_covered':100*float((values>0).mean()) if len(values) else None,'additive_closed_DD_R_covered':dd,'fee_saving_R_same_covered_fills':sum(r['fee_saving_R'] for r in known),'status':'INCONCLUSIVE_MAKER_FILLS_NOT_VERIFIED_PARTIAL_FUNDING','full_net_R':float(values.sum()) if len(known)==len(closed) else None})
   # Weekly paired fee-label swaps are an accounting placebo, NOT a trading-alpha test.
   blocks={}
   for r in known:blocks.setdefault(r['signal_ms']//604800000,0.);blocks[r['signal_ms']//604800000]+=r['fee_saving_R']
   savings=np.array(list(blocks.values()));null=[float(np.sum(savings*rng.choice([-1,1],size=len(savings)))) for _ in range(cfg['controls'])];controls.append({'cohort':cohort,'period':period,'replicates':len(null),'calendar_week_blocks':len(savings),'observed_fee_saving_R':float(savings.sum()),'random_label_saving_mean':float(np.mean(null)),'random_label_saving_p05':float(np.quantile(null,.05)),'random_label_saving_p95':float(np.quantile(null,.95)),'p_value':None,'interpretation':'PAIRED_ACCOUNTING_IDENTITY_NOT_EMPIRICAL_EXECUTION_OR_ALPHA_PROOF'})
 with gzip.open(out/'ALL_PAIRED_RESEARCH_EXECUTIONS.jsonl.gz','wt') as f:
  for r in rows:f.write(json.dumps(r,allow_nan=False)+'\n')
 (out/'TABLES.json').write_text(json.dumps(tables,indent=2,allow_nan=False)+'\n');(out/'CONTROLS.json').write_text(json.dumps(controls,indent=2)+'\n');print(json.dumps([r for r in tables if r['cohort']=='RAW' and r['period']=='FULL'],indent=2))
if __name__=='__main__':main()
