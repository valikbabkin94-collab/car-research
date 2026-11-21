"""CAR research exporter. OFFLINE, explicit snapshots only; no network or trading SDK.
Does not read .env, credentials, Windows tasks or services. Never runs SQL writes.
Use --help. Output is PRIVATE; do not commit actual bundles to a public repository.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,hmac,io,json,os,re,secrets,sqlite3,sys
from pathlib import Path

SENSITIVE_KEY=re.compile(r'(?:api.?key|api.?secret|token|password|passphrase|authorization|cookie|private.?key|session|chat.?id|user.?id|raw.?text|^text$|^body$|^headers$)',re.I)
SENSITIVE_LINE=re.compile(r'api[_-]?(?:key|secret)|authorization|bearer\s|bot\d{5,}:|password|passphrase|set-cookie|[?&](?:token|key|secret)=|-----BEGIN .*PRIVATE KEY',re.I)
IDENTITY_KEY=re.compile(r'(?:^id$|(?:trade|order|signal|fill|exec|family|position|parent|stop|tp)[_-]?id$|^enter_tag$|^entry_tag$|^replyTo$|^owned_tp_ids$|^imported_cum$)',re.I)
DENY_NAME=re.compile(r'(?:^\.env(?:\.|$)|\.session(?:\.|$)|credentials|secrets|api[_-]?keys|^config\.|^ingest\.config)',re.I)
BASE_TABLES=('trades','orders','trade_custom_data','funding_fees','funding_payments','funding')
PAPER_TABLES=('positions','opportunities','events','runs','funding','funding_events','intents','rejections','price_batches','variants')
CANDIDATES=(
 'car_signals/signals.json','car_signals/strategy_state.json',
 'shadow/pump_fade_signals.ndjson','shadow/pump_fade_S.json','shadow/pump_fade30.json',
 'shadow/pump_fade_30.json','shadow/paper_channels.json','shadow/paper_channels.posts.jsonl',
 'shadow/paper_channels.errors.jsonl','shadow/factory_events.jsonl',
 'signals.json','strategy_state.json','pump_fade_signals.ndjson','pump_fade_S.json',
 'research_config_extract.json','egress_events.jsonl','decision_events.jsonl','http_timing.jsonl',
 'exchange_positions.json','exchange_executions.json','exchange_closed_pnl.json',
 'exchange_order_history.json','exchange_open_orders.json','initial_protection_events.jsonl',
 'manager_events.jsonl','source_recipe_manifest.json','clock_offsets.json','report_full.txt')
MAX_DEPTH=40

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def fingerprint(path):
    s=path.stat();return (s.st_size,s.st_mtime_ns,s.st_ino)

def forbidden(path):
    return any(DENY_NAME.search(p)for p in path.parts) or path.suffix.lower() in ('.key','.pem','.pfx')

def regular(path):
    path=Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('SYMLINK_INPUT_FORBIDDEN')
    if forbidden(path):raise ValueError('SENSITIVE_INPUT_FORBIDDEN')
    if not path.is_file():raise FileNotFoundError('SOURCE_MISSING')
    return path.resolve()

class Exporter:
    def __init__(self,out,roots,dbs,max_bytes=50_000_000,max_rows=200_000):
        self.out=Path(out).resolve();self.roots=[Path(r).resolve()for r in roots]
        self.dbs=[Path(d).resolve()for d in dbs];self.max_bytes=max_bytes;self.max_rows=max_rows
        for root in self.roots+[p.parent for p in self.dbs]:
            if self.out==root or root in self.out.parents:raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE_TREE')
        if self.out.exists():raise ValueError('OUTPUT_MUST_NOT_EXIST')
        self.out.mkdir(parents=True);self.salt=secrets.token_bytes(32)
        self.manifest={'schema':'CAR_RESEARCH_EXPORT_V1','privacy':'PRIVATE_NOT_FOR_PUBLIC_GITHUB',
          'network_calls':0,'source_SQL_writes':0,'source_files_modified':False,
          'mode':'EXPLICIT_OFFLINE_SNAPSHOTS_ONLY','records':[],
          'identity':'HMAC-SHA256 per bundle, common domain for all IDs; source paths not exported',
          'cash_rule':'raw realized_profit and close_profit_abs separate; no fallback or PnL calculation',
          'R_rule':'initial_stop_loss may be emergency; protective event history required; no derived R',
          'coverage_claim':'selected explicit snapshots only; missing history/fields is not zero',
          'missing_required':['producer decision quote/time and stage events if not historically logged',
           'deployed code and safe config/variant recipes','clock offsets and route/request durations',
           'actual initial financial protective SL and quantity history','settled funding cashflows',
           'BTC/coin price path before entry and after stop; no downloader included']}

    def ident(self,value):
        return 'h_'+hmac.new(self.salt,str(value).encode(),hashlib.sha256).hexdigest()

    def clean(self,value,key='',depth=0):
        if depth>MAX_DEPTH:return '[DEPTH_LIMIT]'
        if SENSITIVE_KEY.search(str(key)):return '[REDACTED_FIELD]'
        if isinstance(value,dict):
            out={}
            for k,v in value.items():
                newkey=self.ident(k)if str(key) in ('signals','consumed','invalid','chase','imported_cum')else str(k)
                out[newkey]=self.clean(v,str(k),depth+1)
            return out
        if isinstance(value,list):
            if IDENTITY_KEY.search(str(key)):return [self.ident(x)for x in value]
            return [self.clean(x,key,depth+1)for x in value]
        if value is None or isinstance(value,bool):return value
        if IDENTITY_KEY.search(str(key)):return self.ident(value)
        if isinstance(value,str):
            if str(key) in ('cd_value','value'):
                try:return self.clean(json.loads(value),'',depth+1)
                except (ValueError,TypeError):pass
            if SENSITIVE_LINE.search(value):return '[REDACTED_SENSITIVE_VALUE]'
            return value
        if isinstance(value,(bytes,bytearray)):
            return self.clean(bytes(value).decode('utf-8',errors='replace'),key,depth+1)
        if isinstance(value,(int,float)):
            if isinstance(value,float) and (value!=value or abs(value)==float('inf')):return None
            return value
        return str(value)

    def db(self,path,label,paper=False):
        record={'kind':'sqlite','label':label,'status':'MISSING','tables':{}}
        self.manifest['records'].append(record)
        try:
            path=regular(path)
            # immutable RO cannot safely see uncheckpointed WAL; do not open live WAL DB.
            for suffix in ('-wal','-journal'):
                side=Path(str(path)+suffix)
                if side.exists()and side.stat().st_size:
                    raise ValueError('CONSISTENT_OFFLINE_SNAPSHOT_REQUIRED_NONEMPTY_'+suffix[1:].upper())
            before=fingerprint(path)
            con=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=2)
            con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
            try:
                tables={r[0]for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                wanted=PAPER_TABLES if paper else BASE_TABLES
                for table in wanted:
                    if table not in tables:
                        record['tables'][table]={'status':'MISSING','rows':None};continue
                    columns=[r[1]for r in con.execute('PRAGMA table_info("'+table+'")')]
                    # No config/credential tables or arbitrary SQL are ever accepted.
                    rows=[];truncated=False
                    for row in con.execute('SELECT * FROM "'+table+'"'):
                        if len(rows)>=self.max_rows:truncated=True;break
                        record_row=dict(zip(columns,row))
                        if table=='trades':
                            record_row['source']=str(record_row.get('enter_tag')or'?').split(':',1)[0]
                        rows.append(self.clean(record_row))
                    dest=f'{label}_{table}.json';dump(self.out/dest,rows)
                    record['tables'][table]={'status':'TRUNCATED'if truncated else'EXPORTED',
                        'rows_exported':len(rows),'columns':columns,'file':dest,
                        'no_cash_semantics_inferred':True}
                record['schema_only_other_table_names']=sorted(tables-set(wanted))
            finally:con.close()
            if fingerprint(path)!=before:raise ValueError('SOURCE_CHANGED_DURING_READ')
            # Never checksum huge/live DB or touch its journal; snapshot identity is metadata only.
            record.update(status='EXPORTED',snapshot_size=before[0],snapshot_mtime_ns=before[1])
        except (OSError,ValueError,sqlite3.Error)as exc:
            for state in record['tables'].values():
                if state.get('file'):
                    (self.out/state['file']).unlink(missing_ok=True)
                    state['status']='INVALID_SOURCE';state.pop('file',None)
            record.update(status='BLOCKED',error=str(exc)if isinstance(exc,ValueError)else type(exc).__name__)

    def artifact(self,path,label):
        rec={'kind':'file','label':label,'status':'MISSING'};self.manifest['records'].append(rec)
        try:
            path=regular(path);before=fingerprint(path)
            if path.stat().st_size>self.max_bytes:raise ValueError('INPUT_COMPRESSED_SIZE_LIMIT')
            compressed=path.read_bytes();rec['source_sha256']=hashlib.sha256(compressed).hexdigest()
            if path.suffix.lower()=='.gz':
                with gzip.GzipFile(fileobj=io.BytesIO(compressed))as fh:raw=fh.read(self.max_bytes+1)
            else:raw=compressed
            if len(raw)>self.max_bytes:raise ValueError('DECOMPRESSED_SIZE_LIMIT')
            text=raw.decode('utf-8-sig');ext=path.with_suffix('').suffix.lower()if path.suffix.lower()=='.gz'else path.suffix.lower()
            truncated=False
            if ext=='.json':result=self.clean(json.loads(text))
            elif ext in ('.ndjson','.jsonl'):
                result=[]
                for line in text.splitlines():
                    if not line.strip():continue
                    if len(result)>=self.max_rows:truncated=True;break
                    try:result.append(self.clean(json.loads(line)))
                    except ValueError:result.append({'status':'MALFORMED_JSON_LINE'})
            elif ext=='.csv':
                result=[]
                for row in csv.DictReader(text.splitlines()):
                    if len(result)>=self.max_rows:truncated=True;break
                    result.append(self.clean(row))
            elif ext in ('.log','.txt'):
                lines=text.splitlines();truncated=len(lines)>self.max_rows
                result=[('[REDACTED_SENSITIVE_LINE]'if SENSITIVE_LINE.search(line)else line)
                        for line in lines[:self.max_rows]]
                rec['logs_may_contain_private_trade_ids']='PRIVATE_BUNDLE_ONLY'
            else:raise ValueError('UNSUPPORTED_INPUT_FORMAT')
            if fingerprint(path)!=before:raise ValueError('SOURCE_CHANGED_DURING_READ')
            dest=label+'.json';dump(self.out/dest,result)
            rec.update(status='TRUNCATED'if truncated else'EXPORTED',file=dest,
                input_bytes=before[0],output_records=len(result)if isinstance(result,list)else None)
        except (OSError,ValueError,UnicodeError,OverflowError)as exc:
            rec.update(status='BLOCKED',error=str(exc)if isinstance(exc,ValueError)and str(exc).isupper()else type(exc).__name__)

    def code_digest(self,path,label):
        rec={'kind':'code_digest_only','label':label,'status':'MISSING'}
        self.manifest['records'].append(rec)
        try:
            path=regular(path)
            if path.suffix.lower()not in ('.py','.ps1','.js'):raise ValueError('CODE_FORMAT_NOT_ALLOWED')
            if path.stat().st_size>self.max_bytes:raise ValueError('CODE_SIZE_LIMIT')
            before=fingerprint(path);raw=path.read_bytes()
            if fingerprint(path)!=before:raise ValueError('SOURCE_CHANGED_DURING_READ')
            rec.update(status='EXPORTED',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),contents_exported=False)
        except (OSError,ValueError)as exc:
            rec.update(status='BLOCKED',error=str(exc)if isinstance(exc,ValueError)else type(exc).__name__)

    def finish(self):
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in self.out.iterdir()if p.is_file()}
        self.manifest['output_sha256']=files
        self.manifest['has_missing_or_blocked']=any(r['status']!='EXPORTED'for r in self.manifest['records'])
        dump(self.out/'MANIFEST.json',self.manifest)
        return self.manifest

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db',type=Path,required=True,help='Consistent offline SQLite snapshot, no nonempty WAL')
    ap.add_argument('--paper-db',type=Path,action='append',default=[])
    ap.add_argument('--snapshot-root',type=Path,action='append',default=[],help='Explicit existing user_data snapshot directory')
    ap.add_argument('--artifact',type=Path,action='append',default=[],help='Explicit existing log/JSON/CSV/1m/manager-history/Bybit cached response; never fetched')
    ap.add_argument('--code-file',type=Path,action='append',default=[],help='Code SHA256 only; no contents copied')
    ap.add_argument('--out',type=Path,required=True,help='New PRIVATE directory outside all source directories')
    ap.add_argument('--max-bytes',type=int,default=50_000_000);ap.add_argument('--max-rows',type=int,default=200_000)
    args=ap.parse_args()
    if not 1<=args.max_bytes<=200_000_000 or not 1<=args.max_rows<=1_000_000:ap.error('bounded limits required')
    inputs=[args.db,*args.paper_db,*args.artifact]
    # Also prohibit output below artifact parents, not just DB/snapshot roots.
    roots=[*args.snapshot_root,*[p.parent for p in args.artifact],*[p.parent for p in args.code_file]]
    ex=Exporter(args.out,roots,[args.db,*args.paper_db],args.max_bytes,args.max_rows)
    ex.db(args.db,'live')
    for n,p in enumerate(args.paper_db):ex.db(p,f'paper{n}',True)
    for n,root in enumerate(args.snapshot_root):
        for rel in CANDIDATES:
            p=root/rel
            if p.exists():ex.artifact(p,f'root{n}_'+rel.replace('/','__').replace('.','_'))
        # Existing rotated feeds/logs only, bounded, no recursive traversal.
        for folder in ('shadow','car_signals'):
            d=root/folder
            if not d.is_dir():continue
            for n2,p in enumerate(sorted(d.iterdir())):
                if n2>=500:break
                if p.is_file()and p.name.endswith('.gz')and p.name.startswith(('pump_fade','decision_events','egress_events','manager_events')):
                    ex.artifact(p,f'root{n}_rotated{folder}_{n2}')
    for n,p in enumerate(args.artifact):ex.artifact(p,f'artifact{n}')
    for n,p in enumerate(args.code_file):ex.code_digest(p,f'code{n}')
    result=ex.finish()
    print(json.dumps({'output':str(ex.out),'records':len(result['records']),
       'missing_or_blocked':result['has_missing_or_blocked'],'privacy':result['privacy'],
       'network_calls':0,'PnL_computed':False},ensure_ascii=False))
if __name__=='__main__':main()
