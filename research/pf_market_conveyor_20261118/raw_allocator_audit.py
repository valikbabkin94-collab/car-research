"""Additional RAW-all2113 causal allocator on saved paths only. No quotes or simulation."""
import research as r
import json,gzip,random,os,collections
import numpy as np
from pathlib import Path
LAB=Path(__file__).parent;OUT=LAB/'raw_allocator_audit';OUT.mkdir(exist_ok=True)
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def allocate(rows):
 weeks=range(r.monday(r.START),r.END,7*r.D)
 decisions={w:r.choose(rows,w) if w-28*r.D>=r.START else None for w in weeks}
 return [dict(x,variant=n) for n,rs in rows.items() for x in rs if decisions[r.monday(x['signal_ms'])]==n],decisions
raw=json.loads(gzip.decompress((LAB/'results/ALL_ENTRY_MODE_TRADES.json.gz').read_bytes()));assert all(len(v)==2113 for v in raw.values())
alltests=[];tables=[];randoms={};selections={};checks={};decisions_out={};rng=random.Random(20261118)
for cohort,rows in [('RAW2113',raw),('MODEL_SELECTED_CONDITIONAL',{n:[x for x in xs if x['selected']] for n,xs in raw.items()})]:
 train={n:r.metrics(rs,r.START,r.HALF) for n,rs in rows.items()};best=sorted(train,key=lambda n:(-train[n]['netR'],n))[0];selections[cohort]=dict(best_static=best,H1=train,selection_only_H1=True)
 selected,decisions=allocate(rows);decisions_out[cohort]=[dict(monday_ms=w,winner=n,warmup=w-28*r.D<r.START) for w,n in decisions.items()]
 if cohort=='MODEL_SELECTED_CONDITIONAL':assert best==json.loads((LAB/'results/SELECTION_FROZEN.json').read_text())['H1_best_static']
 every=[dict(x,net_R=x.get('net_R',0)/len(rows),net_R_adverse=x.get('net_R_adverse',0)/len(rows)) for rs in rows.values() for x in rs]
 for period,a,b in [('H1',r.START,r.HALF),('H2',r.HALF,r.END),('LAST40',r.TAIL,r.END),('FULL',r.START,r.END)]:
  for name,rs in [('CONVEYOR',selected),('PF_BASE',rows['PF_BASE']),('H1_STATIC_'+best,rows[best]),('ALL_EQUAL',every)]:tables.append(dict(cohort=cohort,period=period,strategy=name,**r.metrics(rs,a,b)))
  vals=[];random_daily=collections.defaultdict(float);names=sorted(rows)
  for rep in range(1000):
   picks={w:rng.choice(names) if w-28*r.D>=r.START else None for w in decisions}
   rs=[x for n,xs in rows.items() for x in xs if picks[r.monday(x['signal_ms'])]==n]
   vals.append(r.metrics(rs,a,b)['netR'])
   for d,v in r.daily(rs,a,b).items():random_daily[d]+=v/1000
  randoms[cohort+':'+period]=dict(n=1000,mean=float(np.mean(vals)),median=float(np.median(vals)),p05=float(np.quantile(vals,.05)),p95=float(np.quantile(vals,.95)),conveyor_percentile=sum(v<=r.metrics(selected,a,b)['netR'] for v in vals)/1000)
  if period in ['H2','LAST40']:
   cd=r.daily(selected,a,b)
   for name,other in [('PF_BASE',r.daily(rows['PF_BASE'],a,b)),('H1_STATIC',r.daily(rows[best],a,b)),('RANDOM1000_MEAN',random_daily)]:alltests.append(dict(cohort=cohort,period=period,comparison=name,excessR=sum(cd.values())-sum(other.values()),p=r.sign_p(cd,other)))
  save('RUNNING.json',dict(cohort=cohort,period=period,market_simulations=0))
 save('SELECTIONS_H1.json',selections)
 checks[cohort]=all(x['netR']>0 and x['netR_adverse']>0 and x['unknown_funding_n']==0 for x in tables if x['cohort']==cohort and x['strategy']=='CONVEYOR' and x['period'] in ['H2','LAST40'])
