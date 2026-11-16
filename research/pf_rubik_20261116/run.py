"""Frozen 20-variant research on cached market data. No trading interfaces."""
import sys,argparse,json,gzip,collections,math,datetime as dt,hashlib,concurrent.futures as cf,time,subprocess
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pf_execution_common_20261116'))
from market import Quotes,Funding,save,sha,gzread,month_list,M,H
from engine import simulate
LAB=Path(__file__).parent;CFG=json.loads((LAB/'CONFIG_FROZEN.json').read_text());START=CFG['window_start_ms'];END=CFG['window_end_ms'];HALF=CFG['half_ms'];TAIL=CFG['tail_ms'];PURGE=CFG['purge_hours']*H

def gzsave(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(d,allow_nan=False).encode(),mtime=0))
def indicators(q):
 n=len(q);rsi=np.full(n,np.nan);atr=np.full(n,np.nan);gains=[];losses=[];trs=[];ag=al=av=None
 for i in range(1,n):
  if q[i,0]-q[i-1,0]!=H:gains=[];losses=[];trs=[];ag=al=av=None;continue
  d=q[i,4]-q[i-1,4];gains.append(max(d,0));losses.append(max(-d,0));trs.append(max(q[i,2]-q[i,3],abs(q[i,2]-q[i-1,4]),abs(q[i,3]-q[i-1,4])))
  if len(gains)<14:continue
  if ag is None:ag=np.mean(gains[-14:]);al=np.mean(losses[-14:]);av=np.mean(trs[-14:])
  else:ag=(13*ag+gains[-1])/14;al=(13*al+losses[-1])/14;av=(13*av+trs[-1])/14
  rsi[i]=100-100/(1+ag/al) if al>0 else 100 if ag>0 else 50;atr[i]=av
 return rsi,atr

