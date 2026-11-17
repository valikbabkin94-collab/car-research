"""Frozen-entry edge study, train-only gates and exit selection, pure GitHub offline run."""
import os,json,gzip,hashlib,time,datetime as dt,collections,concurrent.futures as cf,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter1d,minimum_filter1d
from vendor.market import Quotes,Funding,save,month_list,M,H,DAY
from engine_v1_1 import simulate
P=Path(__file__).resolve().parent;OUT=P/'RESULTS';SEED=20261117;HOURS=[1,4,24,72];MANAGERS=['X'+str(i)for i in range(1,10)];MIRRORS=['X1','X3','X6','X7'];MISSING=['G3h','R2','R5','ALT_CLONE','ALTCOIN','SCALP_C10','Yoda','Pirates','Oleg','CAR_MAIN_R9']
def read(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.loads(p.read_text())
def gz(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(x,allow_nan=False).encode(),mtime=0))
def clean(x):
 if isinstance(x,dict):return {k:clean(v)for k,v in x.items()}
 if isinstance(x,list):return [clean(v)for v in x]
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(float,np.floating)):return float(x)if np.isfinite(x)else None
 return x
def bh(values):
 n=len(values);o=np.argsort(values);q=np.ones(n);last=1.
 for k in range(n-1,-1,-1):i=o[k];last=min(last,values[i]*n/(k+1));q[i]=last
 return q.tolist()
def pvalue(blocks,seed,two=False):
 v=np.array(list(blocks.values()),float)
 if len(v)<10:return 1.
 rng=np.random.default_rng(seed);null=rng.choice([-1,1],size=(4095,len(v)))@v;obs=v.sum();return (1+int(np.sum(abs(null)>=abs(obs)if two else null>=obs)))/4096

