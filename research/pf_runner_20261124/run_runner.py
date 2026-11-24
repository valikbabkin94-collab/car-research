"""New exits on cached PR4 fills. Never recalculates entries or baseline PnL."""
import argparse,collections,datetime as dt,gzip,hashlib,json,os
from pathlib import Path
import numpy as np
from runner_tail import create,advance,MODES
from pr4_engine import funding_result
D=Path('/dev/shm/car_runner_20261124')
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def loadgz(p):return[json.loads(s)for s in gzip.open(p,'rt')]
def price(r,cost):return(r['gross_return']-cost/10000)/.056

def stats(rows,bp):
 rr=sorted(rows,key=lambda r:(r['exit_ms'],r['id']));v=[price(r,bp)for r in rr];g=sum(x for x in v if x>0);l=-sum(x for x in v if x<0);eq=peak=dd=0
 for x in v:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
 n=len(v);tail=sorted(v)[:max(1,int(np.ceil(.05*n)))];worst=sorted(rr,key=lambda r:price(r,bp))[:10]
 return dict(n=n,WR=100*sum(x>0 for x in v)/n if n else None,mean_R=sum(v)/n if n else None,sum_R=sum(v),PF=g/l if l else None,DD_R=dd,min_R=min(v)if v else None,CVaR5=sum(tail)/len(tail)if n else None,worst10=[{'id':r['id'],'R':price(r,bp)}for r in worst])
def ci(delta,weeks,alpha):
 if len(delta)<40 or len(set(weeks))<8:return None
 keys=sorted(set(weeks));groups={k:[]for k in keys}
 for d,w in zip(delta,weeks):groups[w].append(d)
 sums=np.array([sum(groups[k])for k in keys]);counts=np.array([len(groups[k])for k in keys]);rng=np.random.default_rng(20261124)
 w=rng.multinomial(len(keys),np.full(len(keys),1/len(keys)),size=20000);b=(w@sums)/(w@counts)
 return [float(np.quantile(b,alpha/2)),float(np.quantile(b,1-alpha/2))]
def pair_metrics(base,run,bp,regime):
 bs={r['id']:r for r in base if regime=='ALL'or r['regime']==regime};rs={r['id']:r for r in run if regime=='ALL'or r['regime']==regime};assert set(bs)==set(rs)
 ids=sorted(bs);ds=[price(rs[k],bp)-price(bs[k],bp)for k in ids];weeks=[dt.datetime.fromtimestamp(bs[k]['signal_ms']/1000,dt.timezone.utc).strftime('%G-W%V')for k in ids]
 known=[k for k in ids if bs[k].get('funding_R_proxy')is not None and rs[k].get('funding_R_proxy')is not None];nds=[price(rs[k],bp)+rs[k]['funding_R_proxy']-price(bs[k],bp)-bs[k]['funding_R_proxy']for k in known]
 n=len(ds);return dict(regime=regime,cost_bp=bp,n=n,weeks=len(set(weeks)),mean_delta_R=sum(ds)/n if n else None,better_pct=100*sum(x>1e-10 for x in ds)/n if n else None,worse_pct=100*sum(x< -1e-10 for x in ds)/n if n else None,tie_pct=100*sum(abs(x)<=1e-10 for x in ds)/n if n else None,CI95=ci(ds,weeks,.05),CI_family98_75=ci(ds,weeks,.0125),CI_status='SMALL_SAMPLE'if n<40 or len(set(weeks))<8 else'EXPOSED_WEEK_CLUSTER_BOOTSTRAP',common_known_funding_n=len(known),common_known_funding_mean_delta=sum(nds)/len(nds)if nds else None,true_net_delta=None,baseline=stats(list(bs.values()),bp),runner=stats(list(rs.values()),bp))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['train','test'],required=True);ap.add_argument('--root',type=Path,default=D);a=ap.parse_args();root=a.root;out=root/'results';out.mkdir(exist_ok=True)
 if(out/('COMPLETE_'+a.stage+'.json')).exists():raise RuntimeError('ALREADY_COMPLETE_NO_REPEAT')
 split=a.stage.upper();allbase=loadgz(root/'input'/('TRAIN_ALL_ROWS.jsonl.gz'if split=='TRAIN'else'TEST_ALL_ROWS.jsonl.gz'))
 base=[r for r in allbase if r['entry_mode']=='LIVE_GATES_REPRICE_5M_PROXY'and r['exit_mode']=='E0'and r['status']=='CLOSED'];assert len(base)==(564 if split=='TRAIN'else 473)
 packets={x['id']:x for x in json.loads((root/'prepared/packets.json').read_text())};funding=json.loads((root/'prepared/funding.json').read_text())
 with np.load(root/'prepared/frames.npz',allow_pickle=False)as z:frames={k:z[k]for k in z.files}
 allrows=[];table=[]
 for mode in [m for m in MODES if m!='BASE']:
  rows=[]
  for b in base:
   frame=frames[packets[b['id']]['frame_key']];p=create(b['entry'],b['entry_ms'],mode);advance(p,frame[frame[:,0]>=b['entry_ms']]);assert p['status']=='CLOSED'
   r={**b,**p,'runner_mode':mode,'cached_base_exit_ms':b['exit_ms'],'cached_base_gross_return':b['gross_return']};r['funding_R_proxy'],r['funding_status']=funding_result(r,frame,funding);rows.append(r)
   # Both policies are identical before TP2 (or TP3 for RUN10), check cached events without replaying baseline.
   pre=2 if mode!='TP3_RUN10'else 3
   be=[e for e in b['events']if e['kind'].startswith('TP')and int(e['kind'][2:])<pre]
   re=[e for e in r['events']if e['kind'].startswith('TP')and int(e['kind'][2:])<pre]
   assert be==re
  allrows+=rows
  for regime in ['ALL','DOWN','SIDEWAYS','UP']:
   for bp in [21,40]:table.append(dict(mode=mode,split=split,**pair_metrics(base,rows,bp,regime)))
 (out/(split+'_RUNNER_ROWS.jsonl.gz')).write_bytes(gzip.compress(('\n'.join(json.dumps(r,allow_nan=False)for r in allrows)+'\n').encode(),mtime=0));save(out/(split+'_METRICS.json'),table)
 if split=='TRAIN':
  ranks=[x for x in table if x['regime']=='ALL'and x['cost_bp']==40];ranks.sort(key=lambda x:(-x['mean_delta_R'],x['runner']['DD_R'],x['mode']))
  save(out/'TRAIN_SELECTION.json',{'winner':ranks[0]['mode'],'ranked':ranks,'chosen_only_TRAIN':True,'absolute_profit_not_assumed':True})
 else:
  assert(root/'selection_commit.json').exists(),'commit winner before TEST'
 save(out/('COMPLETE_'+a.stage+'.json'),{'stage':a.stage,'code_commit':os.environ.get('CODE_COMMIT'),'base_reused_n':len(base),'new_modes':4,'new_exit_rows':len(allrows),'base_replayed':False,'entry_replayed':False,'complete':True})
 print(json.dumps({'stage':a.stage,'n_base':len(base),'new_exit_rows':len(allrows)}))
if __name__=='__main__':main()