def prepare(source,work):
 work=Path(work);dest=work/'PACKETS.json.gz'
 if dest.exists():
  d=gzread(dest)
  if d['config_sha256']!=sha((LAB/'CONFIG_FROZEN.json').read_bytes()):raise ValueError('PACKET_CONFIG_SHA_MISMATCH')
  return d
 ranks=np.load(Path(source)/'PIT_RANKS.npz',allow_pickle=False);idx={s:i for i,s in enumerate(ranks['symbols'])};ts=ranks['times'];rank=ranks['rank'];fund=Funding(source,work);frames={}
 manifest=json.loads((Path(source)/'H1_MANIFEST.json').read_text())
 for p in (Path(source)/'h1').glob('*.json.gz'):
  r=gzread(p)
  expected=manifest['files'].get(str(p.relative_to(Path(source))))
  if expected!=sha(p.read_bytes()):raise ValueError('H1_SOURCE_SHA_MISMATCH')
  if r['bars']:frames[r['symbol']]=np.asarray(r['bars'],dtype=float)
 btc={int(x[0]):x[4] for x in frames.get('BTCUSDT',[])};packets=[];counts=collections.Counter()
 for sym,q in sorted(frames.items()):
  if sym not in idx:continue
  rsi,atr=indicators(q);cool={};base_next=0
  for j in range(25,len(q)):
   signal=int(q[j,0]+H)
   if not START<=signal<END:continue
   pos=int(np.searchsorted(ts,q[j,0]));rk=int(rank[idx[sym],pos]) if pos<len(ts) and ts[pos]==q[j,0] else 0
   if not 0<rk<=50:continue
   if any(np.diff(q[j-24:j+1,0])!=H):continue
   r24=q[j,4]/q[j-24,4]-1;obs=signal+CFG['observation_delay_ms'];f=fund.latest(sym,obs);base=j>=169 and np.all(np.diff(q[j-169:j+1,0])==H) and r24>=.15 and q[j,4]/np.max(q[j-167:j+1,2])-1<=-.03 and rsi[j]<=65
   base_setup=base and signal>=base_next
   if base_setup:base_next=signal+24*H
   for v in CFG['variants']:
    name=v['name']
    if signal<cool.get(name,0):continue
    e1=v.get('setup')=='DUMP_RECLAIM';e2=v.get('setup')=='PUMP_CONTINUATION'
    if e1:trigger=r24<=-.15
    elif e2:trigger=j>=169 and np.all(np.diff(q[j-169:j+1,0])==H) and r24>=.15 and q[j,4]>np.max(q[j-168:j,2]) and q[j,5]>=3*np.median(q[j-168:j,5])
    else:trigger=base_setup
    if not trigger:continue
    counts[name+':RAW_SETUP']+=1
    filt=v.get('filter');reason=None
    if filt in ['FUND_POS_8H_0003','FUND_NEGATIVE']:
     if f is None:reason='FEATURE_DATA_GAP_FUNDING'
     elif not(f>=.0003 if filt=='FUND_POS_8H_0003' else f<0):continue
    elif filt=='VOL24_3X_PRIOR7D_MEDIAN':
     if j<191 or np.any(np.diff(q[j-191:j+1,0])!=H):reason='FEATURE_DATA_GAP_192H'
     elif sum(q[j-23:j+1,5])<3*np.median([sum(q[j-47-24*k:j-23-24*k,5]) for k in range(7)]):continue
    elif filt=='RSI_PEAK6H_GE70':
     peak=j-5+int(np.argmax(q[j-5:j+1,2]))
     if not np.isfinite(rsi[peak]):reason='FEATURE_DATA_GAP_RSI'
     elif rsi[peak]<70:continue
    elif filt=='BTC_R24_LE0':
     if int(q[j,0]) not in btc or int(q[j,0]-24*H) not in btc:reason='FEATURE_DATA_GAP_BTC'
     elif btc[int(q[j,0])]/btc[int(q[j,0]-24*H)]-1>0:continue
    p={**v,'symbol':sym,'signal_ms':signal,'observed_ms':obs,'side':v.get('side',-1),'atr':float(atr[j]),'limit':float(q[j,4]*(1+v.get('entry_offset',.013))),'rank':rk,'r24':float(r24),'funding_8h_known':f}
    if reason:p['pre_status']=reason
    if v.get('limit_kind')=='HIGH7':p['limit']=float(np.max(q[j-167:j+1,2]))
    if v.get('stop_kind')=='PUMP_HIGH_005':p['absolute_stop']=float(np.max(q[j-23:j+1,2])*1.005)
    if v.get('stop_kind')=='ATR15':p['stop_atr_distance']=float(1.5*atr[j])
    if e1 or v.get('confirm_kind'):
     if e1:
      anchor=j-3+int(np.argmin(q[j-3:j+1,3]));level=float(np.max(q[max(0,anchor-3):anchor+1,2]));p['absolute_stop']=float(q[anchor,3]*(1-1e-8));p['move_be']=False
     confirm=None;missing=False
     for k in range(j+1,min(j+9,len(q))):
      if q[k,0]-q[k-1,0]!=H:missing=True;break
      if (q[k,4]>level if e1 else q[k,4]<q[k-1,1]):confirm=k;break
     if confirm is None:p['pre_status']='DATA_GAP_CONFIRMATION' if missing else 'NO_CONFIRMATION_8H'
     else:p['observed_ms']=int(q[confirm,0]+H+CFG['observation_delay_ms'])
    packets.append(p);cool[name]=signal+24*H;counts[name+':PACKET']+=1
 data=dict(packets=packets,counts=dict(counts),source='CACHED_H1_PIT_AND_SETTLED_FUNDING',config_sha256=sha((LAB/'CONFIG_FROZEN.json').read_bytes()));gzsave(dest,data);return data

