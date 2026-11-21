"""Manual import of a GitHub-exported signal batch into a NEW research journal.
No network or service; never opens a source database or edits the source batch.
"""
import argparse,hashlib,json
from pathlib import Path
from replay import validate_signal
FIELDS=('id','symbol','model_sha','signal_ms','first_received_ms','reference_price','ml_passed','filter_keep')
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def ingest(rows,registration,source):
 out=[];seen={};prev='0'*64
 for raw in rows:
  s={k:raw.get(k)for k in FIELDS};validate_signal(s)
  if s['id']in seen:
   if seen[s['id']]!=s:raise ValueError('conflicting duplicate signal id')
   continue
  seen[s['id']]=s
  old=min(s['signal_ms'],s['first_received_ms'])<=registration['registration_ms']
  label='EXPOSED_NOT_OOS'if old else'FORWARD_MODEL_NOT_PINNED'if not registration.get('model_snapshot_verified')else'FORWARD_MODEL_MISMATCH'if s['model_sha']!=registration.get('model_sha256')else'FORWARD_DECLARED_RECEIPT_NOT_INDEPENDENTLY_VERIFIED'
  r={'sequence':len(out),'signal':s,'cohort':label,'source':source,'previous_sha256':prev}
  prev=hashlib.sha256(canonical(r)).hexdigest();r['sha256']=prev;out.append(r)
 return out

def verify(rows):
 prev='0'*64
 for i,row in enumerate(rows):
  r=dict(row);digest=r.pop('sha256')
  if r['sequence']!=i or r['previous_sha256']!=prev or hashlib.sha256(canonical(r)).hexdigest()!=digest:raise ValueError('journal hash chain invalid')
  prev=digest
 return prev

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-repo',required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--source-path',required=True);a=ap.parse_args()
 if a.out.exists():raise ValueError('refusing overwrite; each batch creates a NEW journal')
 source={'repository':a.source_repo,'commit':a.source_commit,'path':a.source_path,'batch_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'provenance':'declared GitHub source; verify externally'}
 registration=json.loads(Path(__file__).with_name('REGISTRATION.json').read_text());rows=[json.loads(s)for s in a.input.read_text().splitlines()if s.strip()]
 out=ingest(rows,registration,source);verify(out)
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('x')as f:
  for r in out:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
 print(json.dumps({'imported':len(out),'cohorts':dict(__import__('collections').Counter(r['cohort']for r in out)),'no_live_changes':True}))
if __name__=='__main__':main()
