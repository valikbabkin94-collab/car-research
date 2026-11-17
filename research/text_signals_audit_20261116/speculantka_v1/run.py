"""Full SPECULANTKA archive audit. No account/order/Telegram interfaces."""
import sys,json,gzip,time,datetime as dt,collections,subprocess,hashlib,random,concurrent.futures as cf
from pathlib import Path
import numpy as np
P=Path(__file__).parent;sys.path.insert(0,str(P.parent));sys.path.insert(0,str(P))
import full_run as F
from market import Quotes,Funding,save,sha,M,H,DAY
from spec_engine import simulate
OUT=P/'RESULTS';NAMES=['T1','T2','T3'];SEED=20261117

def gz(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(x,allow_nan=False).encode(),mtime=0))
def load(p):return json.loads(gzip.decompress(p.read_bytes()))if p.suffix=='.gz'else json.loads(p.read_text())

def collect_jobs(quotes,jobs,deadline):
 jobs=sorted(set(jobs));receipts=[]
 def fetch(x):
  sym,period,kind=x
  try:return dict(symbol=sym,period=period,kind=kind,status='OK',receipt=quotes.fetch(sym,period,kind))
  except Exception as e:return dict(symbol=sym,period=period,kind=kind,status='DATA_GAP',error=type(e).__name__+': '+str(e))
 with cf.ThreadPoolExecutor(max_workers=4)as pool:
  for j in range(0,len(jobs),4):
   if time.monotonic()>deadline:break
   receipts+=list(pool.map(fetch,jobs[j:j+4]));save(OUT/'SOURCE_CHECKPOINT.json',dict(total=len(jobs),done=len(receipts),receipts=receipts))
   if j%100==0:print('SOURCES',len(receipts),'/',len(jobs),flush=True)
 save(OUT/'SOURCE_CHECKPOINT.json',dict(total=len(jobs),done=len(receipts),receipts=receipts))
 return receipts

def execute(s,policy,qreader,bybit,fund,asof,control=False,geometry=None):
 start=(s['pub']+M+M-1)//M*M;q=qreader.load(s['symbol']);i=int(np.searchsorted(q[:,0],start))if len(q)else 0;venue='BINANCE_USDT_M_PROXY'
 base=dict(post_key=s['post_key'],channel='SPECULANTKA',symbol=s['symbol'],policy=policy,pub=s['pub'],edited=s['edited'],grid=s.get('grid'),reported=s['reported'],random_control=control,net_R=None)
 if policy=='T1'and s.get('grid_mentioned')and not s.get('grid'):return dict(base,status='UNRESOLVED_GRID_RANGE',venue=venue)
 if i>=len(q)or q[i,0]!=start:q=bybit.get(s['symbol'],max(0,start-24*H),min(asof,start+97*H));venue='BYBIT_PUBLIC_LINEAR';i=int(np.searchsorted(q[:,0],start))if len(q)else 0
 if i>=len(q)or q[i,0]!=start:return dict(base,status='нет данных',detail='NO_ENTRY_CANDLE',venue=venue)
 side=1 if s['side']=='LONG'else -1;p=dict(symbol=s['symbol'],signal_ms=s['pub'],observed_ms=s['pub']+M-1,side=side,entry_type='MARKET',hold_hours=72,stop_fraction=.056)
 if s.get('grid'):p.update(entry_type='LIMIT',limit=sum(s['grid'])/2,ttl_hours=24,fixed_limit_price=True)
 elif policy=='T1'and s.get('explicit_limit'):p.update(entry_type='LIMIT',limit=s['explicit_limit'],ttl_hours=24)
 if policy=='T1':
  if s.get('stop')is not None:p['absolute_stop']=s['stop']
  p['author_events']=s['events']
  if control and geometry and geometry.get('entry'):
   old=geometry['entry'];new=float(q[i,1]);ratio=new/old;p['stop_fraction']=geometry['risk_fraction'];p.pop('absolute_stop',None)
   if 'limit'in p:p['limit']*=ratio
   for e in p['author_events']:
    if e.get('price')is not None:e['price']*=ratio
 if policy=='T2':
  lo=int(np.searchsorted(q[:,0],start-24*H));past=q[lo:i]
  if len(past)!=1440 or np.any(np.diff(past[:,0])!=M):return dict(base,status='нет данных',detail='NO_FULL_24H_PAST',venue=venue)
  stop=float(past[:,2].max()*1.01)if side==-1 else float(past[:,3].min()*.99);p.update(absolute_stop=stop,tp_kind='R',tp_R=[1,2],weights=[.5,.5])
 r=simulate(q,p,asof);r.update(base,venue=venue,entry_policy='GRID_MEAN_LIMIT_PROXY'if s.get('grid')else'EXPLICIT_LIMIT'if p['entry_type']=='LIMIT'else'MARKET_1MIN',unknown_grid_market_substitute=bool(s.get('grid_mentioned')and not s.get('grid')and policy!='T1'))
 if r['status']=='CLOSED':
  cash=fund.cash(s['symbol'],r,q)if venue=='BINANCE_USDT_M_PROXY'else None;r['funding_status']='KNOWN_REAL_CASH'if cash is not None else'ASSUMED_ZERO_UNKNOWN';r['funding_R']=0. if cash is None else cash;r['net_R']=r['price_R']+r['funding_R'];exposure=sum(e['fraction']*max(0,e['time_ms']-r['entry_ms'])/(8*H)for e in r['events']);stress=.0001*exposure/r['risk_denominator']if cash is None else 0.;r.update(funding_stress_R=stress,net_R_funding_adverse=r['net_R']-stress,net_R_funding_favourable=r['net_R']+stress)
 return r

