import unittest,copy
from runner_tail import create,advance
M=300000
def row(t,o=100,h=100.1,l=99,c=100):return[t,o,h,l,c]
class TailTests(unittest.TestCase):
 def test_SL_first(self):
  p=create(100,0,'RUN15');advance(p,[row(0,h=110,l=80)]);self.assertEqual(p['events'][0]['kind'],'SL')
 def test_no_TP_fill(self):
  p=create(100,0,'RUN25');advance(p,[row(0,l=90)]);self.assertEqual(p['events'],[])
 def test_no_trail_before_TP2(self):
  p=create(100,0,'RUN15');advance(p,[row(0),row(M,h=100,l=97.8,c=98)]);self.assertIsNone(p['trail_low']);self.assertAlmostEqual(p['remaining'],.5)
 def test_trail_next_bar(self):
  p=create(100,0,'RUN15');advance(p,[row(0),row(M,h=100,l=93,c=94)]);self.assertEqual(p['status'],'OPEN');self.assertAlmostEqual(p['remaining'],.2)
  advance(p,[row(2*M,o=94,h=96,l=92,c=93)]);self.assertEqual(p['events'][-1]['kind'],'TRAIL');self.assertEqual(p['events'][-1]['time_ms'],3*M)
 def test_TP3_no_longer_closes_20(self):
  p=create(100,0,'RUN35');advance(p,[row(0),row(M,h=100,l=90,c=95)]);self.assertEqual(p['status'],'OPEN');self.assertEqual(p['hit'],2)
 def test_10_after_TP3(self):
  p=create(100,0,'TP3_RUN10');advance(p,[row(0),row(M,h=100,l=90,c=95)]);self.assertAlmostEqual(p['remaining'],.1);self.assertEqual([e['fraction']for e in p['events']],[.5,.3,.1])
 def test_BE_never_loosened(self):
  p=create(100,0,'RUN35');advance(p,[row(0),row(M,h=100,l=95.7,c=96)]);self.assertLessEqual(p['stop'],99.89)
 def test_gap_stop(self):
  p=create(100,0,'RUN25');advance(p,[row(0),row(M,o=110,h=111,l=108,c=110)]);self.assertEqual(p['events'][0]['price'],110)
 def test_gap_rejected(self):
  p=create(100,0,'RUN25')
  with self.assertRaises(ValueError):advance(p,[row(M)])
 def test_incremental_idempotent(self):
  b=[row(0),row(M,h=100,l=90,c=95),row(2*M,o=95,h=100,l=94,c=97)];a=create(100,0,'RUN25');c=create(100,0,'RUN25');advance(a,b)
  for r in b:advance(c,[r]);advance(c,[r])
  self.assertEqual(a,c)
 def test_closed_immutable(self):
  p=create(100,0,'RUN15');advance(p,[row(0,h=110)]);old=copy.deepcopy(p);advance(p,[row(M)]);self.assertEqual(p,old)
 def test_BASE_targets(self):
  p=create(100,0,'BASE');advance(p,[row(0),row(M,h=100,l=90,c=95)]);self.assertEqual(p['status'],'CLOSED');self.assertEqual(len(p['events']),3)
 def test_invalid_numeric(self):
  for v in [0,-1,True,float('nan')]:
   with self.assertRaises(ValueError):create(v,0,'RUN15')
 def test_minute_and_5m(self):
  for step in [60000,M]:
   p=create(100,0,'RUN15',step);advance(p,[row(0),row(step,h=100,l=93,c=94),row(2*step,o=94,h=96,l=92,c=93)]);self.assertEqual(p['exit_ms'],3*step)
if __name__=='__main__':unittest.main()
