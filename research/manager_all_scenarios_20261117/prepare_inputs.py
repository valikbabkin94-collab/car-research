from pathlib import Path
import json,gzip,csv,io,hashlib,collections,ast,subprocess
P=Path('research/manager_all_scenarios_20261117');sources=json.loads((P/'SOURCE_MANIFEST.json').read_text());rows=[];excluded=[]
def load(n):
 b=gzip.decompress((P/'inputs'/(n+'.gz')).read_bytes())
 try:return json.loads(b)
 except ValueError:return [json.loads(x)for x in b.splitlines()]if b.startswith(b'{')else list(csv.DictReader(io.StringIO(b.decode())))
def add(r,name,lineage,defaultside=None,source=None):
 s=r.get('side',r.get('direction',defaultside));s={'LONG':1,'SHORT':-1,'long':1,'short':-1}.get(s,s)
 if s is None and r.get('initial_stop')and r.get('entry'):s=1 if r['initial_stop']<r['entry']else -1
 t=r.get('entry_ms');price=r.get('entry');sig=r.get('signal_ms',r.get('pub',t));key=hashlib.sha256(json.dumps([name,r.get('post_key'),r.get('id'),r.get('symbol'),sig,t],sort_keys=True).encode()).hexdigest()
 if not t or not price or s not in [-1,1]:excluded.append(dict(scenario=name,key=key,source_status=r.get('status'),reason='NO_FROZEN_EXECUTED_ENTRY_OR_DIRECTION'));return
 ev=[]
 for e in r.get('events',[]):
  tm=e.get('time_ms',e.get('bar_open_ms'))
  if tm and e.get('price')and e.get('fraction')is not None:ev.append(dict(time_ms=int(tm),price=float(e['price']),fraction=float(e['fraction']),kind=e['kind']))
 stop=r.get('initial_stop',r.get('stop'));risk=r.get('risk_fraction')or (abs(price-stop)/price if stop else .056 if name in ['PF_BASE','S1']else None)
 packet=r.get('packet',{});rows.append(dict(key=key,scenario=name,lineage=lineage,symbol=r['symbol'],signal_ms=int(sig or t),entry_ms=int(t),entry=float(price),side=int(s),entry_type=packet.get('entry_type',r.get('entry_policy','LIMIT'if r.get('limit')else'MARKET')),native_risk_fraction=risk,native_events=ev,native_status=r.get('status'),native_net_R=r.get('net_R',r.get('netR',r.get('net_R_closed'))),source=source or name,edited=bool(r.get('edited',r.get('edited_visible')))))
for n in ['PF_BASE','S1','S2','S3','G3']:
 for r in load(n):add(r,n,'PF'if n in ['PF_BASE','S1']else n,-1 if n in ['PF_BASE','S1','S2']else 1,n)
for n in ['RUBIK_TRAIN','RUBIK_H2']:
 for r in load(n):
  name=r.get('name')
  if name not in ['E1','E2','E3','E4']:continue
  if r.get('parent'):
   add(dict(r['parent'],symbol=r['symbol']),name,'PF',-1,n);add(dict(r['flip'],symbol=r['symbol']),name+'_FROZEN_FLIP','PF',1,n)
  else:add(r,name,'PF',-1,n)
for n in ['TEXT','SPEC']:
 for r in load(n):
  if r.get('policy')!='T1':continue
  name='SPECULANTKA'if n=='SPEC'else 'TEXT_'+r['channel'];add(r,name,'TG_'+r.get('channel','SPECULANTKA'),source=n)
for r in load('CHANNEL_P1'):
 if r.get('policy')=='P1'and r.get('channel')in ['Whalesguide','WolfxCrypto_VIP','BitcoinBullet_official']:add(r,'P1_'+r['channel'],'TG_'+r['channel'],source='CHANNEL_P1')
for n in [r['name']for r in sources if r['name'].startswith('L30_')or r['name'].startswith('L90_')]:
 pos=collections.defaultdict(float)
 for r in sorted(load(n),key=lambda r:int(r['time_ms'])):
  sy=r['symbol'];before=pos[sy];delta=float(r['quantity_delta']);after=before+delta
  if abs(after)<1e-7:after=0.
  if after and (not before or before*after<0):add(dict(symbol=sy,entry_ms=int(r['time_ms']),entry=float(r['reference_open']),side=1 if after>0 else-1,status='FROZEN_POSITION_START'), 'R1_'+n,'R1',source=n)
  pos[sy]=after
# Exact same source event duplicated only once per scenario, no global cross-scenario deletion.
seen=set();unique=[]
for r in rows:
 k=(r['scenario'],r['symbol'],r['entry_ms'],r['side'],r['entry'])
 if k in seen:excluded.append(dict(scenario=r['scenario'],key=r['key'],reason='EXACT_EXECUTED_ENTRY_DUPLICATE'))
 else:seen.add(k);unique.append(r)
(P/'ENTRIES.json.gz').write_bytes(gzip.compress(json.dumps(unique,sort_keys=True).encode(),mtime=0));(P/'EXCLUDED_INPUTS.json.gz').write_bytes(gzip.compress(json.dumps(excluded,sort_keys=True).encode(),mtime=0));(P/'INPUT_COVERAGE.json').write_text(json.dumps(dict(entries=len(unique),scenarios=dict(collections.Counter(r['scenario']for r in unique)),excluded=dict(collections.Counter(r['scenario']for r in excluded)),source_names=[r['name']for r in sources]),indent=2)+'\n')
