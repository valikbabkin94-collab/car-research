"""Other package studies with explicit data gaps; no production interfaces."""
import os,json,time,io,concurrent.futures as cf,urllib.parse,gzip,csv,zipfile,hashlib,urllib.request,urllib.error,xml.etree.ElementTree as ET,collections
from pathlib import Path
import numpy as np
from .common import *
from .study import study,passed

class PIT:
 def __init__(self):
  raw=fetch_github('inputs/pit/PIT_RANKS.npz',os.environ['PIT_SOURCE_SHA']);z=np.load(io.BytesIO(raw),allow_pickle=False);self.times=z['decision_ms'];self.sy=z['symbols'];self.r=z['rank'];self.index={str(s):i for i,s in enumerate(self.sy)};self.sha=hashlib.sha256(raw).hexdigest()
 def ranks(self,t,limit):
  i=np.searchsorted(self.times,t,side='left')-1
  if i<0 or t-self.times[i]>24*H:return []
  return [str(s)for s,r in zip(self.sy,self.r[i])if 0<r<=limit]
 def rank(self,sy,t):return sy in self.ranks(t,50)

def actual_return(trade):
 total=sum(max(0,float(x['frac']))for x in trade['exits'])
 if total<=0:return None
 side=1 if trade['side']=='long'else-1;entry=trade['entry'];gross=0.;cost=.00055
 for x in trade['exits']:
  w=max(0,float(x['frac']))/total;gross+=side*(x['price']/entry-1)*w;cost+=(.0002 if x['type']=='limit'else .00055)*x['price']/entry*w
 return gross-cost

def risk_calibration(trades):
 lo=min(stamp(t['open'])for t in trades);hi=max(stamp(t['open'])for t in trades);half=(lo+hi)//2;out={'PUMP_FADE':dict(width=.056,source='SIGNAL_SL5.6_PERCENT')}
 for source in sorted({t['source']for t in trades}):
  if source=='PUMP_FADE':continue
  values=[-actual_return(t)for t in trades if t['source']==source and stamp(t['close'])<half and len(t['exits'])==1 and t['exit_reason']in['stoploss_on_exchange','stop_on_exchange_panel']and actual_return(t)is not None and actual_return(t)<0]
  out[source]=dict(width=float(np.median(values))if values else None,n_H1_full_stopouts=len(values),source='H1_MEDIAN_REALIZED_FULL_STOP_LOSS'if values else'UNKNOWN_STRATEGY_R_NO_H1_FULL_STOP_OUT')
 return out

def live_entries(trades):
 out=[]
 for n,t in enumerate(trades):
  out.append(dict(key=hashlib.sha256(json.dumps([t['source'],t['coin'],t['open'],t['close']],sort_keys=True).encode()).hexdigest(),scenario='LIVE_'+t['source'],source=t['source'],symbol=t['coin']+'USDT',side=1 if t['side']=='long'else-1,entry_ms=stamp(t['open']),signal_ms=stamp(t['open']),entry=t['entry'],entry_type='MARKET',entry_window_ms=M,native_close_ms=stamp(t['close']),actual_stop_fraction=abs(t['initial_stop']/t['entry']-1),reported_native_R=t['net_R'],exits=t['exits']))
 return out

