"""Private snapshot -> causal numeric plans. No raw text is returned or published."""
import re,hashlib,unicodedata,datetime as dt,collections,json
M=60000;H=3600000;DAY=24*H
NUM=r'(?:\d+(?:[.,]\d+)?|[.,]\d+)'
SKIP={'USDT','USD','LONG','SHORT','TP','SL','BE','ENTRY','TARGET','TARGETS','STOP','LOSS','VIP','SIGNAL','COIN','BUY','SELL','ROI','PNL','RISK','RSI','EMA','HOLD','CROSS','BTCUSDT','SIGNALS','CRYPTO','TYPE','POSITION','DIRECTION','UPDATE','USDC','TPUSDT'}
def timestamp(v):
 if v is None or v is False:return None
 if isinstance(v,(int,float))and not isinstance(v,bool):return int(v*1000)if v<10**11 else int(v)
 if isinstance(v,str):
  z=dt.datetime.fromisoformat(v.replace('Z','+00:00'))
  if z.tzinfo is None:raise ValueError('TIMEZONE_UNKNOWN')
  return int(z.timestamp()*1000)
 return None

def norm(s):
 s=unicodedata.normalize('NFKC',str(s)).replace('\u200b','').replace('\ufe0f','').replace('\u20e3','');return s

def prices(s):
 s=re.sub(r'(?m)^\s*[1-9]\d?\s*(?:[):]\s*|[.]\s+)(?=\d|\$)','',s)
 if re.search(r'(?i)price|цен[аеыу]',s):s=re.split(r'(?i)price|цен[аеыу]',s,maxsplit=1)[-1]
 return [float(v.replace(',','.'))for v in re.findall(NUM,s)if float(v.replace(',','.'))>0]

HEADERS={'entry':r'entry(?:\s+(?:zone|range|targets?))?|entries|диапазон\s+входа|зона\s+входа|точк\w*\s+входа|вход|твх|price\s+between', 'stop':r'stop\s*(?:loss)?|\bsl\b|стоп(?:\s*лосс)?', 'tp':r'take[ -]?profit(?:\s+targets?)?|sell\s+targets?|targets?|\btp\s*\d*\b|тейк\w*|цел[ьи]\w*'}
STOP_SECTION=re.compile(r'(?i)risk|риск|leverage|плеч|published|join|subscribe|by:|итог|профит|profit:|loss\s*\(|loss\s*%')
def levels(t,kind):
 out=[];active=False
 for raw in t.splitlines():
  line=raw.strip()
  if kind=='tp'and re.search('(?i)'+HEADERS['entry'],line):continue
  m=re.search('(?i)'+HEADERS[kind],line)
  other=any(re.search('(?i)'+p,line)for k,p in HEADERS.items()if k!=kind)
  if m:
   active=True;s=line[m.end():].lstrip(' :=–—-')
   if not re.search(NUM,s)and m.start():s=line[:m.start()]
   if kind=='tp'and '%'in s:continue
   # End same-line section at another explicit label.
   for k,p in HEADERS.items():
    if k!=kind:s=re.split('(?i)'+p,s,maxsplit=1)[0]
   vals=prices(s)
   if kind=='stop':return vals[:1]
   out+=vals
  elif active:
   if other or STOP_SECTION.search(line):active=False;continue
   if not line:continue
   if re.search(NUM,line)and not ('%'in line or re.search(r'https?://|@[A-Za-z]',line)):out+=prices(line)
   elif len(line)>80:active=False
 return out

