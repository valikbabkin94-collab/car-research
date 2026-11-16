"""Frozen G3h descriptive portfolio replay. NO_QUALITY and NO_MEME only have
known filter identities; other rows retain unknown historical meme metadata.
H1 funding inside an exit bar uses conservative quantity bounds, flagged.
"""
import argparse,gzip,json,sys,importlib.util
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'research/round3_20261115/tools'))
from audit_saved_inputs import load,START,END,HOUR as H
spec=importlib.util.spec_from_file_location('r1_account',Path(__file__).with_name('replay_r1h.py'));r1=importlib.util.module_from_spec(spec);spec.loader.exec_module(r1)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from execution_guard import long_quantity
DIAG_END=r1.DIAG_END;HALF=r1.HALF;TAIL=r1.TAIL

def main():
 p=argparse.ArgumentParser();p.add_argument('--hourly',required=True);p.add_argument('--funding',required=True);p.add_argument('--out',required=True);p.add_argument('--interval',choices=['1h','15m'],default='1h');p.add_argument('--opportunities');a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 step=H if a.interval=='1h' else 900000
 source=ROOT/'research/round4_20261115/C/g3h_opportunities_43758200928/G3h_OPPORTUNITIES_NOT_TRADES.jsonl.gz';source=Path(a.opportunities) if a.opportunities else source;allrows=[json.loads(x) for x in gzip.open(source,'rt')];candidates=[x for x in allrows if x['variant'] in ['NO_MEME','NO_QUALITY'] and x['technical_executable']];symbols=sorted({x['symbol'] for x in candidates});bars={};fund={}
 for s in symbols:
  bars[s],_=load(a.hourly,s,a.interval);fund[s]=json.load(gzip.open(Path(a.funding)/'symbols'/(s+'.json.gz'),'rt'))
 reports={}
 for variant in ['NO_MEME','NO_QUALITY']:
  signals=sorted([x for x in candidates if x['variant']==variant],key=lambda x:(x['decision_ms'],x['symbol']));bytime={}
  for x in signals:bytime.setdefault(x['entry_open_ms'],[]).append(x)
  cash=10000.;active=[];closed=[];rejections=[];navrows=[];paymentlog=[];fee_total=slip_total=fund_total=0.;blocked=None
  # Event lists preserve exact timestamps; H1 assignment is only an index.
  payments={}
  for s in {x['symbol'] for x in signals}:
   for f in fund[s]['rows']:
    t=int(f['ts'])
    if START<=t<DIAG_END:payments.setdefault((s,t//step*step),[]).append(f)
  def mark(t):
   nav=cash
   for pos in active:
    b=bars[pos['symbol']];px=b.open.get(t,np.nan)
    if not np.isfinite(px):raise ValueError('MISSING_ACTIVE_OPEN '+pos['symbol'])
    nav+=pos['qty']*pos['remain']*(px-pos['entry'])
   return nav
  def funding_cash(pos,event,remaining,ambiguous=False):
   nonlocal cash,fund_total
   t=int(event['ts']);b=bars[pos['symbol']];m=b.close.get(t//step*step-step,np.nan)
   if not np.isfinite(m):raise ValueError('MISSING_FUNDING_MARK')
   value=-pos['qty']*remaining*float(event['rate'])*m;cash+=value;fund_total+=value;pos['funding']+=value;paymentlog.append({'symbol':pos['symbol'],'entry_ms':pos['entry_ms'],'payment_ms':t,'rate':event['rate'],'quantity':pos['qty']*remaining,'mark_candle_close_approx':float(m),'mark_interval':a.interval,'cash':value,'exit_bar_quantity_bound':ambiguous})
  def leave(pos,t,kind,price,fraction):
   nonlocal cash,fee_total,slip_total
   notional=pos['qty']*fraction*price;fc=.00055*notional;sc=.0005*notional;realized=pos['qty']*fraction*(price-pos['entry']);cash+=realized-fc-sc;fee_total+=fc;slip_total+=sc;pos['realized']+=realized-fc-sc;pos['remain']=max(0.,pos['remain']-fraction);pos['events'].append({'bar_open_ms':int(t),'kind':kind,'price':float(price),'fraction':fraction,'fee':fc,'slippage':sc})
   if pos['remain']<1e-9:pos['exit_ms']=int(t+step);pos['status']='CLOSED'
  try:
   for t in range(START,DIAG_END,step):
    # Payments exactly at hour OPEN belong to positions already held, before entries.
    for pos in active:
     for e in payments.get((pos['symbol'],t),[]):
      if int(e['ts'])==t and t>pos['entry_ms']:funding_cash(pos,e,pos['remain'])
    for pos in list(active):
     if t>=pos['entry_ms']+48*H:leave(pos,t,'TIME',float(bars[pos['symbol']].loc[t,'open']),pos['remain']);pos['exit_ms']=t;active.remove(pos);closed.append(pos)
    nav=mark(t)
    for signal in bytime.get(t,[]):
     sym=signal['symbol'];reason=None
     if any(x['symbol']==sym for x in active):reason='ALREADY_OPEN'
     elif len(active)>=5:reason='POSITION_CAP'
     elif not r1.certified(fund[sym]['coverage'],t,min(t+48*H,DIAG_END)):reason='DATA_BLOCKED_FUNDING'
     if reason:rejections.append({'symbol':sym,'decision_ms':t,'reason':reason});continue
     entry=float(bars[sym].loc[t,'open']);stop=signal['stop'];risk_usd=.005*nav
     try:qty=long_quantity(entry,stop,risk_usd)
     except ValueError as exc:
      rejections.append({'symbol':sym,'decision_ms':t,'reason':str(exc)});continue
     gross=sum(abs(x['qty']*x['remain']*float(bars[x['symbol']].loc[t,'open'])) for x in active)
     if gross+qty*entry>nav:rejections.append({'symbol':sym,'decision_ms':t,'reason':'GROSS_NOTIONAL_CAP'});continue
     fc=qty*entry*.00055;sc=qty*entry*.0005;cash-=fc+sc;fee_total+=fc;slip_total+=sc;pos={'symbol':sym,'entry_ms':t,'entry':entry,'qty':qty,'stop':stop,'remain':1.,'hit':0,'BE_from':None,'targets':[entry+(entry-stop),entry+2*(entry-stop),signal['tp3']],'risk_usd':risk_usd,'realized':-fc-sc,'funding':0.,'events':[],'status':'OPEN','MFE_coarse_R':0.,'MAE_coarse_R':0.};active.append(pos)
    for pos in list(active):
     sym=pos['symbol'];b=bars[sym]
     if t not in b.index:raise ValueError('MISSING_H1 '+sym)
     if not r1.certified(fund[sym]['coverage'],t,t+step-1):raise ValueError('UNCERTIFIED_ACTIVE_FUNDING '+sym)
     bar=b.loc[t];before=pos['remain'];risk=pos['entry']-pos['stop'];pos['MFE_coarse_R']=max(pos['MFE_coarse_R'],(float(bar.high)-pos['entry'])/risk);pos['MAE_coarse_R']=max(pos['MAE_coarse_R'],(pos['entry']-float(bar.low))/risk);stop=pos['entry'] if pos['BE_from'] is not None and t>=pos['BE_from'] else pos['stop']
     if float(bar.low)<=stop:leave(pos,t,'BE' if stop==pos['entry'] else 'SL',min(float(bar.open),stop),pos['remain'])
     elif t!=pos['entry_ms']:
      while pos['hit']<3 and float(bar.high)>=pos['targets'][pos['hit']]:
       j=pos['hit'];leave(pos,t,'TP'+str(j+1),pos['targets'][j],[.5,.3,.2][j]);pos['hit']+=1
       if j==0:pos['BE_from']=t+step
     for e in payments.get((sym,t),[]):
      if int(e['ts'])<=t:continue
      remain=before if float(e['rate'])>0 else pos['remain'];funding_cash(pos,e,remain,before!=pos['remain'])
     if pos['status']=='CLOSED':active.remove(pos);closed.append(pos)
    endnav=cash+sum(x['qty']*x['remain']*(float(bars[x['symbol']].loc[t,'close'])-x['entry']) for x in active);navrows.append({'ts':t+step,'nav':endnav})
  except Exception as exc:blocked=type(exc).__name__+': '+str(exc)
  frame=pd.DataFrame([{'ts':START,'nav':10000.}]+navrows);frame.to_csv(out/(variant+'_NAV.csv.gz'),index=False)
  for pos in active:pos['status']='RIGHT_CENSORED'
  ledger=closed+active
  for pos in ledger:pos['net_usdt_closed']=pos['realized']+pos['funding'] if pos['status']=='CLOSED' else None;pos['net_R_closed']=pos['net_usdt_closed']/pos['risk_usd'] if pos['status']=='CLOSED' else None
  for name,rows in [('TRADES',ledger),('REJECTIONS',rejections),('FUNDING',paymentlog)]:
   with gzip.open(out/(variant+'_'+name+'.jsonl.gz'),'wt') as dest:
    for row in rows:dest.write(json.dumps(row,allow_nan=False)+'\n')
  metrics={}
  for name,s,e in [('H1',START,HALF),('H2_SOURCE_BOUNDED',HALF,END),('TAIL40_SOURCE_BOUNDED',TAIL,END),('SOURCE_BOUNDED_FULL',START,END)]:
   mm=r1.summarize(frame,s,e);tr=[x for x in closed if x['entry_ms']>=s and x['exit_ms']<=min(e,DIAG_END)];values=np.array([x['net_R_closed'] for x in tr]);profit=float(values[values>0].sum());loss=float(-values[values<0].sum());mm.update({'closed_trades_contained':len(tr),'win_rate_percent':100*float((values>0).mean()) if len(values) else None,'sum_R_closed':float(values.sum()),'PF_R_closed':profit/loss if loss else None,'R_note':'fee-inclusive planned per-trade risk; no portfolio R','cross_boundary_closed':sum(x['entry_ms']<s<x['exit_ms'] or x['entry_ms']<e<x['exit_ms'] for x in closed)});metrics[name]=mm
  blocks={}
  for x in signals:blocks.setdefault((x['symbol'],x['decision_ms']%(24*H)//H,x['decision_ms']//(7*24*H)),set()).add(x['decision_ms']//(24*H))
  mutable=sum(len(v)>1 for v in blocks.values());
  for mm in metrics.values():mm['mark']=a.interval+'_close_MTM; funding_previous_closed_'+a.interval+'_close_proxy'
  reports[variant]={'opportunities_all':len(signals),'opportunities_in_source_window':sum(x['decision_ms']<DIAG_END for x in signals),'closed':len(closed),'right_censored':len(active),'rejected':len(rejections),'cash':{'fees':fee_total,'slippage':slip_total,'funding_conservative_candle_bound':fund_total},'periods':metrics,'control':{'status':'INSUFFICIENT_MATCHED_OTHER_DAY_BLOCKS','mutable_blocks':mutable,'required_min':10,'random_replicates_run':0,'reason':'Do not invent matched causal confirmations at random days'},'blocked':blocked,'primary_full_status':'DATA_BLOCKED_NOVEMBER_FUNDING','primary_full_net':None,'profitability':'INCONCLUSIVE','funding_execution_note':'actual rates/timestamps; '+a.interval+' close mark approximation; adverse exit-bar quantity bounds'};print(variant,json.dumps(reports[variant]),flush=True)
 for variant in ['FULL','NO_OWN_DECLINE','NO_REVERSAL']:reports[variant]={'status':'DATA_BLOCKED_CAUSAL_NONMEME_METADATA','PnL':None,'technical_upper_bound_opportunities':sum(x['variant']==variant and x['technical_executable'] for x in allrows),'small_sample':variant!='NO_REVERSAL','not_replaced_by_NO_MEME':True}
 (out/('G3h_RESULTS.json' if a.interval=='1h' else 'G3_15M_RESULTS.json')).write_text(json.dumps(reports,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
