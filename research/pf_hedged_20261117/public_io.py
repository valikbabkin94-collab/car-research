"""Public archive acquisition only, disjoint symbol shards; no PnL."""
import os,json,gzip,csv,io,zipfile,hashlib,urllib.request,urllib.parse,urllib.error,datetime as dt,time,concurrent.futures as cf
from pathlib import Path
import numpy as np
B=Path("research/pf_hedged_20261117");H=3600000;START=int(dt.datetime(2025,10,1,tzinfo=dt.timezone.utc).timestamp()*1000);END=int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
def write(p,d):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def get(url):
 host=urllib.parse.urlsplit(url).hostname
 assert host in["data.binance.vision","s3-ap-northeast-1.amazonaws.com"]
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"CAR-carry-offline"}),timeout=25)as r:return r.read(32*1024*1024)
  except urllib.error.HTTPError as e:
   if e.code not in[429,500,502,503,504]or attempt==2:raise
  except(OSError,TimeoutError):
   if attempt==2:raise
  time.sleep(2**attempt)
def catalogue(prefix):
 out=[];token=None;receipts=[]
 for page in range(30):
  args={"list-type":"2","prefix":prefix,"delimiter":"/"}
  if token:args["continuation-token"]=token
  u="https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?"+urllib.parse.urlencode(args);raw=get(u);root=__import__("xml.etree.ElementTree",fromlist=[""]).fromstring(raw);ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"};out += [x.text.rstrip("/").split("/")[-1]for x in root.findall("s:CommonPrefixes/s:Prefix",ns)];receipts.append(dict(url=u,sha256=hashlib.sha256(raw).hexdigest()));nxt=root.find("s:NextContinuationToken",ns)
  if nxt is None:return sorted(set(x for x in out if x.endswith("USDT"))),receipts
  token=nxt.text
 raise ValueError("CATALOGUE_PAGINATION_INCOMPLETE")
def archive(key):
 u="https://data.binance.vision/"+urllib.parse.quote(key,safe="/");expect=get(u+".CHECKSUM").decode().split()[0];raw=get(u)
 if hashlib.sha256(raw).hexdigest()!=expect:raise ValueError("ARCHIVE_CHECKSUM")
 z=zipfile.ZipFile(io.BytesIO(raw));assert len(z.namelist())==1
 rows=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding="utf-8-sig")))
 if rows and not rows[0][0].isdigit():rows=rows[1:]
 return rows,dict(key=key,sha256=expect,rows=len(rows))
def prices(sy,month,kind,frequency="monthly"):
 branch={"spot":"spot","perp":"futures/um","mark":"futures/um"}[kind];family="markPriceKlines"if kind=="mark"else"klines";key=f"data/{branch}/{frequency}/{family}/{sy}/1h/{sy}-1h-{month}.zip";rows,receipt=archive(key);a=np.array([[int(r[0]),float(r[1]),float(r[2]),float(r[3]),float(r[4])]for r in rows],float).reshape(-1,5)
 if len(a):
  if a[0,0]>1e14:a[:,0]/=1000
  if np.any(a[:,0]%H)or np.any(~np.isfinite(a))or np.any(a[:,1:]<=0)or np.any(a[:,3]>np.minimum(a[:,1],a[:,4]))or np.any(a[:,2]<np.maximum(a[:,1],a[:,4]))or np.any(np.diff(a[:,0])<=0):raise ValueError("BAD_REAL_OHLC")
 return a,receipt
def covered(cov,a,b):
 cursor=a
 for lo,hi in sorted(cov):
  if lo<=cursor<hi:cursor=max(cursor,hi)
 return cursor>=b
def months():
 t=dt.datetime(2025,10,1,tzinfo=dt.timezone.utc)
 while t.timestamp()*1000<END:
  nxt=(t.replace(day=28)+dt.timedelta(days=4)).replace(day=1);yield t.strftime("%Y-%m"),int(t.timestamp()*1000),int(nxt.timestamp()*1000);t=nxt
