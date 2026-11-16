import unittest,importlib.util
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parents[1]/'research/pf_equity_switch_20261116/run.py';s=importlib.util.spec_from_file_location('switch',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CausalMemoryTests(unittest.TestCase):
 def fixture(self,n=30):
  return [dict(status='CLOSED',symbol='S',signal_ms=i*10,entry_ms=i*10+1,exit_ms=i*10+5,net_R=1.)for i in range(n)]
 def test_only_already_closed_and_full_window(self):
  a,y,t,e,win=m.layout(self.fixture(),'YEAR_5M');w=m.weights(y,win);self.assertEqual(w[0,9],0);self.assertEqual(w[0,10],1);self.assertEqual(w[1,19],0);self.assertEqual(w[1,20],1);self.assertEqual(w[3,0],.25)
 def test_same_timestamp_not_visible(self):
  rows=self.fixture();rows[9]['exit_ms']=rows[10]['signal_ms'];a,y,t,e,win=m.layout(rows,'YEAR_5M');w=m.weights(y,win);self.assertEqual(w[0,10],0);self.assertEqual(w[0,11],1)
 def test_future_outcomes_do_not_change_earlier_weights(self):
  a,y,t,e,win=m.layout(self.fixture(),'YEAR_5M');w=m.weights(y,win);y[20:]=-100;z=m.weights(y,win);np.testing.assert_equal(w[:,:21],z[:,:21]);self.assertEqual(z[1,21],0)
 def test_unknown_closure_kept_in_memory(self):
  rows=self.fixture();rows[8]['net_R']=None;a,y,t,e,win=m.layout(rows,'YEAR_5M');w=m.weights(y,win);self.assertTrue(np.isnan(w[0,10]));self.assertTrue(np.isnan(w[1,20]));self.assertEqual(w[0,19],1)
 def test_recent_phase_reset(self):
  rows=self.fixture(45)
  for i,r in enumerate(rows):r.update(period='TRAIN'if i<25 else 'H2',packet=dict(observed_ms=r['signal_ms']))
  a,y,t,e,win=m.layout(rows,'RECENT_1M');w=m.weights(y,win);self.assertEqual(w[1,25],0);self.assertEqual(w[3,25],.25)
 def test_quarter_risk_does_not_redefine_R(self):
  r=m.metrics(np.array([1.,-2.]),np.array([.25,.25]),np.ones(2,dtype=bool));self.assertEqual(r['netR'],-.25);self.assertEqual(r['maxDD_R'],.5);self.assertEqual(r['n'],2)
 def test_bh(self):np.testing.assert_allclose(m.bh([.01,.04,.03,.2]),[.04,.05333333333333334,.05333333333333334,.2])
if __name__=='__main__':unittest.main()
