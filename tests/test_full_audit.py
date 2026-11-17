import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/text_signals_audit_20261116'))
from full_engine import simulate,M
from full_run import bh,metrics
class FullTests(unittest.TestCase):
 def test_author_close_is_received_not_backdated(self):
  p=dict(symbol='XUSDT',signal_ms=0,observed_ms=0,entry_type='MARKET',side=1,author_events=[dict(kind='CLOSE_ALL',effective_ms=2*M,pub=M+1,post_key='x')]);q=np.array([[M,100,100,100,100],[2*M,101,101,101,101]],float);r=simulate(q,p,3*M);self.assertEqual(r['status'],'CLOSED');self.assertEqual(r['exit_ms'],2*M)
 def test_unknown_fraction_is_not_known_return(self):
  p=dict(symbol='XUSDT',signal_ms=0,observed_ms=0,entry_type='MARKET',side=1,author_events=[dict(kind='UNRESOLVED_FRACTION',effective_ms=M,pub=0,post_key='x')]);q=np.array([[M,100,100,100,100],[2*M,100,110,100,106]],float);r=simulate(q,p,3*M);self.assertEqual(r['status'],'UNRESOLVED_AUTHOR_ACTION')
 def test_empty_data_preserved(self):
  p=dict(symbol='X',signal_ms=0,observed_ms=0);self.assertEqual(simulate(np.empty((0,5)),p,100)['status'],'DATA_GAP_M1')
 def test_bh_missing_equals_one(self):self.assertEqual(bh([1.]*135),[1.]*135)
if __name__=='__main__':unittest.main()
