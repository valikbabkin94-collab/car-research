"""One official archive proves public network and known old source SHA only.
Not a strategy experiment and not a replacement for the full source comparison.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('research/web_ideas_20261114/unblock_20261114/resume_503').resolve()))
from collect_priority1 import archive
from resilient_http import Client
out=Path('work/smoke');out.mkdir(parents=True,exist_ok=True);key='data/futures/um/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-2026-10.zip';archive(Client(out/'HTTP_LOG.jsonl'),key,out);receipt=json.loads((out/'BTCUSDT-15m-2026-10.json').read_text());expected=json.loads(Path('reference/M15_SOURCE_REFERENCE.json').read_text())['same_official_archive_anchor']['BTCUSDT-15m-2026-10'];assert receipt['checksum_verified'] and receipt['source_sha256']==expected;assert receipt['rows']==31*24*4
print(json.dumps({'status':'KNOWN_SOURCE_SHA_MATCH','rows':receipt['rows'],'source_sha256':receipt['source_sha256'],'bar_gaps':receipt['bar_gaps'],'scope':'one old source anchor, not full old dataset parity'},indent=2))
