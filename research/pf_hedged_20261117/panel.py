"""Verified5m hedge panel, historical ranks, closed-price pump cohort and funding prefixes."""
import json,hashlib,io
from pathlib import Path
import numpy as np
from prepare import github,ALIASES
M=60000;F=5*M;H=3600000;DAY=24*H
class Data:
 def __init__(self,folder="assets",metadata="metadata"):
  files=sorted(Path(folder).glob("*.npz"));manifest={}
  for p in Path(metadata).rglob("DATA_INVENTORY.json"):
   for r in json.load(p.open()):manifest[r["symbol"]]=r["sha256"]
  assert files and manifest,"NO_VERIFIED_HEDGE_INPUTS"
  bounds=[json.load(p.open())for p in Path(metadata).rglob("UNIVERSE.json")];self.start=min(x["start"]for x in bounds)//F*F;self.end=max(x["end"]for x in bounds)//F*F;self.times=np.arange(self.start,self.end+F,F,dtype=np.int64);T=len(self.times);n=len(files);self.sy=[p.stem for p in files];self.index={s:i for i,s in enumerate(self.sy)};self.q=np.full((n,T),np.nan);self.fc=np.zeros((n,T));self.unknown=np.zeros((n,T),dtype=np.int32);self.missing=np.zeros((n,T),dtype=np.int32);self.lastpump=np.full((n,T),-1,dtype=np.int32);self.crypto=np.zeros(n,bool);self.type_status=[];self.rawfund=[];self.hashes={};self.baskets={}
  for j,p in enumerate(files):
   digest=hashlib.sha256(p.read_bytes()).hexdigest();assert manifest.get(p.stem)==digest,"ASSET_SHA_MISMATCH";self.hashes[p.stem]=digest;z=np.load(p,allow_pickle=False);q=z["quotes"];ix=((q[:,0]-self.start)//F).astype(int);ok=(ix>=0)&(ix<T);self.q[j,ix[ok]]=q[ok,1];self.crypto[j]=bool(z["crypto"]);self.type_status.append(str(z["type_status"]));f=z["funding"];known=np.zeros(T,bool)
   for lo,hi in z["coverage"]:known|=(self.times>=lo)&(self.times+F<=hi)
   self.unknown[j]=np.r_[0,np.cumsum(~known[:-1],dtype=np.int32)];self.missing[j]=np.cumsum(~np.isfinite(self.q[j]),dtype=np.int32)
   event=np.zeros(T,bool);event[288:]=np.isfinite(self.q[j,288:])&np.isfinite(self.q[j,:-288])&(self.q[j,288:]/self.q[j,:-288]>=1.15);self.lastpump[j]=np.maximum.accumulate(np.where(event,np.arange(T,dtype=np.int32),-1))
   ft=f[:,0]if len(f)else np.empty(0);rate=f[:,2]if len(f)else np.empty(0);qi=np.searchsorted(q[:,0],ft,side="right")-1 if len(q)else np.full(len(ft),-1);good=qi>=0;values=np.zeros(len(ft));bad=np.ones(len(ft),bool)
   if len(q):
    ids=np.maximum(qi,0);good&=(ft-q[ids,0])<=F;values[good]=rate[good]*q[ids[good],1];bad[good]=False
   markfile=Path("carrymarks")/(p.stem+".npz")
   if markfile.exists()and len(ft):
    mq=np.load(markfile,allow_pickle=False)["mark"];mi=np.searchsorted(mq[:,0],ft,side="right")-1 if len(mq)else np.full(len(ft),-1);mg=mi>=0
    if len(mq):
     ids=np.maximum(mi,0);mg&=(ft-mq[ids,0])<H;values[mg]=rate[mg]*mq[ids[mg],1];bad[mg]=False
   at=np.searchsorted(self.times+1000,ft,side="left");valid=(at>=0)&(at<T);cash=np.zeros(T);np.add.at(cash,at[valid],values[valid]);self.fc[j]=np.cumsum(cash);self.rawfund.append((ft,np.r_[0,np.cumsum(np.where(values>0,values,0))],np.r_[0,np.cumsum(np.where(values<0,values,0))],np.r_[0,np.cumsum(bad,dtype=np.int32)]))
  raw=github("inputs/pit/PIT_RANKS.npz","d3c667f95ee38ef8eae18214b14d94960846f5aa");z=np.load(io.BytesIO(raw),allow_pickle=False);self.pt=z["decision_ms"];self.ranks=z["rank"];self.ps=[ALIASES.get(str(s),str(s))for s in z["symbols"]]
 def ix(self,t):return int((int(t)-self.start)//F)
 def basket(self,t,kind,exclude):
  if kind=="BTC":return[self.index["BTCUSDT"]]if"BTCUSDT"in self.index else None
  key=(int(t),kind)
  if key not in self.baskets:
   row=np.searchsorted(self.pt,t,side="left")-1
   if row<0 or t-self.pt[row]>24*H:self.baskets[key]=None
   else:
    ti=np.searchsorted(self.times,t,side="left")-1;ranked=[];seen=set()
    for k in np.argsort(np.where(self.ranks[row]>0,self.ranks[row],65535)):
     rank=int(self.ranks[row,k]);s=self.ps[k]
     if not rank or s in seen or s not in self.index:continue
     seen.add(s);j=self.index[s]
     if not self.crypto[j]or ti<0 or not np.isfinite(self.q[j,ti]):continue
     if kind=="ALT":
      if s not in["BTCUSDT","ETHUSDT"]:ranked.append((rank,j))
      if len(ranked)>=50:break
     elif rank<=200 and self.lastpump[j,ti]>=0 and self.lastpump[j,ti]>=ti-7*DAY//F:ranked.append((-int(self.lastpump[j,ti]),rank,j))
    self.baskets[key]=([j for rank,j in ranked]if len(ranked)==50 else None)if kind=="ALT"else[x[-1]for x in sorted(ranked)[:11]]
  got=self.baskets[key]
  if got is None:return None
  if kind=="ALT":return got
  exclude=ALIASES.get(exclude,exclude);got=[j for j in got if self.sy[j]!=exclude][:10];return got if len(got)>=3 else[]
