"""Audit verified saved candles against frozen R1/R2 execution requirements; no network."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

START=1698796800000
END=1794614400000
HOUR=3600000


def load(root, sym, interval):
    parts=[]; receipts=[]
    for path in sorted(Path(root).rglob(sym+'-'+interval+'-*.npz')):
        if not path.name.startswith(sym+'-'+interval+'-'): continue
        receipt=json.loads(path.with_suffix('.json').read_text())
        if not receipt.get('checksum_verified') or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['parsed_sha256']:
            raise ValueError('UNVERIFIED '+str(path))
        with np.load(path) as data:
            parts.append(pd.DataFrame({k:data[k] for k in data.files}).set_index('ts'))
        receipts.append(receipt)
    if not parts:return pd.DataFrame(),[]
    frame=pd.concat(parts).sort_index()
    if frame.index.duplicated().any():raise ValueError('DUPLICATE '+sym+' '+interval)
    return frame,receipts


def run(hourly,m15,pit,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with np.load(Path(pit)/'PIT_RANKS.npz') as data:
        times=data['decision_ms'];syms=data['symbols'];ranks=data['rank']
    eligible=(times>=START)&(times<END)
    stamps=pd.to_datetime(times,unit='ms',utc=True)
    eligible &= (stamps.dayofweek==0)&(stamps.hour==0)
    weekly=[];needed=set()
    for i in np.flatnonzero(eligible):
        chosen=[(int(ranks[i,j]),str(syms[j])) for j in range(len(syms)) if 1<=ranks[i,j]<=20]
        names=[s for _,s in sorted(chosen)]
        weekly.append({'decision_ms':int(times[i]),'symbols':names})
        needed.update(names)
    (out/'R1_WEEKLY_SELECTION.json').write_text(json.dumps(weekly,indent=2)+'\n')
    records=[]; execution={};daily={}
    for sym in sorted(needed|{'BTCUSDT','ETHUSDT'}):
        h,hr=load(hourly,sym,'1h');m,mr=load(m15,sym,'15m')
        opens=set(m.index.tolist()) if not m.empty else set()
        relevant=[w['decision_ms']+900000 for w in weekly if sym in w['symbols']]
        absent=[t for t in relevant if t not in opens]
        execution[sym]={'needed':len(relevant),'missing':len(absent),'missing_ms':absent}
        if not h.empty:
            # UTC daily close exists only with 24 contiguous completed real hours.
            bars=h['close'].resample('1D',origin='epoch') if False else None
            d=h.copy();d.index=pd.to_datetime(d.index,unit='ms',utc=True)
            counts=d['close'].resample('1D').count();closes=d['close'].resample('1D').last().where(counts==24)
            daily[sym]=closes
        records.append({'symbol':sym,'h1_files':len(hr),'h1_rows':len(h),'m15_files':len(mr),'m15_rows':len(m),'R1_execution_needed':len(relevant),'R1_execution_missing':len(absent)})
    pd.DataFrame(records).to_csv(out/'SOURCE_COVERAGE.csv',index=False)
    rows=[]
    for w in weekly:
        t=pd.Timestamp(w['decision_ms'],unit='ms',tz='UTC')
        for lookback in (30,90):
            for longonly in (False,True):
                raw=[]
                for sym in w['symbols']:
                    series=daily.get(sym)
                    valid=False;weight=0.
                    if series is not None:
                        # Last daily close before decision: never same-day close.
                        sample=series.reindex(pd.date_range(t-pd.Timedelta(days=lookback+1),t-pd.Timedelta(days=1),freq='D'))
                        v30=series.reindex(pd.date_range(t-pd.Timedelta(days=31),t-pd.Timedelta(days=1),freq='D'))
                        if len(sample)==lookback+1 and sample.notna().all() and v30.notna().all():
                            vol=np.log(v30/v30.shift()).dropna().std(ddof=1)*np.sqrt(365)
                            sign=np.sign(sample.iloc[-1]/sample.iloc[0]-1)
                            if vol>0 and np.isfinite(vol):
                                valid=True;weight=float((max(sign,0) if longonly else sign)*.20/(20*vol))
                    raw.append([sym,weight,valid])
                gross=sum(abs(x[1]) for x in raw);scale=1/max(1,gross)
                for sym,weight,valid in raw:rows.append({'decision_ms':w['decision_ms'],'variant':f'L{lookback}_'+('LONG_ONLY' if longonly else 'LONG_SHORT'),'symbol':sym,'weight':weight*scale,'history_eligible':valid,'execution_ms':w['decision_ms']+900000,'execution_available':w['decision_ms']+900000 not in execution[sym]['missing_ms']})
    pd.DataFrame(rows).to_csv(out/'R1_FROZEN_WEIGHTS.csv',index=False)
    r2=[]
    for sym in ('BTCUSDT','ETHUSDT'):
        h,_=load(hourly,sym,'1h');m,_=load(m15,sym,'15m')
        expected=np.arange(START+900000,END, HOUR)
        available=set(m.index) if not m.empty else set()
        missing=[int(t) for t in expected if t not in available]
        r2.append({'symbol':sym,'required_hourly_execution_quotes':len(expected),'missing_00_15_quotes':len(missing),'missing_first20':missing[:20],'h1_rows':len(h)})
    report={'stage':'INPUT_AND_FROZEN_SIGNAL_AUDIT_NO_PNL','protocol_unchanged':True,'R1':{'weekly_decisions':len(weekly),'unique_selected_symbols':len(needed),'required_execution_quotes':sum(x['needed'] for x in execution.values()),'missing_execution_quotes':sum(x['missing'] for x in execution.values()),'weights_rows':len(rows),'status':'DATA_BLOCKED_MISSING_EXECUTION_QUOTES' if any(x['missing'] for x in execution.values()) else 'EXECUTION_QUOTES_PRESENT_FUNDING_AUDIT_REQUIRED'},'R2':r2,'PnL_runs':0}
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hourly',required=True);p.add_argument('--m15',required=True);p.add_argument('--pit',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.hourly,a.m15,a.pit,a.out)
