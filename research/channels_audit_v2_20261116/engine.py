"""Isolated minute-bar virtual author execution, no network or real orders."""
import numpy as np
M=60000
def simulate(q,s,policy,cutoff):
 sign=1 if s['side']=='LONG'else -1;start=s['pub']//M*M+M;out=dict(status='DATA_GAP_ENTRY',policy=policy,events=[],netR=None,source='BINANCE_1M_PROXY_EX_FUNDING',author_identity='UNKNOWN_CHANNEL_LEVEL')
 k=int(np.searchsorted(q[:,0],start))if len(q)else 0
 if k>=len(q)or int(q[k,0])!=start:out['needed_from_ms']=start;return out
 entry=float(q[k,1]);stop=float(s['stop']);targets=s['targets'];risk=sign*(entry-stop)
 if risk<=0 or any(sign*(float(t)-entry)<=0 for t in targets):out['status']='REJECTED_MARKET_GEOMETRY_OR_STALE_TARGET';return out
 if policy=='P1':tp=[float(targets[-1])];ws=[1.]
 elif policy=='P2':tp=list(map(float,targets[:2]));ws=[.5,.5]if len(tp)==2 else [1.]
 else:tp=[float(targets[0])];ws=[1.]
 ev=sorted(s.get('events',[]),key=lambda x:(x['effective_ms'],x['post_key']));ei=0;left=1.;gross=0.;slip=.0005*entry;hit=0;be=False;author_ignored=0;out.update(entry_ms=start,entry=entry,initial_stop=stop,risk_abs=risk,single_tp_fallback=policy=='P2'and len(tp)==1)
 def leave(t,kind,px,f,market=False,at_open=False):
  nonlocal left,gross,slip
  gross+=sign*(px-entry)*f
  if market:slip+=.0005*px*f
  left=max(0,left-f);out['events'].append(dict(time_ms=int(t if at_open else t+M),kind=kind,price=float(px),fraction=float(f)))
 for j in range(k,len(q)):
  t,o,h,l,c=q[j];t=int(t)
  if t+M>cutoff:out['status']='CENSORED_ASOF';break
  expected=start+(j-k)*M
  if t!=expected:out['status']='DATA_GAP_HOLD_NEEDS_EXTENSION';out['needed_from_ms']=expected;break
  # Resting protection executes at a gap before newly received author actions.
  if (o<=stop if sign==1 else o>=stop):leave(t,'GAP_BE'if be else 'GAP_SL',o,left,True,True);break
  if policy=='P1':
   while ei<len(ev)and ev[ei]['effective_ms']<=t:
    e=ev[ei];ei+=1;kind=e['kind']
    if kind=='CLOSE_ALL':leave(t,'AUTHOR_CLOSE_ALL',o,left,True,True)
    elif kind=='CLOSE_PART':leave(t,'AUTHOR_CLOSE_PART',o,left*e['fraction'],True,True)
    elif kind=='MOVE_BE':stop=entry;be=True
    elif kind=='MOVE_STOP':
     proposed=e['price']
     if sign*(o-proposed)>0:stop=proposed;be=abs(stop-entry)<1e-10
     else:author_ignored+=1
    elif kind not in ['TP_REACHED_CLAIM','MARKET_ENTRY_INSTRUCTION']:author_ignored+=1
    if left<1e-9:break
   if left<1e-9:break
  if l<=stop if sign==1 else h>=stop:leave(t,'BE'if be else 'SL',min(o,stop)if sign==1 else max(o,stop),left,True);break
  if t!=start:
   while hit<len(tp)and(h>=tp[hit]if sign==1 else l<=tp[hit]):leave(t,'TP'+str(hit+1),tp[hit],min(left,ws[hit]));hit+=1
  if left<1e-9:break
  if policy=='P2'and hit:stop=entry;be=True
 else:out['status']='CENSORED_NEEDS_EXTENSION';out['needed_from_ms']=int(q[-1,0])+M
 if left<1e-9:
  fee=.0021*entry;out.update(status='TRADE',exit_ms=out['events'][-1]['time_ms'],grossR=gross/risk,feeR=fee/risk,slippageR=slip/risk,netR=(gross-fee-slip)/risk,duration_h=(out['events'][-1]['time_ms']-start)/3600000)
 out['remaining_fraction']=left;out['unresolved_author_actions']=author_ignored;return out
