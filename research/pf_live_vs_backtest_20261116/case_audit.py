"""Only the 13 supplied trades / 31 decisions; no annual replay."""
import sys,argparse,json,csv,gzip,datetime as dt,concurrent.futures as cf,collections,math,hashlib,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pf_execution_common_20261116'))
from market import Quotes,Funding,save,sha,M,H,DAY,gzread,day_list
from engine import simulate
LAB=Path(__file__).parent;I=LAB/'inputs'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',default='work/pf-case31');ap.add_argument('--out',default=str(LAB/'RESULTS/CASE31'));a=ap.parse_args();work=Path(a.work);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 T=json.loads((I/'LIVE_TRADES_AGGREGATES.json').read_text());D=json.loads((I/'LIVE_DECISIONS_AGGREGATES.json').read_text());tr=T.get('trades',T.get('rows',[]));dec=D.get('decisions',D.get('rows',[]));end=min(T['meta']['exported_ms'],D['meta']['exported_ms'])//M*M;quote=Quotes(work);fund=Funding(work,work);bylive={(x['symbol'],x['signal_ms']):x for x in tr};ref=[json.loads(x) for x in gzip.open(I/'REFERENCE_EXECUTIONS.jsonl.gz','rt')];byref={(x['symbol'],x['signal_ms']):x for x in ref}
 catalog=set(json.loads((LAB.parents[0]/'s1_s3_history_20261116/RESULTS/SOURCE_AUDIT.json').read_text())['symbols']);jobs=set();errors=[]
 for d in dec:
  sym=d['symbol'];lo=d['signal_ms']-H;hi=min(end,d['created_ms']+81*H)
  if sym not in catalog:errors.append(dict(symbol=sym,reason='NOT_IN_OLD_CATALOG_ACTUAL_ARCHIVE_STILL_REQUESTED'))
  for day in day_list(lo,hi):jobs.add((sym,day))
 def fetch(job):
  sym,day=job
  try:return dict(symbol=sym,day=day,status='OK',receipt=quote.fetch(sym,day,'daily'))
  except Exception as e:return dict(symbol=sym,day=day,status='DATA_GAP_ARCHIVE',error=type(e).__name__+': '+str(e))
 receipts=[];started=time.monotonic()
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  for offset in range(0,len(jobs),4):
   if time.monotonic()-started>420:errors.append(dict(reason='RESOURCE_CHECKPOINT_UNFETCHED_REMAIN_UNKNOWN'));break
   for r in pool.map(fetch,sorted(jobs)[offset:offset+4]):receipts.append(r)
   save(work/'COLLECTION_CHECKPOINT.json',dict(completed=len(receipts),total=len(jobs),results=receipts))
 # One host-level test; do not repeat a geographic block for every instrument.
 today=end//DAY*DAY;probe=quote.probe_rest('BTCUSDT',today,end)
 if probe is not None:
  for sym in sorted({x['symbol'] for x in dec}):quote.probe_rest(sym,today,end)
 funding_probe=None
 try:
  fund.http.get('https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-11.zip.CHECKSUM');funding_probe='AVAILABLE'
 except Exception as e:funding_probe=type(e).__name__+': '+str(e)
 if funding_probe=='AVAILABLE':
  for sym in sorted({x['symbol'] for x in dec}):
   try:fund.extend_month(sym,'2026-11',False)
   except Exception as e:errors.append(dict(symbol=sym,reason='FUNDING_MONTH_GAP',error=type(e).__name__+': '+str(e)))
 # Reuse cached Bybit5m only to recover native signal reference prices, never invent M1.
 wanted={(d['symbol'],d['signal_ms']-300000) for d in dec};native={}
 with gzip.open(I/'BYBIT_RESEARCH_5M.csv.gz','rt') as f:
  for x in csv.DictReader(f):
   key=x['symbol'],int(x['ts'])
   if key in wanted:native[key]=float(x['close'])
 rows=[]
 for d in dec:
  sym=d['symbol'];t=d['signal_ms'];q=quote.load(sym);old=byref.get((sym,t));live=bylive.get((sym,t));limit=old['limit'] if old else native.get((sym,t-300000),0)*1.013;source='ORIGINAL_BYBIT_REFERENCE_LIMIT' if old else 'CACHED_BYBIT5M_CLOSED_REFERENCE' if limit else 'BINANCE_M1_REFERENCE_PROXY'
  if not limit and len(q):
   k=np.searchsorted(q[:,0],t-M)
   if k<len(q) and q[k,0]==t-M:limit=q[k,4]*1.013
  if not limit:r=dict(status='DATA_GAP_SIGNAL_REFERENCE',symbol=sym,signal_ms=t,events=[])
  else:r=simulate(q,dict(symbol=sym,signal_ms=t,observed_ms=d['created_ms'],limit=float(limit),side=-1),end)
  funding=fund.cash(sym,r,q) if r['status']=='CLOSED' else None
  r.update(model_funding_R=funding,model_net_R=r.get('price_R',0)+funding if funding is not None else None,reference_source=source,reference_limit=float(limit) if limit else None,live_decision=d['decision'],native_old_status=old.get('status') if old else 'NOT_IN_FROZEN_YEAR_SIGNAL_SET',venue='BINANCE_PROXY_NOT_BYBIT_EXECUTION',maker_fill_verified=False)
  if live:
   gross=sum((1-e['price']/live['entry_price'])*e['fraction_of_initial_qty'] for e in live['exits'])/.0581
   r['live']={**live,'db_initial_stop_width_pct':100*(live['initial_stop_price']/live['entry_price']-1),'signal_stop_width_pct':100*(live['signal_stop_price']/live['entry_price']-1),'gross_from_rounded_exit_aggregates_R':gross,'implied_total_cost_R':gross+(live.get('funding_R') or 0)-live['net_R'],'exit_kind_is_heuristic':True}
   r['live_entry_below_reference_limit']=bool(live['entry_price']<limit) if limit else None
  rows.append(r)
 save(out/'ALL31.json',rows)
 fields=['symbol','signal_ms','decision','live_net_R','live_stop_signal_pct','db_initial_stop_pct','model_status','model_entry_ms','model_first_exit','model_price_R','model_funding_R','model_net_R','old_status','reference_source','limit','venue']
 with (out/'ALL31.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:
   live=r.get('live',{});w.writerow(dict(symbol=r['symbol'],signal_ms=r['signal_ms'],decision=r['live_decision'],live_net_R=live.get('net_R'),live_stop_signal_pct=live.get('signal_stop_width_pct'),db_initial_stop_pct=live.get('db_initial_stop_width_pct'),model_status=r['status'],model_entry_ms=r.get('entry_ms'),model_first_exit=r.get('events',[{}])[0].get('kind') if r.get('events') else None,model_price_R=r.get('price_R'),model_funding_R=r['model_funding_R'],model_net_R=r['model_net_R'],old_status=r['native_old_status'],reference_source=r['reference_source'],limit=r['reference_limit'],venue=r['venue']))
 # Pre-entry H1 return correlation. It is not binary-outcome correlation.
 data=collections.defaultdict(dict)
 for x in csv.DictReader(gzip.open(I/'TRADFI_PREENTRY_H1.csv.gz','rt')):data[x['symbol']][int(x['open_ms'])]=float(x['close'])
 common=sorted(set.intersection(*(set(v) for v in data.values())))[-169:];ret=[]
 for sym in sorted(data):ret.append([math.log(data[sym][b]/data[sym][a]) for a,b in zip(common,common[1:]) if b-a==H])
 corr=np.corrcoef(np.asarray(ret)).tolist() if ret and len(ret[0])>=48 else None
 if corr is not None and not np.all(np.isfinite(corr)):corr=None
 selected=json.loads((LAB/'RESULTS/TABLES.json').read_text());p=next(x['probability_12_of_13']['p'] for x in selected['BE_ALIGNED'] if x['cohort']=='SELECTED_DESCRIPTIVE' and x['period']=='FULL');ind=13*p**12*(1-p)+p**13;group=p*(10*p**9*(1-p)+p**10)
 summary=dict(trades_n=len(tr),wins=sum(x['net_R']>0 for x in tr),sum_live_R=sum(x['net_R'] for x in tr),first_entry_ms=min(x['entry_ms'] for x in tr),last_exit_ms=max(x['exit_ms'] for x in tr),decision_n=len(dec),not_entered_n=sum(x['decision']!='ENTERED' for x in dec),decision_coverage_complete=False,actual_loss_exit_move_pct=[100*(x['exits'][-1]['price']/x['entry_price']-1) for x in tr if x['net_R']<0],same_signal_cluster_symbols=['NBISUSDT','KORUUSDT','MVLLUSDT'],cluster_common_signal=len({x['signal_ms'] for x in tr if x['symbol'] in ['NBISUSDT','KORUUSDT','MVLLUSDT']})==1,cluster_R=sum(x['net_R'] for x in tr if x['symbol'] in ['NBISUSDT','KORUUSDT','MVLLUSDT']),preentry_return_correlation=corr,correlation_symbol_order=sorted(data),common_preentry_return_n=len(ret[0]) if ret else 0,probability_sensitivity=dict(p=p,iid_P_at_least12=ind,perfect_correlation_triplet_P_at_least12=group,assumption='Only triplet correlation changes; other10 iid; not estimated actual probability of luck'),model_status_counts=dict(collections.Counter(x['status'] for x in rows)),model_net_known_n=sum(x['model_net_R'] is not None for x in rows),funding_november_probe=funding_probe,rest_host_blocked=quote.http.rest_blocked,initial_stop_policy='5.6percent signal; DB initial fallback not attested active stop; no12percent change',model_validation='INCONCLUSIVE_SAME_VENUE_AND_EXECUTION_GAPS',annual_replay_repeated=False)
 save(out/'SUMMARY.json',summary);save(out/'SOURCES.json',dict(archive_receipts=receipts,errors=errors+quote.errors));save(out/'CHECKPOINT.json',dict(stage='TARGETED31_COMPLETE_WITH_EXPLICIT_GAPS',next='Rubik exploratory proxy matrix; no further annual replay',source_trade_commit='b711017'))
 # Update requested report; do not pretend proxy gaps prove live luck or bot skipping.
 report=f"""# PF: сверка 13 live-сделок и 18 сигналов без входа

Выгрузка b711017 разобрана. Реально: **{summary['trades_n']} сделок, {summary['wins']} прибыльных, сумма {summary['sum_live_R']:.4f}R**. Годовой replay не повторялся. Все 31 строки: [CSV](RESULTS/CASE31/ALL31.csv), [полные события](RESULTS/CASE31/ALL31.json), [источники и пробелы](RESULTS/CASE31/SOURCES.json).

|Символ|Live R|1m proxy статус|Price R модели|Net R модели|
|---|---:|---|---:|---:|
"""
 for row in rows:
  def fmt(x):return 'NA' if x is None else f'{x:.4f}'
  report+='|'+row['symbol']+'|'+fmt(row.get('live',{}).get('net_R'))+'|'+row['status']+'|'+fmt(row.get('price_R'))+'|'+fmt(row.get('model_net_R'))+'|\n'
 report+=f"""
## Стоп и различие периодов

Все 13 входов датированы 11–16 ноября. Старый годовой корпус полноценно оценивал сигналы только до 08.11 23:00 из-за требования 80h наблюдения. Сравнение годового RAW и этой live-когорты не является сравнением одинаковых сделок.

Во всех 13 карточках signal stop равен 5,6% от actual entry. Единственный убыток SPACE закрылся примерно на +5,49% против шорта. DB initial_stop около 12%/19,8% не доказывает действующий stop: snapshot стратегии имеет широкий initial fallback до custom stop. Оснований менять торговый SL на 12% нет. Нативная история стоп-ордеров отсутствует, вывод ограничен этими фактами.

Суммируются все partial exits. Переданные kind эвристические, fee_R оценочный; реальные доли отличаются от идеальных 50/30/20 из-за округления. Trade-level net_R сохраняется как передан оператором, не заменяется суммой оценочных legs и funding не прибавляется дважды.

## Корреляция

NBIS/KORU/MVLL имеют общий signal_ms: {summary['cluster_common_signal']}. Их сумма {summary['cluster_R']:.4f}R. По закрытым H1 ДО входа рассчитана матрица корреляции, n={summary['common_preentry_return_n']}; данные и значения в SUMMARY.json. Ценовая корреляция не равна корреляции бинарных побед.

При historical selected p={p:.4f} условная вероятность ≥12 побед из 13: iid **{100*ind:.2f}%**; при полной зависимости только этой тройки и независимости остальных десяти **{100*group:.2f}%**. Это чувствительность к зависимости, а не измеренная вероятность «удачи». Истинная корреляция исходов и сопоставимость p для нового режима не установлены.

## Исполнение и 18 невходов

Статусы 1m proxy: {json.dumps(summary['model_status_counts'],ensure_ascii=False)}. Полный денежный model net известен для {summary['model_net_known_n']} из 31 строк. Funding November probe: {funding_probe}. REST blocked: {quote.http.rest_blocked}. Недостающие свечи/funding дают DATA_GAP/null, не NOFILL/0.

Binance явно является proxy Bybit. Даже касание лимита здесь не устанавливает причину отказа живого бота. До истечения TTL — pending/censored. Покрытие signals.json неполное; отсутствие записи не подтверждает отсутствие всех старых сигналов. Все 18 NOT_ENTERED_UNKNOWN оставлены в таблице независимо от наличия цены.

Без native Bybit 1m и фактических order/BE updates точная реплика LIVE не сертифицирована. Лимит +1,3% может менять отбор; в live есть зона вокруг midpoint и обновляемые заявки. Это проверяемая гипотеза, не объявленная причина всей разницы. Старый BE-компонент уже проверен отдельно и не объяснил годовой убыток.

## Следующий этап

Сразу запускается заранее замороженная матрица из 20 вариантов в research/pf-rubik. Она использует 1m, stop сигнала 5,6%, BE с fees и causal receipt clock, но остаётся экспериментальным Binance proxy. Разница top50 PIT в новом ТЗ и factory top200+model top50% фиксируется в её протоколе; LIVE-вариантом её молча не называем.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

Выгрузка проверена, все сделки и невходы сохранены. Подсказка про действующий стоп 12% не подтвердилась. Положительная серия и старая история относятся к разным временным когортам; зависимость трёх одновременных сделок повышает вероятность серии. Пробелы цен/funding не скрыты. Дальше — ограниченный исследовательский поиск, без изменения торговли.

Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
"""
 (LAB/'OTCHET_DLYA_CLAUDE_CODEX_PF_LIVE_VS_BT_20261116.md').write_text(report);save(LAB/'CHECKPOINT.json',dict(stage='PART1_TARGETED31_COMPLETE_WITH_EXPLICIT_GAPS',actual_live_trades=len(tr),actual_live_wins=summary['wins'],actual_live_R=summary['sum_live_R'],source_export_commit='b711017',annual_replay_repeated=False,next='PART2 research/pf-rubik frozen20 variants; experimental proxy not validatedLIVE',LIVE_changes=0));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
