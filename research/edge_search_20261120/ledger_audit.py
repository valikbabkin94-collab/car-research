"""Frozen post-selection economics audit, not a new trade/bar simulation.
Input is a numeric derivative; no network, keys, broker, Telegram or runtime imports.
"""
import json,math,hashlib,datetime as dt,statistics,random,time,os
from pathlib import Path
from collections import Counter,defaultdict
LAB=Path(__file__).parent;DAY=86400000;MONTH=365.25/12*DAY;SEED=20261120;REPS=9999

def save(name,x):
 p=LAB/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def iso(ms):return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).isoformat()
def ms(s):return int(dt.datetime.fromisoformat(s).timestamp()*1000)
def quantile(v,q):
 if not v:return None
 v=sorted(v);i=(len(v)-1)*q;a=int(i);b=min(a+1,len(v)-1);return v[a]+(v[b]-v[a])*(i-a)
def width(r):
 e,s=r['entry'],r['initial_stop']
 if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>0 for x in [e,s]) or e==s:raise ValueError('INVALID_ENTRY_STOP')
 if r['side']=='LONG' and s>=e or r['side']=='SHORT' and s<=e:raise ValueError('WRONG_STOP_SIDE')
 return abs(e-s)/e

def adjust(r,cost_bp):
 # Original source formula: (gross-.0021*entry)/abs(entry-initialSL).
 return r['source_post21bp_R']-(cost_bp-21)*.0001/width(r)
def closed(r):return r['source_status']=='MATCHED' and r['model_status']=='TRADE'
def metric(rows,cost):
 v=sorted([r for r in rows if closed(r)],key=lambda r:(r['exit_ms'],r['fill_ms'],r['key']))
 xs=[adjust(r,cost)for r in v];pos=sum(x for x in xs if x>0);neg=-sum(x for x in xs if x<0);eq=peak=dd=0.
 for x in xs:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
 return {'model_closed_n':len(v),'price_cost_R':sum(xs),'mean_price_cost_R':statistics.mean(xs)if xs else None,
         'PF_price_cost_only':pos/neg if neg else None,'win_rate_pct':100*sum(x>0 for x in xs)/len(xs)if xs else None,
         'close_order_maxDD_R':dd,'unknown_funding_closed_n':len(v),'true_net_R':None,
         'no_fill_n':sum(r['source_status']=='MATCHED' and r['model_status']=='NOFILL'for r in rows),
         'all_source_opportunities':len(rows),'root_statuses':dict(Counter(r['source_status']for r in rows)),
         'matched_model_statuses':dict(Counter(str(r['model_status'])for r in rows if r['source_status']=='MATCHED'))}

def groups(rows,cost,kind):
 d=defaultdict(float)
 for r in rows:
  if not closed(r):continue
  if kind=='symbol':key=r['symbol']
  else:
   t=dt.datetime.fromtimestamp(r['exit_ms']/1000,dt.timezone.utc)
   if kind=='day':key=t.strftime('%Y-%m-%d')
   elif kind=='week':key=(t-dt.timedelta(days=t.weekday())).strftime('%Y-%m-%d')
   else:key=t.strftime('%Y-%m')
  d[key]+=adjust(r,cost)
 return dict(d)
def concentration(rows,cost,kind):
 d=groups(rows,cost,kind);total=sum(d.values());best=sorted(d.items(),key=lambda x:(-x[1],x[0]))
 loo={k:total-v for k,v in d.items()}
 return {'groups':d,'total_price_cost_R':total,'best1':best[:1],'best3':best[:3],
         'best1_share_of_net':best[0][1]/total if total>0 and best else None,
         'best3_share_of_net':sum(v for _,v in best[:3])/total if total>0 else None,
         'without_best1_R':total-sum(v for _,v in best[:1]),'without_best3_R':total-sum(v for _,v in best[:3]),
         'leave_one_group_out_R':loo,'leave_one_out_min_R':min(loo.values())if loo else None}

def bootstrap(rows,cost,kind):
 blocks=defaultdict(list)
 for r in rows:
  if not closed(r):continue
  t=dt.datetime.fromtimestamp(r['exit_ms']/1000,dt.timezone.utc)
  key=r['symbol'] if kind=='coin' else (t-dt.timedelta(days=t.weekday())).strftime('%Y-%m-%d')
  blocks[key].append(adjust(r,cost))
 vals=[(sum(v),len(v))for k,v in sorted(blocks.items())];rng=random.Random(SEED);draws=[]
 for rep in range(REPS):
  selected=[vals[rng.randrange(len(vals))]for _ in vals]
  if selected:draws.append(sum(s for s,n in selected)/sum(n for s,n in selected))
 return {'cluster_axis':kind,'nonempty_blocks':len(vals),'replications':REPS,'seed':SEED,
         'meanR_q05':quantile(draws,.05),'meanR_q95':quantile(draws,.95),
         'interpretation':'Descriptive exchangeable-cluster sensitivity of EXPOSED sample. Not selection-adjusted confidence, not independent-trade significance.'}

