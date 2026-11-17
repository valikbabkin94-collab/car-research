"""Cached public data, fixed plans and statistics for the parallel research jobs."""
import os,json,gzip,time,hashlib,datetime as dt,urllib.request,base64,collections,concurrent.futures as cf
from pathlib import Path
import numpy as np
from .engine import simulate,path_first,M,H
DAY=24*H;SEED=20261117

def load(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def gzip_json(p,d):Path(p).write_bytes(gzip.compress(json.dumps(d,allow_nan=False).encode(),mtime=0))
def stamp(t):return int(dt.datetime.fromisoformat(t.replace('Z','+00:00')).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
def fetch_github(path,ref,repo='valikbabkin94-collab/car-research'):
 headers={'Accept':'application/vnd.github+json','User-Agent':'CAR-offline-research'}
 if os.environ.get('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
 def get(p):
  with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+'/'+p,headers=headers),timeout=60)as r:return json.load(r)
 d=get('contents/'+path+'?ref='+ref)
 if not d.get('content'):d=get('git/blobs/'+d['sha'])
 return base64.b64decode(d['content'])

def bh(p):
 order=np.argsort(p);q=np.ones(len(p));last=1.
 for j in range(len(p)-1,-1,-1):i=order[j];last=min(last,p[i]*len(p)/(j+1));q[i]=last
 return q.tolist()
def paired_test(rows,controls,seed=SEED):
 blocks=collections.defaultdict(float);diff=[]
 for r,c in zip(rows,controls):
  values=np.array(c,float);valid=np.isfinite(values)
  if r[0]==1 and np.sum(valid)>=180:
   d=float(r[1]-np.mean(values[valid]));diff.append(d);blocks[int(r[31])//DAY]+=d
 if len(diff)<20 or len(blocks)<8:return dict(n=len(diff),excessR=float(sum(diff)),p=1.,coverage=len(diff)/max(1,sum(r[0]==1 for r in rows)))
 v=np.array(list(blocks.values()));rng=np.random.default_rng(seed);null=rng.choice([-1.,1.],size=(9999,len(v)))@v;p=(1+int(np.sum(null>=v.sum())))/10000
 return dict(n=len(diff),excessR=float(sum(diff)),p=p,coverage=len(diff)/max(1,sum(r[0]==1 for r in rows)))
def metrics(rows):
 valid=[r for r in rows if r[0]==1];a=np.array([r[1]for r in valid]);a=a[np.argsort([r[7]for r in valid],kind='stable')]if valid else a;net=float(a.sum());loss=float(-a[a<0].sum());eq=np.cumsum(a);top=float(np.sort(a)[-3:].sum())
 return dict(n=len(a),WR=float(100*np.mean(a>0))if len(a)else None,PF=float(a[a>0].sum()/loss)if loss else None,netR=net,USD_at_5risk=5*net,maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(a)else 0,top3_share=top/net if net>0 else None,netR_adverse=float(sum(r[1]-r[6]for r in valid)),status_counts=dict(collections.Counter(str(int(r[0]))for r in rows)),funding_unknown_n=sum(r[5]==0 for r in valid))

class Market:
 def __init__(self,asof,folder='work/market'):
  # Reuse the audited public loader verbatim from saved v1 artifact.
  import importlib.util
  path=Path('inputs_v1/vendor/market.py');spec=importlib.util.spec_from_file_location('car_public_market',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);self.io=mod;self.quotes=mod.Quotes(folder);self.fund=mod.Funding('source','work/funding');self.asof=asof;self.symbol=None;self.q=None;self.hour=None;self.receipts=[];self.funding_cache={}
 def get(self,symbol):
  if self.symbol==symbol:return self.q
  q=self.quotes.load(symbol);q=q[:np.searchsorted(q[:,0],self.asof-M,side='right')];self.quotes.cache={symbol:q};self.symbol=symbol;self.q=q;self.hour=self.hours(q);return q
 @staticmethod
 def hours(q):
  if not len(q):return np.empty((0,6))
  labels=(q[:,0]//H)*H;hs,start,count=np.unique(labels,return_index=True,return_counts=True);end=start+count-1;v=(count==60)&(q[start,0]==hs)&(q[end,0]==hs+H-M);hi=np.maximum.reduceat(q[:,2],start);lo=np.minimum.reduceat(q[:,3],start);z=np.column_stack([hs,q[start,1],hi,lo,q[end,4]])[v];atr=np.full(len(z),np.nan)
  if len(z)>=15:
   prev=np.r_[z[0,4],z[:-1,4]];tr=np.maximum(z[:,2]-z[:,3],np.maximum(abs(z[:,2]-prev),abs(z[:,3]-prev)));cs=np.r_[0,np.cumsum(tr)];ix=np.arange(14,len(z));ok=z[ix,0]-z[ix-14,0]==14*H;atr[ix[ok]]=(cs[ix[ok]+1]-cs[ix[ok]-13])/14
  return np.column_stack([z,atr])
 def atr(self,t):
  h=self.hour;j=np.searchsorted(h[:,0],t//H*H-H)if len(h)else 0
  return float(h[j,5])if j<len(h)and h[j,0]==t//H*H-H and np.isfinite(h[j,5])else None
 def funding(self,symbol):
  if symbol in self.funding_cache:return self.funding_cache[symbol]
  d=self.fund.get(symbol);v=sorted(d.get('rows',[]),key=lambda x:x['ts']);self.funding_cache[symbol]=(np.array([r['ts']for r in v],float),np.array([r['rate']for r in v],float),np.array(sorted(d.get('coverage',[])),float).reshape(-1,2));return self.funding_cache[symbol]
 def collect(self,windows,minutes=25):
  jobs=set();now=dt.datetime.fromtimestamp(self.asof/1000,dt.timezone.utc).strftime('%Y-%m')
  for sy,a,b in windows:
   for month in self.io.month_list(a,min(b,self.asof)):
    if month<now:jobs.add((sy,month,'monthly'))
    else:
     t=max(a//DAY*DAY,stamp(month+'-01'))
     while t<min(b,self.asof):jobs.add((sy,dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m-%d'),'daily'));t+=DAY
  jobs=sorted(jobs);deadline=time.monotonic()+minutes*60
  def one(j):
   try:return dict(symbol=j[0],period=j[1],status='OK',receipt=self.quotes.fetch(*j))
   except Exception as e:return dict(symbol=j[0],period=j[1],status='DATA_GAP',error=type(e).__name__+':'+str(e))
  with cf.ThreadPoolExecutor(max_workers=4)as pool:
   for k in range(0,len(jobs),4):
    if time.monotonic()>deadline:break
    self.receipts+=list(pool.map(one,jobs[k:k+4]))
    if k%200==0:print('SOURCE_WINDOWS',len(self.receipts),'/',len(jobs),flush=True)
  self.symbol=None;return dict(total=len(jobs),done=len(self.receipts),receipts=self.receipts)

def resolve_entry(q,e):
 t=e['entry_ms'];price=e['entry'];start=t//M*M;end=start+int(e.get('entry_window_ms',M));i=np.searchsorted(q[:,0],start);j=np.searchsorted(q[:,0],end)
 if not len(q)or j-i!=(end-start)//M:return None
 for k in range(i,j):
  if q[k,3]<=price<=q[k,2]:return int(q[k,0])if e.get('entry_window_ms',M)>M else t
 return None

def plan(code,e,market,mirror=False,unit=None):
 entry=e['entry'];side=e['side']*(-1 if mirror else 1);q=market.get(e['symbol']);pub=min(e['signal_ms'],e['entry_ms']);atr=market.atr(pub if code in ['X1','X2']else e['entry_ms']);p=np.array([.01,0,0,0,0,0,0,0,0,0,-1,72,0,1,0,unit or 0.],float)
 p[14]=float(not mirror and e.get('entry_type')in ['LIMIT','EXPLICIT_LIMIT','GRID_MEAN_LIMIT_PROXY'])
 if code in ['X1','X2','X4','X5']and atr is None:return None
 if code in ['X1','X2']:
  p[0]=1.5*atr/entry;p[1:4]=[p[0],2*p[0],3*p[0]];p[4:7]=[.5,.25,.25];p[7]=1;p[11]=24;p[12]=.5 if code=='X2'else 0.;p[8]=.0011 if code=='X2'else 0.
 elif code=='X3':p[1]=.015;p[4]=1
 elif code=='X4':p[1]=.01;p[4]=.5;p[9]=-atr/entry;p[10]=1
 elif code=='X5':p[0]=1.5*atr/entry;p[9]=-1.5*atr/entry;p[10]=0
 elif code=='X6':p[11]=4
 elif code=='X7':p[11]=24
 elif code=='X8':p[1]=.005;p[4]=1
 elif code=='X9':p[0]=.02;p[1]=.02;p[4]=1
 elif code.startswith('N'):
  p[0]=.08;p[1:4]=[.04,.08,.12];p[4:7]=[1/3]*3;p[11]=168
 elif code.startswith('WL')or code.startswith('WS'):
  p[0]=e['wick_risk_fraction'];p[1:3]=[p[0],2*p[0]];p[4:6]=[.5,.5];p[11]=4
 elif code.startswith('T'):
  take,stop,be=map(int,[code[1],code[3],code[5]]);p[0]=[.056,.12,0][stop];p[7]=[1,2,0][be];p[8]=.0011;p[4:7]=[1/3]*3
  if take in[0,1,2]:p[1:4]=[[.021,.042,.063],[.042,.063,.084],[.03,.06,.09]][take]
  elif take==3:p[1]=.063;p[4:7]=[1,0,0]
  elif take==4:p[1]=.042;p[4:7]=[.5,0,0];p[9]=.04;p[10]=1
  if take==5 or stop==2:
   end=pub//M*M;j=np.searchsorted(q[:,0],end);i=np.searchsorted(q[:,0],end-DAY)
   if j-i!=1440:return None
   peak=float(q[i:j,2].max());base=float(q[i,1])
   if peak<=base:return None
   if stop==2:p[0]=peak*1.01/entry-1
   if take==5:
    targets=peak-np.array([.38,.50,.62])*(peak-base);p[1:4]=1-targets/entry
  if e.get('actual_stop_fraction')is not None:p[0]=e['actual_stop_fraction']
 else:raise ValueError(code)
 return p

def model(market,e,code,mirror=False,unit=None):
 q=market.get(e['symbol']);t=resolve_entry(q,e)
 if t is None:r=np.zeros(40);r[0]=-2;r[1]=np.nan;r[31]=e['entry_ms'];r[32]=e['entry'];return r
 e=dict(e,entry_ms=t,signal_ms=min(e['signal_ms'],t));p=plan(code,e,market,mirror,unit)
 if p is None:r=np.zeros(40);r[0]=-5;r[1]=np.nan;r[31]=t;r[32]=e['entry'];return r
 ft,fr,cov=market.funding(e['symbol']);return simulate(q,t,e['entry'],e['side']*(-1 if mirror else 1),p,ft,fr,cov)

def controls(market,e,code,split,mirror=False,unit=None,repeats=200):
 t=e['entry_ms'];lo,mid,tail,hi=split;phase_lo,phase_hi=(lo,mid)if t<mid else(mid,tail)if t<tail else(tail,hi);a=max(phase_lo,t-7*DAY);b=min(phase_hi-72*H,t+7*DAY,market.asof-72*H);rng=np.random.default_rng(SEED+int(e['key'][:12],16));out=[]
 if b<a:return np.full(repeats,np.nan)
 times=rng.integers((a+M-1)//M,max((a+M-1)//M+1,b//M+1),size=repeats)*M;q=market.get(e['symbol'])
 for v in times:
  k=np.searchsorted(q[:,0],v)
  if k>=len(q)or q[k,0]!=v:out.append(np.nan);continue
  c=dict(e,entry_ms=int(v),signal_ms=int(v)-(e['entry_ms']-e['signal_ms']),entry=float(q[k,1]),entry_type='MARKET',entry_window_ms=M);r=model(market,c,code,mirror,unit);out.append(r[1]if r[0]==1 else np.nan)
 return np.array(out)

def splitting(es):
 lo=min(e['entry_ms']for e in es);hi=max(e['entry_ms']for e in es)+M;return lo,(lo+hi)//2,lo+int(.6*(hi-lo)),hi
def phase(e,sp,purge_h=72):
 return 'H1'if e['entry_ms']+purge_h*H<=sp[1]else'PURGE'if e['entry_ms']<sp[1]else'H2'
def finite(d):
 if isinstance(d,dict):return {k:finite(v)for k,v in d.items()}
 if isinstance(d,(list,tuple)):return [finite(v)for v in d]
 if isinstance(d,np.ndarray):return finite(d.tolist())
 if isinstance(d,(float,np.floating)):return float(d)if np.isfinite(d)else None
 if isinstance(d,np.integer):return int(d)
 return d
