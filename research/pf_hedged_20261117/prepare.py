"""PF hedge public-source preparation only. No new hedge/short PnL."""
import os,json,gzip,hashlib,base64,urllib.request,urllib.parse,urllib.error,datetime as dt,concurrent.futures as cf,threading,re
from pathlib import Path
import numpy as np
from public_io import archive,covered,write,prices
H=3600000;M=60000;F=5*M;DAY=24*H;B=Path("research/pf_hedged_20261117")
ALIASES={"SHIB1000USDT":"1000SHIBUSDT","PUMPFUNUSDT":"PUMPUSDT","RAYDIUMUSDT":"RAYUSDT","SKYAI1USDT":"SKYAIUSDT"}
def github(path,ref):
 headers={"Authorization":"Bearer "+os.environ["GH_TOKEN"],"Accept":"application/vnd.github+json","User-Agent":"CAR-PF-hedge-offline"}
 def get(p):
  with urllib.request.urlopen(urllib.request.Request("https://api.github.com/repos/valikbabkin94-collab/car-research/"+p,headers=headers),timeout=90)as r:return json.load(r)
 d=get("contents/"+path+"?"+urllib.parse.urlencode({"ref":ref}))
 if not d.get("content"):d=get("git/blobs/"+d["sha"])
 return base64.b64decode(d["content"])
def months(a,b):
 t=dt.datetime.fromtimestamp(a/1000,dt.timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0)
 while t.timestamp()*1000<b:
  nxt=(t.replace(day=28)+dt.timedelta(days=4)).replace(day=1);yield t.strftime("%Y-%m"),int(t.timestamp()*1000),int(nxt.timestamp()*1000);t=nxt
def from_m1(path):
 if not path.exists():return None
 meta=path.with_suffix(".json")
 if not meta.exists()or json.load(meta.open()).get("parsed_sha256")!=hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError("M1_CACHE_SHA_MISMATCH")
 a=np.load(path,allow_pickle=False)["bars"]
 if not len(a):return np.empty((0,2))
 labels=(a[:,0]//F)*F;times,st,count=np.unique(labels,return_index=True,return_counts=True);en=st+count-1;good=(count==5)&(a[st,0]==times)&(a[en,0]==times+4*M)
 return np.column_stack([times[good]+F,a[en[good],4]])
def q5(sy,period,kind):
 cached=Path("work/market/m1")/(sy+"-"+period+".npz");a=from_m1(cached)
 if a is not None:return a,dict(source="VERIFIED_SAVED_M1_AGGREGATION",path=str(cached),parsed_sha256=hashlib.sha256(cached.read_bytes()).hexdigest())
 rows,r=archive(f"data/futures/um/{kind}/klines/{sy}/5m/{sy}-5m-{period}.zip");a=np.array([[int(x[0])+F,float(x[4])]for x in rows],float).reshape(-1,2)
 if len(a)and(np.any(a[:,0]%F)or np.any(~np.isfinite(a))or np.any(a[:,1]<=0)or np.any(np.diff(a[:,0])<=0)):raise ValueError("INVALID_REAL5M")
 return a,r
rest_blocked=False;rest_lock=threading.Lock()
def funding_rest(sy,a,b):
 global rest_blocked
 with rest_lock:
  if rest_blocked:raise ValueError("PUBLIC_REST_ALREADY_GEOBLOCKED")
 url="https://fapi.binance.com/fapi/v1/fundingRate?"+urllib.parse.urlencode(dict(symbol=sy,startTime=a,endTime=b-1,limit=1000))
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"CAR-offline-public-funding"}),timeout=25)as r:raw=r.read(2*1024*1024)
 except urllib.error.HTTPError as e:
  if e.code in[403,451]:
   with rest_lock:rest_blocked=True
  raise
 d=json.loads(raw)
 if not isinstance(d,list)or len(d)>=1000:raise ValueError("FUNDING_REST_RESPONSE_OR_PAGINATION")
 # REST lacks historical fundingInterval: infer from adjacent real payouts, do not assume8h.
 out=[]
 for i,r in enumerate(d):
  ts=int(r["fundingTime"]);interval=(ts-int(d[i-1]["fundingTime"]))/H if i else (int(d[1]["fundingTime"])-ts)/H if len(d)>1 else None
  if interval and 0.5<=interval<=8.01:out.append([ts,round(interval),float(r["fundingRate"])])
 return out,dict(source=url,sha256=hashlib.sha256(raw).hexdigest(),interval_source="Observed adjacent payout intervals, no forecast")
