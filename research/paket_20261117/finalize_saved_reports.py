"""Final checkpoint and exact last40 arithmetic on saved outcomes. No market IO/replay/selection."""
import os,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from lab.common import *
from lab.runner import report
B=Path('research/paket_20261117');out=Path(os.environ['LAB_OUTPUT']);out.mkdir(parents=True,exist_ok=True);w=B/'part3_complete';records=load(w/'ALL_SAVED_ACTUAL_OUTCOMES.json.gz');entries={e['key']:e for e in load(w/'INPUTS.json')}
for e in load(B/'part3_source_completion'/'NEW_EVENTS.json'):entries[e['key']]=e
lo=min(e['entry_ms']for e in entries.values());hi=max(e['entry_ms']for e in entries.values())+M;cut=lo+int(.6*(hi-lo));selection=load(w/'ORIGINAL_SELECTION_UNCHANGED.json');winner=selection['winner'];zz=np.load(w/'H2_CONTROL200_COMBINED.npz',allow_pickle=False);controls_map={k.decode():r for k,r in zip(zz['keys'],zz['netR'])};selected=[r for r in records if r['variant']==winner and r['period']=='H2'and entries[r['key']]['entry_ms']>=cut];rs=[np.array(r['outcome'],float)for r in selected];ns=[controls_map[r['key']]for r in selected];p=paired_test(rs,ns);train_overlap=sum(r['variant']==winner and r['period']=='H1'and entries[r['key']]['entry_ms']>=cut for r in records);exact=dict(variant=winner,period='LAST40_EXACT_COMPLETED_CORPUS_H2_ONLY',**metrics(rs),excessR=p['excessR'],p=p['p'],BH_q=min(1.,p['p']*4),control_coverage=p['coverage'],calendar_start_ms=lo,calendar_end_ms=hi,last40_cut_ms=cut,frozen_original_cut_ms=selection['split'][2],original_H1_end_ms=selection['split'][1],train_overlap_excluded=train_overlap,selection_unchanged=True,prices_not_replayed=True);write(out/'EXACT_LAST40_COMPLETED_CORPUS.json',finite(exact))
write(out/'SOURCE_INPUT_COUNTS.json',dict(all_input_policy_rows=len(entries),unique_key_rows=len(entries),explanation='Rows are policy-specific potential entries, not a count of closed trades. Multiple timing/side policies may derive from the same event.',original_inputs=22440,current_daily_inputs=len(load(B/'part3_source_completion'/'NEW_EVENTS.json')),resource_shards={str(i):load(B/f'part3_resource_shard{i}'/'CHECKPOINT.json')['new_events']for i in range(4)}))
refs=dict(package_initial_code='2690eefd603c90d7351224f2df4796b4d3a1b752',PF_H2_code='47df7923e130a1fa08683f34bceea6381fb522cd',daily_completion_code='9bc2581f8764cfafc626756ac352bf5cbd294f98',resource_completion_code='804d96aaabe5a0cba60d29d5339a5279cabfc737',manager_result_commit='e4412b2cfdccbb6f710f7b32da2f1db6fc360b32',manager_initial_code='61130fcdae2d2ea944a4c5a3af406fc1d30e362c',manager_resume_code='5b290e403d1a185a1518eb48695d949dc4f86773')
manager=json.loads(fetch_github('v2/coverage_fix/ALL_TABLES.json',refs['manager_result_commit']));ledger=[]
def add(name,folder,verdict,reason,table='TABLES.json'):
 rows=load(B/folder/table)if(B/folder/table).exists()else[];ledger.append(dict(name=name,verdict=verdict,reason=reason,artifact=str(B/folder),rows=[r for r in rows if r.get('period')!='H1']))
