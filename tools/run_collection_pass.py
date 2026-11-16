"""Invoke unchanged collector, preserve expected time checkpoints as resumable."""
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--shard',type=int,required=True);a=p.parse_args();root=Path(f'm15-{a.shard}');root.mkdir(exist_ok=True);checkpoint=root/'CHECKPOINT.json'
if checkpoint.exists() and json.loads(checkpoint.read_text()).get('status')=='PRIORITY1_PRICES_COMPLETE':
 print('Completed shard reused; no source requests');raise SystemExit(0)
lab='research/web_ideas_20261114/unblock_20261114/resume_503';r=subprocess.run([sys.executable,lab+'/collect_priority1.py','--catalog-root','inputs/metadata','--out',str(root),'--symbol-file',f'inputs/pit/shard{a.shard}.json','--interval','15m','--daily-tail','--deadline-seconds','14400'])
if not checkpoint.exists():raise SystemExit(r.returncode or 1)
d=json.loads(checkpoint.read_text());print('Collector checkpoint:',d['status'],d['counts'])
# No PnL is allowed until final verification. Any pause remains explicit, not absent data.
if d['status']=='PAUSED':print('Checkpoint preserved; next bounded pass will resume')
elif d['status']!='PRIORITY1_PRICES_COMPLETE':raise SystemExit(1)
