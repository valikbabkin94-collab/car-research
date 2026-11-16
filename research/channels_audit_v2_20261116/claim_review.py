"""Market-touch compatibility of explicit TP claims. No PnL or author return inference."""
import json
from pathlib import Path
import numpy as np
from market import Quotes,save,M
LAB=Path(__file__).parent

def check_claim(q,r):
 a=r['signal_pub']//M*M+M;b=r['claim_pub']//M*M;out=dict(r,verification='TP_INDEX_UNRESOLVED',levels=[])
 if not r['targets']:return out
 if b<=a:out['verification']='NO_FULL_MINUTE_BEFORE_CLAIM';return out
 lo=int(np.searchsorted(q[:,0],a))if len(q)else 0;hi=int(np.searchsorted(q[:,0],b))if len(q)else 0;v=q[lo:hi]
 if len(v)!=(b-a)//M or len(v)and(v[0,0]!=a or v[-1,0]!=b-M or np.any(np.diff(v[:,0])!=M)):
  out['verification']='DATA_GAP_PROXY_PRICES';return out
 for t in r['targets']:
  touched=bool(np.any(v[:,2]>=t['price']))if r['side']=='LONG'else bool(np.any(v[:,3]<=t['price']));out['levels'].append(dict(**t,market_touch=touched))
 out['verification']='MARKET_TOUCH_COMPATIBLE_NOT_FILL_PROOF'if all(x['market_touch']for x in out['levels'])else 'NO_TOUCH_IN_COMPLETE_PROXY_WINDOW_NOT_FRAUD_PROOF'
 return out

def main():
 rows=json.loads((LAB/'inputs/TP_CLAIM_REQUESTS.json').read_text());q=Quotes('work/market');q.http.get=lambda *args:(_ for _ in ()).throw(RuntimeError('NO_NETWORK_DURING_CLAIM_REVIEW'));results=[check_claim(q.load(r['symbol']),r)for r in sorted(rows,key=lambda r:(r['symbol'],r['claim_pub']))];save(LAB/'RESULTS/TP_CLAIM_MARKET_CHECK.json',results)
 counts={s:sum(r['verification']==s for r in results)for s in sorted(set(r['verification']for r in results))};save(LAB/'RESULTS/TP_CLAIM_SUMMARY.json',dict(counts=counts,scope='Only explicitly linked TP-reached messages with unambiguous numbered targets, full closed minutes after signal before claim',limitations='Binance proxy, no actual author fill or position size, edited/deleted/VIP unknown, publication-minute touch excluded, not monthly return verification'))
 print(counts)
if __name__=='__main__':main()
