import unittest
import numpy as np
from lab.engine import simulate,path_first,M,H
from lab.common import resolve_entry,bh
class EngineTests(unittest.TestCase):
 def bars(self,n=10):
  return np.array([[i*M,100,100.1,99.9,100]for i in range(n)],float)
 def plan(self):return np.array([.01,.015,0,0,1,0,0,0,0,0,-1,1,0,1,0,0],float)
 def runp(self,q,p=None,side=1):return simulate(q,0,100,side,self.plan()if p is None else p,np.array([],float),np.array([],float),np.empty((0,2)))
 def test_same_bar_sl_first(self):
  q=self.bars();q[1,2:4]=[103,98];r=self.runp(q);self.assertEqual(r[8],1);self.assertEqual(r[34],1);self.assertLess(r[1],-1)
 def test_no_tp_in_entry_bar(self):
  q=self.bars();q[0,2]=103;self.assertEqual(self.runp(q)[0],0)
 def test_tp_next_bar(self):
  q=self.bars();q[1,2]=102;r=self.runp(q);self.assertEqual(r[8],2);self.assertAlmostEqual(r[1],1.5-(.00105+.0002*1.015)/.01)
 def test_short_symmetry(self):
  q=self.bars();q[1,3]=98;self.assertEqual(self.runp(q,side=-1)[8],2)
 def test_gap_not_closed(self):
  q=self.bars();q[1:,0]+=M;self.assertEqual(self.runp(q)[0],-3)
 def test_price_unavailable(self):
  q=self.bars();q[0,3]=100.01;self.assertEqual(self.runp(q)[0],-2)
 def test_censor_not_forced_profit(self):self.assertEqual(self.runp(self.bars())[0],0)
 def test_time_exit(self):
  p=self.plan();p[11]=2/60;r=self.runp(self.bars(),p);self.assertEqual(r[8],4);self.assertEqual(r[7],2*M)
 def test_partial_and_be_next_bar(self):
  p=self.plan();p[1:4]=[.01,.02,.03];p[4:7]=[.5,.25,.25];p[7]=1;q=self.bars();q[1,2]=101.1;r=self.runp(q,p);self.assertEqual(r[8],3);self.assertEqual(r[12],2);self.assertAlmostEqual(r[15]+r[19],1)
 def test_funding_stress(self):
  q=self.bars();q[1,2]=102;r=self.runp(q);self.assertEqual(r[5],0);self.assertGreater(r[6],0)
 def test_5m_price_window(self):
  q=self.bars();q[4,2]=102;e=dict(entry_ms=0,entry=101,entry_window_ms=5*M);self.assertEqual(resolve_entry(q,e),4*M);e['entry_window_ms']=M;self.assertIsNone(resolve_entry(q,e))
 def test_path_adverse_first(self):
  q=self.bars();q[1,2:4]=[103,98];self.assertEqual(path_first(q,0,100,1,.01),0)
 def test_bh(self):self.assertEqual(bh([.01,.04,1.]),[.03,.06,1.])
if __name__=='__main__':unittest.main()