add('MANAGER_V2','../manager_v2_not_in_package','INCONCLUSIVE_NO_REGISTERED_PASS','12 cohorts plus PF: no frozen winner passed all independent registered criteria; see other research branch.');ledger[-1]['artifact']='https://github.com/valikbabkin94-collab/car-research/tree/'+refs['manager_result_commit']+'/v2/coverage_fix';ledger[-1]['rows']=[r for r in manager if r['period']!='H1']
add('OLEG_FIX','part1_oleg_fix','INCONCLUSIVE','Full author archive/zones/SL/TP absent in checked GitHub sources; only13 OLEG and3 STYLE live examples.')
add('NEW_LISTING_FADE_N24','part2_source_completion','REJECTED','Frozen H1 winner failed H2 and last40 after Unicode/daily source correction.')
add('LIQ_WICK_WL0','part3_complete','REJECTED','Frozen rule failed H2 and last40 after all1616 missing resource windows and current-month dailyV completion.')
add('UNLOCK_SHORT','part4_unlocks','INCONCLUSIVE_DATA_BLOCKED','No validated publicly accessible point-in-time calendar in checked sources; actual402/404 preserved; no fabricated PnL.')
add('PF_TIMING_BTC_UP_ONLY','part5_pf_timing','REJECTED','H1-selected filter failed H2/last40, no parameter changes after validation.')
add('PF_EXIT_T0S1B0','part6_coverage_fix','REJECTED','54 H1 variants retained. Frozen selected model lost money on H2 despite significant positive excess vs random. SignalR5.6%, modelSL12%.')
add('LIVE97_EXIT_DIAGNOSTIC','part7_risk_units_fix','INCONCLUSIVE','All97 inventoried,53 price-compatible/44 unresolved; small per-source n. Emergency initial_stop is not financial1R.',table='ALL_SOURCE_TABLES.json')
write(out/'STRATEGY_LEADERBOARD.json',finite(ledger));write(out/'variants.json',[])
# Human-readable deliverable. Code and numerical tables remain linked for independent review.
text='''# Итог CAR: OWNER restart и пакет исследований 17.11.2026

Новых торговых стратегий, прошедших все зарегистрированные проверки, не найдено. Файлы кандидатов пустые; автоматического включения в бумагу или LIVE нет.

|Исследование|Результат независимой проверки|Вердикт|
|---|---|---|
|Manager v2: 12 наборов × X1–X9, плюс PF_BASE|H1-победители и разрешённые зеркала не прошли весь набор H2 / last40 / excess / BH|Нет подтверждённого кандидата|
|OLEG_FIX|13 живых OLEG:5 плюсов/8 минусов; OLEG_STYLE3/3. Полного архива авторских зон/SL/TP в проверенных GitHub-источниках нет|INCONCLUSIVE / DATA_GAP|
|NEW_LISTING_FADE, N24|270 закрытых H2, −0.7007R, PF0.9933, WR51.48%, DD13.8656R; last40 −4.5639R, q0.7437|REJECTED|
|LIQ_WICK_REBOUND, WL0|11390 закрытых H2, −415.3207R, PF0.9262, WR39.71%, DD618.8837R; исходный frozen last40 −352.5105R, q1|REJECTED|
|UNLOCK_SHORT|Исторический PIT-календарь не получен из проверенных публичных источников: HTTP402/404 и результаты поиска сохранены|DATA_BLOCKED|
|PF_TIMING, BTC_UP_ONLY|401 H2, −41.8896R, PF0.6826, WR67.83%; last40 −36.7602R, q1|REJECTED|
|PF54, T0S1B0|813 H2, −32.8593 сигнальныхR, PF0.8809, WR83.76%, DD65.9007R; last40 −0.4723R|REJECTED|
|97 живых сделок|Все сохранены, но53 входа подтверждены Binance1m,44 имеют DATA_GAP; размеры независимых источников слишком малы|INCONCLUSIVE|

R разных моделей имеет разное определение: PF54 — сигнал5.6% цены; listing — исходный стоп8%; wick — расстояние до модельного SL. Их суммы нельзя складывать как доходность одного портфеля. Для PF S1=12% есть отдельная арифметика фиксированного номинального стоп-риска в PF_RISK_UNITS_AUDIT.json. Старое поле USD_at_5risk у PF54 означает $5 на сигнальныйR; оно не равно $5 риска расширенного стопа. Стоп S1 — заказанная модель, не доказанное постоянное правило LIVE.

## Что фактически выполнено

- Код OWNER lock/restart подготовлен в отдельной указанной приватной ветке; Linux228 тестов проходят. WindowsCI заблокирована биллингом до выполнения шагов, поэтому Windows-проверка не заявляется. Установку выполняет Claude после ревью; установка не выполнялась.
- Все правила и исходный код опубликованы до PnL. В v2 рассчитаны108 H1 исходных комбинаций плюс9 для PF. В PF54 рассчитаны все54 H1, включая отрицательные. H2 считается только для frozen winner и заранее указанного контроля.
- Новые листинги:924 символа получили доказательство первого публичного архива после исправления пяти Unicode-ошибок и дополнения daily-only источника. Дата первой свечи — proxy фактического начала торговли, а не доказанная дата объявления листинга.
- Wick:1616 уникальных ранее незавершённых окон объёмов обработаны четырьмя отдельными job; предыдущие успешные профили не пересчитывались. Новые H1 сохранены как аудит прежнего выбора, новая оптимизация по дополненной H1 после увиденной H2 запрещена. Универсум ограничен сохранёнными OHLCV проекта.
- Корректировка покрытия PF переиспользовала54 H1; исправлялась только ошибочная блокировка из-за DATA_GAP цены. Неподтверждённые цены не считались убытками. Все2113 исходные записи учтены:1761 фиксированный вход,316 NOFILL,36 RIGHT_CENSORED без сохранённого входа.
- LIVE97: сырые net_R/исполнения сохранены. Калибровка R исправлена по собственному H1 каждого источника арифметическим пересчётом уже сохранённых исходов, без повторного реплея. Где финансовый R не восстановлен, долларовая проекция убрана.

## Реальная зацепка и её предел

Входы PF с T0S1B0 лучше случайного времени той же монеты: excess+107.7369R на H2, BH-q0.0108; на frozen last40 excess+108.8384R, q0.0054. Однако сама модель убыточна: относительное преимущество не означает положительного ожидания после издержек.

На11 сопоставимых из15 живых PF расширенные тейки дали+3.7961R против+2.9135R, R=5.6% цены. Это диагностический маленький набор, а не подтверждение прибыльности на всей истории. Оставшиеся4 не были дорисованы. Итоги54 H1 и независимой проверки нельзя отменять удачным малым примером.

## Что проверить Claude

1. Совпадение PRE_PNL_CODE_HASHES, code_sha, исходных входов и SELECTION_FROZEN; v1 не переписана. Технические исправления и неудачный JSON-resume сохранены в TECHNICAL_FIXES_AND_LIMITS_RU.md.
2. PF цена проверяется во всём исходном5m-окне:1415/1761=80.3521%, остальные346 отдельно DATA_GAP. Не считать касание свечой доказательством tick-fill/очереди лимита. Для живых сделок отделить усреднённую entry от первого исполнения.
3. ATR/стоп/тейки/BE/trailing совпадают с прежним движком:13 execution-тестов прошли в Actions;90 синтетических parity-кейсов дали0 расхождений. Это проверка реализации, не искусственная ценовая история для доказательства прибыли.
4. Проверить funding cash при полном покрытии, неизвестный funding0 и чувствительность0.01%/8h, maker/taker, проскальзывание5bps, SLfirst/noTPentrybar. MFE/MAE на1m — ценовой envelope при неизвестном intrabar-порядке.
5. Проверить200 контрольных времён/монет, пропуски без пересэмплирования, BH по всей семье, концентрацию прибыли и календарные границы. H2 и last40 перекрываются. Дополнение источников сохраняло исходные cutoffs; отдельно вычислен точный last40 полного доступного корпуса без новых ценовых расчётов.
6. Не путать G3/NO_QUALITY15m в текущем источнике с каноническим G3h98. R1-входы извлечены из сохранённых ребалансировок; происхождение описано в v1 SOURCE_MANIFEST/INPUT_COVERAGE.
7. До любого продолжения проверить единицы риска: safety initial_stop не1R; исходный net_R не пересчитывать как будто известны notional/funding. СуммаR независимых сделок не заменяет портфель с лимитом одновременного риска и ликвидности.
8. Не включать кандидатов автоматически. Новые SL/TP/фильтры нельзя подбирать по уже увиденной H2: для следующей проверки требуется отдельно зафиксированный протокол и новые независимые данные.

## Где лежат доказательства

- В этой ветке: part2_source_completion, part3_complete, part4_unlocks, part5_pf_timing, part6_pf_exits + part6_coverage_fix, part7_live_trades + part7_risk_units_fix; все первоначальные/отрицательные результаты сохранены.
- Manager v2: другая ветка research/manager-all-scenarios, папки v2/results и v2/coverage_fix, итоговый result commit e4412b2cfdccbb6f710f7b32da2f1db6fc360b32.
- Новые numerical source delta caches сохранены отдельными Actions artifacts. Старый проверенный OHLCV-кэш: run44092086995; funding: run43874717889. Новые месячные и дневные архивы имеют официальные CHECKSUM и parsed SHA.
- DATA_NEEDED_RU.md перечисляет недостающие поля Oleg, Bybit-цен/исполнений, фактического риска и unlock-calendar; приватные архивы/ключи/сессии не загружались.

## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА

Проверка нашла несколько красивых первых половин и удачных коротких примеров. Они не удержали прибыль на проверочных данных. У PF есть относительная сила входа, но выбранный выход всё равно теряет деньги: редкие широкие стопы съедают маленькие плюсы. Это основание для будущего отдельного исследования, а не разрешение торговать. Уже проверенные убыточные варианты сохранены, чтобы не повторять их снова.

Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0
Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0
'''
text+='\nТочный last40 дополненного корпуса для frozen WL0: n='+str(exact['n'])+', netR='+str(round(exact['netR'],6))+', PF='+str(round(exact['PF'],6)if exact['PF']is not None else None)+', BH-q='+str(exact['BH_q'])+'; исключено пересечений с H1='+str(train_overlap)+'. См. EXACT_LAST40_COMPLETED_CORPUS.json.\n'
(out/'FINAL_SUMMARY_RU.md').write_text(text);(out/'CLAUDE_HANDOFF_RU.md').write_text(text);write(out/'CODE_AND_SOURCE_REFS.json',refs);write(out/'FINAL_CHECKPOINT.json',dict(status='AVAILABLE_RESEARCH_COMPLETE_WITH_EXPLICIT_DATA_BLOCKERS',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),new_validated_strategies=0,paper_candidates=0,owner_installed=False,live_changes=0,blocked=['Full Oleg author archive/zones/SL/TP','44 live entry prices not confirmed Binance proxy','Validated public PIT unlock calendar','Windows OWNER CI billing'],original_successful_profiles_recomputed=False,methodology_changes_documented=True));write(out/'CHECKPOINT.json',load(out/'FINAL_CHECKPOINT.json'));write(out/'ARTIFACT_HASHES.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and p.name!='ARTIFACT_HASHES.json'})
