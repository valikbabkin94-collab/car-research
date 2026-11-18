"""Offline saved Bybit5m entry sensitivity and causal weekly allocator. No trading API."""
import csv,gzip,json,hashlib,collections,datetime as dt,random,math,os
from pathlib import Path
import numpy as np
LAB=Path(__file__).parent;H=3600000;S=300000;D=24*H;R=.0581
START=1762930800000;END=1794466800000;HALF=(START+END)//2;TAIL=START+int(.6*(END-START))
def save(name,x):
 p=LAB/'results'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def gzsave(name,x):
 p=LAB/'results'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(x,ensure_ascii=False,allow_nan=False).encode(),mtime=0))
def read(p):return [json.loads(l) for l in gzip.open(p,'rt')]
def load_frames(path):
 frames=collections.defaultdict(dict);bad=set();n=0
 with gzip.open(path,'rt') as f:
  for r in csv.DictReader(f):
   n+=1;sym=r['symbol'];t=int(r['ts'])
   if not START<=t<END or (sym,t) in bad:continue
   b=tuple(float(r[k]) for k in ['open','high','low','close'])
   if t%S or not all(math.isfinite(x) and x>0 for x in b) or b[2]>min(b[0],b[3]) or b[1]<max(b[0],b[3]):continue
   old=frames[sym].get(t)
   if old is not None and old!=b:bad.add((sym,t));frames[sym].pop(t);continue
   frames[sym][t]=b
 return frames,dict(rows=n,symbols=len(frames),conflicts=len(bad),bars=sum(map(len,frames.values())))
def replay(frame,signal,mode='limit_up',tps=(.021,.042,.063)):
 t=signal['signal_ms'];limit=signal['limit'];anchor=limit/1.013
 p=dict(id=signal['id'],symbol=signal['symbol'],signal_ms=t,selected=signal['selected'],mode=mode,status='RIGHT_CENSORED',events=[])
 if t+80*H>END:return p
 entry=None;et=None;targets=None;weights=[.5,.3,.2];stop=None;ambiguity=[]
 for bt in range(t,t+8*H,S):
  bar=frame.get(bt)
  if bar is None:p['status']='DATA_GAP_ENTRY_5M';return p
  o,h,l,c=bar
  if mode!='market' and h>=limit:
   entry=max(o,limit);et=bt;stop=entry*1.056;targets=[entry*(1-x) for x in tps]
   if mode=='chase_tp2' and l<=anchor*(1-tps[0]):ambiguity.append('LIMIT_AND_CHASE_SAME_5M_LIMIT_FIRST')
   break
  if mode=='market' or mode=='chase_tp2' and l<=anchor*(1-tps[0]):
   entry=c;et=bt+S
   if mode=='market':stop=entry*1.056;targets=[entry*(1-x) for x in tps]
   else:
    stop=limit*1.056;targets=[anchor*(1-x) for x in tps[1:]];weights=[.6,.4]
    if c<=targets[0] or c>=stop:p['status']='REJECTED_CHASE_GEOMETRY';return p
   break
 if entry is None:p.update(status='NOFILL',exit_ms=t+8*H);return p
 bars=[(bt,frame.get(bt)) for bt in range(et,et+72*H,S)]
 if any(b is None for _,b in bars):p.update(status='DATA_GAP_HOLD_5M',entry_ms=et);return p
 left=1.;hit=0;events=[];original_stop=stop;mfe=mae=0.
 for j,(bt,(o,h,l,c)) in enumerate(bars):
  mfe=max(mfe,(entry-l)/entry/R);mae=max(mae,(h-entry)/entry/R)
  if h>=stop:
   if hit<len(targets) and l<=targets[hit]:ambiguity.append('SL_TP_SAME_5M')
   events.append(dict(time_ms=bt+S,kind='SL' if hit==0 else 'BE',price=max(o,stop),fraction=left));left=0.;break
  if j>0:
   before=hit
   while hit<len(targets) and l<=targets[hit]:
    q=min(weights[hit],left);events.append(dict(time_ms=bt+S,kind='TP'+str(hit+1+(len(targets)==2)),price=targets[hit],fraction=q));left-=q;hit+=1
   if hit>before:stop=entry*(1-.0011)
   if left<1e-9:left=0.;break
  if j==len(bars)-1:events.append(dict(time_ms=bt+S,kind='TIME',price=c,fraction=left));left=0.
 assert abs(sum(e['fraction'] for e in events)-1)<1e-8
 p.update(status='CLOSED',entry=entry,entry_ms=et,exit_ms=events[-1]['time_ms'],events=events,initial_stop=original_stop,MFE_R=mfe,MAE_R=mae,ambiguities=ambiguity)
 return p

