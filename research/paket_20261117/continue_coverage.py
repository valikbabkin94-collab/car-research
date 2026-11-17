"""Resume only previously skipped H2. Reuse all saved H1 profiles, never refit prices/SL/TP.
Price DATA_GAP is excluded from coverage denominator, kept as a missing row.
"""
import os,sys,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from lab.common import *
from lab.study import passed
from lab.runner import report,CODES
prev=Path('previous_results');out=Path(os.environ['LAB_OUTPUT']);out.mkdir(parents=True,exist_ok=True);kind=os.environ['RESUME_KIND'];asof=int(os.environ['LAB_ASOF_MS']);code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();write(out/'STARTED.json',dict(code_sha=code_sha,kind=kind,asof=asof));m=Market(asof)

def repair(source,dest,codes,family,unit=None,extras=()):
 dest.mkdir(parents=True,exist_ok=True);old=load(source/'SELECTION_FROZEN.json');table=load(source/'TABLES.json')
 if old['winner'] is not None:return dict(status='ALREADY_COMPLETE_NO_RECOMPUTE',selection=old,tables=table,source=str(source))
 es=load(source/'INPUTS.json');sp=old['splits'];h1=[e for e in es if phase(e,sp)=='H1'];h2=[e for e in es if phase(e,sp)=='H2'];z=np.load(source/'ALL_ACTUAL_EXITS.npz',allow_pickle=False);h1keys={e['key']for e in h1};arrays={}
 for c in codes:
  mask=(z['variants']==c.encode())&(~z['mirrors']);records=[(k.decode(),r)for k,r in zip(z['keys'][mask],z['outcomes'][mask])if k.decode()in h1keys];arrays[c]=records
 options=[];audit=[]
 for c,records in arrays.items():
  rs=[r for k,r in records];eligible=sum(r[0]!=-2 for r in rs);closed=sum(r[0]==1 for r in rs);net=float(sum(r[1]for r in rs if r[0]==1));coverage=closed/max(1,eligible);audit.append(dict(variant=c,H1_rows=len(rs),price_confirmed=eligible,n_closed=closed,coverage_of_price_confirmed=coverage,netR=net))
  if closed>=max(5,min(60,len(h1)))and coverage>=.9:options.append((net,c))
 winner=max(options,key=lambda x:(x[0],x[1]))[1]if options else None
 frozen=dict(code_sha=code_sha,source_code_sha=old['code_sha'],original_selection=old,winner=winner,mirror_winner=old.get('mirror_winner'),method='H1 netR unchanged; only coverage denominator corrected to exclude priceDATA_GAP, no SL/TP/entry-price change',H1_recomputed=False,H1_source_sha256=hashlib.sha256((source/'ALL_ACTUAL_EXITS.npz').read_bytes()).hexdigest(),audit=audit,splits=sp)
 # Freeze before any new H2 calculations. Original SELECTION remains intact in previous result commit/artifact.
 write(dest/'SELECTION_FROZEN_COVERAGE_FIX.json',frozen);newrows=[];newnull=[];keys=[];variants=[];outcomes=[]
 if winner:
  for c in list(dict.fromkeys([winner]+list(extras))):
   rr=[];nn=[]
   for i,e in enumerate(h2):
    r=model(m,e,c,unit=unit);v=controls(m,e,c,sp,unit=unit);rr.append(r);nn.append(v);keys.append(e['key']);variants.append(c);outcomes.append(r);newnull.append(v)
    if i%100==0:print('RESUME_H2_ONLY',dest.name,c,i,'/',len(h2),flush=True)
   for period in ['H2','LAST40']:
    ix=[i for i,e in enumerate(h2)if period=='H2'or e['entry_ms']>=sp[2]];rs=[rr[i]for i in ix];n=[nn[i]for i in ix];p=paired_test(rs,n);row=dict(period=period,variant=c,mirror=False,**metrics(rs),excessR=p['excessR'],p=p['p'],control_coverage=p['coverage'],control_n=p['n'],selected_on_H1=c==winner);newrows.append(row)
 table+=newrows
 if outcomes:np.savez_compressed(dest/'NEW_H2_ACTUAL_AND_CONTROL200.npz',keys=np.array(keys,dtype='S64'),variants=np.array(variants,dtype='S16'),outcomes=np.array(outcomes),control_netR=np.array(newnull,dtype='f4'))
 write(dest/'H1_SAVED_COVERAGE_AUDIT.json',audit);write(dest/'TABLES.json',finite(table));return dict(status='RESUMED_H2_ONLY'if winner else'NO_H1_ELIGIBLE_WINNER_AFTER_PRICE_GAP_EXCLUSION',selection=frozen,tables=table)

