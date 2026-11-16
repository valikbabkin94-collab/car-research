"""Original G3 15m causal opportunity extraction, no PnL. Right-only pivot
confirmation is preserved from saved pit_features.py, not G3h symmetric pivots.
Explicit latest user instruction: execution +15m after hourly decision.
"""
import importlib.util,sys,gzip,json,argparse
from pathlib import Path
import numpy as np,pandas as pd
from collections import deque
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('base_g3',HERE.parent/'extract_g3h.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sys.path.insert(0,str(HERE))
from execution_guard import long_quantity
M=900000

def old_features(b):
 ix=np.arange(int(b.index.min()),int(b.index.max())+M,M);b=b.reindex(ix);n=len(b);low=b.low.to_numpy();c=b.close.to_numpy();v=b.volume.to_numpy();q=b.quote_volume.to_numpy();anchors=np.zeros(n,dtype=int);dq=deque()
 for i in range(n):
  while dq and dq[0]<i-95:dq.popleft()
  if np.isfinite(low[i]):
   while dq and low[dq[-1]]>=low[i]:dq.pop()
   dq.append(i)
  anchors[i]=dq[0] if dq else i
 confirm=np.zeros(n,dtype=bool);confirm[2:]=(low[:-2]<=low[1:-1])&(low[:-2]<=low[2:]);events=np.flatnonzero(confirm);k=np.searchsorted(events,np.arange(n),side='right')-1;last=np.full(n,-1);prev=np.full(n,-1);valid=k>=1
 if len(events):
  last[valid]=events[k[valid]]-2;prev[valid]=events[k[valid]-1]-2
 hl=np.zeros(n,dtype=bool);good=valid&(prev>=anchors);hl[good]=low[last[good]]>low[prev[good]]
 qs=np.r_[0,np.cumsum(np.nan_to_num(q))];vs=np.r_[0,np.cumsum(np.nan_to_num(v))];den=vs[1:]-vs[anchors];avwap=np.divide(qs[1:]-qs[anchors],den,out=np.full(n,np.nan),where=den>0);complete=b.close.rolling(96,min_periods=96).count()==96;prior=b.volume.shift().rolling(96,min_periods=96).median();rev=hl&(c>avwap)&(v>=1.5*prior)&complete
 result=pd.DataFrame({'r24':b.close/b.close.shift(96)-1,'reversal':rev,'low24':b.low.rolling(96,min_periods=96).min(),'close':b.close,'close24ago':b.close.shift(96),'entry':b.open.shift(-2)},index=b.index)
 result.index+=M
 return result

if __name__=='__main__':
 original=base.load
 base.load=lambda root,sym,interval:original(root,sym,'15m')
 base.features=old_features
 base.main()
 # Legacy base field names do not determine original15m execution availability.
 out=Path(sys.argv[sys.argv.index('--out')+1]);source=out/'G3h_OPPORTUNITIES_NOT_TRADES.jsonl.gz'
 with gzip.open(source,'rt') as src,gzip.open(out/'G3_15M_OPPORTUNITIES_NOT_TRADES.jsonl.gz','wt') as dest:
  for line in src:
   row=json.loads(line);row['entry_open_ms']=row['decision_ms']+M;row['timeframe']='15m';row['execution_delay_ms']=M
   if row['technical_executable']:
    try:long_quantity(row['entry_open'],row['stop'],1.)
    except (ValueError,TypeError):
     row['technical_executable']=False;row['execution_guard_rejection']='INVALID_LONG_ENTRY_STOP'
   if row['decision_ms']+M+48*base.H>base.KNOWN_END:row['monthly_funding_envelope_known']=False
   dest.write(json.dumps(row,allow_nan=False)+'\n')
 summary=json.loads((out/'G3h_SUMMARY.json').read_text());summary.update(kind='ORIGINAL_G3_15M_OPPORTUNITY_AUDIT_NOT_PNL',execution_delay_ms=M,output_corrected='G3_15M_OPPORTUNITIES_NOT_TRADES.jsonl.gz',legacy_base_summary='Preserved; funding envelope counts are coarse, use corrected per-row windows')
 (out/'G3_15M_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
