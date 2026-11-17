"""Self-financed matched-quantity carry simulator. No exchange client or live operations."""
import json,math,hashlib,datetime as dt
from pathlib import Path
import numpy as np
H=3600000;DAY=24*H
def ms(s):return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
PERIODS={"H1":(ms("2025-11-01"),ms("2026-05-01")),"H2":(ms("2026-05-01"),ms("2026-11-01")),"LAST40":(ms("2026-06-08"),ms("2026-11-01")),"FULL":(ms("2025-11-01"),ms("2026-11-01"))}
def finite(x):
 if isinstance(x,dict):return {k:finite(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [finite(v)for v in x]
 if isinstance(x,np.ndarray):return finite(x.tolist())
 if isinstance(x,(float,np.floating)):return float(x)if np.isfinite(x)else None
 if isinstance(x,np.integer):return int(x)
 if isinstance(x,np.bool_):return bool(x)
 return x
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(finite(x),ensure_ascii=False,allow_nan=False,indent=2)+"\n")
class Data:
 def __init__(self,folder="coins",metadata="metadata"):
  files=sorted(Path(folder).glob("*.npz"));manifest={}
  for p in Path(metadata).rglob("DATA_INVENTORY.json"):
   for r in json.load(p.open()):
    if r["status"]=="AVAILABLE":manifest[r["symbol"]]=r["npz_sha256"]
  self.symbols=[p.stem for p in files];self.times=np.arange(ms("2025-10-01"),ms("2026-11-01")+H,H,dtype=np.int64);n=len(files);T=len(self.times);self.spot=np.full((n,T,4),np.nan);self.perp=np.full((n,T,4),np.nan);self.mark=np.full((n,T,4),np.nan);self.latest=np.full((T,n),np.nan);self.previous=self.latest.copy();self.avg72=self.latest.copy();self.fresh=np.zeros((T,n),bool);self.cover=np.zeros((T,n),bool);self.cashrate=np.zeros((T,n));self.hashes={};self.issues=[]
  for j,p in enumerate(files):
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   if manifest and manifest.get(p.stem)!=digest:raise ValueError("SOURCE_CACHE_SHA_MISMATCH:"+p.stem)
   self.hashes[p.stem]=digest;z=np.load(p,allow_pickle=False)
   for k in["spot","perp","mark"]:
    a=z[k];ix=((a[:,0]-self.times[0])//H).astype(int);ok=(ix>=0)&(ix<T);getattr(self,k)[j,ix[ok]]=a[ok,1:5]
   f=z["funding"];ts=f[:,0];interval=f[:,1];rate=f[:,2]
   if np.any(np.diff(ts)<=0)or np.any(interval<=0)or np.any(~np.isfinite(f)):raise ValueError("BAD_FUNDING_ROWS:"+p.stem)
   norm=rate*8/interval;idx=np.searchsorted(ts,self.times,side="left")-1;valid=idx>=0;ii=np.maximum(idx,0);self.latest[valid,j]=norm[ii[valid]];prev=idx>=1;self.previous[prev,j]=norm[ii[prev]-1];self.fresh[valid,j]=(self.times[valid]-ts[ii[valid]])<=1.5*interval[ii[valid]]*H
   left=np.searchsorted(ts,self.times-72*H,side="left");right=np.searchsorted(ts,self.times,side="left");cr=np.r_[0,np.cumsum(rate)];ch=np.r_[0,np.cumsum(interval)];weight=ch[right]-ch[left];good=(weight>=64)&(weight<=80)&self.fresh[:,j];self.avg72[good,j]=(cr[right[good]]-cr[left[good]])*8/weight[good]
   for a,b in z["coverage"]:self.cover[(self.times>=a)&(self.times+H<=b),j]=True
   bucket=((ts-self.times[0])//H).astype(int)
   for k,r in zip(bucket,rate):
    if 0<=k<T:self.cashrate[k,j]+=r
  self.index={s:i for i,s in enumerate(self.symbols)}
 def quote(self,kind,j,i):
  if i<0 or i>=len(self.times):return None
  a=getattr(self,kind)[j,i];return a if np.all(np.isfinite(a))else None

def trade_return(q,S0,P0,S1,P1,fund,fees):return q*((S1-S0)+(P0-P1))+fund-fees

def simulate(d,variant,leverage,period,slip=.0005,mmr=.005,min_notional=0):
 start,end=PERIODS[period];si=int(np.searchsorted(d.times,start));ei=int(np.searchsorted(d.times,end));cash=100.;pos={};equity=[dict(time_ms=start,equity=100.)];events=[];trades=[];stats=dict(funding_cash=0.,spot_price_PnL=0.,perp_price_PnL=0.,fees=0.,slippage_cost=0.,liquidation_penalty=0.,margin_below50_episodes=0,proxy_liquidations=0,mark_proxy_hours=0,funding_unknown_position_hours=0,position_hours=0,order_filter_rejected=0,maker_missed=0,maker_unhedged_aborts=0,maker_touch_assumption=variant=="FC5");gap=None;nextid=0;minmargin=1.;min_equity_notional=1.;maxnav=100.;dd=0.;ddbound=0.;pending_abort=[];cooldown=set()
 def quote(j,i,kind="spot"):
  return d.quote(kind,j,i)
 def mark(j,i):
  a=quote(j,i,"mark")
  if a is None:
   a=quote(j,i,"perp");stats["mark_proxy_hours"]+=int(a is not None)
  return a
 def total(i,field=0):
  value=cash
  for j,p in pos.items():
   s=quote(j,i);m=mark(j,i)
   if s is None or m is None:return None
   sp=p["sx"]if p["sx"]is not None else s[field]
   pp=p["px"]if p["px"]is not None else m[2 if field==2 else field]
   value+=p["q"]*sp+p["margin"]+p["fund"]+p["q"]*(p["pe"]-pp)-p["exitfees"]
  return value
 def exit_leg(p,leg,price,fee,t,kind):
  key="sx"if leg=="spot"else"px"
  if p[key]is not None:return
  p[key]=float(price);f=p["q"]*price*fee;p["exitfees"]+=f;stats["fees"]+=f;events.append(dict(time_ms=t,trade=p["id"],symbol=d.symbols[p["j"]],event="EXIT_"+leg,price=price,q=p["q"],fee=f,kind=kind))
 def finish(j,t,reason):
  nonlocal cash
  p=pos[j]
  if p["sx"]is None or p["px"]is None:return
  returned=p["q"]*p["sx"]+p["margin"]+p["fund"]+p["q"]*(p["pe"]-p["px"])-p["exitfees"];cash+=returned;sp=p["q"]*(p["sx"]-p["se"]);pp=p["q"]*(p["pe"]-p["px"]);stats["spot_price_PnL"]+=sp;stats["perp_price_PnL"]+=pp;trades.append(dict(id=p["id"],symbol=d.symbols[j],entry_ms=p["t"],exit_ms=t,spot_entry=p["se"],perp_entry=p["pe"],spot_exit=p["sx"],perp_exit=p["px"],quantity=p["q"],initial_short_margin=p["margin"],funding=p["fund"],fees=p["entryfees"]+p["exitfees"],net=returned-p["reserved"],basis_entry=(p["pe"]-p["se"])/p["se"],basis_exit=(p["px"]-p["sx"])/p["sx"],reason=reason));del pos[j]
 def market_close(j,i,t,reason,terminal=False):
  p=pos[j];s=quote(j,i);pp=quote(j,i,"perp");k=3 if terminal else 0
  if s is None or pp is None:return False
  if p["sx"]is None:stats["slippage_cost"]+=p["q"]*s[k]*slip;exit_leg(p,"spot",s[k]*(1-slip),.001,t,reason)
  if p["px"]is None:stats["slippage_cost"]+=p["q"]*pp[k]*slip;exit_leg(p,"perp",pp[k]*(1+slip),.00055,t,reason)
  finish(j,t,reason);return True
 for i in range(si,ei):
  t=int(d.times[i]);closed_this_hour=set()
  # Existing positions receive/debit current-hour payout before new orders.
  for j,p in list(pos.items()):
   if quote(j,i)is None or quote(j,i,"perp")is None:
    gap=dict(time_ms=t,symbol=d.symbols[j],reason="HELD_LEG_PRICE_GAP");break
   stats["position_hours"]+=1
   if not d.cover[i,j]or not d.fresh[i,j]:stats["funding_unknown_position_hours"]+=1
   if p["px"]is None and i>p["entry_i"]:
    a=mark(j,i);rate=d.cashrate[i,j]
    if a is not None and rate:
     payment=p["q"]*a[0]*rate;p["fund"]+=payment;stats["funding_cash"]+=payment;events.append(dict(time_ms=t,trade=p["id"],symbol=d.symbols[j],event="FUNDING",raw_rate=rate,mark_proxy=a[0],cash=payment))
   if p.get("abort_next")or p.get("liquidated"):
    if not market_close(j,i,t,p.get("close_reason","UNHEDGED_ABORT")):gap=dict(time_ms=t,symbol=d.symbols[j],reason="NO_REAL_CLOSE_PRICE");break
    closed_this_hour.add(j)
  if gap:break
  # Cash settlements of one-legged maker entry failures.
  for a in list(pending_abort):
   if i<a["due"]:continue
   q=a["q"];j=a["j"];v=quote(j,i,a["leg"])
   if v is None:gap=dict(time_ms=t,symbol=d.symbols[j],reason="UNHEDGED_ABORT_PRICE_GAP");break
   if a["leg"]=="spot":px=v[0]*(1-slip);pnl=q*(px-a["price"]);fee=q*px*.001
   else:px=v[0]*(1+slip);pnl=q*(a["price"]-px);fee=q*px*.00055
   cash+=a["reserved"]+pnl-fee;stats["fees"]+=fee;stats["slippage_cost"]+=q*v[0]*slip;events.append(dict(time_ms=t,symbol=d.symbols[j],event="UNHEDGED_ABORT_CLOSE",price=px,net=pnl-a["entryfee"]-fee));pending_abort.remove(a);closed_this_hour.add(j)
  if gap:break
  tradable=np.array([quote(j,i)is not None and quote(j,i,"perp")is not None for j in range(len(d.symbols))]);eligible=tradable&d.fresh[i]&d.cover[i]&np.isfinite(d.latest[i])
  if variant in["FC3","FC6"]:
   ranked=[j for j in range(len(d.symbols))if eligible[j]and np.isfinite(d.avg72[i,j])and d.avg72[i,j]>0];ranked.sort(key=lambda j:(-d.avg72[i,j],d.symbols[j]));desired=ranked[:5]if (t//H)%24==1 else None
   if desired is not None:
    for j in list(pos):
     if j not in desired:
      market_close(j,i,t,"DAILY_RANK_EXIT");closed_this_hour.add(j)
  else:
   desired=None
   for j,p in list(pos.items()):
    rate=d.latest[i,j];leave=(rate<(.0 if variant=="FC4"else .0001))or(variant in["FC1","FC5"]and t-p["t"]>=168*H)
    if leave or p.get("exit_requested"):
     if variant!="FC5":market_close(j,i,t,"RATE_OR_TIME_EXIT");closed_this_hour.add(j)
     else:
      p["exit_requested"]=True;s=quote(j,i);pp=quote(j,i,"perp");prevs=quote(j,i-1);prevp=quote(j,i-1,"perp")
      if prevs is None or prevp is None:continue
      if p["sx"]is None and prevs[3]>s[0]and s[2]<=prevs[3]<=s[1]:exit_leg(p,"spot",prevs[3],.001,t+H-1,"MAKER_TOUCH")
      if p["px"]is None and prevp[3]<pp[0]and pp[2]<=prevp[3]<=pp[1]:exit_leg(p,"perp",prevp[3],.0002,t+H-1,"MAKER_TOUCH")
      if p["sx"]is not None and p["px"]is not None:finish(j,t+H-1,"MAKER_PAIR_EXIT");closed_this_hour.add(j)
      elif p["sx"]is not None or p["px"]is not None:p["abort_next"]=True;p["close_reason"]="MAKER_EXIT_UNHEDGED_ABORT";stats["maker_unhedged_aborts"]+=1
  # Open only after exits. Do not reopen the same coin in its exit hour.
  if variant in["FC3","FC6"]:open_candidates=[]if desired is None else[j for j in desired if j not in pos and j not in closed_this_hour]
  elif pos or pending_abort:open_candidates=[]
  else:
   condition=eligible.copy()
   if variant in["FC1","FC5"]:condition&=(d.latest[i]>=.0003)&(d.previous[i]>=.0003)
   elif variant=="FC2":condition&=d.latest[i]>=.0005
   elif variant=="FC4":condition&=(d.latest[i]>=.0001)&np.array([s in["BTCUSDT","ETHUSDT","SOLUSDT"]for s in d.symbols])
   choices=[j for j in range(len(d.symbols))if condition[j]and j not in closed_this_hour];choices.sort(key=lambda j:(-d.latest[i,j],d.symbols[j]));open_candidates=choices[:1]
  nav=total(i)
  if nav is None:gap=dict(time_ms=t,reason="CANNOT_MARK_HELD_PORTFOLIO");break
  per_slot=nav/5 if variant in["FC3","FC6"]else cash
  for j in open_candidates:
   if cash<=0 or per_slot<=0:break
   s=quote(j,i);pp=quote(j,i,"perp")
   if variant=="FC6"and abs(pp[0]/s[0]-1)>.001:continue
   maker=variant=="FC5";sf=.001;pf=.0002 if maker else .00055;ps=quote(j,i-1)if maker else None;pprev=quote(j,i-1,"perp")if maker else None
   if maker and(ps is None or pprev is None):continue
   se=ps[3]if maker else s[0]*(1+slip);pe=pprev[3]if maker else pp[0]*(1-slip);budget=min(cash,per_slot);q=budget/(se*(1+sf)+pe/leverage+pe*pf)
   if min(q*se,q*pe)<min_notional:stats["order_filter_rejected"]+=1;continue
   entryfee=q*(se*sf+pe*pf);reserved=q*se+q*pe/leverage+entryfee
   if maker:
    st=se<s[0]and s[2]<=se<=s[1];pt=pe>pp[0]and pp[2]<=pe<=pp[1]
    if not(st and pt):
     stats["maker_missed"]+=1
     if st or pt:
      leg="spot"if st else"perp";price=se if st else pe;fee=q*price*(sf if st else pf);cash-=reserved;cash-=fee;stats["fees"]+=fee;pending_abort.append(dict(due=i+1,j=j,leg=leg,price=price,q=q,reserved=reserved,entryfee=fee));stats["maker_unhedged_aborts"]+=1
     continue
   cash-=reserved;stats["fees"]+=entryfee
   if not maker:stats["slippage_cost"]+=q*(s[0]+pp[0])*slip
   p=dict(j=j,id=nextid,q=q,se=float(se),pe=float(pe),margin=q*pe/leverage,fund=0.,entryfees=entryfee,exitfees=0.,reserved=reserved,t=t,entry_i=i,sx=None,px=None,below50=False);nextid+=1;pos[j]=p;events.append(dict(time_ms=t,trade=p["id"],symbol=d.symbols[j],event="OPEN_PAIR",quantity=q,spot_price=se,perp_price=pe,basis=pe/se-1,collateral=p["margin"],fees=entryfee,maker=maker))
  # Isolated short cannot use unrealised spot profit as collateral.
  bound=cash
  for j,p in list(pos.items()):
   s=quote(j,i);mk=mark(j,i);pp=quote(j,i,"perp")
   if s is None or mk is None or pp is None:gap=dict(time_ms=t,symbol=d.symbols[j],reason="PRICE_GAP");break
   bound+=p["q"]*(p["sx"]if p["sx"]is not None else s[2])+p["margin"]+p["fund"]+p["q"]*(p["pe"]-(p["px"]if p["px"]is not None else mk[1]))-p["exitfees"]
   if p["px"]is None:
    balance=p["margin"]+p["fund"]-p["q"]*(mk[1]-p["pe"]);ratio=balance/p["margin"];minmargin=min(minmargin,ratio);min_equity_notional=min(min_equity_notional,balance/(p["q"]*mk[1]));below=ratio<.5
    if below and not p["below50"]:stats["margin_below50_episodes"]+=1
    p["below50"]=below;barrier=(p["margin"]+p["fund"]+p["q"]*p["pe"])/(p["q"]*(1+mmr))
    if mk[1]>=barrier:
     px=max(pp[0],barrier)*(1+slip);exit_leg(p,"perp",px,.00055,t+H-1,"MMR_PROXY_LIQUIDATION");penalty=p["q"]*px*.005;p["exitfees"]+=penalty;stats["liquidation_penalty"]+=penalty;stats["proxy_liquidations"]+=1;p["liquidated"]=True;p["close_reason"]="PROXY_LIQUIDATION_SPOT_UNWIND_NEXT_HOUR";events.append(dict(time_ms=t+H-1,trade=p["id"],symbol=d.symbols[j],event="LIQUIDATION_PROXY",mark_barrier=barrier,assumed_perp_fill=px,inside_trade_hour_bounds=bool(pp[2]<=px/(1+slip)<=pp[1]),penalty=penalty))
  if gap:break
  ddbound=max(ddbound,(maxnav-bound)/maxnav*100 if maxnav>0 else 0.)
  if i==ei-1:
   for j in list(pos):market_close(j,i,end-1,"FIXED_PERIOD_TERMINAL_CASHOUT",terminal=True)
   # Emergency unwind of one-legged entry attempted in the final bar, real final close only.
   for a in list(pending_abort):
    v=quote(a["j"],i,a["leg"]);px=v[3]*(1-slip if a["leg"]=="spot"else 1+slip);pnl=a["q"]*(px-a["price"])*(1 if a["leg"]=="spot"else-1);fee=a["q"]*px*(.001 if a["leg"]=="spot"else .00055);cash+=a["reserved"]+pnl-fee;stats["fees"]+=fee;pending_abort.remove(a)
   nav=cash
  else:nav=total(i+1)
  if nav is None:gap=dict(time_ms=t+H,reason="NEXT_MARK_UNAVAILABLE");break
  maxnav=max(maxnav,nav);dd=max(dd,100*(maxnav-nav)/maxnav);equity.append(dict(time_ms=t+H,equity=nav))
 # A missing held quote censors the run; never invent a tradable close.
 status="COMPLETE"if gap is None else"INCONCLUSIVE_DATA_GAP"
 months={}
 for r in equity:
  day=dt.datetime.fromtimestamp(r["time_ms"]/1000,dt.timezone.utc);key=day.strftime("%Y-%m");months.setdefault(key,[]).append(r)
 monthly=[];lookup={r["time_ms"]:r["equity"]for r in equity}
 a=dt.datetime.fromtimestamp(start/1000,dt.timezone.utc).replace(day=1)
 while int(a.timestamp()*1000)<end:
  b=(a.replace(day=28)+dt.timedelta(days=4)).replace(day=1);l=max(start,int(a.timestamp()*1000));r=min(end,int(b.timestamp()*1000));full=l==int(a.timestamp()*1000)and r==int(b.timestamp()*1000);available=l in lookup and r in lookup;monthly.append(dict(month=a.strftime("%Y-%m"),start_ms=l,end_ms=r,complete_calendar_month=full,observed=available,profit_USD=lookup[r]-lookup[l]if available else None));a=b
 full=[r["profit_USD"]for r in monthly if r["complete_calendar_month"]and r["observed"]];days=(equity[-1]["time_ms"]-start)/DAY;final=equity[-1]["equity"];summary=dict(variant=variant,leverage=leverage,period=period,status=status,gap=gap,net_USD=final-100,return_pct=final-100,annualized_simple_pct=(final-100)*365/days if days else None,annualized_geometric_pct=100*((final/100)**(365/days)-1)if days and final>0 else None,monthly_mean_USD=float(np.mean(full))if full else None,monthly_median_USD=float(np.median(full))if full else None,worst_month_USD=float(min(full))if full else None,full_observed_months=len(full),n_closed_pairs=len(trades),maxDD_hourly_pct=dd,maxDD_intrahour_envelope_pct=ddbound,min_short_margin_remaining_ratio=minmargin,min_short_equity_to_current_notional=min_equity_notional,fees_over_positive_funding=stats["fees"]/stats["funding_cash"]if stats["funding_cash"]>0 else None,liquidation_mmr_assumption=mmr,continuous_quantity_model=True,Bybit_filters_available=False,**stats)
 return dict(summary=finite(summary),monthly=monthly,trades=finite(trades),events=finite(events),equity=finite(equity))
