"""Prepare existing pinned GitHub datasets, no download or PnL."""
import argparse,csv,gzip,json,time,hashlib,collections,math
from pathlib import Path
import numpy as np
M=300000;H=3600000

def prepare(data,out):
 start=time.monotonic();raw=[json.loads(x)for x in gzip.open(data/'all_signals.jsonl.gz','rt')]
 rows=[x for x in raw if x['hypothesis']=='BASE'and x['cohort']=='PRIMARY']
 assert len(rows)==2113
 rows.sort(key=lambda x:(x['signal_ms'],x['symbol'],x['id']))
 assert len({x['id']for x in rows})==len(rows)
 packets=[{'id':x['id'],'symbol':x['symbol'],'signal_ms':int(x['signal_ms']),'C':float(x['limit'])/1.013 if x.get('limit')else None,'original_limit':x.get('limit'),
          'archive_selected_exposed':bool(x.get('selected')),'symbol_type':x.get('symbol_type','UNKNOWN')}for x in rows]
 lookup={(x['symbol'],x['signal_ms']):i for i,x in enumerate(packets)};frames={};bad=collections.Counter();source_rows=0
 current=None;buf=[]
 def flush(key,b):
  if key not in lookup:return
  index=lookup[key];a=np.asarray(b,dtype=np.float64);frames['p'+str(index)]=a
 with gzip.open(data/'pf_5m.csv.gz','rt')as f:
  for r in csv.DictReader(f):
   source_rows+=1;key=(r['symbol'],int(r['signal_ms']))
   if current is not None and key!=current:flush(current,buf);buf=[]
   current=key
   v=[float(r[k])for k in ['ts','open','high','low','close']];buf.append(v)
 flush(current,buf)
 for i,p in enumerate(packets):
  a=frames.get('p'+str(i));p['frame_key']='p'+str(i);p['coverage_status']='DATA_GAP_5M'
  if a is None or len(a)==0:continue
  a=a[np.argsort(a[:,0])];frames[p['frame_key']]=a
  if len(np.unique(a[:,0]))!=len(a)or not np.all(np.isfinite(a))or np.any(a[:,1:]<=0):bad['INVALID_VALUES']+=1;continue
  if np.any(a[:,3]>np.minimum(a[:,1],a[:,4]))or np.any(a[:,2]<np.maximum(a[:,1],a[:,4])):bad['INVALID_OHLC']+=1;continue
  t=p['signal_ms'];wanted=np.arange(t-M,t+80*H+M,M,dtype=np.int64);ii=np.searchsorted(a[:,0],wanted)
  good=(ii<len(a));good[good]&=a[ii[good],0]==wanted[good]
  if not good.all():
   p['coverage_status']='RIGHT_CENSORED_80H'if a[-1,0]<t+80*H else'DATA_GAP_5M'
   continue
  p['coverage_status']='COMPLETE_80H';prev=float(a[int(np.searchsorted(a[:,0],t-M)),4])
  p['signal_C_vs_previous5mclose_fraction']=float(prev/p['C']-1)if p['C']else None
  if p['C']is None:p['C']=prev;p['C_source']='observed_previous_closed5m_not_synthetic'
  else:p['C_source']='original_limit_divided_by1.013'
 minimum=min(p['signal_ms']for p in packets);maximum=max(p['signal_ms']for p in packets)+H
 cut=(int(minimum+.6*(maximum-minimum))//M)*M
 for p in packets:p['split']='TEST'if p['signal_ms']>=cut else('TRAIN'if p['signal_ms']+80*H<=cut else'TRAIN_PURGED')
 btc={}
 with gzip.open(data/'btc_h1.csv.gz','rt')as f:
  for r in csv.DictReader(f):
   if r['symbol']=='BTCUSDT':btc[int(r['ts'])+H]=float(r['close'])
 for p in packets:
  known=(p['signal_ms']//H)*H
  rv=100*(btc[known]/btc[known-24*H]-1)if known in btc and known-24*H in btc else None
  p['btc_r24_pct']=rv;p['regime']='UNKNOWN'if rv is None else'DOWN'if rv<=-3 else'UP'if rv>=3 else'SIDEWAYS'
 funds=collections.defaultdict(dict);fund_bad=set()
 with gzip.open(data/'funding_full.csv.gz','rt')as f:
  for r in csv.DictReader(f):
   sym=r['symbol'];t=int(r['ts']);rate=float(r['funding_rate'])
   if t in funds[sym]and funds[sym][t]!=rate:fund_bad.add((sym,t))
   funds[sym][t]=rate
 funding={s:sorted([[t,v]for t,v in d.items()if(s,t)not in fund_bad])for s,d in funds.items()}
 out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'frames.npz',**frames)
 (out/'packets.json').write_text(json.dumps(packets,ensure_ascii=False,indent=2)+'\n')
 (out/'funding.json').write_text(json.dumps(funding,separators=(',',':')))
 audit={'original_signal_rows':len(packets),'already_filled_only_part6_rows':1761,'selected_exposed_rows':sum(x['archive_selected_exposed']for x in packets),
  'source_5m_rows':source_rows,'frames':len(frames),'coverage':dict(collections.Counter(p['coverage_status']for p in packets)),
  'split':dict(collections.Counter(p['split']for p in packets)),'cut_ms':cut,'min_signal_ms':minimum,'max_signal_ms':maximum-H,
  'coverage_by_split':{s:dict(collections.Counter(p['coverage_status']for p in packets if p['split']==s))for s in ['TRAIN','TEST','TRAIN_PURGED']},
  'C_recovered_from_real_closed5m_n':sum(p.get('C_source')=='observed_previous_closed5m_not_synthetic'for p in packets),'C_original_vs_previous5m_max_abs':max((abs(p.get('signal_C_vs_previous5mclose_fraction')or 0)for p in packets),default=None),'bad_price_frames':dict(bad),'conflicting_funding_timestamps':len(fund_bad),'regime_opportunities':dict(collections.Counter(p['regime']for p in packets)),
  'preparation_seconds':time.monotonic()-start,'PnL_computed':False}
 (out/'INPUT_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();prepare(a.data,a.out)
