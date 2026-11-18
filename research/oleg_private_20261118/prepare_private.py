"""Run only where private archives are available; writes numeric/aggregate allowlist."""
import json,pathlib,gzip,hashlib,sys,collections
from parser import build
root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);allplans=[];allclaims=[];stats=[];classified=[]
source={'OLEG':json.load((root/'oleg_raw.json').open())['messages']}
for f in (root/'channels').glob('*.jsonl'):source[f.stem]=[json.loads(s)for s in f.open()if s.strip()]
for ch,rs in source.items():
 plans,claims,st,cl=build(ch,rs);allplans+=plans;allclaims+=claims;stats.append(st);classified+=cl;print(ch,'posts',st['posts'],'signals',st['signals'],'structured',st['structured'],'text',st['text'],'events',st['signals_with_events'],'labels',st['labels'],flush=True)
for n,v in [('PLANS.json.gz',allplans),('CLAIMS.json.gz',allclaims),('CLASSIFICATION.json.gz',classified)]:
 (out/n).write_bytes(gzip.compress(json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0))
(out/'DATA_INVENTORY.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n');(out/'PRIVATE_SOURCE_PROVENANCE.json').write_text(json.dumps(dict(oleg_blob='e6c66348127c9c8c2bf3a36221b08ade621e405f',private19_blob='4f9fac60aa57777e902482ef547a9d0b13b49ab6',oleg_sha256=hashlib.sha256((root/'oleg_raw.json').read_bytes()).hexdigest(),zip_sha256=hashlib.sha256((root/'tg_private.zip').read_bytes()).hexdigest(),private_raw_copied_to_public=False,raw_posts=sum(s['posts']for s in stats),plans=len(allplans),claims=len(allclaims),parser_frozen_commit='8fe9b5e7c79be5e1ec9ad7d249260401e6de4074'),indent=2)+'\n')