order=sorted(range(len(alltests)),key=lambda i:alltests[i]['p']);q=1.
for rank,i in reversed(list(enumerate(order,1))):q=min(q,alltests[i]['p']*len(alltests)/rank);alltests[i]['BH_q_family12']=q
save('TABLES.json',tables);save('RANDOM1000.json',randoms);save('CONTROLS_BH12.json',alltests);save('WEEKLY_DECISIONS.json',decisions_out)
answers={cohort:checks[cohort] and all(x['excessR']>0 and x['BH_q_family12']<=.1 for x in alltests if x['cohort']==cohort) for cohort in checks}
save('CHECKPOINT.json',dict(status='COMPLETE_NO_NEW_MARKET_SIMULATIONS',answers=answers,code_sha=os.environ['GITHUB_SHA'],source_rows_per_variant=2113,variants=list(raw),controls=1000,tests_family=12,warmup='28 complete source calendar days for allocator and random weekly comparator',model_selection_causality='UNKNOWN: saved model cut later than H1; conditional model subset not proof that model existed then',data_limits='unknown funding modeled0 and stress; no historical ranks for TOP100/WIDE/R10; entry replay5m not1m',live_changes=0))
lines=['# Итог B: конвейер по всем 2113 сигналам и условной модельной подвыборке','','## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','','**Конвейер лучше статичного и случайного на H2 и last40 — '+('ДА' if answers['RAW2113'] else 'НЕТ')+'.**','', 'Это аудит распределения риска по уже рассчитанным сделкам: новых ценовых расчётов нет. RAW использует все2113 исходных сигнала каждого из5 режимов. MODEL_SELECTED — условные1041 из прежнего сохранённого selected-mask; причинная доступность обученной модели в прошлом не доказана. Весь исторический результат модели как торговой системы не валидирован. После обнаружения этого ограничения добавлена заранее зафиксированная проверка RAW, прежние результаты сохранены.','', 'Для выбора недели необходимы28 полных дней исходной истории: до этого cash; у случайного недельного контроля тот же warmup. Статичные сравнения оставлены с начала соответствующего периода, поскольку не нуждаются в lookback. Сделки доступны рейтингу только после закрытия и выбираются на следующую неделю по дате сигнала. Нет закрытия позиции по смене недели.','', '|Когорта|Стратегия|Период|n|netR|PF|DD R|Неизв. funding|','|---|---|---|---:|---:|---:|---:|---:|']
for x in tables:lines.append(f"|{x['cohort']}|{x['strategy']}|{x['period']}|{x['n']}|{x['netR']:.3f}|{x['PF'] if x['PF'] is not None else 'н/д'}|{x['maxDD_R']:.3f}|{x['unknown_funding_n']}|")
lines+=['', 'SELECTIONS_H1 содержит полные H1-scores без выбора по H2. CONTROLS_BH12 — все12 сравнений, RANDOM1000 — все распределения, WEEKLY_DECISIONS — решения с warmup. Никакие положительные результаты не объявляются устойчивыми при неизвестном funding. См. исходный results/DATA_NEEDED.json: полных исторических TOP100/WIDE/R10/других источников не выдумывали.','', '5m-справка трёх входов сохранена в ../results/ENTRY_MODE_TABLES.json и ../results/OTCHET_RU.md. Она не равна минутному forwardpaper исполнению. R0.0581 исторического исследования, sumR не portfolio%. Maker fee-view не доказывает касание/очередь maker. Last40 пересекается сH2.','', 'Контроль недельного выбора — не случайные времена входа на рынке и не доказательство навыка PF-сигналов. Этот тест проверяет только пользу правила переключения. Отдельного random-time/BH теста рыночного преимущества новых entry modes здесь нет; бумажное включение A не трактуется как положительная статистическая рекомендация.','', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0.']
(OUT/'OTCHET_RU.md').write_text('\n'.join(lines)+'\n')
