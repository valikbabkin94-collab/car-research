"""Correct only terminal over-allocation in saved event journals, no market replay."""
import copy

def repair(r,s):
 events=r.get('events',[])
 if sum(e['fraction']for e in events)<=1+1e-8:return r,None
 left=1.;fixed=[]
 for e in events:
  f=min(left,float(e['fraction']))
  if f>1e-12:fixed.append(dict(e,fraction=f));left-=f
  if left<=1e-12:break
 assert left<1e-8,'OVERFILL_JOURNAL_NOT_CLOSED'
 assert fixed[-1]['time_ms']==events[-1]['time_ms'],'NONTERMINAL_OVERFILL_REQUIRES_REPLAY'
 out=copy.deepcopy(r);out['events']=fixed;out['terminal_overfill_repaired']=True
 delta=dict(post_key=r['post_key'],channel=r['channel'],policy=r['policy'],old_fraction_sum=sum(e['fraction']for e in events),new_fraction_sum=sum(e['fraction']for e in fixed),old_netR=r.get('net_R'),funding_unchanged_because_same_preterminal_exposure_and_exit_time=True)
 if r.get('net_R')is not None and r['status']=='CLOSED':
  entry=r['entry'];denom=r['risk_denominator'];side=r['side'];gross=sum(side*(e['price']/entry-1)*e['fraction']for e in fixed)/denom;fee=.00055*(1+sum(e['price']/entry*e['fraction']for e in fixed))/denom;limit=r['policy']in['O3','O5']or(s['channel']!='OLEG'and s['kind']=='TEXT'and r['policy']in['T1','AUTHOR']and s['entry_zone']is not None);slip=.0005*((0 if limit else 1)+sum(e['price']/entry*e['fraction']for e in fixed if not e['kind'].startswith('TP')))/denom;net=gross-fee-slip+r['funding_R'];out.update(gross_R=gross,execution_cost_R=fee+slip,fee_R=fee,slip_R=slip,price_R=gross-fee-slip,net_R=net,net_R_adverse=net-r.get('funding_stress_R',0)-fee-slip)
 delta['new_netR']=out.get('net_R');return out,delta
