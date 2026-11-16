"""Verify copied source identity and explicitly declared portability edits."""
import hashlib,json
from pathlib import Path
rows=json.loads(Path('MIGRATION_INPUT_MANIFEST.json').read_text())
for row in rows:
 actual=hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
 if actual!=row['published_sha256']:raise SystemExit('Migration manifest mismatch: '+row['path'])
 if row.get('classification')=='RESEARCH_PUBLIC_MARKET_COLLECTOR' and actual!=row['original_sha256']:raise SystemExit('Collector changed; protocol identity lost')
print('Migration manifest verified:',len(rows),'source files/immutable input records')
