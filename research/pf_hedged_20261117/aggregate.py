import json,gzip,os,subprocess,hashlib
from pathlib import Path
import numpy as np
from hedge import *
B=Path('research/pf_hedged_20261117')
def load(phase):
 rows=[];null={}
 for p in sorted(Path('model').glob(phase+'_shard*')):
  with gzip.open(p/'ACTUAL_ROWS.jsonl.gz','rt')as f:rows.extend(json.loads(s)for s in f)
  z=np.load(p/'CONTROL200.npz',allow_pickle=False)
  for k,v,c in zip(z['keys'],z['variants'],z['netR']):null[(k.decode(),v.decode())]=c
 return rows,null
def select():
 rows,_=load('train');scores={c:metrics([r for r in rows if r['variant']==c])for c in CODES};eligible=[c for c,m in scores.items()if m['n']>=60 and m['coverage']>=.95];winner=max(eligible,key=lambda c:scores[c]['netR'])if eligible else None;raw=max(CODES,key=lambda c:scores[c]['netR']);save(B/'selection/SELECTION_FROZEN.json',dict(winner=winner,raw_winner=raw,scores=scores,eligible=eligible,criterion='max H1 netR coverage>=95% n>=60, no H2 selection',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
def final():
 train,_=load('train');test,null=load('test');rows=train+test;sel=json.load(open('selection/SELECTION_FROZEN.json'));winner=sel['winner'];tables={};q={}
 for part in['H1','H2','LAST40','FULL']:
  tables[part]={}
  for c in CODES+['NO_HEDGE']:
   rr=[r for r in rows if r['variant']==c and(part=='FULL'or r['split']==part or part=='LAST40'and r['last40'])];m=metrics(rr)
   if c!='NO_HEDGE'and part in['H2','LAST40']:m.update(paired(rr,[null.get((r['key'],c),np.full(200,np.nan))for r in rr]))
   tables[part][c]=m
  if part in['H2','LAST40']:
   qq=bh([tables[part][c]['p']for c in CODES]);q[part]=dict(zip(CODES,qq))
   for c,x in zip(CODES,qq):tables[part][c]['BH_q']=x
 ok=winner is not None
 for part,n in[('H1',60),('H2',30),('LAST40',30)]:
  m=tables[part].get(winner,{})
  ok=bool(ok and m.get('n',0)>=n and m.get('coverage',0)>=.95 and m.get('netR',0)>0 and(m.get('PF')or 0)>=1.3 and m.get('netR_funding_adverse',-1)>0 and(m.get('top3_share')or 1)<=.5 and m.get('funding_unknown_n',1)==0)
 for part in['H2','LAST40']:
  m=tables[part].get(winner,{});ok=bool(ok and m.get('excessR',0)>0 and m.get('BH_q',1)<=.1 and m.get('control_coverage',0)>=.95)
 out=B/'final';save(out/'METRICS_ALL_VARIANTS.json',tables);save(out/'VERDICT.json',dict(hedge_turns_PF_positive_all_history=ok,frozen_winner=winner,raw_H1_winner=sel['raw_winner'],status='PROMISING'if ok else'NOT_CONFIRMED',fresh_independent_OOS=False));save(out/'variants.json',[] if not ok else[dict(id='PF_HEDGED_'+winner,enabled=False,status='PROMISING')])
 lines=['# PF_HEDGED — итог','',f'**Хедж превращает PF в плюс на всей истории — {"ДА"if ok else"НЕТ"} (не подтверждено по зафиксированным критериям).**','',f'Победитель H1: {winner}; сырой максимум H1: {sel["raw_winner"]}. Выбор на H2 не изменялся.','']
 for part in['H1','H2','LAST40','FULL']:
  lines+=['## '+part,'','|Вариант|n|WR %|PF|netR|шорт R|лонг R|DD R|покрытие %|excess R|q|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
  for c,m in tables[part].items():
   def f(k):return f'{m[k]:.3f}'if m.get(k)is not None else'—'
   lines.append('|'+ '|'.join([c,str(m['n']),f('WR'),f('PF'),f('netR'),f('short_R'),f('hedge_R'),f('maxDD_R'),f'{100*m["coverage"]:.1f}',f('excessR'),f('BH_q')])+'|')
  lines.append('')
 lines+=['## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','','Мы оставили короткие сделки неизменными и добавили покупку корзины или BTC. Считаются комиссии и проскальзывание каждого изменения обеих ног. Сравнивать нужно также с шортом на точно тех же сделках: пропуски котировок могут создавать ложное улучшение.','', 'Положительный excess означает преимущество относительно случайных входов, а не положительную доходность. Победитель должен зарабатывать и после издержек. Все 6 результатов сохранены, включая отрицательные.','', 'H2 уже участвовал в постановке гипотезы: даже положительный результат требует нового периода. Last40 перекрывается с H2. DD — по закрытым сделкам, не портфельный MTM; $5/R — линейная проекция без ограничений капитала.','', '## Источники и ограничения','','Исходные1761 входов, исходные346 DATA_GAP не восстанавливались подменой пар. Старые H1/H2 реальные события взяты из сохранённых артефактов; реконструированы только отсутствующие PURGE-пути и200 контрольных событий, ранее сохранённых лишь итоговым netR. Проверка контрольных масок и доходности сохранена в PARENT_CONTROL_REPRODUCTION. Funding Binance; неизвестный funding отдельно отмечен и стрессирован. Метрики matched_nohedge_netR, неизвестный funding, комиссии, концентрация и gap counts доступны в METRICS_ALL_VARIANTS.json.','', 'Bybit недоступен из Actions для рыночного исполнения: цены Binance — прокси. Публичный снимок Bybit13.11 использован для статических типов и текущих минимальных лотов, не как историческая вселенная. На $5/signalR short notional=$89.29; ALT100 на50 монет=$1.79/монету ниже типового5USDT; ALT50=$0.89. BTC minQty=.001 при73541.50 даёт минимум73.54USDT: BTC50 на44.64 не проходит; BTC100 округляется с89.29 до73.54 или147.08. Исполнимость55USDT не доказана, текущие дробные корзины не являются готовой конфигурацией ордеров.','', '## Независимая проверка Claude Code','','Проверить исходные source pins/sha и parent-control identity; неизменность шорт-пути; исполнение после5mclose и оставшуюся долю; PIT rank строго до входа, aliases и static type; знаки и покрытие funding; прибыль обеих ног и все расходы; matched-sample baseline; заморозку H1 до H2; BH6 и долю valid controls. Без повторения54 старых профилей.','', 'Код: research/pf_hedged_20261117; источник подготовленных данных run44169150415, путей run44171887648. Каждая строка сделки и контроля сохранена в train/test shard artifacts; SOURCE manifest содержит SHA256 входов.','', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
 (out/'OTCHET_DLYA_CLAUDE_CODEX_PF_HEDGED_20261117.md').write_text('\n'.join(lines)+'\n');save(out/'CHECKPOINT.json',dict(status='COMPLETE',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),winner=winner,live_changes=0))
if __name__=='__main__':select()if os.environ['AGG_PHASE']=='select'else final()
