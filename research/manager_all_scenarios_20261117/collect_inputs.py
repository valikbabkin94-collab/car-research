"""Fetch immutable already-public source blobs. Only GitHub repository reads."""
from pathlib import Path
import json,urllib.request,os,base64,hashlib,concurrent.futures
P=Path(__file__).resolve().parent
manifest=json.loads((P/'SOURCE_MANIFEST.json').read_text())
headers={'User-Agent':'CAR-offline-research','Accept':'application/vnd.github+json'}
if os.environ.get('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
def get(path):
 with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/valikbabkin94-collab/car-research/'+path,headers=headers),timeout=60)as r:return json.load(r)
trees={ref:get('git/trees/'+ref+'?recursive=1')['tree']for ref in sorted({m['commit']for m in manifest})}
(P/'inputs').mkdir(exist_ok=True)
def one(m):
 p=P/'inputs'/m['local']
 if p.exists()and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']:return
 sha=next(v['sha']for v in trees[m['commit']]if v['path']==m['path']);raw=base64.b64decode(get('git/blobs/'+sha)['content']);assert hashlib.sha256(raw).hexdigest()==m['sha256'];p.write_bytes(raw)
list(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(one,manifest))