def parse_one(channel,r,known=()):
 t=norm(r.get('text',''));low=t.lower();pub=timestamp(r['date']);ed=timestamp(r.get('edit_date',r.get('edited')));av=max(pub,ed or pub);key=hashlib.sha256((channel+':'+str(r['id'])).encode()).hexdigest();sidewords=set()
 if re.search(r'(?i)\blong\b(?![- ]term)|лонг',t):sidewords.add('LONG')
 if re.search(r'(?i)\bshort\b(?![- ]term)|шорт',t):sidewords.add('SHORT')
 if not sidewords and re.search(r'(?i)(?:direction|position|type)\s*[:=]\s*buy\b|\bbuy\s+(?:#|\$)',t):sidewords.add('LONG')
 if not sidewords and re.search(r'(?i)(?:direction|position|type)\s*[:=]\s*sell\b|\bsell\s+(?:#|\$)',t):sidewords.add('SHORT')
 side=next(iter(sidewords))if len(sidewords)==1 else None
 coins=[];field=re.search(r'(?i)(?:\bcoin|\bsymbol|монета)\s*[:=]?\s*[#$]?([A-Z0-9]{1,18})(?:\s*[/_-]?\s*(?:USDT|USD))?',t)
 if field:coins=[field[1].upper().removesuffix('USDT')]
 else:
  coins=re.findall(r'(?i)(?<![a-z0-9])([A-Z0-9]{1,18})\s*[/_-]\s*(?:USDT|USD)\b',t)
  coins +=[x[:-4]for x in re.findall(r'(?<![A-Za-z0-9])([A-Z0-9]{2,20}USDT)\b',t)]
 if not coins:
  coins=re.findall(r'(?<!\w)[#$]([A-Z0-9]{1,15})(?![A-Za-z0-9])',t)
  if not coins:
   for x in re.findall(r'\b([A-Z0-9]{2,15})\b',t):
    if x in known and x not in SKIP:coins.append(x)
 coins=list(dict.fromkeys(x.upper().removesuffix('USDT')for x in coins if x.upper()not in SKIP));symbol=coins[0]+'USDT'if len(coins)==1 else None
 en=levels(t,'entry');sl=levels(t,'stop');tp=levels(t,'tp');sl=sl[0]if sl else None;zone=[min(en),max(en)]if en else None
 # English Klondike entry prose includes deposit/leverage, isolate first two price operands.
 m=re.search(r'(?i)price\s+between\s*\$?('+NUM+')\s*[-–—]\s*\$?('+NUM+')',t)
 if m:zone=sorted([float(m[1].replace(',','.')),float(m[2].replace(',','.'))])
 tp=list(dict.fromkeys(tp));tp=sorted(tp,reverse=side=='SHORT')if side else tp
 riskm=re.search(r'(?i)(?:риск|risk(?:\s+of\s+the\s+signal)?)\s*[:=]?\s*('+NUM+')\s*%',t);risk=float(riskm[1].replace(',','.'))if riskm else None
 levm=re.search(r'(?i)(?:leverage|плеч\w*)\s*[:=]?\s*(\d+)\s*[x×х]?|\bx(\d+)\b|(\d+)\s*[x×х]\b',t);lev=int(next(x for x in levm.groups()if x))if levm else None
 conditional=bool(re.search(r'(?i)\bif\b|если|жд[уё]м.{0,35}(?:подтверж|тогда)|при\s+пробое|возможн\w*\s+(?:лонг|шорт)',t));negative=bool(re.search(r'(?i)не\s+(?:беру|открываю|захожу)|not\s+(?:buy|sell|enter)',t));past=bool(re.search(r'(?i)закрыл|закрыла|вышел|вышла|closed|target\s*\d*.{0,5}(?:hit|reached|achieved)|\btp\s*\d*.{0,5}(?:hit|reached)|отработал|loss.{0,20}took this one out',t))
 claim=bool(re.search(r'(?i)(?:profit|прибыл|профит|roi|pnl)\s*[:+]?\s*'+NUM+r'\s*%|[+−-]\s*'+NUM+r'\s*%|(?:target|tp)\s*\d*.{0,8}(?:hit|reached|achieved)',t))
 claims=[float(v.replace('−','-').replace(',','.'))for v in re.findall(r'(?i)(?:profit|прибыл\w*|профит|roi|pnl)\s*[:=]?\s*([+−-]?'+NUM+r')\s*%',t)]
 if claim and not claims:claims=[float(v.replace('−','-').replace(',','.'))for v in re.findall(r'([+−-]'+NUM+r')\s*%',t)]
 card=bool(symbol and side and sl and tp);fresh=bool(re.search(r'(?i)\bentry\b|entries|диапазон\s+входа|зона\s+входа|вхожу|захожу|заходим|беру|открываю|набираю|\bopen\s+(?:long|short)|\bdirection\s*:',t))or bool(re.search(r'(?i)[#$][A-Z0-9]+.{0,40}(?:лонг|шорт|\bLONG\b|\bSHORT\b)',t))
 update=bool(re.search(r'(?i)вышел|вышла|закры|\bclos(?:e|ed|ing)\b|фиксир|фикс\b|безубыт|б/у|breakeven|cancel|отмен|добор|усредн|перенос.{0,12}стоп',t))
 if card and fresh and not past and not claim and not negative and not conditional:label='SIGNAL';kind='STRUCTURED'
 elif side and fresh and not past and not claim and not negative and not conditional:label='SIGNAL';kind='TEXT'
 elif claim or past:label='REPORT';kind=None
 elif update:label='UPDATE';kind=None
 else:label='OTHER';kind=None
 actions=[]
 if re.search(r'(?i)отмен.{0,15}(?:вход|сигнал|лимит)|cancel.{0,15}(?:entry|signal|order)',t):actions.append(dict(kind='CANCEL_PENDING'))
 if re.search(r'(?i)безубыт|б/у|break.?even|\bbe\b',t):actions.append(dict(kind='MOVE_BE'))
 elif sl and re.search(r'(?i)перен[ое]с|передвин|move.{0,8}stop',t):actions.append(dict(kind='MOVE_STOP',price=sl))
 if re.search(r'(?i)вышел|вышла|выходим|закрыл[аи]?|закрываю|закрываем|фиксирую|фиксируем|\bclose\s+(?:all|position|trade)|\bclosed\b',t):
  f=re.search(r'(?i)(?:закрыл\w*|фиксир\w*|close\w*)\s*('+NUM+r')\s*%\s*(?:позици|объ[её]м|position|volume)',t)
  if re.search(r'(?i)половин|half',t):actions.append(dict(kind='CLOSE_PART',fraction=.5))
  elif f and 0<float(f[1].replace(',','.'))<100:actions.append(dict(kind='CLOSE_PART',fraction=float(f[1].replace(',','.'))/100))
  elif re.search(r'(?i)часть|частич|partial',t)and not re.search(r'(?i)остаток|полностью|всю|all',t):actions.append(dict(kind='UNRESOLVED_FRACTION'))
  else:actions.append(dict(kind='CLOSE_ALL'))
 if re.search(r'(?i)добрал|добор|усреднил|докупил|добавил.{0,15}позици',t):actions.append(dict(kind='UNRESOLVED_DCA'))
 if re.search(r'(?i)(?:снят|убрал|убрать).{0,10}стоп|remove.{0,10}stop',t):actions.append(dict(kind='REMOVE_STOP'))
 flags=[]
 if len(coins)!=1:flags.append('MULTI_OR_UNRESOLVED_SYMBOL')
 if len(sidewords)>1:flags.append('MULTIPLE_DIRECTIONS')
 if isinstance(r.get('edited'),bool)and r.get('edited')and not ed:flags.append('EDIT_TIME_UNKNOWN')
 if ed and ed>pub:flags.append('LAST_SNAPSHOT_AT_EDIT_TIME')
 if r.get('fwd'):flags.append('FORWARDED_AUTHOR_UNKNOWN')
 if negative:flags.append('NEGATED')
 if conditional:flags.append('CONDITIONAL')
 if re.search(r'(?i)short.term|long.term|market analysis|price analysis',t)and not card:
  label='OTHER';kind=None;flags.append('ANALYTICS_NOT_FRESH_TRADE')
 return dict(post_key=key,channel=channel,pub=pub,available_ms=av,edited_delay_ms=max(0,av-pub),reply_key=hashlib.sha256((channel+':'+str(r['reply_to'])).encode()).hexdigest()if r.get('reply_to')else None,label=label,kind=kind,symbol=symbol,side=side,entry_zone=zone,stop=sl,targets=tp,risk_signature_pct=risk,leverage=lev,claims=claims,actions=actions,flags=flags,media=bool(r.get('media',r.get('photo'))),author_identity='SINGLE_SOURCE_CHANNEL'if channel=='OLEG'else'UNKNOWN_ANONYMIZED_CHANNEL_STREAM')