def live_study(out,asof):
 from .runner import live_inputs,prepare_market,report,CODES
 trades=live_inputs();es=live_entries(trades);risk=risk_calibration(trades);write(out/'RISK_CALIBRATION_H1_ONLY.json',risk);market=prepare_market(es,out,asof);rows=[];baselines=[];source_results={};diagnostics=[]
 for source in sorted({t['source']for t in trades}):
  group=[e for e in es if e['source']==source];unit=risk[source]['width']or .01;codes=CODES+[f'T{j}S0B0'for j in range(6)];result=study(market,group,codes,out/source,unit=unit,family_count=14*15);source_results[source]=result
  for r in result['tables']:r['case']=source;r['risk_unit']=risk[source]['source'];r['reported_native_R_sum']=sum(t['net_R']for t in trades if t['source']==source);rows.append(r)
  # Every alternative on every actual entry is kept as descriptive audit, never used to reselect on H2.
  audit=[]
  for e in group:
   for code in codes:audit.append(dict(key=e['key'],code=code,result=finite(model(market,e,code,unit=unit)),diagnostic_only_not_used_to_reselect=True))
   q=market.get(e['symbol']);record=dict(key=e['key'],source=source,entry_ms=e['entry_ms'],native_close_ms=e['native_close_ms'],status='DATA_GAP');k=np.searchsorted(q[:,0],e['entry_ms']//M*M)
   if k<len(q)and q[k,0]==e['entry_ms']//M*M:
    record['status']='PARTIAL_AVAILABLE'
    for hours in[24,72]:
     b=np.searchsorted(q[:,0],e['entry_ms']+hours*H);v=q[k:b];complete=len(v)>=hours*60 and len(v)>0 and np.all(np.diff(v[:,0])==M)
     record[str(hours)]=dict(status='AVAILABLE'if complete else'DATA_GAP',MFE_pct=100*max(0.,float(v[:,2].max())/e['entry']-1)if e['side']==1 and len(v)else 100*max(0.,1-float(v[:,3].min())/e['entry'])if len(v)else None,MAE_pct=100*max(0.,1-float(v[:,3].min())/e['entry'])if e['side']==1 and len(v)else 100*max(0.,float(v[:,2].max())/e['entry']-1)if len(v)else None)
    a=np.searchsorted(q[:,0],e['native_close_ms']+M);b=np.searchsorted(q[:,0],e['native_close_ms']+72*H);v=q[a:b];lastpx=float(e['exits'][-1]['price']);record['extra_after_real_exit_72h_pct']=100*((float(v[:,2].max())/lastpx-1)if e['side']==1 else(1-float(v[:,3].min())/lastpx))if len(v)else None;record['post_exit_complete']=bool(len(v)>=72*60-1 and np.all(np.diff(v[:,0])==M))
   diagnostics.append(record)
  gzip_json(out/source/'ALL97_ALTERNATIVES_DIAGNOSTIC.json.gz',audit)
 for t,e in zip(trades,es):baselines.append(dict(key=e['key'],source=t['source'],open=t['open'],close=t['close'],provided_native_R=t['net_R'],reconstructed_price_return=actual_return(t),calibrated_R=actual_return(t)/risk[t['source']]['width']if risk[t['source']]['width']and actual_return(t)is not None else None,risk_source=risk[t['source']]['source'],exit_fractions_normalized=[x['frac']/sum(z['frac']for z in t['exits'])for x in t['exits']],funding_actual_cash_not_in_export=True,initial_stop_is_emergency_not_R=True))
 pf_audit=load(out/'PUMP_FADE'/'ALL97_ALTERNATIVES_DIAGNOSTIC.json.gz')if(out/'PUMP_FADE'/'ALL97_ALTERNATIVES_DIAGNOSTIC.json.gz').exists()else[];pairs=collections.defaultdict(dict)
 for row in pf_audit:
  if row['code']in['T0S0B0','T1S0B0']:pairs[row['key']][row['code']]=row['result']
 paired=[v for v in pairs.values()if len(v)==2 and all(r[0]==1 for r in v.values())]
 write(out/'CLAUDE_15PF_HINT_VERIFICATION.json',dict(input_n=15,paired_executable_n=len(paired),current_T0_netR=sum(v['T0S0B0'][1]for v in paired),wider_T1_netR=sum(v['T1S0B0'][1]for v in paired),R_price_width=.056,actual_safety_stop_used_as_stop_not_R=True,legacy_2_06_2_81_not_assumed=True))
 write(out/'SOURCE_VERDICTS.json',[dict(source=source,n=sum(t['source']==source for t in trades),verdict='INCONCLUSIVE_SMALL_N',reason='Early-exit vs entry-edge cannot be established statistically from1–16 trades/source; descriptive path and paired alternatives preserved')for source in risk])
 write(out/'X0_ACTUAL_FILLS_AUDIT.json',baselines);write(out/'POST_ENTRY_AND_EXIT.json',finite(diagnostics));write(out/'ALL_SOURCE_TABLES.json',finite(rows));write(out/'variants.json',[])
 report(out,'Часть7 — все97 закрытых живых сделок',f'Все97 записей сохранены; источников {len(risk)}. Доли выходов нормализованы суммой fill frac, а не обрезаны на1. initial_stop не использован как1R. Калибровка R только по H1 полным стопам источника, PUMP_FADE5.6%; при отсутствии калибровки — явно PRICE_R1%, не финансовый R. Кандидатов0: малые независимые выборки не позволяют выполнить n60/30.',rows,notes='X0: сырой net_R выгрузки хранится отдельно, знаменатель не сопоставляется молча с новыми R. Восстановленный процент из заполнений — модель известных комиссий; фактического funding/исходного notional нет в выгрузке. Все X1–X9/T0–T5 выполнены для каждой доступной входной точки, включая отрицательные; таблицаH2 используется только для frozen H1 winner, остальныеH2 записаны diagnostic-only. Неподтверждённые1m цены Bybit-only и неполные горизонты — DATA_GAP. Ранний выход и плохой вход не объявляются систематическими по1–16 сделкам; нужны контроль и достаточный n. Подсказка Claude на15 PF проверяется как диагностический пакет, а не обещание +2.81R.')
 return dict(status='COMPLETE_SMALL_N_INCONCLUSIVE',raw_trades=97,sources=len(risk),candidates=0)

def oleg(out,asof):
 from .runner import live_inputs,report
 ts=live_inputs();oleg=[t for t in ts if t['source']=='OLEG'];style=[t for t in ts if t['source']=='OLEG_STYLE'];audit=[]
 for name,group in [('O0_LIVE_AVAILABLE_ONLY',oleg),('O1_SHORT', [t for t in oleg if t['side']=='short']),('O2_LONG',[t for t in oleg if t['side']=='long']),('OLEG_STYLE',style)]:
  values=[actual_return(t)for t in group];audit.append(dict(variant=name,n=len(group),observed_price_return_sum=sum(v for v in values if v is not None),reported_native_R_sum=sum(t['net_R']for t in group),full_history=False,not_independent_validation=True))
 write(out/'AVAILABLE_LIVE_DESCRIPTIVE_ONLY.json',audit);write(out/'variants.json',[]);write(out/'DATA_NEEDED.json',dict(missing='Complete normalized Oleg signal history, author entry zones/SL/TP and source chronology',searched_sources=['feat/tg-only-live-20261111','research/codex-direction-new14-oleg-20261110','feat/manager-author-zone-20261114','data/tg-mirrors-20261114'],found='oleg_main_study.py/oleg_style_study.py are tools reading an external Honor archive, not the archive itself',required_fields=['published_utc','first_observed_utc','symbol','side','entry_low','entry_high','stop','targets','updates_time','revision_vintage']))
 report(out,'Часть1 — OLEG_FIX',f'Полная история сигналов в проверенных GitHub-источниках не найдена. Доступны {len(oleg)} живых OLEG и {len(style)} OLEG_STYLE; они не подменяют полную историю. O0/O1/O2: сохранён описательный разбор реальных заполнений. O3/O4/O5 требуют авторских зон/стопов/целей, которых в97-trade export нет. DATA_GAP; прибыльность не доказана.',notes='Пути и код инструментов проверены, доступ к Honor/Acer/Telegram не выполнялся. OLEG_STYLE3/3 — слишком маленькая выборка для статистического вывода. Полный replay всех97 и менеджеров выполняется независимым параллельнымPart7; повторного счёта тех же вариантов здесь нет.')
 return dict(status='DATA_GAP_FULL_OLEG_ARCHIVE',available_OLEG=len(oleg),available_STYLE=len(style),candidates=0)

def timing(out,asof):
 from .runner import native_entries,prepare_market,report,live_inputs
 es=[dict(e,entry_window_ms=5*M)for e in native_entries()if e['scenario']=='PF_BASE'];m=prepare_market(es+[dict(es[0],symbol='BTCUSDT')],out,asof);btc=m.get('BTCUSDT').copy();sp=splitting(es);records=[]
 for e in es:
  r=model(m,e,'T0S0B0',unit=.056);d=dt.datetime.fromtimestamp(e['entry_ms']/1000,dt.timezone.utc);j=np.searchsorted(btc[:,0],e['signal_ms']//M*M)-1;i=j-240;bs='UNKNOWN'
  if i>=0 and j<len(btc)and btc[j,0]-btc[i,0]==4*H:bs='UP'if btc[j,4]>btc[i,4]else'DOWN'
  records.append(dict(e=e,r=r,hour=d.hour//6,dow=d.weekday(),weekend=d.weekday()>=5,btc=bs))
 predicates={**{'EXCLUDE_UTC_'+str(k):lambda r,k=k:r['hour']!=k for k in range(4)},**{'EXCLUDE_DOW_'+str(k):lambda r,k=k:r['dow']!=k for k in range(7)},'WEEKDAYS_ONLY':lambda r:not r['weekend'],'WEEKENDS_ONLY':lambda r:r['weekend'],'BTC_UP_ONLY':lambda r:r['btc']=='UP','BTC_DOWN_ONLY':lambda r:r['btc']=='DOWN'}
 train=[r for r in records if phase(r['e'],sp)=='H1'];options=[];table=[]
 for name,fn in predicates.items():
  selected=[r for r in train if fn(r)];stats=metrics([r['r']for r in selected]);table.append(dict(variant=name,period='H1',**stats))
  if stats['n']>=60:options.append((stats['netR'],name))
 winner=max(options)[1]if options else None;write(out/'SELECTION_FROZEN.json',dict(winner=winner,train_only=True,one_filter_only=True,split=sp))
 if winner:
  for period in ['H2','LAST40']:
   rs=[r for r in records if phase(r['e'],sp)=='H2'and predicates[winner](r)and(period=='H2'or r['e']['entry_ms']>=sp[2])];null=[controls(m,r['e'],'T0S0B0',sp,unit=.056)for r in rs];test=paired_test([r['r']for r in rs],null);table.append(dict(variant=winner,period=period,**metrics([r['r']for r in rs]),excessR=test['excessR'],p=test['p'],BH_q=min(1.,test['p']*15),control_coverage=test['coverage']))
 descriptive=[]
 for dimension,values in [('UTC_BLOCK',range(4)),('DOW',range(7)),('WEEKEND',[False,True]),('BTC',['UP','DOWN','UNKNOWN'])]:
  key={'UTC_BLOCK':'hour','DOW':'dow','WEEKEND':'weekend','BTC':'btc'}[dimension]
  for value in values:descriptive.append(dict(dimension=dimension,value=value,**metrics([r['r']for r in records if r[key]==value])))
 write(out/'DESCRIPTIVE_ALL_PERIODS_NOT_FOR_SELECTION.json',finite(descriptive));write(out/'TABLES.json',finite(table));gzip_json(out/'BASELINE_ALL_ENTRIES.json.gz',finite([dict(key=r['e']['key'],groups={k:r[k]for k in['hour','dow','weekend','btc']},outcome=r['r'])for r in records]));write(out/'LIVE15_DESCRIPTIVE.json',[t for t in live_inputs()if t['source']=='PUMP_FADE']);variants=[dict(name='PF_TIMING_'+winner,enabled=False,filter=winner,status='PROMISING_REQUIRES_CLAUDE_REVIEW')]if winner and passed(table,winner)else[];write(out/'variants.json',variants)
 report(out,'Часть5 — PF_TIMING',f'2113 исходных записей / {len(es)} сохранённых входов. Описательные группыUTC×6ч, дни недели, выходные, BTC4h; ровно один фильтр выбранH1: {winner}. 15 живых PF сохранены отдельно как наблюдение, не смешаны с исторической оптимизацией.',table,notes='Базовый выход для этой части зафиксированT0S0B0, thirds, SL5.6%, R5.6%; это не повтор Part6, где stop12 и другие варианты. Все описательные H2 группы не используются для выбора нового фильтра. Кандидат после независимой проверки и общих порогов; при недоказанном n/control — INCONCLUSIVE.')
 return dict(status='COMPLETE_WITH_DATA_GAPS',winner=winner,candidates=len(variants))

def listing_catalog(market,out):
 prefix='data/futures/um/monthly/klines/';url='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?list-type=2&delimiter=/&prefix='+prefix
 records=[];token=None;symbols=[]
 for page in range(10):
  u=url+('&continuation-token='+urllib.parse.quote(token,safe='')if token else'')
  with urllib.request.urlopen(u,timeout=30)as r:raw=r.read(5000000)
  root=ET.fromstring(raw);ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'};records.append(dict(url=u,sha256=hashlib.sha256(raw).hexdigest()))
  for v in root.findall('s:CommonPrefixes/s:Prefix',ns):
   sy=v.text.rstrip('/').split('/')[-1]
   if sy.endswith('USDT'):symbols.append(sy)
  nxt=root.find('s:NextContinuationToken',ns)
  if nxt is None:break
  token=nxt.text
 else:raise ValueError('CATALOG_PAGINATION_INCOMPLETE')
 write(out/'CATALOG_RECEIPTS.json',records);return sorted(set(symbols))

def listing(out,asof):
 from .runner import report
 market=Market(asof);birth={};errors=[]
 try:symbols=listing_catalog(market,out)
 except Exception as ex:
  write(out/'DATA_NEEDED.json',dict(reason='Historical archive universe catalogue not accessible; current exchange list cannot replace delisted history',error=type(ex).__name__+':'+str(ex)));write(out/'variants.json',[]);report(out,'Часть2 — NEW_LISTING_FADE','DATA_BLOCKED: полный исторический Binance USDT-M catalogue недоступен. Survivorship bias не обходился выбором сегодняшних монет.');return dict(status='DATA_BLOCKED_UNIVERSE',candidates=0)
 deadline=time.monotonic()+25*60
 def first(sy):
  prefix='data/futures/um/monthly/klines/'+sy+'/1m/';u='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?list-type=2&max-keys=2&prefix='+prefix
  try:
   with urllib.request.urlopen(u,timeout=20)as r:raw=r.read(2000000)
   root=ET.fromstring(raw);keys=[v.text for v in root.iter()if v.tag.endswith('Key')and v.text and v.text.endswith('.zip')]
   if not keys:return sy,None,'NO_MONTHLY_1M_ARCHIVE'
   key=min(keys);mon=key.rsplit('-',2)[-2:] # suffix YYYY-MM.zip
   name=key.split('/')[-1];period=name.split('-1m-')[1].removesuffix('.zip');receipt=market.quotes.fetch(sy,period,'monthly');arr=np.load(market.quotes.root/'m1'/f'{sy}-{period}.npz',allow_pickle=False)['bars'];lo=receipt['first_ms'];i=np.searchsorted(arr[:,0],lo);end=np.searchsorted(arr[:,0],lo+H)
   if end-i!=60:return sy,None,'NO_COMPLETE_FIRST_HOUR'
   return sy,dict(first_ms=int(lo),first_hour_close=float(arr[end-1,4]),source_key=key,source_sha256=receipt['source_sha256']),None
  except Exception as ex:return sy,None,type(ex).__name__+':'+str(ex)
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for j in range(0,len(symbols),4):
   if time.monotonic()>deadline:break
   for sy,item,error in pool.map(first,symbols[j:j+4]):
    if item:birth[sy]=item
    else:errors.append(dict(symbol=sy,error=error))
   if j%80==0:print('LISTING_FIRST_ARCHIVE',j,'/',len(symbols),flush=True)
 write(out/'FIRST_ARCHIVES.json',birth);write(out/'CATALOG_ERRORS.json',dict(requested=len(symbols),processed=len(birth)+len(errors),errors=errors))
 entries=[]
 for sy,record in birth.items():
  for delay in[24,48,72]:
   ts=record['first_ms']+delay*H
   if ts>=asof:continue
   entries.append(dict(key=hashlib.sha256(f'{sy}:{ts}:N{delay}'.encode()).hexdigest(),scenario='NEW_LISTING_FADE',symbol=sy,entry_ms=ts,signal_ms=ts,side=-1,entry_type='MARKET',entry_window_ms=M,first_hour_close=record['first_hour_close'],delay=delay))
 write(out/'SOURCE_WINDOWS.json',market.collect([(e['symbol'],e['entry_ms']-H,min(asof,e['entry_ms']+8*DAY))for e in entries],minutes=25));selected=[];rejected=[]
 for e in entries:
  q=market.get(e['symbol']);i=np.searchsorted(q[:,0],e['entry_ms'])
  if i<len(q)and q[i,0]==e['entry_ms']and q[i,1]>e['first_hour_close']:selected.append(dict(e,entry=float(q[i,1])))
  else:rejected.append(dict(e,status='PRICE_FILTER_REJECTED'if i<len(q)and q[i,0]==e['entry_ms']else'DATA_GAP'))
 write(out/'REJECTED_ENTRIES.json',rejected)
 if not selected:write(out/'variants.json',[]);report(out,'Часть2 — NEW_LISTING_FADE','Нет исполнимых входов по зарегистрированным условиям; источники/отказы сохранены.');return dict(status='INCONCLUSIVE_NO_EXECUTABLE_ENTRIES',candidates=0)
 sp=splitting(selected);train=[];opts=[];actual_audit=[];codes=['N24','N48','N72']
 for c in codes:
  es=[e for e in selected if e['delay']==int(c[1:])and phase(e,sp,168)=='H1'];rs=[model(market,e,c)for e in es];actual_audit.extend(dict(key=e['key'],variant=c,period='H1',outcome=finite(r))for e,r in zip(es,rs));m=metrics(rs);train.append(dict(variant=c,period='H1',**m))
  if m['n']>=60:opts.append((m['netR'],c))
 winner=max(opts)[1]if opts else None;write(out/'SELECTION_FROZEN.json',dict(winner=winner,split=sp,train_only=True));write(out/'INPUTS.json',selected)
 # Other-coin top100 benchmark, same clock: no future price/universe substitution.
 try:pit=PIT()
 except Exception as ex:pit=None;write(out/'PIT_ERROR.json',dict(error=str(ex)))
 if winner:
  test=[e for e in selected if e['delay']==int(winner[1:])and phase(e,sp,168)=='H2'];actual=[model(market,e,winner)for e in test];actual_audit.extend(dict(key=e['key'],variant=winner,period='H2',outcome=finite(r))for e,r in zip(test,actual));null=np.full((len(test),200),np.nan);control_inputs=[]
  for i,e in enumerate(test):
   pool=[s for s in(pit.ranks(e['entry_ms'],100)if pit else[])if s!=e['symbol']and s in birth and birth[s]['first_ms']<e['entry_ms']]
   if not pool:continue
   rng=np.random.default_rng(SEED+int(e['key'][:12],16))
   for j,sy in enumerate(rng.choice(pool,200)):control_inputs.append((str(sy),i,j,e))
  market.collect([(sy,e['entry_ms']-H,e['entry_ms']+8*DAY)for sy,i,j,e in control_inputs],minutes=20)
  for sy,i,j,e in sorted(control_inputs,key=lambda x:x[0]):
   q=market.get(sy);k=np.searchsorted(q[:,0],e['entry_ms'])
   if k<len(q)and q[k,0]==e['entry_ms']:
    r=model(market,dict(e,symbol=sy,entry=float(q[k,1])),winner);null[i,j]=r[1]if r[0]==1 else np.nan
  np.savez_compressed(out/'H2_CONTROL200_TOP100.npz',netR=null)
  for period in ['H2','LAST40']:
   idx=[i for i,e in enumerate(test)if period=='H2'or e['entry_ms']>=sp[2]];rows=[actual[i]for i in idx];p=paired_test(rows,[null[i]for i in idx]);train.append(dict(variant=winner,period=period,**metrics(rows),excessR=p['excessR'],control_coverage=p['coverage'],BH_q=min(1.,p['p']*3)))
 gzip_json(out/'ALL_ACTUAL_EXITS.json.gz',actual_audit);write(out/'TABLES.json',finite(train));variants=[dict(name='NEW_LISTING_FADE_'+winner,enabled=False,status='PROMISING_REQUIRES_CATALOGUE_AND_CLAUDE_REVIEW')]if winner and passed(train,winner)else[];write(out/'variants.json',variants);report(out,'Часть2 — NEW_LISTING_FADE',f'Каталог {len(symbols)} символов, подтверждённых первых часов{len(birth)}; входов {len(selected)}. Frozen winner {winner}. Контроль: исторический PIT top100, та же дата; периоды без PIT остаются DATA_GAP.',train,notes='Биржевой каталог включает delisted. Не брали первую свечу случайно обрезанного локального кэша как дату листинга: проверялся первый доступный monthly1m archive. У неполной первой истории/новейших daily-only листингов DATA_GAP. Ограничение текущего запуска: кандидат не повышается без независимого подтверждения полноты catalogue/PIT и отсутствующих ранних интервалов.')
 return dict(status='COMPLETE_WITH_DATA_GAPS',catalogue_symbols=len(symbols),first_archives=len(birth),entries=len(selected),winner=winner,candidates=len(variants))

def volume_bars(market,sy,period,kind='monthly'):
 dest=market.quotes.root/'volume'/f'{sy}-{period}.npz';meta=dest.with_suffix('.json')
 if dest.exists()and meta.exists():
  receipt=load(meta)
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=receipt['parsed_sha256']:raise ValueError('VOLUME_CACHE_SHA')
  return np.load(dest,allow_pickle=False)['bars'],receipt
 rows,receipt=market.quotes.http.archive(f'data/futures/um/{kind}/klines/{sy}/1m/{sy}-1m-{period}.zip');arr=np.array([[int(r[0]),float(r[1]),float(r[2]),float(r[3]),float(r[4]),float(r[5])]for r in rows],float);dest.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(dest,bars=arr);receipt['parsed_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest();write(meta,receipt);return arr,receipt

def wick(out,asof):
 from .runner import native_entries,report
 m=Market(asof);symbols=sorted({e['symbol']for e in native_entries()});candidates=[];receipts=[];missing=[]
 try:pit=PIT()
 except Exception:pit=None
 deadline=time.monotonic()+35*60
 for sy in symbols:
  q=m.get(sy)
  if len(q)<1442:continue
  ranges=q[:,2]-q[:,3];lower=np.minimum(q[:,1],q[:,4])-q[:,3];upper=q[:,2]-np.maximum(q[:,1],q[:,4]);down=1-q[:,3]/q[:,1];up=q[:,2]/q[:,1]-1
  for side,move,shadow in[(1,down,lower),(-1,up,upper)]:
   ix=np.where((move>=.03)&(ranges>0)&(shadow>=.4*ranges))[0]
   bymonth=collections.defaultdict(list)
   for i in ix:
    if move[i]<.05 and(not pit or not pit.rank(sy,q[i,0])):continue
    period=dt.datetime.fromtimestamp(q[i,0]/1000,dt.timezone.utc).strftime('%Y-%m');bymonth[period].append(int(i))
   for month,inds in bymonth.items():
    if time.monotonic()>deadline:missing.append(dict(symbol=sy,month=month,reason='RESOURCE_CHECKPOINT'));continue
    try:
     v,receipt=volume_bars(m,sy,month);receipts.append(dict(symbol=sy,month=month,**receipt))
     if any(q[i,0]<stamp(month+'-01')+DAY for i in inds):
      prev=dt.datetime.fromtimestamp((stamp(month+'-01')-M)/1000,dt.timezone.utc).strftime('%Y-%m');prior,pr=volume_bars(m,sy,prev);v=np.concatenate([prior[-1440:],v]);receipts.append(dict(symbol=sy,month=prev,**pr))
    except Exception as ex:missing.append(dict(symbol=sy,month=month,error=str(ex)));continue
    for i in inds:
     k=np.searchsorted(v[:,0],q[i,0]);past=v[max(0,k-1440):k]
     if len(past)!=1440 or np.any(np.diff(past[:,0])!=M):missing.append(dict(symbol=sy,time=int(q[i,0]),reason='NO_CONTIGUOUS_VOLUME_PAST24H'));continue
     median=float(np.median(past[:,5]));
     if median<=0 or v[k,5]<10*median:continue
     for delay in[1,2]:
      j=i+delay
      if j>=len(q)or q[j,0]!=q[i,0]+delay*M:continue
      entry=float(q[j,1]);stop=float(q[i,3]*.997 if side==1 else q[i,2]*1.003);width=side*(entry-stop)/entry
      if width<=0:continue
      code=('WL'if side==1 else'WS')+str(delay-1);candidates.append(dict(key=hashlib.sha256(f'{sy}:{q[i,0]}:{code}'.encode()).hexdigest(),scenario='LIQ_WICK_REBOUND',symbol=sy,entry_ms=int(q[j,0]),signal_ms=int(q[i,0]+delay*M)-1,entry=entry,side=side,entry_type='MARKET',entry_window_ms=M,wick_risk_fraction=width,variant=code,volume_rvol=float(v[k,5]/median)))
  if len(candidates)%50==0:print('WICK_EVENTS',sy,len(candidates),flush=True)
 write(out/'VOLUME_SOURCES.json',receipts);write(out/'DATA_GAPS.json',missing);write(out/'INPUTS.json',candidates);tables=[];actual_audit=[];null_audit=[]
 # Four fixed variants have different entry points, so select on H1 then test the chosen rule, not a new entry.
 if candidates:
  sp=splitting(candidates);opts=[]
  for code in['WL0','WL1','WS0','WS1']:
   es=[e for e in candidates if e['variant']==code and phase(e,sp,4)=='H1'];rs=[model(m,e,code)for e in es];actual_audit.extend(dict(key=e['key'],variant=code,period='H1',outcome=finite(r))for e,r in zip(es,rs));met=metrics(rs);tables.append(dict(variant=code,period='H1',**met))
   if met['n']>=60:opts.append((met['netR'],code))
  winner=max(opts)[1]if opts else None;write(out/'SELECTION_FROZEN.json',dict(winner=winner,split=sp,train_only=True))
  if winner:
   es=[e for e in candidates if e['variant']==winner and phase(e,sp,4)=='H2'];rs=[model(m,e,winner)for e in es];null=[controls(m,e,winner,sp)for e in es];actual_audit.extend(dict(key=e['key'],variant=winner,period='H2',outcome=finite(r))for e,r in zip(es,rs));null_audit=finite(null)
   for period in['H2','LAST40']:
    ix=[i for i,e in enumerate(es)if period=='H2'or e['entry_ms']>=sp[2]];aa=[rs[i]for i in ix];test=paired_test(aa,[null[i]for i in ix]);tables.append(dict(variant=winner,period=period,**metrics(aa),excessR=test['excessR'],control_coverage=test['coverage'],BH_q=min(1.,test['p']*4)))
 else:winner=None
 gzip_json(out/'ALL_ACTUAL_EXITS.json.gz',actual_audit);gzip_json(out/'CONTROL200.json.gz',null_audit);write(out/'TABLES.json',finite(tables));variants=[dict(name='LIQ_WICK_'+winner,enabled=False,status='PROMISING_CACHED_UNIVERSE_ONLY_REQUIRES_CLAUDE_REVIEW')]if winner and passed(tables,winner)else[];write(out/'variants.json',variants);report(out,'Часть3 — LIQ_WICK_REBOUND',f'Реальных событий после проверки цены/объёма: {len(candidates)}; frozen winner {winner}. LONG после нижней тени и SHORT после верхней, два момента подтверждения.',tables,notes='Падение/памп — excursion open→low/high в минуте; тень≥40%, объём текущей минуты≥10×медианы предшествующих1440 закрытых минут. Вход — первый доступный open после закрытой свечи/следующей свечи, не неисполняемый close задним числом. SL по исходной тени±.3%, TP1/2R50/50, max4h. OHLС-cache не содержитV: volume отдельно взят только для price-кандидатов, не выдуман. Для первых суток месяца догружается предыдущий volume-window; недоступное помечено DATA_GAP. Случайный контроль сохраняет относительную ширину wick-stop.')
 return dict(status='COMPLETE_WITH_DATA_GAPS',events=len(candidates),winner=winner,candidates=len(variants))

def execute(part,out,asof):
 if part=='part1_oleg_fix':return oleg(out,asof)
 if part=='part2_new_listing':return listing(out,asof)
 if part=='part3_liq_wick':return wick(out,asof)
 if part=='part5_pf_timing':return timing(out,asof)
 if part=='part7_live_trades':return live_study(out,asof)
 raise ValueError(part)
