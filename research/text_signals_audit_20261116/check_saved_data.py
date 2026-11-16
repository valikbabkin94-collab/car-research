"""Availability only: no execution, returns, strategy selection or network downloads."""
import json,gzip,collections,hashlib,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from market import Quotes,Funding,save,M,H
P=Path(__file__).parent

def main():
 raw=(P/'inputs/TEXT_COHORT.json.gz').read_bytes();rows=json.loads(gzip.decompress(raw));q=Quotes('work/market');f=Funding('source','work/funding-audit');out=[]
 for r in sorted(rows,key=lambda r:(r['symbol'],r['pub'])):
  a=(r['pub']+M+M-1)//M*M;bars=q.load(r['symbol']);lo=int(np.searchsorted(bars[:,0],a-24*H))if len(bars)else 0;hi=int(np.searchsorted(bars[:,0],a+72*H))if len(bars)else 0;segment=bars[lo:hi];complete=len(segment)==96*60 and len(segment)>0 and segment[0,0]==a-24*H and segment[-1,0]==a+72*H-M and bool(np.all(np.diff(segment[:,0])==M));entry=int(np.searchsorted(bars[:,0],a))if len(bars)else 0;entry_ok=entry<len(bars)and int(bars[entry,0])==a
  out.append(dict(post_key=r['post_key'],channel=r['channel'],symbol=r['symbol'],decision_ms=a,entry_minute_available=bool(entry_ok),full_24h_past_72h_future_prices=bool(complete),full_72h_funding_known=f.known(r['symbol'],a,a+72*H),edited=r['edited'],classification='STILL_PENDING_SEMANTIC_REVIEW'))
 counts=dict(cohort_n=len(out),entry_available=sum(r['entry_minute_available']for r in out),full_price_window=sum(r['full_24h_past_72h_future_prices']for r in out),full_funding=sum(r['full_72h_funding_known']for r in out),both_price_funding=sum(r['full_24h_past_72h_future_prices']and r['full_72h_funding_known']for r in out),cohort_sha256=hashlib.sha256(raw).hexdigest(),PnL_calculated=False,selection_changed=False)
 save(P/'SAVED_DATA_AVAILABILITY.json',dict(summary=counts,rows=out));print(counts)
 ck=json.loads((P/'CHECKPOINT.json').read_text());ck.update(saved_data_availability_checked=True,saved_data_summary=counts);save(P/'CHECKPOINT.json',ck)
if __name__=='__main__':main()