def claim_check(records,signals,actual,quotes):
 smap={s['post_key']:s for s in signals};trades={(r['post_key'],r['policy']):r for r in actual};out=[]
 for r in records:
  if r['label']!='REPORT'and not r['claimed_percentages']and not(r['label']=='UPDATE'and any(e['kind']=='CLOSE_ALL'for e in r['actions'])):continue
  c=dict(post_key=r['post_key'],pub=r['pub'],label=r['label'],report_type=r['report_type'],claimed_percentages=r['claimed_percentages'],edited=r['edited'],linked_signal=r.get('linked_signal'),status='UNLINKED_OR_AGGREGATE',realized_author_R=None)
  if r['report_type']!='RESULT_OR_CLAIM':c['status']='PROMOTIONAL_OR_PROJECTION_NOT_A_TRADE_REPORT';out.append(c);continue
  s=smap.get(r.get('linked_signal'))
  if not s:out.append(c);continue
  m=trades.get((s['post_key'],'T1'));ref='T1'
  if not m or m.get('entry')is None:m=trades.get((s['post_key'],'T3'));ref='T3_MARKET_REFERENCE_NOT_AUTHOR_GRID'
  if not m or m.get('entry')is None:c['status']='нет данных';out.append(c);continue
  q=quotes.load(s['symbol']);a=m['entry_ms'];b=r['pub']//M*M;lo=int(np.searchsorted(q[:,0],a))if len(q)else 0;hi=int(np.searchsorted(q[:,0],b))if len(q)else 0;v=q[lo:hi]
  if b<=a:c['status']='REPORT_BEFORE_MODEL_ENTRY';out.append(c);continue
  if len(v)!=(b-a)//M or not len(v)or v[0,0]!=a or v[-1,0]!=b-M or np.any(np.diff(v[:,0])!=M):c['status']='нет данных';out.append(c);continue
  side=1 if s['side']=='LONG'else -1;entry=m['entry'];fav=100*(float(v[:,2].max())/entry-1)if side==1 else 100*(1-float(v[:,3].min())/entry);adv=100*(1-float(v[:,3].min())/entry)if side==1 else 100*(float(v[:,2].max())/entry-1);close=100*side*(float(v[-1,4])/entry-1);L=s.get('leverage');c.update(status='PRICE_WINDOW_AVAILABLE_NOT_AUTHOR_FILL_PROOF',reference=ref,entry=entry,price_MFE_pct=fav,price_MAE_pct=adv,price_at_report_pct=close,declared_leverage=L,claims=[])
  for pct in r['claimed_percentages']:
   implied=pct/L if L else None;inside=(-adv-1e-9<=implied<=fav+1e-9)if implied is not None else None;c['claims'].append(dict(declared_pct=pct,implied_unlevered_pct_if_ROI=pct/L if L else None,inside_price_envelope_if_declared_leverage=inside,raw_pct_minus_market_close_pct=pct-close,note='Percent basis/partial size/actual average entry unknown;outside envelope is not proof of false report'))
  out.append(c)
 return out

