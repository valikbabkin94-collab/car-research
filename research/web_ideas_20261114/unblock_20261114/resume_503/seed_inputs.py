"""Reuse verified source inputs; no network."""
import argparse,json,hashlib,zipfile,io,shutil
from pathlib import Path
import numpy as np,pandas as pd
p=argparse.ArgumentParser();p.add_argument('--saved');p.add_argument('--metadata');p.add_argument('--symbols');p.add_argument('--out');p.add_argument('--interval',default='1h');a=p.parse_args()
if a.saved:
 saved=Path(a.saved);meta=Path(a.metadata);shutil.copytree(saved/'verified_hourly_seed',meta/'seed_1h',dirs_exist_ok=True);target=meta/'seed_15m';target.mkdir(exist_ok=True)
 raw=(saved/'source_checks/btc_202610.zip').read_bytes();h=hashlib.sha256(raw).hexdigest();assert h=='4c146566bbff66b73f4058120be7d2188d7cef4d2fd7c0deab8308233de80b85';z=zipfile.ZipFile(io.BytesIO(raw));d=pd.read_csv(z.open(z.namelist()[0]));dest=target/'BTCUSDT-15m-2026-10.npz';np.savez_compressed(dest,ts=d.open_time.to_numpy(dtype='int64'),open=d.open.to_numpy(),high=d.high.to_numpy(),low=d.low.to_numpy(),close=d.close.to_numpy(),volume=d.volume.to_numpy(),quote_volume=d.quote_volume.to_numpy());dest.with_suffix('.json').write_text(json.dumps({'key':'data/futures/um/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-2026-10.zip','checksum_verified':True,'source_sha256':h,'parsed_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'rows':len(d),'reused_existing_verified_source':True},indent=2))
else:
 symbols=set(json.loads(Path(a.symbols).read_text()));out=Path(a.out);out.mkdir(exist_ok=True,parents=True)
 for f in (Path(a.metadata)/('seed_'+a.interval)).glob('*.npz'):
  symbol=f.name.split('-'+a.interval+'-')[0]
  if symbol in symbols:
   for p in [f,f.with_suffix('.json')]:
    if not (out/p.name).exists():shutil.copy(p,out/p.name)
