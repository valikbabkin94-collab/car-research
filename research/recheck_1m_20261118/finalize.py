import json,gzip,os,subprocess,collections
from pathlib import Path
import numpy as np
from market import save,H,DAY
B=Path('research/recheck_1m_20261118');START=1762930800000;END=1794466800000;CUT=1778698800000;TAIL=START+int(.6*(END-START));SEED=20261118

def records(name):
 out=[]
 for p in Path('results').glob('dump_shard*/'+name):
  with gzip.open(p,'rt')as f:out.extend(json.loads(s)for s in f)
 return out

def metrics(rows):
 good=sorted([r for r in rows if r['status']=='CLOSED'],key=lambda r:r['exit_ms']);v=np.array([r['R']for r in good]);loss=-v[v<0].sum();eq=np.cumsum(v);net=v.sum();base=sum(r['original_R']for r in good)
 return dict(n_original=len(rows),n=len(good),coverage=len(good)/max(1,len(rows)),netR=float(net),meanR=float(v.mean())if len(v)else None,PF=float(v[v>0].sum()/loss)if loss else None,WR=float(100*(v>0).mean())if len(v)else None,maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(v)else None,parent_hourly_R_on_same_rows=float(base),delta_vs_same_rows=float(net-base),top3_share=float(np.sort(v)[-3:].sum()/net)if net>0 else None,entry_minute_ambiguous=sum(r['entry_minute_TP_ambiguous']for r in good),new_BE_minute_ambiguous=sum(r['new_BE_same_minute_ambiguous']for r in good),simultaneous_SL_TP=sum(r['SL_TP_same_minute_ambiguous']for r in good),sensitivity_R=float(sum(r['sensitivity_entryTP_delayedBE_R']for r in good)),netR_with_known_funding=float(sum(r['R_with_known_funding']for r in good)),funding_unknown_n=sum(not r['funding_known']for r in good),netR_funding_adverse=float(sum(r['R_with_known_funding']-r['funding_unknown_stress_R']for r in good)),statuses=dict(collections.Counter(r['status']for r in rows)))

def paired(rows,cm):
 blocks={};vs=[];controlsum=0.;matchedactual=0.;filledpair=[];cnofill=0
 for r in rows:
  c=cm.get(r['id'])
  if r['status']!='CLOSED'or not c or c['status']not in['CLOSED','ORIGINAL_NOFILL']:continue
  d=r['R']-c['R'];vs.append(d);day=r['signal_ms']//DAY;blocks[day]=blocks.get(day,0.)+d;controlsum+=c['R'];matchedactual+=r['R'];cnofill+=c['status']=='ORIGINAL_NOFILL'
  if c['status']=='CLOSED':filledpair.append(d)
 p=1.
 if len(vs)>=30 and len(blocks)>=8:
  v=np.array(list(blocks.values()));rng=np.random.default_rng(SEED);p=(1+int(np.sum((rng.choice([-1,1],size=(9999,len(v)))@v)>=v.sum())))/10000
 return dict(paired_n=len(vs),paired_actual_R=matchedactual,paired_control_R=controlsum,excessR=float(sum(vs)),control_nofill=cnofill,common_filled_n=len(filledpair),common_filled_excessR=float(sum(filledpair)),p=p)

def family_bh(ps):
 ix=np.argsort(ps);q=np.ones(len(ps));v=1.
 for n in range(len(ix)-1,-1,-1):j=ix[n];v=min(v,ps[j]*len(ps)/(n+1));q[j]=v
 return q

