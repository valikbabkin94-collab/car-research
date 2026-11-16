"""Public archive-only research, no bot imports, credentials or order interfaces."""
import argparse, bisect, concurrent.futures as cf, csv, datetime as dt, gzip, hashlib, io, json, math, random, re, statistics, threading, time, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile
from pathlib import Path
import numpy as np
H=3600000; B=300000; DAY=24*H
START=int(dt.datetime(2026,8,1,tzinfo=dt.timezone.utc).timestamp()*1000)
END=int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
WARM=int(dt.datetime(2026,7,24,tzinfo=dt.timezone.utc).timestamp()*1000)
BASE='https://data.binance.vision/'; S3='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
NS={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
def digest(b):return hashlib.sha256(b).hexdigest()
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2)+'\n');q.replace(p)
def gzwrite(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(d,ensure_ascii=False,allow_nan=False).encode(),mtime=0))
def gzread(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
class HTTP:
 def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.lock=threading.Lock()
 def get(self,url):
  # Host allowlist applies to research public GET only. No exchange account/trade API.
  host=urllib.parse.urlsplit(url).hostname
  if host not in ('data.binance.vision','s3-ap-northeast-1.amazonaws.com','api.bybit.com','announcements.bybit.com','www.binance.com'):raise ValueError('UNAPPROVED_PUBLIC_HOST')
  for attempt in range(3):
   try:
    req=urllib.request.Request(urllib.parse.quote(url,safe=':/?=&%'),headers={'User-Agent':'CAR-public-archive-research'})
    with urllib.request.urlopen(req,timeout=30) as r:
     if urllib.parse.urlsplit(r.url).hostname!=host:raise ValueError('REDIRECT_HOST_CHANGED')
     raw=r.read(32*1024*1024+1)
     if len(raw)>32*1024*1024:raise ValueError('SOURCE_TOO_LARGE')
    self.log(url,200,len(raw),digest(raw));return raw
   except urllib.error.HTTPError as e:
    self.log(url,e.code,0,None)
    if e.code not in (429,500,502,503,504) or attempt==2:raise
   except (TimeoutError,OSError) as e:
    self.log(url,type(e).__name__,0,None)
    if attempt==2:raise
   time.sleep(2**attempt)
 def log(self,url,status,size,sha):
  with self.lock:
   with (self.root/'HTTP.jsonl').open('a') as f:f.write(json.dumps(dict(url=url,status=status,bytes=size,sha256=sha))+'\n')

def catalog(http):
 prefix='data/futures/um/monthly/klines/';marker='';symbols=[];pages=[]
 for _ in range(20):
  args={'prefix':prefix,'delimiter':'/','max-keys':1000}
  if marker:args['marker']=marker
  raw=http.get(S3+'?'+urllib.parse.urlencode(args));x=ET.fromstring(raw);pages.append(digest(raw))
  for e in x.findall('s:CommonPrefixes',NS):
   sym=e.findtext('s:Prefix',namespaces=NS).rstrip('/').split('/')[-1]
   if sym.endswith('USDT') and not any(c in sym for c in '/\\'):symbols.append(sym)
  if x.findtext('s:IsTruncated',namespaces=NS)!='true':return sorted(set(symbols)),pages
  marker=x.findtext('s:NextMarker',namespaces=NS)
  if not marker:raise ValueError('CATALOG_TRUNCATED_WITHOUT_CURSOR')
 raise ValueError('CATALOG_PAGE_BUDGET')

def archive(http,key):
 check=http.get(BASE+key+'.CHECKSUM').decode().split()[0];raw=http.get(BASE+key)
 if digest(raw)!=check:raise ValueError('CHECKSUM_MISMATCH')
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist()
 if len(names)!=1:raise ValueError('UNEXPECTED_ZIP_MEMBERS')
 rows=list(csv.reader(io.TextIOWrapper(z.open(names[0]),encoding='utf-8-sig')))
 if rows and not rows[0][0].isdigit():rows=rows[1:]
 return rows,dict(key=key,source_sha256=check,rows=len(rows))

def candle_month(http,symbol,month,interval):
 key=f'data/futures/um/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip'
 rows,receipt=archive(http,key);bars=[];step={'1h':H,'5m':B}[interval]
 for r in rows:
  t=int(r[0]);o,h,l,c,v,q=map(float,[r[1],r[2],r[3],r[4],r[5],r[7]])
  if t>10**14 or t%step or not all(math.isfinite(n) for n in [o,h,l,c,v,q]) or min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c):raise ValueError('INVALID_SOURCE_CANDLE')
  bars.append([t,o,h,l,c,v,q])
 if len({r[0] for r in bars})!=len(bars):raise ValueError('DUPLICATE_SOURCE_CANDLE')
 return bars,receipt

