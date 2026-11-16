"""Publish only research outcomes and public-input receipts, never machine state."""
import argparse,json,os,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',required=True);p.add_argument('--out',required=True);a=p.parse_args();source=Path(a.results);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
# Explicit allowlist: simulated outcomes/public funding, no runner env, credentials or git state.
for file in source.rglob('*') if source.exists() else []:
 if not file.is_file() or not (file.name.endswith('.json') or file.name.endswith('.jsonl.gz') or file.name.endswith('.csv.gz') or file.name.endswith('.json.gz')):continue
 target=out/'artifacts'/file.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
lines=['# Оригинальный15m Round4 — автоматическая контрольная точка','',f"GitHub run: {os.environ.get('GITHUB_RUN_ID','unknown')}",f"Workflow code SHA: {os.environ.get('GITHUB_SHA','unknown')}",'','Это исследовательская симуляция по публичным рыночным данным, не история реальной торговли. Полный старый per-file эталон недоступен: не заявлять полную эквивалентность старых SHA. Новые источники проверены по CHECKSUM. Неизвестный ноябрь и non-meme метаданные не заменяются нулями.','']
r1=next(iter(source.rglob('R1_15M_RESULTS.json')),None) if source.exists() else None
if r1:
 lines+=['## R1, исходные00:15','', '|Вариант|Net на подтверждённом участке|SharpeH1|SharpeH2,усечённый|','|---|---:|---:|---:|']
 for name,r in json.loads(r1.read_text()).items():
  periods=r['periods'];lines.append(f"|{name}|{periods['SOURCE_BOUNDED_FULL'].get('net_usdt')}|{periods['H1'].get('daily_sharpe')}|{periods['H2_SOURCE_BOUNDED'].get('daily_sharpe')}|")
else:lines+=['R1 PnL не найден: не считать расчёт завершённым.']
g3=next(iter(source.rglob('G3_15M_RESULTS.json')),None) if source.exists() else None
if g3:
 lines+=['','## G3, настоящие15mподтверждения','','|Вариант|Закрытых|NetRзакрытых|PF_R|Статус|','|---|---:|---:|---:|---|']
 for name,r in json.loads(g3.read_text()).items():
  mm=r.get('periods',{}).get('SOURCE_BOUNDED_FULL',{});lines.append(f"|{name}|{r.get('closed','NA')}|{mm.get('sum_R_closed','NA')}|{mm.get('PF_R_closed','NA')}|{r.get('status',r.get('profitability','INCONCLUSIVE'))}|")
else:lines+=['','G3 PnL не найден: возможно завершён только source audit или сбор funding.']
lines+=['','## Незавершённое','Полное окно с неизвестными расходами не является подтверждённым результатом. При DATA_MISMATCH запрещено использовать новые данные вместо исходных. При source/data блокере сохранять результаты и конкретный checkpoint, не запускать слепой новый перебор.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','Результаты выше существуют только там, где фактически сохранён итоговый JSON. Это не разрешение менять торговлю. Отсутствующий результат или неизвестные расходы не означают прибыль или ноль.','','Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
(out/'OTCHET_RU.md').write_text('\n'.join(lines)+'\n');(out/'CHECKPOINT.json').write_text(json.dumps({'run':os.environ.get('GITHUB_RUN_ID'),'workflow_code_sha':os.environ.get('GITHUB_SHA'),'R1_result_present':r1 is not None,'G3_result_present':g3 is not None,'live_changes':0,'old_reference':'INCOMPLETE_PER_FILE_MANIFEST'},indent=2)+'\n')
