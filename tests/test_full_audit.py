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

class FundingZeroTests(unittest.TestCase):
 def test_unknown_funding_zero_is_included_with_stress(self):
  from full_run import run_case,metrics
  class Q:
   def load(self,sym):return np.array([[M,100,101,93,94]],float)
  class F:
   def cash(self,*args):return None
  class B:
   def get(self,*args):raise AssertionError('No fallback needed')
  s=dict(channel='c',post_key='k',symbol='XUSDT',pub=0,side='LONG');r=run_case(s,'T3',Q(),B(),F());self.assertEqual(r['funding_R'],0);self.assertEqual(r['funding_status'],'ASSUMED_ZERO_UNKNOWN');self.assertEqual(metrics([r])['n'],1);self.assertLess(r['net_R_funding_adverse'],r['net_R']);self.assertGreater(r['net_R_funding_favourable'],r['net_R'])
 def test_public_fallback_has_no_credentials_or_private_route(self):
  from full_run import PublicBybit
  from unittest.mock import patch
  import json
  seen=[]
  class R:
   url='https://api.bybit.com/v5/market/kline'
   def __enter__(self):return self
   def __exit__(self,*args):return False
   def read(self,*args):return json.dumps(dict(retCode=0,result=dict(list=[]))).encode()
  def opener(req,**kwargs):seen.append(req);return R()
  with patch('urllib.request.urlopen',opener):PublicBybit().get('BTCUSDT',0,M)
  self.assertTrue(seen[0].full_url.startswith('https://api.bybit.com/v5/market/kline?'));self.assertIn('category=linear',seen[0].full_url);self.assertFalse(any('key'in k.lower()or'auth'in k.lower()for k,v in seen[0].header_items()))
