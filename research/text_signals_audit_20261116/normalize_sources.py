from pathlib import Path
import json,gzip,hashlib,sys,re,random,collections,unicodedata
P=Path('/workspace/car-text-signals-audit/research/text_signals_audit_20261116');sys.path.insert(0,str(P));from classifier import classify
SRC=Path('/workspace/car-managers-authors-20261114/delivery_package/research/managers_authors_20261114/results');old=[json.loads(x)for x in gzip.decompress(b''.join(f.read_bytes()for f in sorted(SRC.glob('parsed_posts.jsonl.gz.part*')))).splitlines()];idx={(r['channel'],r['id']):r for r in old};known={r['symbol'][:-4]for r in old if r.get('symbol')};channels={};sha=lambda b:hashlib.sha256(b).hexdigest()
for f in sorted(Path('/workspace/channels-v2-private-normalized').glob('*.json.gz'),key=lambda f:(f.name.startswith('METADATA'),f.name)):
 d=json.loads(gzip.decompress(f.read_bytes()))
 for ch,rows in d['channels'].items():
  for r in rows:channels.setdefault(ch,{})[r['id']]=r
safe_words=set('long short лонг шорт стоп словили закрыла закрываем фикс фиксируем бу безубыток добор добрали тейк вход цена уровень liquidity обновили все максимумы полка ликвидности снизу жду откат фиксации часов entry stop loss tp sl target reached hit close closed profit итоги месяц неделя buy sell market limit shorting longing above below выше ниже'.split())
def redact(t):
 t=unicodedata.normalize('NFKC',t)
 t=re.sub(r'(?i)\b(?:signal\s*)?id\b[^\nA-Za-zА-Яа-я]*[A-Za-z0-9_-]+',' ',t)
 t=re.sub(r'(?<!\w)\d{9,}(?!\w)','[NUMBER_REMOVED]',t)
 t=re.sub(r'(?i)\b(?:signal\s+)?id\s*[:#]?\s*[A-Za-z0-9]+',' ',t)
 t=re.sub(r'https?://\S+|t\.me/\S+|@[\w]+',' ',t)
 return ' '.join(w if w.lower()in safe_words or (w==w.upper()and w.strip('#$').removesuffix('USDT')in known) or re.fullmatch(r'[+−-]?\d+(?:[.,]\d+)?[%$Rr]?',w)else '…'for w in re.findall(r'[A-Za-zА-Яа-яЁё0-9_+−.%$-]+',t))[:500]
allrows=[];byclass=collections.defaultdict(list);coverage=[];reg=json.loads((P/'CHANNEL_REGISTRY.json').read_text())
for ch in reg:
 rows=channels.get(ch,{});counts=collections.Counter();missing=0;executable=0
 for r in sorted(rows.values(),key=lambda x:(x.get('datetime_utc')or'',x['id'])):
  c=classify(r.get('text',''),known);o=idx.get((ch,r['id']),{});key=sha((ch+':'+str(r['id'])).encode());lack=not o.get('stop')or not o.get('targets');newmissing=c['label']=='SIGNAL'and lack and o.get('status')!='PARSED';counts[c['label']]+=1;missing+=newmissing;executable+=bool(newmissing and c['executable_text_direction']and not r.get('forwarded_from'))
  reply=r.get('reply_to')or'';m=re.search(r'/'+re.escape(ch)+r'/(\d+)(?:\?|$)',reply,re.I)
  if o.get('classification')=='NON_CRYPTO_INSTRUMENT':c['flags'].append('LEGACY_NON_CRYPTO_INSTRUMENT');c['executable_text_direction']=False
  a=dict(channel=ch,post_key=key,date=r.get('datetime_utc'),**c,old_status=o.get('status','UNKNOWN'),old_classification=o.get('classification','UNKNOWN'),missing_explicit_SL_TP=bool(lack),new_missing_levels_signal=bool(newmissing),edited=bool(r.get('edited_visible')),forwarded=bool(r.get('forwarded_from')),reply_to=sha((ch+':'+m[1]).encode())if m else None,text_sha256=r.get('text_sha256'),redacted_text=redact(r.get('text','')),stop=o.get('stop'),targets=o.get('targets')or[])
  allrows.append(a);byclass[c['label']].append(a)
 coverage.append(dict(channel=ch,posts=len(rows),classes=dict(counts),text_signals_without_levels_previously_unparsed=missing,unconditional_unforwarded_candidates=executable,share_among_detected_signals=missing/counts['SIGNAL']if counts['SIGNAL']else None,note='Parser candidate posts, not verified independent trades; no missing levels invented'))
(P/'inputs/CLASSIFIED_POSTS.json.gz').write_bytes(gzip.compress(json.dumps(allrows,ensure_ascii=False).encode(),mtime=0));(P/'SOURCE_COVERAGE.json').write_text(json.dumps(coverage,indent=2)+'\n');rng=random.Random(20261116);samples={c:rng.sample(v,min(30,len(v)))for c,v in sorted(byclass.items())};(P/'REVIEW_PACK_30_PER_CLASS.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2)+'\n');print('TOTAL',len(allrows),dict(collections.Counter(r['label']for r in allrows)),'MISSING',sum(x['text_signals_without_levels_previously_unparsed']for x in coverage),'CANDIDATES',sum(x['unconditional_unforwarded_candidates']for x in coverage))
