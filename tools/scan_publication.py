"""Fail closed on forbidden paths and credential/address values before publishing.
Scans all tracked and untracked publishable files, decompresses gzip and ZIP/NPZ.
Never prints matched values, only path and finding category.
"""
import argparse,gzip,io,json,re,subprocess,sys,zipfile
from pathlib import Path

RULES={
 'telegram_credential':re.compile(rb'\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}\b'),
 'github_credential':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
 'aws_credential':re.compile(rb'\bAKIA[A-Z0-9]{16}\b'),
 'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'secret_assignment':re.compile(rb'''(?i)(?:api[_-]?key|api[_-]?secret|secret[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|bot[_-]?token|token|chat[_-]?id|password)["']?\s*[=:]\s*["']?[A-Za-z0-9:_-]{6,}'''),
 'address_literal':re.compile(rb'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
}
BANNED=re.compile(r'(^|/)(fastpath|strategies|windows|acer_runtime|owner_[^/]*)(/|$)|(^|/)\.env(?:\.|$)')

def inspect(path,raw,depth=0):
 if depth>4:raise ValueError('Archive recursion limit')
 findings=[]
 for name,rule in RULES.items():
  if name=='address_literal':
   if any(all(int(v)<=255 for v in m.group().split(b'.'))for m in rule.finditer(raw)):findings.append({'path':path,'rule':name})
  elif rule.search(raw):findings.append({'path':path,'rule':name})
 if raw.startswith(b'\x1f\x8b'):findings+=inspect(path+'!gzip',gzip.decompress(raw),depth+1)
 elif raw.startswith(b'PK\x03\x04'):
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   for info in z.infolist():
    if info.is_dir():continue
    if info.file_size>128*1024*1024:raise ValueError('Unreviewed oversized archive member')
    if BANNED.search(info.filename):findings.append({'path':path+'!'+info.filename,'rule':'forbidden_path'})
    findings+=inspect(path+'!'+info.filename,z.read(info),depth+1)
 return findings

def main():
 p=argparse.ArgumentParser();p.add_argument('--out');a=p.parse_args();root=Path.cwd();names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0');findings=[];scanned=[]
 for name in sorted(set(filter(None,names))):
  path=root/name
  if not path.is_file():continue
  if path.is_symlink():findings.append({'path':name,'rule':'symlink_requires_manual_review'});continue
  if BANNED.search(name):findings.append({'path':name,'rule':'forbidden_path'})
  try:findings+=inspect(name,path.read_bytes());scanned.append(name)
  except Exception as exc:findings.append({'path':name,'rule':'scan_error_'+type(exc).__name__})
 report={'status':'PASS' if not findings else 'BLOCK_PUSH','files_scanned':len(scanned),'findings':findings,'scope':'all publishable files; recursive gzip/zip/npz; no matched values printed'}
 if a.out:Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));sys.exit(1 if findings else 0)
if __name__=='__main__':main()