def collect(source,work):
 data=prepare(source,work);quote=Quotes(work);needed=set()
 for p in data['packets']:
  if p.get('pre_status'):continue
  if p['signal_ms']>=END-PURGE:continue
  for month in month_list(p['observed_ms']-M,min(END,p['observed_ms']+81*H)):needed.add((p['symbol'],month))
 started=time.monotonic();done=[]
 def one(x):
  sym,month=x
  try:return dict(symbol=sym,month=month,status='OK',receipt=quote.fetch(sym,month))
  except Exception as e:return dict(symbol=sym,month=month,status='DATA_GAP_M1_SOURCE',error=type(e).__name__+': '+str(e))
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  for offset in range(0,len(needed),4):
   if time.monotonic()-started>2400:save(Path(work)/'SOURCE_CHECKPOINT.json',dict(stage='PAUSED_RESOURCE_RESUME_MISSING_ONLY',done=done,total=len(needed)));return False
   for x in pool.map(one,sorted(needed)[offset:offset+4]):done.append(x)
   save(Path(work)/'SOURCE_CHECKPOINT.json',dict(stage='COLLECTING_ADDRESSED_M1_ONLY',done=done,total=len(needed)))
   if len(done)%40==0:print('M1 archives',len(done),'/',len(needed),flush=True)
 save(Path(work)/'SOURCE_CHECKPOINT.json',dict(stage='COMPLETE_WITH_EXPLICIT_SOURCE_GAPS' if any(x['status']!='OK' for x in done) else 'COMPLETE',done=done,total=len(needed)));return True

def execute(p,q,fund,end,forced=None,width=None):
 pp=dict(p)
 if pp.get('stop_atr_distance') and forced is None:
  # Entry-anchored ATR stop; width calculated after actual causal fill.
  pp['stop_distance_abs']=pp.pop('stop_atr_distance')
 r=simulate(q,pp,end,forced,width);r['net_R']=None;r['name']=p['name'];r['family']=p['family'];r['legs_n']=1 if r.get('entry_ms') is not None else 0
 if r['status']!='CLOSED':return r
 r['funding_R']=fund.cash(p['symbol'],r,q);r['net_R']=r['price_R']+r['funding_R'] if r['funding_R'] is not None else None
 if not p.get('compound_flip') or r['events'][-1]['kind']!='SL':return r
 parent=dict(r);t=r['exit_ms'];deadline=r['entry_ms']+72*H
 if t>=deadline:r['flip_status']='NO_TIME_FOR_FLIP';return r
 fp=dict(p,observed_ms=t-1,side=-r['side'],entry_type='MARKET',absolute_stop=r['entry'],tp_dist=[.04],weights=[1.],move_be=False,compound_flip=False,absolute_deadline=deadline)
 # Fixed parent entry is the stop for the opposite position, not a new fitted width.
 flip=simulate(q,fp,end);r['flip']=flip;r['parent']=parent;r['flip_status']=flip['status'];r['legs_n']+=int(flip.get('entry_ms') is not None)
 if flip['status'].startswith('REJECTED'):return r
 if flip['status']!='CLOSED':r['status']='DATA_GAP_OR_CENSORED_FLIP';r['net_R']=None;return r
 fc=fund.cash(p['symbol'],flip,q);scale=flip['entry']/parent['entry']*flip['risk_denominator']/parent['risk_denominator'];r.update(exit_ms=flip['exit_ms'],price_R=parent['price_R']+scale*flip['price_R'],funding_R=parent['funding_R']+scale*fc if fc is not None and parent['funding_R'] is not None else None)
 r['gross_R']=parent['gross_R']+scale*flip['gross_R'];r['execution_cost_R']=parent['execution_cost_R']+scale*flip['execution_cost_R'];r['hold_hours']=(r['exit_ms']-r['entry_ms'])/H
 r['net_R']=r['price_R']+r['funding_R'] if r['funding_R'] is not None else None;return r

