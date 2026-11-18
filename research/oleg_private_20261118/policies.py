"""Fixed, preregistered policies. No parameter fitting or runtime imports."""
import copy,numpy as np
M=60000;H=3600000;ASOF=1794960000000
O=['O0','O1','O2','O3','O4','O5','AUTHOR'];C=['P1','P2','P3','T1','T2','T3','AUTHOR']
def entry_start(s):return ((s['available_ms']+M-1)//M+1)*M
def plan(s,policy,q,random=False):
 obs=s['available_ms']+M-1;t=entry_start(s);i=np.searchsorted(q[:,0],t)if len(q)else 0
 if i>=len(q)or q[i,0]!=t:return None,'NO_ENTRY_CANDLE'
 if policy=='AUTHOR'and'AUTHOR_DCA_SIZING_UNSPECIFIED'in s.get('flags',[]):return None,'UNRESOLVED_AUTHOR_DCA_SIZING'
 side=1 if s['side']=='LONG'else-1;market=float(q[i,1]);p=dict(symbol=s['symbol'],signal_ms=s['pub'],observed_ms=obs,side=side,entry_type='MARKET',hold_hours=72,stop_fraction=.056,move_be=True,tp_dist=[.021,.042,.063],weights=[.5,.3,.2])
 def authored_stop():
  if s['stop'] is not None:p['absolute_stop']=s['stop'];return True
  if s.get('stop_percent')is not None and s['stop_percent']>0:p['stop_fraction']=s['stop_percent']/100;return True
  return False
 def zone(ttl):
  if not s.get('entry_zone'):return False
  p.update(entry_type='LIMIT',limit=sum(s['entry_zone'])/2,ttl_hours=ttl);return True
 def targets(ts,ws):p.update(absolute_targets=list(ts),weights=ws)
 if s['channel']=='OLEG':
  if policy=='O1'and side!= -1:return None,'DIRECTION_FILTER_LONG'
  if policy=='O2'and side!=1:return None,'DIRECTION_FILTER_SHORT'
  if not authored_stop()or not s['targets']:return None,'MISSING_AUTHOR_LEVELS'
  ts=s['targets'];n=len(ts)
  if policy in['O4','O5','AUTHOR']:
   if n<2:return None,'MISSING_SECOND_AUTHOR_TARGET'
   targets(ts[:2],[.5,.5]);p['move_be']=False
  else:
   # Source strategy standard split for >3 targets is not frozen in the archive.
   if n>3:return None,'LIVE_TARGET_SPLIT_NOT_RECONSTRUCTABLE'
   targets(ts,[1.]if n==1 else[.5,.5]if n==2 else[.5,.3,.2])
  if policy in['O3','O5']and not zone(12):return None,'MISSING_AUTHOR_ENTRY_ZONE'
  if policy=='AUTHOR'and not random:p['author_events']=s['events']
 else:
  structured=s['kind']=='STRUCTURED';effective=policy
  if policy=='AUTHOR':effective='P1'if structured else'T1'
  if effective.startswith('P'):
   if not structured:return None,'NOT_APPLICABLE_TEXT_COHORT'
   if not authored_stop()or not s['targets']:return None,'MISSING_AUTHOR_LEVELS'
   p['hold_hours']=100000;p['move_be']=effective=='P2';p['be_offset']=0.;p['all_author_targets']=s['targets']
   if effective=='P1':targets(s['targets'][-1:],[1.]);
   elif effective=='P2':targets(s['targets'][:2],[.5,.5]if len(s['targets'])>=2 else[1.])
   else:targets(s['targets'][:1],[1.])
   if effective=='P1'and not random:p['author_events']=s['events']
  else:
   if structured:return None,'NOT_APPLICABLE_STRUCTURED_COHORT'
   if effective=='T1':
    authored_stop()
    if s.get('entry_zone'):zone(24)
    if not random:p['author_events']=s['events']
   elif effective=='T2':
    past=q[np.searchsorted(q[:,0],t-24*H):i]
    if len(past)!=1440 or np.any(np.diff(past[:,0])!=M):return None,'MISSING_24H_HISTORY'
    stop=float(past[:,2].max()*1.01)if side==-1 else float(past[:,3].min()*.99);width=side*(market-stop)/market
    p.update(absolute_stop=stop,tp_dist=[width,2*width],weights=[.5,.5])
 return p,None

def translated_control(s,when,source_q,control_q):
 r=copy.deepcopy(s);a=entry_start(s);b=((when+M-1)//M+1)*M;i=np.searchsorted(source_q[:,0],a)if len(source_q)else 0;j=np.searchsorted(control_q[:,0],b)if len(control_q)else 0
 r.update(pub=when,available_ms=when,events=[])
 if i>=len(source_q)or j>=len(control_q)or source_q[i,0]!=a or control_q[j,0]!=b:return r,'NO_SOURCE_OR_CONTROL_REFERENCE'
 ratio=float(control_q[j,1]/source_q[i,1]);r['entry_zone']=[x*ratio for x in r['entry_zone']]if r['entry_zone']else None;r['stop']=r['stop']*ratio if r['stop']is not None else None;r['targets']=[x*ratio for x in r['targets']];return r,None