def economics(p,funding,signal,fee_mode='taker'):
 if p['status']!='CLOSED':return p
 e=p['entry'];events=p['events'];gross=sum((1-x['price']/e)*x['fraction'] for x in events)
 fees=.00055+sum((.0002 if fee_mode=='maker_view' and x['kind'].startswith('TP') else .00055)*x['fraction']*x['price']/e for x in events)
 if fee_mode=='maker_view':fees-=.00035
 slip=.0005*(1+sum(x['fraction']*x['price']/e for x in events))
 # Only the original trade's archived funding interval is proved by this ledger.
 a,b=signal.get('entry_ms'),signal.get('exit_ms');known=bool(funding.get('known') and a is not None and b is not None and a<=p['entry_ms'] and p['exit_ms']<=b)
 cash=0.
 if known:
  for pay in funding['payments']:
   t=pay['time_ms'];rate=pay['rate'];credit=rate>0
   if not p['entry_ms']<=t<=p['exit_ms'] or t==p['entry_ms'] and credit:continue
   rem=1-sum(x['fraction'] for x in events if x['time_ms']<(t+1 if credit else t));cash+=rate*pay['mark']/e*max(0.,rem)
 p.update(gross_R=gross/R,fee_R=fees/R,slip_R=slip/R,funding_R=cash/R if known else None,funding_known=known,net_R=(gross-fees-slip+cash)/R,unknown_funding_assumed_zero=not known)
 p['net_R_adverse']=p['net_R']-(fees+slip)/R-(0 if known else .0001*math.ceil((p['exit_ms']-p['entry_ms'])/(8*H))/R)
 return p

def metrics(rows,a=START,b=END):
 cohort=[x for x in rows if a<=x['signal_ms']<b];closed=sorted([x for x in cohort if x['status']=='CLOSED' and x['exit_ms']<b],key=lambda x:x['exit_ms']);v=np.array([x['net_R'] for x in closed]);eq=np.cumsum(v)
 return dict(opportunities=len(cohort),n=len(v),netR=float(v.sum()),WR=100*float(np.mean(v>0)) if len(v) else None,PF=float(v[v>0].sum()/-v[v<0].sum()) if np.any(v<0) else None,maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq)) if len(v) else 0.,netR_adverse=sum(x['net_R_adverse'] for x in closed),unknown_funding_n=sum(not x['funding_known'] for x in closed),statuses=dict(collections.Counter(x['status'] for x in cohort)),boundary_censored=sum(x['status']=='CLOSED' and x['exit_ms']>=b for x in cohort))
def monday(t):
 d=dt.datetime.fromtimestamp(t/1000,dt.timezone.utc);return int((d-dt.timedelta(days=d.weekday())).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()*1000)
def choose(rows,week):
 eligible=[]
 for name,rs in sorted(rows.items()):
  past=[x for x in rs if x['status']=='CLOSED' and week-28*D<=x['exit_ms']<week]
  score=sum(x['net_R'] for x in past)
  if len(past)>=10 and score>0:eligible.append((score,name,len(past)))
 if not eligible:return None
 return sorted(eligible,key=lambda x:(-x[0],x[1]))[0][1]
