"""SPECULANTKA text/reply reconstruction. No market outcomes accessed."""
import re,unicodedata,hashlib,collections,random,json
NUM=r'\d+(?:[.,]\d+)?'
STOPWORDS={'USDT','LONG','SHORT','STOP','TP','SL','BE','BTCUSDT','H4','H12','VIP','USD','ROI','PNL','RSI','EMA','HTF','LTF'}
def text(t):return unicodedata.normalize('NFKC',t)
def number(s):return float(s.replace(',','.'))
def discover(rows):
 coins={'BTC','ETH','SOL','BNB','XRP'}
 for r in rows:
  t=text(r['text']);m=re.search(r'(?i)монета\s*:\s*([a-z0-9]{2,15})',t)
  if m:coins.add(m[1].upper().removesuffix('USDT'))
  for m in re.finditer(r'\b([A-Z][A-Z0-9]{1,14})\s+(?:SHORT|LONG|шорт|лонг)\b',t):coins.add(m[1].removesuffix('USDT'))
 return {c for c in coins-STOPWORDS if c}

def parse(r,coins):
 t=text(r['text']);low=t.lower();found=[];m=re.search(r'(?i)монета\s*:\s*([a-z0-9]{2,15})',t)
 if m:found=[m[1].upper().removesuffix('USDT')]if m[1].upper().removesuffix('USDT')else[]
 else:
  for c in sorted(coins,key=len,reverse=True):
   if re.search(r'(?i)(?<![a-z0-9])\$?#?'+re.escape(c)+r'(?:/?usdt)?(?![a-z0-9])',t):found.append(c)
 directions=set()
 if re.search(r'(?i)\blong\b|лонг',t):directions.add('LONG')
 if re.search(r'(?i)\bshort\b|шорт',t):directions.add('SHORT')
 side=next(iter(directions))if len(directions)==1 else None
 past=bool(re.search(r'(?i)словили.{0,8}стоп|выбило.{0,12}стоп|закрыл[аи]?|закрыт|фиксировали|отработал|отработано|пошла отработка|забрали.{0,15}цел|взяли.{0,15}%|вышли.{0,10}плюс',t))
 entry=bool(re.search(r'(?i)захож|заходим|вхожу|входим|открываю|перезаход|пробую|взяла|беру|вход|твх|лонг|шорт|\bshort\b|\blong\b',t));conditional=bool(re.search(r'(?i)пока.{0,15}не.{0,6}открыва|ничего не открыва|если|при пробое|жду.{0,25}(?:тогда|точк)',t))
 pct=[number(x.replace('−','-'))if not x.startswith(('-','+','−'))else float(x.replace('−','-').replace(',','.')) for x in re.findall(r'([+−-]?\d+(?:[.,]\d+)?)\s*%',t)]
 update=bool(re.search(r'(?i)стоп|фиксир|фикс\b|закры|безубыт|б/у|\bбу\b|добрал|добавила|усреднил|сня[лт]|убрать стоп',t))
 fresh=bool(m)or bool(re.search(r'(?i)захож|заходим|вхожу|входим|открываю|перезахож|пробую|беру|взяла|набираюсь',t))or bool(re.search(r'\b[A-Z][A-Z0-9]{1,14}\s*[—–:-]?\s*(?:SHORT|LONG|short|long|шорт|лонг)\b',t))
 if len(found)==1 and side and entry and fresh and not past and not conditional:label='SIGNAL'
 elif update:label='UPDATE'
 elif pct or re.search(r'(?i)итог|отработк|результат|профит|прибыль',t):label='REPORT'
 else:label='OTHER'
 stop=re.search(r'(?i)стоп\s*[:=\-]?\s*\$?('+NUM+')',t);stop=number(stop[1])if stop else None
 grid=re.search(r'(?i)(?:сетк\w*|набор\w*|диапазон\w*|зона\s+входа|вход\w*\s+частями|твх|вход)\s*[^\n]{0,55}?('+NUM+r')\s*[$]?\s*[-–—]\s*('+NUM+r')',t)
 limit=re.search(r'(?i)(?:лимит\w*|твх)\s*[:=]?\s*\$?('+NUM+')',t)if re.search(r'(?i)лимит',t)else None
 events=[]
 if re.search(r'(?i)(?:снять|снял|убрать|убрал|снимаем).{0,15}стоп',t):events.append(dict(kind='REMOVE_STOP'))
 elif re.search(r'(?i)стоп.{0,30}(?:безубыт|б/у|\bбу\b|вход)|безубыт',t):events.append(dict(kind='MOVE_BE'))
 elif re.search(r'(?i)перен[ое]с|передвин|постав.{0,15}стоп',t)and stop is not None:events.append(dict(kind='MOVE_STOP',price=stop))
 if re.search(r'(?i)(?<![а-я])(?:закрыл(?:а|ся)?|закрываю|закрываем|фиксирую|фиксируем|выходим)(?![а-я])|словили.{0,8}стоп|выбило.{0,12}стоп|ушла.{0,8}стоп|закрылись.{0,8}стоп|меня выбило|закрыаю',t):
  f=re.search(r'(?i)(?:закрыл\w*|закрываю|фиксирую|фиксируем|закрываем)\s+(\d+(?:[.,]\d+)?)\s*%\s*(?:позици|объ[её]м|сделк|остат)',t)
  if re.search(r'(?i)половин',t):events.append(dict(kind='CLOSE_PART',fraction=.5))
  elif f and 0<number(f[1])<100:events.append(dict(kind='CLOSE_PART',fraction=number(f[1])/100))
  elif re.search(r'(?i)часть|частич|только объем|только объём|на который докуп',t)and not re.search(r'(?i)полностью|всю|остаток',t):events.append(dict(kind='UNRESOLVED_FRACTION'))
  else:events.append(dict(kind='CLOSE_ALL'))
 if label!='SIGNAL'and re.search(r'(?i)добрал|добор|добавила|усреднил|докупал|докупил',t):events.append(dict(kind='UNRESOLVED_DCA'))
 leverage=re.search(r'(?i)плечо\s*:\s*(\d+)',t)or re.search(r'(?i)(\d+)\s*[xх]\b',t)
 report_type='PROJECTION'if re.search(r'(?i)ожидаю|рассчитываю|может.{0,15}(?:процент|%)',t)and not past else 'PROMOTIONAL'if re.search(r'(?i)реферал|бонус|регистрац|обучен|розыгрыш|курирован',t)and not past else 'RESULT_OR_CLAIM'
 if report_type=='PROMOTIONAL'and not found and not past:label='OTHER'
 return dict(report_type=report_type,label=label,symbol=found[0]+'USDT'if len(found)==1 else None,coin_candidates=found,side=side,conditional=conditional,stop=stop,grid_mentioned=bool(re.search(r'(?i)сетк',t)),grid=[min(number(grid[1]),number(grid[2])),max(number(grid[1]),number(grid[2]))]if grid else None,explicit_limit=number(limit[1])if limit else None,claimed_percentages=pct if label!='SIGNAL'else[],actions=events,leverage=int(leverage[1])if leverage else None,classification_uncertain=len(found)>1 or conditional or len(directions)>1)

