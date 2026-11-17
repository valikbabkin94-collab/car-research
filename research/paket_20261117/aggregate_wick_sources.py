"""Combine saved original and disjoint source-completion outcomes; no price replay, no reselection."""
import os,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from lab.common import *
from lab.study import passed
from lab.runner import report
prev=Path('previous_results');out=Path(os.environ['LAB_OUTPUT']);out.mkdir(parents=True,exist_ok=True);selection=load(prev/'SELECTION_FROZEN.json');winner=selection['winner'];sp=selection['split'];entries={e['key']:e for e in load(prev/'INPUTS.json')};records=load(prev/'ALL_ACTUAL_EXITS.json.gz');null=load(prev/'CONTROL200.json.gz');h2=[r for r in records if r['period']=='H2'];assert len(h2)==len(null);controls_map={r['key']:np.array(n,float)for r,n in zip(h2,null)};seen={(r['key'],r['variant'])for r in records};source_audit=[];remaining=0
for directory in sorted(Path('source_shards').iterdir()):
 if not directory.is_dir():continue
 inputs=load(directory/'NEW_INPUTS.json');newrows=load(directory/'NEW_ACTUAL_ONLY.json.gz');zz=np.load(directory/'NEW_H2_CONTROL200.npz',allow_pickle=False)
 for key,row in zip(zz['keys'],zz['netR']):assert key.decode()not in controls_map;controls_map[key.decode()]=row
 for e in inputs:
  if e['key']in entries:raise ValueError('DUPLICATED_INPUT_SOURCE')
  entries[e['key']]=e
 for r in newrows:
  key=(r['key'],r['variant'])
  if key in seen:raise ValueError('DUPLICATED_SUCCESSFUL_PROFILE')
  seen.add(key);records.append(r)
 cp=load(directory/'CHECKPOINT.json');counts=load(directory/'WINDOW_COUNTS.json');remaining+=len(counts['remaining']);source_audit.append(cp)
# Current-month dailyV completion is a separate already frozen source job.
daily=Path('daily_completion');newdaily=load(daily/'NEW_EVENTS.json');added=[e for e in newdaily if e['variant']==winner and e['entry_ms']>=sp[1]];zz=np.load(daily/'NEW_H2_ONLY_OUTCOMES_AND_CONTROLS.npz',allow_pickle=False);assert len(added)==len(zz['outcomes'])==len(zz['control_netR'])
for e,row,n in zip(added,zz['outcomes'],zz['control_netR']):
 if(e['key'],winner)in seen:raise ValueError('DUPLICATED_DAILY_SOURCE_EVENT')
 entries[e['key']]=e;seen.add((e['key'],winner));records.append(dict(key=e['key'],variant=winner,period='H2',outcome=finite(row)));controls_map[e['key']]=n
source_audit.append(load(daily/'CHECKPOINT.json'));tables=[]
for code in['WL0','WL1','WS0','WS1']:
 rs=[np.array(r['outcome'],float)for r in records if r['period']=='H1'and r['variant']==code];tables.append(dict(period='H1',variant=code,**metrics(rs),not_used_for_reselection=True))
if winner:
 for period in['H2','LAST40']:
  selected=[r for r in records if r['period']=='H2'and r['variant']==winner and(period=='H2'or entries[r['key']]['entry_ms']>=sp[2])];rs=[np.array(r['outcome'],float)for r in selected];ns=[controls_map[r['key']]for r in selected];p=paired_test(rs,ns);tables.append(dict(period=period,variant=winner,**metrics(rs),excessR=p['excessR'],p=p['p'],control_coverage=p['coverage'],BH_q=min(1.,p['p']*4)))
variants=[dict(name='LIQ_WICK_'+winner,enabled=False,status='PROMISING_CACHED_UNIVERSE_REQUIRES_CLAUDE_REVIEW')]if winner and remaining==0 and passed(tables,winner)else[];write(out/'TABLES.json',finite(tables));write(out/'SOURCE_CHECKPOINTS.json',source_audit);write(out/'ORIGINAL_SELECTION_UNCHANGED.json',selection);gzip_json(out/'ALL_SAVED_ACTUAL_OUTCOMES.json.gz',records);write(out/'INPUTS.json',list(entries.values()));np.savez_compressed(out/'H2_CONTROL200_COMBINED.npz',keys=np.array(list(controls_map),dtype='S64'),netR=np.array(list(controls_map.values()),dtype='f4'));write(out/'variants.json',variants)
report(out,'Часть3 — объединённая проверка после догрузки пропущенных источников',f'Исходный H1 winner {winner} не менялся. Успешных исходных профилей повторно рассчитано0; добавлены только ранее не обработанные окна и current-month dailyV. Новых правил/параметров0. Оставшихся resource-окон {remaining}; кандидатов {len(variants)}.',tables,notes='Обогащённая H1 — аудит устойчивости исходного выбора, не повторная оптимизация: нельзя переключаться на другое правило по дополненнойH1 после увиденнойH2. LAST40 использует исходный замороженный cutoff плюс новыеOOSдни; это не независимая репликация. Универсум — только сохранённыеOHLCV проекта, не весь рынок. Имеются source/public-price gaps; перечислены в shard artifacts. СуммаR по сделкам не заменяет портфельный тест с ограничением одновременного риска/капитала. Новые quote/volume delta caches сохранены отдельными Actions artifacts с SHA; старый2.6GBкэш повторно не публиковался.')
write(out/'CHECKPOINT.json',dict(code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),status='COMPLETE_SAVED_SOURCE_MERGE_WITH_REMAINING_GAPS',winner=winner,candidates=len(variants),remaining_resource_windows=remaining,original_H1_choice_unchanged=True,successful_profiles_recomputed=False,no_live_changes=True));write(out/'ARTIFACT_HASHES.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and p.name!='ARTIFACT_HASHES.json'})
