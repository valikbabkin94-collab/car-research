"""Train-only exit selection; only frozen winners evaluated out of sample."""
import json,hashlib,collections,subprocess,time
from pathlib import Path
import numpy as np
from .common import *

def study(market,entries,codes,out,unit=None,mirrors=False,family_count=None,extra_fixed=()):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);entries=sorted(entries,key=lambda e:(e['symbol'],e['entry_ms']));sp=splitting(entries);table=[];train={c:[]for c in codes};actual_records=[];control_records=[];input_meta=[]
 def run_group(es,cs,mirror=False,with_controls=()):
  results={c:[]for c in cs};null={c:[]for c in cs}
  for i,e in enumerate(es):
   for c in cs:
    r=model(market,e,c,mirror,unit);results[c].append(r);actual_records.append((e['key'],c,mirror,r))
    if c in with_controls:
     v=controls(market,e,c,sp,mirror,unit);null[c].append(v);control_records.append((e['key'],c,mirror,v))
   if i%50==0:print('SIM',out.name,'MIRROR'if mirror else'',i,'/',len(es),flush=True)
  return results,null
 h1=[e for e in entries if phase(e,sp)=='H1'];h2=[e for e in entries if phase(e,sp)=='H2']
 rs,nc=run_group(h1,codes,with_controls=['X3','X6','X7']if mirrors else [])
 for c in codes:table.append(dict(period='H1',variant=c,mirror=False,**metrics(rs[c])))
 options=[(metrics(rs[c])['netR'],c)for c in codes if metrics(rs[c])['n']>=max(5,min(60,len(h1)))and metrics(rs[c])['n']/max(1,len(h1))>=.9]
 winner=max(options,key=lambda x:(x[0],x[1]))[1]if options else None
 mirror_codes=[c for c in ['X3','X6','X7']if c in rs and paired_test(rs[c],nc[c])['excessR']<0]if mirrors else[];mirror_winner=None
 if mirror_codes:
  mr,mn=run_group(h1,mirror_codes)
  for c in mirror_codes:table.append(dict(period='H1',variant=c,mirror=True,**metrics(mr[c])))
  opts=[(metrics(mr[c])['netR'],c)for c in mirror_codes if metrics(mr[c])['n']>=max(5,min(60,len(h1)))];mirror_winner=max(opts)[1]if opts else None
 frozen=dict(code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),winner=winner,mirror_winner=mirror_winner,train_only=True,train_rows_sha256=hashlib.sha256(np.array([r for _,_,_,r in actual_records]).tobytes()).hexdigest(),splits=sp,n_H1=len(h1),n_H2=len(h2));write(out/'SELECTION_FROZEN.json',frozen)
 for flip,chosen in [(False,winner),(True,mirror_winner)]:
  if chosen is None:continue
  testcodes=list(dict.fromkeys([chosen]+([]if flip else list(extra_fixed))));rr,nn=run_group(h2,testcodes,flip,testcodes)
  for c in testcodes:
   for period in ['H2','LAST40']:
    inds=[i for i,e in enumerate(h2)if period=='H2'or e['entry_ms']>=sp[2]];rows=[rr[c][i]for i in inds];ns=[nn[c][i]for i in inds];test=paired_test(rows,ns);table.append(dict(period=period,variant=c,mirror=flip,**metrics(rows),control_n=test['n'],control_coverage=test['coverage'],excessR=test['excessR'],p=test['p'],selected_on_H1=c==chosen))
 for period in ['H2','LAST40']:
  tests=[r for r in table if r['period']==period];ps=[r['p']for r in tests]+[1.]*max(0,(family_count or len(codes))-len(tests))
  for r,q in zip(tests,bh(ps)):r['BH_q']=q
 if actual_records:
  np.savez_compressed(out/'ALL_ACTUAL_EXITS.npz',keys=np.array([k for k,c,m,r in actual_records],dtype='S64'),variants=np.array([c for k,c,m,r in actual_records],dtype='S16'),mirrors=np.array([m for k,c,m,r in actual_records]),outcomes=np.array([r for k,c,m,r in actual_records]))
 if control_records:np.savez_compressed(out/'CONTROL200.npz',keys=np.array([k for k,c,m,v in control_records],dtype='S64'),variants=np.array([c for k,c,m,v in control_records],dtype='S16'),mirrors=np.array([m for k,c,m,v in control_records]),netR=np.array([v for k,c,m,v in control_records],dtype='f4'))
 write(out/'TABLES.json',finite(table));write(out/'INPUTS.json',entries);write(out/'OUTCOME_SCHEMA.json',{'array_columns':{'0':'status:1CLOSED,0CENSORED,-1NO_MINUTE,-2PRICE_NOT_REPRODUCIBLE,-3HOLD_GAP,-4INVALID_GEOMETRY,-5MISSING_PAST_FEATURES','1':'netR','2':'gross price fraction','3':'cost price fraction','4':'funding price fraction','5':'funding complete','6':'unknown funding adverse stress R','7':'exit_ms','8':'exit reason 1SL/2TP/3BE/4TIME/5TRAIL/6GIVEBACK','9':'MFE R','10':'MAE R','11':'hold_hours','12':'event_count','13..28':'up to4 events:time,price,fraction,kind','29':'initialSL price width','30':'R normalization width','31':'entry_ms resolved to source precision','32':'entryprice unchanged','34':'same-bar SL/TP ambiguity'}})
 return dict(selection=frozen,tables=table,actual=actual_records,controls=control_records)

def passed(table,winner,mirror=False,q=.10):
 rows=[r for r in table if r['variant']==winner and r.get('mirror',False)==mirror and r['period']in ['H1','H2','LAST40']]
 return len(rows)==3 and all(r['n']>=(60 if r['period']=='H1'else 30)and r['netR']>0 and r['netR_adverse']>0 and r['PF']is not None and r['PF']>=1.3 and r['top3_share']is not None and r['top3_share']<=.5 for r in rows)and all(r.get('BH_q',1)<=q and r.get('excessR',0)>0 and r.get('control_coverage',0)>=.9 for r in rows if r['period']!='H1')
