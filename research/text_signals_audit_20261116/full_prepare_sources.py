from pathlib import Path
import subprocess,json,gzip,hashlib,sys,re,datetime as dt,random,collections
P=Path('/workspace/car-text-signals-audit/research/text_signals_audit_20261116');sys.path.insert(0,str(P));from classifier import classify
sys.path.insert(0,'/workspace/car-channels-audit-v2/research/channels_audit_v2_20261116');from update_parser import actions
old=json.loads(gzip.decompress(subprocess.check_output(['git','show','32f48a5:research/text_signals_audit_20261116/inputs/CLASSIFIED_POSTS.json.gz'],cwd=P.parents[1])));base=[r for r in old if r['new_missing_levels_signal']and r['executable_text_direction']and not r['forwarded']];assert len(base)==374,len(base);keys={r['post_key']for r in base};raw={};bych=collections.defaultdict(list);known={r['symbol'][:-4]for r in old if r.get('symbol')};h=lambda ch,n:hashlib.sha256((ch+':'+str(n)).encode()).hexdigest()
for f in sorted(Path('/workspace/channels-v2-private-normalized').glob('*.json.gz'),key=lambda f:(f.name.startswith('METADATA'),f.name)):
 d=json.loads(gzip.decompress(f.read_bytes()))
 for ch,rows in d['channels'].items():
  for r in rows:raw[h(ch,r['id'])]=r
for k,r in raw.items():bych[r['channel']].append((k,r))
coverage=[]
for ch,posts in sorted(bych.items()):
 cc=collections.Counter(classify(r.get('text',''),known)['label']for key,r in posts);coverage.append(dict(channel=ch,posts=len(posts),classes=dict(cc),OTHER_share=cc['OTHER']/len(posts)if posts else None))
(P/'FULL_CLASS_COVERAGE.json').write_text(json.dumps(coverage,indent=2)+'\n')
plans=[];seen=set();cool={};funnel=collections.Counter()
for r in sorted(base,key=lambda r:(r['date']or'',r['post_key'])):
 source=raw[r['post_key']];c=classify(source.get('text',''),known);pub=int(dt.datetime.fromisoformat(r['date']).timestamp()*1000);s={k:r.get(k)for k in ['post_key','channel','symbol','side','date','stop','targets','edited','old_classification']};s.update(pub=pub,events=[],status='CANDIDATE',classifier=c,original374=True);dupe=(r['channel'],source.get('text_sha256'));ck=(r['channel'],r['symbol'],r['side'])
 if c['label']!='SIGNAL' or not c['executable_text_direction']:s['status']='CLASSIFIER_REJECTED_NOT_FRESH_SIGNAL'
 elif dupe in seen:s['status']='DUPLICATE_TEXT'
 elif pub<cool.get(ck,-1)+6*3600000:s['status']='COOLDOWN6H'
 else:
  seen.add(dupe);cool[ck]=pub
  # Explicit single limit only. Do not invent a zone fill or unspecified price.
  text=source.get('text','');m=re.search(r'(?i)(?:limit|лимит).{0,30}?(?:entry|вход|:)?\s*\$?(\d+(?:\.\d+)?)',text)
  if m:s['explicit_limit']=float(m[1])
 funnel[s['status']]+=1;plans.append(s)
# No unverified links to multi-candidate positions. Exact reply or unique symbol within7days.
for ch,posts in bych.items():
 candidates=[s for s in plans if s['channel']==ch and s['status']=='CANDIDATE']
 for key,r in posts:
  if key in keys or not r.get('datetime_utc'):continue
  a=actions(r.get('text',''))
  if re.search(r'(?i)словили.{0,8}стоп|закрыла|закрыл|фиксируем|выходим',r.get('text','')) and not any(x['kind']in ['CLOSE_ALL','CLOSE_PART']for x in a):
   a.append(dict(kind='CLOSE_PART',fraction=.5)if re.search(r'(?i)половин',r.get('text',''))else dict(kind='CLOSE_ALL'))
  if not a:continue
  t=int(dt.datetime.fromisoformat(r['datetime_utc']).timestamp()*1000);reply=r.get('reply_to')or'';m=re.search(r'/'+re.escape(ch)+r'/(\d+)(?:\?|$)',reply,re.I);replykey=h(ch,int(m[1]))if m else None;possible=[s for s in candidates if 0<t-s['pub']<=7*86400000 and (s['post_key']==replykey if replykey else re.search(r'(?<![A-Za-z0-9])'+re.escape(s['symbol'][:-4])+r'(?:/?USDT)?(?![A-Za-z0-9])',r.get('text',''),re.I))]
  if len(possible)==1:
   for e in a:possible[0]['events'].append(dict(**e,pub=t,effective_ms=t//60000*60000+60000,post_key=key))
(P/'inputs/FULL_374_PLANS.json.gz').write_bytes(gzip.compress(json.dumps(plans).encode(),mtime=0));(P/'FULL_374_FUNNEL.json').write_text(json.dumps(dict(original374=len(plans),counts=dict(funnel),selection='Original frozen374,all classification/dedup exclusions retained as rows; no return-based selection'),indent=2)+'\n');print('FUNNEL',dict(funnel))
# New deterministic OTHER sample, full normalized text inspected locally; publish only opaque keys.
others=[]
for key,r in raw.items():
 if classify(r.get('text',''),known)['label']=='OTHER':others.append((key,r))
sample=random.Random(20261117).sample(sorted(others,key=lambda t:t[0]),30);(P/'OTHER_REVIEW_KEYS_AFTER_FIX.json').write_text(json.dumps([k for k,r in sample],indent=2)+'\n')
print('OTHER review keys saved;raw private text is deliberately not printed')
