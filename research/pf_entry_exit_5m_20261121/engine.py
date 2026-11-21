"""Frozen 5m PF execution proxies; no broker/runtime/network imports."""
import bisect,math
M=300000;H=3600000
ENTRIES=['LIVE_GATES_REPRICE_5M_PROXY','MARKET_NEXT_OPEN','LIMIT_SIGNAL_0','LIMIT_PLUS_0_5','RESTING_PLUS_1_3','HYBRID_1H_1PCT']
EXITS={'E0':([.021,.042,.063],[.5,.3,.2]),'E1':([.028,.056,.112],[.5,.3,.2]),
       'E2':([.056,.112,.224],[.5,.3,.2]),'E3':([.021,.042,.063],[.7,.2,.1]),
       'E4':([.021,.042,.063],[.3,.3,.4]),'E5':([.021],[.5])}

def replay(packet,a,entry_mode,exit_mode):
 p=packet;result={'id':p['id'],'symbol':p['symbol'],'signal_ms':p['signal_ms'],'split':p['split'],
  'regime':p['regime'],'archive_selected_exposed':p['archive_selected_exposed'],'symbol_type':p['symbol_type'],
  'entry_mode':entry_mode,'exit_mode':exit_mode,'status':p['coverage_status']}
 if p['split']=='TRAIN_PURGED':result['status']='TRAIN_PURGED_80H';return result
 if p['coverage_status']!='COMPLETE_80H':return result
 C=p['C'];signal=p['signal_ms'];expiry=signal+8*H;lo=C*1.013*.999;hi=C*1.013*1.003
 offset={'LIMIT_SIGNAL_0':0,'LIMIT_PLUS_0_5':.005}.get(entry_mode,.013);limit=C*(1+offset)
 ref=C*1.013 if entry_mode=='LIVE_GATES_REPRICE_5M_PROXY'else limit
 tp_pre=ref*.979;stop_pre=ref*1.056;wait=0;fill=None
 for j in range(int(bisect.bisect_left(a[:,0],signal+M)),len(a)):
  t,o,h,l,c=map(float,a[j]);t=int(t)
  if t>=expiry:result.update(status='NOFILL',wait_checks=wait);return result
  if entry_mode=='MARKET_NEXT_OPEN':fill=(j,o,'MARKET');break
  if entry_mode=='LIVE_GATES_REPRICE_5M_PROXY':
   known_close=float(a[j-1,4])
   if known_close<=tp_pre:result.update(status='PRICE_ALREADY_AT_TP1',decision_ms=t);return result
   if known_close>=stop_pre:result.update(status='PRICE_ALREADY_AT_STOP',decision_ms=t);return result
   quote=max(o,lo)
   if quote>hi:wait+=1;continue
   if h>=quote:fill=(j,quote,'LIVE_PROXY_LIMIT');break
  else:
   if o<=tp_pre:result.update(status='PRICE_ALREADY_AT_TP1',decision_ms=t);return result
   if o>=stop_pre:result.update(status='PRICE_ALREADY_AT_STOP',decision_ms=t);return result
   if entry_mode=='HYBRID_1H_1PCT'and t>=signal+H:
    if abs(o/C-1)>.01:result.update(status='HYBRID_DISTANCE_REJECT',decision_ms=t);return result
    fill=(j,o,'HYBRID_MARKET');break
   if h>=limit:fill=(j,limit,'RESTING_LIMIT');break
  wait+=1
 if fill is None:result['status']='DATA_GAP_ENTRY';return result
 j,entry,fill_kind=fill;tentry=int(a[j,0]);stop=entry*1.056;remaining=1.;hit=0;gross=0.;events=[];lowest=entry
 tp_dist,weights=EXITS[exit_mode];targets=[entry*(1-x)for x in tp_dist];mfe=mae=0.;fill_tp=False;same_sl_tp=0
 end=tentry+72*H
 for k in range(j,len(a)):
  t,o,h,l,c=map(float,a[k]);t=int(t)
  mfe=max(mfe,(entry-l)/(entry*.056));mae=max(mae,(h-entry)/(entry*.056))
  def leave(kind,price,frac):
   nonlocal remaining,gross
   frac=min(frac,remaining);gross+=frac*(entry-price)/entry;remaining=max(0.,remaining-frac)
   events.append({'time_ms':t if kind=='TIME'else t+M,'kind':kind,'price':price,'fraction':frac})
  if t>=end:leave('TIME',o,remaining);break
  if h>=stop:
   if hit<len(targets)and l<=targets[hit]:same_sl_tp+=1
   kind='SL'if hit==0 else'TRAIL'if exit_mode=='E5'and stop<entry*.9989-1e-12 else'BE'
   leave(kind,max(stop,o),remaining);break
  if k==j and l<=targets[0]:fill_tp=True
  if k>j:
   while hit<len(targets)and l<=targets[hit]:
    leave('TP'+str(hit+1),targets[hit],weights[hit]);hit+=1
   if remaining<1e-9:break
   if hit>0:stop=min(stop,entry*.9989)
  lowest=min(lowest,l)
  if exit_mode=='E5'and hit>0:stop=min(stop,lowest+entry*.056)
 if remaining>1e-8:result.update(status='DATA_GAP_EXIT',entry_ms=tentry);return result
 assert abs(sum(e['fraction']for e in events)-1)<1e-8
 result.update(status='CLOSED',entry=entry,entry_ms=tentry,exit_ms=events[-1]['time_ms'],gross_return=gross,
  events=events,fill_kind=fill_kind,wait_checks=wait,fill_bar_TP_banned=fill_tp,SL_TP_same_bar=same_sl_tp,
  original_TP1_already_passed_at_entry=entry<=C*1.013*.979,
  original_SL_already_passed_at_entry=entry>=C*1.013*1.056,
  pending_fill_vs_TP1_order_ambiguous=bool(fill_kind!='MARKET'and a[j,3]<=tp_pre and a[j,1]<entry),
  MFE_coarse_R=mfe,MAE_coarse_R=mae,MFE_MAE_note='whole fill/exit bars, not exact pre-exit excursion',
  hold_hours=(events[-1]['time_ms']-tentry)/H,initial_geometric_risk_fraction=.056)
 return result

