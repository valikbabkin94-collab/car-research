"""Deterministic textual taxonomy; never infers missing trade prices or fills."""
import re,unicodedata
SIDE=re.compile(r'(?i)\b(long|short|лонг|шорт)\b(?!\s*[- ]?term)')
ADS=re.compile(r'(?i)subscribe|subscription|join\s+(?:our|vip)|premium\s+access|подписывай|доступ\s+в|реклама|оплат|промокод|vip\s+(?:group|membership)')
UPDATE=re.compile(r'(?i)словили\s+стоп|стоп|\bstop\b|\bsl\b|фиксир|фикс\b|закрыл|закрыла|закрываем|\bclos(?:e|ed|ing)\b|breakeven|безубыт|\bбу\b|б/у|добрал|добор|ушли\s+выше')
REPORT=re.compile(r'(?i)[+−-]\s*\d+(?:[.,]\d+)?\s*%|итоги|итог\s+недел|monthly\s+result|weekly\s+result|\btp\s*\d*\s*(?:hit|reached)')
PAST=re.compile(r'(?i)словили|закрыла|закрыл|\bclosed\b|фиксировал|reached|\bhit\b')
CONDITIONAL=re.compile(r'(?i)\bif\b|\bonce\b|если|возможно|рассматрива|при\s+пробое')
SKIP={'LONG','SHORT','USDT','USD','TP','SL','VIP','BUY','SELL','UPDATE','BTCUSDT','ENTRY','SIGNAL','FREE','DCA','NEW','NOW','COIN','DIRECTION','TARGET','TARGETS','STOP','LOSS','PROFIT','MARKET','AND','RANGE','CRYPTO','SIGNALS'}
def classify(text,known):
 text=unicodedata.normalize('NFKC',text)
 sides=SIDE.findall(text);side=None if not sides else 'LONG'if sides[0].lower()in ['long','лонг']else 'SHORT';coins=[]
 for x in re.findall(r'(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,14})(?:[/ _-]?(?:USDT|USD))?(?![A-Za-z0-9])',text):
  x=x[:-4]if x.endswith('USDT')else x
  if x in known and x not in SKIP and x not in coins:coins.append(x)
 for match in re.finditer(r'(?i)(?:#|\$)([A-Z][A-Z0-9]{1,14})\b|\b([A-Z][A-Z0-9]{1,14})\s*(?:/|[-_])\s*USDT\b',text):
  x=(match[1]or match[2]).upper()
  if x not in SKIP and x not in coins:coins.append(x)
 # Explicit upper-case coin immediately beside direction, even absent current catalog.
 for match in re.finditer(r'\b([A-Z][A-Z0-9]{1,14})\s*[—–:-]?\s*(?:SHORT|LONG|short|long|шорт|лонг)\b',text):
  x=match[1]
  if x not in SKIP and x not in coins:coins.append(x)
 symbol=coins[0]+'USDT'if len(coins)==1 else None;reason=[]
 direct=bool(re.search(r'\b[A-Z][A-Z0-9]{1,14}\s*[—–:-]?\s*(?:SHORT|LONG|short|long|шорт|лонг)\b|(?:\bShorting|\bLonging|\bLong|\bShort|\bLONG|\bSHORT|лонг|шорт)\s+[$#]?[A-Z][A-Z0-9]{1,14}\b',text))
 header=bool(re.search(r'(?i)\bentry\b|вход|\bcoin\b.{0,80}direction',text[:600]))
 narrative=bool(re.search(r'(?i)market analysis|price analysis|market recap|daily crypto|as long as|long.term|short.term',text))
 if ADS.search(text):label='OTHER';reason.append('PROMOTIONAL_OR_PAID_CONTEXT')
 elif (re.search(r'(?i)(?:profit|прибыль)\s*[:+]?\s*\d+(?:[.,]\d+)?\s*%|(?:target|tp)\s*\d*\s*(?:achieved|hit|reached)',text)):label='REPORT'
 elif REPORT.search(text)and(PAST.search(text)or not side or re.search(r'[+−-]\s*\d+(?:[.,]\d+)?\s*%',text)):label='REPORT'
 elif UPDATE.search(text)and(PAST.search(text)or not side):label='UPDATE'
 elif side and symbol and (direct or header)and not narrative:label='SIGNAL'
 elif UPDATE.search(text):label='UPDATE'
 elif REPORT.search(text):label='REPORT'
 else:label='OTHER'
 if len(set(x.lower()for x in sides))>1:reason.append('MULTIPLE_DIRECTIONS')
 if len(coins)>1:reason.append('MULTIPLE_COINS')
 if CONDITIONAL.search(text):reason.append('CONDITIONAL_SCENARIO')
 if side and not symbol:reason.append('SYMBOL_UNRESOLVED')
 return dict(label=label,symbol=symbol,side=side,flags=reason,executable_text_direction=label=='SIGNAL'and symbol is not None and not reason)