def probe(root):
 http=HTTP(root);d={'stage':'SOURCE_AUDIT','pnl_runs':0,'start':START,'end':END,'sources':{}}
 requests={
 'binance_h1_checksum':BASE+'data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2026-10.zip.CHECKSUM',
 'binance_funding_checksum':BASE+'data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-10.zip.CHECKSUM',
 'bybit_announcements':'https://api.bybit.com/v5/announcements/index?locale=en-US&type=delistings&page=1&limit=50',
 'binance_announcement_proxy':'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50&catalogId=161'}
 for name,url in requests.items():
  try:
   raw=http.get(url);d['sources'][name]={'status':'FETCHED','bytes':len(raw),'sha256':digest(raw)}
   (Path(root)/(name+'.gz')).write_bytes(gzip.compress(raw,mtime=0))
  except Exception as e:d['sources'][name]={'status':'FETCH_FAILED','error':type(e).__name__+': '+str(e)}
 try:
  symbols,pages=catalog(http);d['symbols']=symbols;d['catalog_page_sha256']=pages;d['catalog_status']='COMPLETE_CURRENT_ARCHIVE_INDEX_INCLUDES_DELISTED'
 except Exception as e:d['catalog_status']='DATA_GAP';d['catalog_error']=str(e)
 write(Path(root)/'SOURCE_AUDIT.json',d);print(json.dumps({k:v for k,v in d.items() if k!='symbols'}));return d

def collect_h1(root,audit):
 root=Path(root);http=HTTP(root);a=json.loads(Path(audit).read_text());symbols=a.get('symbols',[])
 if not symbols:raise ValueError('No complete archive catalogue')
 out=root/'h1';out.mkdir(exist_ok=True);done=[];lock=threading.Lock()
 def one(sym):
  target=out/(sym+'.json.gz')
  if target.exists():return gzread(target)
  bars=[];sources=[];errors=[];absent=[]
  for month in ['2026-07','2026-08','2026-09','2026-10']:
   try:
    b,r=candle_month(http,sym,month,'1h');bars.extend(x for x in b if WARM<=x[0]<END);sources.append(r)
   except urllib.error.HTTPError as e:
    if e.code==404:absent.append(month)
    else:errors.append({'month':month,'error':'HTTP_'+str(e.code)})
   except Exception as e:errors.append({'month':month,'error':type(e).__name__+': '+str(e)})
  d=dict(symbol=sym,bars=sorted(bars),sources=sources,absent_months=absent,errors=errors);gzwrite(target,d)
  return d
 started=time.monotonic()
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  for offset in range(0,len(symbols),4):
   if time.monotonic()-started>3000:raise RuntimeError('BOUNDED_COLLECTION_PAUSE_RESUME_FROM_ARTIFACT')
   for d in pool.map(one,symbols[offset:offset+4]):
    done.append(dict(symbol=d['symbol'],rows=len(d['bars']),errors=d['errors'],absent_months=d['absent_months']))
    write(root/'COLLECTION_CHECKPOINT.json',{'completed':len(done),'total':len(symbols),'symbols':done,'pnl_runs':0})
   if len(done)%100==0:print('H1 completed',len(done),'/',len(symbols),flush=True)
 write(root/'H1_MANIFEST.json',{'archive_catalog_size':len(symbols),'symbols':done,'files':{str(p.relative_to(root)):digest(p.read_bytes()) for p in out.glob('*.gz')}})

