"""Offline PF model audit. No bot imports, network, keys or order interface."""
import argparse,collections,csv,datetime as dt,gzip,hashlib,json,math,random,subprocess
from pathlib import Path
LAB=Path(__file__).parent;I=LAB/'inputs';H=3600000;S=300000
START=1762930800000;END=1794466800000;HALF=1778698800000;TAIL=1781852400000
ASOF=int(dt.datetime(2026,11,16,tzinfo=dt.timezone.utc).timestamp()*1000)
def readlines(p):return [json.loads(x) for x in gzip.open(p,'rt')]
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def gzsave(p,rs):
 with gzip.open(p,'wt') as f:
  for r in rs:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
def load_frames():
 frames=collections.defaultdict(dict);bad=set();n=0
 with gzip.open(I/'BYBIT_RESEARCH_5M.csv.gz','rt') as f:
  reader=csv.DictReader(f)
  if set(reader.fieldnames)!={'symbol','signal_ms','ts','open','high','low','close','volume','turnover'}:raise ValueError('UNEXPECTED_SOURCE_FIELDS')
  for r in reader:
   n+=1;sym=r['symbol'];t=int(r['ts'])
   if t<START or t+S>END:continue
   if (sym,t) in bad:continue
   b=tuple(float(r[k]) for k in ['open','high','low','close'])
   if t%S or not all(math.isfinite(x) and x>0 for x in b) or b[2]>min(b[0],b[3]) or b[1]<max(b[0],b[3]):continue
   old=frames[sym].get(t)
   if old is not None and old!=b:bad.add((sym,t));frames[sym].pop(t);continue
   frames[sym][t]=b
 return frames,dict(source_rows=n,symbols=len(frames),conflicting_symbol_timestamps=len(bad),unique_valid_rows=sum(map(len,frames.values())))
def replay(frame,t,limit,be_offset=0.):
 p=dict(status='RIGHT_CENSORED',signal_ms=t)
 if t+80*H>END:return p
 pending=[frame.get(x) for x in range(t,t+8*H,S)]
 if any(x is None for x in pending):p['status']='DATA_GAP_ENTRY_5M';return p
 hit=next((j for j,b in enumerate(pending) if b[1]>=limit),None)
 if hit is None:p['status']='NOFILL';return p
 et=t+hit*S;entry=max(limit,pending[hit][0]);bars=[(x,frame.get(x)) for x in range(et,et+72*H,S)]
 if any(b is None for x,b in bars):p.update(status='DATA_GAP_HOLD_5M',entry_ms=et);return p
 stop=entry*1.056;tp=[entry*(1-r) for r in [.021,.042,.063]];weights=[.5,.3,.2];left=1.;k=0;events=[];gross=0.;fillamb=False;beamb=False
 for j,(bt,(op,hi,lo,cl)) in enumerate(bars):
  if hi>=stop:
   price=max(stop,op);gross+=(1-price/entry)*left;events.append(dict(time_ms=bt+S,kind='SL' if k==0 else 'BE',price=price,fraction=left));left=0.;break
  if j==0 and lo<=tp[0]:fillamb=True
  if j>0:
   before=k
   while k<3 and lo<=tp[k]:
    q=weights[k];gross+=(1-tp[k]/entry)*q;events.append(dict(time_ms=bt+S,kind='TP'+str(k+1),price=tp[k],fraction=q));left-=q;k+=1
   if k>before:
    if before==0 and left>1e-9 and hi>=entry*(1-be_offset):beamb=True
    stop=entry*(1-be_offset)
   if left<1e-9:left=0.;break
  if j==len(bars)-1:gross+=(1-cl/entry)*left;events.append(dict(time_ms=bt+S,kind='TIME',price=cl,fraction=left));left=0.
 assert left==0 and abs(sum(e['fraction'] for e in events)-1)<1e-8
 return dict(status='CLOSED',signal_ms=t,entry_ms=et,exit_ms=events[-1]['time_ms'],entry=entry,limit=limit,gross_return=gross,events=events,fill_bar_tp_ambiguous=fillamb,new_be_samebar_ambiguous=beamb)
