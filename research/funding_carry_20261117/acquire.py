"""Public archive acquisition only, disjoint symbol shards; no PnL."""
import os,json,gzip,csv,io,zipfile,hashlib,urllib.request,urllib.parse,urllib.error,datetime as dt,time,concurrent.futures as cf
from pathlib import Path
import numpy as np
B=Path("research/funding_carry_20261117");H=3600000;START=int(dt.datetime(2025,10,1,tzinfo=dt.timezone.utc).timestamp()*1000);END=int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
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
def main():
 shard=int(os.environ["DATA_SHARD"]);dest=Path("work/coins");dest.mkdir(parents=True,exist_ok=True);out=B/f"data_shard{shard}";out.mkdir(parents=True,exist_ok=True);spot,sr=catalogue("data/spot/monthly/klines/");perp,pr=catalogue("data/futures/um/monthly/klines/");syms=sorted(set(spot)&set(perp));assigned=[s for i,s in enumerate(syms)if i%4==shard];existing={p.name.removesuffix(".json.gz"):p for p in Path("source").rglob("funding/*.json.gz")};records=[];deadline=time.monotonic()+75*60
 write(out/"UNIVERSE.json",dict(historical_spot=len(spot),historical_perp=len(perp),intersection=len(syms),assigned=assigned,receipts=sr+pr,exact_symbol_only=True))
 def one(sy):
  if time.monotonic()>deadline:return dict(symbol=sy,status="RESOURCE_CHECKPOINT")
  file=existing.get(sy);d=json.loads(gzip.decompress(file.read_bytes()))if file else dict(rows=[],coverage=[]);fund={int(r["ts"]):dict(ts=int(r["ts"]),interval_hours=r.get("interval_hours"),rate=float(r["rate"]))for r in d["rows"]};cov=d.get("coverage",[]);parts={k:[]for k in["spot","perp","mark"]};sources=[];errors=[]
  for mo,a,b in months():
   ok={}
   for kind in parts:
    try:v,r=prices(sy,mo,kind);parts[kind].append(v);sources.append(dict(kind=kind,**r));ok[kind]=len(v)>0
    except Exception as e:errors.append(dict(month=mo,kind=kind,error=type(e).__name__+":"+str(e)));ok[kind]=False
   if ok.get("perp")and ok.get("spot")and not covered(cov,a,b):
    try:
     rows,r=archive(f"data/futures/um/monthly/fundingRate/{sy}/{sy}-fundingRate-{mo}.zip")
     for row in rows:
      ts=int(row[0]);x=dict(ts=ts,interval_hours=float(row[1]),rate=float(row[2]))
      if ts in fund and abs(fund[ts]["rate"]-x["rate"])>1e-12:raise ValueError("CONFLICTING_FUNDING")
      fund[ts]=x
     cov.append([a,b]);sources.append(dict(kind="funding",**r))
    except Exception as e:errors.append(dict(month=mo,kind="funding",error=type(e).__name__+":"+str(e)))
  for kind in parts:
   try:v,r=prices(sy,"2026-11-01",kind,"daily");parts[kind].append(v[v[:,0]==END]);sources.append(dict(kind=kind,**r))
   except Exception as e:errors.append(dict(day="2026-11-01",kind=kind,error=str(e)))
  merged={}
  for kind,pp in parts.items():
   a=np.concatenate(pp)if pp else np.empty((0,5));a=a[(a[:,0]>=START)&(a[:,0]<=END)];a=a[np.argsort(a[:,0])];_,ix=np.unique(a[:,0],return_index=True);merged[kind]=a[np.sort(ix)]
  rr=[r for ts,r in sorted(fund.items())if START-24*H<=ts<END and r.get("interval_hours")and float(r["interval_hours"])>0]
  if len(merged["spot"])and len(merged["perp"])and rr:
   output=dest/(sy+".npz");np.savez_compressed(output,**merged,funding=np.array([[r["ts"],r["interval_hours"],r["rate"]]for r in rr],float),coverage=np.array(cov,float).reshape(-1,2));status="AVAILABLE";digest=hashlib.sha256(output.read_bytes()).hexdigest()
  else:status="DATA_GAP_NO_OVERLAP";digest=None
  return dict(symbol=sy,status=status,npz_sha256=digest,source_saved_funding_sha256=hashlib.sha256(file.read_bytes()).hexdigest()if file else None,funding_reused=file is not None,n_funding=len(rr),n_spot=len(merged["spot"]),n_perp=len(merged["perp"]),n_mark=len(merged["mark"]),sources=sources,errors=errors)
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for r in pool.map(one,assigned):records.append(r);print("DATA",shard,len(records),"/",len(assigned),r["symbol"],r["status"],flush=True)
 write(out/"DATA_INVENTORY.json",records);write(out/"CHECKPOINT.json",dict(status="DATA_COMPLETE_WITH_EXPLICIT_GAPS",shard=shard,assigned=len(assigned),available=sum(r["status"]=="AVAILABLE"for r in records),code_sha=os.popen("git rev-parse HEAD").read().strip(),PnL_calculated=False,live_changes=0))
if __name__=="__main__":main()
