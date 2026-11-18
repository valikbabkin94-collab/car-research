import json,gzip,collections,subprocess,datetime as dt
from pathlib import Path
import numpy as np
from market import save,M,H,DAY
from policies import O,C
B=Path('research/oleg_private_20261118');I=B/'inputs'
def load(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.load(p.open())
def read(name):
 rows=[]
 for p in Path('results').glob('*_shard*/'+name):rows+=load(p)
 return rows

def metrics(rows,bound=None):
 rr=[r for r in rows if not str(r['status']).startswith(('NOT_APPLICABLE','DIRECTION_FILTER'))];eligible=[r for r in rr if r.get('net_R')is not None and(r['status']=='NOFILL'and r.get('intent_expiry_ms',0)<(bound or 10**20)or r['status']=='CLOSED'and r.get('exit_ms',10**20)<(bound or 10**20))];closed=sorted([r for r in eligible if r['status']=='CLOSED'],key=lambda r:r['exit_ms']);x=np.array([r['net_R']for r in closed]);eq=np.cumsum(x);loss=-x[x<0].sum();gaps=sum(any(k in str(r['status'])for k in['DATA_GAP','NO_ENTRY','NO_SOURCE','MISSING_24H'])for r in rr);censored=sum('CENSORED'in str(r['status'])or(bound is not None and r.get('exit_ms',0)>=bound)for r in rr)
 return dict(n_input=len(rr),n=len(x),nofill=sum(r['status']=='NOFILL'for r in eligible),rejected=sum(str(r['status']).startswith(('REJECTED','MISSING_AUTHOR','MISSING_SECOND','LIVE_TARGET'))for r in rr),gaps=gaps,censored=censored,coverage=1-gaps/max(1,len(rr)),netR=float(x.sum()),WR=float(100*np.mean(x>0))if len(x)else None,PF=float(x[x>0].sum()/loss)if loss else None,maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(x)else None,meanR=float(x.mean())if len(x)else None,mean_holding_h=float(np.mean([r['hold_hours']for r in closed]))if closed else None,netR_adverse=float(sum(r['net_R_adverse']for r in closed)),fee_R=float(sum(r['fee_R']for r in closed)),funding_R=float(sum(r['funding_R']for r in closed)),funding_unknown_n=sum(not r['funding_known']for r in closed),top3_share=float(np.sort(x)[-3:].sum()/x.sum())if x.sum()>0 else None,statuses=dict(collections.Counter(r['status']for r in rr)))

def paired(rows,cm,bound=None):
 blocks={};ds=[];actual=0.;control=0.
 for r in rows:
  c=cm.get((r['post_key'],r['policy']));a=r.get('net_R');b=c.get('net_R')if c else None
  if a is None or b is None:continue
  if bound and(r.get('exit_ms',0)>=bound or c.get('exit_ms',0)>=bound or(r['status']=='NOFILL'and r.get('intent_expiry_ms',0)>=bound)or(c['status']=='NOFILL'and c.get('intent_expiry_ms',0)>=bound)):continue
  v=a-b;ds.append(v);day=r['available_ms']//DAY;blocks[day]=blocks.get(day,0.)+v;actual+=a;control+=b
 p=1.
 if len(ds)>=30 and len(blocks)>=8:
  a=np.array(list(blocks.values()));rng=np.random.default_rng(20261118);p=(1+int(np.sum(rng.choice([-1,1],size=(9999,len(a)))@a>=a.sum())))/10000
 return dict(paired_n=len(ds),excessR=float(sum(ds)),paired_actual_R=actual,paired_control_R=control,p=p)

def bh(ps):
 ix=np.argsort(ps);q=np.ones(len(ps));v=1.
 for k in range(len(ps)-1,-1,-1):j=ix[k];v=min(v,ps[j]*len(ps)/(k+1));q[j]=v
 return q

def main():
 a=read('ACTUAL.json.gz');c=read('CONTROL.json.gz');assert len(a)==len(c)==len(load(I/'PLANS.json.gz'))*7,'INCOMPLETE_CASE_MATRIX';assert len({(r['post_key'],r['policy'])for r in a})==len(a),'DUPLICATE_CASE';claims=read('CLAIMS.json.gz');cm={(r['post_key'],r['policy']):r for r in c};st={r['channel']:r for r in load(I/'DATA_INVENTORY.json')};out=B/'final';out.mkdir(parents=True,exist_ok=True);table=[];selection={}
 for ch,s in st.items():
  codes=O if ch=='OLEG'else C;rr=[r for r in a if r['channel']==ch];h1={p:metrics([r for r in rr if r['policy']==p and r['available_ms']<s['midpoint']],s['midpoint'])for p in codes};eligible=[p for p,m in h1.items()if m['n']>=60 and m['coverage']>=.95];selection[ch]=dict(winner=max(eligible,key=lambda p:h1[p]['netR'])if eligible else None,raw_max=max(codes,key=lambda p:h1[p]['netR']),H1=h1)
 save(out/'SELECTION_FROZEN.json',dict(selection=selection,selection_only_H1=True,code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
 for ch,s in st.items():
  for p in(O if ch=='OLEG'else C):
   for period in['H1','H2','LAST40','FULL']:
    rr=[r for r in a if r['channel']==ch and r['policy']==p and(period=='FULL'or period=='H1'and r['available_ms']<s['midpoint']or period=='H2'and r['available_ms']>=s['midpoint']or period=='LAST40'and r['available_ms']>=s['last40'])];bound=s['midpoint']if period=='H1'else None;table.append(dict(channel=ch,policy=p,period=period,**metrics(rr,bound),**paired(rr,cm,bound)))
 for per in['H2','LAST40']:
  rr=[r for r in table if r['period']==per];assert len(rr)==140
  for r,q in zip(rr,bh([r['p']for r in rr])):r['BH_q_family140']=float(q)
 candidates=[]
 for ch,s in selection.items():
  w=s['winner'];rr=[r for r in table if r['channel']==ch and r['policy']==w and r['period']in['H1','H2','LAST40']]
  ok=len(rr)==3
  for r in rr:
   ok=bool(ok and r['n']>=60 and r['coverage']>=.95 and r['netR']>0 and(r['PF']or 0)>=1.3 and r['netR_adverse']>0 and(r['top3_share']or 1)<=.5 and r['funding_unknown_n']<=.05*r['n'])
   if r['period']!='H1':ok=bool(ok and r['excessR']>0 and r.get('BH_q_family140',1)<=.1)
  if ok:candidates.append(dict(id=ch+'_'+w,channel=ch,policy=w,enabled=False,status='PROMISING_REQUIRES_INDEPENDENT_REVIEW',author_identity_verified=ch=='OLEG'))
 save(out/'TABLES_ALL140.json',table);save(out/'variants.json',candidates)
 risk=[]
 for k in sorted(set(r['risk_signature_pct']for r in a if r['channel']=='OLEG'and r['risk_signature_pct']is not None)):
  for p in O:risk.append(dict(risk_signature_pct=k,policy=p,**metrics([r for r in a if r['channel']=='OLEG'and r['policy']==p and r['risk_signature_pct']==k])))
 save(out/'OLEG_RISK_SIGNATURES.json',risk);save(out/'CLAIM_RECONCILIATION_SUMMARY.json',{ch:dict(claims_in_source=st[ch]['claims'],linked_market_claims=sum(r['channel']==ch for r in claims),statuses=dict(collections.Counter(r['status']for r in claims if r['channel']==ch)),unlinked_in_source=st[ch]['unlinked_claims'])for ch in st})
 # Compare archived13 fills without treating emergency initial_stop as financial risk.
 plans=load(I/'PLANS.json.gz');op=[s for s in plans if s['channel']=='OLEG'];live=load(I/'LIVE13.json');comparison=[]
 for n,r in enumerate(live):
  t=int(dt.datetime.fromisoformat(r['open']).replace(tzinfo=dt.timezone.utc).timestamp()*1000);sy=r['coin']+'USDT';side=1 if r['side']=='long'else-1;matches=[s for s in op if s['symbol']==sy and(1 if s['side']=='LONG'else-1)==side and 0<=t-s['pub']<=12*H];causal=[s for s in matches if s['available_ms']<=t];s=max(causal or matches,key=lambda s:s['pub'])if matches else None;model=next((x for x in a if s and x['post_key']==s['post_key']and x['policy']=='O0'),None);comparison.append(dict(index=n,symbol=sy,live_entry_ms=t,live_entry=r['entry'],live_exit_reason=r['exit_reason'],emergency_initial_stop=r['initial_stop'],author_signal=s['post_key']if s else None,match_status='CAUSAL_CANDIDATE_12H'if causal else'LAST_EDIT_AFTER_LIVE_ENTRY'if matches else'NO_MATCHING_PARSED_SIGNAL',model_status=model['status']if model else None,model_entry=model.get('entry')if model else None,model_exit_ms=model.get('exit_ms')if model else None,model_netR=model.get('net_R')if model else None,live_close_ms=int(dt.datetime.fromisoformat(r['close']).replace(tzinfo=dt.timezone.utc).timestamp()*1000),live_last_exit_price=r['exits'][-1]['price']if r['exits']else None,live_recorded_exit_fraction_sum=sum(e['frac']for e in r['exits']),entry_difference_bps=(model['entry']/r['entry']-1)*10000 if model and model.get('entry')else None,exact_live_replay_proven=False,blockers=['historical runtime reversal/settings and ingest timestamps absent','position_size and complete fill allocation absent','Binance proxy vs Bybit','initial_stop emergency not financial1R']))
 save(out/'OLEG_LIVE13_COMPARISON.json',comparison);save(out/'CHECKPOINT.json',dict(status='COMPLETE_WITH_RECORDED_LIMITATIONS',posts=sum(r['posts']for r in st.values()),sources=len(st),actual_rows=len(a),control_rows=len(c),claims_checked=len(claims),paper_candidates=len(candidates),oleg_answer='YES_PROMISING_NOT_PROVEN_LIVE'if any(r['channel']=='OLEG'for r in candidates)else'NO_PROFITABILITY_PROVEN',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),live_changes=0))
 lines=['# Олег: полная история и19 закрытых каналов','','## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','',f'Обработано {sum(r["posts"]for r in st.values())} постов20 источников. Реальных модельных строк {len(a)}, контрольных {len(c)}; это не число сделок. Кандидатов после H1/H2/last40 и BH140: {len(candidates)}. Все результаты и причины отказов сохранены.','', '**По сигналам Олега можно зарабатывать — '+('ДА, предварительно: '+', '.join(r['policy']for r in candidates if r['channel']=='OLEG')if any(r['channel']=='OLEG'for r in candidates)else'НЕТ: доказательство прибыльности не получено')+'.**','', 'O0 — приближение опубликованного OLEG-кода, не доказанная точная копия исторического LIVE. OLEG_MAIN с4% стопом — другой источник. Сверка13 сохранена отдельно; аварийный initial_stop не использован как1R. Без количеств/полных fills нельзя пересчитать известные−3.7USDT.','', 'История постов начинается раньше полноценных карточек. Учитывается last snapshot в момент edit_date, не подставляется будущее редактирование в исходную публикацию. В19 архивах история редакций/идентичность автора неизвестны. Результат — механическая модель потока, не доказательство навыка отдельного человека.','', '## Каналы и фактическое покрытие','','|Источник|Постов|Кандидатов|Структурных|Текстовых|С событиями|','|---|---:|---:|---:|---:|---:|']
 for ch,s in st.items():lines.append(f'|{ch}|{s["posts"]}|{s["signals"]}|{s["structured"]}|{s["text"]}|{s["signals_with_events"]}|')
 lines+=['','## Олег: все политики','','|Политика|Период|n|WR %|PF|netR|DD R|Отказы|Нет входа|GAP|q BH140|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in table:
  if r['channel']!='OLEG':continue
  def f(k):return f'{r[k]:.4f}'if r.get(k)is not None else'—'
  lines.append('|'+ '|'.join([r['policy'],r['period'],str(r['n']),f('WR'),f('PF'),f('netR'),f('maxDD_R'),str(r['rejected']),str(r['nofill']),str(r['gaps']),f('BH_q_family140')])+'|')
 lines+=['','##19 каналов: замороженные H1-выборы','','|Источник|H1 выбор|Период|n|WR %|PF|netR|excessR|q|','|---|---|---|---:|---:|---:|---:|---:|---:|']
 for ch,s in selection.items():
  if ch=='OLEG':continue
  p=s['winner']or s['raw_max']
  for r in table:
   if r['channel']!=ch or r['policy']!=p:continue
   def f(k):return f'{r[k]:.4f}'if r.get(k)is not None else'—'
   lines.append('|'+ '|'.join([ch,p+(' (RAW ONLY)'if s['winner']is None else''),r['period'],str(r['n']),f('WR'),f('PF'),f('netR'),f('excessR'),f('BH_q_family140')])+'|')
 lines+=['','## Ограничения и независимая проверка','','TABLES_ALL140.json содержит ВСЕ политики, включая отрицательные и неприменимые; SELECTION_FROZEN.json выбирает только по H1. Last40 перекрывает H2. Публикации/правила ранее могли быть просмотрены — не новый untouched OOS. Открытые позиции не закрывались искусственно по ASOF. Финансовые R нормированы по исходному SL, не по плечу.','', 'Издержки: taker0.055% за каждое изменение,5bps market/SL/time slippage; limit/TP без дополнительного slip. Funding Binance по реальным доступным ставкам; неизвестное0±.01%/8h и двойные комиссии/slippage в adverse. Funding не выдаётся за подтверждённый ноль.','', 'Claims сравниваются с предшествующим закрытым1m market envelope на время сообщения. ПроцентROI с неизвестными плечом/долями/капиталом не равен движению цены; превышение unlevered envelope не доказывает ложь. TP-hit не считался командой закрытия. Части/доборы без веса — UNRESOLVED, не придумывались.','', 'Риск-подписи Олега: OLEG_RISK_SIGNATURES.json, никаких порогов по ним не подбиралось. Графики/изображения в текстовых выгрузках не восстановлены; отсутствие распознанной сделки не означает отсутствие сделки у автора. Все классификации/пропуски — в inputs/DATA_INVENTORY и CLASSIFICATION.','', 'Для Claude: проверить source hashes, edited-time causality, reply linkage, numeric levels (включая проценты), совпадение OLEG vsOLEG_MAIN, 13live reconciliation limitations, H1exit-before-split guard, контроль без будущих авторских действий, BH140, реальные расходы и gaps. Сырые тексты остаются в приватном источнике, публично их нет.','', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
 (out/'OTCHET_DLYA_CLAUDE_CODEX_OLEG_I_PRIVATE_20261118.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
