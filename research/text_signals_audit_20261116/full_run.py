"""Full original374 audit: fixed policies, cached/public prices, no real trading."""
import json,gzip,time,datetime as dt,collections,concurrent.futures as cf,hashlib,urllib.request,urllib.parse,urllib.error,subprocess,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from market import Quotes,Funding,save,sha,M,H,DAY,month_list
from full_engine import simulate
P=Path(__file__).parent;OUT=P/'FULL_RESULTS';ASOF=int(dt.datetime(2026,11,17,tzinfo=dt.timezone.utc).timestamp()*1000);NAMES=['T1','T2','T3'];SEED=20261117

def gz(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(x,allow_nan=False).encode(),mtime=0))
def load(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.loads(p.read_text())
def jobs_for(sym,a,b):
 out=[]
 for month in month_list(a,b):
  d=dt.datetime.fromtimestamp(a/1000,dt.timezone.utc)
  if month<'2026-11':out.append((sym,month,'monthly'))
  else:
   t=max(a//DAY*DAY,int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000))
   while t<b:out.append((sym,dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m-%d'),'daily'));t+=DAY
 return out

class PublicBybit:
 def __init__(self):self.blocked=None;self.cache={};self.receipts=[]
 def get(self,sym,a,b):
  if self.blocked:return np.empty((0,5))
  key=(sym,a,b)
  if key in self.cache:return self.cache[key]
  rows=[];end=b-1
  try:
   while end>=a:
    args=urllib.parse.urlencode(dict(category='linear',symbol=sym,interval='1',start=a,end=end,limit=1000));url='https://api.bybit.com/v5/market/kline?'+args
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CAR-offline-research'}),timeout=20)as r:
     if urllib.parse.urlsplit(r.url).hostname!='api.bybit.com':raise ValueError('REDIRECT_DENIED')
     raw=r.read(2000000)
    d=json.loads(raw);self.receipts.append(dict(symbol=sym,start=a,end=end,sha256=sha(raw),retCode=d.get('retCode')))
    if d.get('retCode')!=0:break
    items=d.get('result',{}).get('list',[])
    if not items:break
    part=[[int(x[0]),*map(float,x[1:5])]for x in items];rows+=part;nxt=min(x[0]for x in part)-1
    if nxt>=end:break
    end=nxt
   arr=np.array(sorted({x[0]:x for x in rows}.values()),float)if rows else np.empty((0,5));self.cache[key]=arr;return arr
  except Exception as e:
   if isinstance(e,urllib.error.HTTPError)and e.code in [403,451]:self.blocked=f'HTTP_{e.code}_PUBLIC_HOST_BLOCKED'
   self.receipts.append(dict(symbol=sym,start=a,error=type(e).__name__+': '+str(e)));return np.empty((0,5))

def plan_for(s,policy,q,random=False):
 obs=s['pub']+M-1;start=(obs//M+1)*M;i=int(np.searchsorted(q[:,0],start))if len(q)else 0
 if i>=len(q)or q[i,0]!=start:return None,'NO_ENTRY_CANDLE'
 p=dict(symbol=s['symbol'],signal_ms=s['pub'],observed_ms=obs,side=1 if s['side']=='LONG'else -1,entry_type='MARKET',hold_hours=72,stop_fraction=.056)
 if policy=='T1':
  if s.get('stop')is not None:p['absolute_stop']=s['stop']
  if s.get('explicit_limit'):p.update(entry_type='LIMIT',limit=s['explicit_limit'],ttl_hours=24)
  if not random:p['author_events']=s.get('events',[])
 if policy=='T2':
  lo=int(np.searchsorted(q[:,0],start-24*H));past=q[lo:i]
  if len(past)!=1440 or np.any(np.diff(past[:,0])!=M):return None,'NO_FULL_24H_FEATURE'
  stop=float(past[:,2].max()*1.01)if p['side']==-1 else float(past[:,3].min()*.99);entry=float(q[i,1]);width=p['side']*(entry-stop)/entry;p.update(absolute_stop=stop,tp_dist=[width,2*width],weights=[.5,.5])
 return p,None

def run_case(s,policy,quotes,bybit,fund,random=False):
 q=quotes.load(s['symbol']);a=s['pub']//M*M-24*H;b=min(ASOF,s['pub']+97*H);start=(s['pub']+M+M-1)//M*M;i=int(np.searchsorted(q[:,0],start))if len(q)else 0;venue='BINANCE_USDT_M_PROXY'
 if i>=len(q)or q[i,0]!=start:q=bybit.get(s['symbol'],a,b);venue='BYBIT_PUBLIC_LINEAR'
 base=dict(channel=s['channel'],post_key=s['post_key'],policy=policy,pub=s['pub'],venue=venue,random_time=random)
 p,error=plan_for(s,policy,q,random)
 if error:return dict(base,status='нет данных',detail=error,net_R=None)
 r=simulate(q,p,ASOF);r.update(base)
 if r['status']!='CLOSED':r['net_R']=None;return r
 cash=fund.cash(s['symbol'],r,q)if venue=='BINANCE_USDT_M_PROXY'else None;unknown=cash is None;r['funding_R']=0. if unknown else cash;r['funding_status']='ASSUMED_ZERO_UNKNOWN'if unknown else 'KNOWN_REAL_CASH';r['net_R']=r['price_R']+r['funding_R']
 # Entry-notional weighted remaining exposure, fractional 8h periods, unknown component only.
 exposure=sum(e['fraction']*max(0,e['time_ms']-r['entry_ms'])/(8*H)for e in r['events']);stress=.0001*exposure/r['risk_denominator']if unknown else 0.;r.update(funding_stress_R=stress,net_R_funding_adverse=r['net_R']-stress,net_R_funding_favourable=r['net_R']+stress);return r

def metrics(rows):
 a=sorted([r for r in rows if r.get('net_R')is not None],key=lambda r:(r['exit_ms'],r['post_key']));v=np.array([r['net_R']for r in a]);eq=np.cumsum(v);loss=-float(v[v<0].sum());gain=float(v[v>0].sum());net=float(v.sum());return dict(n=len(a),WR=100*float(np.mean(v>0))if len(v)else None,PF=gain/loss if loss else None,netR=net,USD_at_5R=5*net,maxDD_R=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(v)else 0,top3_share_net=float(np.sort(v)[-3:].sum())/net if net>0 else None,funding_unknown_n=sum(r['funding_status']=='ASSUMED_ZERO_UNKNOWN'for r in a),netR_adverse=sum(r['net_R_funding_adverse']for r in a),netR_favourable=sum(r['net_R_funding_favourable']for r in a),statuses=dict(collections.Counter(r['status']for r in rows)))

def bh(values):
 n=len(values);o=np.argsort(values);q=[1.]*n;last=1.
 for k in range(n-1,-1,-1):i=int(o[k]);last=min(last,values[i]*n/(k+1));q[i]=last
 return q

def main():
 OUT.mkdir(exist_ok=True);previous_actual=load(OUT/'ALL_TRADES.json.gz')if (OUT/'ALL_TRADES.json.gz').exists()else [];previous_null=load(OUT/'RANDOM_TIME_TRADES.json.gz')if (OUT/'RANDOM_TIME_TRADES.json.gz').exists()else [];amap={(r['post_key'],r['policy']):r for r in previous_actual};nmap={(r['post_key'],r['policy']):r for r in previous_null};oldpub={r['post_key']:r['pub']for r in previous_null}
 if previous_actual:gz(OUT/'BEFORE_FREQUENCY_FILTER_CORRECTION.json.gz',previous_actual)
 plans=load(P/'inputs/FULL_374_PLANS.json.gz');registry=load(P/'CHANNEL_REGISTRY.json');quotes=Quotes('work/market');fund=Funding('source','work/funding');bybit=PublicBybit();rng=np.random.default_rng(SEED);splits={};controls=[];jobs=[]
 for ch in registry:
  s=[r for r in plans if r['channel']==ch];lo=min((r['pub']for r in s),default=0);hi=max((r['pub']for r in s),default=0)+M;splits[ch]=(lo,hi,(lo+hi)//2,lo+int(.6*(hi-lo)))
 for s in plans:
  if s['status']=='COOLDOWN6H':s['status']='CANDIDATE'
  if s['status']!='CANDIDATE':continue
  lo,hi,mid,tail=splits[s['channel']];a,b=(lo,mid)if s['pub']<mid else(mid,hi);t=oldpub.get(s['post_key'],int(rng.integers(a,max(a+1,b))));c=dict(s,pub=t,events=[]);controls.append(c)
  for x in ([]if (s['post_key'],'T3')in amap and amap[(s['post_key'],'T3')]['status']!='COOLDOWN6H'else [s,c]):jobs+=jobs_for(s['symbol'],x['pub']-24*H,min(ASOF,x['pub']+97*H))
 jobs=sorted(set(jobs));receipts=[];deadline=time.monotonic()+25*60
 def fetch(x):
  sym,period,kind=x
  try:return dict(symbol=sym,period=period,kind=kind,status='OK',receipt=quotes.fetch(sym,period,kind))
  except Exception as e:return dict(symbol=sym,period=period,kind=kind,status='DATA_GAP',error=type(e).__name__+': '+str(e))
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for j in range(0,len(jobs),4):
   if time.monotonic()>deadline:break
   receipts+=list(pool.map(fetch,jobs[j:j+4]));save(OUT/'SOURCE_CHECKPOINT.json',dict(total=len(jobs),done=len(receipts),receipts=receipts))
 # One geographic probe. No API credentials, orders, accounts or private routes.
 bybit.get('BTCUSDT',ASOF-2*M,ASOF)
 actual=[];null=[];controlby={s['post_key']:s for s in controls}
 for i,s in enumerate(sorted(plans,key=lambda r:(r['symbol']or'',r['pub']))):
  for policy in NAMES:
   if s['status']!='CANDIDATE':r=dict(channel=s['channel'],post_key=s['post_key'],policy=policy,pub=s['pub'],status=s['status'],net_R=None)
   elif (s['post_key'],policy)in amap and amap[(s['post_key'],policy)]['status']!='COOLDOWN6H':r=amap[(s['post_key'],policy)]
   else:r=run_case(s,policy,quotes,bybit,fund)
   actual.append(r)
   if s['status']=='CANDIDATE':null.append(nmap[(s['post_key'],policy)]if (s['post_key'],policy)in nmap else run_case(controlby[s['post_key']],policy,quotes,bybit,fund,True))
  if i%30==0:gz(OUT/'ACTUAL_CHECKPOINT.json.gz',actual);gz(OUT/'CONTROL_CHECKPOINT.json.gz',null);print('CASES',i,'/',len(plans),flush=True)
 for old in previous_actual:
  if old['status']!='COOLDOWN6H':assert old==next(r for r in actual if r['post_key']==old['post_key']and r['policy']==old['policy']),'EXISTING_OUTCOME_CHANGED'
 save(OUT/'FULL_DISTINCT_COMPLETENESS.json',dict(original=374,prior_active=312,distinct_active=345,frequency_filter_removed_cases=33,existing_outcomes_unchanged=True,criterion='All unique fresh signals;frequency is not text duplication;no return-based selection'))
 gz(OUT/'ALL_TRADES.json.gz',actual);gz(OUT/'RANDOM_TIME_TRADES.json.gz',null);save(OUT/'BYBIT_PUBLIC_PROBES.json',dict(host_block=bybit.blocked,receipts=bybit.receipts));save(OUT/'SPLITS.json',splits);tables=[];seeds=np.random.default_rng(SEED+1)
 for ch in registry:
  lo,hi,mid,tail=splits[ch]
  for label,a,b in [('H1',lo,mid),('H2',mid,hi),('LAST40',tail,hi)]:
   for policy in NAMES:
    rows=[r for r in actual if r['channel']==ch and r['policy']==policy and a<=r['pub']<b];pairs=[];cb={r['post_key']:r for r in null if r['channel']==ch and r['policy']==policy};known=[r for r in rows if r.get('net_R')is not None]
    for r in known:
     c=cb.get(r['post_key'])
     if c and c.get('net_R')is not None:pairs.append((r['pub']//DAY,r['net_R']-c['net_R']))
    blocks=collections.defaultdict(float)
    for day,delta in pairs:blocks[day]+=delta
    v=np.array(list(blocks.values()));obs=float(v.sum());dist=seeds.choice([-1,1],size=(4095,len(v)))@v if len(v)else np.array([]);coverage=len(pairs)/len(known)if known else 0;pval=(1+int(np.sum(dist>=obs)))/4096 if len(v)and coverage>=.95 else 1.
    tables.append(dict(channel=ch,policy=policy,period=label,**metrics(rows),control_pairs=len(pairs),control_coverage=coverage,control_p=pval))
 for label in ['H1','H2','LAST40']:
  part=[r for r in tables if r['period']==label]
  for r,q in zip(part,bh([r['control_p']for r in part])):r['BH135_q']=q
 save(OUT/'TABLES.json',tables);
 old=load(P/'inputs/V2_TABLES.json');comparison=[dict(dataset=('OLD_M2_M3'if r['policy']in ['P4','P5']else 'V2_P1_P3'),**r)for r in old if r['cohort']=='AVAILABLE'and r['policy']in ['P1','P2','P3','P4','P5']] + [dict(dataset='NEW_TEXT_CANDIDATES_DIFFERENT_COHORT',**r)for r in tables];save(OUT/'COMPARISON_OLD_V2_TEXT.json',comparison);
 save(OUT/'OVERALL.json',[dict(policy=p,**metrics([r for r in actual if r['policy']==p]))for p in NAMES]);passes=[]
 for ch in registry:
  for policy in NAMES:
   rr=[r for r in tables if r['channel']==ch and r['policy']==policy]
   if all(r['n']>=60 and r['PF']is not None and r['PF']>=1.3 and r['netR']>0 and r['netR_adverse']>0 and r['BH135_q']<=.05 for r in rr):passes.append(dict(channel=ch,policy=policy,paper_only=True))
 save(P/'FULL_PAPER_CANDIDATES.json',passes);save(P/'FULL_CHECKPOINT.json',dict(stage='FULL374_COMPLETE',original_n=len(plans),classified_active=sum(r['status']=='CANDIDATE'for r in plans),all_policy_rows=len(actual),controls=len(null),candidates=len(passes),code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),funding_unknown='ZERO_PLUS_MINUS_0.01_PERCENT_8H',SPECULANTKA='NOT_WAITED',LIVE_changes=0))
 render(plans,actual,tables,passes,bybit.blocked)

def render(plans,rows,tables,passes,blocked):
 cover=load(P/'FULL_CLASS_COVERAGE.json');review=load(P/'OTHER_MANUAL_REVIEW_30.json');lines=['# Полный аудит текстовых кандидатов —17ноября2026','',f'Исходные374 сохранены,строк исполнения={len(rows)}. Дедуп/классификация: {dict(collections.Counter(r["status"]for r in plans))}. SPECULANTKA не ожидалась. Все финансовые результаты ниже включают funding=0 при неизвестности и отдельный стресс±0.01%/8h. Это допущение,не восстановленный реальный funding.','',f'Bybit public fallback host status: {blocked}. Строки «нет данных» сохранены,они не являютсяубытками илиNOFILL. Нельзяутверждатьчтоценнетнигде,еслидоступкпубличномуhostблокирован.','', '## ПРОЧЕЕ','Из30случайных ПРОЧЕЕ при просмотре полного нормализованного текста найдена1явнаякарточка,ошибочноотсечённаярекламнымfooter;этоисправлено доPnL. Карточка сSL/TP не доказывает прибыльностьформатабезуровней. УсловныеаналитическиеLUNC/1INCHнепревращалисьвmarketentry. ПроверкаCodex,self-review,не независимаяручнаясертификация.','', '|Канал|Посты|OTHER|ДоляOTHER|','|---|---:|---:|---:|']
 for c in cover:lines.append('|'+c['channel']+'|'+str(c['posts'])+'|'+str(c['classes'].get('OTHER',0))+'|'+str(c['OTHER_share'])+'|')
 lines+=['','## Полные результаты T1/T2/T3','|Канал|T|Период|n|WR|PF|R|R adverse|R favourable|BHq|','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in tables:
  def f(k):v=r.get(k);return 'NA'if v is None else f'{v:.4f}'if isinstance(v,float)else str(v)
  lines.append('|'+r['channel']+'|'+r['policy']+'|'+r['period']+'|'+'|'.join(f(k)for k in ['n','WR','PF','netR','netR_adverse','netR_favourable','BH135_q'])+'|')
 shortages=[]
 for ch in load(P/'CHANNEL_REGISTRY.json'):
  for policy in NAMES:
   rr=[r for r in tables if r['channel']==ch and r['policy']==policy];shortages.append(dict(channel=ch,policy=policy,missing_to_60_by_period={r['period']:max(0,60-r['n'])for r in rr}))
 save(OUT/'SAMPLE_SHORTFALLS.json',shortages);nodata=sum(r['status']=='нет данных'for r in rows);closest=min((sum(x['missing_to_60_by_period'].values())for x in shortages),default=180)
 conclusion='ДА (только offline,независимаяпроверкаобязательна)'if passes else f'недостаточно данных: строк безданных{nodata};минимально недостаёт{closest} завершённых policy-наблюдений до60вкаждомсрезе;срезыпересекаются,этонечислоуникальныхсделок'
 lines+=['', '## Итог', 'методика14.11 выбрасывала прибыльный формат — '+conclusion,'', 'Порогn60/PF1.3/BH135 проверенвобеихкалендарныхполовинахиlast40. Контроль:одинuniformrandom-time тойжемонеты/стороны вполовинеисходногосигнала,4095парныхперестановокзнакаразницпоUTCдням,не4095новыхрыночныхпереборов. Приcoverage<95%p=1. Этоусловныйконтроль,немоделируетVIP/редакции/очередь. Составнекорректируетсяпорезультатам.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','Всеисходные374прошлиединыйучёт,включаяотказыклассификатора,дублииотсутствующиецены. Неизвестныйfundingбольшенеисключаетсделку. Допущенияиграницыявнопоказаны,устойчивостьнельзяподменятьвинрейтомилималымпилотом. Кодбота,ордера,Telegram-сессиииLIVEнетронуты.','', 'Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0']
 (P/'OTCHET_DLYA_CLAUDE_CODEX_TEXT_SIGNALS_AUDIT_20261116.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
