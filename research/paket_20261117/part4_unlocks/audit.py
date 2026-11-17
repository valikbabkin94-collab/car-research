"""Public-source unlock archive audit; no market/trade/account interfaces."""
import json,hashlib,urllib.request,urllib.error,datetime
from pathlib import Path
P=Path(__file__).parent;out=[]
urls=['https://api.llama.fi/emissions','https://api.github.com/repos/DefiLlama/emissions-adapters']
for url in urls:
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'CAR-offline-public-source-audit','Accept':'application/json'})
  with urllib.request.urlopen(req,timeout=25)as r:raw=r.read(10000000);status=r.status
  d=json.loads(raw);out.append(dict(url=url,status=status,sha256=hashlib.sha256(raw).hexdigest(),root_type=type(d).__name__,root_fields=list(d)[:30]if isinstance(d,dict)else[],rows=len(d)if isinstance(d,list)else None))
 except Exception as e:out.append(dict(url=url,status='UNAVAILABLE',error=type(e).__name__))
(P/'SOURCE_AUDIT.json').write_text(json.dumps(dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=out),indent=2)+'\n')
status='DATA_BLOCKED_NO_VALIDATED_POINT_IN_TIME_UNLOCK_INPUT'
(P/'CHECKPOINT.json').write_text(json.dumps(dict(status=status,PnL_run=False,reason='Available current schedules/repository metadata do not constitute a validated event-level historical input with first-known timestamp and historical supply. No historical calendar was inferred from a revised current schedule.',required_fields=['symbol','unlock_time_utc','unlocked_amount','historical_supply','first_known_utc','source_url','source_commit_or_snapshot_sha']),indent=2)+'\n')
(P/'REPORT_RU.md').write_text('''# Часть4 — UNLOCK_SHORT\n\nDATA_BLOCKED: в этом запуске нет проверенного входного исторического календаря с timestamp первой публикации и историческим предложением. Выполненные обращения к открытым источникам и SHA сохранены в SOURCE_AUDIT.json. Это не утверждение, что истории нигде не существует. Текущий пересмотренный календарь нельзя выдавать за информацию, известную за7/3/1день до события. PnL не запускался.\n\nЗарегистрирована сетка: short за7/3/1день до разлока>=1% исторического предложения; выход в день события/+3дня. SL1.5ATR14 по закрытым1h, maxhold11дней; параметры фиксируются до любого PnL. Данные не генерировались.\n\n## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА\n\nДля честной проверки нужен календарь, который действительно был известен заранее. По сегодняшнему расписанию задним числом торговать нельзя. Остальные части не ждут этот источник.\n\nDesktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0\n''')
(P/'variants.json').write_text('[]\n')
