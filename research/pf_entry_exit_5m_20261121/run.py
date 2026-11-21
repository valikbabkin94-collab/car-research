"""Bounded staged PF study; uses prepared real GitHub prices only, no network."""
import argparse,collections,csv,datetime as dt,gzip,hashlib,json,os,time
from pathlib import Path
import numpy as np
from engine import replay,costs,funding_result,ENTRIES,EXITS,H

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def gzsave(p,rows):p.write_bytes(gzip.compress(('\n'.join(json.dumps(x,ensure_ascii=False,allow_nan=False)for x in rows)+'\n').encode(),mtime=0))
def gzload(p):return [json.loads(x)for x in gzip.open(p,'rt')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(rows,cost):
 closed=sorted([r for r in rows if r['status']=='CLOSED'],key=lambda r:(r['exit_ms'],r['id']))
 vals=[costs(r,cost)for r in closed];gain=sum(x for x in vals if x>0);loss=-sum(x for x in vals if x<0);eq=peak=dd=0.
 for x in vals:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
 eligible=sum(r['status']not in ('RIGHT_CENSORED_80H','DATA_GAP_5M','TRAIN_PURGED_80H')for r in rows)
 known=[(r,v)for r,v in zip(closed,vals)if r.get('funding_R_proxy')is not None]
 netv=[v+r['funding_R_proxy']for r,v in known]
 return {'opportunities':len(rows),'eligible_80h':eligible,'n':len(closed),'fill_pct':100*len(closed)/eligible if eligible else None,
  'WR_price_pct':100*sum(v>0 for v in vals)/len(vals)if vals else None,'mean_price_R':sum(vals)/len(vals)if vals else None,
  'sum_price_R':sum(vals),'PF_price':gain/loss if loss else None,'maxDD_close_R':dd,
  'known_funding_proxy_n':len(known),'unknown_funding_n':len(closed)-len(known),'mean_R_known_funding_proxy':sum(netv)/len(netv)if netv else None,
  'sum_R_known_funding_proxy':sum(netv)if netv else None,'PF_known_funding_proxy':sum(v for v in netv if v>0)/(-sum(v for v in netv if v<0))if any(v<0 for v in netv)else None,
  'true_net_R':None,'statuses':dict(collections.Counter(r['status']for r in rows)),
  'hold_hours_mean':sum(r['hold_hours']for r in closed)/len(closed)if closed else None,
  'unique_symbols':len({r['symbol']for r in closed}),'unique_signal_days':len({dt.datetime.fromtimestamp(r['signal_ms']/1000,dt.timezone.utc).strftime('%Y-%m-%d')for r in closed}),
  'fillbar_TP_banned_n':sum(r['fill_bar_TP_banned']for r in closed),'ambiguous_pending_fill_TP1_n':sum(r['pending_fill_vs_TP1_order_ambiguous']for r in closed),
  'known_original_TP1_passed_entries':sum(r['original_TP1_already_passed_at_entry']for r in closed),'small_sample':len(closed)<40}

def evaluate(packets,frames,funding,configs,split):
 out=[];started=time.monotonic()
 for entry,ex in configs:
  for p in packets:
   if p['split']!=split:continue
   r=replay(p,frames[p['frame_key']],entry,ex)
   fr,why=funding_result(r,frames[p['frame_key']],funding);r.update(funding_R_proxy=fr,funding_status=why)
   out.append(r)
  if time.monotonic()-started>300:raise RuntimeError('STAGE_TIME_BUDGET_EXCEEDED')
 return out

def score(rows,configs):
 tables=[]
 for e,x in configs:
  rr=[r for r in rows if r['entry_mode']==e and r['exit_mode']==x]
  tables.append({'entry':e,'exit':x,**metrics(rr,.004)})
 good=[r for r in tables if r['n']>=100]
 good.sort(key=lambda r:(-(r['mean_price_R']or 0),-r['sum_price_R'],r['entry'],r['exit']))
 return tables,good

def final_views(rows,audit,out):
 configs=sorted({(r['entry_mode'],r['exit_mode'])for r in rows});table=[];concentr=[]
 for split in ['TRAIN','TEST']:
  for e,x in configs:
   for co in ['RAW','ARCHIVE_SELECTED_EXPOSED']:
    rr=[r for r in rows if r['split']==split and r['entry_mode']==e and r['exit_mode']==x and(co=='RAW'or r['archive_selected_exposed'])]
    for regime in ['ALL','DOWN','SIDEWAYS','UP','UNKNOWN']:
     rs=rr if regime=='ALL'else[r for r in rr if r['regime']==regime]
     for cost in [.0021,.004]:
      m=metrics(rs,cost);duration=(audit['cut_ms']-audit['min_signal_ms'])if split=='TRAIN'else(audit['max_signal_ms']+H-audit['cut_ms'])
      m.update(entry=e,exit=x,split=split,cohort=co,regime=regime,cost_bp=round(cost*10000),
        fills_month=m['n']/(duration/(86400000*365.25/12)),opportunities_month=len(rs)/(duration/(86400000*365.25/12)))
      table.append(m)
    for cost in [.0021,.004]:
     for axis in ['day','coin']:
      d=collections.defaultdict(float)
      for r in rr:
       if r['status']!='CLOSED':continue
       key=r['symbol']if axis=='coin'else dt.datetime.fromtimestamp(r['exit_ms']/1000,dt.timezone.utc).strftime('%Y-%m-%d')
       d[key]+=costs(r,cost)
      top=sorted(d.items(),key=lambda t:(-t[1],t[0]));total=sum(d.values())
      concentr.append({'entry':e,'exit':x,'split':split,'cohort':co,'cost_bp':round(cost*10000),'axis':axis,'groups':dict(d),
       'without_best3_R':total-sum(v for k,v in top[:3]),'best3_share_net':sum(v for k,v in top[:3])/total if total>0 else None})
 save(out/'METRICS.json',table);save(out/'CONCENTRATION.json',concentr)
 fields=['entry','exit','split','cohort','regime','cost_bp','opportunities','eligible_80h','n','fill_pct','WR_price_pct','mean_price_R','sum_price_R','PF_price','maxDD_close_R','fills_month','known_funding_proxy_n','unknown_funding_n','mean_R_known_funding_proxy','PF_known_funding_proxy','small_sample','unique_symbols','unique_signal_days']
 with(out/'METRICS.csv').open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(table)
 return table

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--stage',choices=['train_entries','train_exits','test'],required=True);a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=True);checkpoint=a.out/('COMPLETE_'+a.stage+'.json')
 if checkpoint.exists():raise RuntimeError('ALREADY_COMPLETE_DO_NOT_REPEAT')
 packets=json.loads((a.prepared/'packets.json').read_text());funding=json.loads((a.prepared/'funding.json').read_text());audit=json.loads((a.prepared/'INPUT_AUDIT.json').read_text())
 with np.load(a.prepared/'frames.npz',allow_pickle=False)as z:frames={k:z[k]for k in z.files}
 metadata={'stage':a.stage,'code_commit':os.environ.get('CODE_COMMIT'),'packet_sha256':sha(a.prepared/'packets.json'),'exposed_history':True}
 save(a.out/('STARTED_'+a.stage+'.json'),metadata)
 if a.stage=='train_entries':
  configs=[(e,'E0')for e in ENTRIES];rows=evaluate(packets,frames,funding,configs,'TRAIN');tables,good=score(rows,configs)
  if len(good)<2:raise RuntimeError('NOT_ENOUGH_TRAIN_CLOSED_N_FOR_TWO_ENTRIES')
  selection={**metadata,'entries':[r['entry']for r in good[:2]],'top2':good[:2],'profitability_not_assumed':True}
  gzsave(a.out/'TRAIN_ENTRIES_ROWS.jsonl.gz',rows);save(a.out/'TRAIN_ENTRY_TABLES.json',tables);save(a.out/'TRAIN_ENTRY_SELECTION.json',selection)
 elif a.stage=='train_exits':
  selected=json.loads((a.out/'TRAIN_ENTRY_SELECTION.json').read_text())
  configs=[(e,x)for e in selected['entries']for x in EXITS if x!='E0'];new=evaluate(packets,frames,funding,configs,'TRAIN')
  rows=gzload(a.out/'TRAIN_ENTRIES_ROWS.jsonl.gz')+new;configs=sorted({(r['entry_mode'],r['exit_mode'])for r in rows});tables,good=score(rows,configs)
  final={**metadata,'entry_selection_sha256':sha(a.out/'TRAIN_ENTRY_SELECTION.json'),'all_configs':configs,'winner':{'entry':good[0]['entry'],'exit':good[0]['exit']},'winner_train':good[0],'actual_combinations':len(configs),'parameter_selection_only_TRAIN':True}
  gzsave(a.out/'TRAIN_ALL_ROWS.jsonl.gz',rows);save(a.out/'TRAIN_ALL_TABLES.json',tables);save(a.out/'FINAL_TRAIN_SELECTION.json',final)
 else:
  selected=json.loads((a.out/'FINAL_TRAIN_SELECTION.json').read_text());rows=evaluate(packets,frames,funding,selected['all_configs'],'TEST')
  gzsave(a.out/'TEST_ALL_ROWS.jsonl.gz',rows);allrows=gzload(a.out/'TRAIN_ALL_ROWS.jsonl.gz')+rows;table=final_views(allrows,audit,a.out)
  win=selected['winner'];subset=[m for m in table if m['entry']==win['entry']and m['exit']==win['exit']and m['cohort']=='RAW'and m['regime']=='ALL']
  save(a.out/'FROZEN_WINNER_EVALUATION.json',{'winner':win,'actual_combinations':selected['actual_combinations'],'selected_on_TRAIN_only':True,'metrics':subset,'owner_forward_gate':'100 new shadow trades and >0.1R/trade; NOT FULFILLED BY THESE HISTORICAL TRADES','LIVE_changes':0,'true_net_R':None})
 save(checkpoint,{**metadata,'complete':True,'no_runtime_changes':True})
 print(json.dumps({'stage':a.stage,'complete':True,'rows':len(rows),'out':str(a.out)}))
if __name__=='__main__':main()
