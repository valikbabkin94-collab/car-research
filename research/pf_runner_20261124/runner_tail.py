"""Pure incremental short exit kernel; no I/O, network, broker or entry selection."""
import math
MODES={'RUN15':(.015,2,[.5,.3]),'RUN25':(.025,2,[.5,.3]),'RUN35':(.035,2,[.5,.3]),'TP3_RUN10':(.025,3,[.5,.3,.1]),'BASE':(None,99,[.5,.3,.2])}
def create(entry,entry_ms,mode,step_ms=300000):
 if mode not in MODES or isinstance(entry,bool)or not isinstance(entry,(int,float))or not math.isfinite(entry)or entry<=0:raise ValueError('invalid mode/entry')
 if isinstance(entry_ms,bool)or not isinstance(entry_ms,int)or entry_ms<0 or step_ms not in (60000,300000):raise ValueError('invalid clock')
 return dict(entry=float(entry),entry_ms=entry_ms,mode=mode,step_ms=step_ms,next_ms=entry_ms,status='OPEN',remaining=1.,hit=0,stop=entry*1.056,events=[],gross_return=0.,trail_low=None,MFE_coarse_R=0.,MAE_coarse_R=0.,fill_bar_TP_banned=False)
def advance(p,rows):
 if p['status']!='OPEN':return p
 step=p['step_ms'];entry=p['entry'];distance,activation,weights=MODES[p['mode']];targets=[entry*(1-x)for x in [.021,.042,.063]]
 for row in rows:
  t=int(row[0]);o,h,l,c=map(float,row[1:5])
  if t<p['next_ms']:continue
  if t!=p['next_ms']:raise ValueError('DATA_GAP')
  if not all(math.isfinite(v)and v>0 for v in (o,h,l,c))or l>min(o,c)or h<max(o,c):raise ValueError('INVALID_OHLC')
  def leave(kind,price,frac,stamp):
   f=min(frac,p['remaining']);p['remaining']=max(0.,p['remaining']-f);p['gross_return']+=f*(entry-price)/entry
   p['events'].append(dict(time_ms=stamp,kind=kind,price=price,fraction=f))
   if p['remaining']<1e-9:p.update(status='CLOSED',exit_ms=stamp)
  if t>=p['entry_ms']+72*3600000:leave('TIME',o,p['remaining'],t)
  else:
   p['MFE_coarse_R']=max(p['MFE_coarse_R'],(entry-l)/(entry*.056));p['MAE_coarse_R']=max(p['MAE_coarse_R'],(h-entry)/(entry*.056))
   if h>=p['stop']:
    kind='SL'if p['hit']==0 else'TRAIL'if p['stop']<entry*.9989-1e-12 else'BE'
    leave(kind,max(o,p['stop']),p['remaining'],t+step)
   elif t==p['entry_ms']:
    if l<=targets[0]:p['fill_bar_TP_banned']=True
   else:
    while p['hit']<len(weights)and l<=targets[p['hit']]:
     j=p['hit'];leave('TP'+str(j+1),targets[j],weights[j],t+step);p['hit']+=1
    if p['status']=='OPEN'and p['hit']>0:p['stop']=min(p['stop'],entry*.9989)
    if p['status']=='OPEN'and p['hit']>=activation:
     p['trail_low']=l if p['trail_low']is None else min(p['trail_low'],l)
     p['stop']=min(p['stop'],p['trail_low']*(1+distance))
  p['next_ms']=t+step
  if p['status']=='CLOSED':
   assert abs(sum(e['fraction']for e in p['events'])-1)<1e-8
   break
 return p
