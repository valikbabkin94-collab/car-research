"""Private GitHub normalized-member reader. HTML never extracted or parsed."""
from pathlib import Path
import subprocess,json,gzip,hashlib,io,tarfile,base64,concurrent.futures as cf,sys,re,datetime as dt,collections
PUBLIC=Path('/workspace/car-channels-audit-v2/research/channels_audit_v2_20261116');sys.path.insert(0,str(PUBLIC));from update_parser import actions
SRC=Path('/workspace/car-managers-authors-20261114/delivery_package');manifest=json.loads((SRC/'data/published_tg_20261114/manifest.json').read_text());ROOT=Path('/workspace/channels-v2-private-normalized');ROOT.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def key(ch,mid):return sha((ch+':'+str(mid)).encode())
def fetch(part):
 res=json.loads(subprocess.check_output(['gh','api','repos/valikbabkin94-collab/Crypto-Auto-Radar/contents/'+part['path']+'?ref=data%2Ftg-mirrors-20261114']));b=base64.b64decode(res['content']);assert len(b)==part['bytes'] and sha(b)==part['sha256'];return b
for arch in manifest:
 dest=ROOT/(arch['channel']+'.json.gz')
 if dest.exists():continue
 try:
  with cf.ThreadPoolExecutor(max_workers=4)as pool:raw=b''.join(pool.map(fetch,arch['parts']))
  assert len(raw)==arch['bytes'] and sha(raw)==arch['sha256'];members={};metadata={}
  with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as tar:
   for m in tar.getmembers():
    if not m.isfile()or not m.name.startswith('study_input_20261114/'):continue
    if m.name.endswith('/posts.jsonl'):
     ch=m.name.split('/')[1];members[ch]=[json.loads(x)for x in tar.extractfile(m).read().splitlines()]
    elif m.name.endswith('/coverage.json'):
     ch=m.name.split('/')[1];metadata[ch]=json.load(tar.extractfile(m))
  dest.write_bytes(gzip.compress(json.dumps(dict(channels=members,coverage=metadata,archive_sha=arch['sha256'])).encode(),mtime=0));print('NORMALIZED',arch['channel'],sum(map(len,members.values())),flush=True)
 except Exception as e:print('GAP',arch['channel'],type(e).__name__,flush=True)
# Apply metadata-correction overlay after originals; no HTML or personal IDs exported.
channels={};meta={};sources=[]
for arch in manifest:
 dest=ROOT/(arch['channel']+'.json.gz')
 if not dest.exists():continue
 d=json.loads(gzip.decompress(dest.read_bytes()));sources.append(dict(channel=arch['channel'],archive_sha256=d['archive_sha'],normalized_cache_sha256=sha(dest.read_bytes())))
 for ch,rows in d['channels'].items():
  idx=channels.setdefault(ch,{})
  for r in rows:idx[r['id']]=r
 meta.update(d['coverage'])
p=SRC/'research/managers_authors_20261114/results';parsed=[json.loads(x)for x in gzip.decompress(b''.join(x.read_bytes()for x in sorted(p.glob('parsed_posts.jsonl.gz.part*')))).splitlines()];old=[json.loads(x)for x in gzip.open(p/'outcomes.jsonl.gz','rt')];oldby={(r['channel'],r['id']):r for r in old};bych=collections.defaultdict(list);signals=[]
for r in parsed:
 if r['status']!='PARSED':continue
 pub=int(dt.datetime.fromisoformat(r['datetime_utc']).timestamp()*1000)
 if pub>=1794614400000:continue
 source=channels.get(r['channel'],{}).get(r['id'],{});s={k:r[k]for k in ['channel','symbol','side','entry_low','entry_high','stop','targets','edited_visible']};s.update(post_key=key(r['channel'],r['id']),pub=pub,text_sha256=r['text_sha256'],events=[],author_identity='UNKNOWN_CHANNEL_LEVEL_ATTRIBUTION',source_forwarded=bool(source.get('forwarded_from')))
 o=oldby.get((r['channel'],r['id']));s['legacy']={k:o['variants'].get(v)for k,v in [('P4','M2'),('P5','M3')]}if o and 'variants'in o else {};signals.append(s);bych[r['channel']].append((r['id'],s))
