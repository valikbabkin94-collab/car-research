"""Frozen R1h cash replay, source-bounded diagnostics and sign controls.
No HTTP, no strategy fitting. All missing prices/certificates fail closed.
"""
import argparse,gzip,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'research/round3_20261115/tools'))
from audit_saved_inputs import load,START,END,HOUR as H
HALF=1746705600000;TAIL=1756287360000;DIAG_END=1793487600000

def certified(cov,a,b):
 cursor=a
 for lo,hi in sorted(cov):
  if lo<=cursor<hi:cursor=max(cursor,hi)
 return cursor>b

def summarize(nav,start,end):
 a=nav[(nav.ts>=start)&(nav.ts<=end)]
 if len(a)<2:return {'status':'INSUFFICIENT'}
 e=a.nav.to_numpy();dd=np.maximum.accumulate(e);draw=float(np.max(1-e/dd));daily=a.assign(day=a.ts//(24*H)).groupby('day').nav.last().pct_change().dropna();sharpe=float(daily.mean()/daily.std(ddof=1)*np.sqrt(365)) if len(daily)>1 and daily.std(ddof=1)>0 else None
 net=float(e[-1]-e[0]);months=a.assign(month=pd.to_datetime(a.ts,unit='ms',utc=True).dt.strftime('%Y-%m'),pnl=a.nav.diff().fillna(0)).groupby('month').pnl.sum();best=float(months.max()) if len(months) else None
 return {'start_ms':int(a.ts.iloc[0]),'end_ms':int(a.ts.iloc[-1]),'net_usdt':net,'return_percent':100*(e[-1]/e[0]-1),'annualized_return_percent':100*((e[-1]/e[0])**(365*24*H/(a.ts.iloc[-1]-a.ts.iloc[0]))-1) if min(e)>0 else None,'max_drawdown_percent':100*draw,'daily_sharpe':sharpe,'best_month_fraction_net':best/net if net>0 else None,'R':None,'PF':'NA_PORTFOLIO_MTM_NOT_INDEPENDENT_CLOSED_TRADES','end_truncated':int(a.ts.iloc[-1])<end,'mark':'H1_open_MTM; funding previous_closed_H1_close_proxy'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--hourly',required=True);p.add_argument('--funding',required=True);p.add_argument('--out',required=True);p.add_argument('--controls',type=int,default=1000);p.add_argument('--interval',choices=['1h','15m'],default='1h');a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 step=H if a.interval=='1h' else 900000
 w=pd.read_csv(ROOT/'research/round3_20261115/saved_input_audit_43742911716/R1_FROZEN_WEIGHTS.csv.gz');symbols=sorted(w.symbol.unique());times=np.arange(START,DIAG_END+step,step);price=np.full((len(times),len(symbols)),np.nan);fund=np.zeros_like(price);cov={};receipts={}
 for j,s in enumerate(symbols):
  b,r=load(a.hourly,s,a.interval);price[:,j]=b.open.reindex(times).to_numpy();receipts[s]=len(r);f=json.load(gzip.open(Path(a.funding)/'symbols'/(s+'.json.gz'),'rt'));cov[s]=f['coverage']
  for e in f['rows']:
   stamp=int(e['ts'])
   if not START<stamp<=DIAG_END:continue
   i=int(np.searchsorted(times,stamp,side='left'));mark=b.close.get(stamp//step*step-step,np.nan)
   if not np.isfinite(mark):fund[i,j]=np.nan
   else:fund[i,j]+=float(e['rate'])*mark
 reports={};rng=np.random.default_rng(20261115)
 for variant,g in w.groupby('variant'):
  weights=g.pivot(index='decision_ms',columns='symbol',values='weight').reindex(columns=symbols).fillna(0);weights.index+=step;weights=weights[weights.index<=DIAG_END];lookup={int(t):row.to_numpy() for t,row in weights.iterrows()};nav=10000.;qty=np.zeros(len(symbols));prev=np.zeros(len(symbols));records=[];trades=[];fee=slip=funding_cash=0.;block=None
  for i,t in enumerate(times):
   active=qty!=0
   if active.any():
    if np.any(~np.isfinite(price[i,active])) or np.any(~np.isfinite(prev[active])):block={'time':int(t),'reason':'MISSING_ACTIVE_QUOTE'};break
    if any(not certified(cov[symbols[j]],int(t-step),int(t)) for j in np.flatnonzero(active)):block={'time':int(t),'reason':'UNCERTIFIED_FUNDING_WINDOW'};break
    if np.any(~np.isfinite(fund[i,active])):block={'time':int(t),'reason':'MISSING_FUNDING_MARK'};break
    cash=-float(np.dot(qty[active],fund[i,active]));funding_cash+=cash;nav+=float(np.dot(qty[active],price[i,active]-prev[active]))+cash
   if int(t) in lookup:
    target=lookup[int(t)];needed=(target!=0)|active
    if np.any(~np.isfinite(price[i,needed])):block={'time':int(t),'reason':'MISSING_REBALANCE_QUOTE'};break
    pp=np.where(needed,price[i],1.);estimate=nav
    for _ in range(12):q=target*estimate/pp;turn=float(np.sum(np.abs(q-qty)*pp));estimate=nav-.00105*turn
    q=target*estimate/pp;delta=q-qty;turn=float(np.sum(np.abs(delta)*pp));fc=turn*.00055;sc=turn*.0005;nav-=fc+sc;fee+=fc;slip+=sc
    for j in np.flatnonzero(delta):trades.append({'time_ms':int(t),'symbol':symbols[j],'quantity_delta':float(delta[j]),'reference_open':float(pp[j]),'fee':float(abs(delta[j])*pp[j]*.00055),'slippage_cash':float(abs(delta[j])*pp[j]*.0005)})
    qty=q
   prev=price[i].copy();records.append({'ts':int(t),'nav':nav,'funding_cash_cumulative':funding_cash,'fees_cumulative':fee,'slippage_cumulative':slip,'gross_notional':float(np.sum(np.abs(qty[qty!=0])*price[i,qty!=0]))})
  frame=pd.DataFrame(records);frame.to_csv(out/(variant+'_NAV.csv.gz'),index=False);pd.DataFrame(trades).to_csv(out/(variant+'_EXECUTIONS.csv.gz'),index=False)
  periods={name:summarize(frame,s,e) for name,s,e in [('H1',START,HALF),('H2_SOURCE_BOUNDED',HALF,END),('TAIL40_SOURCE_BOUNDED',TAIL,END),('SOURCE_BOUNDED_FULL',START,END)]}
  periods['PRIMARY_FULL']={'status':'DATA_BLOCKED_CURRENT_MONTH_FUNDING','net_usdt':None,'PF':None,'end_required':END,'data_end':DIAG_END}
  # Controls: vectorized weekly cash algebra, independently checked against hourly NAV.
  ws=weights.to_numpy();stamps=weights.index.to_numpy();week_end=np.r_[stamps[1:],DIAG_END];valid=stamps<DIAG_END;ws=ws[valid];stamps=stamps[valid];week_end=week_end[valid];starts=np.searchsorted(times,stamps);ends=np.searchsorted(times,week_end);cs=np.vstack([np.zeros(len(symbols)),np.cumsum(np.nan_to_num(fund),axis=0)]);coef=[]
  for ii,jj,row in zip(starts,ends,ws):
   used=row!=0;v=np.zeros(len(symbols));v[used]=(price[jj,used]-price[ii,used]-(cs[jj+1,used]-cs[ii+1,used]))/price[ii,used];coef.append(v)
  coef=np.array(coef);results=[];controls_blocked=False
  for rep in range(-1,a.controls):
   test=ws.copy()
   if rep>=0:
    for j in range(len(symbols)):
     ix=np.flatnonzero(ws[:,j]);test[ix,j]=np.abs(ws[ix,j])*rng.permutation(np.sign(ws[ix,j]))
   nn=10000.;qq=np.zeros(len(symbols))
   for k,ii in enumerate(starts):
    needed=(test[k]!=0)|(qq!=0);pp=np.where(needed,price[ii],1.)
    if np.any(~np.isfinite(pp[needed])):controls_blocked=True;break
    estimate=nn
    for _ in range(12):qt=test[k]*estimate/pp;estimate=nn-.00105*float(np.sum(np.abs(qt-qq)*pp))
    qt=test[k]*estimate/pp;nn-=.00105*float(np.sum(np.abs(qt-qq)*pp));nn+=estimate*float(np.dot(test[k],coef[k]));qq=qt
   if rep==-1:
    if not controls_blocked and abs(nn-float(frame.nav.iloc[-1]))>1e-6:raise AssertionError('Hourly/weekly cash identity mismatch')
   else:results.append({'replicate':rep,'net_usdt':nn-10000. if not controls_blocked else None})
   if controls_blocked:break
  pd.DataFrame(results).to_csv(out/(variant+'_CONTROLS.csv.gz'),index=False);mutable=sum(len(set(np.sign(ws[ws[:,j]!=0,j])))>1 for j in range(len(symbols)));observed=float(frame.nav.iloc[-1]-10000)
  control={'n':len(results),'mutable_sign_symbols':mutable,'status':'INSUFFICIENT_SIGN_VARIATION' if mutable<10 else 'SOURCE_BOUNDED_DIAGNOSTIC' if not controls_blocked else 'DATA_BLOCKED','one_sided_p':(1+sum(x['net_usdt']>=observed for x in results if x['net_usdt'] is not None))/(len(results)+1) if results and not controls_blocked and mutable>=10 else None,'null_mean_net_usdt':float(np.mean([x['net_usdt'] for x in results])) if results and not controls_blocked else None}
  
  for mm in periods.values():
   if 'mark' in mm:mm['mark']=a.interval+'_open_MTM; funding previous_closed_'+a.interval+'_close_proxy'
  reports[variant]={'periods':periods,'control':control,'cash':{'fees':fee,'slippage':slip,'funding':funding_cash},'execution_legs':len(trades),'weekly_decisions':len(weights),'early_block':block,'primary_status':'INCONCLUSIVE_NO_FULL_FUNDING','source_end':DIAG_END};print(variant,json.dumps(reports[variant]),flush=True)
 family=sorted([(r['control'].get('one_sided_p') if r['control'].get('one_sided_p') is not None else 1,v) for v,r in reports.items()]);maximum=0
 for i,(pv,v) in enumerate(family):maximum=max(maximum,min(1,(4-i)*pv));reports[v]['control']['holm4_p']=maximum
 (out/('R1h_RESULTS.json' if a.interval=='1h' else 'R1_15M_RESULTS.json')).write_text(json.dumps(reports,indent=2,allow_nan=False)+'\n');(out/'SOURCE_RECEIPTS.json').write_text(json.dumps(receipts,indent=2)+'\n')
if __name__=='__main__':main()