def build(rows):
 coins=discover(rows);records=[];signals=[];byid={};hashkey=lambda n:hashlib.sha256(('speculantka:'+str(n)).encode()).hexdigest()
 for r in sorted(rows,key=lambda r:(r['date'],r['id'])):
  d=parse(r,coins);a=dict(post_key=hashkey(r['id']),pub=r['date']*1000,edited=bool(r.get('edit_date')),edit_time_ms=r['edit_date']*1000 if r.get('edit_date')else None,media=r.get('media'),forwarded=r.get('fwd',False),reply_key=hashkey(r['reply_to'])if r.get('reply_to')else None,source_text_sha256=hashlib.sha256(r['text'].encode()).hexdigest(),**d);records.append(a);byid[r['id']]=a
  if a['label']=='SIGNAL'and not a['forwarded']:signals.append(dict(a,channel='SPECULANTKA',events=[],reported=False,report_keys=[]))
 bykey={s['post_key']:s for s in signals};unlinked=[]
 for r in records:
  if r['label']=='SIGNAL':continue
  if not r['actions']and not r['claimed_percentages']and r['label']!='REPORT':continue
  if r['forwarded']:r['link_status']='FORWARDED_ORIGIN_UNKNOWN';unlinked.append(r['post_key']);continue
  current=r.get('reply_key');root=None
  for k in range(8):
   if current in bykey:root=bykey[current];break
   parent=next((v for v in records if v['post_key']==current),None)if current else None
   if not parent:break
   current=parent.get('reply_key')
  if root and r['symbol']and r['symbol']!=root['symbol']:r['link_status']='REPLY_COIN_CONFLICT';unlinked.append(r['post_key']);continue
  c=[root]if root and 0<r['pub']-root['pub']<=7*86400000 else []
  if not current and not c:c=[s for s in signals if s['symbol']==r['symbol']and 0<r['pub']-s['pub']<=7*86400000 and (r['side']is None or s['side']==r['side'])]
  if len(c)==1:
   s=c[0];r['linked_signal']=s['post_key'];r['link_method']='REPLY_CHAIN'if root else 'UNIQUE_COIN_7D'
   for e in r['actions']:s['events'].append(dict(**e,effective_ms=r['pub']//60000*60000+60000,pub=r['pub'],post_key=r['post_key']))
   if (r['claimed_percentages']and r['report_type']=='RESULT_OR_CLAIM')or any(e['kind']=='CLOSE_ALL'for e in r['actions']):s['reported']=True;s['report_keys'].append(r['post_key'])
  else:r['link_status']='AMBIGUOUS_OR_UNLINKED';unlinked.append(r['post_key'])
 return dict(records=records,signals=signals,unlinked=unlinked,coins=sorted(coins))
