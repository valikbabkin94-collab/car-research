"""Cashflows: unchanged short path; hedge at observed5m close, proportional reductions."""
import json
from pathlib import Path
import numpy as np
from panel import Data,M,F,H,DAY
R=.056;CODES=["H_PUMP50","H_PUMP100","H_ALT50","H_ALT100","H_BTC50","H_BTC100"]
def finite(x):
 if isinstance(x,dict):return{k:finite(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return[finite(v)for v in x]
 if isinstance(x,np.ndarray):return finite(x.tolist())
 if isinstance(x,(float,np.floating)):return float(x)if np.isfinite(x)else None
 if isinstance(x,np.integer):return int(x)
 if isinstance(x,np.bool_):return bool(x)
 return x
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(finite(x),ensure_ascii=False,allow_nan=False,indent=2)+"\n")
def schedule(e,r):
 a=e["entry_ms"]//F*F+F;groups={}
 for k in range(int(r[12])):
  t=int(r[13+4*k]);kind=int(r[16+4*k]);close=t//F*F+F if kind==4 else((t+F-1)//F)*F
  if close>a:groups[close]=groups.get(close,0.)+float(r[15+4*k])
 return a,sorted(groups.items())
def short(d,e,r):
 if r[0]!=1:return None
 entry=float(r[32]);start=int(r[31]);end=int(r[7]);j=d.index.get(e["symbol"]);gross=float(r[2]);turnover=1+sum(r[15+4*k]*r[14+4*k]/entry for k in range(int(r[12])));fee=.00105*turnover;fund=0.;unknown=0.;good=True
 if j is None:good=False;unknown=(end-start)/(8*H)*.0001
 else:
  ft,cp,cn,bad=d.rawfund[j]
  for k in range(int(r[12])):
   t=int(r[13+4*k]);f=float(r[15+4*k]);a=np.searchsorted(ft,start,side="right");b=np.searchsorted(ft,t,side="left");c=np.searchsorted(ft,start,side="left");dd=np.searchsorted(ft,t,side="right");fund+=f*((cp[b]-cp[a])+(cn[dd]-cn[c]))/entry
   if bad[dd]-bad[c]:good=False
  a=max(0,d.ix(start));b=min(len(d.times)-1,d.ix(end));uc=int(d.unknown[j,b]-d.unknown[j,a]);unknown=uc*F/(8*H)*.0001;good&=uc==0
 return dict(short_R=(gross-fee+fund)/R,short_gross_R=gross/R,short_fee_R=fee/R,short_funding_R=fund/R,short_funding_known=bool(good),short_unknown_stress_R=unknown/R,parent_original_netR=float(r[1]))
def evaluate(d,e,r,kind):
 s=short(d,e,r)
 if s is None:return dict(status="SHORT_DATA_GAP")
 a,ev=schedule(e,r);remain=sum(f for t,f in ev)
 def zero(reason):return dict(status="VALID",**s,long_gross_R=0.,long_fee_R=0.,long_funding_R=0.,long_R=0.,long_unknown_stress_R=0.,funding_known=s["short_funding_known"],n_members=0,no_hedge_reason=reason,hedge_entry_close=a,hedge_exit_close=a,members=[])
 if remain<1e-10:return zero("SHORT_FLAT_BEFORE_HEDGE_CLOSE")
 members=d.basket(e["entry_ms"],kind,e["symbol"])
 if members is None:return dict(status="HEDGE_BASKET_DATA_GAP",**s)
 if not members:return zero("PUMP_COHORT_LT3")
 ia=d.ix(a);iex=np.array([d.ix(t)for t,f in ev]);fs=np.array([f for t,f in ev]);jj=np.array(members)
 if ia<0 or np.any(iex>=len(d.times)):return dict(status="HEDGE_QUOTE_RANGE_GAP",**s)
 pe=d.q[jj,ia];px=d.q[jj[:,None],iex[None,:]];missing=d.missing[jj,iex[-1]]-d.missing[jj,ia]
 if np.any(~np.isfinite(pe))or np.any(~np.isfinite(px))or np.any(missing):return dict(status="HELD_HEDGE_PRICE_DATA_GAP",**s,members=[d.sy[j]for j in members])
 gross=float(np.mean(np.sum(fs*(px/pe[:,None]-1),axis=1)))/R;fee=.00105*float(np.mean(remain+np.sum(fs*px/pe[:,None],axis=1)))/R
 fc=d.fc[jj[:,None],iex[None,:]]-d.fc[jj,ia,None];fund=-float(np.mean(np.sum(fs*fc/pe[:,None],axis=1)))/R;unknown=d.unknown[jj[:,None],iex[None,:]]-d.unknown[jj,ia,None];stress=.0001*F/(8*H)*float(np.mean(np.sum(fs*unknown,axis=1)))/R
 return dict(status="VALID",**s,long_gross_R=gross,long_fee_R=fee,long_funding_R=fund,long_R=gross-fee+fund,long_unknown_stress_R=stress,funding_known=bool(s["short_funding_known"]and np.max(unknown)==0),n_members=len(members),no_hedge_reason=None,hedge_entry_close=a,hedge_exit_close=ev[-1][0],members=[d.sy[j]for j in members])
def scaled(result,ratio):
 r=dict(result)
 if r["status"]!="VALID":return r
 for k in["long_gross_R","long_fee_R","long_funding_R","long_R","long_unknown_stress_R"]:r[k]*=ratio
 r["netR"]=r["short_R"]+r["long_R"];r["unknown_funding_stress_R"]=r["short_unknown_stress_R"]+r["long_unknown_stress_R"];return r
def metrics(rows):
 good=sorted([r for r in rows if r.get("status")=="VALID"],key=lambda r:r.get("exit_ms",0));x=np.array([r["netR"]for r in good]);net=float(x.sum());loss=float(-x[x<0].sum());eq=np.cumsum(x);top=float(np.sort(x)[-3:].sum())
 return dict(n=len(x),WR=float(100*np.mean(x>0))if len(x)else None,PF=float(x[x>0].sum()/loss)if loss else None,netR=net,USD_per5signalR=5*net,maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(x)else 0,short_R=float(sum(r["short_R"]for r in good)),hedge_R=float(sum(r["long_R"]for r in good)),short_fees_R=float(sum(r["short_fee_R"]for r in good)),hedge_fees_R=float(sum(r["long_fee_R"]for r in good)),hedge_funding_R=float(sum(r["long_funding_R"]for r in good)),short_funding_R=float(sum(r["short_funding_R"]for r in good)),matched_nohedge_netR=float(sum(r["short_R"]for r in good)),top3_share=top/net if net>0 else None,netR_funding_adverse=float(sum(r["netR"]-r["unknown_funding_stress_R"]for r in good)),funding_unknown_n=sum(not r["funding_known"]for r in good),no_hedge_n=sum(r["n_members"]==0 for r in good),coverage=len(good)/max(1,len(rows)),data_gap_n=len(rows)-len(good))
def bh(ps):
 ix=np.argsort(ps);q=np.ones(len(ps));v=1.
 for k in range(len(ps)-1,-1,-1):j=ix[k];v=min(v,ps[j]*len(ps)/(k+1));q[j]=v
 return q.tolist()
def paired(rows,nulls):
 blocks={};diff=[]
 for r,c in zip(rows,nulls):
  a=np.array(c,float);ok=np.isfinite(a)
  if r.get("status")=="VALID"and ok.sum()>=180:
   v=r["netR"]-float(a[ok].mean());day=int(r["entry_ms"])//DAY;blocks[day]=blocks.get(day,0.)+v;diff.append(v)
 if len(diff)<20 or len(blocks)<8:p=1.
 else:
  vals=np.array(list(blocks.values()));rng=np.random.default_rng(20261117);p=(1+int(np.sum((rng.choice([-1.,1.],size=(9999,len(vals)))@vals)>=vals.sum())))/10000
 return dict(excessR=float(sum(diff)),p=p,paired_n=len(diff),control_coverage=len(diff)/max(1,sum(r.get("status")=="VALID"for r in rows)))
