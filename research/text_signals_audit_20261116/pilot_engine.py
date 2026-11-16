"""Causal virtual M1 execution. No networking, bot or exchange interfaces."""
import math
import numpy as np
M=60000;H=3600000
TAKER=.00055;MAKER=.00055;SLIP=.0005

def simulate(q,p,end_bound,force=None,mirror_width=None):
 side=p.get('side',-1);observed=p['observed_ms'];first=(observed//M+1)*M;ttl=p.get('ttl_hours',8)*H;expires=observed+ttl
 out=dict(status='DATA_GAP_M1',symbol=p['symbol'],signal_ms=p['signal_ms'],observed_ms=observed,side=side,events=[],mfe_R=0.,mae_R=0.)
 if len(q)==0:return out
 k=int(np.searchsorted(q[:,0],first));entry=None;et=None;entry_i=None
 if force is not None:
  et=force[0];entry=force[1];k=int(np.searchsorted(q[:,0],et));entry_i=k
  if k>=len(q) or q[k,0]!=et:return out
 else:
  cursor=first
  while cursor+M<=min(expires,end_bound):
   if k>=len(q) or q[k,0]!=cursor:return out
   t,o,hi,lo,cl=q[k]
   if p.get('entry_type','LIMIT')=='MARKET':entry=o;et=int(t);entry_i=k;break
   limit=p['limit']
   if hi>=limit if side==-1 else lo<=limit:
    entry=max(o,limit) if side==-1 else min(o,limit);et=int(t);entry_i=k;break
   k+=1;cursor+=M
  if entry is None:out['status']='NOFILL' if expires<=end_bound else 'PENDING_RIGHT_CENSORED';return out
 if mirror_width is not None:width=mirror_width;stop=entry*(1-side*width)
 elif p.get('absolute_stop') is not None:stop=p['absolute_stop'];width=side*(entry-stop)/entry
 elif p.get('stop_distance_abs') is not None:width=p['stop_distance_abs']/entry;stop=entry*(1-side*width)
 else:width=p.get('stop_fraction',.056);stop=entry*(1-side*width)
 if not math.isfinite(width) or width<=0 or stop<=0:out['status']='REJECTED_INVALID_STOP';return out
 if p.get('tp_kind')=='ATR':dist=[p['atr']/entry*z for z in [1,2,3]]
 elif p.get('tp_kind')=='R':dist=[width*z for z in [1,2,3]]
 else:dist=p.get('tp_dist',[.021,.042,.063])
 targets=[entry*(1+side*d) for d in dist];weights=p.get('weights',[.5,.3,.2]) if dist else []
 if len(targets)!=len(weights) or any(x<=0 for x in targets):out['status']='REJECTED_INVALID_TARGETS';return out
 denom=width;entry_maker=p.get('entry_type','LIMIT')=='LIMIT'
 cost=(MAKER if entry_maker else TAKER+SLIP);gross=0.;left=1.;hit=0;be_from=None;trail_from=None;best=entry
 cutoff=min(et+int(p.get('hold_hours',72)*H),p.get('absolute_deadline',2**63-1));out.update(status='OPEN_RIGHT_CENSORED',entry_ms=et,entry=float(entry),initial_stop=float(stop),risk_fraction=float(width),risk_denominator=float(denom))
 def leave(kind,t,price,fraction,passive=False):
  nonlocal gross,cost,left
  gross+=side*(price/entry-1)*fraction;cost+=(MAKER if passive else TAKER+SLIP)*price/entry*fraction
  out['events'].append(dict(time_ms=int(t if kind=='TIME' else t+M),bar_ms=int(t),kind=kind,price=float(price),fraction=float(fraction)));left=max(0,left-fraction)
 for j in range(entry_i,len(q)):
  t,o,hi,lo,cl=q[j];t=int(t)
  if t+M>end_bound:break
  if t!=et+(j-entry_i)*M:out['status']='DATA_GAP_M1_HOLD';return out
  if t>=cutoff or p.get('time_if_no_tp_hours') and hit==0 and t>=et+p['time_if_no_tp_hours']*H:
   leave('TIME',t,o,left);break
  out['mfe_R']=max(out['mfe_R'],side*((hi if side==1 else lo)/entry-1)/width);out['mae_R']=max(out['mae_R'],-side*((lo if side==1 else hi)/entry-1)/width)
  if lo<=stop if side==1 else hi>=stop:
   price=min(o,stop) if side==1 else max(o,stop);kind='TRAIL' if trail_from is not None else 'BE' if be_from is not None else 'SL';leave(kind,t,price,left);break
  if t!=et:
   while hit<len(targets) and (hi>=targets[hit] if side==1 else lo<=targets[hit]):leave('TP'+str(hit+1),t,targets[hit],weights[hit],True);hit+=1
  if left<1e-9:break
  if p.get('trail_after_profit') is not None:
   best=max(best,hi) if side==1 else min(best,lo)
   if side*(best/entry-1)>=p['trail_after_profit']:
    next_stop=best*(1-side*p.get('trail_fraction',.04));stop=max(stop,next_stop) if side==1 else min(stop,next_stop);trail_from=t+M
  elif hit and p.get('trail_atr'):
   best=max(best,hi) if side==1 else min(best,lo);next_stop=best-side*p['trail_atr']*p['atr'];stop=max(stop,next_stop) if side==1 else min(stop,next_stop);trail_from=t+M
  elif hit and p.get('move_be',True):stop=entry*(1+side*.0011);be_from=t+M
 if left<1e-9:
  out.update(status='CLOSED',exit_ms=out['events'][-1]['time_ms'],gross_R=float(gross/denom),execution_cost_R=float(cost/denom),price_R=float((gross-cost)/denom),hold_hours=(out['events'][-1]['time_ms']-et)/H)
 return out
