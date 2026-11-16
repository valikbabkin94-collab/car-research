"""Second venue event proxy, never merged into exact Bybit results.
Reads prior first-page snapshots before fetching missing historical pages.
"""
import argparse,datetime as dt,gzip,json,re,sys
from pathlib import Path
import history as h

def articles(obj):
 found=[]
 if isinstance(obj,dict):
  if all(k in obj for k in ['code','title','releaseDate']):found.append(obj)
  else:
   for v in obj.values():found.extend(articles(v))
 elif isinstance(obj,list):
  for v in obj:found.extend(articles(v))
 return found

def plain(obj):
 if isinstance(obj,str):
  try:return plain(json.loads(obj))
  except (ValueError,TypeError):return re.sub('<[^>]+>',' ',obj)
 if isinstance(obj,dict):
  return ' '.join(plain(v) for k,v in obj.items() if k in ['text','children','content','body','title'])
 if isinstance(obj,list):return ' '.join(plain(v) for v in obj)
 return ''

DATE=re.compile(r'\b(20\d{2})-(\d{2})-(\d{2})\s+(?:at\s+)?(\d{2}):(\d{2})(?::\d{2})?\s*\(?UTC\)?',re.I)
def parse(record,detail):
 pub=record.get('releaseDate');text=' '.join((record['title']+' '+plain(detail.get('body',''))).split())
 if not isinstance(pub,(int,float)) or not h.START<=pub<h.END:return {'status':'REJECTED_PUBLICATION_WINDOW_OR_TIMESTAMP'}
 if not re.search(r'Futures',text,re.I) or not re.search(r'delist',text,re.I) or not re.search(r'perpetual',text,re.I):return {'status':'REJECTED_NOT_FUTURES_PERPETUAL_DELISTING'}
 if re.search(r'temporar|migrat',text,re.I):return {'status':'REJECTED_TEMPORARY_OR_MIGRATION'}
 symbols=sorted(set(re.findall(r'\b[A-Z0-9]{2,30}USDT\b',text)));deadlines=set()
 for m in DATE.finditer(text):
  context=text[max(0,m.start()-300):m.start()].lower()
  if not any(x in context for x in ['delist','close all positions','automatic settlement','cease trading']):continue
  try:deadlines.add(int(dt.datetime(*map(int,m.groups()),tzinfo=dt.timezone.utc).timestamp()*1000))
  except ValueError:continue
 if not symbols or len(deadlines)!=1:return dict(status='DATA_GAP_UNAMBIGUOUS_SYMBOL_OR_DELIST_TIME',symbols=symbols,deadline_candidates=len(deadlines))
 end=next(iter(deadlines))-h.DAY;first=(int(pub)//h.B+1)*h.B
 return dict(status='ELIGIBLE' if first<end and first<=pub+h.H else 'REJECTED_LATE_OR_TOO_CLOSE',symbols=symbols,publication_ms=int(pub),exit_deadline_ms=end//h.B*h.B,revision_status='CURRENT_SNAPSHOT_ORIGINAL_REVISION_UNAVAILABLE')

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default='results/s1-s3-history');a=p.parse_args();root=Path(a.out);http=h.HTTP(root);pages=[];events=[];errors=[];complete=False;seen=set();last=None
 for page in range(1,101):
  try:
   raw=None
   if page==1:
    for name in ['BINANCE_ANNOUNCEMENT_FALLBACK.json.gz','binance_announcement_proxy.gz']:
     path=root/name
     if path.exists():raw=gzip.decompress(path.read_bytes());break
   if raw is None:raw=http.get(f'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo={page}&pageSize=50&catalogId=161')
   sha=h.digest(raw)
   if sha==last:raise ValueError('REPEATED_PAGE_NO_COMPLETENESS_CERTIFICATE')
   last=sha;data=json.loads(raw);records=articles(data);pages.append(dict(page=page,sha256=sha,rows=len(records)))
   if not records:
    if str(data.get('code')) in ('000000','0'):complete=True
    else:errors.append(dict(reason='API_FAILURE_OR_UNKNOWN_EMPTY_SCHEMA',code=data.get('code')))
    break
   stamps=[]
   for r in records:
    pub=r.get('releaseDate')
    if not isinstance(pub,(int,float)):errors.append(dict(reason='MISSING_RELEASE_TIMESTAMP',article_code=r.get('code')));continue
    stamps.append(pub)
    if not h.START<=pub<h.END or r['code'] in seen:continue
    seen.add(r['code'])
    if not re.search(r'futures.*delist|delist.*futures',r['title'],re.I):continue
    try:
     code=r['code']
     if not re.fullmatch('[A-Za-z0-9]+',code):raise ValueError('INVALID_ARTICLE_CODE')
     rawdetail=http.get('https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode='+code);d=json.loads(rawdetail).get('data')
     if not isinstance(d,dict):raise ValueError('DETAIL_BODY_UNAVAILABLE')
     if d.get('releaseDate') not in (None,pub):raise ValueError('CONFLICTING_PUBLICATION_TIME')
     h.gzwrite(root/'binance_announcements'/(code+'.json.gz'),{'record':r,'detail':d,'source_sha256':h.digest(rawdetail)})
     events.append({'record':r,'parsed':parse(r,d),'url':'https://www.binance.com/en/support/announcement/'+code,'detail_sha256':h.digest(rawdetail)})
    except Exception as ex:errors.append(dict(article_code=r.get('code'),reason=type(ex).__name__+': '+str(ex)))
   if stamps and max(stamps)<h.START:complete=True;break
  except Exception as ex:errors.append(dict(page=page,reason=type(ex).__name__+': '+str(ex)));break
 trades=[];pairs=[];unique=set()
 for event in events:
  e=event['parsed']
  if e.get('status')!='ELIGIBLE':continue
  obs=e['publication_ms'];expiry=e['exit_deadline_ms']
  for sym in e['symbols']:
   if (sym,obs) in unique:continue
   unique.add((sym,obs))
   try:
    bars=h.window_bars(http,root,sym,obs,min(expiry+h.B,h.END));entry=next((x[1] for x in bars if x[0]==(obs//h.B+1)*h.B),None)
    if entry is None:raise ValueError('NO_ENTRY_PRICE')
    f=h.funding(http,root,sym);r=h.simulate(bars,obs,-1,entry*1.08,expiry,f,False);r.update(symbol=sym,source_url=event['url'],proxy='BINANCE_EVENT_AND_PRICES_NOT_BYBIT',original_revision_certified=False);trades.append(r)
    if r.get('status')=='CLOSED':
     c=h.simulate(bars,obs,1,entry*.92,expiry,f,False)
     if c.get('status')=='CLOSED':pairs.append([r['net_R'],c['net_R']])
   except Exception as ex:trades.append(dict(symbol=sym,signal_ms=obs,status='DATA_GAP_PRICE',reason=type(ex).__name__+': '+str(ex)))
 rng=h.random.Random(20261116);dist=[sum(p[rng.randrange(2)] for p in pairs) for _ in range(999)];actual=sum(a for a,b in pairs)
 result=dict(status='BINANCE_ONLY_DELIST_EVENT_PROXY_NOT_EXACT_BYBIT' if trades else 'INCONCLUSIVE_DATA_GAP_OR_NO_ELIGIBLE_EVENTS',tables=h.tables(trades),pages=pages,catalog_period_complete=complete,events=events,errors=errors,control=dict(kind='RANDOM_DIRECTION_SYMMETRIC_8_PERCENT_SAME_ENTRY_DEADLINE',paired_n=len(pairs),n=999,netR_distribution=dist,observed_short_R=actual,p_add_one=(1+sum(x>=actual for x in dist))/1000 if pairs else None))
 h.gzwrite(root/'S2_BINANCE_TRADES.json.gz',trades);h.write(root/'S2_BINANCE_RESULTS.json',result);print(json.dumps({k:v for k,v in result.items() if k in ['status','tables','catalog_period_complete']}))
if __name__=='__main__':main()