def build(channel,raw,known=()):
 records=[parse_one(channel,r,known)for r in raw];records.sort(key=lambda r:(r['available_ms'],r['post_key']));signals=[];bykey={};dedup=set();statuses=collections.Counter();linked=0
 for r in records:
  if r['label']!='SIGNAL':continue
  if r['symbol']is None or r['side']is None or any(f in r['flags']for f in['EDIT_TIME_UNKNOWN','MULTIPLE_DIRECTIONS','FORWARDED_AUTHOR_UNKNOWN']):r['parse_status']='AMBIGUOUS_SIGNAL';statuses[r['parse_status']]+=1;continue
  sig=(r['available_ms']//M,r['symbol'],r['side'],tuple(r['entry_zone']or[]),r['stop'],tuple(r['targets']))
  if sig in dedup:r['parse_status']='DUPLICATE_CANONICAL_SIGNAL';statuses[r['parse_status']]+=1;continue
  dedup.add(sig);r['parse_status']='CANDIDATE';statuses['CANDIDATE']+=1;v={k:r[k]for k in['post_key','channel','pub','available_ms','edited_delay_ms','kind','symbol','side','entry_zone','stop','targets','risk_signature_pct','leverage','flags','author_identity']};v.update(events=[],claims=[],parse_status='CANDIDATE');signals.append(v);bykey[r['post_key']]=v
 recby={r['post_key']:r for r in records};claims=[]
 for r in records:
  if r['label']=='SIGNAL'or not(r['actions']or r['claims']):continue
  root=None;key=r['reply_key'];seen=set()
  while key and key not in seen and len(seen)<20:
   seen.add(key)
   if key in bykey:root=bykey[key];break
   key=recby.get(key,{}).get('reply_key')
  candidates=[root]if root and 0<r['available_ms']-root['available_ms']<=7*DAY and(not r['symbol']or r['symbol']==root['symbol'])else[]
  if not candidates and r['symbol']:candidates=[s for s in signals if s['symbol']==r['symbol']and 0<r['available_ms']-s['available_ms']<=7*DAY and(not r['side']or s['side']==r['side'])]
  if len(candidates)==1:
   s=candidates[0];linked+=1;r['link_status']='REPLY_CHAIN'if root else'UNIQUE_COIN_7D';r['signal_key']=s['post_key']
   for e in r['actions']:s['events'].append(dict(e,effective_ms=((r['available_ms']+M-1)//M+1)*M,post_key=r['post_key'],link_status=r['link_status']))
   for n in r['claims']:
    c=dict(claim_key=r['post_key'],signal_key=s['post_key'],channel=channel,claim_ms=r['available_ms'],claimed_pct=n,reported_leverage=r['leverage']or s['leverage']);claims.append(c)
  else:r['link_status']='AMBIGUOUS_OR_UNLINKED';claims.extend(dict(claim_key=r['post_key'],signal_key=None,channel=channel,claim_ms=r['available_ms'],claimed_pct=n,reported_leverage=r['leverage'])for n in r['claims'])
 span=[timestamp(r['date'])for r in raw];stats=dict(channel=channel,posts=len(raw),labels=dict(collections.Counter(r['label']for r in records)),parse_statuses=dict(statuses),structured=sum(s['kind']=='STRUCTURED'for s in signals),text=sum(s['kind']=='TEXT'for s in signals),signals=len(signals),linked_update_posts=linked,signals_with_events=sum(bool(s['events'])for s in signals),claims=len(claims),unlinked_claims=sum(c['signal_key']is None for c in claims),media_posts=sum(r['media']for r in records),edited_delayed_posts=sum(r['edited_delay_ms']>0 for r in records),source_start=min(span),source_end=max(span),midpoint=(min(span)+max(span)+M)//2,last40=min(span)+int(.6*(max(span)+M-min(span))),snapshot_edit_history_available=False,author_identity_verified=channel=='OLEG')
 # Public classification records contain categories/keys only, no texts or numerical unlinked chatter.
 classification=[{k:r.get(k)for k in['post_key','label','kind','parse_status','link_status','signal_key','media','edited_delay_ms']}for r in records]
 return signals,claims,stats,classification
