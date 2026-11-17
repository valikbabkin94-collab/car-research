"""Pure virtual exits on frozen entries. No account, order or runtime interfaces."""
from types import SimpleNamespace
import numpy as np
from vendor.pure_manager import atr_from_closed_hours,geometry,PureManager
M=60000;H=3600000
TAKER=.00055;MAKER=.0002;SLIP=.0005
MAN=PureManager();MAN.cfg={'move_be_after_tp1':True,'fee_rate':TAKER,'reversal':{'enabled':True,'after_tp1_only':True,'min_move_r':1.,'giveback':.5,'against_candles':0}}
def atr_at(q,t):
 cutoff=t//H*H;a=cutoff-15*H;i=np.searchsorted(q[:,0],a);j=np.searchsorted(q[:,0],cutoff);v=q[i:j]
 if len(v)!=900 or np.any(np.diff(v[:,0])!=M):raise ValueError('ATR_H1_DATA_GAP')
 z=v.reshape(15,60,5);bars=np.column_stack((z[:,0,0],z[:,0,1],z[:,:,2].max(1),z[:,:,3].min(1),z[:,-1,4]));return atr_from_closed_hours(bars.tolist(),t)['atr']
def simulate(q,e,manager,mirror=False):
 t=e['entry_ms'];entry=e['entry'];side=e['side']*(-1 if mirror else 1);base=dict(key=e['key'],scenario=e['scenario'],manager=manager,mirror=mirror,entry_ms=t,entry=entry,side=side,status='DATA_GAP',net_R=None,events=[])
 k=int(np.searchsorted(q[:,0],t))if len(q)else 0
 if t%M or k>=len(q)or q[k,0]!=t:return dict(base,reason='NO_EXACT_ENTRY_MINUTE')
 if not q[k,3]<=entry<=q[k,2]:return dict(base,reason='FROZEN_ENTRY_OUTSIDE_BINANCE_1M_RANGE')
 try:atr=atr_at(q,min(t,e.get('signal_ms',t))if manager in ['X1','X2']else t)if manager in ['X1','X2','X4','X5']else None
 except ValueError as ex:return dict(base,reason=str(ex))
 width=.01;weights=[1.];targets=[];hold=72;trail=False;hit=0;best=entry;left=1.;gross=0.;entrymaker=e.get('entry_type')=='LIMIT';cost=MAKER if entrymaker else TAKER+SLIP;initialstop=entry*(1-side*.01)
 if manager in ['X1','X2']:
  distance,initialstop,targets=geometry(atr,entry,side);width=distance/entry;weights=[.5,.25,.25];hold=24
 elif manager=='X3':targets=[entry*(1+side*.015)]
 elif manager=='X4':targets=[entry*(1+side*.01)];weights=[.5]
 elif manager=='X5':width=1.5*atr/entry;initialstop=entry-side*1.5*atr;trail=True
 elif manager=='X6':hold=4
 elif manager=='X7':hold=24
 elif manager=='X8':targets=[entry*(1+side*.005)]
 elif manager=='X9':width=.02;initialstop=entry*(1-side*.02);targets=[entry*(1+side*.02)]
 if initialstop<=0 or any(x<=0 for x in targets):return dict(base,status='REJECTED_GEOMETRY')
 stop=initialstop;trade=SimpleNamespace(is_short=side==-1,open_rate=entry,max_rate=entry,min_rate=entry,nr_of_successful_exits=0);sig={'stop':initialstop};base.update(risk_fraction=width,risk_denominator=width,initial_stop=initialstop,atr=atr,mfe_R=0.,mae_R=0.,ambiguous_sl_tp_bars=0)
 def leave(kind,ts,price,f,passive=False):
  nonlocal left,gross,cost
  f=min(left,f);gross+=side*(price/entry-1)*f;cost+=(MAKER if passive else TAKER+SLIP)*price/entry*f;left-=f;base['events'].append(dict(kind=kind,time_ms=int(ts),bar_ms=int(ts if kind=='TIME'else ts-M),price=float(price),fraction=float(f)))
 for j in range(k,len(q)):
  ts,o,hi,lo,cl=q[j];ts=int(ts)
  if ts!=t+(j-k)*M:return dict(base,status='DATA_GAP_HOLD')
  if ts>=t+hold*H:leave('TIME',ts,o,left);break
  base['mfe_R']=max(base['mfe_R'],side*((hi if side==1 else lo)/entry-1)/width);base['mae_R']=max(base['mae_R'],-side*((lo if side==1 else hi)/entry-1)/width)
  if lo<=stop if side==1 else hi>=stop:
   base['ambiguous_sl_tp_bars']+=int(hit<len(targets)and(hi>=targets[hit]if side==1 else lo<=targets[hit]));leave('SL_OR_TRAIL',ts+M,min(o,stop)if side==1 else max(o,stop),left);break
  if j!=k:
   while hit<len(targets)and(hi>=targets[hit]if side==1 else lo<=targets[hit]):leave('TP'+str(hit+1),ts+M,targets[hit],weights[hit],True);hit+=1
  if left<1e-9:break
  best=max(best,hi)if side==1 else min(best,lo);trade.max_rate=max(trade.max_rate,hi);trade.min_rate=min(trade.min_rate,lo);trade.nr_of_successful_exits=hit
  if manager in ['X1','X2']:
   stop=MAN._desired_stop(trade,sig)[0]
   if manager=='X2'and MAN._reversal_exit(trade,dict(sig,_research_reversal=True,reversal_enabled=True),cl,'OFFLINE'):
    if j+1<len(q)and q[j+1,0]==ts+M:leave('REVERSAL_GIVEBACK',ts+M,float(q[j+1,1]),left);break
  elif manager=='X4'and hit:
   ns=best-side*atr;stop=max(stop,ns)if side==1 else min(stop,ns)
  elif manager=='X5':
   ns=best-side*1.5*atr;stop=max(stop,ns)if side==1 else min(stop,ns)
 if left>1e-9:return dict(base,status='RIGHT_CENSORED')
 base.update(status='CLOSED',exit_ms=base['events'][-1]['time_ms'],gross_R=gross/width,execution_cost_R=cost/width,price_R=(gross-cost)/width,hold_hours=(base['events'][-1]['time_ms']-t)/H)
 return base
