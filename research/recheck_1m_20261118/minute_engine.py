"""Frozen DUMP trade paths with minute chronology; no order/account interfaces."""
import numpy as np
M=60000;H=3600000;STOP=.056;COST=.0021;DEN=STOP+COST

def replay(q,r,optimistic_entry_minute=False,delayed_new_BE=False):
 if r['status']!='CLOSED':return dict(status='ORIGINAL_'+r['status'])
 a=int(r['entry_ms']);end=a+72*H;entry=float(r['entry']);ts=q[:,0];i=int(np.searchsorted(ts,a));j=int(np.searchsorted(ts,end));bars=q[i:j]
 if len(bars)!=4320 or bars[0,0]!=a or bars[-1,0]+M!=end or np.any(np.diff(bars[:,0])!=M):return dict(status='DATA_GAP_MINUTES',available=len(bars),required=4320)
 touch=np.flatnonzero((bars[:60,3]<=entry)&(bars[:60,2]>=entry))
 if not len(touch):return dict(status='DATA_GAP_ORIGINAL_ENTRY_PRICE_NOT_REACHED',original_entry=entry)
 k=int(touch[0]);et=int(bars[k,0]);remaining=1.;stop=entry*(1-STOP);targets=entry*np.array([1.021,1.042,1.063]);weights=[.5,.3,.2];tp=0;gross=0.;events=[];ambig_entry=False;ambig_BE=False;simultaneous=False
 for ix in range(k,len(bars)):
  t,o,hi,lo,c=bars[ix];t=int(t);newentry=ix==k
  if lo<=stop:
   simultaneous|=bool(tp<3 and hi>=targets[tp]);px=min(stop,o);gross+=(px/entry-1)*remaining;events.append(dict(time_ms=t+M,bar_ms=t,kind='SL'if tp==0 else'BE',price=float(px),fraction=remaining));remaining=0.;break
  if newentry and hi>=targets[tp]:ambig_entry=True
  if newentry and not optimistic_entry_minute:continue
  while tp<3 and hi>=targets[tp]:
   px=float(targets[tp]);part=weights[tp];gross+=(px/entry-1)*part;remaining-=part;events.append(dict(time_ms=t+M,bar_ms=t,kind='TP'+str(tp+1),price=px,fraction=part));tp+=1
   if tp==1 and remaining>1e-10:
    stop=entry
    if lo<=entry:
     ambig_BE=True
     if not delayed_new_BE:
      gross+=0.;events.append(dict(time_ms=t+M,bar_ms=t,kind='BE_SAME_MINUTE_BOUND',price=entry,fraction=remaining));remaining=0.;break
  if remaining<1e-10:remaining=0.;break
 if remaining>0:
  t,o,hi,lo,c=bars[-1];gross+=(c/entry-1)*remaining;events.append(dict(time_ms=int(t+M),bar_ms=int(t),kind='TIME',price=float(c),fraction=remaining));remaining=0.
 assert abs(sum(v['fraction']for v in events)-1)<1e-8
 finish=events[-1]['time_ms'];held=bars[k:int(np.searchsorted(bars[:,0],finish))];after=held[1:]
 return dict(status='CLOSED',R=float((gross-COST)/DEN),gross_return=float(gross),cost_return=COST,entry_ms=et,entry=entry,original_entry_hour=a,horizon_ms=end,exit_ms=finish,holding_hours=(finish-et)/H,events=events,entry_minute_TP_ambiguous=ambig_entry,new_BE_same_minute_ambiguous=ambig_BE,SL_TP_same_minute_ambiguous=simultaneous,MFE_R_envelope=float((held[:,2].max()/entry-1)/DEN),MAE_R_envelope=float((1-held[:,3].min()/entry)/DEN),MFE_R_excluding_entry_minute=float((after[:,2].max()/entry-1)/DEN)if len(after)else None)

def funding_cash(q,r,ft,fr):
 if r['status']!='CLOSED':return None
 start=r['entry_ms'];end=r['exit_ms'];fund=0.;count=0
 for t,rate in zip(ft,fr):
  if t<start or t>end:continue
  if(t==start or t==end)and rate<0:continue
  ix=np.searchsorted(q[:,0],t,side='left')-1
  if ix<0 or t-q[ix,0]>M:continue
  # Payer keeps exposure until close; receipt needs position strictly after open.
  remaining=1-sum(e['fraction']for e in r['events']if e['time_ms']<t or(e['time_ms']==t and rate<0));fund-=max(0,remaining)*rate*q[ix,4]/r['entry'];count+=1
 return float(fund/DEN),count