def make_ranks(root):
 root=Path(root);d=json.loads((root/'H1_MANIFEST.json').read_text());frames={};errors=[x for x in d['symbols'] if x['errors']]
 if errors:raise ValueError('PIT_BLOCKED_SOURCE_ERRORS_'+str(len(errors)))
 symbols=[];times=np.arange(WARM,END,H,dtype=np.int64);mat=[]
 for x in d['symbols']:
  rec=gzread(root/'h1'/(x['symbol']+'.json.gz'));bars=rec['bars']
  if not bars:continue
  frames[x['symbol']]=bars;symbols.append(x['symbol']);q=np.full(len(times),np.nan)
  for b in bars:q[(b[0]-WARM)//H]=b[6]
  mat.append(q)
 q=np.asarray(mat);valid=np.isfinite(q);v=np.where(valid,q,0);cs=np.pad(np.cumsum(v,axis=1),((0,0),(1,0)));cc=np.pad(np.cumsum(valid,axis=1),((0,0),(1,0)));vol=np.full(q.shape,np.nan);vol[:,23:]=cs[:,24:]-cs[:,:-24];vol[:,23:][(cc[:,24:]-cc[:,:-24])!=24]=np.nan
 rank=np.zeros(q.shape,dtype=np.int32)
 # symbols lexical order from manifest guarantees deterministic tie-break.
 for j in range(23,len(times)):
  ids=np.flatnonzero(np.isfinite(vol[:,j]));order=ids[np.argsort(-vol[ids,j],kind='stable')];rank[order,j]=np.arange(1,len(order)+1)
 np.savez_compressed(root/'PIT_RANKS.npz',symbols=np.array(symbols),times=times,rank=rank)
 write(root/'PIT_STATUS.json',{'status':'BINANCE_ARCHIVE_PIT24H_PROXY','symbols':len(symbols),'catalog_symbols':d['archive_catalog_size'],'errors':errors,'tradfi':'NOT_AVAILABLE','bybit_universe':'NOT_EQUIVALENT'})
 return frames,{s:i for i,s in enumerate(symbols)},rank

def funding(http,root,sym):
 root=Path(root);p=root/'funding'/(sym+'.json.gz')
 if p.exists():return gzread(p)
 seed=Path('inputs/funding/symbols')/(sym+'.json.gz');rows={};coverage=[];sources=[];errors=[]
 if seed.exists():
  d=gzread(seed);coverage=d.get('coverage',[]);sources=[{'seed_sha256':digest(seed.read_bytes()),'public_seed':str(seed)}]
  rows={int(r['ts']):r for r in d['rows']}
 for month in ['2026-08','2026-09','2026-10']:
  lo=int(dt.datetime.fromisoformat(month+'-01').replace(tzinfo=dt.timezone.utc).timestamp()*1000);t=dt.datetime.fromtimestamp(lo/1000,dt.timezone.utc);hi=int((t.replace(day=28)+dt.timedelta(days=4)).replace(day=1).timestamp()*1000)
  if any(a<=lo and b>=hi for a,b in coverage):continue
  try:
   rr,receipt=archive(http,f'data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{month}.zip')
   for r in rr:
    stamp=int(r[0]);rate=float(r[2]);hours=float(r[1]);row=dict(ts=stamp,rate=rate,interval_hours=hours)
    if stamp in rows and abs(float(rows[stamp]['rate'])-rate)>1e-12:raise ValueError('FUNDING_CONFLICT')
    rows[stamp]=row
   coverage.append([lo,hi]);sources.append(receipt)
  except Exception as e:errors.append({'month':month,'error':type(e).__name__+': '+str(e)})
 d=dict(symbol=sym,rows=[rows[t] for t in sorted(rows)],coverage=coverage,sources=sources,errors=errors);gzwrite(p,d);return d

def covered(d,a,b):
 cursor=a
 for lo,hi in sorted(d['coverage']):
  if lo<=cursor<hi:cursor=max(cursor,hi)
 return cursor>=b

def monthly_5m(http,root,sym,month):
 p=Path(root)/'m5'/f'{sym}-{month}.json.gz'
 if p.exists():return gzread(p)['bars']
 b,r=candle_month(http,sym,month,'5m');gzwrite(p,dict(bars=b,source=r));return b

def window_bars(http,root,sym,a,b):
 start=dt.datetime.fromtimestamp((a-B)/1000,dt.timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0);bars=[]
 while start.timestamp()*1000<b:
  bars+=monthly_5m(http,root,sym,start.strftime('%Y-%m'));start=(start.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
 return sorted(x for x in bars if a-B<=x[0]<b)

def simulate(bars,signal,side,stop,expiry,fund,targets=True):
 """Replay one frozen event; money funding with causal last closed candle mark."""
 first=(signal//B+1)*B;bb=[x for x in bars if x[0]>=first];p=dict(signal_ms=signal,entry_ms=first,status='NO_PRICE',direction=side,events=[],mfe_R=0.,mae_R=0.)
 if not bb or bb[0][0]!=first:return p
 o=bb[0][1];width=side*(o-stop)/o
 if not math.isfinite(width) or width<=0:p['status']='REJECTED_INVALID_STOP';return p
 denom=width+.0021;rem=1.;hit=0;net=-.00105;ev=[];end=None;last=first-B;tp=[o+side*(o*width)*r for r in (1,2,3)] if targets else []
 for t,op,hi,lo,cl,*_ in bb:
  if t!=last+B:p['status']='DATA_GAP_PRICE';return p
  last=t
  # Scheduled deadline uses actual available open; no exposure to remainder of exit bar.
  if t>=expiry:
   price=op;net+=rem*(side*(price/o-1)-.00105*price/o);ev.append(dict(time_ms=t,kind='TIME',fraction=rem,price=price));rem=0;end=t;break
  p['mfe_R']=max(p['mfe_R'],side*((hi if side==1 else lo)/o-1)/width)
  p['mae_R']=max(p['mae_R'],-side*((lo if side==1 else hi)/o-1)/width)
  if (lo<=stop if side==1 else hi>=stop):
   price=min(op,stop) if side==1 else max(op,stop);net+=rem*(side*(price/o-1)-.00105*price/o);ev.append(dict(time_ms=t,kind='SL',fraction=rem,price=price));rem=0;end=t;break
  if t==first:continue
  while hit<len(tp) and (hi>=tp[hit] if side==1 else lo<=tp[hit]):
   fraction=(.5,.3,.2)[hit];price=tp[hit];net+=fraction*(side*(price/o-1)-.00055*price/o);ev.append(dict(time_ms=t,kind='TP'+str(hit+1),fraction=fraction,price=price));rem=max(0.,rem-fraction);hit+=1
  if rem<1e-9:end=t;break
 p.update(entry=o,risk_fraction=width,risk_denominator=denom,events=ev)
 if end is None:p.update(status='CENSORED',remaining=rem);return p
 p.update(exit_ms=end,hold_hours=(end-first)/H,status='CLOSED',price_net_R=net/denom)
 if not covered(fund,first,end):p.update(status='FUNDING_UNKNOWN',net_R=None);return p
 funding_return=0.;ts=[r[0] for r in bars]
 for payment in fund['rows']:
  t=int(payment['ts'])
  if not first<t<=end:continue
  k=bisect.bisect_right(ts,t-B)-1
  if k<0 or bars[k][0]+B>t or t-(bars[k][0]+B)>B:p.update(status='FUNDING_MARK_UNKNOWN',net_R=None);return p
  remaining=remaining_for_payment(ev,t,side,float(payment['rate']))
  funding_return+=-side*remaining*float(payment['rate'])*bars[k][4]/o
 p.update(funding_R=funding_return/denom,net_R=(net+funding_return)/denom);return p

def remaining_for_payment(events,t,side,rate):
 pays=side*rate>0
 return max(0.,1.-sum(e['fraction'] for e in events if (e['time_ms']<t if e['kind']=='TIME' or not pays else e['time_ms']+B<=t)))

def reprice_saved_funding(r,bars,fund):
 # Preserve already calculated fills/fees/slippage; correct only ambiguous funding quantity.
 if r.get('status')!='CLOSED' or r.get('price_net_R') is None:return r
 r=dict(r);r['pre_correction_net_R']=r.get('net_R');a=r['entry_ms'];end=r['exit_ms']
 if not covered(fund,a,end):r.update(status='FUNDING_UNKNOWN',net_R=None);return r
 ts=[x[0] for x in bars];cash=0.
 for payment in fund['rows']:
  t=int(payment['ts'])
  if not a<t<=end:continue
  k=bisect.bisect_right(ts,t-B)-1
  if k<0 or bars[k][0]+B>t or t-(bars[k][0]+B)>B:r.update(status='FUNDING_MARK_UNKNOWN',net_R=None);return r
  rate=float(payment['rate']);side=1 if r['direction']==1 else -1
  cash+=-side*remaining_for_payment(r['events'],t,side,rate)*rate*bars[k][4]/r['entry']/r['risk_denominator']
 r.update(funding_R=cash,net_R=r['price_net_R']+cash,funding_ordering='CONSERVATIVE_PAYER_VS_RECEIVER_SAME_BAR');return r

def metrics(trades):
 closed=[t for t in trades if t.get('status')=='CLOSED' and t.get('net_R') is not None];v=[t['net_R'] for t in closed];positive=sum(x for x in v if x>0);negative=-sum(x for x in v if x<0);net=sum(v);peak=0.;equity=0.;dd=0.
 for t in sorted(closed,key=lambda x:(x['exit_ms'],x.get('symbol',''))):equity+=t['net_R'];peak=max(peak,equity);dd=max(dd,peak-equity)
 return dict(n=len(v),WR=100*sum(x>0 for x in v)/len(v) if v else None,PF=positive/negative if negative else None,netR=net,USD_at_5R=5*net,maxDD_R=dd,maxDD_percent_fixed_10000=dd*5/100,average_hold_hours=statistics.mean(t['hold_hours'] for t in closed) if closed else None,best3_share_net=sum(sorted([x for x in v if x>0],reverse=True)[:3])/net if net>0 else None,status_counts={s:sum(t.get('status')==s for t in trades) for s in sorted({t.get('status','UNKNOWN') for t in trades})})
def tables(trades):
 middle=(START+END)//2;tail=START+int((END-START)*.6)
 return {name:metrics([t for t in trades if a<=t['signal_ms']<b]) for name,a,b in [('FULL',START,END),('H1',START,middle),('H2',middle,END),('OOS40',tail,END)]}

def s1(root,index,ranks):
 src=Path('research/scenario_factory_20261116/inputs');fmap={r['id']:r for r in [json.loads(x) for x in gzip.open(src/'PF_RESEARCH_FUNDING.jsonl.gz','rt')]};tr=[];excluded=[]
 for line in gzip.open(src/'PF_RESEARCH_EXECUTIONS.jsonl.gz','rt'):
  r=json.loads(line);t=r['signal_ms']
  if not START<=t<END or not r.get('selected'):continue
  sym=r['symbol'];rank=int(ranks[index[sym],(t-H-WARM)//H]) if sym in index and t-H>=WARM else 0
  if not rank or rank>200:excluded.append(dict(id=r['id'],rank=rank,reason='OUTSIDE_RECONSTRUCTED_TOP200_OR_MISSING_SOURCE'));continue
  f=fmap.get(r['id'],{});z=dict(r,rank=rank,net_R=None,hold_hours=(r['exit_ms']-r['entry_ms'])/H if r.get('exit_ms') and r.get('entry_ms') else 0)
  if r['status']=='CLOSED' and r.get('exit_ms',END)>=END:z['status']='CENSORED'
  elif r['status']=='CLOSED' and f.get('funding_known'):
   # Exact same old-research taker accounting as S5, not a new strategy/model replay.
   fees=.00055*(1+sum(e['fraction']*e['price']/r['entry'] for e in r['events']));slip=.0005*(1+sum(e['fraction']*e['price']/r['entry'] for e in r['events'] if e['kind'] in ('SL','BE','TIME')))
   z['net_R']=(r['gross_return']-fees-slip)/.0581+f['funding_cash_R']
  elif r['status']=='CLOSED':z['status']='FUNDING_UNKNOWN'
  tr.append(z)
 top50=[t for t in tr if t['rank']<=50];actual=sum(x['net_R'] for x in top50 if x.get('net_R') is not None);rng=random.Random(20261116);dist=[]
 known=[t for t in tr if t.get('net_R') is not None];groups={}
 for t in known:groups.setdefault((t['signal_ms']-START)//(7*DAY),[]).append(t)
 for _ in range(999):
  total=0
  for g in groups.values():
   labels=[t['rank']<=50 for t in g];rng.shuffle(labels);total+=sum(t['net_R'] for t,k in zip(g,labels) if k)
  dist.append(total)
 out=dict(status='PARTIAL_SAVED_SELECTED_EXECUTION_BINANCE_PIT_PROXY_NOT_NEW_EXACT_S1',top200=tables(tr),top50_diagnostic=tables(top50),excluded=excluded,control=dict(kind='WITHIN_WEEK_RANK_LABEL_PERMUTATION',n=999,observed_top50_R=actual,p_add_one=(1+sum(x>=actual for x in dist))/1000,netR_distribution=dist),source_model_selection_cut=1788079200000)
 gzwrite(Path(root)/'S1_TRADES.json.gz',tr);write(Path(root)/'S1_RESULTS.json',out);return out

def s3(root,frames,index,ranks):
 root=Path(root);http=HTTP(root);signals=[];gaps=[];funds={}
 for sym,b in frames.items():
  if not any(START<=x[0]+H<END and 0<ranks[index[sym],(x[0]-WARM)//H]<=200 for x in b):continue
  f=funding(http,root,sym);funds[sym]=f;fr=f['rows'];ft=[int(x['ts']) for x in fr];cool=0
  for j in range(23,len(b)):
   hour=b[j][0]+H;obs=hour+17*60000
   if not START<=hour<END or obs<cool:continue
   rank=int(ranks[index[sym],(b[j][0]-WARM)//H])
   if not 0<rank<=200:continue
   w=b[j-23:j+1]
   if any(y[0]-x[0]!=H for x,y in zip(w,w[1:])):continue
   k=bisect.bisect_left(ft,obs)-1
   if k<0:continue
   rate=fr[k];hours=rate.get('interval_hours')
   if hours is None or not covered(f,ft[k],obs):continue
   # Reject stale observations, using recorded actual interval only.
   if obs-ft[k]>float(hours)*H or float(rate['rate'])*8/float(hours)>-.001:continue
   if min(x[3] for x in w[-6:])<min(x[3] for x in w[:-6]):continue
   signals.append(dict(symbol=sym,signal_ms=obs,stop=min(x[3] for x in w)*(1-1e-8),funding_source_ms=ft[k],funding_rate=rate['rate'],funding_interval_hours=hours,rank=rank));cool=hour+DAY
  write(root/'S3_SIGNAL_CHECKPOINT.json',{'symbols_examined':len(funds),'signals':len(signals),'pnl_started':False})
 gzwrite(root/'S3_SIGNALS.json.gz',signals);tr=[];controls=[];rng=random.Random(20261116);control_rng=[random.Random(20261116+i) for i in range(999)];dist=[0.]*999;nextfree={};paired=[]
 for n,sg in enumerate(sorted(signals,key=lambda x:(x['signal_ms'],x['symbol']))):
  sym=sg['symbol'];obs=sg['signal_ms'];expiry=(obs//B+1)*B+48*H
  if nextfree.get(sym,0)>obs:tr.append(dict(sg,status='REJECTED_OVERLAPPING_POSITION'));continue
  try:
   bars=window_bars(http,root,sym,obs,min(expiry+B,END));f=funds[sym];a=simulate(bars,obs,1,sg['stop'],expiry,f);a.update(sg);tr.append(a)
   if a.get('entry_ms') and a.get('status') not in ('REJECTED_INVALID_STOP','NO_PRICE'):nextfree[sym]=a.get('exit_ms',END)
   if a.get('status')=='CLOSED':
    mirror=2*a['entry']-sg['stop'];short=simulate(bars,obs,-1,mirror,expiry,f)
    if short.get('status')=='CLOSED':paired.append([a['net_R'],short['net_R']])
    else:gaps.append(dict(symbol=sym,signal_ms=obs,reason='RANDOM_DIRECTION_PAIR_UNAVAILABLE',status=short['status']))
  except Exception as e:tr.append(dict(sg,status='DATA_GAP_PRICE'));gaps.append(dict(symbol=sym,signal_ms=obs,reason=type(e).__name__+': '+str(e)))
  if n%10==0:gzwrite(root/'S3_TRADES.json.gz',tr);write(root/'REPLAY_CHECKPOINT.json',{'signals':len(signals),'processed':n+1,'errors':gaps});print('S3 replay',n+1,'/',len(signals),flush=True)
 for i,rng in enumerate(control_rng):dist[i]=sum(pair[rng.randrange(2)] for pair in paired)
 observed=sum(a for a,b in paired);control=dict(kind='PAIRED_RANDOM_DIRECTION_SAME_ENTRY_SYMMETRIC_RISK',n=999,paired_n=len(paired),observed_paired_long_R=observed,p_add_one=(1+sum(x>=observed for x in dist))/1000 if paired else None,netR_distribution=dist)
 out=dict(status='S3_SETTLED_BINANCE_PROXY_NOT_EXACT_TICKER_FACTORY',tables=tables(tr),control=control,gaps=gaps,signal_count=len(signals),funding_sources_examined=len(funds),exact_factory_status='DATA_GAP_HISTORICAL_INDICATIVE_TICKER')
 gzwrite(root/'S3_TRADES.json.gz',tr);write(root/'S3_RESULTS.json',out);return out

def s2(root):
 # Current snapshots preserve every article/rejection and do not claim first-edition fidelity.
 import sys
 sys.path.insert(0,str(Path('research/scenario_factory_20261116').resolve()))
 from rules import parse_delisting
 root=Path(root);http=HTTP(root);events=[];errors=[];pages=[];complete=False;seen=set()
 for page in range(1,101):
  try:
   url=f'https://api.bybit.com/v5/announcements/index?locale=en-US&type=delistings&page={page}&limit=50';raw=http.get(url);d=json.loads(raw)
   if d.get('retCode')!=0:raise ValueError('BYBIT_RETCODE_'+str(d.get('retCode')))
   records=d.get('result',{}).get('list',[]);pages.append(dict(page=page,sha256=digest(raw),rows=len(records)));gzwrite(root/'announcements'/f'index-{page}.json.gz',d)
   if not records:complete=True;break
   stamps=[]
   for r in records:
    pub=r.get('dateTimestamp')
    if not isinstance(pub,(int,float)):errors.append(dict(reason='EXACT_TIMESTAMP_MISSING',url=r.get('url')));continue
    stamps.append(pub)
    if not START<=pub<END:continue
    url=r.get('url','')
    if url in seen:continue
    seen.add(url)
    try:
     article=http.get(url).decode();gzwrite(root/'announcements'/(digest(url.encode())+'.json.gz'),dict(record=r,article=article));parsed=parse_delisting(r,article,pub);events.append(dict(record=r,parsed=parsed,source='BYBIT_CURRENT_REVISION_BINANCE_PRICE_PROXY',revision_history='DATA_GAP_ORIGINAL_VERSION'))
    except Exception as e:errors.append(dict(url=url,reason=type(e).__name__+': '+str(e)))
   if stamps and max(stamps)<START:complete=True;break
  except Exception as e:errors.append(dict(page=page,reason=type(e).__name__+': '+str(e)));break
 # Always preserve fallback availability; do not invent an exact delist time from a title.
 if not pages:
  try:
   raw=http.get('https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50&catalogId=161');(root/'BINANCE_ANNOUNCEMENT_FALLBACK.json.gz').write_bytes(gzip.compress(raw,mtime=0));errors.append(dict(reason='BINANCE_FALLBACK_SNAPSHOT_ONLY_NOT_COMPLETE_HISTORICAL_DELISTING_CORPUS',sha256=digest(raw)))
  except Exception as e:errors.append(dict(reason='BINANCE_FALLBACK_'+type(e).__name__+': '+str(e)))
 trades=[];control=[];unique=set()
 for e in events:
  p=e['parsed']
  if p.get('status')!='ELIGIBLE':continue
  obs=p['publication_ms'];expiry=p['exit_deadline_ms']//B*B
  for sym in p['symbols']:
   key=(sym,obs)
   if key in unique:continue
   unique.add(key)
   try:
    bars=window_bars(http,root,sym,obs,min(expiry+B,END));first=(obs//B+1)*B;entry=next((x[1] for x in bars if x[0]==first),None)
    if entry is None:raise ValueError('NO_ENTRY_PRICE_OR_CONTRACT_NOT_ON_BINANCE')
    f=funding(http,root,sym);t=simulate(bars,obs,-1,entry*1.08,expiry,f,False);t.update(symbol=sym,source_url=e['record']['url'],original_revision_certified=False);trades.append(t)
    shifted=obs+7*DAY;shiftend=expiry+7*DAY
    if shiftend>=END:control.append(dict(symbol=sym,status='CONTROL_CENSORED'));continue
    cb=window_bars(http,root,sym,shifted,shiftend+B);ce=next((x[1] for x in cb if x[0]==(shifted//B+1)*B),None)
    if ce is None:control.append(dict(symbol=sym,status='CONTROL_NO_PRICE'));continue
    ct=simulate(cb,shifted,-1,ce*1.08,shiftend,f,False);ct.update(symbol=sym);control.append(ct)
   except Exception as ex:trades.append(dict(symbol=sym,signal_ms=obs,status='DATA_GAP_PRICE',reason=type(ex).__name__+': '+str(ex)))
 out=dict(status='CURRENT_REVISION_BYBIT_EVENT_BINANCE_PRICE_PROXY' if trades else 'INCONCLUSIVE_DATA_GAP',tables=tables(trades),events=events,pages=pages,catalog_period_complete=complete,errors=errors,control=dict(kind='FIXED_PLUS_7_DAY_TIME_SHIFT',tables=tables(control) if control else None,status='AVAILABLE_PARTIAL' if control else 'CONTROL_DATA_GAP'),original_revision_status='DATA_GAP')
 gzwrite(root/'S2_TRADES.json.gz',trades);gzwrite(root/'S2_CONTROL_TRADES.json.gz',control);write(root/'S2_RESULTS.json',out);return out

def report(root):
 root=Path(root);results={}
 for s in ['S1','S2','S3','S2_BINANCE','S3_FACTORY','S2_BINANCE_REPLAY']:
  p=root/(s+'_RESULTS.json');results[s]=json.loads(p.read_text()) if p.exists() else {'status':'NOT_COMPLETED'}
 write(root/'CHECKPOINT.json',dict(stage='RESULTS_SAVED_WITH_LIMITATIONS',results={s:d['status'] for s,d in results.items()},code_sha=__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),protocol_commit='48c6061',profitability='NOT_CERTIFIED',round4_run_untouched=43842872790))
 lines=['# S1–S3 история: фактические результаты','', 'Только публичные архивы и исследовательские прокси. Результаты не являются доказательством доходности точной Bybit-фабрики.','', '|Сценарий/период|n|WR%|PF|netR|$ при $5/R|MaxDD R|Среднее часов|Top3/net|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for s,d in results.items():
  groups={'top200':d.get('top200',{}),'top50':d.get('top50_diagnostic',{})} if s=='S1' else {'main':d.get('tables',{})}
  for group,tt in groups.items():
   for period,m in tt.items():
    def fmt(k):
     v=m.get(k);return 'NA' if v is None else f'{v:.4f}' if isinstance(v,float) else str(v)
    lines.append('|'+s+'/'+group+'/'+period+'|'+'|'.join(fmt(k) for k in ['n','WR','PF','netR','USD_at_5R','maxDD_R','average_hold_hours','best3_share_net'])+'|')
  lines.extend(['',s+': '+d['status']+'. Подробные источники/исключения/контроль: '+s+'_RESULTS.json.',''])
 lines+=['## Ограничения и независимая проверка','S1: сохранённый прежний selected-корпус, не полный новый PUMP_FADE; top50 не настоящий фабричный BASE. До model cut2026-08-30 присутствует selection leakage. S3: settled funding Binance — известная после расчёта величина, не исторический live indicative ticker; строго раньше observation. S2: сегодняшние редакции объявлений не доказывают первоначальные версии. Binance цены/платежи не равны Bybit. Funding mark приближен закрытой5m ценой. OOS40 календарный, но сам по себе не независим от прежнего изучения корпуса. UNKNOWN не равен нулю. Смотреть все trades/status counts, каталог и checksum receipts.','', 'Случайные контроли фиксированы до расчёта; не корректированы на все прежние исследования. 5m недостаточно для внутрисвечного порядка: SL-first, noTP entrybar. MaxDD — закрытая аддитивная кривая R, не MTM. Новых параметров по результатам не выбирали.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','Исторические фиктивные сделки считаются только там, где доступны настоящие цены и расходы. Прокси не переименованы в точную фабрику. Недостающие сведения и отрицательные результаты сохранены. Устойчивую прибыльность по этому запуску не сертифицируем.','', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
 (root/'OTCHET_DLYA_CLAUDE_CODEX_S1_S3_HISTORY_20261116.md').write_text('\n'.join(lines)+'\n')
 write(root/'MANIFEST.json',{str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.json'})

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['probe','collect','replay','s2','report']);p.add_argument('--out',default='results/s1-s3-history');a=p.parse_args();root=Path(a.out);root.mkdir(parents=True,exist_ok=True)
 if a.stage=='probe':probe(root)
 elif a.stage=='collect':collect_h1(root,root/'SOURCE_AUDIT.json')
 elif a.stage=='s2':s2(root)
 elif a.stage=='replay':
  frames,index,ranks=make_ranks(root);s1(root,index,ranks);s3(root,frames,index,ranks)
 else:report(root)
if __name__=='__main__':main()
