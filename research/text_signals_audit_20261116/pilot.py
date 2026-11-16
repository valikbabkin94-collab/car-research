"""Small preregistered T2/T3 engineering pilot, never a channel validation."""
import json,gzip,sys,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from market import Quotes,Funding,save,M,H
from pilot_engine import simulate
P=Path(__file__).parent

def main():
 review=json.loads((P/'SEMANTIC_REVIEW_30.json').read_text());keys={r['post_key']for r in review['rows']if r['review_label']=='TEXT_DIRECTIONAL_CALL'};rows=json.loads(gzip.decompress((P/'inputs/TEXT_COHORT.json.gz').read_bytes()));selected=[r for r in rows if r['post_key']in keys];assert len(selected)==17;q=Quotes('work/market');fund=Funding('source','work/funding');out=[]
 for r in sorted(selected,key=lambda r:(r['symbol'],r['pub'])):
  bars=q.load(r['symbol']);entry=(r['pub']+M+M-1)//M*M;i=int(np.searchsorted(bars[:,0],entry))if len(bars)else 0
  for policy in ['T2','T3']:
   base=dict(channel=r['channel'],post_key=r['post_key'],symbol=r['symbol'],policy=policy,selection='PRE_PNL_TEXT_ONLY_SELF_REVIEW_SAMPLE',signal_ms=r['pub'])
   if i>=len(bars)or int(bars[i,0])!=entry:out.append(dict(base,status='DATA_GAP_ENTRY',net_R=None));continue
   p=dict(symbol=r['symbol'],signal_ms=r['pub'],observed_ms=r['pub']+M-1,entry_type='MARKET',side=1 if r['side']=='LONG'else -1,hold_hours=72,stop_fraction=.056)
   if policy=='T2':
    lo=int(np.searchsorted(bars[:,0],entry-24*H));past=bars[lo:i]
    if len(past)!=1440 or np.any(np.diff(past[:,0])!=M):out.append(dict(base,status='DATA_GAP_24H_FEATURE',net_R=None));continue
    stop=float(np.max(past[:,2])*1.01)if p['side']==-1 else float(np.min(past[:,3])*.99);price=float(bars[i,1]);width=p['side']*(price-stop)/price;p.update(absolute_stop=stop,tp_dist=[width,2*width],weights=[.5,.5])
   res=simulate(bars,p,1794614400000);cash=fund.cash(r['symbol'],res,bars)if res['status']=='CLOSED'else None;res.update(base,funding_R=cash,net_R=res.get('price_R')+cash if cash is not None else None);out.append(res)
 save(P/'PILOT_TRADES.json',out);summ=[]
 for policy in ['T2','T3']:
  allr=[r for r in out if r['policy']==policy];closed=[r for r in allr if r['status']=='CLOSED'];known=[r for r in closed if r['net_R']is not None];v=np.array([r['net_R']for r in known]);loss=float(-v[v<0].sum());summ.append(dict(policy=policy,attempts=len(allr),price_closed_n=len(closed),net_known_n=len(known),unknown_funding_n=len(closed)-len(known),price_R_ex_funding_sum=sum(r['price_R']for r in closed),net_R_known_subset_sum=float(v.sum())if len(v)else None,net_WR_known_subset=100*float(np.mean(v>0))if len(v)else None,net_PF_known_subset=float(v[v>0].sum())/loss if loss else None,status='INCONCLUSIVE_ENGINEERING_PILOT_NOT_CHANNEL_SELECTION'))
 save(P/'PILOT_SUMMARY.json',dict(sample_n=17,policies=summ,T1='NOT_RUN_AUTHOR_UPDATE_LINKING_NOT_VERIFIED',T4='NO_SPECULANTKA_EXPORT',limitations='Not all149,not the whole45 corpus; small self-reviewed random subset,not independent holdout; no statistical promotion; unknown funding not0; results never used to adjust classifier or parameters.'))
 print(summ)
if __name__=='__main__':main()