def concurrency(rows):
 events=[]
 for r in rows:
  if not closed(r):continue
  notional_per_unit=1/width(r)
  # Reserving full original notional until final close overstates remaining exposure after partials.
  events += [(r['fill_ms'],1,r['key'],notional_per_unit),(r['exit_ms'],-1,r['key'],notional_per_unit)]
 active={};peakn=0;peakfull=0.;atn=atfull=None
 for t,sign,key,n in sorted(events,key=lambda e:(e[0],e[1],e[2])):
  if sign<0:active.pop(key,None)
  else:active[key]=n
  if len(active)>peakn:peakn=len(active);atn=t
  if sum(active.values())>peakfull:peakfull=sum(active.values());atfull=t
 return {'peak_open_model_positions':peakn,'peak_positions_at_ms':atn,
         'peak_full_initial_notional_per_1USDT_R':peakfull,'peak_full_reservation_at_ms':atfull,
         'full_reserve_margin_at_10x_per_1USDT_R':peakfull/10,
         'deposit_reference_USDT':55,'reference_leverage_ceiling_not_recommendation':10,
         'actual_remaining_risk_USDT':None,'actual_leverage':None,'actual_account_equity':None,
         'interpretation':'Full original notional reserved until final exit is conservative reservation, not actual margin; no partial-fill chronology, no mark-to-market. Above55 does not prove impossibility; below55 does not prove feasibility.'}

