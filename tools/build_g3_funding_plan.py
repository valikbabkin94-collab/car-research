"""Address funding only for real original15m opportunities, no parameter selection."""
import argparse,gzip,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--opportunities',required=True);p.add_argument('--out',required=True);a=p.parse_args();symbols={}
for r in (json.loads(x) for x in gzip.open(a.opportunities,'rt')):
 if r['technical_executable'] and r['variant'] in ['NO_QUALITY','NO_MEME']:
  symbols.setdefault(r['symbol'],set()).add((r['entry_open_ms'],r['entry_open_ms']+48*3600000,'ORIGINAL_G3_15M'))
Path(a.out).write_text(json.dumps({'symbols':{s:sorted(v) for s,v in sorted(symbols.items())},'kind':'OPPORTUNITY_WINDOWS_NOT_PNL_SELECTION'},indent=2)+'\n');print('Required original G3 funding symbols',len(symbols))
