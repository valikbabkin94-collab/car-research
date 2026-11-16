"""Metadata-only author-log quality gate. Never reruns fills or queries prices."""
import sys,json,copy,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from run import read,gz,render,LAB,OUT,I
from market import save,sha

def gate(rows):
 result=[]
 for old in rows:
  r=copy.deepcopy(old)
  if r['policy']=='P1'and r.get('unresolved_author_actions',0)>0:
   r['execution_quality']='UNRESOLVED_AUTHOR_LOG'
   if r['status']=='TRADE':r['counterfactual_netR']=r['netR'];r['netR']=None;r['status']='UNRESOLVED_AUTHOR_LOG'
  result.append(r)
 return result

def main():
 src=OUT/'ALL_POLICY_TRADES.json.gz';raw=src.read_bytes();original=OUT/'RAW_POLICY_TRADES_BEFORE_QUALITY.json.gz'
 if original.exists():raise RuntimeError('QUALITY_ALREADY_APPLIED_NO_OVERWRITE')
 original.write_bytes(raw);save(OUT/'EXECUTION_CHECKPOINT_BEFORE_QUALITY.json',read(LAB/'CHECKPOINT.json'));rows=gate(read(src));signals=read(I/'SIGNALS_WITH_UPDATES.json.gz');receipts=read(OUT/'ALL_SOURCE_RECEIPTS.json');render(rows,signals,receipts)
 save(OUT/'QUALITY_REVIEW.json',dict(criterion='P1 unresolved_author_actions>0 excludes exact author outcome regardless of sign; conditional baseline retained separately',before_quality_sha256=sha(raw),implementation='metadata_only_no_fills_or_PnL_replay',changed_closed_rows=sum(a['status']!=b['status']for a,b in zip(read(original),rows)),code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
 tables=read(OUT/'TABLES.json');idx={(r['channel'],r['period'],r['policy']):r for r in tables if r['cohort']=='MATCHED5'};comparison=[]
 for ch in read(LAB/'CHANNEL_REGISTRY.json'):
  for policy in ['P1','P2','P3']:
   parts={}
   for period in ['CAL_H1','CAL_H2','HIST_LAST40']:
    r=idx[(ch,period,policy)];parts[period]=dict(n=r['n'],PF=r['PF'],netR=r['netR'],delta_vs_P4=r['netR']-idx[(ch,period,'P4')]['netR'],delta_vs_P5=r['netR']-idx[(ch,period,'P5')]['netR'])
   comparison.append(dict(channel=ch,policy=policy,periods=parts,improved_vs_P4_both_halves=all(parts[z]['n']>0 and parts[z]['delta_vs_P4']>0 for z in ['CAL_H1','CAL_H2']),interpretation='Composite entry/exit/friction policy effect on complete matched cohort, not pure author skill or causal exit effect'))
 save(OUT/'BASELINE_COMPARISON.json',comparison)
 p=LAB/'OTCHET_DLYA_CLAUDE_CODEX_CHANNELS_AUDIT_V2_20261116.md';text=p.read_text();text=text.replace('## Фактически выполнено','''## Фильтр качества журнала автора

Если в P1 есть неразобранное действие автора, результат удержания до SL/TP является только контрфактическим. Он сохранён в RAW_POLICY_TRADES_BEFORE_QUALITY.json.gz и поле counterfactual_netR, но исключён из строгого P1 и matched5 независимо от знака прибыли. Это уточнение соответствия исходному протоколу об UNRESOLVED, без повторного исполнения или подбора политики. Критерий и SHA до/после сохранены в QUALITY_REVIEW.json.

## Фактически выполнено''');p.write_text(text)
if __name__=='__main__':main()
