"""Synthetic execution fixtures, never used as research market history."""
import unittest,sys,importlib.util
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'research/pf_execution_common_20261116'))
from engine import simulate
from market import Funding,M,H
class M1ExecutionTests(unittest.TestCase):
 def test_stop_first_and_no_tp_in_entry_minute(self):
  p=dict(symbol='ABCUSDT',signal_ms=0,observed_ms=0,limit=100,side=-1)
  q=np.array([[M,100,107,90,100],[2*M,100,101,99,100]],float);r=simulate(q,p,3*M);self.assertEqual(r['events'][0]['kind'],'SL')
  q[0]=[M,100,101,93,99];q[1]=[2*M,100,107,99,101];r=simulate(q,p,3*M);self.assertEqual(r['events'][0]['kind'],'SL')
 def test_gap_never_becomes_no_fill(self):
  p=dict(symbol='ABCUSDT',signal_ms=0,observed_ms=0,limit=110,side=-1)
  q=np.array([[2*M,100,101,99,100]],float);self.assertEqual(simulate(q,p,3*M)['status'],'DATA_GAP_M1')
 def test_partials_be_fee_and_cash_costs(self):
  p=dict(symbol='ABCUSDT',signal_ms=0,observed_ms=0,limit=100,side=-1)
  q=np.array([[M,100,101,99,100],[2*M,99,100,95,97],[3*M,99.8,100,99.7,99.9]],float);r=simulate(q,p,4*M)
  self.assertEqual([x['kind'] for x in r['events']],['TP1','TP2','BE']);self.assertAlmostEqual(r['events'][-1]['price'],99.89);self.assertGreater(r['price_R'],0)
 def test_next_minute_trailing_and_invalid_geometry(self):
  p=dict(symbol='ABCUSDT',signal_ms=0,observed_ms=0,entry_type='MARKET',side=1,stop_fraction=.04,tp_dist=[],weights=[],move_be=False,trail_after_profit=.04,trail_fraction=.04)
  q=np.array([[M,100,106,99,105],[2*M,103,104,100,101]],float);r=simulate(q,p,3*M);self.assertEqual(r['events'][0]['bar_ms'],2*M);self.assertEqual(r['events'][0]['kind'],'TRAIL')
  p['absolute_stop']=110;r=simulate(q,p,3*M);self.assertEqual(r['status'],'REJECTED_INVALID_STOP')
 def test_mirror_same_initial_fee_mode(self):
  p=dict(symbol='ABCUSDT',signal_ms=0,observed_ms=0,side=-1,entry_type='LIMIT',limit=100,hold_hours=1)
  q=np.array([[M*i,100,100.01,99.99,100] for i in range(1,63)],float);r=simulate(q,p,63*M);mirror=simulate(q,{**p,'side':1},63*M,(r['entry_ms'],r['entry']),r['risk_fraction']);self.assertAlmostEqual(r['execution_cost_R'],mirror['execution_cost_R'])
class IndicatorCausalityTests(unittest.TestCase):
 def test_future_closes_do_not_change_past_rsi_atr(self):
  path=BASE/'research/pf_rubik_20261116/run.py'
  if not path.exists():self.skipTest('Rubik-only indicator test')
  sp=importlib.util.spec_from_file_location('rubik',path);r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
  q=np.array([[i*H,100+i*.1,101+i*.1,99+i*.1,100+i*.1,1,100] for i in range(80)],float);a,b=r.indicators(q);q[60:,4]*=1.5;c,d=r.indicators(q);np.testing.assert_allclose(a[:60],c[:60],equal_nan=True);np.testing.assert_allclose(b[:60],d[:60],equal_nan=True)
if __name__=='__main__':unittest.main()