def main():
 shard=int(os.environ["DATA_SHARD"]);out=B/f"data_shard{shard}";out.mkdir(parents=True,exist_ok=True);dest=Path("assets");dest.mkdir(exist_ok=True);raw=github("inputs/pit/PIT_RANKS.npz","d3c667f95ee38ef8eae18214b14d94960846f5aa");Path("PIT_RANKS.npz").write_bytes(raw);z=np.load("PIT_RANKS.npz",allow_pickle=False);es=json.load(open("baseline/INPUTS.json"));a=min(e["entry_ms"]for e in es)-16*DAY;b=min(1794919920000,max(e["entry_ms"]for e in es)+11*DAY);rank=z["rank"][(z["decision_ms"]>=a)&(z["decision_ms"]<=b)];names=z["symbols"];ever={ALIASES.get(str(s),str(s))for s,use in zip(names,np.any((rank>0)&(rank<=200),axis=0))if use};shorts={e["symbol"]for e in es};syms=sorted(ever|shorts|{"BTCUSDT"});assigned=[s for i,s in enumerate(syms)if i%4==shard];meta=json.load((B/"MARKET_METADATA_SNAPSHOT_20261113.json").open());types={ALIASES.get(r["symbol"],r["symbol"]):r.get("symbolType","")for r in meta["records"]};saved={p.name.removesuffix(".json.gz"):p for p in Path("source").rglob("funding/*.json.gz")};receipts=[]
 write(out/"UNIVERSE.json",dict(total=len(syms),assigned=assigned,start=a,end=b,PIT_sha256=hashlib.sha256(raw).hexdigest(),aliases=ALIASES,short_inputs=len(es),no_PnL=True))
 def one(sy):
  src=[];errors=[];chunks=[];carry=Path("carrycoins")/(sy+".npz");firstspot=-1
  if carry.exists():
   cc=np.load(carry,allow_pickle=False);fund=cc["funding"].tolist();cov=cc["coverage"].tolist();sp=cc["spot"];firstspot=int(sp[:,0].min()+H)if len(sp)else-1;src.append(dict(kind="REUSED_CARRY_FUNDING_AND_SPOT_TYPE_PROOF",sha256=hashlib.sha256(carry.read_bytes()).hexdigest()))
  elif sy in saved:
   pp=saved[sy];d=json.loads(gzip.decompress(pp.read_bytes()));fund=[[r["ts"],r["interval_hours"],r["rate"]]for r in d["rows"]if r.get("interval_hours")];cov=d.get("coverage",[]);src.append(dict(kind="REUSED_SAVED_FUNDING",sha256=hashlib.sha256(pp.read_bytes()).hexdigest()))
  else:fund=[];cov=[]
  fdict={int(r[0]):r for r in fund}
  for mo,lo,hi in months(a,b):
   has=False
   if hi<=1793491200000:
    try:v,r=q5(sy,mo,"monthly");chunks.append(v);src.append(dict(kind="QUOTE5",**r));has=len(v)>0
    except Exception as e:errors.append(dict(month=mo,kind="QUOTE5",error=str(e)))
   else:
    t=max(lo,a//DAY*DAY)
    while t<min(hi,b):
     day=dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime("%Y-%m-%d")
     try:v,r=q5(sy,day,"daily");chunks.append(v);src.append(dict(kind="QUOTE5",**r));has|=len(v)>0
     except Exception as e:errors.append(dict(day=day,kind="QUOTE5",error=str(e)))
     t+=DAY
   if has and not covered(cov,lo,hi):
    try:
     rr,r=archive(f"data/futures/um/monthly/fundingRate/{sy}/{sy}-fundingRate-{mo}.zip");new=[[int(x[0]),float(x[1]),float(x[2])]for x in rr];src.append(dict(kind="FUNDING",**r));cov.append([lo,hi])
    except Exception as e:
     try:new,r=funding_rest(sy,max(lo,a),min(hi,b));src.append(dict(kind="FUNDING",**r));cov.append([max(lo,a),min(hi,b)])
     except Exception as ex:errors.append(dict(month=mo,kind="FUNDING",archive_error=str(e),rest_error=str(ex)));new=[]
    for row in new:fdict[int(row[0])]=row
  # Delisted instruments absent from current metadata are not silently excluded.
  type_status="CURRENT_STATIC_TYPE_LABEL_NOT_TRADABILITY_FILTER"if sy in types else"HISTORICAL_SPOT_TYPE_PROXY"if firstspot>0 else"UNKNOWN_TYPE_DATA_GAP";crypto=types.get(sy)not in["stock","ETF","commodity","forex"]if sy in types else firstspot>0
  if sy not in types and firstspot<0:
   # Public historical spot proof;1000... alias is classification only, no short-price remapping.
   candidates=[sy];m=re.match(r"^(1000(?:000)?)([A-Z].+USDT)$",sy)
   if m:candidates.append(m.group(2))
   for base in candidates:
    try:sp,r=prices(base,"2025-10","spot");firstspot=int(sp[:,0].min()+H)if len(sp)else-1;src.append(dict(kind="HISTORICAL_SPOT_TYPE_PROOF",**r))
    except Exception:continue
    if firstspot>0:crypto=True;type_status="HISTORICAL_SPOT_TYPE_PROXY";break
  q=np.concatenate(chunks)if chunks else np.empty((0,2));q=q[(q[:,0]>=a)&(q[:,0]<=b)];q=q[np.argsort(q[:,0])];_,ix=np.unique(q[:,0],return_index=True);q=q[np.sort(ix)];fund=np.array([v for ts,v in sorted(fdict.items())if a-24*H<=ts<=b],float).reshape(-1,3)
  path=dest/(sy+".npz");np.savez_compressed(path,quotes=q,funding=fund,coverage=np.array(cov,float).reshape(-1,2),crypto=np.array(int(crypto)),type_status=np.array(type_status),first_spot_proof=np.array(firstspot));return dict(symbol=sy,quotes=len(q),funding_rows=len(fund),crypto=bool(crypto),type_status=type_status,first_spot_proof=firstspot,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sources=src,errors=errors)
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for r in pool.map(one,assigned):receipts.append(r);print("PF_HEDGE_DATA",shard,len(receipts),"/",len(assigned),r["symbol"],r["quotes"],flush=True)
 write(out/"DATA_INVENTORY.json",receipts);write(out/"CHECKPOINT.json",dict(status="DATA_PREPARED_WITH_EXPLICIT_GAPS",shard=shard,assigned=len(assigned),quotes_available=sum(r["quotes"]>0 for r in receipts),no_PnL=True,code_sha=os.popen("git rev-parse HEAD").read().strip()))
if __name__=="__main__":main()
