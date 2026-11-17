"""Pure change of displayed R units using each source's own H1. No backtest runs.
Entries, prices, execution events, PF/WR, p/q and frozen choices unchanged.
"""
import os,json,gzip,hashlib,subprocess,collections
from pathlib import Path
import numpy as np
from lab.common import load,write,gzip_json,finite,stamp,M
from lab.extra import actual_return
from lab.runner import live_inputs,report
prev=Path('previous_results');out=Path(os.environ['LAB_OUTPUT']);out.mkdir(parents=True,exist_ok=True);trades=live_inputs();old=load(prev/'RISK_CALIBRATION_H1_ONLY.json');new={};audit=[];rows=load(prev/'ALL_SOURCE_TABLES.json');table=[]
for source in old:
 ts=[t for t in trades if t['source']==source];lo=min(stamp(t['open'])for t in ts);hi=max(stamp(t['open'])for t in ts)+M;half=(lo+hi)//2
 stops=[t for t in ts if stamp(t['close'])<half and len(t['exits'])==1 and t['exit_reason']in['stoploss_on_exchange','stop_on_exchange_panel']and actual_return(t)is not None and actual_return(t)<0]
 vals=[-actual_return(t)for t in stops];width=.056 if source=='PUMP_FADE'else float(np.median(vals))if vals else None;unit=width or .01;oldunit=old[source]['width']or .01;factor=oldunit/unit
 new[source]=dict(width=width,diagnostic_display_unit=unit,H1_end_ms=half,n_H1_full_stopouts=len(stops),source='SIGNAL_SL5.6_PERCENT'if source=='PUMP_FADE'else'SOURCE_OWN_H1_MEDIAN_FULL_STOP_LOSS'if width else'UNKNOWN_STRATEGY_R_DIAGNOSTIC_PRICE1_PERCENT',old_width=old[source]['width'],rescale_factor=factor,no_backtest_repeated=True)
 for row in rows:
  if row['case']!=source:continue
  r=dict(row,risk_unit=new[source]['source'])
  for k in ['netR','USD_at_5risk','maxDD_R','netR_adverse','excessR']:
   if r.get(k)is not None:r[k]*=factor
  if width is None:r['USD_at_5risk']=None;r['USD_reason']='UNKNOWN_FINANCIAL_R_DO_NOT_TREAT_PRICE1PCT_AS_STRATEGY_R'
  table.append(r)
 p=prev/source/'ALL97_ALTERNATIVES_DIAGNOSTIC.json.gz';records=load(p)
 for record in records:
  r=record['result']
  if r[0]==1:
   for k in[1,6,9,10]:r[k]*=factor
   r[30]=unit
  record['risk_unit']=new[source]['source']
 (out/source).mkdir(exist_ok=True);gzip_json(out/source/'ALL_ALTERNATIVES_SAME_EXITS_NEW_R_UNITS.json.gz',records)
 rr=[r for r in table if r['case']==source];h1=[r for r in rr if r['period']=='H1'];positive_n=[r for r in h1 if r['n']>0];best=max(positive_n,key=lambda r:r['netR'])if positive_n else None;worst=min(positive_n,key=lambda r:r['netR'])if positive_n else None
 frozen=load(prev/source/'SELECTION_FROZEN.json');audit.append(dict(source=source,n_live=len(ts),H1_winner_frozen=frozen['winner'],H1_best_descriptive=best['variant']if best else None,H1_worst_descriptive=worst['variant']if worst else None,H1_selection_below_min_n=frozen['winner']is None,verdict='INCONCLUSIVE_SMALL_N',no_claim_systematic_early_exit_or_bad_entry=True))
baseline=load(prev/'X0_ACTUAL_FILLS_AUDIT.json')
for r in baseline:
 w=new[r['source']]['width'];r['calibrated_R']=r['reconstructed_price_return']/w if w and r['reconstructed_price_return']is not None else None;r['risk_source']=new[r['source']]['source']
write(out/'X0_ACTUAL_FILLS_AUDIT.json',baseline);write(out/'RISK_CALIBRATION_OWN_SOURCE_H1_ONLY.json',new);write(out/'ALL_SOURCE_TABLES.json',finite(table));write(out/'SOURCE_BEST_WORST_H1.json',audit);write(out/'variants.json',[])
# Original p/q/PF/WR do not change under positive constant unit scaling.
report(out,'Часть7 — поправка отображения R: собственный H1 источника','97 записей,14 источников. Исправлена только нормализация: полный стоп источника должен закрыться до его собственного H1_end, а не общей середины всех источников. Никаких новых свечных реплеев. Сигналы/выходы/WR/PF/p/q и H1-choice сохранены.',table,notes='Изначальный report и массивы сохранены как техническая версия. Для неизвестного финансовогоR долларовая проекция убрана: PRICE1% — только единица описания движения цены. raw provided_native_R остаётся отдельно. Исходный экспорт не содержит исходных notional/amount/fundingcash, поэтому точный долларовый PnL не восстанавливается. Проверка Claude15PF остаётся11пар,+2.9135R/+3.7961R при ценовомR5.6%; остальные4 не дорисованы. SOURCE_BEST_WORST_H1 показывает сохранённый выбор и отдельно descriptive best/worst; маленькие выборки не позволяют систематический вывод об ошибке входа/раннем выходе.')
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();write(out/'CHECKPOINT.json',dict(code_sha=sha,status='COMPLETE_R_UNITS_CORRECTED_NO_BACKTEST_REPEAT',raw_trades=97,sources=14,candidates=0,source_artifact_run=44134160121,source_artifact='paket-part7_live_trades',no_live_changes=True));write(out/'ARTIFACT_HASHES.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and p.name!='ARTIFACT_HASHES.json'})
