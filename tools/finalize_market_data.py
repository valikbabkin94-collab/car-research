"""Source/bar manifests and explicit old-reference parity gate. No PnL."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--shard',type=int,required=True);a=p.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);reference=json.loads(Path('reference/M15_SOURCE_REFERENCE.json').read_text());checkpoint=json.loads((root/'CHECKPOINT.json').read_text());expected=set(json.loads(Path(f'inputs/pit/shard{a.shard}.json').read_text()));rows=[];symbols=set();errors=[]
 for file in sorted(root.glob('*.npz')):
  receipt=json.loads(file.with_suffix('.json').read_text());payload=file.read_bytes();sym=file.name.split('-15m-')[0]
  if sym not in expected:errors.append({'file':file.name,'reason':'OUTSIDE_FROZEN_UNIVERSE'})
  if not receipt.get('checksum_verified') or hashlib.sha256(payload).hexdigest()!=receipt['parsed_sha256']:raise ValueError('Unverified NPZ '+file.name)
  with np.load(file) as z:
   if set(z.files)!={'ts','open','high','low','close','volume','quote_volume'}:raise ValueError('Unexpected array schema')
   ts=z['ts'];canonical=hashlib.sha256()
   for name in sorted(z.files):
    v=z[name];canonical.update(name.encode());canonical.update(str(v.dtype).encode());canonical.update(v.tobytes())
   record={'file':file.name,'rows':len(ts),'first_open_ms':int(ts[0]),'last_open_ms':int(ts[-1]),'source_sha256':receipt['source_sha256'],'parsed_sha256':receipt['parsed_sha256'],'canonical_bar_sha256':canonical.hexdigest(),'bar_gaps':int((np.diff(ts)!=900000).sum())}
  rows.append(record);symbols.add(sym)
  anchor=reference['same_official_archive_anchor'].get(file.stem)
  if anchor and anchor!=receipt['source_sha256']:errors.append({'file':file.name,'reason':'SOURCE_SHA_MISMATCH_KNOWN_ANCHOR'})
 complete=checkpoint['status']=='PRIORITY1_PRICES_COMPLETE' and checkpoint['gaps']==[]
 if complete and set(symbols)!=expected:errors.append({'reason':'SYMBOL_SET_MISMATCH'})
 if complete and len(rows)!=reference['archives_per_shard'][a.shard]:errors.append({'reason':'ARCHIVE_COUNT_MISMATCH','expected':reference['archives_per_shard'][a.shard],'actual':len(rows)})
 report={'status':'DATA_MISMATCH' if errors else 'KNOWN_REFERENCE_MATCH_FULL_REFERENCE_INCOMPLETE' if complete else 'DATA_PENDING_CHECKPOINT','shard':a.shard,'symbols':len(symbols),'expected_symbols':len(expected),'archives':len(rows),'bar_rows':sum(x['rows'] for x in rows),'source_checksum_all_verified':True,'complete':complete,'full_old_per_file_sha_and_bar_count_comparison':'UNAVAILABLE_REFERENCE_NOT_EXPORTED','errors':errors}
 (out/f'DATA_PARITY_{a.shard}.json').write_text(json.dumps(report,indent=2)+'\n');(out/f'FINAL_DATA_MANIFEST_{a.shard}.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(report,indent=2))
 if errors:raise SystemExit(2)
if __name__=='__main__':main()
