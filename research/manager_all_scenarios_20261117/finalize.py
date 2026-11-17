"""Integrity checks and readable summaries of existing outputs; never replay or refit."""
from pathlib import Path
import json,gzip,hashlib,csv,collections,statistics,subprocess
import numpy as np
P=Path(__file__).resolve().parent;R=P/'RESULTS'
def read(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def fmt(v):return '—'if v is None else f'{v:.4f}'if isinstance(v,float)else str(v)
a=read(P/'ENTRIES.json.gz');by={e['key']:e for e in a};features=read(R/'ENTRY_FEATURES.json.gz');gate=read(R/'EDGE_TRAIN_FROZEN.json');selection=read(R/'SELECTION_FROZEN.json');trades=read(R/'MANAGER_TRADES.json.gz');controls=read(R/'MANAGER_RANDOM_CONTROL.json.gz');tables=read(R/'MANAGER_TABLES.json');edge=read(R/'EDGE_TABLES.json');splits=read(R/'SPLITS.json');params=read(R/'PARAMS.json');source=read(R/'SOURCE_CHECKPOINT.json');checkpoint=read(P/'CHECKPOINT.json');variants=read(P/'variants.json')
assert len(a)==len(features)==9935 and set(by)=={r['key']for r in features}
for name,digest in read(P/'PRE_PNL_HASHES.json').items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,('FROZEN_HASH',name)
assert selection['before_H2_manager_execution']is True
assert len(trades)==len(controls)
assert len({(r['key'],r['manager'])for r in trades})==len(trades)
null_entries={r['key']:r for r in read(R/'CONTROL0_ENTRIES.json.gz')}
for rows,index in [(trades,by),(controls,null_entries)]:
 for r in rows:
  e=index[r['key']];assert r['entry_ms']==e['entry_ms']and r['entry']==e['entry'];assert r['side']==e['side']*(-1 if r['mirror']else 1)
  if r.get('net_R')is not None:
   assert r['status']=='CLOSED'and r['exit_ms']>=r['entry_ms']and r['exit_ms']<=params['asof']
   assert abs(sum(x['fraction']for x in r['events'])-1)<1e-8
   assert abs(r['net_R']-(r['price_R']+r['funding_R']))<1e-8
   assert abs(r['price_R']-(r['gross_R']-r['execution_cost_R']))<1e-8
for r in tables:assert 0<=r['BH_q']<=1
npz_n=0
for f in (R/'CONTROL200').glob('*.npz'):
 meta=read(f.with_suffix('.json'));assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256']
 with np.load(f,allow_pickle=False)as z:
  n=len(z['keys']);assert z['times'].shape==(n,200)and z['returns'].shape==(n,200,3)and z['mfe_R'].shape==(n,200,4);npz_n+=n
assert npz_n==len(a)
coverage=[]
for sc in sorted(splits):
 es=[e for e in a if e['scenario']==sc];fs=[r for r in features if r['scenario']==sc];closed=[r for r in trades if r['scenario']==sc and r.get('net_R')is not None];coverage.append(dict(scenario=sc,input_entries=len(es),compatible_binance_entry=sum(r['compatible']for r in fs),full_actual_72h=sum(all(x is not None for x in r['mfe_R'])for r in fs),full_1_4_24h_returns=sum(all(x is not None for x in r['returns'])for r in fs),gate=gate['decisions'][sc],manager_rows=sum(r['scenario']==sc for r in trades),manager_closed=len(closed),manager_rejections=dict(collections.Counter(r.get('reason',r['status'])for r in trades if r['scenario']==sc and r.get('net_R')is None))))
save(R/'DATA_COVERAGE_BY_SCENARIO.json',coverage)
legacy=[]
for sc in splits:
 for per in ['H1','H2','LAST40','ALL']:
  s=splits[sc];es=[e for e in a if e['scenario']==sc and (per=='ALL'or e['entry_ms']+72*3600000<=s['half']if per=='H1'else e['entry_ms']>=s['half']if per=='H2'else e['entry_ms']>=s['tail']if per=='LAST40'else True)];v=[e['native_net_R']for e in es if e.get('native_net_R')is not None];gain=sum(x for x in v if x>0);loss=-sum(x for x in v if x<0);legacy.append(dict(scenario=sc,period=per,manager='X0',n=len(v),WR=100*sum(x>0 for x in v)/len(v)if v else None,PF=gain/loss if loss else None,netR=sum(v),maxDD_R=None,note='Immutable native R, original fees/funding/venue/risk; no identical 1m replay, no train selection; DD not inferred from missing native position ledger.'))
save(R/'X0_LEGACY_TABLES.json',legacy)
for file,data in [('MANAGER_TABLES.csv',tables),('EDGE_TABLES.csv',edge),('DATA_COVERAGE_BY_SCENARIO.csv',coverage),('X0_LEGACY_TABLES.csv',legacy)]:
 keys=sorted(set(k for r in data for k in r));f=(R/file).open('w',newline='');w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(list,dict))else v for k,v in r.items()}for r in data);f.close()
