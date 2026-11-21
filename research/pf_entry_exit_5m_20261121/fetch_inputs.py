"""Fetch pinned existing GitHub blobs only; requires authorized gh. No exchange access."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def check(p,r):
 if not p.exists()or p.stat().st_size!=r['bytes']:return False
 b=p.read_bytes()
 return hashlib.sha256(b).hexdigest()==r['sha256']and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 for r in json.loads(Path(__file__).with_name('CORE_INPUTS.json').read_text()):
  target=a.out/r['file']
  if check(target,r):print(r['file'],'verified existing; skipped');continue
  if target.exists():raise RuntimeError('Existing input hash mismatch; refusing overwrite: '+str(target))
  tmp=target.with_suffix(target.suffix+'.partial')
  if tmp.exists():raise RuntimeError('Unfinished download exists: '+str(tmp))
  with tmp.open('wb')as f:
   subprocess.run(['gh','api','repos/valikbabkin94-collab/'+r['repository']+'/git/blobs/'+r['git_blob'],'-H','Accept: application/vnd.github.raw'],stdout=f,check=True)
  if not check(tmp,r):raise RuntimeError('Downloaded GitHub bytes/hash mismatch: '+str(tmp))
  tmp.replace(target);print(r['file'],'verified')
if __name__=='__main__':main()
