"""Fill only previously unprocessed public sources, keep H1 selection/splits frozen.
Never recompute successful initial profiles or use new H2 to change any rule.
"""
import os,json,hashlib,subprocess,io,time,urllib.request,urllib.parse,xml.etree.ElementTree as ET,concurrent.futures as cf,collections
from pathlib import Path
import numpy as np
from lab.common import *
from lab.extra import PIT,volume_bars
from lab.study import passed
from lab.runner import report,native_entries
old=Path('previous_results');out=Path(os.environ['LAB_OUTPUT']);out.mkdir(parents=True,exist_ok=True);kind=os.environ['SOURCE_COMPLETION'];asof=int(os.environ['LAB_ASOF_MS']);sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();m=Market(asof);selection=load(old/'SELECTION_FROZEN.json')if(old/'SELECTION_FROZEN.json').exists()else{};winner=selection.get('winner');sp=selection.get('split');write(out/'SELECTION_PRESERVED_BEFORE_NEW_H2.json',dict(source=selection,code_sha=sha,original_H1_recomputed=False,parameters_changed=False));pit=PIT()

def s3(prefix,delimiter=None,maxkeys=1000):
 token=None;values=[];receipts=[];ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
 for page in range(20):
  params={'list-type':'2','prefix':prefix,'max-keys':str(maxkeys)}
  if delimiter:params['delimiter']=delimiter
  if token:params['continuation-token']=token
  url='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?'+urllib.parse.urlencode(params)
  with urllib.request.urlopen(url,timeout=30)as r:raw=r.read(8*1024*1024)
  root=ET.fromstring(raw);receipts.append(dict(url=url,sha256=hashlib.sha256(raw).hexdigest()));values.extend(v.text for v in root.findall('s:CommonPrefixes/s:Prefix'if delimiter else's:Contents/s:Key',ns));nxt=root.find('s:NextContinuationToken',ns)
  if nxt is None or maxkeys==2:break
  token=nxt.text
 else:raise ValueError('PAGINATION_INCOMPLETE')
 return values,receipts