def main():
 rows=records('ACTUAL_ROWS.jsonl.gz');controls=records('CONTROL_ROWS.jsonl.gz');assert len(rows)==1141 and len(set(r['id']for r in rows))==1141,'FROZEN_INPUT_COUNT_MISMATCH';cm={r['source_id']:r for r in controls};out=B/'final';out.mkdir(parents=True,exist_ok=True)
 # Selection artifact emitted BEFORE test summaries, no data-dependent parameter changes.
 table={};phase=lambda r:r['signal_ms']+80*H<CUT
 train={v:metrics([r for r in rows if phase(r)and(v=='RAW'or r['selected'])])for v in['RAW','TOP50']};eligible=[v for v,m in train.items()if m['n']>=30 and m['coverage']>=.95];winner=max(eligible,key=lambda v:train[v]['netR'])if eligible else None;raw=max(train,key=lambda v:train[v]['netR']);save(out/'SELECTION_FROZEN.json',dict(winner=winner,raw_max=raw,H1=train,original_logistic_refit=False,reason='No eligible candidate if minute data coverage<95%',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
 for part in['H1','H1_ALL','H2','LAST40','FULL']:
  table[part]={}
  for variant in['RAW','TOP50']:
   rr=[r for r in rows if(variant=='RAW'or r['selected'])and(part=='FULL'or part=='H1'and phase(r)or part=='H1_ALL'and r['signal_ms']<CUT or part=='H2'and r['signal_ms']>=CUT or part=='LAST40'and r['signal_ms']>=TAIL)];m=metrics(rr);m.update(paired(rr,cm));table[part][variant]=m
  if part in['H2','LAST40']:
   q=family_bh([table[part][v]['p']for v in['RAW','TOP50']]+[1.]*6)
   for v,x in zip(['RAW','TOP50'],q[:2]):table[part][v]['BH_q_family8']=float(x)
 save(out/'DUMP_METRICS.json',table);candidate=winner is not None
 for part in['H1','H2','LAST40']:
  m=table[part].get(winner,{})
  candidate=bool(candidate and m.get('n',0)>=30 and m.get('coverage',0)>=.95 and m.get('netR',-1)>0 and(m.get('PF')or 0)>=1.3 and m.get('netR_funding_adverse',-1)>0 and(m.get('top3_share')or 1)<=.5 and m.get('funding_unknown_n',1)==0)
 for part in['H2','LAST40']:
  m=table[part].get(winner,{});candidate=bool(candidate and m.get('excessR',0)>0 and m.get('BH_q_family8',1)<=.1)
 save(out/'variants.json',[dict(id='DUMP_BOUNCE_LONG_1M_'+winner,enabled=False,status='PROMISING_NOT_FRESH_OOS')]if candidate else[])
 save(out/'CHECKPOINT.json',dict(status='DUMP_MINUTE_COMPLETE_OTHER_PARTS_SOURCE_AUDITED',source_code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),original_closed=1141,minute_closed=table['FULL']['RAW']['n'],gaps=1141-table['FULL']['RAW']['n'],winner=winner,paper_candidate=candidate,code_only_execution_changed=True,live_changes=0))
 lines=['# Перепроверка отказов на1m','','## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','','Пересчитан порядок исполнения DUMP на фиксированных1141 исходных входах. Отсутствующие котировки и недостижимая исходная цена сохранены как DATA_GAP. Это не повод заменять сделки новыми входами. Binance1m является прокси другого рынка относительно исходных Bybit1h.','',f'Замороженный H1-выбор: {winner}; сырой максимум: {raw}. Допуск в бумажную фабрику: {candidate}. Исходная модель TOP50 не переобучалась.','']
 for part,tab in table.items():
  lines+=['## '+part,'','|Вариант|Исходных|1m сделок|Покрытие|WR %|PF|netR|Тот же набор1h R|Разница R|DD R|excessR|q BH8|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
  for v,m in tab.items():
   def f(k):return f'{m[k]:.4f}'if m.get(k)is not None else'—'
   lines.append('|'+ '|'.join([v,str(m['n_original']),str(m['n']),f'{m["coverage"]:.1%}',f('WR'),f('PF'),f('netR'),f('parent_hourly_R_on_same_rows'),f('delta_vs_same_rows'),f('maxDD_R'),f('excessR'),f('BH_q_family8')])+'|')
  lines.append('')
 lines+=['## Остальные части','','A5/B10 уже проверялись на1m в исходном исследовании; повторная симуляция не нужна. Сохранены исходные протокол/метрики, отрицательный H1 не исправлялся подбором. Дополнительные last40/новый случайный контроль требуют индивидуальных журналов, которых нет в опубликованных исходниках.','', 'IDEAS_A/B/C: опубликованы агрегаты10882/5044/1648 сигналов, но точный исходный журнал и скрипты описаны манифестом как файлы Honor. Более поздние E2/E3 в car-research — другие выборки332/505 сделок, не подмена исходных. Без точных входов/ATR/исходных контролей этот пересчёт DATA_BLOCKED.','', 'NIGHT: фиксирован пропуск при низкой волатильности И низком ATR. PASSPORT_DATASET и три MANAGER_TRADES описаны как файлы Honor; таблица выбранных правил не заменяет индивидуальные строки. До выгрузки сохранённого датасета — DATA_BLOCKED.','', 'Список недостающих полей: DATA_NEEDED.md; источник и SHA: SOURCE_AUDIT.json. Отсутствующие тесты получают p=1 в семье BH8, не скрываются из поправки.','', '## Пределы минутной проверки','','Порядок high/low внутри самой минуты остаётся неизвестным. Первичный расчёт консервативен; число таких случаев и диагностическая альтернатива sensitivity_R есть в DUMP_METRICS.json. Альтернативу не использовали для выбора. Funding показан отдельно, неизвестные выплаты не исключают сделку. FULL не равен H1+H2 из-за purge; LAST40 перекрывает H2. Известная история не является новым независимым OOS.','', 'Все отрицательные/неисполненные/недостающие строки, события и source errors сохранены в dump_shard0..3. Код и протокол зафиксированы до запуска. Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0.']
 (out/'OTCHET_DLYA_CLAUDE_CODEX_RECHECK_1M_20261118.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