def jobs_for(symbol,a,b):
 out=[]
 for mon in month_list(a,b):
  now=dt.datetime.fromtimestamp(ASOF/1000,dt.timezone.utc).strftime('%Y-%m')
  if mon<now:out.append((symbol,mon,'monthly'))
  else:
   start=int(dt.datetime.fromisoformat(mon+'-01').replace(tzinfo=dt.timezone.utc).timestamp()*1000);t=max(a//DAY*DAY,start)
   while t<b:out.append((symbol,dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m-%d'),'daily'));t+=DAY
 return out

def collect(q,entries):
 jobs=sorted(set(j for e in entries for j in jobs_for(e['symbol'],e['entry_ms']-8*DAY,min(ASOF,e['entry_ms']+11*DAY))))
 def one(x):
  sy,period,kind=x
  try:return dict(symbol=sy,period=period,status='OK',receipt=q.fetch(sy,period,kind))
  except Exception as ex:return dict(symbol=sy,period=period,status='DATA_GAP',error=type(ex).__name__+': '+str(ex))
 receipts=[];deadline=time.monotonic()+30*60
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for j in range(0,len(jobs),4):
   if time.monotonic()>deadline:break
   receipts+=list(pool.map(one,jobs[j:j+4]));save(OUT/'SOURCE_CHECKPOINT.json',dict(total=len(jobs),done=len(receipts),receipts=receipts))
   if j%100==0:print('SOURCES',len(receipts),'/',len(jobs),flush=True)
 save(OUT/'SOURCE_CHECKPOINT.json',dict(total=len(jobs),done=len(receipts),receipts=receipts));return receipts

def features(q,times,entries,side):
 # outcomes only; no future data used to choose entry or risk.
 shape=np.shape(times);t=np.asarray(times).ravel();pr=np.broadcast_to(entries,shape).ravel();valid0=np.isfinite(pr)&(pr>0);idx=np.searchsorted(q[:,0],t)if len(q)else np.zeros(len(t),int);valid0 &=idx<len(q)
 ret=np.full((len(t),3),np.nan);mfe=np.full((len(t),4),np.nan);mae=np.full_like(mfe,np.nan)
 if not len(q):return ret.reshape(*shape,3),mfe.reshape(*shape,4),mae.reshape(*shape,4)
 safe=np.minimum(idx,len(q)-1);valid0&=q[safe,0]==t
 for z,h in enumerate(HOURS):
  n=h*60;end=idx+n;valid=valid0&(end<len(q));es=np.minimum(end,len(q)-1);valid&=(q[es,0]==t+n*M)
  high=maximum_filter1d(q[:,2],size=n,origin=-(n//2),mode='constant',cval=-np.inf);low=minimum_filter1d(q[:,3],size=n,origin=-(n//2),mode='constant',cval=np.inf)
  # source timestamps strictly increasing => endpoint difference n minutes implies no missing middle minute.
  mfe[valid,z]=((high[safe[valid]]/pr[valid]-1)if side==1 else(1-low[safe[valid]]/pr[valid]))/.01
  mae[valid,z]=((1-low[safe[valid]]/pr[valid])if side==1 else(high[safe[valid]]/pr[valid]-1))/.01
  if z<3:ret[valid,z]=side*(q[es[valid],1]/pr[valid]-1)
 return ret.reshape(*shape,3),mfe.reshape(*shape,4),mae.reshape(*shape,4)

def periods(entries):
 d={}
 for scenario in sorted({e['scenario']for e in entries}):
  a=[e['entry_ms']for e in entries if e['scenario']==scenario];lo=min(a);hi=max(a)+M;mid=(lo+hi)//2;tail=lo+int(.6*(hi-lo));d[scenario]=dict(start=lo,end=hi,half=mid,tail=tail)
 return d

def label(e,splits):
 s=splits[e['scenario']];t=e['entry_ms']
 if t+72*H<=s['half']:return 'H1'
 if t<s['half']:return 'PURGED_H1_BOUNDARY'
 return 'H2'

def symbol_groups(entries):
 import itertools
 # Consume each group before advancing groupby; sorting group iterators would exhaust them.
 for symbol,group in itertools.groupby(sorted(entries,key=lambda e:e['symbol']),lambda e:e['symbol']):yield symbol,list(group)

def step0(entries,quotes,splits):
 control={};obs=[];storage=collections.defaultdict(list)
 for sy,group in symbol_groups(entries):
  group=list(group);q=quotes.load(sy)
  for side in [-1,1]:
   g=[e for e in group if e['side']==side]
   if not g:continue
   actualtimes=np.array([e['entry_ms']for e in g],np.int64);price=np.array([e['entry']for e in g]);ret,mfe,mae=features(q,actualtimes,price,side);times=[]
   for e in g:
    s=splits[e['scenario']];t=e['entry_ms'];part=label(e,splits);a,b=(s['start'],s['half'])if part=='H1'else(s['half'],s['tail'])if t<s['tail']and part=='H2'else(s['tail'],s['end'])if part=='H2'else(s['start'],s['half']);a=max(a,t-7*DAY);b=min(b-72*H,ASOF-72*H,t+7*DAY)
    rng=np.random.default_rng(SEED+int(e['key'][:12],16));times.append(rng.integers((a+M-1)//M,max((a+M-1)//M+1,b//M+1),size=200,dtype=np.int64)*M if b>=a else np.full(200,-1,np.int64))
   times=np.array(times);idx=np.searchsorted(q[:,0],times)if len(q)else np.zeros_like(times);cp=np.full(times.shape,np.nan)
   if len(q):safe=np.minimum(idx,len(q)-1);v=(idx<len(q))&(q[safe,0]==times);cp[v]=q[safe[v],1]
   cr,cm,ca=features(q,times,cp,side)
   for i,e in enumerate(g):
    compatible=bool(len(q)and e['entry_ms']%M==0 and (lambda k:k<len(q)and q[k,0]==e['entry_ms']and q[k,3]<=e['entry']<=q[k,2])(int(np.searchsorted(q[:,0],e['entry_ms']))))
    r=dict(key=e['key'],scenario=e['scenario'],entry_ms=e['entry_ms'],side=side,compatible=compatible,returns=ret[i].tolist(),mfe_R=mfe[i].tolist(),mae_R=mae[i].tolist(),control_mean=np.nanmean(cr[i],axis=0).tolist(),control_valid=np.isfinite(cr[i]).sum(0).tolist(),control_mfe_valid=np.isfinite(cm[i]).sum(0).tolist(),control_mfe_mean=np.nanmean(cm[i],axis=0).tolist(),control_mae_mean=np.nanmean(ca[i],axis=0).tolist(),inverse_returns=(-ret[i]).tolist(),inverse_mfe_R=mae[i].tolist(),inverse_mae_R=mfe[i].tolist());obs.append(clean(r));control[e['key']]=dict(e,signal_ms=int(times[i,0])-(e['entry_ms']-e['signal_ms']),entry_ms=int(times[i,0]),entry=float(cp[i,0])if np.isfinite(cp[i,0])else 0.,native_events=[])
    storage[e['scenario']].append((e['key'],times[i],cr[i].astype('f4'),cm[i].astype('f4'),ca[i].astype('f4')))
  quotes.cache.pop(sy,None);print('EDGE_FEATURES',sy,'entries',len(group),flush=True)
 for sc,records in storage.items():
  name=hashlib.sha256(sc.encode()).hexdigest()[:12];dest=OUT/'CONTROL200';dest.mkdir(exist_ok=True);np.savez_compressed(dest/(name+'.npz'),keys=np.array([r[0]for r in records],dtype='S64'),times=np.array([r[1]for r in records]),returns=np.array([r[2]for r in records]),mfe_R=np.array([r[3]for r in records]),mae_R=np.array([r[4]for r in records]));save(dest/(name+'.json'),dict(scenario=sc,n=len(records),replicates=200,price_R_definition='.01',key='opaque research hash',dtype='float32 outcomes; int64 timestamps',sha256=hashlib.sha256((dest/(name+'.npz')).read_bytes()).hexdigest()))
 assert len(obs)==len(entries)and len({r['key']for r in obs})==len(entries),'ENTRY_FEATURE_COVERAGE_INTEGRITY'
 gz(OUT/'ENTRY_FEATURES.json.gz',obs);gz(OUT/'CONTROL0_ENTRIES.json.gz',list(control.values()));return obs,control

def edge_tables(entries,obs,splits):
 by={e['key']:e for e in entries};out=[]
 for scenario in sorted(splits):
  for period in ['H1','H2','LAST40']:
   allrows=[r for r in obs if r['scenario']==scenario and (label(by[r['key']],splits)==period if period!='LAST40'else r['entry_ms']>=splits[scenario]['tail'])];valid=[r for r in allrows if r['compatible']and all(v is not None for v in r['returns'])and all(v is not None for v in r['control_mean'])and all(v is not None for v in r['mfe_R'])and min(r['control_valid'])>=180 and min(r['control_mfe_valid'])>=180];blocks=collections.defaultdict(float)
   for r in valid:blocks[r['entry_ms']//DAY]+=r['returns'][1]-r['control_mean'][1]
   n=len(valid);cov=n/len(allrows)if allrows else 0;p=pvalue(blocks,SEED,two=True)if n>=60 and cov>=.9 else 1.;actual=np.mean([r['returns']for r in valid],axis=0).tolist()if valid else[None]*3;excess=np.mean([[a-b for a,b in zip(r['returns'],r['control_mean'])]for r in valid],axis=0).tolist()if valid else[None]*3
   out.append(dict(scenario=scenario,period=period,total=len(allrows),n=n,coverage=cov,return_mean=actual,excess_mean=excess,p=p,mfe_R_mean=np.mean([r['mfe_R']for r in valid],axis=0).tolist()if valid else[],mae_R_mean=np.mean([r['mae_R']for r in valid],axis=0).tolist()if valid else[]))
 for sc in MISSING:
  for period in ['H1','H2','LAST40']:out.append(dict(scenario=sc,period=period,total=0,n=0,coverage=0.,return_mean=[None]*3,excess_mean=[None]*3,p=1.,mfe_R_mean=[],mae_R_mean=[]))
 train=[r for r in out if r['period']=='H1'];qs=bh([r['p']for r in train for _ in range(2)])
 gate={}
 for i,r in enumerate(train):
  r['q']=qs[2*i];ex=r['excess_mean'];v='ЕСТЬ_КРАЙ'if r['q']<=.05 and all(x is not None and x>0 for x in ex)and r['return_mean'][1]>0 else'АНТИ_КРАЙ'if r['q']<=.05 and all(x is not None and x<0 for x in ex)and r['return_mean'][1]<0 else'ШУМ';r['verdict']=v;r['data_status']='SUFFICIENT_FOR_GATE'if r['n']>=60 and r['coverage']>=.9 else'DATA_GAP_OR_INSUFFICIENT_N';gate[r['scenario']]=v
 save(OUT/'EDGE_TABLES.json',clean(out));save(OUT/'EDGE_TRAIN_FROZEN.json',dict(code_sha=CODE_SHA,decisions=gate,source='H1 only, 72h purge, BH all scenarios x two signs'));return gate

def metrics(rows):
 v=sorted([r for r in rows if r.get('net_R')is not None],key=lambda r:(r['exit_ms'],r['key']));a=np.array([r['net_R']for r in v]);eq=np.cumsum(a);loss=-a[a<0].sum();net=a.sum();top=np.sort(a)[-3:].sum();return dict(n=len(a),WR=float(100*np.mean(a>0))if len(a)else None,PF=float(a[a>0].sum()/loss)if loss else None,netR=float(net),USD_at_5risk=float(5*net),maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(a)else 0.,top3_R=float(top),top3_share_net=float(top/net)if net>0 else None,netR_adverse=float(sum(r.get('net_R_adverse',r['net_R'])for r in v)),funding_unknown_n=sum(r.get('funding_status')=='ASSUMED_ZERO_UNKNOWN'for r in v),statuses=dict(collections.Counter(r['status']for r in rows)))

def finish_cash(r,e,q,fund):
 if r['status']!='CLOSED':return r
 cash=fund.cash(e['symbol'],r,q);r['funding_status']='KNOWN_REAL_CASH'if cash is not None else'ASSUMED_ZERO_UNKNOWN';r['funding_R']=cash or 0.;r['net_R']=r['price_R']+r['funding_R'];exposure=sum(z['fraction']*max(0,z['time_ms']-r['entry_ms'])/(8*H)for z in r['events']);stress=.0001*exposure/r['risk_denominator']if cash is None else 0.;r['net_R_adverse']=r['net_R']-stress;return r

def confluence(entries,gate):
 out={};eligible=[e for e in entries if gate[e['scenario']]=='ЕСТЬ_КРАЙ']
 for e in entries:
  causal=[];symmetric=[]
  for b in eligible:
   if b['lineage']==e['lineage']or b['scenario']==e['scenario']or b['side']!=e['side']:continue
   delta=e['entry_ms']-b['signal_ms'];same=e['symbol']==b['symbol']
   if same and abs(delta)<=2*H:symmetric.append(b['key'])
   if (same and 0<=delta<=2*H)or(b['symbol']=='BTCUSDT'and 0<=delta<=4*H):causal.append(b['key'])
  out[e['key']]=dict(causal=bool(causal),causal_keys=causal,symmetric_diagnostic=bool(symmetric),future_only_diagnostic=bool(symmetric)and not causal)
 save(OUT/'CONFLUENCE_FLAGS.json',out);return out

def main():
 OUT.mkdir(exist_ok=True)
 for name,digest in read(P/'PRE_PNL_HASHES.json').items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,('FROZEN_INPUT_CHANGED',name)
 entries=read(P/'ENTRIES.json.gz');splits=periods(entries);save(OUT/'PARAMS.json',dict(asof=ASOF,seed=SEED,code_sha=CODE_SHA,entries=len(entries),R_step0=.01,random_repeats=200,managers=MANAGERS,mirrors=MIRRORS));save(OUT/'SPLITS.json',splits);q=Quotes('work/market');q.cache=__import__('collections').OrderedDict();fund=Funding('source','work/funding');collect(q,entries);obs,control=step0(entries,q,splits);gate=edge_tables(entries,obs,splits);flags=confluence(entries,gate);actual=[];null=[];selection={};index={e['key']:e for e in entries}
 # TRAIN management first; final selection file exists before any H2 exit computation.
 for phase in ['H1','H2']:
  for e in sorted(entries,key=lambda e:(e['symbol'],e['entry_ms'])):
   if label(e,splits)!=phase:continue
   verdict=gate[e['scenario']]
   if verdict=='ШУМ':continue
   mirror=verdict=='АНТИ_КРАЙ';codes=MIRRORS if mirror else MANAGERS;bars=q.load(e['symbol']);q.cache={e['symbol']:bars}
   for code in codes:
    r=finish_cash(simulate(bars,e,code,mirror),e,bars,fund);r['phase']=phase;actual.append(r);ce=control[e['key']];nr=finish_cash(simulate(bars,ce,code,mirror),ce,bars,fund);nr['phase']=phase;null.append(nr)
   if len(actual)%200==0:gz(OUT/'MANAGER_CHECKPOINT.json.gz',actual);gz(OUT/'MANAGER_CONTROL_CHECKPOINT.json.gz',null)
  if phase=='H1':
   for sc in splits:
    options=[]
    for code in MANAGERS:
     rs=[r for r in actual if r['scenario']==sc and r['manager']==code];m=metrics(rs);den=sum(e['scenario']==sc and label(e,splits)=='H1'for e in entries)
     if m['n']>=60 and den and m['n']/den>=.9:options.append((m['netR']/m['n'],code))
    selection[sc]=max(options,key=lambda t:(t[0],-int(t[1][1:])))[1]if options else None
   save(OUT/'SELECTION_FROZEN.json',dict(code_sha=CODE_SHA,winners=selection,train_results_sha256=hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest(),selection_metric='maximum H1 mean netR, n>=60 and >=90% original coverage',before_H2_manager_execution=True))
 gz(OUT/'MANAGER_TRADES.json.gz',actual);gz(OUT/'MANAGER_RANDOM_CONTROL.json.gz',null);nullmap={(r['key'],r['manager']):r for r in null};tables=[]
 for period in ['H1','H2','LAST40','ALL']:
  family=[]
  for sc in splits:
   for kind,codes in [('ORIGINAL',['X'+str(i)for i in range(10)]),('MIRROR',MIRRORS),('CONFLUENCE',['X'+str(i)for i in range(10)])]:
    for code in codes:
     rows=[r for r in actual if r['scenario']==sc and r['manager']==code and r['mirror']==(kind=='MIRROR')and(kind!='CONFLUENCE'or flags[r['key']]['causal'])and(period=='ALL'or r['phase']==period if period!='LAST40'else r['entry_ms']>=splits[sc]['tail'])];m=metrics(rows);pairs=[];blocks=collections.defaultdict(float)
     for r in rows:
      c=nullmap[(r['key'],code)]
      if r.get('net_R')is not None and c.get('net_R')is not None:pairs.append(r);blocks[r['entry_ms']//DAY]+=r['net_R']-c['net_R']
     cov=len(pairs)/m['n']if m['n']else 0.;pv=pvalue(blocks,SEED)if len(pairs)>=30 and cov>=.9 else 1.;family.append(dict(scenario=sc,kind=kind,manager=code,period=period,**m,control_n=len(pairs),control_coverage=cov,p=pv,train_winner=selection[sc]==code))
  for r,qv in zip(family,bh([r['p']for r in family]+[1.]*(24*len(MISSING)))):r['BH_q']=qv
  tables+=family
 save(OUT/'MANAGER_TABLES.json',tables);native=[dict(scenario=e['scenario'],key=e['key'],entry_ms=e['entry_ms'],native_net_R=e.get('native_net_R'),native_events=e['native_events'],note='X0 immutable historical control; original costs/venue/timeframe, not eligible for fitted manager selection')for e in entries];gz(OUT/'X0_NATIVE_REFERENCE.json.gz',native);candidates=[]
 for sc,code in selection.items():
  if not code:continue
  kind='MIRROR'if gate[sc]=='АНТИ_КРАЙ'else'ORIGINAL';rs=[next(r for r in tables if r['scenario']==sc and r['kind']==kind and r['manager']==code and r['period']==p)for p in ['H1','H2','LAST40']];edgeverify=[r for r in read(OUT/'EDGE_TABLES.json')if r['scenario']==sc and r['period']in ['H2','LAST40']];direction=1 if kind=='ORIGINAL'else-1;epass=all(r['coverage']>=.9 and r['n']>=30 and all(x is not None and direction*x>0 for x in r['excess_mean'])for r in edgeverify)
  ok=epass and all(r['n']>=(60 if r['period']=='H1'else 30)and r['PF']is not None and r['PF']>=1.3 and r['netR']>0 and r['netR_adverse']>0 and r['top3_share_net']is not None and r['top3_share_net']<=.5 for r in rs)and all(r['BH_q']<=.05 and r['control_coverage']>=.9 for r in rs[1:])
  if ok:candidates.append(dict(scenario=sc,manager=code,mirror=kind=='MIRROR',status='PROMISING_REQUIRES_CLAUDE_REVIEW',enabled=False))
 save(P/'variants.json',candidates);save(P/'CHECKPOINT.json',dict(stage='COMPLETE_WITH_EXPLICIT_DATA_GAPS',code_sha=CODE_SHA,entries=len(entries),scenarios=len(splits),edge_verdicts=dict(collections.Counter(gate.values())),manager_rows=len(actual),control_rows=len(null),train_winners=selection,candidates=len(candidates),source_jobs=read(OUT/'SOURCE_CHECKPOINT.json')['done'],source_jobs_total=read(OUT/'SOURCE_CHECKPOINT.json')['total'],no_live_changes=True));report(entries,gate,selection,tables,candidates)

def report(entries,gate,selection,tables,candidates):
 lines=['# Менеджеры на всех доступных фиксированных входах','',f'Нормализовано {len(entries)} исполненных входов, {len(gate)} сценариев. Новых сигналов/входов не генерировали. Все первоначальные отказы — EXCLUDED_INPUTS.json.gz. Приватные недостающие истории — DATA_NEEDED.md.','',f'Результаты gate: {dict(collections.Counter(gate.values()))}. Кандидатов: {len(candidates)}. Методика и ограничения — PROTOCOL_PRE_PNL_RU.md.','', '## Шаг0: TRAIN определяет разрешённые исследования','', '|Сценарий|Вердикт|Train n|Покрытие|Excess1/4/24h|q|Победитель TRAIN|','|---|---|---:|---:|---|---:|---|']
 for r in read(OUT/'EDGE_TABLES.json'):
  if r['period']=='H1':lines.append(f'|{r["scenario"]}|{gate[r["scenario"]]}|{r["n"]}|{r["coverage"]:.3f}|{r["excess_mean"]}|{r["q"]:.5f}|{selection.get(r["scenario"])}|')
 lines+=['', '## Победитель TRAIN: судьба на независимой календарной части','', '|Сценарий|Выход|Период|n|WR|PF|netR|$5 риска|DD R|BH q|Топ3/netR|','|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in tables:
  if r['train_winner']and r['period']in ['H1','H2','LAST40']and r['kind']==('MIRROR'if gate[r['scenario']]=='АНТИ_КРАЙ'else'ORIGINAL'):lines.append('|'+r['scenario']+'|'+r['manager']+'|'+r['period']+'|'+'|'.join(str(r[k])for k in ['n','WR','PF','netR','USD_at_5risk','maxDD_R','BH_q','top3_share_net'])+'|')
 lines+=['', 'Полная таблица всех разрешённых и неисполненных слотов X0–X9, зеркал и causal-confluence: RESULTS/MANAGER_TABLES.json. Неисполненные слоты не являются нулевыми PnL; n=0,p=1. X0 сохранён отдельно как несопоставимый нативный контроль и не участвовал в выборе нового победителя. Последние40% пересекают H2. Корпус ранее известен, это ретроспективная проверка, не новый forward.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','', 'Сначала сравнили цену после старых входов со случайным временем той же монеты (200 повторов). Выходы разрешены только для edge первой половины; зеркала — для anti-edge. Плохие/неполные исходники не превращались в новые исполненные сделки. Текущие слова ШУМ при недостатке цен не означают доказанное отсутствие эффекта. Все цены/отказы/неопределённости и отрицательные варианты сохранены. variants.json содержит только прошедших зафиксированные условия, по умолчанию выключенных; включение бумаги/торговли не выполнялось.','', 'Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0. Main не изменён.']
 (P/'OTCHET_DLYA_CLAUDE_CODEX_MANAGER_ALL_SCENARIOS_20261117.md').write_text('\n'.join(lines)+'\n')
ASOF=int(os.environ.get('CAR_RESEARCH_ASOF_MS',int(time.time()*1000)//M*M));CODE_SHA=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if __name__=='__main__':main()
