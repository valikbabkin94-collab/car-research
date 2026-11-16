"""Deterministic candidate funnel; no prices, PnL, or profit-based selection."""
import json,gzip,collections,datetime as dt,hashlib
from pathlib import Path
LAB=Path(__file__).parent
BAD={'AD','UPDATE_TP_CLAIM','PAID_TEASER','NON_CRYPTO_INSTRUMENT','EMPTY'}
def main():
 raw=(LAB/'inputs/CLASSIFIED_POSTS.json.gz').read_bytes();rows=json.loads(gzip.decompress(raw));seen=set();last={};eligible=[];audit=[];counts=collections.Counter()
 for r in sorted(rows,key=lambda x:(x.get('date')or'',x['post_key'])):
  if not r['new_missing_levels_signal']:continue
  reasons=list(r['flags'])
  if r['old_classification']in BAD:reasons.append('LEGACY_AD_OR_OUTCOME_REQUIRES_REVIEW')
  if r['forwarded']or r['old_status']in ['REPOST_FORWARD','DUPLICATE']:reasons.append('REPOST_OR_DUPLICATE')
  if (r.get('symbol')or'').removesuffix('USDT')in ['XAU','XAG','GOLD','EUR','GBP','JPY']:reasons.append('ASSET_CLASS_UNRESOLVED')
  if not r['date']:reasons.append('NO_PUBLICATION_TIME');t=0
  else:t=int(dt.datetime.fromisoformat(r['date']).timestamp()*1000)
  if t>=1794614400000:reasons.append('AFTER_FROZEN_CUTOFF')
  k=(r['channel'],r.get('text_sha256'))
  if k in seen:reasons.append('REPEATED_TEXT')
  clock=(r['channel'],r['symbol'],r['side'])
  if not reasons and t<last.get(clock,-1)+6*3600000:reasons.append('COOLDOWN_6H')
  if not reasons:eligible.append(dict(r,pub=t,qualification='REVIEW_CANDIDATE_NOT_VERIFIED_TRADE'));seen.add(k);last[clock]=t
  counts.update(reasons or ['ELIGIBLE_FOR_REVIEW']);audit.append(dict(post_key=r['post_key'],channel=r['channel'],reasons=reasons))
 out=dict(source_sha256=hashlib.sha256(raw).hexdigest(),candidate_posts=len(audit),eligible_after_funnel=len(eligible),reason_counts=dict(counts),profitability='NOT_TESTED',selection='No PnL accessed; old AD/outcome classes remain reviewable, not permanently deleted')
 (LAB/'COHORT_FUNNEL.json').write_text(json.dumps(out,indent=2)+'\n');(LAB/'inputs/TEXT_COHORT.json.gz').write_bytes(gzip.compress(json.dumps(eligible).encode(),mtime=0));(LAB/'COHORT_EXCLUSIONS.json.gz').write_bytes(gzip.compress(json.dumps(audit).encode(),mtime=0));print(out)
if __name__=='__main__':main()
