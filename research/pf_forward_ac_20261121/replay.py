"""Offline minute-price diagnostic. No network, trading SDK, database, order or service access.
Candle touch is never promoted to an actual or guaranteed paper fill.
"""
import argparse,collections,datetime as dt,gzip,hashlib,json,math
from pathlib import Path
M=60000;H=3600000
FLAGS=('source_enabled','egress_safe','slots_available','risk_allowed','min_order_ok','symbol_available','network_ok')
def number(v):return not isinstance(v,bool)and isinstance(v,(int,float))and math.isfinite(v)
def positive(v):return number(v)and v>0
def integer(v):return isinstance(v,int)and not isinstance(v,bool)and v>=0
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_signal(s):
 for k in ('id','symbol','model_sha'):
  if not isinstance(s.get(k),str)or not s[k]:raise ValueError('missing '+k)
 for k in ('signal_ms','first_received_ms'):
  if not integer(s.get(k)):raise ValueError('invalid '+k)
 if s['first_received_ms']<s['signal_ms']:raise ValueError('receipt precedes signal')
 if not positive(s.get('reference_price')):raise ValueError('invalid reference price')
 if not isinstance(s.get('ml_passed'),bool)or s.get('filter_keep')!='top50':raise ValueError('ML evidence missing')
def bars_index(bars):
 out={}
 for b in bars:
  if not integer(b.get('ts'))or b['ts']%M:raise ValueError('unaligned minute')
  if not all(positive(b.get(k))for k in ('open','high','low','close')):raise ValueError('invalid OHLC')
  if b['low']>min(b['open'],b['close'])or b['high']<max(b['open'],b['close']):raise ValueError('invalid range')
  if b['ts']in out:raise ValueError('duplicate candle')
  out[b['ts']]=b
 return out

def gate_evidence(observation,decision_ms):
 if observation is None:return {'status':'UNKNOWN','reasons':['NO_GATE_SNAPSHOT']}
 if not integer(observation.get('asof_ms'))or observation['asof_ms']>decision_ms:return {'status':'UNKNOWN','reasons':['FUTURE_OR_INVALID_SNAPSHOT']}
 if decision_ms-observation['asof_ms']>M:return {'status':'UNKNOWN','reasons':['STALE_SNAPSHOT']}
 flags=observation.get('flags',{});blocked=[k for k in FLAGS if flags.get(k)is False]
 if blocked:return {'status':'BLOCKED','reasons':blocked}
 if not all(flags.get(k)is True for k in FLAGS):return {'status':'UNKNOWN','reasons':['INCOMPLETE_GATE_SNAPSHOT']}
 return {'status':'OBSERVED_GATES_PASS','reasons':[], 'caveat':'actual A account state is not the hypothetical C portfolio; no execution proof'}

