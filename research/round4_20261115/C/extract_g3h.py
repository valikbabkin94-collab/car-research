"""Causal G3h opportunity audit; NOT a PnL replay or executed trade count.
Real H1 only. Non-meme metadata not supplied => unknown, never false/zero.
"""
import argparse,gzip,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'research/round3_20261115/tools'))
from audit_saved_inputs import load,START,END,HOUR as H
KNOWN_END=1793491200000

def features(b):
 ix=np.arange(int(b.index.min()),int(b.index.max())+H,H);b=b.reindex(ix);n=len(b);low=b.low.to_numpy();close=b.close.to_numpy();vol=b.volume.to_numpy();quote=b.quote_volume.to_numpy();higher=np.zeros(n,dtype=bool);vw=np.full(n,np.nan);piv=[]
 for i in range(25,n):
  if not np.isfinite(low[i-23:i+1]).all():continue
  win=low[i-23:i+1];anchor=i-23+len(win)-1-int(np.argmin(win[::-1]))
  j=i-2
  if j>=2 and np.isfinite(low[j-2:j+3]).all() and low[j]<=min(low[j-2:j]) and low[j]<=min(low[j+1:j+3]):piv.append(j)
  piv=[j for j in piv if j>=i-23]
  eligible=[j for j in piv if j>=anchor]
  if len(eligible)>=2:higher[i]=low[eligible[-1]]>low[eligible[-2]]
  den=np.sum(vol[anchor:i+1]);num=np.sum(quote[anchor:i+1])
  if den>0 and np.isfinite(num):vw[i]=num/den
 prior=b.volume.shift().rolling(24,min_periods=24).median()
 out=pd.DataFrame({'r24':b.close/b.close.shift(24)-1,'reversal':higher&(close>vw)&(b.volume>=1.5*prior),'low24':b.low.rolling(24,min_periods=24).min(),'close':b.close,'close24ago':b.close.shift(24),'entry':b.open.shift(-1)},index=ix+H)
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--hourly',required=True);p.add_argument('--pit',required=True);p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 with np.load(Path(a.pit)/'PIT_RANKS.npz') as z:times=z['decision_ms'];symbols=z['symbols'];ranks=z['rank']
 use=(times>=START)&(times<END);times=times[use];ranks=ranks[use];names=[str(symbols[j]) for j in range(len(symbols)) if ((ranks[:,j]>0)&(ranks[:,j]<=150)).any()]
 frames={};age={}
 for k,s in enumerate(names):
  b,_=load(a.hourly,s,'1h')
  if b.empty:continue
  age[s]=int(b.index.min());frames[s]=features(b).reindex(times)
  if k%100==0:print('verified symbols',k,flush=True)
 btc,_=load(a.hourly,'BTCUSDT','1h');btc=features(btc).reindex(times).r24.to_numpy();r24=np.column_stack([frames[s].r24.to_numpy() if s in frames else np.full(len(times),np.nan) for s in names]);column={str(s):j for j,s in enumerate(symbols)}
 rank=np.column_stack([ranks[:,column[s]] for s in names]);eligible=(rank>0)&(rank<=150)&np.isfinite(r24)&(r24<=-.08)
 funding_dir=Path(a.data)/'research_data/round3_20261115/funding_inputs_43722362909';fund={}
 for s in names:
  path=funding_dir/(s+'.json.gz')
  if path.exists():fund[s]=json.load(gzip.open(path,'rt'))
 counts={v:{'possible_before_unknown_Q':0,'known_eligible_before_portfolio':0,'unknown_nonmeme':0,'entry_or_stop_rejected':0,'funding_window_unknown':0,'funding_file_missing':0} for v in ['FULL','NO_OWN_DECLINE','NO_REVERSAL','NO_QUALITY','NO_MEME']};records=[]
 for i,t in enumerate(times):
  candidates=sorted(np.flatnonzero(eligible[i]),key=lambda j:(r24[i,j],names[j]))[:10]
  for j in candidates:
   s=names[j];x=frames[s].iloc[i];own=bool(np.isfinite(btc[i]) and r24[i,j]-btc[i]<=-.06);reversal=bool(x.reversal) if pd.notna(x.reversal) else False;quality_rank=0<rank[i,j]<=40;age_proven=int(t)-age[s]>180*24*H
   for v in counts:
    if v!='NO_OWN_DECLINE' and not own:continue
    if v!='NO_REVERSAL' and not reversal:continue
    if v!='NO_QUALITY' and not (quality_rank and age_proven):continue
    c=counts[v];c['possible_before_unknown_Q']+=1
    unknown=v not in ['NO_QUALITY','NO_MEME']
    if unknown:c['unknown_nonmeme']+=1
    entry=float(x.entry);stop=float(x.low24)*(1-1e-8);width=(entry-stop)/entry if np.isfinite(entry) and entry>0 else np.nan;tp3=entry+.5*(float(x.close24ago)-float(x.low24))
    executable=bool(np.isfinite(width) and 0<width<=.06 and tp3>entry+2*(entry-stop))
    if not executable:c['entry_or_stop_rejected']+=1
    elif not unknown:c['known_eligible_before_portfolio']+=1
    ff=fund.get(s);fund_known=bool(ff and ff.get('monthly_complete') and t+48*H<=KNOWN_END)
    if not fund_known:c['funding_window_unknown']+=1
    if ff is None:c['funding_file_missing']+=1
    records.append({'variant':v,'symbol':s,'decision_ms':int(t),'entry_open_ms':int(t),'entry_open':entry if np.isfinite(entry) else None,'stop':stop if np.isfinite(stop) else None,'risk_fraction':width if np.isfinite(width) else None,'tp3':tp3 if np.isfinite(tp3) else None,'technical_executable':executable,'nonmeme_known':False,'nonmeme_required':unknown,'age_lowerbound_proven':age_proven,'own_decline':own,'reversal':reversal,'funding_file_present':ff is not None,'monthly_funding_envelope_known':fund_known})
 with gzip.open(out/'G3h_OPPORTUNITIES_NOT_TRADES.jsonl.gz','wt') as dest:
  for r in records:dest.write(json.dumps(r,allow_nan=False)+'\n')
 report={'kind':'CAUSAL_H1_OPPORTUNITY_AUDIT_NOT_PNL','counts':counts,'universe_symbols':len(names),'verified_frames':len(frames),'meme_asof':'MISSING_UNKNOWN_NOT_FALSE','funding_envelope_note':'File/month coverage only, individual payment/continuity/mark not yet audited; not net coverage proof','portfolio_replay':'NOT_RUN; no holding cap applied in opportunity counts','PnL_runs':0,'status':'PARTIAL_INPUT_FORENSICS_G3h_REPLAY_PENDING','window':[START,END]}
 (out/'G3h_SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
