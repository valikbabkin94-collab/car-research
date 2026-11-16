"""HTTP fixture tests; no fabricated price/PnL history."""
import tempfile,io,urllib.error,json
from pathlib import Path
from resilient_http import Client,FileFailed,NetworkPause,ascii_url
from collect_priority1 import archive
class Clock:
 def __init__(self):self.t=0
 def now(self):return self.t
 def sleep(self,n):self.t+=n
class Response:
 status=200
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self):return b'ok'
with tempfile.TemporaryDirectory() as d:
 clock=Clock();attempt=[0]
 def opener(url,**kwargs):
  attempt[0]+=1
  if attempt[0]<3:raise urllib.error.HTTPError(url,503 if attempt[0]==1 else 429,'temporary',{'Retry-After':'7' if attempt[0]==1 else '0'},io.BytesIO(b'temporary'))
  return Response()
 c=Client(Path(d)/'retry.jsonl',clock=clock.now,sleep=clock.sleep,opener=opener);assert c.get('https://example.test/data')==b'ok';assert attempt[0]==3 and clock.t>=17
 # Two entire failed files followed by a third distinct failure invoke600s cooldown.
 clock=Clock()
 def failed(url,**kwargs):raise urllib.error.HTTPError(url,503,'temporary',{},io.BytesIO(b'temporary'))
 c=Client(Path(d)/'cooldown.jsonl',clock=clock.now,sleep=clock.sleep,opener=failed)
 for file in ['a','b','c']:
  try:c.get('https://example.test/'+file)
  except FileFailed:pass
 assert c.cooldowns==1 and clock.t>=600
 events=[json.loads(x) for x in (Path(d)/'cooldown.jsonl').read_text().splitlines()];assert len([x for x in events if x.get('status')==503])==18
 assert any(x.get('event')=='COOLDOWN' and x['seconds']==600 for x in events)
 # SHA failure must not create a parsed market file.
 class BadChecksum:
  def get(self,url,file_id):return b'0'*64+b' filename' if url.endswith('.CHECKSUM') else b'actual bytes'
 try:archive(BadChecksum(),'test.zip',Path(d));raise AssertionError('SHA mismatch accepted')
 except ValueError as e:assert 'CHECKSUM_MISMATCH' in str(e)
 assert not list(Path(d).glob('*.npz'))

 # Regression for the actual failed key class: Unicode symbols must reach urllib
 # as ASCII escapes, with original source identity unchanged. No market/PnL data.
 sent=[]
 def unicode_wire(url,**kwargs):
  url.encode('ascii');sent.append(url);return Response()
 raw='https://data.binance.vision/data/futures/um/monthly/klines/币安人生USDT/1h/币安人生USDT-1h-2026-10.zip.CHECKSUM'
 c=Client(Path(d)/'unicode.jsonl',spacing=0,opener=unicode_wire)
 assert c.get(raw,file_id='币安人生USDT_source_key')==b'ok'
 assert '%E5%B8%81' in sent[0] and ascii_url(sent[0])==sent[0]
 encoded='https://example.test/path?a=%E5%B8%81&b=1+2'
 assert ascii_url(encoded)==encoded
 assert ascii_url('https://example.test/BTCUSDT.zip')=='https://example.test/BTCUSDT.zip'
 try:ascii_url('https://example.test/file#unexpected');raise AssertionError('fragment accepted')
 except ValueError:pass

print(json.dumps({'status':'PASS','checks':['503_and429_retry_after','six_attempts_per_file','600_second_distinct_file_cooldown','checksum_mismatch_never_writes_data','unicode_wire_ascii_and_idempotence','preserve_encoded_queries','reject_fragments'],'market_pnl':False},indent=2))