def cash_R(r,f):
 if not f['known'] or r['status']!='CLOSED':return None
 cash=0.
 for pay in f['payments']:
  t=pay['time_ms'];rate=pay['rate'];credit=rate>0
  if not r['entry_ms']<=t<=r['exit_ms'] or t==r['entry_ms'] and credit:continue
  rem=1-sum(e['fraction'] for e in r['events'] if e['time_ms']<(t+1 if credit else t))
  cash+=rate*pay['mark']/r['entry']*max(0,rem)/.0581
 return cash

def economics(r,f):
 r=dict(r);r['net_R']=None
 if r['status']!='CLOSED':return r
 legs=1+sum(e['fraction']*e['price']/r['entry'] for e in r['events']);r['fee_R']=.00055*legs/.0581;r['slippage_R']=.0005*legs/.0581;r['price_R']=(r['gross_return']-.00105*legs)/.0581;r['funding_R']=cash_R(r,f);r['hold_hours']=(r['exit_ms']-r['entry_ms'])/H
 if r['funding_R'] is not None:r['net_R']=r['price_R']+r['funding_R']
 return r

def differences(a,b):
 errors=[]
 if a['status']!=b['status']:return ['STATUS']
 if a['status']!='CLOSED':return errors
 for key in ['entry_ms','exit_ms','entry','gross_return']:
  if key.endswith('_ms'):
   if a[key]!=b[key]:errors.append(key)
  elif not math.isclose(a[key],b[key],abs_tol=1e-12,rel_tol=1e-11):errors.append(key)
 if len(a['events'])!=len(b['events']):errors.append('EVENT_COUNT')
 else:
  for x,y in zip(a['events'],b['events']):
   if x['kind']!=y['kind'] or x['time_ms']!=y['time_ms'] or not math.isclose(x['price'],y['price'],rel_tol=1e-11,abs_tol=1e-12) or not math.isclose(x['fraction'],y['fraction'],abs_tol=1e-12):errors.append('EVENT')
 return errors

def series_probability(p,n=13):
 return dict(exact12=13*p**12*(1-p),at_least12=13*p**12*(1-p)+p**13,all13=p**13)
def beta_binomial(k,n,a,b):
 def lb(x,y):return math.lgamma(x)+math.lgamma(y)-math.lgamma(x+y)
 return math.exp(math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)+lb(a+k,b+n-k)-lb(a,b))
def metrics(rows):
 closed=sorted([x for x in rows if x['status']=='CLOSED'],key=lambda x:(x['exit_ms'],x['id']));known=[x for x in closed if x['net_R'] is not None];v=[x['net_R'] for x in known];net=sum(v);gain=sum(x for x in v if x>0);loss=-sum(x for x in v if x<0);peak=0.;eq=0.;dd=0.
 for x in v:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
 n=len(v);wins=sum(x>0 for x in v);prob=None
 if n:
  p=wins/n;z=1.959963984540054;den=1+z*z/n;center=(p+z*z/(2*n))/den;rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
  prob=dict(p=p,n_model=n,wins=wins,**series_probability(p),p_Wilson95=[center-rad,center+rad],at_least12_Wilson_range=[series_probability(center-rad)['at_least12'],series_probability(center+rad)['at_least12']],Jeffreys_predictive_at_least12=sum(beta_binomial(k,13,wins+.5,n-wins+.5) for k in [12,13]),assumption='conditional iid Bernoulli; not P(model correct), not adjusted for selection/correlation')
 return dict(opportunities=len(rows),closed_n=len(closed),known_n=n,unknown_funding_n=len(closed)-n,nofill=sum(x['status']=='NOFILL' for x in rows),censored=sum(x['status']=='RIGHT_CENSORED' for x in rows),WR_percent=100*wins/n if n else None,PF=gain/loss if loss else None,net_R=net,price_R_known=sum(x['price_R'] for x in known),funding_R_known=sum(x['funding_R'] for x in known),maxDD_R=dd,mean_R=net/n if n else None,mean_win_R=gain/wins if wins else None,mean_loss_R=-loss/(n-wins) if n>wins else None,best3_share_net=sum(sorted(v,reverse=True)[:3])/net if net>0 else None,probability_12_of_13=prob,fill_bar_tp_ambiguous_n=sum(bool(x.get('fill_bar_tp_ambiguous')) for x in closed),be_same_bar_ambiguous_n=sum(bool(x.get('new_be_samebar_ambiguous')) for x in closed))
