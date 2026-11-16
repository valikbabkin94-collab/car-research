"""Fixed-channel author audit, public archives and virtual execution only."""
import sys,json,gzip,csv,collections,hashlib,time,concurrent.futures as cf,subprocess,datetime as dt
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from market import Quotes,save,sha,month_list,M,DAY,H
from engine import simulate
LAB=Path(__file__).parent;I=LAB/'inputs';OUT=LAB/'RESULTS';CUTOFF=1794614400000

def gz(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(data,allow_nan=False).encode(),mtime=0))
def read(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.loads(p.read_text())
def collect_jobs(quote,jobs,deadline):
 jobs=sorted(set(jobs));receipts=[];previous={}
 prior=Path('work/prior-audit/RESULTS/SOURCE_CHECKPOINT.json')
 if prior.exists():
  for r in read(prior).get('receipts',[]):
   if r['status']=='DATA_GAP' and '404' in r.get('error',''):previous[(r['symbol'],r['period'],r['kind'])]=r
 def one(x):
  sym,period,kind=x
  if x in previous:return dict(previous[x],reused_negative_probe=True)
  try:return dict(symbol=sym,period=period,kind=kind,status='OK',receipt=quote.fetch(sym,period,kind))
  except Exception as e:return dict(symbol=sym,period=period,kind=kind,status='DATA_GAP',error=type(e).__name__+': '+str(e))
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for offset in range(0,len(jobs),4):
   if time.monotonic()>deadline:break
   receipts+=list(pool.map(one,jobs[offset:offset+4]));save(OUT/'SOURCE_CHECKPOINT.json',dict(total=len(jobs),completed=len(receipts),receipts=receipts))
   if len(receipts)%80==0:print('ARCHIVES',len(receipts),'/',len(jobs),flush=True)
 return receipts

def jobs_for(sym,start,end):
 jobs=[]
 for month in month_list(start,end):
  if month<'2026-11':jobs.append((sym,month,'monthly'))
  else:
   t=max(start//DAY*DAY,1793491200000)
   while t<end:jobs.append((sym,dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m-%d'),'daily'));t+=DAY
 return jobs

def stats(rows):
 good=sorted([r for r in rows if r.get('status')=='TRADE'and r.get('netR')is not None],key=lambda r:(r['exit_ms'],r['post_key']));v=np.array([r['netR']for r in good]);gain=float(v[v>0].sum());loss=float(-v[v<0].sum());eq=np.cumsum(v);return dict(n=len(v),WR=100*float(np.mean(v>0))if len(v)else None,PF=gain/loss if loss else None,netR=float(v.sum()),USD_at_5R=5*float(v.sum()),maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(v)else 0,statuses=dict(collections.Counter(r['status']for r in rows)))

def execute(signals,q,phase):
 rows=[];chunks=OUT/'chunks';chunks.mkdir(exist_ok=True);code=sha((LAB/'engine.py').read_bytes());extension=[]
 for i,s in enumerate(sorted(signals,key=lambda x:(x['symbol'],x['pub'],x['post_key']))):
  path=chunks/(s['post_key']+'.json.gz');stored=read(path)if path.exists()else {};res={};bars=None
  for policy in ['P1','P2','P3']:
   cached=stored.get(policy);plan={k:s[k]for k in ['symbol','pub','side','stop','targets']}
   if policy=='P1':plan['events']=s.get('events',[])
   input_sha=sha(json.dumps(plan,sort_keys=True).encode())
   if cached and cached.get('engine_sha')==code and (cached.get('input_sha')==input_sha or policy in ['P2','P3'] and not cached.get('input_sha')) and cached['status']in ['TRADE','REJECTED_MARKET_GEOMETRY_OR_STALE_TARGET']:r=cached
   else:
    if bars is None:bars=q.load(s['symbol'])
    r=simulate(bars,s,policy,CUTOFF);r.update(channel=s['channel'],post_key=s['post_key'],pub=s['pub'],symbol=s['symbol'],policy=policy,engine_sha=code,input_sha=input_sha,edited_visible=s['edited_visible'],edited_update_n=sum(e.get('edited_visible',False)for e in s['events']),phase=phase)
   res[policy]=r
   if r.get('needed_from_ms')and r.get('entry_ms')and r['needed_from_ms']<CUTOFF and phase==0:
    begin=r['needed_from_ms'];extension+=jobs_for(s['symbol'],begin,min(CUTOFF,begin+32*DAY))
  for policy in ['P4','P5']:
   old=s.get('legacy',{}).get(policy)
   if old:r=dict(channel=s['channel'],post_key=s['post_key'],pub=s['pub'],symbol=s['symbol'],policy=policy,status=old['status'],netR=old.get('R'),exit_ms=old.get('exit_ms'),entry_ms=old.get('fill_ms'),edited_visible=s['edited_visible'],source='LEGACY_SAVED_NO_REPLAY',funding='NOT_INCLUDED_IN_LEGACY',slippage='NOT_INCLUDED_IN_LEGACY')
   else:r=dict(channel=s['channel'],post_key=s['post_key'],pub=s['pub'],symbol=s['symbol'],policy=policy,status='LEGACY_NOT_AVAILABLE',netR=None)
   res[policy]=r
  gz(path,res);rows+=list(res.values())
  if i%200==0:print('SIGNALS',phase,i,'/',len(signals),flush=True)
 return rows,extension

def render(rows,signals,receipts):
 coverage=read(I/'CHANNEL_SOURCE_COVERAGE.json');registry=read(LAB/'CHANNEL_REGISTRY.json');splits=read(I/'LEGACY_SPLITS.json');tables=[];matched={};by=collections.defaultdict(list)
 for s in signals:by[s['channel']].append(s)
 outcomes={}
 for r in rows:outcomes.setdefault(r['post_key'],{})[r['policy']]=r
 for ch in registry:
  sigs=sorted(by[ch],key=lambda s:(s['pub'],s['post_key']));mid=(sigs[0]['pub']+sigs[-1]['pub'])/2 if sigs else 0;tailset={s['post_key']for s in sigs[int(len(sigs)*.6):]}
  if ch in splits:
   mid=dt.datetime.fromisoformat(splits[ch]['calendar_midpoint_utc']).timestamp()*1000;tailstamp=dt.datetime.fromisoformat(splits[ch]['oos_first_utc']).timestamp()*1000;tailset={s['post_key']for s in sigs if s['pub']>=tailstamp}
  matches={s['post_key']for s in sigs if all(outcomes[s['post_key']][p]['status']=='TRADE'for p in ['P1','P2','P3','P4','P5'])};matched[ch]=len(matches)
  for subset in ['AVAILABLE','MATCHED5','UNEDITED_VISIBLE_SENSITIVITY']:
   for period in ['ALL','CAL_H1','CAL_H2','HIST_LAST40','FORWARD_NEW_POSTS']:
    keys={s['post_key']for s in sigs if (period=='ALL'or period=='CAL_H1'and s['pub']<=mid or period=='CAL_H2'and s['pub']>mid or period=='HIST_LAST40'and s['post_key']in tailset)}
    if subset=='MATCHED5':keys &= matches
    if subset=='UNEDITED_VISIBLE_SENSITIVITY':keys &={s['post_key']for s in sigs if not s['edited_visible']and not any(e.get('edited_visible')for e in s['events'])}
    for policy in ['P1','P2','P3','P4','P5']:
     chosen=[r for r in rows if r['channel']==ch and r['policy']==policy and r['post_key']in keys];tables.append(dict(channel=ch,cohort=subset,period=period,policy=policy,signals=len(keys),status='NOT_STARTED'if period=='FORWARD_NEW_POSTS'else 'NO_EXECUTABLE_SIGNALS'if not sigs else 'DIAGNOSTIC_EX_FUNDING',**stats(chosen)))
 save(OUT/'TABLES.json',tables);save(OUT/'MATCHED_COHORT_COUNTS.json',matched);gz(OUT/'ALL_POLICY_TRADES.json.gz',rows)
 fields=list(tables[0]);
 with (OUT/'TABLES.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(tables)
 partial=collections.Counter(r['status']for r in rows if r['policy']=='P1');trades=[r for r in rows if r['policy']=='P1'and r['status']=='TRADE'];swing=sum(any(e['kind'].startswith('AUTHOR_CLOSE')for e in r['events'])for r in trades);cover={x['channel']:x for x in coverage}
 findings=dict(original_signals=len(signals),channels=len(registry),normalized_posts=sum(x['normalized_posts']for x in coverage),signals_with_any_linked_update=sum(x['signals_with_any_linked_update']for x in coverage),signals_with_actionable_linked_update=sum(x['actionable_update_signals']for x in coverage),P1_statuses=dict(partial),P1_trades_author_closed=swing,matched5_signal_n=sum(matched.values()),methodology_bias='NOT_ESTABLISHED_NOT_ALL_EXECUTIONS_OR_FORWARD_AVAILABLE',friend_channel='BLOCKED_USERNAME_NOT_SUPPLIED',forward='NOT_STARTED_NO_FUTURE_OBSERVATION',funding='NOT_AVAILABLE_EX_FUNDING_RESULTS',paper_candidates=[])
 save(LAB/'CHECKPOINT.json',dict(stage='INITIAL_AUDIT_COMPLETE_WITH_EXPLICIT_GAPS',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),findings=findings,resource_checkpoint=True,next='Resolve friend handle, extend censored source gaps only, verify parser links then prospective forward; never rerun legacy',LIVE_changes=0));save(LAB/'PAPER_CANDIDATES.json',[])
 lines=['# Telegram channels audit v2','', '## Фактически выполнено','',f"Проверены нормализованные посты {len(registry)} каналов. Полных исходных сигналов: {len(signals)}. Связанные обновления есть у {findings['signals_with_any_linked_update']} сигналов, явные действия CLOSE/BE/STOP — у {findings['signals_with_actionable_linked_update']}. Связь по reply или единственной монете/стороне/времени; точность ещё требует независимой проверки. TP-reached — отчёт, не команда закрытия. Идентичность авторов внутри канала неизвестна.", '',f"P1: {dict(partial)}; закрытых сделок с авторским CLOSE: {swing}. Общая закрытая выборка всех пяти политик: {sum(matched.values())}. P4/P5 переиспользованы из старого расчёта, не пересчитаны. Незаполненные и незавершённые строки сохранены. Все новые результаты EX_FUNDING, не доказанная экономическая доходность.", '', '## Каналы и покрытие','', '|Канал|Посты|Полных сигналов|С обновлением|С действием|Видимые редакции|Пропуски числовых слотов|','|---|---:|---:|---:|---:|---:|---:|']
 for ch in registry:
  c=cover[ch];lines.append('|'+ch+'|'+'|'.join(str(c[k])for k in ['normalized_posts','original_full_signals','signals_with_any_linked_update','actionable_update_signals','edited_visible','missing_numerical_slots'])+'|')
 lines+=['','## Канал друга','BLOCKED: владелец пока не сообщил @username. Свежий сбор, полная история и отдельная проверка этого канала не выполнялись. Другой канал вместо него не выбран.','', '## Пять политик на той же полностью закрытой выборке','Полные строки находятся в RESULTS/TABLES.json и CSV:45каналов ×3когорты ×5периодов ×5политик=3375строк. Ниже matched5; пустая выборка не означает убыточность.','', '|Канал|Политика|n|WR%|PF|netR|$5/R|','|---|---|---:|---:|---:|---:|---:|']
 for ch in registry:
  for r in tables:
   if r['channel']==ch and r['cohort']=='MATCHED5'and r['period']=='ALL':
    def fmt(k):v=r.get(k);return 'NA'if v is None else f'{v:.3f}'if isinstance(v,float)else str(v)
    lines.append('|'+ch+'|'+r['policy']+'|'+'|'.join(fmt(k)for k in ['n','WR','PF','netR','USD_at_5R'])+'|')
 lines+=['','## Занижала ли методика14ноября','NOT_ESTABLISHED. Подтверждены ограничения: обновления раньше не применялись, обязательные SL/TP отсекают часть форматов, старый предварительный n>=60 не давал полного исполнения по малым каналам. Но это ещё не доказывает прибыльность отвергнутых каналов. P1 меняет и вход, и выход; у новых политик есть дополнительный slippage, поэтому нельзя весь эффект назвать влиянием сопровождения. Funding и идентичность авторов неизвестны; непрерывный исторический журнал редакций отсутствует.','', '## Заявленная статистика и предвзятость зеркала','AUTHOR_STAT_CLAIMS.json содержит только нормализованные указатели заявлений, без личных ID и сырых текстов. Проценты автора без капитала/плеча/долей/издержек не сравнимы с R. Видимые TP-отчёты не доказывают касание рынка. Числовые пробелы message sequence не доказывают удалённые проигрыши: сервисные сообщения, VIP и ограничения зеркала не наблюдаемы. Исторические редакции и скрытая VIP-история неизвестны. Нет оснований объявлять45каналов убыточными или честными по этим зеркалам.','', '## Незавершённое','Нет названия канала друга и новых перспективных наблюдений. Открытые позиции не закрывались искусственно через24h/7д; CENSORED_NEEDS_EXTENSION/Data gap требуют только продолжения недостающих данных, не повторения готовых сделок. Resource checkpoint и источники сохранены. Исторические последние40% не настоящийforward. Ни один канал не объявлен прошедшим forward; PR591 и runtime не менялись.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','В старом разборе были ограничения, которые могли влиять на итог. Теперь сопровождение учитывается там, где команда однозначно распознана и связана с сигналом. Недостаток данных не записан в убытки. Прибыльность каналов и факт систематического занижения пока не доказаны.','', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
 (LAB/'OTCHET_DLYA_CLAUDE_CODEX_CHANNELS_AUDIT_V2_20261116.md').write_text('\n'.join(lines)+'\n');print(json.dumps(findings),flush=True)

def main():
 OUT.mkdir(exist_ok=True);signals=read(I/'SIGNALS_WITH_UPDATES.json.gz');q=Quotes('work/market');jobs=[];deadline=time.monotonic()+25*60
 for s in signals:jobs+=jobs_for(s['symbol'],s['pub'],min(CUTOFF,s['pub']+8*DAY))
 receipts=collect_jobs(q,jobs,deadline);save(OUT/'INITIAL_SOURCE_CHECKPOINT.json',dict(receipts=receipts,total=len(set(jobs))));rows,extension=execute(signals,q,0)
 if extension and time.monotonic()<deadline:
  new=collect_jobs(q,extension,deadline);receipts+=new;q.cache.clear();rows,_=execute(signals,q,1)
 save(OUT/'ALL_SOURCE_RECEIPTS.json',receipts);render(rows,signals,receipts)
if __name__=='__main__':main()
