"""Addressed Binance public funding repair. No PnL, keys or trading APIs.
Official checksum-verified monthly files; bounded REST for current month.
Checkpoint after every symbol/archive. Existing published complete months reused.
interval_hours is retained as metadata, never a fabricated expected payment grid.
"""
import argparse,calendar,datetime as dt,gzip,hashlib,io,json,time,urllib.request,urllib.error,urllib.parse,zipfile,csv
from pathlib import Path
H=3600000;MONTHLY_END=1793491200000

def sha(b):return hashlib.sha256(b).hexdigest()
def atomic(p,data):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False)+'\n');tmp.replace(p)
def months(a,b):
 t=dt.datetime.fromtimestamp(a/1000,dt.timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0)
 while t.timestamp()*1000<b:
  nxt=(t.replace(day=28)+dt.timedelta(days=4)).replace(day=1);yield t.strftime('%Y-%m'),int(t.timestamp()*1000),int(nxt.timestamp()*1000);t=nxt

class HTTP:
 def __init__(self,root):self.root=root;self.last=0.;self.rest_blocked=None
 def get(self,url):
  url=urllib.parse.quote(url,safe=':/?=&%')
  for attempt in range(4):
   time.sleep(max(0,.3-(time.monotonic()-self.last)));self.last=time.monotonic()
   try:
    with urllib.request.urlopen(url,timeout=25) as r:b=r.read();code=r.status
    self.log(url,code,attempt,len(b));return b
   except urllib.error.HTTPError as e:
    self.log(url,e.code,attempt,0)
    if e.code not in (429,500,502,503,504) or attempt==3:raise
    time.sleep(min(30,2**attempt*2))
   except (TimeoutError,OSError) as e:
    self.log(url,type(e).__name__,attempt,0)
    if attempt==3:raise
    time.sleep(min(30,2**attempt*2))
 def log(self,url,status,attempt,n):
  with (self.root/'HTTP.jsonl').open('a') as f:f.write(json.dumps({'url':url,'status':status,'attempt':attempt+1,'bytes':n,'at':time.time()})+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--seed',required=True);p.add_argument('--out',required=True);p.add_argument('--deadline-seconds',type=int,default=1000);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);http=HTTP(out);planraw=Path(a.plan).read_bytes();plan=json.loads(planraw);start=time.monotonic();status={'state':'RUNNING','plan_sha256':sha(planraw),'completed':[],'unknown':[],'errors':[],'pnl_runs':0}
 try:
  for sym,windows in sorted(plan['symbols'].items()):
   if time.monotonic()-start>a.deadline_seconds:status['state']='PAUSED_DEADLINE';break
   dest=out/'symbols'/(sym+'.json.gz')
   if dest.exists():
    old=json.load(gzip.open(dest,'rt'))
    if old.get('plan_sha256')==sha(planraw) and old.get('complete'):
     status['completed'].append(sym);continue
   seed=Path(a.seed)/(sym+'.json.gz');rows={};coverage=[];sources=[];unknown=[]
   if seed.exists():
    raw=seed.read_bytes();d=json.loads(gzip.decompress(raw))
    if d.get('symbol')!=sym:raise ValueError('Seed identity mismatch')
    if d.get('coverage'):
     coverage.extend(d['coverage']);sources.append({'kind':'PUBLISHED_CERTIFIED_PAYMENT_WINDOWS','sha256':sha(raw),'file':seed.name})
     for r in d['rows']:rows[int(r['ts'])]=r
    elif d.get('monthly_complete') and d.get('monthly_through')=='2026-10':
     coverage.append([1698796800000,MONTHLY_END]);sources.append({'kind':'PUBLISHED_COMPLETE_MONTHLY_SEED','sha256':sha(raw),'file':seed.name})
     for r in d['rows']:rows[int(r['ts'])]=r
   needed={m:(lo,hi) for lo0,hi0,_ in windows for m,lo,hi in months(lo0-8*H,hi0+8*H)}
   for month,(lo,hi) in sorted(needed.items()):
    if any(x<=lo and y>=hi for x,y in coverage):continue
    if time.monotonic()-start>a.deadline_seconds:unknown.append({'month':month,'reason':'DEADLINE'});continue
    try:
     if hi<=MONTHLY_END:
      name=f'{sym}-fundingRate-{month}.zip';target=out/'raw'/name;receipt=target.with_suffix('.receipt.json');target.parent.mkdir(exist_ok=True)
      if target.exists() and receipt.exists() and sha(target.read_bytes())==json.loads(receipt.read_text())['sha256']:payload=target.read_bytes();expected=sha(payload)
      else:
       url='https://data.binance.vision/data/futures/um/monthly/fundingRate/'+sym+'/'+name;expected=http.get(url+'.CHECKSUM').decode().split()[0];payload=http.get(url)
       if sha(payload)!=expected:raise ValueError('Archive SHA mismatch')
       target.write_bytes(payload);atomic(receipt,{'sha256':expected,'url':url})
      z=zipfile.ZipFile(io.BytesIO(payload));read=list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8-sig')))
      for r in read:
       stamp=int(r['calc_time']);row={'ts':stamp,'rate':str(r['last_funding_rate']),'interval_hours':str(r['funding_interval_hours'])}
       if not lo<=stamp<hi:raise ValueError('Payment outside archive month')
       if stamp in rows and float(rows[stamp]['rate'])!=float(row['rate']):raise ValueError('Conflicting rates')
       rows[stamp]=row
      coverage.append([lo,hi]);sources.append({'kind':'OFFICIAL_MONTH','month':month,'sha256':expected,'rows':len(read)})
     else:
      if http.rest_blocked:unknown.append({'month':month,'reason':http.rest_blocked});continue
      # Only requested past windows in the current incomplete monthly archive.
      aa=max(lo,min(x[0]-8*H for x in windows));bb=min(hi,max(x[1]+8*H for x in windows),int(time.time()*1000));cursor=aa;received=[]
      for _ in range(100):
       url='https://fapi.binance.com/fapi/v1/fundingRate?'+urllib.parse.urlencode({'symbol':sym,'startTime':cursor,'endTime':bb-1,'limit':1000})
       payload=http.get(url);page=json.loads(payload)
       if not isinstance(page,list):raise ValueError('Unexpected REST response')
       received.append({'query_start':cursor,'end':bb,'sha256':sha(payload),'rows':len(page)})
       for r in page:
        stamp=int(r['fundingTime'])
        if not cursor<=stamp<bb:raise ValueError('REST ordering/range')
        rows[stamp]={'ts':stamp,'rate':r['fundingRate'],'interval_hours':None}
       if len(page)<1000:coverage.append([aa,bb]);sources.append({'kind':'PUBLIC_REST_COMPLETE_WINDOW','pages':received});break
       nxt=max(int(r['fundingTime']) for r in page)+1
       if nxt<=cursor:raise ValueError('REST cursor repeated')
       cursor=nxt
      else:raise ValueError('REST page budget exhausted')
    except urllib.error.HTTPError as exc:
     reason='HTTP_'+str(exc.code)
     if hi>MONTHLY_END and exc.code in (403,451):http.rest_blocked='REST_'+reason+'_NO_RETRY_OTHER_SYMBOLS'
     unknown.append({'month':month,'reason':reason})
    except Exception as exc:unknown.append({'month':month,'reason':type(exc).__name__+': '+str(exc)})
   for aa,bb,_ in windows:
    cursor=aa
    for lo,hi in sorted(coverage):
     if lo<=cursor<hi:cursor=max(cursor,hi)
    if cursor<bb:unknown.append({'window':[aa,bb],'reason':'UNCERTIFIED_PAYMENT_WINDOW'})
   record={'symbol':sym,'plan_sha256':sha(planraw),'rows':[rows[t] for t in sorted(rows)],'coverage':coverage,'sources':sources,'unknown':unknown,'complete':not unknown,'interval_semantics':'metadata only; complete archive/REST certificate defines coverage','mark':'real causal candle approximation required'}
   dest.parent.mkdir(exist_ok=True);dest.write_bytes(gzip.compress(json.dumps(record,ensure_ascii=False).encode()))
   status['completed'].append(sym)
   if unknown:status['unknown'].append({'symbol':sym,'reasons':unknown})
   atomic(out/'CHECKPOINT.json',status)
  else:status['state']='COLLECTION_FINISHED_WITH_GAPS' if status['unknown'] else 'COLLECTION_COMPLETE'
 except Exception as exc:status['state']='PAUSED_ERROR';status['errors'].append(type(exc).__name__+': '+str(exc))
 status['rest_blocked']=http.rest_blocked;atomic(out/'CHECKPOINT.json',status);atomic(out/'MANIFEST.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='MANIFEST.json'});print(json.dumps({k:v for k,v in status.items() if k not in ['completed','unknown']},indent=2));print('symbols',len(status['completed']),'unknown',len(status['unknown']))
if __name__=='__main__':main()
