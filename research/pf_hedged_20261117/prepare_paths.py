"""Reuse saved actual T0 paths; reconstruct only missing paths and previously unsaved control events."""
import os,json,gzip,hashlib,subprocess,importlib.util,datetime as dt,time
from pathlib import Path
import numpy as np
from parent_engine import simulate
from public_io import write
M=60000;H=3600000;DAY=24*H;SEED=20261117;ASOF=1794919920000;B=Path("research/pf_hedged_20261117")
spec=importlib.util.spec_from_file_location("saved_market","input_v1/vendor/market.py");module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def main():
 shard=int(os.environ["PATH_SHARD"]);out=B/f"paths_shard{shard}";out.mkdir(parents=True,exist_ok=True);entries=json.load(open("baseline/INPUTS.json"));sp=json.load(open("baseline/SELECTION_FROZEN.json"))["splits"];symbols=sorted({e["symbol"]for e in entries});owned={s for i,s in enumerate(symbols)if i%4==shard};entries=sorted([e for e in entries if e["symbol"]in owned],key=lambda e:(e["symbol"],e["entry_ms"]));source={};oldnull={}
 z=np.load("baseline/ALL_ACTUAL_EXITS.npz",allow_pickle=False)
 for key,variant,flip,r in zip(z["keys"],z["variants"],z["mirrors"],z["outcomes"]):
  if variant==b"T0S1B0"and not flip:source[key.decode()]=r
 z=np.load("baseline_h2/NEW_H2_ACTUAL_AND_CONTROL200.npz",allow_pickle=False)
 for key,variant,r,null in zip(z["keys"],z["variants"],z["outcomes"],z["control_netR"]):
  if variant==b"T0S1B0":source[key.decode()]=r;oldnull[key.decode()]=null
 quotes=module.Quotes("work/market");actual=[];control=[];keys=[];checks=[];current=None;q=None
 for n,e in enumerate(entries):
  sy=e["symbol"]
  if sy!=current:
   # Same immutable monthly/daily m1 archives as parent, fetched only if absent.
   es=[v for v in entries if v["symbol"]==sy];a=min(v["entry_ms"]for v in es)-8*DAY;b=min(ASOF,max(v["entry_ms"]for v in es)+11*DAY)
   for mo in module.month_list(a,b):
    try:
     if mo<"2026-11":quotes.fetch(sy,mo,"monthly")
     else:
      t=max(a//DAY*DAY,int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000))
      while t<b:
       try:quotes.fetch(sy,dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime("%Y-%m-%d"),"daily")
       except Exception:pass
       t+=DAY
    except Exception:pass
   quotes.cache={};q=quotes.load(sy);q=q[q[:,0]+M<=ASOF];current=sy
   fpath=Path("source/funding")/(sy+".json.gz");fd=json.loads(gzip.decompress(fpath.read_bytes()))if fpath.exists()else dict(rows=[],coverage=[]);ff=sorted(fd["rows"],key=lambda r:r["ts"]);ft=np.array([r["ts"]for r in ff],float);fr=np.array([r["rate"]for r in ff],float);cov=np.array(sorted(fd["coverage"]),float).reshape(-1,2)
  plan=np.array([.12,.021,.042,.063,1/3,1/3,1/3,1,.0011,0,-1,72,0,1,0,.056],float);r=source.get(e["key"])
  if r is None:
   t=e["entry_ms"];i=np.searchsorted(q[:,0],t);j=np.searchsorted(q[:,0],t+5*M);candidate=None
   if j-i==5:
    for k in range(i,j):
     if q[k,3]<=e["entry"]<=q[k,2]:candidate=int(q[k,0]);break
   if candidate is None:r=np.zeros(40);r[0]=-2;r[1]=np.nan
   else:
    p=plan.copy();p[14]=1;r=simulate(q,candidate,e["entry"],-1,p,ft,fr,cov)
  actual.append(r);keys.append(e["key"]);nulls=np.full((200,40),np.nan)
  if r[0]==1:
   t=e["entry_ms"];lo,mid,tail,hi=sp;pl,ph=(lo,mid)if t<mid else(mid,tail)if t<tail else(tail,hi);a=max(pl,t-7*DAY);b=min(ph-72*H,t+7*DAY,ASOF-72*H)
   if b>=a:
    rng=np.random.default_rng(SEED+int(e["key"][:12],16));times=rng.integers((a+M-1)//M,max((a+M-1)//M+1,b//M+1),200)*M
    for k,t0 in enumerate(times):
     ix=np.searchsorted(q[:,0],t0)
     if ix<len(q)and q[ix,0]==t0:nulls[k]=simulate(q,int(t0),float(q[ix,1]),-1,plan,ft,fr,cov)
   if e["key"]in oldnull:
    old=np.array(oldnull[e["key"]],float);good=(nulls[:,0]==1)&np.isfinite(old);mismatch=float(np.max(np.abs(nulls[good,1]-old[good])))if np.any(good)else None;checks.append(dict(key=e["key"],compared=int(np.sum(good)),max_old_netR_error=mismatch,finite_old=int(np.isfinite(old).sum()),finite_reconstructed=int(np.sum(nulls[:,0]==1))))
    if not np.array_equal(np.isfinite(old),nulls[:,0]==1):raise ValueError("PARENT_CONTROL_VALIDITY_MASK_MISMATCH:"+e["key"])
    if mismatch is not None and mismatch>5e-5:raise ValueError("PARENT_CONTROL_REPRODUCTION_MISMATCH:"+e["key"]+":"+str(mismatch))
  control.append(nulls)
  if n%40==0:print("FIXED_PATHS",shard,n,"/",len(entries),flush=True)
 np.savez_compressed(out/"PATHS.npz",keys=np.array(keys,dtype="S64"),actual=np.array(actual),controls=np.array(control));write(out/"INPUTS.json",entries);write(out/"SPLITS.json",sp);write(out/"PARENT_CONTROL_REPRODUCTION.json",checks);write(out/"CHECKPOINT.json",dict(status="FROZEN_PATHS_PREPARED",inputs=len(entries),valid_actual=sum(r[0]==1 for r in actual),parent_actual_paths_reused=sum(e["key"]in source for e in entries),actual_missing_paths_reconstructed=sum(e["key"]not in source for e in entries),control_event_paths_reconstructed_because_not_previously_saved=True,parameter_search=False,code_sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),live_changes=0))
if __name__=="__main__":main()
