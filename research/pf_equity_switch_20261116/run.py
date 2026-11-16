"""Offline weights on saved outcomes only; no exchange, price feed or order code."""
import json,gzip,csv,hashlib,subprocess,math
from pathlib import Path
import numpy as np
LAB=Path(__file__).parent
NAMES=['SW10','SW20','SW20_PF','SW_HALF'];H=3600000
BOUNDS={'YEAR_5M':(1762930800000,1794466800000,1778698800000,1781852400000),'RECENT_1M':(1785542400000,1793491200000,1789516800000,1790311680000)}
def clean(v):
 if isinstance(v,dict):return {k:clean(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x)for x in v]
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,np.generic):return clean(v.item())
 if isinstance(v,float) and not math.isfinite(v):return None
 return v

def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(clean(v),ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
 if p.suffix=='.gz':p.write_bytes(gzip.compress(b,mtime=0))
 else:p.write_bytes(b)

def load():
 manifest=json.loads((LAB/'INPUT_MANIFEST.json').read_text())
 for x in manifest:assert hashlib.sha256((LAB/'inputs'/x['path']).read_bytes()).hexdigest()==x['sha256']
 year=[json.loads(x)for x in gzip.open(LAB/'inputs/YEAR_BE_ALIGNED_5M.jsonl.gz','rt')]
 recent=[]
 for filename in ['RUBIK_TRAIN_ALL.json.gz','RUBIK_VALIDATION_ALL.json.gz']:
  for x in json.loads(gzip.decompress((LAB/'inputs'/filename).read_bytes())):
   if x['name']=='PF_BASE' and x['period'] in ['TRAIN','H2']:recent.append(x)
 assert len({(x['symbol'],x['signal_ms'])for x in recent})==len(recent)
 return {'YEAR_5M':year,'RECENT_1M':recent}

def layout(rows,corpus):
 a=sorted([x for x in rows if x['status']=='CLOSED'],key=lambda x:(x['exit_ms'],x['symbol'],x['signal_ms']))
 y=np.array([x.get('net_R') if x.get('net_R') is not None else np.nan for x in a]);t=np.array([x['packet']['observed_ms'] if corpus=='RECENT_1M' else x['signal_ms']for x in a],dtype=np.int64);ex=np.array([x['exit_ms']for x in a],dtype=np.int64)
 assert np.all(ex>=t)
 group=np.array([x['period'] if corpus=='RECENT_1M' else 'YEAR'for x in a]);windows={}
 for g in sorted(set(group)):
  ix=np.flatnonzero(group==g);j=np.searchsorted(ex[ix],t[ix],side='left');windows[g]=(ix,j)
 return a,y,t,ex,windows

def weights(y,windows):
 w=np.zeros((4,len(y)));w[3]=.25
 for ix,j in windows.values():
  v=y[ix];known=np.isfinite(v);v0=np.where(known,v,0);c=np.r_[0,np.cumsum(v0)];bad=np.r_[0,np.cumsum(~known)];gain=np.r_[0,np.cumsum(np.maximum(v0,0))];loss=np.r_[0,np.cumsum(np.maximum(-v0,0))]
  for n,ks in [(10,[0]),(20,[1,2,3])]:
   left=np.maximum(j-n,0);total=c[j]-c[left];complete=j>=n;invalid=complete & ((bad[j]-bad[left])>0);positive=complete & (total>0)
   for k in ks:
    if k==2:
     g=gain[j]-gain[left];l=loss[j]-loss[left];w[k,ix]=(complete & (((l>0)&(g>=l))|((l==0)&(g>0)))).astype(float)
    elif k==3:w[k,ix]=np.where(positive,1.,.25)
    else:w[k,ix]=positive.astype(float)
    w[k,ix[invalid]]=np.nan
 return w

def metrics(y,w,mask):
 valid=mask & np.isfinite(y)&np.isfinite(w);v=y[valid]*w[valid];active=w[valid]>0;tr=v[active];eq=np.cumsum(v);dd=float(np.max(np.maximum.accumulate(np.r_[0,eq])[1:]-eq))if len(v)else 0;gain=float(tr[tr>0].sum());loss=float(-tr[tr<0].sum());base=float(y[valid].sum());net=float(v.sum())
 return dict(n=int(active.sum()),eligible_known_n=int(valid.sum()),rejected_n=int((~active).sum()),memory_gap_n=int((mask & ~np.isfinite(w)).sum()),outcome_gap_n=int((mask & ~np.isfinite(y)).sum()),WR=100*float(np.mean(tr>0))if len(tr)else None,PF=gain/loss if loss else None,netR=net,USD_at_5R=net*5,maxDD_R=dd,paired_BASE_netR=base,deltaR=net-base,risk_fraction_mean=float(w[valid].mean())if valid.any()else None)

def bh(p):
 a=np.array(p);order=np.argsort(a);q=np.ones(len(a));v=1.
 for k in range(len(a)-1,-1,-1):i=order[k];v=min(v,float(a[i])*len(a)/(k+1));q[i]=v
 return q.tolist()

def clustering(y):
 s=np.sign(y);valid=np.isfinite(s)&(s!=0);pair=valid[1:]&valid[:-1];a=s[:-1][pair];b=s[1:][pair];ac=float(np.corrcoef(a,b)[0,1])if len(a)>2 and np.std(a)>0 and np.std(b)>0 else None;v=s[valid];n1=int(sum(v>0));n2=int(sum(v<0));n=n1+n2;runs=1+int(np.sum(v[1:]!=v[:-1]))if n else 0;mu=1+2*n1*n2/n if n else None;var=2*n1*n2*(2*n1*n2-n)/(n*n*(n-1))if n>1 else 0;z=math.copysign(max(abs(runs-mu)-.5,0),runs-mu)/math.sqrt(var)if var>0 else None
 return dict(known_sign_n=n,unknown_outcomes=int(sum(~np.isfinite(y))),adjacent_known_pairs=len(a),lag1_sign_autocorrelation=ac,runs=runs,runs_expected=mu,runs_z=z,runs_two_sided_p=math.erfc(abs(z)/math.sqrt(2))if z is not None else None,limitations='Runs on known subset; gaps excluded. Autocorrelation only adjacent complete signs. Ties, overlaps and missing observations prevent iid proof.')

def main():
 data=load();out=LAB/'RESULTS';out.mkdir(exist_ok=True);tables=[];inventory={};clusters={};decisions=[];regimes={};nulls={};curves={};rng=np.random.default_rng(20261116)
 for corpus,rows in data.items():
  a,y,t,ex,win=layout(rows,corpus);w=weights(y,win);start,end,half,tail=BOUNDS[corpus];masks={'H1':(t>=start)&(t<half-81*H),'H2':(t>=half)&(t<end-81*H),'TAIL40':(t>=tail)&(t<end-81*H)}
  inventory[corpus]=dict(source_records=len(rows),closed=len(a),known_net_n=int(np.isfinite(y).sum()),unknown_net_n=int((~np.isfinite(y)).sum()),status_counts={s:sum(x['status']==s for x in rows)for s in sorted(set(x['status']for x in rows))},decision_min_ms=int(t.min()),decision_max_ms=int(t.max()),duplicate_close_timestamp_n=int(len(ex)-len(set(ex))),memory_restart='TRAIN/H2 separately due to saved purge gap'if corpus=='RECENT_1M'else 'continuous, unknown outcomes remain in memory',bounds=BOUNDS[corpus]);clusters[corpus]=clustering(y)
  masks_items=list(masks.items());base={k:metrics(y,np.ones(len(y)),mask)for k,mask in masks_items};actual={};null=np.zeros((1000,3,4));
  for k,mask in masks_items:
   tables.append(dict(corpus=corpus,period=k,name='PF_BASE',**base[k]));actual[k]=[metrics(y,z,mask)for z in w]
  # Same causal timestamps for each shuffled netR assignment; unknown positions fixed.
  known=np.flatnonzero(np.isfinite(y))
  for rep in range(1000):
   yy=y.copy();yy[known]=rng.permutation(y[known]);ww=weights(yy,win)
   for pi,(period,mask)in enumerate(masks_items):
    for k in range(4):
     valid=mask & np.isfinite(yy)&np.isfinite(ww[k]);null[rep,pi,k]=float((yy[valid]*(ww[k,valid]-1)).sum())
  nulls[corpus]=dict(statistic='paired switch minus base netR',period_order=list(masks),variant_order=NAMES,deltaR=null)
  for pi,(period,mask)in enumerate(masks_items):
   ps=[(1+int(sum(null[:,pi,k]>=actual[period][k]['deltaR'])))/1001 for k in range(4)];qs=bh(ps)
   for k,name in enumerate(NAMES):tables.append(dict(corpus=corpus,period=period,name=name,**actual[period][k],control_p=ps[k],BH4_q=qs[k],null_delta_mean=float(null[:,pi,k].mean()),null_delta_p05=float(np.quantile(null[:,pi,k],.05)),null_delta_p95=float(np.quantile(null[:,pi,k],.95))))
  order=np.argsort(t,kind='stable');trans=[];old=None
  for i in order:
   state='DATA_GAP_MEMORY'if not np.isfinite(w[1,i])else 'ON'if w[1,i]>0 else 'OFF_OR_WARMUP'
   if state!=old:trans.append(dict(start_decision_ms=int(t[i]),state=state));old=state
   decisions.append(dict(corpus=corpus,symbol=a[i]['symbol'],signal_ms=a[i]['signal_ms'],decision_ms=int(t[i]),entry_ms=a[i]['entry_ms'],exit_ms=int(ex[i]),net_R=y[i],**{n:w[k,i]for k,n in enumerate(NAMES)}))
  for x,nxt in zip(trans,trans[1:]):x['end_exclusive_ms']=nxt['start_decision_ms']
  if trans:trans[-1]['end_exclusive_ms']=None
  regimes[corpus]=dict(intervals=trans,last_decision_ms=int(t.max()),current_november_regime='UNKNOWN_NO_COMPLETE_NET_OUTCOME_HISTORY',asof_corpus_only=True)
  curves[corpus]=dict(exit_ms=ex,base=np.cumsum(np.nan_to_num(y)),switches={n:np.cumsum(np.nan_to_num(y*w[k]))for k,n in enumerate(NAMES)},note='Unknown pnl or unknown switch weight omitted, never inferred; not complete account equity.')
  print(corpus,'completed1000controls',flush=True)
 save(out/'DATA_INVENTORY.json',inventory);save(out/'CLUSTERING.json',clusters);save(out/'TABLES.json',tables);save(out/'SHUFFLED_CONTROLS.json.gz',nulls);save(out/'TRADE_DECISIONS.json.gz',decisions);save(out/'REGIME_INTERVALS.json',regimes);save(out/'CURVES.json.gz',curves)
 fields=list(tables[0])+[k for k in tables[1]if k not in tables[0]]
 # JSON remains authoritative: CSV union includes control fields on later switch rows.
 fields=sorted(set(k for r in tables for k in r))
 with (out/'TABLES.csv').open('w')as f:wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(tables)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
 for ax,(corpus,c)in zip(axes,curves.items()):
  x=np.array(c['exit_ms'],dtype='datetime64[ms]');ax.plot(x,c['base'],label='PF_BASE',linewidth=2)
  for n,z in c['switches'].items():ax.plot(x,z,label=n,linewidth=1)
  ax.axhline(0,color='grey',linewidth=.5);ax.set_title(corpus+' | saved, known outcomes only');ax.set_ylabel('R (original base risk budget)');ax.legend(ncol=5);ax.grid(alpha=.2)
 fig.savefig(out/'EQUITY_CURVES.png',dpi=140);plt.close(fig)
 candidates=[]
 for name in NAMES:
  r=[x for x in tables if x['corpus']=='RECENT_1M'and x['name']==name];passed=all(x['n']>=30 and x['netR']>0 and x['PF']is not None and x['PF']>=1.3 and x['deltaR']>0 and x['BH4_q']<=.05 and x['memory_gap_n']==0 and x['outcome_gap_n']==0 for x in r)
  if passed:candidates.append(dict(name='PF_SWITCH_'+name,rule=name,paper_only=True,requires_future_holdout=True,requires_execution_engine_support=True,source_model='RESEARCH_TOP50_RAW_NOT_LIVE_FACTORY'))
 save(LAB/'PAPER_VARIANTS.json',candidates);(LAB/'variants.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n'for x in candidates))
 report=['# PF: переключение по своей кривой','',f'Готовые исходы, без нового replay. Кандидатов: {len(candidates)}. YEAR_5M и RECENT_1M не смешиваются; годовая история не является 1m.','', '![Кривые известных результатов](RESULTS/EQUITY_CURVES.png)','', '## Кластеризация до проверки правил','']
 for c,x in clusters.items():report.append(f"{c}: lag1 знаков={x['lag1_sign_autocorrelation']}; runs p={x['runs_two_sided_p']}; неизвестных исходов={x['unknown_outcomes']}. Тест диагностический, не доказательство iid или режима.")
 report+=['','## Все четыре варианта против базы и1000 перестановок','','|Корпус|Период|Правило|n|WR%|PF|netR|DD R|парный BASE R|delta R|BH q|Memory gaps|','|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in tables:
  def fmt(k):v=r.get(k);return 'NA'if v is None else f'{v:.4f}'if isinstance(v,float)else str(v)
  report.append('|'+r['corpus']+'|'+r['period']+'|'+r['name']+'|'+'|'.join(fmt(k)for k in ['n','WR','PF','netR','maxDD_R','paired_BASE_netR','deltaR','BH4_q','memory_gap_n'])+'|')
 report+=['','## Полосы и текущий режим','Точные наблюдённые переходы SW20 сохранены в RESULTS/REGIME_INTERVALS.json и каждое решение в TRADE_DECISIONS.json.gz. Это описание состояний фиксированного правила. Начало текущей ноябрьской полосы установить нельзя: готовая годовая модель заканчивается раньше live-когорты, ноябрьский netR модели неполон. Последнее состояние исторического корпуса не является текущим состоянием16ноября.','', '## Ограничения','YEAR содержит неизвестный funding: эти закрытия остаются в памяти и блокируют неполные окна, а не выкидываются. Delta сравнивает с базой на той же пригодной парной выборке; полный известный PF_BASE показывается отдельно. Недавний H2 стартует с пустой памятью из-за сохранённого81h разрыва. В кривых неизвестный результат пропущен, это не полная equity счёта. Издержки уже включены в исходные netR, SW_HALF масштабирует тот же исходный риск. DD по закрытиям, не mark-to-market и не процент капитала. Перестановки сохраняют времена, перемешивают только известные доходности: проверка условна на расписании и пропусках. H2 и TAIL40 пересекаются; история уже использовалась, будущего независимого теста нет. Стратегия не объявляется точной репликой LIVE Bybit.','', '## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА', 'Четыре переключателя проверены без подбора параметров. '+('Есть только исследовательские кандидаты для независимой проверки, не разрешение на торговлю.'if candidates else 'Ни один не прошёл заранее зафиксированные условия кандидата. Прибыльный устойчивый режим не доказан.'),'', 'Desktop Commander 0, Bybit-ключи 0, LIVE изменений 0']
 (LAB/'OTCHET_DLYA_CLAUDE_CODEX_PF_EQUITY_SWITCH_20261116.md').write_text('\n'.join(report)+'\n');save(LAB/'CHECKPOINT.json',dict(stage='COMPLETE',code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),variants=NAMES,controls_per_corpus=1000,candidates=len(candidates),history_replayed=False,source_manifest_sha256=hashlib.sha256((LAB/'INPUT_MANIFEST.json').read_bytes()).hexdigest(),next='Independent audit; no new parameters on observed results',LIVE_changes=0))
if __name__=='__main__':main()
