"""Correct factory correspondence: SQUEEZE has cooldown but no one-symbol guard.
Reuses completed trades; evaluates only previously overlap-rejected entries.
"""
import argparse
from pathlib import Path
import history as h

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default='results/s1-s3-history');a=p.parse_args();root=Path(a.out)
 if not (root/'S3_TRADES.json.gz').exists():raise ValueError('S3_COMPLETED_SOURCE_LEDGER_REQUIRED')
 if (root/'S3_FACTORY_RESULTS.json').exists():print('S3 factory correction complete: reused');return
 trades=h.gzread(root/'S3_TRADES.json.gz');http=h.HTTP(root);out=[];pairs=[];errors=[]
 for r in trades:
  sym=r['symbol'];obs=r['signal_ms'];expiry=(obs//h.B+1)*h.B+48*h.H
  try:
   if r['status']=='REJECTED_OVERLAPPING_POSITION':
    bars=h.window_bars(http,root,sym,obs,min(expiry+h.B,h.END));f=h.funding(http,root,sym);new=dict(r);new.update(h.simulate(bars,obs,1,r['stop'],expiry,f));new['symbol']=sym;new['overlap_correction']=True;r=new
   out.append(r)
   if r.get('status')!='CLOSED' or r.get('net_R') is None:continue
   bars=h.window_bars(http,root,sym,obs,min(expiry+h.B,h.END));f=h.funding(http,root,sym);r=h.reprice_saved_funding(r,bars,f);out[-1]=r
   if r.get('status')!='CLOSED' or r.get('net_R') is None:continue
   short=h.simulate(bars,obs,-1,2*r['entry']-r['stop'],expiry,f)
   if short.get('status')=='CLOSED':pairs.append([r['net_R'],short['net_R']])
  except Exception as e:
   errors.append(dict(symbol=sym,signal_ms=obs,reason=type(e).__name__+': '+str(e)))
   if r not in out:out.append(dict(r,status='DATA_GAP_PRICE_CORRECTION'))
 rng=h.random.Random(20261116);dist=[sum(pair[rng.randrange(2)] for pair in pairs) for _ in range(999)];observed=sum(a for a,b in pairs)
 h.gzwrite(root/'S3_FACTORY_TRADES.json.gz',out);h.write(root/'S3_FACTORY_RESULTS.json',dict(status='S3_SETTLED_FACTORY_OVERLAP_BINANCE_PROXY_NOT_LIVE_TICKER',tables=h.tables(out),correction_n=sum(r.get('overlap_correction',False) for r in out),gaps=errors,control=dict(kind='RANDOM_DIRECTION_PAIRED_SAME_ENTRY',n=999,paired_n=len(pairs),observed_paired_long_R=observed,netR_distribution=dist,p_add_one=(1+sum(x>=observed for x in dist))/1000 if pairs else None)))
if __name__=='__main__':main()
