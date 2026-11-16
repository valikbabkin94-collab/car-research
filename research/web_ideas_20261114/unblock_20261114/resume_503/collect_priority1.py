"""Resume public Binance priority1 only; complete existing metadata is reused.
No PnL, no order/venue credentials. Raw ZIP stays in memory, checksum mandatory.
"""
import argparse,json,gzip,hashlib,io,zipfile,urllib.parse,xml.etree.ElementTree as ET,concurrent.futures,shutil,time
from pathlib import Path
import numpy as np,pandas as pd
from resilient_http import Client,NetworkPause,FileFailed
NS={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
BASE='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
def metadata(client,symbol,cache,interval="1h"):
 p=cache/(symbol+'_'+interval+'.json.gz')
 if p.exists():return json.loads(gzip.decompress(p.read_bytes()))
 prefix=f'data/futures/um/monthly/klines/{symbol}/{interval}/';marker='';items=[];hashes=[]
 while True:
  args={'prefix':prefix,'max-keys':'1000'}
  if marker:args['marker']=marker
  b=client.get(BASE+'?'+urllib.parse.urlencode(args),symbol+'_'+interval+'_catalog');doc=ET.fromstring(b);hashes.append(hashlib.sha256(b).hexdigest())
  for e in doc.findall('s:Contents',NS):items.append({k:e.findtext('s:'+k,namespaces=NS) for k in ['Key','Size','ETag','LastModified']})
  if doc.findtext('s:IsTruncated',namespaces=NS)!='true':break
  marker=doc.findtext('s:NextMarker',namespaces=NS) or items[-1]['Key']
 d={'symbol':symbol,'kind':interval,'prefix':prefix,'page_sha256':hashes,'objects':items};p.write_bytes(gzip.compress(json.dumps(d).encode()));return d

def daily_metadata(client,symbol,cache,interval="1h"):
 p=cache/(symbol+'_'+interval+'_daily_2026_11.json.gz')
 if p.exists():return json.loads(gzip.decompress(p.read_bytes()))
 prefix=f'data/futures/um/daily/klines/{symbol}/{interval}/{symbol}-{interval}-2026-11-';args={'prefix':prefix,'max-keys':'1000'}
 raw=client.get(BASE+'?'+urllib.parse.urlencode(args),symbol+'_daily_catalog');doc=ET.fromstring(raw)
 if doc.findtext('s:IsTruncated',namespaces=NS)=='true':raise ValueError('Unexpected truncated November daily listing')
 d={'symbol':symbol,'kind':'1h_daily_tail','objects':[{k:e.findtext('s:'+k,namespaces=NS) for k in ['Key','Size','ETag','LastModified']} for e in doc.findall('s:Contents',NS)]};p.write_bytes(gzip.compress(json.dumps(d).encode()));return d

def archive(client,key,out):
 name=key.rsplit('/',1)[-1].removesuffix('.zip');p=out/(name+'.npz');receipt=out/(name+'.json')
 if p.exists() and receipt.exists():
  r=json.loads(receipt.read_text())
  if hashlib.sha256(p.read_bytes()).hexdigest()==r['parsed_sha256']:return 'REUSED'
 # Retain no raw ZIP; source SHA and parsed-array SHA both preserved.
 expected=client.get('https://data.binance.vision/'+key+'.CHECKSUM',key).decode().split()[0]
 raw=client.get('https://data.binance.vision/'+key,key);actual=hashlib.sha256(raw).hexdigest()
 if actual!=expected:raise ValueError('CHECKSUM_MISMATCH '+key)
 z=zipfile.ZipFile(io.BytesIO(raw));f=pd.read_csv(z.open(z.namelist()[0]),header=None)
 if str(f.iloc[0,0])=='open_time':f=f.iloc[1:]
 f=f.astype({0:'int64',1:'float64',2:'float64',3:'float64',4:'float64',5:'float64',7:'float64'});ts=f[0].to_numpy();bar_ms=900000 if "/15m/" in key else 3600000;bad=np.diff(ts)!=bar_ms
 if np.any(ts>10**14):raise ValueError('Unexpected timestamp unit '+key)
 if len(np.unique(ts))!=len(ts):raise ValueError('Duplicate timestamp '+key)
 # Never fill gaps. Save true source timestamps and explicit gap count.
 if shutil.disk_usage(out).free<100*1024*1024:raise NetworkPause('RESOURCE_PAUSE: less than100MiB disk; no source DATA_GAP inferred')
 tmp=p.with_suffix('.tmp.npz');np.savez_compressed(tmp,ts=ts,open=f[1].to_numpy(),high=f[2].to_numpy(),low=f[3].to_numpy(),close=f[4].to_numpy(),volume=f[5].to_numpy(),quote_volume=f[7].to_numpy());tmp.replace(p)
 r={'key':key,'source_bytes':len(raw),'source_sha256':actual,'checksum_verified':True,'rows':len(f),'first_open_ms':int(ts[0]),'last_open_ms':int(ts[-1]),'bar_gaps':int(bad.sum()),'bar_ms':bar_ms,'parsed_sha256':hashlib.sha256(p.read_bytes()).hexdigest()};receipt.write_text(json.dumps(r,indent=2));return 'DOWNLOADED'

def main():
 a=argparse.ArgumentParser();a.add_argument('--catalog-root',required=True);a.add_argument('--out',required=True);a.add_argument('--max-new-archives',type=int,default=0);a.add_argument('--symbols',nargs='*');a.add_argument('--symbol-file');a.add_argument('--metadata-only',action='store_true');a.add_argument('--daily-tail',action='store_true');a.add_argument('--interval',choices=['1h','15m'],default='1h');a.add_argument('--deadline-seconds',type=int,default=16200);args=a.parse_args();root=Path(args.catalog_root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True);cache=root/'catalog_cache';local_cache=out/'_catalog_cache';local_cache.mkdir(exist_ok=True)
 for saved in local_cache.glob('*.gz'):
  if not (cache/saved.name).exists():shutil.copy(saved,cache/saved.name)
 client=Client(out/'HTTP_LOG.jsonl');symbols=json.loads(Path(args.symbol_file).read_text()) if args.symbol_file else (args.symbols or json.loads((root/'SYMBOLS.json').read_text())['symbols']);started=time.monotonic();counts={'reused':0,'downloaded':0,'metadata_reused':0};gaps=[];status='RUNNING'
 def checkpoint():
  (out/'CHECKPOINT.json').write_text(json.dumps({'status':status,'counts':counts,'gaps':gaps,'pnl_started':False,'priority':1 if args.interval=='1h' else 2,'interval':args.interval,'symbols':len(symbols),'configuration':{'workers':2,'spacing_seconds':1.0,'attempts':6,'backoff':[5,10,20,40,80],'distinct_failure_cooldown_seconds':600,'monthly_first':True}},indent=2))
 checkpoint()
 try:
  # Catalogues first, hourly-only; no re-fetch of saved317hourly prefixes.
  for start in range(0,len(symbols),2):
   if time.monotonic()-started>args.deadline_seconds:raise NetworkPause('Time budget checkpoint')
   def meta_job(symbol):
    existing=(cache/(symbol+'_'+args.interval+'.json.gz')).exists()
    try:
     metadata(client,symbol,cache,args.interval)
     if args.daily_tail:daily_metadata(client,symbol,cache,args.interval)
     for saved in [cache/(symbol+'_'+args.interval+'.json.gz'),cache/(symbol+'_'+args.interval+'_daily_2026_11.json.gz')]:
      if saved.exists():shutil.copy(saved,local_cache/saved.name)
     return {'reused':int(existing)}
    except FileFailed as e:return {'failed':symbol,'error':str(e)}
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(meta_job,symbols[start:start+2]))
   for result in results:
    counts['metadata_reused']+=result.get('reused',0)
    if 'failed' in result:gaps.append(result)
   checkpoint()
  if gaps:raise NetworkPause('Hourly catalogue incomplete after bounded retries; no PIT/PnL permitted')
  if args.metadata_only:
   status='PRIORITY1_METADATA_COMPLETE';return 0
  jobs=[]
  for symbol in symbols:
   d=metadata(client,symbol,cache,args.interval)
   if args.daily_tail:d={'objects':d['objects']+daily_metadata(client,symbol,cache,args.interval)['objects']}
   for o in d['objects']:
    key=o['Key'];month=key[-11:-4]
    if not key.endswith('.zip'):continue
    if '/monthly/' in key and '2023-01'<=month<='2026-10':jobs.append(key)
    if '/daily/' in key and '2026-11-01'<=key[-14:-4]<='2026-11-13':jobs.append(key)
  # Two archive workers; shared pacing also covers CHECKSUM calls.
  # Bounded batches avoid submitting thousands of speculative downloads.
  for start in range(0,len(jobs),2):
   if time.monotonic()-started>args.deadline_seconds:raise NetworkPause('Time budget checkpoint')
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda key:archive(client,key,out),jobs[start:start+2]))
   for result in results:counts['downloaded' if result=='DOWNLOADED' else 'reused']+=1
   checkpoint();print(json.dumps({'counts':counts,'done':start+len(results),'total':len(jobs)}),flush=True)
   if args.max_new_archives and counts['downloaded']>=args.max_new_archives:status='BOUNDED_BATCH_COMPLETE';break
  else:status='PRIORITY1_PRICES_COMPLETE' if args.daily_tail else 'MONTHLY_PRIORITY1_COMPLETE_DAILY_TAIL_PENDING'
 except Exception as e:
  status='PAUSED';gaps.append({'type':'OPERATION_FAILED_NOT_ABSENT_MARKET_DATA','error':str(e)});print(status,str(e),flush=True)
 finally:checkpoint()
 return 1 if status=='PAUSED' else 0
if __name__=='__main__':
 import sys
 sys.exit(main())
