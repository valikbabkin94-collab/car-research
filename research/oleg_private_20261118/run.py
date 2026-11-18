import os,json,gzip,hashlib,subprocess,collections,datetime as dt,pathlib,copy
from pathlib import Path
import numpy as np
from market import Quotes,Funding,save,sha,month_list,day_list,M,H,DAY
from engine import simulate
from policies import plan,translated_control,entry_start,O,C,ASOF
B=Path('research/oleg_private_20261118');I=B/'inputs'
def load(n):
 p=I/n;return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.load(p.open())
def gz(p,rows):p.write_bytes(gzip.compress(json.dumps(rows,allow_nan=False,separators=(',',':')).encode(),mtime=0))
def random_time(s,st):
 t=s['available_ms'];a=st['source_start'];mid=st['midpoint'];tail=st['last40'];end=min(st['source_end']+M,ASOF);lo,hi=(a,mid)if t<mid else(mid,tail)if t<tail else(tail,end);lo=max(lo,t-7*DAY);hi=min(hi,t+7*DAY);rng=np.random.default_rng(20261118+int(s['post_key'][:12],16))
 if hi-lo<2*M:return None
 return int(rng.integers((lo+M-1)//M,max((lo+M-1)//M+1,(hi-M)//M)))*M+t%M

def main():
 group=os.environ['GROUP'];shard=int(os.environ['SHARD']);out=B/f'{group}_shard{shard}';out.mkdir(parents=True,exist_ok=True);ss=[s for s in load('PLANS.json.gz')if(s['channel']=='OLEG')==(group=='oleg')];stats={s['channel']:s for s in load('DATA_INVENTORY.json')};symbols=sorted(set(s['symbol']for s in ss));owned=[s for i,s in enumerate(symbols)if i%4==shard];ss=[s for s in ss if s['symbol']in owned];quotes=Quotes('work/market');fund=Funding('source','work/funding');actual=[];controls=[];claims=[];sources=[];errors=[];claimby=collections.defaultdict(list)
 for c in load('CLAIMS.json.gz'):
  if c['signal_key']:claimby[c['signal_key']].append(c)
 for sn,sy in enumerate(owned):
  sigs=[s for s in ss if s['symbol']==sy];times={s['post_key']:random_time(s,stats[s['channel']])for s in sigs};windows=[]
  for s in sigs:
   for t in[s['available_ms'],times[s['post_key']]]:
    if t is None or t>=ASOF:continue
    end=ASOF if group!='oleg'and s['kind']=='STRUCTURED'else min(ASOF,t+98*H)
    windows.append((t-25*H,end))
  periods=set();fmonths=set()
  for a,b in windows:
   for mo in month_list(a,b):
    fmonths.add(mo)
    if mo<'2026-11':periods.add((mo,'monthly'))
    else:
     for d in day_list(max(a,1793491200000),b):periods.add((d,'daily'))
  for period,kind in sorted(periods):
   try:sources.append(dict(symbol=sy,**quotes.fetch(sy,period,kind)))
   except Exception as e:errors.append(dict(symbol=sy,period=period,error=type(e).__name__+':'+str(e)[:140]))
  for mo in sorted(fmonths):
   t=int(dt.datetime.fromisoformat(mo+'-01').replace(tzinfo=dt.timezone.utc).timestamp()*1000);nxt=int((dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).replace(day=28)+dt.timedelta(days=4)).replace(day=1).timestamp()*1000)
   if fund.known(sy,t,min(nxt,ASOF)):continue
   try:fund.extend_month(sy,mo,complete_month=mo<'2026-11')
   except Exception as e:errors.append(dict(symbol=sy,kind='FUNDING',period=mo,error=type(e).__name__+':'+str(e)[:100]))
  q=quotes.load(sy);fd=fund.get(sy);ff=sorted(fd.get('rows',[]),key=lambda x:x['ts']);ft=np.array([x['ts']for x in ff],float)
  def money(r):
   if r.get('status')=='NOFILL':r.update(net_R=0.,funding_R=0.,funding_known=True);return r
   if r.get('status')!='CLOSED':r['net_R']=None;return r
   cash=0.;known=fund.known(sy,r['entry_ms'],r['exit_ms']);a=np.searchsorted(ft,r['entry_ms'],side='left');b=np.searchsorted(ft,r['exit_ms'],side='right')
   for x in ff[a:b]:
    t=x['ts'];rate=x['rate'];payer=r['side']*rate>0
    if t==r['entry_ms']and not payer:continue
    k=np.searchsorted(q[:,0],t,side='left')-1
    if k<0 or t-q[k,0]>M:known=False;continue
    left=1-sum(e['fraction']for e in r['events']if e['time_ms']<t or(e['time_ms']==t and not payer));cash-=r['side']*max(0,left)*rate*q[k,4]/r['entry']/r['risk_denominator']
   r['funding_R']=float(cash);r['funding_known']=bool(known);r['net_R']=r['price_R']+float(cash);r['funding_stress_R']=0. if known else(r['exit_ms']-r['entry_ms'])/(8*H)*.0001/r['risk_denominator'];turn=1+sum(e['fraction']*e['price']/r['entry']for e in r['events']);r['fee_R']=.00055*turn/r['risk_denominator'];r['slip_R']=max(0,r['execution_cost_R']-r['fee_R']);r['net_R_adverse']=r['net_R']-r['funding_stress_R']-r['fee_R']-r['slip_R'];return r
  for s in sigs:
   ct=times[s['post_key']];cs,ce=translated_control(s,ct,q,q)if ct is not None else(None,'NO_CONTROL_STRATUM');codes=O if group=='oleg'else C
   for code in codes:
    common=dict(channel=s['channel'],post_key=s['post_key'],policy=code,pub=s['pub'],available_ms=s['available_ms'],kind=s['kind'],symbol=sy,side=1 if s['side']=='LONG'else-1,risk_signature_pct=s['risk_signature_pct'],edit_delay_ms=s['edited_delay_ms'])
    p,err=plan(s,code,q);expiry=(p['observed_ms']+p.get('ttl_hours',8)*H)if p and p.get('entry_type')=='LIMIT'else s['available_ms'];r=dict(status=err,net_R=None,events=[])if err else money(simulate(q,p,ASOF));actual.append(dict(common,intent_expiry_ms=expiry,**r))
    p,err=plan(cs,code,q,True)if cs is not None and ce is None else(None,ce)
    rr=dict(status=err,net_R=None,events=[])if err else money(simulate(q,p,ASOF));controls.append(dict(common,control_available_ms=ct,intent_expiry_ms=(p['observed_ms']+p.get('ttl_hours',8)*H)if p and p.get('entry_type')=='LIMIT'else ct,**rr))
   for cl in claimby[s['post_key']]:
    start=entry_start(s);end=cl['claim_ms'];i=np.searchsorted(q[:,0],start);j=np.searchsorted(q[:,0],end-M,side='right');b=q[i:j];d=dict(cl,symbol=sy,status='NO_MARKET_OR_ENTRY_DATA')
    if len(b)and b[0,0]==start and len(b)==(int(b[-1,0])-start)//M+1:
     e=float(b[0,1]);side=1 if s['side']=='LONG'else-1;mfe=100*((b[:,2].max()/e-1)if side==1 else(1-b[:,3].min()/e));mae=100*((1-b[:,3].min()/e)if side==1 else(b[:,2].max()/e-1));v=cl['claimed_pct'];lev=cl.get('reported_leverage');ok=(-mae<=v<=mfe);d.update(status='WITHIN_UNDERLYING_ENVELOPE'if ok else'EXCEEDS_UNLEVERED_ENVELOPE_ROI_BASIS_UNKNOWN',mfe_pct=float(mfe),mae_pct=float(mae),reported_leverage=lev,leverage_adjusted_compatible=bool(-mae*lev<=v<=mfe*lev)if lev else None,entry_proxy=e,not_realized_author_profit=True)
    claims.append(d)
  quotes.cache={};gz(out/'ACTUAL.json.gz',actual);gz(out/'CONTROL.json.gz',controls);gz(out/'CLAIMS.json.gz',claims);save(out/'SOURCES.json',sources);save(out/'ERRORS.json',errors);save(out/'CHECKPOINT.json',dict(status='RUNNING',group=group,shard=shard,completed_symbols=sn+1,total_symbols=len(owned),actual_rows=len(actual),code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),live_changes=0));print('DONE_SYMBOL',group,shard,sn+1,'/',len(owned),flush=True)
 save(out/'CHECKPOINT.json',dict(status='COMPLETE',group=group,shard=shard,symbols=len(owned),signals=len(ss),actual_rows=len(actual),controls=len(controls),claims=len(claims),code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),live_changes=0));save(out/'INPUT_SHA256.json',{p.name:sha(p.read_bytes())for p in I.glob('*')if p.is_file()})
if __name__=='__main__':main()