def funding_result(r,a,allfund):
 if r['status']!='CLOSED':return None,'NOT_A_CLOSED_TRADE'
 series=allfund.get(r['symbol'],[])
 if not series:return None,'NO_NATIVE_FUNDING_ARCHIVE'
 times=[v[0]for v in series];et=r['entry_ms'];xt=r['exit_ms']
 left=bisect.bisect_right(times,et)-1;right=bisect.bisect_right(times,xt)
 if left<0 or right>=len(times):return None,'FUNDING_NOT_BRACKETED'
 check=times[left:right+1]
 if any(b-a0>8*H for a0,b in zip(check,check[1:])):return None,'FUNDING_GAP_GT8H'
 cash=0.
 for stamp,rate in series[max(0,left):right]:
  if not et<=stamp<=xt:continue
  if stamp==et and rate>0:continue
  idx=bisect.bisect_left(a[:,0],stamp)
  if idx>=len(a)or a[idx,0]!=stamp:return None,'FUNDING_MARK_PROXY_GAP'
  gone=sum(e['fraction']for e in r['events']if e['time_ms']<=stamp)if rate>=0 else sum(e['fraction']for e in r['events']if e['time_ms']<stamp)
  cash+=rate*float(a[idx,1])/r['entry']*max(0.,1-gone)
 return cash/.056,'BRACKETED_RATE_ARCHIVE_5M_OPEN_MARK_PROXY'

def costs(r,total_cost):
 if r['status']!='CLOSED':return None
 return (r['gross_return']-total_cost)/.056
