"""Independent entrypoints for V2 and package parts. Every variant is frozen before PnL."""
import sys,os,json,gzip,hashlib,time,io,csv,zipfile,urllib.request,urllib.error,subprocess,collections,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from .common import *
from .study import study,passed
CODES=['X'+str(i)for i in range(1,10)]
TWELVE=['E2','E3','E3_FROZEN_FLIP','E4','G3','R1_L30_LONG_ONLY','R1_L30_LONG_SHORT','R1_L90_LONG_ONLY','R1_L90_LONG_SHORT','S3','SPECULANTKA','TEXT_Whalesguide']
BASE=Path(__file__).resolve().parents[1]

def live_inputs():
 p=Path('research/paket_20261117/part7_live_trades/inputs/live_trades_all.json')
 if p.exists():return load(p)['trades']
 b=fetch_github('research/paket_20261117/part7_live_trades/inputs/live_trades_all.json',os.environ['LIVE_INPUT_SHA']);return json.loads(b)['trades']
def native_entries():return load('inputs_v1/ENTRIES.json.gz')
def prepare_market(entries,out,asof):
 market=Market(asof);windows=[(e['symbol'],e['entry_ms']-8*DAY,min(asof,e['entry_ms']+11*DAY))for e in entries];write(out/'SOURCES.json',market.collect(windows));return market

def report(out,title,summary,tables=(),notes=''):
 text='# '+title+'\n\n'+summary+'\n\n'
 if tables:
  text+='|Вариант|Период|n|WR%|PF|netR|$5/R|DD R|excessR|BH q|\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
  for r in tables:text+='|'+r.get('case','')+' '+r.get('variant','')+(' MIRROR'if r.get('mirror')else'')+'|'+r.get('period','')+'|'+'|'.join('—'if r.get(k)is None else str(round(r[k],5))if isinstance(r[k],float)else str(r[k])for k in['n','WR','PF','netR','USD_at_5risk','maxDD_R','excessR','BH_q'])+'|\n'
 text+='\n'+notes+'\n\n## ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА\n\nВыбор сделан только по H1; результаты H2 и последних40% сохранены без повторного подбора. Неполные цены и неопределённость риска не заменены выдуманными значениями. Положительная таблица без независимых критериев не означает доказанную прибыльность.\n\nDesktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0\n';(out/'REPORT_RU.md').write_text(text)

def pf_validation(market,entries,out):
 matched=[];bad=[]
 for e in entries:
  market.get(e['symbol']);v=resolve_entry(market.q,dict(e,entry_window_ms=5*M))
  if v is None:bad.append(dict(key=e['key'],symbol=e['symbol'],bucket=e['entry_ms'],status='DATA_GAP'))
  else:matched.append(dict(key=e['key'],symbol=e['symbol'],bucket=e['entry_ms'],first_compatible_minute=v,price=e['entry']))
 result=dict(input_signals=2113,frozen_entries=len(entries),compatible=len(matched),fraction=len(matched)/max(1,len(entries)),missing_by_symbol=dict(collections.Counter(r['symbol']for r in bad)),missing=bad,matched=matched,entry_price_unchanged=True,coarse_clock_resolution='Earliest compatible candle in original5m bucket; not a measured tick fill',eligible=len(matched)/max(1,len(entries))>=.9);write(out/'PF_5M_ENTRY_VALIDATION.json',result);return result