PERIODS=[('FULL',START,END),('H1_PURGED',START,HALF),('H2',HALF,END),('TAIL40',TAIL,END),('RECENT30_REQUESTED',ASOF-30*24*H,ASOF),('LIVE_WINDOW_REQUESTED',int(dt.datetime(2026,10,23,tzinfo=dt.timezone.utc).timestamp()*1000),ASOF)]
def table(rows,reference):
 out=[]
 for cohort in ['RAW','SELECTED_DESCRIPTIVE']:
  source=rows if cohort=='RAW' else [r for r in rows if r['selected']]
  for period,a,b in PERIODS:
   chosen=[r for r in source if a<=r['signal_ms']<b and not(period=='H1_PURGED' and reference[r['id']].get('status')=='CLOSED' and reference[r['id']]['exit_ms']>=HALF)]
   out.append(dict(cohort=cohort,period=period,requested_start_ms=a,requested_end_ms=b,source_end_ms=END,requested_period_fully_covered=b<=END,**metrics(chosen)))
 return out

def match(signal,reference):
 exact=[r for r in reference if r['symbol']==signal['symbol'] and r['signal_ms']==signal.get('signal_ms')]
 if len(exact)==1:return 'EXACT',exact[0]
 t=signal.get('signal_ms') or signal.get('created_ms')
 if t is None:return 'DATA_GAP_SIGNAL_TIME',None
 near=[r for r in reference if r['symbol']==signal['symbol'] and abs(r['signal_ms']-t)<=H]
 if len(near)==1:return 'UNIQUE_WITHIN_1H',near[0]
 return ('AMBIGUOUS' if len(near)>1 else 'DATA_GAP_WINDOW' if not START<=t<END else 'NOT_IN_SAVED_ARCHIVE'),None

