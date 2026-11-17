"""Rebuild and verify classifications without market data or overwriting frozen inputs."""
import json,gzip,hashlib,sys
from pathlib import Path
from parser import build
P=Path(__file__).resolve().parent
raw=(P.parent/'inputs/speculantka/posts.jsonl').read_bytes()
assert hashlib.sha256(raw).hexdigest()==json.loads((P/'INPUT_MANIFEST.json').read_text())['sha256']
new=build([json.loads(x)for x in raw.splitlines()])
old=json.loads(gzip.decompress((P/'CLASSIFICATION_AND_LINKS.json.gz').read_bytes()))
# Legacy parser enumerates equal-length dictionary coins from a set.
# Only ordering of alternatives in ambiguous NON-signals may vary by Python hash seed.
assert new['signals']==old['signals']
for d in [new,old]:
 for r in d['records']:r['coin_candidates']=sorted(r['coin_candidates'])
assert new==old
print(json.dumps(dict(status='PASS',source_sha256=hashlib.sha256(raw).hexdigest(),signals=len(new['signals']),all_signal_records_identical=True,ambiguous_coin_candidate_order_canonicalized=True,frozen_files_modified=False)))
