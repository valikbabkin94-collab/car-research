"""Offline unit fixtures, not generated market history or profitability evidence."""
import contextlib,gzip,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];LAB=ROOT/'research/round4_20261115/C/continuation_20261116';sys.path.insert(0,str(LAB))
from execution_guard import long_quantity

class ResearchTests(unittest.TestCase):
 def test_invalid_entry_rejected(self):
  for entry,stop in [(94.,95.),(95.,95.),(float('nan'),95.)]:
   with self.assertRaises(ValueError):long_quantity(entry,stop,50.)
 def test_frozen_universe(self):
  allset=set(json.loads((ROOT/'inputs/pit/EVER_TOP150.json').read_text()));shards=[set(json.loads((ROOT/f'inputs/pit/shard{i}.json').read_text())) for i in [0,1]]
  self.assertEqual(len(allset),701);self.assertEqual([len(x) for x in shards],[351,350]);self.assertFalse(shards[0]&shards[1]);self.assertEqual(shards[0]|shards[1],allset)
 def test_15m_portfolio_entry_and_next_bar_exits(self):
  spec=importlib.util.spec_from_file_location('g3_engine_fixture',LAB/'replay_g3h.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);step=900000;m.START=0;m.DIAG_END=4*step
  frame=pd.DataFrame({'open':[100.]*4,'high':[120.,116.,101.,101.],'low':[99.,100.,99.,99.],'close':[100.]*4,'volume':[1.]*4,'quote_volume':[100.]*4},index=np.arange(4)*step);m.load=lambda *args:(frame,[])
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'fund/symbols').mkdir(parents=True);(root/'fund/symbols/TESTUSDT.json.gz').write_bytes(gzip.compress(json.dumps({'rows':[],'coverage':[[0,10*step]]}).encode()));source=root/'opportunities.jsonl.gz'
   with gzip.open(source,'wt') as f:f.write(json.dumps({'symbol':'TESTUSDT','variant':'NO_QUALITY','decision_ms':0,'entry_open_ms':0,'technical_executable':True,'stop':95.,'tp3':115.})+'\n')
   original=sys.argv
   try:
    sys.argv=['replay','--hourly','unused','--funding',str(root/'fund'),'--out',str(root/'out'),'--interval','15m','--opportunities',str(source)]
    with contextlib.redirect_stdout(io.StringIO()):m.main()
   finally:sys.argv=original
   trades=[json.loads(x) for x in gzip.open(root/'out/NO_QUALITY_TRADES.jsonl.gz','rt')];self.assertEqual(len(trades),1);events=trades[0]['events'];self.assertEqual([e['kind'] for e in events],['TP1','TP2','TP3']);self.assertTrue(all(e['bar_open_ms']==step for e in events));self.assertEqual(trades[0]['exit_ms'],2*step)
if __name__=='__main__':unittest.main()
