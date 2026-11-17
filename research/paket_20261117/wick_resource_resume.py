"""Four disjoint missing-source shards. Frozen original rule; no successful profile replay."""
import os,hashlib,time,subprocess,concurrent.futures as cf
from pathlib import Path
import numpy as np
from lab.common import *
from lab.extra import PIT,volume_bars
from lab.runner import report
prev=Path('previous_results');out=Path(os.environ['LAB_OUTPUT']);out.mkdir(parents=True,exist_ok=True);asof=int(os.environ['LAB_ASOF_MS']);shard=int(os.environ['SOURCE_SHARD']);m=Market(asof);pit=PIT();old=load(prev/'INPUTS.json');oldkeys={e['key']for e in old};selection=load(prev/'SELECTION_FROZEN.json');winner=selection['winner'];sp=selection['split'];write(out/'SELECTION_PRESERVED_BEFORE_NEW_PNL.json',dict(original=selection,parameters_changed=False,H1_not_reselected=True));month=dt.datetime.fromtimestamp(asof/1000,dt.timezone.utc).strftime('%Y-%m');pairs=sorted({(r['symbol'],r['month'])for r in load(prev/'DATA_GAPS.json')if r.get('reason')=='RESOURCE_CHECKPOINT'and r.get('month','')<month});pairs=[v for i,v in enumerate(pairs)if i%4==shard];receipts=[];errors=[];done=set();deadline=time.monotonic()+35*60

def prefetch(pair):
 sy,mo=pair
 try:
  v,r=volume_bars(m,sy,mo);return pair,r,None
 except Exception as e:return pair,None,dict(symbol=sy,month=mo,error=type(e).__name__+':'+str(e))
with cf.ThreadPoolExecutor(max_workers=4)as pool:
 for j in range(0,len(pairs),4):
  if time.monotonic()>deadline:break
  for pair,r,error in pool.map(prefetch,pairs[j:j+4]):
   if error:errors.append(error)
   else:done.add(pair);receipts.append(dict(symbol=pair[0],month=pair[1],**r))
  if j%40==0:print('SOURCE_SHARD',shard,j,'/',len(pairs),flush=True)
new=[]
for sy,mo in pairs:
 if(sy,mo)not in done:continue
 q=m.get(sy);start=stamp(mo+'-01');end=int(((dt.datetime.fromtimestamp(start/1000,dt.timezone.utc).replace(day=28)+dt.timedelta(days=4)).replace(day=1)).timestamp()*1000);q=q[(q[:,0]>=start)&(q[:,0]<end)]
 if not len(q):continue
 ranges=q[:,2]-q[:,3];lower=np.minimum(q[:,1],q[:,4])-q[:,3];upper=q[:,2]-np.maximum(q[:,1],q[:,4]);ev=[]
 for side,move,shadow in[(1,1-q[:,3]/q[:,1],lower),(-1,q[:,2]/q[:,1]-1,upper)]:
  for i in np.where((move>=.03)&(ranges>0)&(shadow>=.4*ranges))[0]:
   if move[i]>=.05 or pit.rank(sy,q[i,0]):ev.append((int(i),side))
 if not ev:continue
 v,r=volume_bars(m,sy,mo)
 if any(q[i,0]<start+DAY for i,side in ev):
  date=dt.datetime.fromtimestamp((start-M)/1000,dt.timezone.utc).strftime('%Y-%m-%d')
  try:prior,rr=volume_bars(m,sy,date,'daily');v=np.concatenate([prior[-1440:],v]);receipts.append(dict(symbol=sy,day=date,**rr))
  except Exception as e:errors.append(dict(symbol=sy,date=date,error=type(e).__name__+':'+str(e)))
 for i,side in ev:
  k=np.searchsorted(v[:,0],q[i,0]);past=v[max(0,k-1440):k]
  if k>=len(v)or v[k,0]!=q[i,0]or len(past)!=1440 or np.any(np.diff(past[:,0])!=M):continue
  median=float(np.median(past[:,5]))
  if median<=0 or v[k,5]<10*median:continue
  for delay in[1,2]:
   t=int(q[i,0])+delay*M;full=m.get(sy);j=np.searchsorted(full[:,0],t)
   if j>=len(full)or full[j,0]!=t:continue
   entry=float(full[j,1]);stop=float(q[i,3]*.997 if side==1 else q[i,2]*1.003);width=side*(entry-stop)/entry;code=('WL'if side==1 else'WS')+str(delay-1);key=hashlib.sha256(f'{sy}:{q[i,0]}:{code}'.encode()).hexdigest()
   if width<=0 or key in oldkeys:continue
   new.append(dict(key=key,scenario='LIQ_WICK_REBOUND',symbol=sy,entry_ms=t,signal_ms=t-1,entry=entry,side=side,entry_type='MARKET',entry_window_ms=M,wick_risk_fraction=width,variant=code,volume_rvol=float(v[k,5]/median)))
write(out/'NEW_INPUTS.json',new);audit=[];controlkeys=[];null=[];new_split=(sp[0],sp[1],sp[2],asof)
for i,e in enumerate(sorted(new,key=lambda e:(e['symbol'],e['entry_ms'],e['variant']))):
 per=phase(e,sp,4)
 if per=='H1'or(per=='H2'and e['variant']==winner):
  r=model(m,e,e['variant']);audit.append(dict(key=e['key'],variant=e['variant'],period=per,outcome=finite(r)))
  if per=='H2':controlkeys.append(e['key']);null.append(controls(m,e,winner,new_split))
 if i%500==0:print('NEW_EVENTS_ONLY',shard,i,'/',len(new),flush=True)
gzip_json(out/'NEW_ACTUAL_ONLY.json.gz',audit);np.savez_compressed(out/'NEW_H2_CONTROL200.npz',keys=np.array(controlkeys,dtype='S64'),netR=np.array(null,dtype='f4').reshape(-1,200));write(out/'PUBLIC_SOURCE_RECEIPTS.json',receipts);write(out/'SOURCE_ERRORS.json',errors);write(out/'WINDOW_COUNTS.json',dict(assigned=len(pairs),source_success=len(done),remaining=[dict(symbol=s,month=mo)for s,mo in pairs if(s,mo)not in done]));write(out/'variants.json',[]);report(out,'Wick — отдельный shard ранее незавершённых источников',f'Shard{shard}: окон{len(pairs)}, новых событий{len(new)}, исходных профилей пересчитано0. Объединение по исходному H1-winner {winner} выполняет отдельный агрегатор без нового выбора.',notes='Новые H1 исходы всех4правил сохранены как аудит полноты первоначальнойH1; они не используются, чтобы выбрать новую стратегию после увиденнойH2. На новыхH2 ровно ранее frozen rule.');write(out/'CHECKPOINT.json',dict(code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),status='SOURCE_SHARD_COMPLETE'if len(done)==len(pairs)else'SOURCE_SHARD_WITH_GAPS',shard=shard,assigned=len(pairs),source_success=len(done),new_events=len(new),H1_recomputed=False,successful_profiles_recomputed=False,candidates=0,no_live_changes=True))