def replay(s,bars,variant,protocol,registration_ms,mode='historical',observations=None):
 validate_signal(s);a=bars_index(bars);v=protocol['variants'][variant];g=protocol['geometry']
 r={'id':s['id'],'symbol':s['symbol'],'variant':variant,'signal_ms':s['signal_ms'],'first_received_ms':s['first_received_ms'],
    'study_mode':mode,'actual_fill_verified':False,'admissibility':{'status':'UNKNOWN','reasons':['NOT_EVALUATED']},'true_net_R':None,'funding_R':None,'events':[],'attempts':[]}
 if mode=='forward'and variant not in protocol['forward_variants']:raise ValueError('B is historical only')
 if mode=='forward'and min(s['signal_ms'],s['first_received_ms'])<=registration_ms:r['status']='EXPOSED_NOT_FORWARD';return r
 if not s['ml_passed']:r['status']='EXCLUDED_ML';return r
 if not a:r['status']='DATA_GAP_PRICES';return r
 C=s['reference_price'];plan=C*(1+v['limit_offset']);zone=(plan*.999,plan*1.003);stop_pre=plan*1.056;tp_pre=plan*.979
 start=((s['first_received_ms']+M-1)//M)*M;expiry=s['first_received_ms']+int(v['ttl_hours']*H)
 maxstamp=max(a);entry=None;obs=observations or {}
 for t in range(start,expiry,M):
  if t not in a or t-M not in a:
   r['status']='PENDING_DATA'if t>maxstamp else'DATA_GAP_MINUTE';return r
  prev=a[t-M]['close'];b=a[t]
  if prev<=tp_pre:r.update(status='PRICE_ALREADY_AT_TP1',decision_ms=t);return r
  if prev>=stop_pre:r.update(status='PRICE_ALREADY_AT_STOP',decision_ms=t);return r
  rate=max(b['open'],zone[0]);ev=gate_evidence(obs.get(t),t)
  attempt={'decision_ms':t,'last_closed_ms':t,'last_closed_price':prev,'quote_open_proxy':b['open'],'limit_price':rate,'cancel_ms':t+M,'gate_evidence':ev}
  if rate>zone[1]:attempt['status']='WAIT_ZONE';r['attempts'].append(attempt);continue
  attempt['status']='PRICE_TOUCH_PROXY'if b['high']>=rate else'NO_TOUCH';r['attempts'].append(attempt)
  if b['high']>=rate:
   entry=rate;et=t;r.update(admissibility=ev,entry=entry,entry_ms=t,first_decision_delay_ms=t-s['first_received_ms'],
       pending_fill_TP1_order_ambiguous=b['low']<=tp_pre,zone=list(zone),original_limit=plan);break
 if entry is None:r['status']='NOFILL_EXPIRED';return r
 remaining=1.;hit=0;stop=entry*1.056;gross=0.;mfe=mae=0.;fillbar_tp=False
 def leave(kind,price,frac,t):
  nonlocal remaining,gross
  f=min(remaining,frac);remaining=max(0.,remaining-f);gross+=f*(entry-price)/entry
  r['events'].append({'kind':kind,'price':price,'fraction':f,'time_ms':t})
 for t in range(et,et+int(g['hold_hours']*H)+M,M):
  if t not in a:r['status']='PENDING_DATA'if t>maxstamp else'DATA_GAP_MINUTE';return r
  b=a[t]
  if t>=et+int(g['hold_hours']*H):leave('TIME',b['open'],remaining,t);break
  mfe=max(mfe,(entry-b['low'])/(entry*.056));mae=max(mae,(b['high']-entry)/(entry*.056))
  if b['high']>=stop:leave('SL'if hit==0 else'BE',max(stop,b['open']),remaining,t+M);break
  if t==et:
   fillbar_tp=b['low']<=entry*.979
   continue
  while hit<3 and b['low']<=entry*(1-g['TP_from_fill'][hit]):
   leave('TP'+str(hit+1),entry*(1-g['TP_from_fill'][hit]),g['weights'][hit],t+M);hit+=1
  if remaining<1e-9:break
  if hit:stop=min(stop,entry*g['BE_short_multiplier'])
 if remaining>1e-8:r['status']='DATA_GAP_EXIT';return r
 assert abs(sum(e['fraction']for e in r['events'])-1)<1e-8
 r.update(status='CLOSED_PRICE_MODEL',exit_ms=r['events'][-1]['time_ms'],gross_return=gross,
   price_R={str(bp):(gross-bp/10000)/.056 for bp in protocol['costs_bp']},
   compatibility_R_0581={str(bp):(gross-bp/10000)/.0581 for bp in protocol['costs_bp']},
   MFE_coarse_R=mfe,MAE_coarse_R=mae,fill_minute_TP_banned=fillbar_tp,
   regime=signal_regime(s))
 return r

def regime(current,prior):
 if not positive(current)or not positive(prior):return'UNKNOWN'
 r=100*(current/prior-1)
 return'DOWN'if r<=-3+1e-10 else'UP'if r>=3-1e-10 else'SIDEWAYS'

def signal_regime(s):
 t=s.get('btc_close_known_ms');p=s.get('btc_close_24h_known_ms')
 if not integer(t)or not integer(p)or not 0<=s['signal_ms']-t<M or t-p!=24*H:return 'UNKNOWN'
 return regime(s.get('btc_close_known'),s.get('btc_close_24h_known'))

def summarize(rows):
 out=[]
 for v in sorted({r['variant']for r in rows}):
  rr=[r for r in rows if r['variant']==v];closed=sorted([r for r in rr if r['status']=='CLOSED_PRICE_MODEL'],key=lambda r:(r['exit_ms'],r['id']))
  for bp in ('21','35','50'):
   vals=[r['price_R'][bp]for r in closed];g=sum(x for x in vals if x>0);loss=-sum(x for x in vals if x<0);eq=peak=dd=0.;streak=maxstreak=0
   days=collections.defaultdict(float);coins=collections.defaultdict(float)
   for r,x in zip(closed,vals):
    eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq);streak=streak+1 if x<0 else 0;maxstreak=max(maxstreak,streak)
    days[dt.datetime.fromtimestamp(r['exit_ms']/1000,dt.timezone.utc).date().isoformat()]+=x;coins[r['symbol']]+=x
   out.append({'variant':v,'cost_bp':int(bp),'opportunities':len(rr),'closed_price_model_n':len(closed),'statuses':dict(collections.Counter(r['status']for r in rr)),
    'WR_price_pct':100*sum(x>0 for x in vals)/len(vals)if vals else None,'price_R_per_trade':sum(vals)/len(vals)if vals else None,'sum_price_R':sum(vals)if vals else None,
    'PF_price':g/loss if loss else None,'DD_closed_price_R':dd if vals else None,'max_loss_streak':maxstreak if vals else None,
    'sum_without_best3_days':sum(vals)-sum(sorted(days.values(),reverse=True)[:3])if vals else None,
    'sum_without_best3_coins':sum(vals)-sum(sorted(coins.values(),reverse=True)[:3])if vals else None,
    'actual_verified_fill_n':0,'true_net_R':'НЕ ПРОВЕРЕНО','net_R_per_week':'НЕ ПРОВЕРЕНО','admissible_counterfactual_entry_n':'НЕ ПРОВЕРЕНО'})
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mode',choices=['historical','forward'],required=True);a=ap.parse_args()
 here=Path(__file__).parent;protocol=json.loads((here/'FROZEN_PROTOCOL.json').read_text());registration=json.loads((here/'REGISTRATION.json').read_text());bundle=json.loads(a.input.read_text())
 if a.out.exists():raise ValueError('output exists; refusing overwrite')
 if a.mode=='forward'and not registration.get('model_snapshot_verified'):raise ValueError('forward blocked: pin original top50 model snapshot before new cohort')
 signals=bundle['signals'];ids=[s['id']for s in signals]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate signal id; do not silently deduplicate changed signals')
 if not bundle.get('provenance'):raise ValueError('source provenance missing')
 rows=[]
 for s in signals:
  if a.mode=='forward'and s['model_sha']!=registration['model_sha256']:raise ValueError('model changed; segregate cohort without refit')
  obs={}
  for x in bundle.get('observations',[]):
   if x['signal_id']==s['id']:
    k=(x['variant'],x['decision_ms'])
    if k in obs:raise ValueError('duplicate admission snapshot')
    obs[k]=x
  for v in protocol['forward_variants']if a.mode=='forward'else protocol['variants']:
   vo={t:x for(v0,t),x in obs.items()if v0==v}
   rows.append(replay(s,bundle.get('candles',{}).get(s['symbol'],[]),v,protocol,registration['registration_ms'],a.mode,vo))
 a.out.mkdir(parents=True)
 (a.out/'LEDGER.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(x,allow_nan=False)for x in rows)+'\n').encode(),mtime=0))
 (a.out/'METRICS.json').write_text(json.dumps(summarize(rows),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 (a.out/'CHECKPOINT.json').write_text(json.dumps({'input_sha256':hashfile(a.input),'protocol_sha256':hashfile(here/'FROZEN_PROTOCOL.json'),'registration_sha256':hashfile(here/'REGISTRATION.json'),'rows':len(rows),'mode':a.mode,'actual_collection_started':False,'true_net_verified':False,'source_provenance':'DECLARED_NOT_INDEPENDENTLY_VERIFIED','LIVE_changes':0},indent=2)+'\n')
 print(json.dumps({'rows':len(rows),'out':str(a.out),'warning':'minute price models only; no real execution or true net assertion'}))
if __name__=='__main__':main()