if kind=='pf':
 result=repair(prev,out,[f'T{t}S{s}B{b}'for t in range(6)for s in range(3)for b in range(3)],54,.056,extras=['T0S1B0']);table=result['tables'];family=54
 for period in ['H2','LAST40']:
  rs=[r for r in table if r['period']==period];qs=bh([r['p']for r in rs]+[1.]*max(0,family-len(rs)))
  for r,q in zip(rs,qs):r['BH_q']=q
 validation=load(prev/'PF_5M_ENTRY_VALIDATION.json');winner=result['selection']['winner'];variants=[dict(name='PF_EXIT_'+winner,enabled=False,status='PROMISING_REQUIRES_CLAUDE_REVIEW')]if winner and validation['eligible']and passed(table,winner)else[];write(out/'TABLES.json',finite(table));write(out/'variants.json',variants);report(out,'Часть6 — продолжение H2 без пересчёта54 H1',f'Исправлен только знаменатель покрытия: DATA_GAP цены не является проигрышем профиля. H1 замороженные исходы переиспользованы; winner {winner}. Полное исходное покрытие {validation["compatible"]}/{validation["frozen_entries"]}; оно всё ещё ниже90%, это ограничивает перенос на весьPF. Кандидатов {len(variants)}.',table,notes='Первичный результат54H1 и исходный SELECTION_FROZEN не переписаны; здесь только ранее пропущенный H2. Параметры не менялись и H2 не использовалась для выбора. Пост-выход/BE диагностика сохранена в исходной папке и не пересчитывается.');cp=dict(status=result['status'],winner=winner,candidates=len(variants),H1_recomputed=False,price_coverage=validation['fraction'])
else:
 # Only skipped original-direction winners; keep completed mirrors/qualified cohorts untouched.
 tables=[];changed=[];selections={}
 for source in sorted(prev.iterdir()):
  if not(source/'SELECTION_FROZEN.json').exists():continue
  result=repair(source,out/source.name,CODES,156);selections[source.name]=result['selection'];changed.append(dict(case=source.name,status=result['status']))
  for row in result['tables']:row['case']=source.name;tables.append(row)
 for period in ['H2','LAST40']:
  rs=[r for r in tables if r['period']==period];qs=bh([r['p']for r in rs]+[1.]*max(0,156-len(rs)))
  for row,q in zip(rs,qs):row['BH_q']=q
 validation=load(prev/'PF_5M_ENTRY_VALIDATION.json');variants=[]
 for case,sel in selections.items():
  if case=='PF_BASE'and not validation['eligible']:continue
  for key,flip in [('winner',False),('mirror_winner',True)]:
   c=sel.get(key)
   if c and passed([r for r in tables if r['case']==case],c,flip):variants.append(dict(name='MGR2_'+case+'_'+c+('_MIRROR'if flip else''),enabled=False,status='PROMISING_REQUIRES_CLAUDE_REVIEW'))
 write(out/'ALL_TABLES.json',finite(tables));write(out/'RESUMPTION_AUDIT.json',changed);write(out/'variants.json',variants);report(out,'Manager v2 — продолжение только пропущенных H2',f'Все сохранённые H1 переиспользованы. Исправлено покрытие относительно входов с подтверждённой ценой; n/контроль/BH/параметры сохранены. Кандидатов {len(variants)}.',tables,notes='У ранее квалифицированных сценариев H2/зеркала не пересчитывались. Источник первичных неизменённых результатов — previous_results artifact originalrun. PF_BASE с80.35% полной совместимости остаётся DATA_GAP для обобщения на весь источник.');cp=dict(status='COMPLETE_WITH_DATA_GAPS',candidates=len(variants),H1_recomputed=False,changed=changed)
write(out/'CHECKPOINT.json',dict(code_sha=code_sha,asof=asof,kind=kind,**cp,no_live_changes=True));write(out/'ARTIFACT_HASHES.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and p.name!='ARTIFACT_HASHES.json'})