verification=dict(status='PASS',code_sha=params['code_sha'],entries=len(a),feature_rows=len(features),control_replicates=200,control200_covered_entries=npz_n,manager_rows=len(trades),random_manager_rows=len(controls),all_frozen_hashes_verified=True,entries_and_sides_unchanged_except_declared_mirror=True,exit_fraction_and_fee_funding_accounting=True,train_selection_written_before_H2=True,source_jobs_done=source['done'],source_jobs_total=source['total'],source_job_statuses=dict(collections.Counter(r['status']for r in source['receipts'])),limitations='Internal accounting tests only, not independent method review. X0 reference not a comparable new replay. All underlying price/archival biases remain.')
save(R/'VERIFICATION.json',verification)
report=P/'OTCHET_DLYA_CLAUDE_CODEX_MANAGER_ALL_SCENARIOS_20261117.md';s=report.read_text();s+='\n## Покрытие и проверка целостности\n\n'+f'Все {len(a)} входов имеют feature-строку и200 исходов контроля (в том числе NaN при отсутствии истории). Число фактически исполнимых наблюдений не равно размеру исходного корпуса. Обработано {source["done"]}/{source["total"]} окон источников: {verification["source_job_statuses"]}. Это не число полных торговых историй.\n\n'
s+='|Сценарий|Входов|Цена совпала с минутой Binance|Полных72ч|Вердикт TRAIN|\n|---|---:|---:|---:|---|\n'
for r in coverage:s+='|'+r['scenario']+'|'+str(r['input_entries'])+'|'+str(r['compatible_binance_entry'])+'|'+str(r['full_actual_72h'])+'|'+r['gate']+'|\n'
s+='\nX0: сводка неизменённых старых результатов — RESULTS/X0_LEGACY_TABLES.json/csv. Нативные R нельзя молча выдавать за одинаковую новую комиссию/1m-execution. Поэтому X0 справочный, а основной выбор — среди новых воспроизводимых выходов. Нулевой n слота X0 в основной матрице означает отсутствие такого нового replay, а не нулевую историческую прибыль.\n\nВсе подробные таблицы дополнительно в CSV. Регистр сырой совместимости, пропусков,200 контролей и exit-событий сохранён. Большие CONTROL200 npz содержат float32 исходы и целые времена; NaN обозначает пропуск и никогда не заменён выдуманной ценой. SHA каждого файла проверен.\n\nВ первой технической версии обнаружен дефект ленивых groupby-итераторов, её пустые результаты непригодны. Итог относится только к execute_v1_1.py; grid/входы сохранены, корректировки до годного PnL и первоначальный ASOF описаны в TECHNICAL_FIX_V1_1.md.\n\nОграничения: это уже известные ретроспективные журналы исполнений; fixed fills/старые портфельные ограничения и недостаток receipt могут ограничить воспроизводимость. G3 — no-quality15m replay, S2/S3 — ограниченные proxy исследования, а не полная живая история исходных стратегий. Для confluence подтверждающий fill обязан уже существовать к входу, иначе из-за отбора исполненного журнала возник бы look-ahead. Дневные блоки не гарантируют устранение всех перекрытий72ч; независимая проверка более длинных блоков обязательна перед повышением статуса. Неизвестный funding0±.01%/8ч — допущение, не стресс всех экстремальных пампов.\n'
report.write_text(s)
(P/'HANDOFF_CLAUDE_RU.md').write_text('''# Независимая проверка manager-all-scenarios

Ветка research/manager-all-scenarios, каталог research/manager_all_scenarios_20261117. Исходная сетка/входы зафиксированы ec6067a ДО нового PnL. run.py/engine.py версии1 сохранены; итоговые execute_v1_1.py/engine_v1_1.py исправляют обработку групп, pub-time ATR текущего MANAGER и доступность подтверждающего fill. См. TECHNICAL_FIX_V1_1.md. Первый run44087096459 — источник кэша и ASOF, его пустые группы не финансовый результат. Итоговый code_sha в CHECKPOINT/PARAMS. PRE_PNL_HASHES сохраняет обе версии и immutable inputs.

Сначала RESULTS/VERIFICATION.json, DATA_COVERAGE_BY_SCENARIO и отчёт. Далее:

1. Независимо проверить 9935 фиксированных входов и исключения. G3=NO_QUALITY15m, R1=flat/sign-flip из ребалансов. E3 parent/old-fixed flip разделены. S2/S3 aliases DELIST_SHORT/FUND_SQUEEZE не считать независимыми сценариями. Telegram edited, original author fill неизвестен.
2. Сверить SOURCE_MANIFEST с immutable публичными исходниками и воспроизвести нормализацию collect_inputs.py/prepare_inputs.py в отдельной копии. Сам public input не изменять. Исходные суммы и IDs не публиковались повторно.
3. Сопоставить AST-фрагменты vendor/pure_manager.py с private source commit из PROVENANCE: ATR14 закрытых часов,1.5ATR,50/25/25,BE ровно entry,24ч. X2 явно research bypass выключенного manager reversal, не LIVE изменение. В X1/2 ATR на pub, в X4/5 на entry; frozen fill не меняется.
4. Проверить scipy forward extrema против прямых окон, непрерывность цен и несовместимость saved-entry с Binance1m. Не считать DATA_GAP проигрышем или доказанным ШУМ. Никакого восстановления времени внутри нативной5m/15m свечи не выдумывать.
5. Убедиться: gate только H1,purge72ч,200±7d controls без пересэмплирования missing, train winner сохранён ДО H2. Не оптимизировать по H2. MFE/MAE R1% и PnL R actualinitialSL не смешивать.
6. Проверить все TP/SL/BE/trail/event fractions, комиссии maker .02% только limit, taker .055%,slip5bps; свеча входа без TP, неоднозначность SL-first. Дневные блоки стрессовать недельными/неперекрывающимися исходами в отдельном заранее зарегистрированном аудите, не подбирать лучший результат.
7. Проверить реальные funding coverage/cash и unknown0±.01%/8ч. Экстремальные funding могут выходить за этот стресс.
8. X0 только исходный справочный netR; без полного старого кода/исполнения не считать сопоставимым новым replay и не включать в выбор победителя. R1 динамическое изменение позиции особенно требует отдельного исходного ledger.
9. Конфлюэнс: только независимые lineage, публикация в прошлом и уже произошедший подтверждающий fill; симметричные±2ч diagnostic only, future нельзя превратить в доступный сигнал.
10. Перепроверить BH по фиксированной полной семье, включая неисполненные слоты p1 и отсутствующие10 сценариев; последние40% пересекают H2. variants.json — только PROMISING и enabled=false, ничего не запускается автоматически. Если кандидатов0 — не смягчать пороги задним числом.

DATA_NEEDED.md: точный минимальный экспорт недостающих сценариев, без имен/IDs/ключей/сумм. Desktop Commander/Telegram sessions/order APIs не использованы. Никаких main-merge или установки в LIVE. Следующий этап — независимый аудит, а не разрешение реальной торговли.
''')
checkpoint.update(verification='RESULTS/VERIFICATION.json',actual_feature_rows=len(features),all_frozen_hashes_verified=True,source_job_statuses=verification['source_job_statuses'],X0_status='REFERENCE_ONLY_NOT_IDENTICALLY_REPLAYED',first_technical_run='44087096459',engine_version='v1.1',cutoff_preserved_from_first_run=True,independent_review_required=True);save(P/'CHECKPOINT.json',checkpoint)
save(P/'ARTIFACT_HASHES.json',{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(P.rglob('*'))if f.is_file()and f.suffix!='.pyc'and f.name!='ARTIFACT_HASHES.json'})
print(json.dumps(dict(status='PASS',code_sha=params['code_sha'],edge_counts=checkpoint['edge_verdicts'],manager_rows=len(trades),candidates=len(variants)),ensure_ascii=False))