def reconciliation(reference,old,new,out):
 source=json.loads((I/'LIVE_TRADES_AGGREGATES.json').read_text());dec=json.loads((I/'LIVE_DECISIONS_AGGREGATES.json').read_text());cards=json.loads((I/'SNAPSHOT_SIGNAL_CARDS.json').read_text());byid={r['id']:r for r in old};newid={r['id']:r for r in new};paired=[];cardpairs=[]
 for card in cards['rows']:
  state,r=match(card,reference);x=dict(symbol=card['symbol'],signal_ms=card.get('signal_ms'),created_ms=card.get('created_ms'),match_status=state,is_live_trade=False)
  if r:
   a=byid[r['id']];x.update(model_id=r['id'],OLD_status=a['status'],OLD_entry_ms=a.get('entry_ms'),OLD_net_R=a.get('net_R'),BE_ALIGNED_net_R=newid[r['id']].get('net_R'),model_fill_precedes_card_creation=a.get('entry_ms') is not None and a['entry_ms']<card['created_ms'])
  cardpairs.append(x)
 for live in source['rows']:
  state,r=match(live,reference);x=dict(symbol=live['symbol'],signal_ms=live.get('signal_ms'),live_net_R=live.get('net_R'),match_status=state)
  if r:x.update(model_id=r['id'],model_OLD=byid[r['id']],model_BE_ALIGNED=newid[r['id']])
  paired.append(x)
 recent=[r for r in old if ASOF-30*24*H<=r['signal_ms']<ASOF];unreconciled=[dict(id=r['id'],symbol=r['symbol'],signal_ms=r['signal_ms'],selected=r['selected'],model_status=r['status'],model_entry_ms=r.get('entry_ms'),live_status='UNOBSERVED_NOT_CONFIRMED_SKIPPED') for r in recent]
 save(out/'RECONCILIATION.json',dict(expected_live_closed=13,available_live_closed_rows=len(source['rows']),live_trade_source_status=source['status'],trade_pairs=paired,snapshot_signal_pairs=cardpairs,reverse_reconciliation_status='DATA_GAP_COMPLETE_LIVE_DECISIONS_REQUIRED',decision_log_coverage_complete=dec.get('coverage_complete',False),requested_recent30_end_ms=ASOF,history_end_ms=END,missing_window_ms=max(0,ASOF-END)))
 gzsave(out/'RECENT30_UNRECONCILED_MODEL_SIGNALS.jsonl.gz',unreconciled)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(LAB/'RESULTS'));a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 reference=readlines(I/'REFERENCE_EXECUTIONS.jsonl.gz');byid={r['id']:r for r in reference};fund={r['id']:r for r in readlines(I/'FUNDING_EVENTS.jsonl.gz')};frames,inv=load_frames();save(out/'INPUT_AUDIT.json',inv);old=[];errors=[]
 for r in reference:
  v=replay(frames.get(r['symbol'],{}),r['signal_ms'],r['limit']);err=differences(r,v)
  if err:errors.append(dict(id=r['id'],errors=err,reference_status=r['status'],reproduced_status=v['status']))
  v.update(id=r['id'],symbol=r['symbol'],selected=r['selected']);v=economics(v,fund[r['id']]);old.append(v)
  if v['status']=='CLOSED' and fund[r['id']]['known'] and not math.isclose(v['funding_R'],fund[r['id']]['reference_cash_R'],rel_tol=1e-10,abs_tol=1e-10):errors.append(dict(id=r['id'],errors=['FUNDING_REFERENCE_PARITY']))
 save(out/'BASELINE_PARITY.json',dict(status='PASS' if not errors else 'FAIL_CLOSED',reference_n=len(reference),reproduced_n=len(old),errors=errors))
 if errors:save(out/'CHECKPOINT.json',dict(stage='BASELINE_PARITY_FAILED_CORRECTION_NOT_RUN',errors=len(errors)));raise RuntimeError('Baseline differs; no corrected PnL allowed')
 new=[];changes=[]
 for r,prev in zip(reference,old):
  v=replay(frames.get(r['symbol'],{}),r['signal_ms'],r['limit'],.0011);v.update(id=r['id'],symbol=r['symbol'],selected=r['selected']);v=economics(v,fund[r['id']]);new.append(v)
  if prev['status']=='CLOSED':assert v['entry_ms']==prev['entry_ms'] and v['entry']==prev['entry'] and v['exit_ms']<=prev['exit_ms']
  if differences(prev,v):changes.append(dict(id=r['id'],symbol=r['symbol'],signal_ms=r['signal_ms'],old_exit_ms=prev.get('exit_ms'),new_exit_ms=v.get('exit_ms'),old_price_R=prev.get('price_R'),new_price_R=v.get('price_R'),old_net_R=prev.get('net_R'),new_net_R=v.get('net_R')))
 oldtables=table(old,byid);newtables=table(new,byid);gzsave(out/'OLD_REPRODUCED.jsonl.gz',old);gzsave(out/'BE_ALIGNED_5M.jsonl.gz',new);save(out/'TABLES.json',dict(OLD=oldtables,BE_ALIGNED=newtables));save(out/'CHANGES.json',changes);reconciliation(reference,old,new,out)
 controls=[];rng=random.Random(20261116)
 for cohort in ['RAW','SELECTED_DESCRIPTIVE']:
  for name,lo,hi in PERIODS[:4]:
   blocks=collections.defaultdict(float)
   for x,y in zip(old,new):
    if not lo<=x['signal_ms']<hi or cohort!='RAW' and not x['selected'] or x.get('net_R') is None or y.get('net_R') is None or name=='H1_PURGED' and x['exit_ms']>=HALF:continue
    blocks[(x['signal_ms']//(7*24*H))]+=y['net_R']-x['net_R']
   delta=sum(blocks.values());dist=[sum(v if rng.randrange(2) else -v for v in blocks.values()) for _ in range(1000)]
   controls.append(dict(cohort=cohort,period=name,delta_R=delta,weekly_blocks=len(blocks),draws=1000,p_two_sided=(1+sum(abs(v)>=abs(delta) for v in dist))/1001,kind='PAIRED_WEEKLY_BE_MODEL_SENSITIVITY_NOT_ALPHA_PROOF',null_delta_R=dist))
 save(out/'CONTROLS.json',controls);save(out/'CHECKPOINT.json',dict(stage='HISTORY_BE_COMPONENT_AUDITED_LIVE_RECONCILIATION_BLOCKED',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),reference_n=len(reference),baseline_parity='PASS',changed_outcomes=len(changes),live_rows_available=0,expected_live_rows=13,profitability='NOT_PROVEN',no_runtime_changes=True));print(json.dumps(dict(parity='PASS',reference=len(reference),changed=len(changes),RAW_FULL_OLD=oldtables[0],RAW_FULL_BE_ALIGNED=newtables[0]),indent=2))
if __name__=='__main__':main()