def metrics(rows):
 closed=[r for r in rows if r['status']=='CLOSED'];known=sorted([r for r in closed if r.get('net_R') is not None],key=lambda r:(r['exit_ms'],r['symbol']));v=np.array([r['net_R'] for r in known]);net=float(v.sum());gain=float(v[v>0].sum());loss=float(-v[v<0].sum());eq=np.cumsum(v);dd=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq)) if len(v) else 0
 return dict(data_gap_n=sum('DATA_GAP' in r['status'] for r in rows),mean_hold_hours=float(np.mean([r.get('hold_hours',0) for r in known])) if known else None,opportunities=len(rows),n=len(v),closed_n=len(closed),unknown_funding_n=len(closed)-len(known),WR=100*float(np.mean(v>0)) if len(v) else None,PF=gain/loss if loss else None,netR=net,USD_at_5R=5*net,maxDD_R=dd,mean_R=net/len(v) if len(v) else None,best3_share_net=float(np.sort(v)[-3:].sum())/net if net>0 else None,episode_n=len(known),executed_legs_n=sum(r.get('legs_n',0) for r in known),statuses=dict(collections.Counter(r['status'] for r in rows)))

def calc(source,work,mode):
 quote=Quotes(work);fund=Funding(source,work);data=prepare(source,work)
 if mode=='validation':
  locked=json.loads((LAB/'TRAIN_SELECTION_FROZEN.json').read_text())
  if locked['config_sha256']!=sha((LAB/'CONFIG_FROZEN.json').read_bytes()) or locked['train_tables_sha256']!=sha((LAB/'RESULTS/train/TABLES.json').read_bytes()):raise ValueError('TRAIN_SELECTION_SHA_MISMATCH')
 results=LAB/'RESULTS'/mode;results.mkdir(parents=True,exist_ok=True);allrows=[];tables=[];control=[]
 periods=[('TRAIN',START,HALF-PURGE)] if mode=='train' else [('H2',HALF,END-PURGE),('TAIL40',TAIL,END-PURGE)]
 for label,lo,hi in periods:
  for v in CFG['variants']:
   name=v['name'];chunk=results/'chunks'/(label+'_'+name+'.json.gz');fingerprint=dict(config=sha((LAB/'CONFIG_FROZEN.json').read_bytes()),driver=sha(Path(__file__).read_bytes()),engine=sha((LAB.parents[0]/'pf_execution_common_20261116/engine.py').read_bytes()),sources=sha((Path(work)/'SOURCE_CHECKPOINT.json').read_bytes()) if (Path(work)/'SOURCE_CHECKPOINT.json').exists() else None)
   if chunk.exists():
    cached=gzread(chunk)
    if cached['fingerprint']==fingerprint:tables.append(cached['stat']);control.append(cached['control']);allrows.extend(cached['rows']);print('REUSED_COMPLETE_PROFILE',label,name,flush=True);continue
   rows=[];pairs=[];active={};packets=sorted([p for p in data['packets'] if p['name']==name and lo<=p['signal_ms']<hi],key=lambda p:(p['symbol'],p['observed_ms']))
   for p in packets:
    if p.get('pre_status'):rows.append(dict(symbol=p['symbol'],signal_ms=p['signal_ms'],status=p['pre_status'],name=name));continue
    if active.get(p['symbol'],0)>p['observed_ms']:rows.append(dict(symbol=p['symbol'],signal_ms=p['signal_ms'],status='REJECTED_ALREADY_OPEN',name=name));continue
    q=quote.load(p['symbol']);r=execute(p,q,fund,HALF if mode=='train' else END);r.update(period=label,packet=p);rows.append(r)
    if r.get('entry_ms') is not None:active[p['symbol']]=r.get('exit_ms',END)
    if r['status']=='CLOSED' and r.get('net_R') is not None:
     mirror={**p,'side':-p['side']};mirror.pop('absolute_stop',None);mirror.pop('stop_atr_distance',None)
     z=execute(mirror,q,fund,HALF if mode=='train' else END,(r['entry_ms'],r['entry']),r['risk_fraction'])
     if z['status']=='CLOSED' and z.get('net_R') is not None:pairs.append(dict(day=p['signal_ms']//(24*H),actual_R=r['net_R'],mirror_R=z['net_R']))
   stat=metrics(rows);stat.update(name=name,family=v['family'],period=label,paired_control_n=len(pairs),control_coverage=len(pairs)/stat['n'] if stat['n'] else 0)
   blocks=collections.defaultdict(float)
   for z in pairs:blocks[z['day']]+=z['actual_R']-z['mirror_R']
   delta=np.array(list(blocks.values()));observed=float(delta.sum());rng=np.random.default_rng(CFG['control_seed']+sum(map(ord,name+label)));null=(rng.choice([-1,1],size=(CFG['controls'],len(delta)))@delta) if len(delta) else np.array([]);pval=(1+int(np.sum(null>=observed)))/(len(null)+1) if len(null) and stat['n']>=5 else 1.
   stat.update(control_p=pval,control_day_blocks=len(delta));tables.append(stat);ctrl=dict(name=name,period=label,observed_delta_R=observed,p=pval,draws=len(null),null_delta_R=null.tolist(),pair_n=len(pairs));control.append(ctrl);allrows.extend(rows);gzsave(chunk,dict(fingerprint=fingerprint,stat=stat,control=ctrl,rows=rows));print(mode,label,name,'n',stat['n'],'netR',round(stat['netR'],3),flush=True)
 gzsave(results/'ALL_TRADES.json.gz',allrows);save(results/'TABLES.json',tables);save(results/'CONTROLS.json',control);save(results/'CODE_AND_CONFIG.json',dict(config_sha256=sha((LAB/'CONFIG_FROZEN.json').read_bytes()),code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),mode=mode,source_checkpoint_sha=sha((Path(work)/'SOURCE_CHECKPOINT.json').read_bytes()) if (Path(work)/'SOURCE_CHECKPOINT.json').exists() else None))
 if mode=='train':
  winners={}
  for fam in 'ABCDE':
   eligible=[t for t in tables if t['family']==fam and t['n']>=30 and t['unknown_funding_n']==0 and t['data_gap_n']==0];winners[fam]=max(eligible,key=lambda t:(t['netR'],t['name']))['name'] if eligible else None
  save(LAB/'TRAIN_SELECTION_FROZEN.json',dict(winners=winners,criterion=CFG['selection'],validation_opened=False,config_sha256=sha((LAB/'CONFIG_FROZEN.json').read_bytes()),train_tables_sha256=sha((results/'TABLES.json').read_bytes())))
 else:finalize()

def bh(values):
 vals=np.array(values);order=np.argsort(vals);out=np.ones(len(vals));last=1.
 for rank in range(len(vals)-1,-1,-1):i=order[rank];last=min(last,float(vals[i])*len(vals)/(rank+1));out[i]=last
 return out.tolist()
def finalize():
 train=json.loads((LAB/'RESULTS/train/TABLES.json').read_text());valid=json.loads((LAB/'RESULTS/validation/TABLES.json').read_text());rows=train+valid;qs=bh([r['control_p'] for r in rows])
 for r,q in zip(rows,qs):r['BH_global63_q']=q
 for period in ['TRAIN','H2','TAIL40']:
  subset=[r for r in rows if r['period']==period]
  for r,q in zip(subset,bh([r['control_p'] for r in subset])):r['BH_period21_q']=q
 selection=json.loads((LAB/'TRAIN_SELECTION_FROZEN.json').read_text());candidates=[];leader=[]
 for v in CFG['variants']:
  rr=[r for r in rows if r['name']==v['name']];gates={x['period']:x['n']>=30 and x['unknown_funding_n']==0 and x['data_gap_n']==0 and x['PF'] is not None and x['PF']>=1.3 and x['netR']>0 and x['BH_global63_q']<=.05 and x['best3_share_net'] is not None and x['best3_share_net']<=.5 and x['control_coverage']>=.95 for x in rr};selected=selection['winners'].get(v['family'])==v['name'];passed=selected and len(gates)==3 and all(gates.values());status='PROMISING_PROXY_REQUIRES_INDEPENDENT_FUTURE_CHECK' if passed else 'INCONCLUSIVE' if any(x['n']<30 or x['unknown_funding_n'] or x['data_gap_n'] for x in rr) else 'REJECTED'
  leader.append(dict(name=v['name'],family=v['family'],TRAIN_winner=selected,status=status,selection_reason='FROZEN_TRAIN_WINNER' if selected else 'NOT_FROZEN_TRAIN_WINNER_DESCRIPTIVE_ONLY',periods=rr,gates=gates))
  if passed:candidates.append(dict(**v,paper_only=True,requires_execution_engine_support=True,not_live_ready=True,risk_USD=5,protocol='PF_RUBIK_20261116'))
 save(LAB/'STRATEGY_LEADERBOARD.json',leader);save(LAB/'PAPER_CANDIDATE_VARIANTS.json',candidates)
 lines=['# PF Rubik — все20вариантов и контроль','', 'Binance proxy; baseline literal top50PIT изТЗ,не factorytop200+ML. Все параметры заморожены до PnL. TRAIN выбор опубликован отдельным коммитом до H2. Полный рейтинг: STRATEGY_LEADERBOARD.json.','', '|Вариант|Период|n|WR%|PF|netR|$5/R|DD R|BH global q|Top3/net|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  def fmt(k):return 'NA' if r.get(k) is None else f'{r[k]:.4f}' if isinstance(r[k],float) else str(r[k])
  lines.append('|'+r['name']+'|'+r['period']+'|'+'|'.join(fmt(k) for k in ['n','WR','PF','netR','USD_at_5R','maxDD_R','BH_global63_q','best3_share_net'])+'|')
 lines+=['','## Победители TRAIN и судьба проверки',json.dumps(selection['winners'],ensure_ascii=False),'']
 for x in leader:
  if x['TRAIN_winner']:lines.append(x['name']+': '+x['status']+'; '+json.dumps(x['gates']))
 longs=[x for x in leader if x['name'] in ['E1','E2','E3']];lines+=['','## Лонг-зеркало','Пройденные long/flip кандидаты: '+', '.join(x['name'] for x in longs if x['status'].startswith('PROMISING')) if any(x['status'].startswith('PROMISING') for x in longs) else 'Устойчивое преимущество LONG/flip не подтверждено заданными проверками.','', '## Ограничения','Maker touch — предположение об очереди. Funding/1m gaps и все отказы сохранены. E3метрики по полному parent+flip эпизоду,legs_nотдельно; нельзя выбросить lossродителя. Общийpurge81hпередграницамификсировандоPnL. TAIL40пересекаетсясH2,этоне2независимыхтеста;периодужевиделидругиеисследования. Controls проверяют направление условно на фактических исполненных входах,не полноту LIVEuniverse/очередь/всюalpha. Кандидаты не установлены,совместимость фабрики отдельно.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА','Все20идейпоказаны,провалынескрыты. Положительныевариантытребуютотдельнойбудущейпроверки;прибыльнеобещается.','', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
 (LAB/'OTCHET_DLYA_CLAUDE_CODEX_PF_RUBIK_20261116.md').write_text('\n'.join(lines)+'\n');save(LAB/'CHECKPOINT.json',dict(stage='MATRIX_COMPLETE',variant_count=21,parameter_optimization=False,TRAIN_frozen=True,candidates=len(candidates),next='Independent Claude audit; do not tune on viewedH2/TAIL',LIVE_changes=0))
def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','collect','train','validation']);p.add_argument('--source',default='source');p.add_argument('--work',default='work/rubik');a=p.parse_args();Path(a.work).mkdir(parents=True,exist_ok=True)
 if a.stage=='prepare':prepare(a.source,a.work)
 elif a.stage=='collect':
  if not collect(a.source,a.work):raise SystemExit('PAUSED_WITH_CHECKPOINT')
 else:calc(a.source,a.work,a.stage)
if __name__=='__main__':main()