def monthly(rows,cost,first,last):
 d=groups(rows,cost,'month');start=dt.datetime.fromtimestamp(first/1000,dt.timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0);out=[]
 while start.timestamp()*1000<=last:
  end=(start.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
  key=start.strftime('%Y-%m');full=start.timestamp()*1000>=first and end.timestamp()*1000<=last
  out.append({'month':key,'complete_source_calendar_month':full,'price_cost_R':d.get(key,0),
              'source_opportunities':sum(start.timestamp()*1000<=r['publication_ms']<end.timestamp()*1000 for r in rows),
              'model_fills':sum(closed(r)and start.timestamp()*1000<=r['fill_ms']<end.timestamp()*1000 for r in rows),
              'net_USDT':None})
  start=end
 return out

def main():
 started=time.monotonic();raw=(LAB/'inputs/targeted_numeric.json').read_bytes();data=json.loads(raw);splits=json.loads((LAB/'inputs/split_definitions.json').read_text());freeze=json.loads((LAB/'FROZEN_PROTOCOL_T2.json').read_text())
 assert len(data)<=300 and len({r['key'] for r in data})==len(data)
 allresult={};checks=[]
 for ch,model,expected_n,expected_net in [('Whalesguide','M1',72,12.39),('WolfxCrypto_VIP','M0_PROXY',54,12.84)]:
  rows=[r for r in data if r['channel']==ch and r['model']==model];sp=splits[ch];a,b=ms(sp['first_utc']),ms(sp['last_utc']);half=ms(sp['calendar_midpoint_utc']);tail=ms(sp['oos_first_utc']);months=(b-a)/MONTH
  for r in rows:
   assert a<=r['publication_ms']<=b
   if closed(r):
    width(r);assert math.isfinite(r['source_post21bp_R']) and r['publication_ms']<r['fill_ms']<r['exit_ms']
  slices={'ALL':rows,'CAL_H1':[r for r in rows if r['publication_ms']<=half],
          'CAL_H2':[r for r in rows if r['publication_ms']>half],
          'SOURCE_TRAIN60':[r for r in rows if r['source_channel_order']<=sp['train60_signals']],
          'SOURCE_LAST40':[r for r in rows if r['source_channel_order']>sp['train60_signals']]}
  original=metric(rows,21);assert original['model_closed_n']==expected_n and abs(original['price_cost_R']-expected_net)<.015
  checks.append({'cohort':ch+'_'+model,'source21bp_n_matches':True,'source21bp_rounded_sum_matches':True})
  records=[]
  for name,rs in slices.items():
   for cost in [21,35,50]:
    m=metric(rs,cost);strict=[r for r in rs if not closed(r) or name!='CAL_H1' or r['exit_ms']<=half]
    records.append({'slice':name,'total_cost_budget_bp':cost,**m,
                    'H1_cross_boundary_closed_n':sum(closed(r)and r['exit_ms']>half for r in rs) if name=='CAL_H1' else 0,
                    'strict_H1_price_cost_R':metric(strict,cost)['price_cost_R'] if name=='CAL_H1' else None})
  vs=[r for r in rows if closed(r)];notionals=[1/width(r)for r in vs]
  economics={}
  for cost in [21,35,50]:
   full=metric(rows,cost);cmonth=monthly(rows,cost,a,b)
   economics[str(cost)]={'mean_price_cost_R_per_observed_month':full['price_cost_R']/months,
     'monthly_ledger':cmonth,'worst_complete_month_price_cost_R':min([x['price_cost_R']for x in cmonth if x['complete_source_calendar_month']],default=None),
     'days':concentration(rows,cost,'day'),'coins':concentration(rows,cost,'symbol'),'weeks':concentration(rows,cost,'week')}
  stressgates={}
  for cost in [35,50]:
   slices_cost={x['slice']:x for x in records if x['total_cost_budget_bp']==cost}
   stressgates[str(cost)]={'positive_ALL':slices_cost['ALL']['price_cost_R']>0,
     'positive_calendar_both':all(slices_cost[k]['price_cost_R']>0 for k in ['CAL_H1','CAL_H2']),
     'PF13_calendar_both':all((slices_cost[k]['PF_price_cost_only']or 0)>=1.3 for k in ['CAL_H1','CAL_H2']),
     'positive_exposed_last40':slices_cost['SOURCE_LAST40']['price_cost_R']>0,
     'funding_and_independent_OOS_known':False}
  allresult[ch+'_'+model]={'source_bounds':sp,'source_statuses':dict(Counter(r['source_status']for r in rows)),
    'source_window_months':months,'archive_opportunities_per_month':len(rows)/months,'archive_matched_fills_per_month':len(vs)/months,
    'first_matched_fill_utc':iso(min(r['fill_ms']for r in vs)),'last_matched_fill_utc':iso(max(r['fill_ms']for r in vs)),
    'edited_visible_all_n':sum(r['edited_visible']for r in rows),'first_received_known_n':0,'independent_trade_n':None,
    'unique_fill_day_symbol_n':len({(iso(r['fill_ms'])[:10],r['symbol'])for r in vs}),
    'metrics':records,'economics_by_cost':economics,
    'cluster_sensitivity_35bp':[bootstrap(rows,35,'week'),bootstrap(rows,35,'coin')],
    'concurrency':concurrency(rows),'unit_risk_diagnostic':{'USDT_risk_notional_unit':1,'notional_per_unit_risk_min':min(notionals),'median':statistics.median(notionals),'p95':quantile(notionals,.95),'max':max(notionals),'actual_trade_sizing':None,'actual_lot_tick_filters':None,'no_position_size_recommendation':True},
    'gates':stressgates,'true_net_R':None,'netUSDT_per_month_at55':None,'actual_opportunities_per_month':None,
    'status':'FORWARD_PENDING_WITH_ECONOMIC_DATA_GAPS','untouched_OOS':False,'new_bar_replays':0}
  if time.monotonic()-started>60:raise RuntimeError('FROZEN_TIME_BUDGET_EXCEEDED')
 save('RESULTS.json',{'EXPERIMENT_ID':freeze['EXPERIMENT_ID'],'protocol_commit':'b21119734c7e7e2fa566124aa1e0e9e242c21cfa','code_commit':os.environ.get('EXPERIMENT_CODE_SHA'),'exposure':'EXPOSED','realized_profit_not_reconstructed':True,'inputs_sha256':hashlib.sha256(raw).hexdigest(),'cohorts':allresult,'integrity_checks':checks,'runtime_seconds':time.monotonic()-started,'live_changes':0,'market_downloads':0,'new_trade_simulations':0})
 print(json.dumps({k:{'fills':next(x['model_closed_n']for x in v['metrics']if x['slice']=='ALL' and x['total_cost_budget_bp']==21),'R_21_35_50':[x['price_cost_R']for x in v['metrics']if x['slice']=='ALL'],'fills_month':v['archive_matched_fills_per_month'],'net_USDT':None}for k,v in allresult.items()},indent=2))
if __name__=='__main__':main()