def main():
 OUT.mkdir(exist_ok=True);d=load(P/'CLASSIFICATION_AND_LINKS.json.gz');signals=d['signals'];records=d['records'];asof=(max(max(r['pub'],r.get('edit_time_ms')or 0)for r in records)//M+1)*M;asof=min(asof,int(time.time()*1000)//M*M);F.ASOF=asof;F.OUT=OUT;q=Quotes('work/market');fund=Funding('source','work/funding');bybit=F.PublicBybit();rng=np.random.default_rng(SEED);lo=min(s['pub']for s in signals);hi=max(s['pub']for s in signals)+M;half=(lo+hi)//2;tail=lo+int(.6*(hi-lo));periods=[('H1',lo,half),('H2',half,hi),('LAST40',tail,hi)];controls=[];jobs=[];recmap={r['post_key']:r for r in records}
 for s in signals:
  a,b=(lo,half)if s['pub']<half else(half,tail)if s['pub']<tail else(tail,hi);t=int(rng.integers(a,max(a+1,b)));delta=t-s['pub'];c=dict(s,pub=t,events=[dict(e,effective_ms=e['effective_ms']+delta,pub=e['pub']+delta)for e in s['events']]);controls.append(c)
  report_end=max([s['pub']+97*H]+[recmap[k]['pub']+M for k in s['report_keys']]);jobs+=F.jobs_for(s['symbol'],s['pub']-24*H,min(asof,report_end));jobs+=F.jobs_for(c['symbol'],c['pub']-24*H,min(asof,c['pub']+8*DAY))
 receipts=collect_jobs(q,jobs,time.monotonic()+25*60);save(OUT/'SOURCE_RECEIPTS.json',receipts);bybit.get('BTCUSDT',asof-2*M,asof);cb={s['post_key']:s for s in controls};actual=[];randomrows=[]
 for i,s in enumerate(sorted(signals,key=lambda s:(s['symbol'],s['pub']))):
  for policy in NAMES:
   r=execute(s,policy,q,bybit,fund,asof);actual.append(r);randomrows.append(execute(cb[s['post_key']],policy,q,bybit,fund,asof,True,r))
  if i%25==0:gz(OUT/'ACTUAL_CHECKPOINT.json.gz',actual);gz(OUT/'CONTROL_CHECKPOINT.json.gz',randomrows);print('SIGNALS',i,'/',len(signals),flush=True)
 gz(OUT/'ALL_TRADES.json.gz',actual);gz(OUT/'RANDOM_TIME_TRADES.json.gz',randomrows);save(OUT/'BYBIT_PROBES.json',dict(host_block=bybit.blocked,receipts=bybit.receipts));tables=[];randomidx={(r['post_key'],r['policy']):r for r in randomrows};distrows=[]
 for label,a,b in periods:
  for policy in NAMES:
   rows=[r for r in actual if r['policy']==policy and a<=r['pub']<b];known=[r for r in rows if r.get('net_R')is not None];pairs=[];blocks=collections.defaultdict(float)
   for r in known:
    c=randomidx.get((r['post_key'],policy))
    if c and c.get('net_R')is not None:pairs.append((r,c));blocks[r['pub']//DAY]+=r['net_R']-c['net_R']
   v=np.array(list(blocks.values()));obs=float(v.sum());null=rng.choice([-1,1],size=(4095,len(v)))@v if len(v)else np.array([]);coverage=len(pairs)/len(known)if known else 0;pval=(1+int(np.sum(null>=obs)))/4096 if len(v)and coverage>=.95 else 1.;tables.append(dict(policy=policy,period=label,**F.metrics(rows),control_pairs=len(pairs),control_coverage=coverage,control_p=pval));distrows.append(dict(policy=policy,period=label,deltaR=obs,null_deltaR=null.tolist()))
 for r,qval in zip(tables,F.bh([r['control_p']for r in tables])):r['BH9_q']=qval
 save(OUT/'TABLES.json',tables);save(OUT/'OVERALL.json',[dict(policy=p,**F.metrics([r for r in actual if r['policy']==p]))for p in NAMES]);gz(OUT/'CONTROL_DISTRIBUTIONS.json.gz',distrows);save(OUT/'SPLITS.json',dict(start=lo,end=hi,half=half,tail=tail,asof=asof));save(OUT/'CLAIM_MARKET_CHECK.json',claim_check(records,signals,actual,q));save(OUT/'SIGNALS_WITHOUT_RESULT_REPORT.json',[s for s in signals if not s['reported']]);pf_compare(signals,actual);render(d,actual,tables,asof,bybit.blocked)

def pf_compare(signals,actual):
 pf=load(P/'PF_BASELINES.json.gz');out=[];entry={(r['post_key'],r['policy']):r for r in actual}
 for s in signals:
  if s['side']!='SHORT':continue
  for b in pf:
   if b['symbol']!=s['symbol']or abs(b['signal_ms']-s['pub'])>24*H:continue
   r=entry[(s['post_key'],'T1')];delta=100*(r['entry']/b['entry']-1)if r.get('entry')and b.get('entry')else None;out.append(dict(signal_key=s['post_key'],symbol=s['symbol'],spec_pub=s['pub'],PF_signal_ms=b['signal_ms'],PF_source=b['source'],PF_status=b['status'],spec_T1_status=r['status'],short_entry_delta_pct=delta,interpretation='Higher SHORT entry only;different times and venues,no causal skill/profit proof'))
 save(OUT/'PUMP_FADE_MATCHES.json',out)

def render(d,actual,tables,asof,blocked):
 overall=load(OUT/'OVERALL.json');claims=load(OUT/'CLAIM_MARKET_CHECK.json');manifest=load(P/'INPUT_MANIFEST.json');classcounts=dict(collections.Counter(r['label']for r in d['records']));statuses=dict(collections.Counter(r['status']for r in claims));r1=next(r for r in overall if r['policy']=='T1');coverage=r1['n']/len(d['signals']);conclusion='мало данных для достоверного результата реальной торговли автора';model='в плюсе'if r1['netR']>0 else'в минусе'if r1['netR']<0 else'нулевой';finals=[]
 for s in d['signals']:
  rs=[r for r in d['records']if r.get('linked_signal')==s['post_key']and r['report_type']=='RESULT_OR_CLAIM'and len(r['claimed_percentages'])==1 and any(e['kind']=='CLOSE_ALL'for e in r['actions'])]
  if rs:finals.append(max(rs,key=lambda r:r['pub'])['claimed_percentages'][0])
 save(OUT/'T4_DECLARATIONS.json',dict(final_single_percent_reports=len(finals),claimed_percent_sum_literal=sum(finals),claimed_positive_n=sum(v>0 for v in finals),values=finals,author_returns_verified=False,R=None,equity=None,note='Literal optimistic reference,not additive account ROI or mathematically guaranteed upper bound;leverage/capital/partial basis unknown'))
 lines=['# SPECULANTKA — полный архивный разбор Part1','', 'по реальным ценам канал — '+conclusion+'; условная модель T1 '+model+'.','',f'Архив: {manifest["post_n"]} постов,редактировались {manifest["edited"]};классы {classcounts}. Оригинальные версии текстов неизвестны,изображений нет. Это проверка текущей видимой версии,не доказанный PnLреального счёта.','',f'Нефорвардныхсигналов {len(d["signals"])};T1полностью закрыт/идентифицируем для{r1["n"]}({coverage:.1%}). Явных numericgridranges {sum(bool(s["grid"])for s in d["signals"])};gridбездиапазона не выдуман. 30randomrecordsкаждогокласса сохранены,точностьнезависимо не сертифицирована.','', '|Политика|n|WR%|PF|R|$5/R|DD R|R adverse funding|R favourable funding|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in overall:
  def f(k):v=r.get(k);return 'NA'if v is None else f'{v:.4f}'if isinstance(v,float)else str(v)
  lines.append('|'+r['policy']+'|'+'|'.join(f(k)for k in ['n','WR','PF','netR','USD_at_5R','maxDD_R','netR_adverse','netR_favourable'])+'|')
 lines+=['|T4|NA|NA|NA|NA|NA|NA|NA|NA|','', 'T4—заявления автора,толькооптимистическаясправка. LiteralпроцентыиотдельныефинальныеотчётывT4_DECLARATIONS,неR/доходностьсчёта/строгаяверхняяграница. Не складыватьweekly/monthly/частичныеитогикакнезависимыеденьги.','', '## Половины,последние40%,контроль','|Политика|Период|n|PF|R|BH9q|Контрольcoverage|','|---|---|---:|---:|---:|---:|---:|']
 for r in tables:lines.append('|'+r['policy']+'|'+r['period']+'|'+str(r['n'])+'|'+str(r['PF'])+'|'+str(r['netR'])+'|'+str(r['BH9_q'])+'|'+str(r['control_coverage'])+'|')
 lines+=['', 'Randomtime той же монеты/направления в той же половине/last40. T1managementdelaysиriskwidthсохраненыусловно,неабсолютныепрошлыестопы.4095dayblocksignswaps,BH9;coverage<95%p1. Историческийкорпусужеизвестен,истинногоforwardнет. Last40пересекаетH2.','', '## Сверка всех результатных сообщений','',str(statuses), 'Каждый numericresult/закрытие имеетстрокуCLAIM_MARKET_CHECK,включаяпромо/прогнозы/непривязанные. Длясопоставимыхстрок даныMFE/MAE/ценауотчётаипроцентвнеценовогоenvelope приусловиизаявленногоплеча. Это не доказательствообмана:неизвестныпервоначальныйтекст,среднийвход,размер/доборы,базаROIиactualfills. Безуказанногоплечапроцентнетождествененprice%.','',f'Сигналов без результата в7dlink: {sum(not s["reported"]for s in d["signals"])}. Ониперечисленыотдельно,невыпадаютмолчавшие/убыточные. Общийитогивременныенаблюдениянесколькоразнеприбавляютсякдоходу.','', '## Сравнение с PUMP_FADE','', 'PUMP_FADE_MATCHES:SHORT,coin±24h,отдельноnative5mгодовойисточник иBinance1mRubik. Entrydeltaтолькоеслиобаentryknown;higherSHORTentryещёнеbetterprofitприразныхвременах/venue. СтарыеPF не пересчитывались.','', '## Риск,сетка,ограничения','', 'Numericrange=>midpointfixedlimitTTL24h. Касаниеmidpointнеподтверждаетвсетрaншисетки. Gridбезчисел T1UNRESOLVED_GRID_RANGE;T2/T3market—исследовательскаяподстановка,неавторскийсреднийвход. Доборбезколичества=>UNRESOLVED_DCA,не выдуманновыйaverage. СнятиестопавT1тольковиртуально,исходныйRсохраняется,рискможетпревысить1R. Реальныемаржа/ликвидация/капиталневерифицированы.','', 'T1—causalpolicyсfallbackT3доавторскихкоманд,неидеальнаякопиядискреционнойторговли. Stop/BEupdatesпослепубликации,нетфьючерсныхсообщенийдлявыборамодели.72hисследовательскийгоризонт,болеедлинныеавторскиепозициимогутбытьнедовосстановлены. Fees.055%сторона,slip5bpsmarket,unknownfunding0±.01%/8h,knownrealcashгдеполонархив.','',f'Bybitpublichost:{blocked};sourcecutoff{asof}. Missingpriceнеубыток/неNOFILL. Большинствопостовedited,нетисторическихверсий,chartlevels/mediaнепрочитаны. Поэтому общийреальныйфинансовыйитогканала не подтверждён дажееслиисследовательскаяценоваямодельплюсовая.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','', 'Обработанвесьдоступныйархив,результатыT1/T2/T3икаждыйотчётсохранены. Вышеотдельноусловныеторговыемоделиизаявленияавтора;выводдляреальнойторговли—мало данных. Не объявляемрекламныепроцентыфактическойприбыльюинеобещаемрезультатыдруга. Paper/Live/mainне менялись.','', 'Desktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0']
 (P/'OTCHET_SPECULANTKA_PART1_RU.md').write_text('\n'.join(lines)+'\n');save(P/'CHECKPOINT.json',dict(stage='SPECULANTKA_PART1_COMPLETE_WITH_IDENTIFIABILITY_LIMITS',source=manifest,classes=classcounts,signals=len(d['signals']),T1_identified_fraction=coverage,claim_statuses=statuses,conclusion=conclusion,conditional_T1_model=model,code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),no_live_changes=True))
if __name__=='__main__':main()