def path_diagnostic(market,entries,sp,out):
 records=[]
 for e in entries:
  q=market.get(e['symbol']);t=resolve_entry(q,e);atr=market.atr(min(e['signal_ms'],e['entry_ms']))
  if t is None:records.append(dict(key=e['key'],actual=[-1,-1],control=[]));continue
  widths=[.01,1.5*atr/e['entry']if atr is not None else 0.];actual=[int(path_first(q,t,e['entry'],e['side'],w))if w>0 else-1 for w in widths];a=max(sp[0]if e['entry_ms']<sp[1]else sp[1],e['entry_ms']-7*DAY);b=min((sp[1]if e['entry_ms']<sp[1]else sp[3])-72*H,e['entry_ms']+7*DAY,market.asof-72*H);rng=np.random.default_rng(SEED+int(e['key'][:12],16));controls_p=[]
  if b>=a:
   for ts in rng.integers((a+M-1)//M,max((a+M-1)//M+1,b//M+1),200)*M:
    i=np.searchsorted(q[:,0],ts)
    if i>=len(q)or q[i,0]!=ts:controls_p.append([-1,-1]);continue
    price=float(q[i,1]);atr0=market.atr(int(ts)-(e['entry_ms']-e['signal_ms']));ww=[.01,1.5*atr0/price if atr0 is not None else 0.];controls_p.append([int(path_first(q,int(ts),price,e['side'],w))if w>0 else-1 for w in ww])
  records.append(dict(key=e['key'],entry_ms=e['entry_ms'],actual=actual,control=controls_p))
 gzip_json(out/'PATH_FIRST_DIAGNOSTIC.json.gz',records)
 summaries=[]
 for z,name in enumerate(['R_1_PERCENT','R_ATR_STOP']):
  aa=[r['actual'][z]for r in records if r['actual'][z]in[0,1]];cc=[v[z]for r in records for v in r['control']if v[z]in[0,1]];summaries.append(dict(unit=name,decisive_actual=len(aa),P_MFE_first=sum(aa)/len(aa)if aa else None,decisive_controls=len(cc),P_control=sum(cc)/len(cc)if cc else None,censored_not_failures=True,diagnostic_not_gate=True))
 write(out/'PATH_SUMMARY.json',summaries)

def v2(out,asof):
 entries=native_entries();groups={c:[dict(e)for e in entries if e['scenario']==c]for c in TWELVE};pf=[dict(e,entry_window_ms=5*M)for e in entries if e['scenario']=='PF_BASE'];groups['PF_BASE']=pf;market=prepare_market([e for es in groups.values()for e in es],out,asof);validation=pf_validation(market,pf,out);allrows=[];results={};family=13*12
 for name,es in groups.items():
  result=study(market,es,CODES,out/name,mirrors=True,family_count=family);results[name]=result
  for r in result['tables']:r['case']=name;allrows.append(r)
  path_diagnostic(market,es,splitting(es),out/name)
 for period in ['H2','LAST40']:
  rows=[r for r in allrows if r['period']==period];qs=bh([r['p']for r in rows]+[1.]*max(0,family-len(rows)))
  for r,q in zip(rows,qs):r['BH_q']=q
 variants=[]
 for name,result in results.items():
  write(out/name/'TABLES.json',finite(result['tables']))
  for key,flip in [('winner',False),('mirror_winner',True)]:
   code=result['selection'][key]
   if code and passed(result['tables'],code,flip)and(name!='PF_BASE'or validation['eligible']):variants.append(dict(name='MGR2_'+name+'_'+code+('_MIRROR'if flip else''),source_scenario=name,manager=code,mirror=flip,enabled=False,status='PROMISING_REQUIRES_CLAUDE_REVIEW'))
 write(out/'ALL_TABLES.json',finite(allrows));write(out/'variants.json',variants);live=live_inputs();write(out/'LIVE_SMALL_N_INPUTS.json',dict(n=len(live),sources=dict(collections.Counter(t['source']for t in live)),status='Full X0-X9 replay independently in parallel Part7; source-risk audit there; no emergency stop used as1R',inputs=live))
 report(out,'Manager all scenarios v2',f'12 исходных наборов и отдельная проверка PF_BASE. Пяти минутам соответствует {validation["compatible"]}/{len(pf)} входов ({validation["fraction"]:.2%}). Кандидатов {len(variants)}. Первичный критерий: excess netR замороженного H1-победителя против200 контролей, BH по156 слотам, q≤.10.',allrows,notes='v1 не переписывалась. Все X1–X9 рассчитаны на H1; на H2 только frozen winner и отдельно H1-selected mirror. Форма пути — диагностика. Малая живая выборка разобрана отдельно в Part7, без повторного запуска тех же исходов здесь.')
 return dict(status='COMPLETE_WITH_DATA_GAPS',candidates=len(variants),PF_match_fraction=validation['fraction'])

def pf_exits(out,asof):
 es=[dict(e,entry_window_ms=5*M)for e in native_entries()if e['scenario']=='PF_BASE'];market=prepare_market(es,out,asof);validation=pf_validation(market,es,out);codes=[f'T{t}S{s}B{b}'for t in range(6)for s in range(3)for b in range(3)];result=study(market,es,codes,out,unit=.056,family_count=54,extra_fixed=['T0S1B0']);winner=result['selection']['winner'];variants=[]
 if winner and validation['eligible']and passed(result['tables'],winner):variants=[dict(name='PF_EXIT_'+winner,enabled=False,signal_R_fraction=.056,SL_can_exceed_1R=True,status='PROMISING_REQUIRES_CLAUDE_REVIEW')]
 write(out/'variants.json',variants);post=[];reentries=[]
 for e in es:
  q=market.get(e['symbol']);r=model(market,e,'T0S1B0',unit=.056)
  if r[0]!=1:post.append(dict(key=e['key'],status=int(r[0])));continue
  lastprice=r[14+4*(int(r[12])-1)];a=np.searchsorted(q[:,0],r[7]);record=dict(key=e['key'],exit_ms=r[7],last_exit_price=lastprice)
  for hh in[24,72]:
   b=np.searchsorted(q[:,0],r[7]+hh*H);bars=q[a:b];full=len(bars)==hh*60 and len(bars)>0 and bars[-1,0]==r[7]+hh*H-M
   record[str(hh)]=dict(status='AVAILABLE'if full else'DATA_GAP',extra_fall_pct=100*(1-float(bars[:,3].min())/lastprice)if full else None,adverse_pct=100*(float(bars[:,2].max())/lastprice-1)if full else None)
  adverse_then_drop=False;adverse=False;same_bar_unknown=False
  for bar in q[a:np.searchsorted(q[:,0],r[7]+72*H)]:
   if adverse and bar[3]<=lastprice*.85:adverse_then_drop=True;break
   if bar[2]>=lastprice*1.05 and bar[3]<=lastprice*.85:same_bar_unknown=True
   if bar[2]>=lastprice*1.05:adverse=True
  record['adverse5_then_favourable15_72h_envelope']=adverse_then_drop if record['72']['status']=='AVAILABLE'else None;record['same_bar_order_unknown']=same_bar_unknown;post.append(record)
  if r[8]==3:
   armed=False;re=None
   for bar in q[a:np.searchsorted(q[:,0],r[7]+24*H)]:
    if not armed:
     if bar[4]<e['entry']:armed=True
     continue
    if bar[2]>=e['entry']and bar[3]<=e['entry']:re=dict(e,entry_ms=int(bar[0]),signal_ms=int(bar[0])-M,entry_window_ms=M);break
   if re is not None:rr=model(market,re,'T0S1B0',unit=.056);reentries.append(dict(parent=e['key'],status='ATTEMPTED',result=finite(rr)))
   else:reentries.append(dict(parent=e['key'],status='NO_REENTRY_OR_DATA_GAP'))
 gzip_json(out/'AFTER_EXIT.json.gz',finite(post));gzip_json(out/'ONE_BE_REENTRY.json.gz',reentries)
 report(out,'Часть6 — PUMP_FADE 54 выхода',f'2113 исходных записей; {len(es)} сохранённых исполненных входов, все отказы учтены отдельно в исходном replay. 54 комбинации на TRAIN. Frozen winner {winner}; кандидатов {len(variants)}.',result['tables'],notes='R в этой части всегда сигнал5.6% цены, включая S1/S2: широкий стоп действительно увеличивает риск вR, а не прячет его сменой знаменателя. $5/R — исходный ценовой риск; комиссии добавляются. After-exit и повтор после BE — фиксированные диагностики, не подбор новых правил. Повтор: дождаться закрытия ниже старого входа, затем впервые возврата к resting short limit в24ч; единственный вариант T0S1B0.')
 return dict(status='COMPLETE_WITH_DATA_GAPS',winner=winner,candidates=len(variants))

def main():
 part=sys.argv[1];out=Path(os.environ.get('LAB_OUTPUT','research/paket_20261117/'+part));out.mkdir(parents=True,exist_ok=True);asof=int(os.environ['LAB_ASOF_MS']);sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();write(out/'STARTED.json',dict(part=part,code_sha=sha,asof=asof))
 if part=='v2':result=v2(out,asof)
 elif part=='part6_pf_exits':result=pf_exits(out,asof)
 else:
  from .extra import execute
  result=execute(part,out,asof)
 write(out/'CHECKPOINT.json',dict(part=part,code_sha=sha,asof=asof,**result,no_live_changes=True));write(out/'ARTIFACT_HASHES.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)and p.name!='ARTIFACT_HASHES.json'})
if __name__=='__main__':main()
