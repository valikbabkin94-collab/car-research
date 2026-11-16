"""Public archive IO only. Verified market data; no account/order endpoints."""
import csv,gzip,hashlib,io,json,time,urllib.request,urllib.error,urllib.parse,zipfile,datetime as dt,threading
from pathlib import Path
import numpy as np
M=60000;H=3600000;DAY=24*H
BASE='https://data.binance.vision/'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2)+'\n');q.replace(p)
def gzread(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
class HTTP:
 def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.lock=threading.Lock();self.rest_blocked=False
 def get(self,url):
  host=urllib.parse.urlsplit(url).hostname
  if host not in ['data.binance.vision','fapi.binance.com']:raise ValueError('PUBLIC_HOST_DENIED')
  if host=='fapi.binance.com' and not urllib.parse.urlsplit(url).path.startswith('/fapi/v1/klines'):raise ValueError('PUBLIC_ROUTE_DENIED')
  for n in range(3):
   try:
    req=urllib.request.Request(urllib.parse.quote(url,safe=':/?=&%'),headers={'User-Agent':'CAR-offline-market-research'})
    with urllib.request.urlopen(req,timeout=25) as r:
     if urllib.parse.urlsplit(r.url).hostname!=host:raise ValueError('REDIRECT_DENIED')
     b=r.read(96*1024*1024+1)
     if len(b)>96*1024*1024:raise ValueError('SOURCE_SIZE_LIMIT')
    self.log(url,200,len(b),sha(b));return b
   except urllib.error.HTTPError as e:
    self.log(url,e.code,0,None)
    if e.code not in [429,500,502,503,504] or n==2:raise
   except (OSError,TimeoutError) as e:
    self.log(url,type(e).__name__,0,None)
    if n==2:raise
   time.sleep(2**n)
 def log(self,u,status,size,digest):
  with self.lock:
   with (self.root/'HTTP.jsonl').open('a') as f:f.write(json.dumps(dict(url=u,status=status,bytes=size,sha256=digest))+'\n')
 def archive(self,key):
  expected=self.get(BASE+key+'.CHECKSUM').decode().split()[0];raw=self.get(BASE+key)
  if sha(raw)!=expected:raise ValueError('SOURCE_CHECKSUM_FAILED')
  z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist()
  if len(names)!=1:raise ValueError('ZIP_MEMBERS')
  rows=list(csv.reader(io.TextIOWrapper(z.open(names[0]),encoding='utf-8-sig')))
  if rows and not rows[0][0].isdigit():rows=rows[1:]
  return rows,dict(key=key,source_sha256=expected,rows=len(rows))
def month_list(a,b):
 t=dt.datetime.fromtimestamp(a/1000,dt.timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0)
 while t.timestamp()*1000<b:
  yield t.strftime('%Y-%m');t=(t.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
def day_list(a,b):
 t=a//DAY*DAY
 while t<b:yield dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m-%d');t+=DAY
class Quotes:
 def __init__(self,root):self.root=Path(root);self.http=HTTP(self.root);self.cache={};self.errors=[]
 def fetch(self,symbol,period,kind='monthly'):
  directory=self.root/'m1';directory.mkdir(exist_ok=True);dest=directory/f'{symbol}-{period}.npz';receipt=dest.with_suffix('.json')
  if dest.exists() and receipt.exists():
   r=json.loads(receipt.read_text())
   if sha(dest.read_bytes())==r['parsed_sha256']:return r
   raise ValueError('CORRUPT_LOCAL_QUOTE_CACHE')
  key=f'data/futures/um/{kind}/klines/{symbol}/1m/{symbol}-1m-{period}.zip';rows,r=self.http.archive(key)
  arr=np.asarray([[int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4])] for x in rows],dtype=np.float64)
  if arr.size==0:arr=np.empty((0,5))
  if len(arr) and (np.any(arr[:,0]%M) or np.any(arr[:,0]>10**14) or np.any(~np.isfinite(arr)) or np.any(arr[:,1:]<=0) or np.any(arr[:,3]>np.minimum(arr[:,1],arr[:,4])) or np.any(arr[:,2]<np.maximum(arr[:,1],arr[:,4]))):raise ValueError('INVALID_REAL_M1')
  if len(arr) and (len(np.unique(arr[:,0]))!=len(arr) or np.any(np.diff(arr[:,0])<=0)):raise ValueError('UNSORTED_SOURCE')
  np.savez_compressed(dest,bars=arr);r.update(parsed_sha256=sha(dest.read_bytes()),bar_ms=M,first_ms=int(arr[0,0]) if len(arr) else None,last_ms=int(arr[-1,0]) if len(arr) else None);save(receipt,r);return r
 def load(self,symbol):
  if symbol in self.cache:return self.cache[symbol]
  parts=[]
  for p in sorted((self.root/'m1').glob(symbol+'-*.npz')):
   receipt=p.with_suffix('.json')
   if not receipt.exists() or json.loads(receipt.read_text()).get('parsed_sha256')!=sha(p.read_bytes()):raise ValueError('QUOTE_CACHE_SHA_MISMATCH')
   parts.append(np.load(p,allow_pickle=False)['bars'])
  if not parts:return np.empty((0,5))
  arr=np.concatenate(parts);arr=arr[np.argsort(arr[:,0],kind='stable')];_,index=np.unique(arr[:,0],return_index=True);arr=arr[np.sort(index)]
  if len(self.cache)>=6:self.cache.pop(next(iter(self.cache)))
  self.cache[symbol]=arr;return arr
 def probe_rest(self,symbol,a,b):
  # Only unfinished current-day public candles. Never private exchange methods.
  if self.http.rest_blocked:return None
  try:
   raw=self.http.get('https://fapi.binance.com/fapi/v1/klines?'+urllib.parse.urlencode(dict(symbol=symbol,interval='1m',startTime=a,endTime=b-1,limit=1500)));data=json.loads(raw)
   if not isinstance(data,list):raise ValueError('REST_RESPONSE')
   arr=np.array([[int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4])] for x in data if int(x[0])+M<=b],dtype=float)
   if not len(arr):return None
   p=self.root/'m1'/f'{symbol}-rest-{a}.npz';p.parent.mkdir(exist_ok=True);np.savez_compressed(p,bars=arr);save(p.with_suffix('.json'),dict(source='PUBLIC_KLINES_REST_CURRENT_DAY_ONLY',source_sha256=sha(raw),parsed_sha256=sha(p.read_bytes()),first_ms=int(arr[0,0]),last_ms=int(arr[-1,0])));self.cache.pop(symbol,None);return arr
  except urllib.error.HTTPError as e:
   if e.code in [403,451]:self.http.rest_blocked=True
   self.errors.append(dict(symbol=symbol,kind='REST_UNAVAILABLE',error='HTTP_'+str(e.code)));return None
  except Exception as e:self.errors.append(dict(symbol=symbol,kind='REST_UNAVAILABLE',error=type(e).__name__+': '+str(e)));return None