def listing():
 birth=load(old/'FIRST_ARCHIVES.json');before=set(birth);prefixes,receipts=s3('data/futures/um/daily/klines/','/');daily={v.rstrip('/').split('/')[-1]for v in prefixes if v.rstrip('/').endswith('USDT')};gaps=load(old/'CATALOG_ERRORS.json');unknown=sorted((daily|{r['symbol']for r in gaps['errors']})-before);errors=[];newbirth={}
 def first(sy):
  try:
   found=[]
   for kind in['monthly','daily']:
    keys,_=s3(f'data/futures/um/{kind}/klines/{sy}/1m/',maxkeys=2);keys=[k for k in keys if k.endswith('.zip')]
    if keys:
     key=min(keys);period=key.split('/')[-1].split('-1m-')[1].removesuffix('.zip');found.append((period,key,kind))
   if not found:return sy,None,'NO_PUBLIC_ARCHIVE'
   period,key,kind=min(found,key=lambda x:x[0]);r=m.quotes.fetch(sy,period,kind);lo=r['first_ms'];q=m.quotes.load(sy);i=np.searchsorted(q[:,0],lo);j=np.searchsorted(q[:,0],lo+H)
   if j-i!=60:
    nextday=dt.datetime.fromtimestamp((lo+H)/1000,dt.timezone.utc).strftime('%Y-%m-%d');m.quotes.fetch(sy,nextday,'daily');m.quotes.cache.pop(sy,None);q=m.quotes.load(sy);i=np.searchsorted(q[:,0],lo);j=np.searchsorted(q[:,0],lo+H)
   if j-i!=60 or np.any(np.diff(q[i:j,0])!=M):return sy,None,'NO_COMPLETE_FIRST_HOUR'
   return sy,dict(first_ms=int(lo),first_hour_close=float(q[j-1,4]),source_key=key,source_sha256=r['source_sha256']),None
  except Exception as e:return sy,None,type(e).__name__+':'+str(e)
 # Quotes.load's shared cache is not used concurrently: each symbol's parsed files are read directly below.
 import threading
 # Loading shared cache guarded only for these few new birth proofs.
 original_load=m.quotes.load;lock=threading.Lock()
 def safe_load(sy):
  with lock:return original_load(sy)
 m.quotes.load=safe_load
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for sy,item,error in pool.map(first,unknown):
   if item:birth[sy]=item;newbirth[sy]=item
   else:errors.append(dict(symbol=sy,error=error))
 write(out/'NEW_BIRTH_PROOFS.json',newbirth);write(out/'CATALOG_DAILY_COMPLETION.json',dict(catalogue_daily=len(daily),already_proven_monthly=len(before),new_requested=len(unknown),new_proven=len(newbirth),errors=errors,receipts=receipts));m.symbol=None;entries=[]
 for sy,b in newbirth.items():
  ts=b['first_ms']+int(winner[1:])*H if winner else b['first_ms']+24*H
  if ts>=asof:continue
  entries.append(dict(key=hashlib.sha256(f'{sy}:{ts}:{winner}'.encode()).hexdigest(),scenario='NEW_LISTING_FADE',symbol=sy,entry_ms=ts,signal_ms=ts,side=-1,entry_type='MARKET',entry_window_ms=M,first_hour_close=b['first_hour_close'],delay=int(winner[1:])if winner else 24))
 write(out/'NEW_MARKET_SOURCES.json',m.collect([(e['symbol'],e['entry_ms']-H,min(asof,e['entry_ms']+8*DAY))for e in entries],minutes=15));new=[];rejected=[]
 for e in entries:
  q=m.get(e['symbol']);i=np.searchsorted(q[:,0],e['entry_ms'])
  if sp and e['entry_ms']<sp[1]:rejected.append(dict(e,status='OLDER_H1_SOURCE_GAP_REQUIRES_REVIEW_NO_REFIT'));continue
  if i<len(q)and q[i,0]==e['entry_ms']and q[i,1]>e['first_hour_close']:new.append(dict(e,entry=float(q[i,1])))
  else:rejected.append(dict(e,status='PRICE_FILTER_REJECTED'if i<len(q)and q[i,0]==e['entry_ms']else'DATA_GAP'))
 write(out/'NEW_INPUTS.json',new);write(out/'NEW_REJECTED.json',rejected)
 oldactual=[r for r in load(old/'ALL_ACTUAL_EXITS.json.gz')if r['period']=='H2'];oldnull=np.load(old/'H2_CONTROL200_TOP100.npz',allow_pickle=False)['netR']if(old/'H2_CONTROL200_TOP100.npz').exists()else np.empty((0,200));assert len(oldactual)==len(oldnull)
 oldinputs={e['key']:e for e in load(old/'INPUTS.json')};test=[oldinputs[r['key']]for r in oldactual];actual=[np.array(r['outcome'],float)for r in oldactual];null=[r for r in oldnull];newactual=[model(m,e,winner)for e in new]if winner else[];newnull=np.full((len(new),200),np.nan);control_inputs=[]
 for i,e in enumerate(new):
  pool=[s for s in pit.ranks(e['entry_ms'],100)if s!=e['symbol']and s in birth and birth[s]['first_ms']<e['entry_ms']]
  if not pool:continue
  rng=np.random.default_rng(SEED+int(e['key'][:12],16))
  for j,sy in enumerate(rng.choice(pool,200)):control_inputs.append((str(sy),i,j,e))
 write(out/'NEW_CONTROL_MARKET_SOURCES.json',m.collect([(sy,e['entry_ms']-H,min(asof,e['entry_ms']+8*DAY))for sy,i,j,e in control_inputs],minutes=15))
 for sy,i,j,e in sorted(control_inputs,key=lambda x:x[0]):
  q=m.get(sy);k=np.searchsorted(q[:,0],e['entry_ms'])
  if k<len(q)and q[k,0]==e['entry_ms']:
   rr=model(m,dict(e,symbol=sy,entry=float(q[k,1])),winner);newnull[i,j]=rr[1]if rr[0]==1 else np.nan
 actual+=newactual;null+=list(newnull);test+=new;tables=[r for r in load(old/'TABLES.json')if r['period']=='H1'];np.savez_compressed(out/'NEW_H2_ONLY_OUTCOMES_AND_CONTROLS.npz',outcomes=np.array(newactual),control_netR=newnull);write(out/'CONTROL_COINS_NEW.json',[dict(symbol=sy,parent=e['key'],repeat=j)for sy,i,j,e in control_inputs])
 if winner:
  for period in['H2','LAST40']:
   ix=[i for i,e in enumerate(test)if period=='H2'or e['entry_ms']>=sp[2]];rs=[actual[i]for i in ix];p=paired_test(rs,[null[i]for i in ix]);tables.append(dict(variant=winner,period=period,**metrics(rs),excessR=p['excessR'],control_coverage=p['coverage'],BH_q=min(1.,p['p']*3)))
 variants=[dict(name='NEW_LISTING_FADE_'+winner,enabled=False,status='PROMISING_REQUIRES_CLAUDE_REVIEW')]if winner and passed(tables,winner)else[];write(out/'TABLES.json',finite(tables));write(out/'variants.json',variants);report(out,'Часть2 — исправление пяти Unicode и дополнение daily-only листингов',f'Исходные H1/выбор {winner} и успешные профили не пересчитывались. Новых доказанных birth {len(newbirth)}, новых входов с условием {len(new)}, модель новыхH2 только по исходному winner. Контроль исходных H2 взят из NPZ, рассчитан только для новых входов.',tables,notes='Календарные границы/правила/стоп/тейки не менялись. Daily-only новые листинги включены, UnicodeURL percent-encoded. Объединённые H2/LAST40 служат проверкой зафиксированногоH1выбора, а не новым подбором. После асоф неизвестные свечи остаются CENSORED/DATA_GAP.');return dict(status='COMPLETE_SOURCE_GAPS_REVIEWED',new_births=len(newbirth),new_entries=len(new),candidates=len(variants),winner=winner,successful_profiles_recomputed=False)