def weekly(rows):
 weeks=list(range(monday(START),END,7*D));decisions={w:choose(rows,w) for w in weeks};out=[]
 for name,rs in rows.items():
  out.extend(dict(x,variant=name) for x in rs if decisions.get(monday(x['signal_ms']))==name)
 return out,decisions

def daily(rows,a,b):
 out=collections.defaultdict(float)
 for x in rows:
  if x['status']=='CLOSED' and a<=x['signal_ms']<b and x['exit_ms']<b:out[x['exit_ms']//D]+=x['net_R']
 return out

def sign_p(a,b,seed=20261118):
 keys=sorted(set(a)|set(b));v=np.array([a.get(k,0)-b.get(k,0) for k in keys]);total=float(v.sum())
 if not len(v):return 1.
 rng=np.random.default_rng(seed);hits=0
 for i in range(0,9999,500):
  n=min(500,9999-i);hits+=int(np.sum((rng.choice([-1,1],size=(n,len(v)))*v).sum(axis=1)>=total))
 return (1+hits)/10000

def main():
 src=Path('saved/research/pf_live_vs_backtest_20261116/inputs');refs=read(src/'REFERENCE_EXECUTIONS.jsonl.gz');fund={x['id']:x for x in read(src/'FUNDING_EVENTS.jsonl.gz')};frames,inventory=load_frames(src/'BYBIT_RESEARCH_5M.csv.gz');save('SOURCE_INVENTORY.json',inventory);assert len(refs)==2113
 configs={'PF_BASE':('limit_up',(.021,.042,.063),'taker'),'PF_TP_FAST':('limit_up',(.015,.03,.045),'taker'),'PF_MAKER_EXIT':('limit_up',(.021,.042,.063),'maker_view'),'PF_MARKET':('market',(.021,.042,.063),'taker'),'PF_CHASE':('chase_tp2',(.021,.042,.063),'taker')}
 results={};allrows={};tables=[]
 for name,(mode,tps,fees) in configs.items():
  rs=[economics(replay(frames.get(r['symbol'],{}),r,mode,tps),fund[r['id']],r,fees) for r in refs];allrows[name]=rs;results[name]=[x for x in rs if x['selected']]
  for universe,rows in [('RAW2113',rs),('FROZEN_MODEL',results[name])]:
   for period,a,b in [('H1',START,HALF),('H2',HALF,END),('LAST40',TAIL,END),('FULL',START,END)]:tables.append(dict(variant=name,universe=universe,period=period,**metrics(rows,a,b)))
  print(name,'completed rows',len(rs),flush=True)
 gzsave('ALL_ENTRY_MODE_TRADES.json.gz',allrows);save('ENTRY_MODE_TABLES.json',tables)
 # Algebraic parity with existing BE-aligned baseline, same source5m semantics.
 fromfile=Path('baseline/research/pf_equity_switch_20261116/inputs/YEAR_BE_ALIGNED_5M.jsonl.gz')
 old=read(fromfile) if fromfile.exists() else []
 idx={x['id']:x for x in old};errors=[]
 for x in allrows['PF_BASE']:
  y=idx.get(x['id'])
  if y is None:continue
  keys=['status']+(['entry_ms','exit_ms','entry'] if x['status']=='CLOSED' and y['status']=='CLOSED' else [])
  if any(x.get(k)!=y.get(k) for k in keys) or x['status']=='CLOSED' and (abs(x['net_R']-y['net_R'])>1e-9 if y.get('net_R') is not None else abs((x['gross_R']-x['fee_R']-x['slip_R'])-y['price_R'])>1e-9):errors.append(x['id'])
 save('SAVED_BASELINE_PARITY.json',dict(compared=len(idx),differences=errors,roundoff_tolerance_R=1e-9))
 assert len(idx)==2113 and not errors,'SAVED_BASELINE_PARITY_FAILED'
 scores={name:metrics(rs,START,HALF) for name,rs in results.items()};best=sorted(scores,key=lambda n:(-scores[n]['netR'],n))[0];save('SELECTION_FROZEN.json',dict(H1_best_static=best,H1_scores=scores,selection_only_H1=True,code_sha=os.environ['GITHUB_SHA']))
 selected,decisions=weekly(results);save('WEEKLY_DECISIONS.json',[dict(monday_ms=w,winner=n,scores={k:dict(n=len([x for x in rs if x['status']=='CLOSED' and w-28*D<=x['exit_ms']<w]),netR=sum(x['net_R'] for x in rs if x['status']=='CLOSED' and w-28*D<=x['exit_ms']<w)) for k,rs in results.items()}) for w,n in decisions.items()])
 every=[dict(x,net_R=x.get('net_R',0)/len(results),net_R_adverse=x.get('net_R_adverse',0)/len(results)) for rs in results.values() for x in rs];gzsave('CONVEYOR_TRADES.json.gz',selected)
 rng=random.Random(20261118);names=sorted(results);random_summaries={};random_days={}
 for period,a,b in [('H1',START,HALF),('H2',HALF,END),('LAST40',TAIL,END),('FULL',START,END)]:
  vals=[];days=collections.defaultdict(float)
  for rep in range(1000):
   picks={w:rng.choice(names) for w in decisions};rs=[x for name,source in results.items() for x in source if picks[monday(x['signal_ms'])]==name];v=metrics(rs,a,b)['netR'];vals.append(v)
   for k,vv in daily(rs,a,b).items():days[k]+=vv/1000
  random_summaries[period]=dict(n=1000,mean=float(np.mean(vals)),median=float(np.median(vals)),p05=float(np.quantile(vals,.05)),p95=float(np.quantile(vals,.95)),conveyor_percentile=sum(v<=metrics(selected,a,b)['netR'] for v in vals)/1000)
  random_days[period]=days
 save('RANDOM1000.json',random_summaries)
 table=[];tests=[]
 for period,a,b in [('H1',START,HALF),('H2',HALF,END),('LAST40',TAIL,END),('FULL',START,END)]:
  for name,rs in [('CONVEYOR',selected),('PF_BASE',results['PF_BASE']),('H1_STATIC_'+best,results[best]),('ALL_EQUAL',every)]:table.append(dict(period=period,strategy=name,**metrics(rs,a,b)))
  if period in ['H2','LAST40']:
   cd=daily(selected,a,b)
   for name,other in [('PF_BASE',daily(results['PF_BASE'],a,b)),('H1_STATIC',daily(results[best],a,b)),('RANDOM1000_MEAN',random_days[period])]:tests.append(dict(period=period,comparison=name,excessR=sum(cd.values())-sum(other.values()),p=sign_p(cd,other)))
 order=sorted(range(len(tests)),key=lambda i:tests[i]['p']);q=1.
 for rank,i in reversed(list(enumerate(order,1))):q=min(q,tests[i]['p']*len(tests)/rank);tests[i]['BH_q']=q
 yes=all(x['excessR']>0 and x['BH_q']<=.1 for x in tests) and all(metrics(selected,a,END)['netR']>0 and metrics(selected,a,END)['netR_adverse']>0 and metrics(selected,a,END)['unknown_funding_n']==0 for a in [HALF,TAIL])
 save('CONVEYOR_TABLES.json',table);save('CONTROLS_BH.json',tests);save('variants.json',[])
 save('DATA_NEEDED.json',{'PF_TOP100':'point-in-time source ranks unavailable in saved2113 executions; cannot substitute today rank','PF_TOP200':'duplicate of source PF_BASE; not separate independent alternative','PF_WIDE':'full WIDE source signals/model metadata absent in saved2113','PF_R10':'missing10-15pct pump source signals; cannot manufacture by relabeling15pct cohort','FUND_SQUEEZE_DELIST_SHORT':'historical entry streams differ from saved2113; excluded from PF-only allocator; source mapping not established','PF_MARKET_TOP100':'requires historical rank, not inferred','funding':'saved ledger proves original holding windows only; new wider windows marked unknown0 plus adverse stress; never infer absence of payments from absent archived row','market_resolution':'5m source cannot recover minute/tick touch order; historical modes explicitly close-confirmed5m proxies, not exact forward1m parity'})
 save('CHECKPOINT.json',dict(status='COMPLETE_WITH_EXPLICIT_DATA_LIMITS',source_signals=2113,model_selected_signals=sum(x['selected'] for x in refs),variants=list(configs),profiles=len(tables),conveyor_better=yes,headline='конвейер лучше статичного и случайного на H2 и last40 — '+('ДА' if yes else 'НЕТ'),code_sha=os.environ['GITHUB_SHA'],protocol_commit='93e21a3200a4d6121de7098720dd70546b36b79f',LIVE_changes=0))
 report(table,tables,tests,random_summaries,best,yes)
def report(table,entries,tests,randoms,best,yes):
 lines=['# PF входы и конвейер — 18.11.2026','','## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','','**Конвейер лучше статичного и случайного на H2 и last40 — '+('ДА' if yes else 'НЕТ')+'.**','',f'Статичный выбор только на H1: {best}. Еженедельный выбор: закрытые сделки предыдущих28 дней, минимум10, positive max, иначе cash. Незакрытые будущие результаты не участвуют. Стратегия выбирается по дате сигнала, позиции не обрубаются при смене недели. Все R — прежний источник риска0.0581, не доходность портфеля в%.','', '|Стратегия|Период|n|netR|PF|DD R|неизвестный funding|','|---|---|---:|---:|---:|---:|---:|']
 for x in table:lines.append(f"|{x['strategy']}|{x['period']}|{x['n']}|{x['netR']:.3f}|{x['PF'] if x['PF'] is not None else 'н/д'}|{x['maxDD_R']:.3f}|{x['unknown_funding_n']}|")
 lines+=['','## Справочно: три режима на всех2113 исходных записях','','|Режим|Период|n|netR|PF|Неизвестный funding|','|---|---|---:|---:|---:|---:|']
 for x in entries:
  if x['universe']=='RAW2113' and x['variant'] in ['PF_BASE','PF_MARKET','PF_CHASE'] and x['period']!='FULL':lines.append(f"|{x['variant']}|{x['period']}|{x['n']}|{x['netR']:.3f}|{x['PF'] if x['PF'] is not None else 'н/д'}|{x['unknown_funding_n']}|")
 lines+=['','Полные negative/positive результаты, контроль1000 и BH6 — отдельные JSON. Ни один H2 максимум не использован для изменения стратегии. Last40 перекрывается сH2. RANDOM1000 — распределение одинакового недельного выбора, не1000 независимых рынков. ALL_EQUAL делит риск на фиксированное число вариантов, совпавшие сделки не имеют полный риск каждая. Это условная сумма риска на сигнал, без доказанного капитального/корреляционного лимита.','', 'Сохранённая история содержит2113 RAW, но только1041 model-selected: конвейер использует один неизменный selected-mask для всех5 сравнимых исполнений. TOP100/WIDE/R10/FUND_SQUEEZE/DELIST не придуманы из отсутствующих метаданных: DATA_NEEDED.json. PF_MAKER_EXIT — fee sensitivity, не доказанное maker-исполнение. Выбор по неизвестному funding использует0; adverse±0.01%/8h показан. При неизвестном funding положительный вывод запрещён.','', 'История — сохранённые Bybit5m, а не1m. Market/chase используют close первой подтверждающей5m; невозможно честно заявить, что это tick/1m исполнение. Исходный сигнал доступен кt, новый close доступен кt+5m, его прошедшие high/low не считаются исполнением после входа. BE исторического источника имеет−0.11% отentry, в прежнем forwardpaper BE наentry: это различие не скрыто. Фабричный code-parity и историческая справка — разные проверки.','', 'Финансовая модель не доказывает разрешение LIVE или преимущество входов: параметры не оптимизировались, paper variants отдельно в приватном коде. Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0.']
 (LAB/'results/OTCHET_RU.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