class Funding:
 def __init__(self,root,quote_root):self.root=Path(root);self.http=HTTP(quote_root);self.cache={}
 def get(self,symbol):
  if symbol in self.cache:return self.cache[symbol]
  p=self.root/'funding'/(symbol+'.json.gz');d=gzread(p) if p.exists() else dict(symbol=symbol,rows=[],coverage=[],errors=[])
  self.cache[symbol]=d;return d
 def extend_month(self,symbol,month,complete_month=False):
  d=self.get(symbol);rows,r=self.http.archive(f'data/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip');merged={int(x['ts']):x for x in d['rows']}
  for row in rows:merged[int(row[0])]=dict(ts=int(row[0]),interval_hours=float(row[1]),rate=float(row[2]))
  d['rows']=[merged[t] for t in sorted(merged)];start=int(dt.datetime.fromisoformat(month+'-01').replace(tzinfo=dt.timezone.utc).timestamp()*1000)
  if complete_month:
   t=dt.datetime.fromtimestamp(start/1000,dt.timezone.utc);end=int((t.replace(day=28)+dt.timedelta(days=4)).replace(day=1).timestamp()*1000)
  else:end=max((int(x[0]) for x in rows),default=start)
  d.setdefault('coverage',[]).append([start,end]);d.setdefault('sources',[]).append(r);p=self.root/'funding'/(symbol+'.json.gz');p.parent.mkdir(exist_ok=True);p.write_bytes(gzip.compress(json.dumps(d).encode(),mtime=0));return d
 def known(self,symbol,a,b):
  cursor=a
  for lo,hi in sorted(self.get(symbol).get('coverage',[])):
   if lo<=cursor<hi:cursor=max(cursor,hi)
  return cursor>=b
 def latest(self,symbol,t):
  rows=[x for x in self.get(symbol)['rows'] if int(x['ts'])<t and x.get('interval_hours') is not None]
  if not rows:return None
  r=max(rows,key=lambda x:int(x['ts']));hours=float(r['interval_hours'])
  if hours<=0 or t-int(r['ts'])>hours*H:return None
  return float(r['rate'])*8/hours
 def cash(self,symbol,r,quotes):
  if r['status']!='CLOSED' or not self.known(symbol,r['entry_ms'],r['exit_ms']):return None
  total=0.;side=r['side'];a=r['entry_ms'];b=r['exit_ms'];events=r['events'];ts=quotes[:,0]
  for pay in self.get(symbol)['rows']:
   t=int(pay['ts'])
   if not a<t<=b:continue
   k=int(np.searchsorted(ts,t-M,side='right'))-1
   if k<0 or quotes[k,0]+M>t or t-(quotes[k,0]+M)>M:return None
   rate=float(pay['rate']);pays=side*rate>0
   remain=1-sum(e['fraction'] for e in events if (e['time_ms']<t if e['kind']=='TIME' else e['time_ms']<=t if pays else e['bar_ms']<t))
   total+=-side*max(0,remain)*rate*quotes[k,4]/r['entry']/r['risk_denominator']
  return total