coverage=[];unlinked=[];claims=[]
oldcov={r['channel']:r for r in json.loads((p/'coverage.json').read_text())}
for ch in json.loads((PUBLIC/'CHANNEL_REGISTRY.json').read_text()):
 rows=channels.get(ch,{});ordered=sorted(rows.values(),key=lambda r:(r.get('datetime_utc')or'',r['id']));sigs=bych[ch];smap=dict(sigs);counts=collections.Counter();linked=set();ambiguous=0
 for r in ordered:
  text=r.get('text','');acts=[] if r['id']in smap else actions(text)
  if re.search(r'(?i)(?:monthly|month|месяц|итог|result|profit|прибыль)',text) and re.search(r'[+−-]?\d+(?:\.\d+)?\s*%',text):claims.append(dict(channel=ch,post_key=key(ch,r['id']),status='NON_COMPARABLE_CAPITAL_LEVERAGE_FEES_UNSPECIFIED'))
  if not acts:continue
  if not r.get('datetime_utc'):continue
  pub=int(dt.datetime.fromisoformat(r['datetime_utc']).timestamp()*1000);candidates=[];method=None
  reply=r.get('reply_to')or'';match=re.search(r'(?:^|/)'+re.escape(ch)+r'/(\d+)(?:\?|$)',reply,re.I)
  if match and int(match[1])in smap and smap[int(match[1])]['pub']<pub:candidates=[smap[int(match[1])]];method='EXACT_REPLY'
  else:
   symbols={s['symbol'] for mid,s in sigs if 0<pub-s['pub']<=30*86400000 and re.search(r'(?<![A-Za-z0-9])'+re.escape(s['symbol'][:-4])+r'(?:[/ _-]?USDT)?(?![A-Za-z0-9])',text,re.I)}
   candidates=[s for mid,s in sigs if s['symbol']in symbols and 0<pub-s['pub']<=30*86400000];side='LONG'if re.search(r'\blong\b|лонг',text,re.I)else 'SHORT'if re.search(r'\bshort\b|шорт',text,re.I)else None
   if side:candidates=[s for s in candidates if s['side']==side]
   method='UNIQUE_SYMBOL_SIDE_TIME'
  if method=='EXACT_REPLY' and candidates:
   explicit_side='LONG' if re.search(r'\blong\b|лонг',text,re.I) else 'SHORT' if re.search(r'\bshort\b|шорт',text,re.I) else None
   if explicit_side and explicit_side!=candidates[0]['side']:candidates=[];method='REPLY_DIRECTION_CONFLICT'
  if r.get('forwarded_from') and method!='EXACT_REPLY':candidates=[];method='FORWARDED_AUTHOR_UNKNOWN'
  counts.update(a['kind']for a in acts)
  if len(candidates)==1:
   s=candidates[0];linked.add(s['post_key'])
   for act in acts:s['events'].append(dict(**act,pub=pub,effective_ms=pub//60000*60000+60000,post_key=key(ch,r['id']),link_method=method,edited_visible=bool(r.get('edited_visible')),source_text_sha256=r.get('text_sha256')))
  else:
   ambiguous+=int(len(candidates)>1);unlinked.append(dict(channel=ch,post_key=key(ch,r['id']),pub=pub,kinds=[a['kind']for a in acts],status='AMBIGUOUS'if candidates else 'UNLINKED',candidate_n=len(candidates)))
  if re.search(r'(?i)(?:monthly|month|месяц|итог|result|profit|прибыль)',text)and re.search(r'[+−-]?\d+(?:\.\d+)?\s*%',text):claims.append(dict(channel=ch,post_key=key(ch,r['id']),pub=pub,status='NON_COMPARABLE_CAPITAL_LEVERAGE_FEES_UNSPECIFIED'))
 ids=sorted(rows);slots=max(ids)-min(ids)+1 if ids else 0;coverage.append(dict(channel=ch,normalized_posts=len(rows),original_full_signals=len(sigs),signals_with_any_linked_update=len(linked),update_coverage=len(linked)/len(sigs)if sigs else None,update_kind_counts=dict(counts),ambiguous_update_posts=ambiguous,edited_visible=sum(bool(r.get('edited_visible'))for r in rows.values()),deleted_visible=sum(bool(r.get('deleted_visible'))for r in rows.values()),numerical_slots=slots,missing_numerical_slots=slots-len(ids),gap_fraction=(slots-len(ids))/slots if slots else None,mirror_status=meta.get(ch,{}).get('status','DATA_GAP_NORMALIZED_POSTS'),integrity='UNKNOWN_NOT_DELETION_PROOF',source_authors='UNKNOWN_MULTIAUTHOR_POSSIBLE',actionable_update_signals=sum(any(e['kind']in ['CLOSE_ALL','CLOSE_PART','MOVE_BE','MOVE_STOP']for e in sig['events'])for mid,sig in sigs),legacy_classification_counts=oldcov.get(ch,{}).get('classification_counts',{})))
def save(n,obj):
 b=(json.dumps(obj,ensure_ascii=False,allow_nan=False)+'\n').encode();(PUBLIC/'inputs'/n).write_bytes(gzip.compress(b,mtime=0)if n.endswith('.gz')else b)
save('SIGNALS_WITH_UPDATES.json.gz',signals);save('CHANNEL_SOURCE_COVERAGE.json',coverage);save('UNLINKED_UPDATES.json.gz',unlinked);save('AUTHOR_STAT_CLAIMS.json',list({x['post_key']:x for x in claims}.values()));save('SOURCE_MANIFEST.json',sources);splits=json.loads((p/'split_definitions.json').read_text());save('LEGACY_SPLITS.json',splits)
print('COMPLETE',len(signals),len(coverage),'linked',sum(c['signals_with_any_linked_update']for c in coverage),flush=True)
