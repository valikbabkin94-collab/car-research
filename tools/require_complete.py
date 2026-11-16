"""Fail closed before PnL on incomplete source or observed reference mismatch."""
import json
from pathlib import Path
for shard in [0,1]:
 d=json.loads(Path(f'parity/DATA_PARITY_{shard}.json').read_text())
 if not d['complete'] or d['errors'] or d['status']=='DATA_MISMATCH':raise SystemExit('DATA_PENDING_OR_MISMATCH: research results not started')
print('Known frozen references match; full old per-file reference unavailable, caveat retained')