def wick():
 # Original November monthly requests failed because that monthly archive is not published yet.
 # Process only those missing source windows. Existing price/volume-confirmed events are never replayed.
 missing=load(old/'DATA_GAPS.json');month=dt.datetime.fromtimestamp(asof/1000,dt.timezone.utc).strftime('%Y-%m');pairs=sorted({(r['symbol'],r['month'])for r in missing if r.get('month')==month});allnew=[];receipts=[];errors=[];deadline=time.monotonic()+30*60;codes=['WL0','WL1','WS0','WS1'];oldkeys={e['key']for e in load(old/'INPUTS.json')};start=stamp(month+'-01')
 for sy,mon in pairs:
  if time.monotonic()>deadline:errors.append(dict(symbol=sy,reason='RESOURCE_CHECKPOINT'));continue
  q=m.get(sy);q=q[q[:,0]>=start]
  if not len(q):continue
  # Fetch only dailyV windows needed by price-first events, including preceding day for median.
  ranges=q[:,2]-q[:,3];lower=np.minimum(q[:,1],q[:,4])-q[:,3];upper=q[:,2]-np.maximum(q[:,1],q[:,4]);down=1-q[:,3]/q[:,1];up=q[:,2]/q[:,1]-1;events=[]
  for side,move,shadow in[(1,down,lower),(-1,up,upper)]:
   for i in np.where((move>=.03)&(ranges>0)&(shadow>=.4*ranges))[0]:
    if move[i]>=.05 or pit.rank(sy,q[i,0]):events.append((int(i),side))
  dates=set()
  for i,side in events:
   for t in[q[i,0]-DAY,q[i,0]]:dates.add(dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m-%d'))
  def vol(day):
   try:v,r=volume_bars(m,sy,day,'daily');return v,r,None
   except Exception as e:return None,None,dict(symbol=sy,date=day,error=type(e).__name__+':'+str(e))
  parts=[]
  with cf.ThreadPoolExecutor(max_workers=4)as pool:
   for v,r,error in pool.map(vol,sorted(dates)):
    if error:errors.append(error)
    else:parts.append(v);receipts.append(dict(symbol=sy,**r))
  if not parts:continue
  v=np.concatenate(parts);v=v[np.argsort(v[:,0])];_,ix=np.unique(v[:,0],return_index=True);v=v[np.sort(ix)]
  for i,side in events:
   k=np.searchsorted(v[:,0],q[i,0]);past=v[max(0,k-1440):k]
   if k>=len(v)or v[k,0]!=q[i,0]or len(past)!=1440 or np.any(np.diff(past[:,0])!=M):continue
   median=float(np.median(past[:,5]))
   if median<=0 or v[k,5]<10*median:continue
   for delay in[1,2]:
    j=i+delay
    if j>=len(q)or q[j,0]!=q[i,0]+delay*M:continue
    entry=float(q[j,1]);stop=float(q[i,3]*.997 if side==1 else q[i,2]*1.003);width=side*(entry-stop)/entry
    if width<=0:continue
    code=('WL'if side==1 else'WS')+str(delay-1);key=hashlib.sha256(f'{sy}:{q[i,0]}:{code}'.encode()).hexdigest()
    if key in oldkeys:continue
    allnew.append(dict(key=key,scenario='LIQ_WICK_REBOUND',symbol=sy,entry_ms=int(q[j,0]),signal_ms=int(q[i,0]+delay*M)-1,entry=entry,side=side,entry_type='MARKET',entry_window_ms=M,wick_risk_fraction=width,variant=code,volume_rvol=float(v[k,5]/median)))
  print('DAILY_VOLUME_COMPLETION',sy,'new_events',len(allnew),flush=True)
 write(out/'NEW_EVENTS.json',allnew);write(out/'DAILY_VOLUME_SOURCES.json',receipts);write(out/'REMAINING_SOURCE_GAPS.json',errors);tables=[r for r in load(old/'TABLES.json')if r['period']=='H1'];actualaudit=load(old/'ALL_ACTUAL_EXITS.json.gz');oldactual=[r for r in actualaudit if r['period']=='H2'];oldnull=load(old/'CONTROL200.json.gz');assert len(oldactual)==len(oldnull);oldinputs={e['key']:e for e in load(old/'INPUTS.json')};es=[oldinputs[r['key']]for r in oldactual];rs=[np.array(r['outcome'],float)for r in oldactual];ns=[np.array(r,float)for r in oldnull];added=[];newout=[];newctrl=[]
 if winner:
  added=[e for e in allnew if e['variant']==winner and e['entry_ms']>=sp[1]]
  for e in added:
   newout.append(model(m,e,winner));newctrl.append(controls(m,e,winner,(sp[0],sp[1],sp[2],asof)))
  # First three calendar cutoffs immutable; only end of available H2 clock extended to fixed ASOF for new dates.
  es+=added;rs+=newout;ns+=newctrl
  for period in['H2','LAST40']:
   ix=[i for i,e in enumerate(es)if period=='H2'or e['entry_ms']>=sp[2]];a=[rs[i]for i in ix];p=paired_test(a,[ns[i]for i in ix]);tables.append(dict(variant=winner,period=period,**metrics(a),excessR=p['excessR'],control_coverage=p['coverage'],BH_q=min(1.,p['p']*4)))
 np.savez_compressed(out/'NEW_H2_ONLY_OUTCOMES_AND_CONTROLS.npz',outcomes=np.array(newout),control_netR=np.array(newctrl));variants=[dict(name='LIQ_WICK_'+winner,enabled=False,status='PROMISING_CACHED_UNIVERSE_REQUIRES_CLAUDE_REVIEW')]if winner and passed(tables,winner)else[];write(out/'TABLES.json',finite(tables));write(out/'variants.json',variants);report(out,'Часть3 — dailyV вместо отсутствующего current-month monthlyV',f'Исходный H1 winner {winner}, исходныеH1/успешныеH2 не пересчитывались. В новых источниках найдено {len(allnew)} событий, из них {len(added)} относятся к ранее выбранному правилу на H2. Ни один параметр не менялся.',tables,notes='Новые daily-источники закрывают ранее неуспешные monthly-запросы текущего месяца. Cached-universe не объявляется всем рынком. Данные по завершённым исходным событиям/контролям взяты из сохранённых файлов. Если H1не имела winner достаточногоn, новыеH2 не используются для выбора.');return dict(status='COMPLETE_DAILY_SOURCE_COMPLETION_WITH_REMAINING_GAPS',new_events=len(allnew),new_frozen_rule_H2=len(added),winner=winner,candidates=len(variants),successful_profiles_recomputed=False)

result=listing()if kind=='listing'else wick();write(out/'CHECKPOINT.json',dict(code_sha=sha,asof=asof,**result,no_live_changes=True));write(out/'ARTIFACT_HASHES.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and p.name!='ARTIFACT_HASHES.json'})
