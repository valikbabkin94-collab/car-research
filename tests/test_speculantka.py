import unittest,sys,importlib.util
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parents[1]/'research/text_signals_audit_20261116/speculantka_v1';sp=importlib.util.spec_from_file_location('spec_parser',P/'parser.py');parser=importlib.util.module_from_spec(sp);sp.loader.exec_module(parser);sp=importlib.util.spec_from_file_location('spec_engine',P/'spec_engine.py');engine=importlib.util.module_from_spec(sp);sp.loader.exec_module(engine)
class SpecTests(unittest.TestCase):
 def row(self,t):return dict(text=t)
 def test_unknown_grid_not_invented(self):
  r=parser.parse(self.row('EVAA SHORT набираюсь сеткой'),{'EVAA'});self.assertTrue(r['grid_mentioned']);self.assertIsNone(r['grid'])
 def test_numeric_grid_fixed_midpoint(self):
  r=parser.parse(self.row('EVAA SHORT набор сеткой 1.0–1.4'),{'EVAA'});self.assertEqual(r['grid'],[1.,1.4]);self.assertAlmostEqual(sum(r['grid'])/2,1.2)
 def test_close_roi_not_position_fraction(self):
  r=parser.parse(self.row('SOL закрываю полностью сделку +38.12%'),{'SOL'});self.assertIn({'kind':'CLOSE_ALL'},r['actions']);self.assertFalse(any(e['kind']=='CLOSE_PART'for e in r['actions']))
 def test_future_workout_not_past_trade(self):
  r=parser.parse(self.row('MAGMA SHORT жду быструю отработку'),{'MAGMA'});self.assertEqual(r['label'],'SIGNAL')
 def test_two_sides_are_uncertain(self):
  r=parser.parse(self.row('BTC лонг и шорт в разных ситуациях'),{'BTC'});self.assertIsNone(r['side']);self.assertNotEqual(r['label'],'SIGNAL')
 def test_remove_stop_and_initial_risk_retained(self):
  M=60000;p=dict(symbol='X',signal_ms=0,observed_ms=0,entry_type='MARKET',side=1,author_events=[dict(kind='REMOVE_STOP',effective_ms=M,pub=0,post_key='a'),dict(kind='CLOSE_ALL',effective_ms=3*M,pub=2*M,post_key='b')]);q=np.array([[M,100,101,99,100],[2*M,100,101,90,92],[3*M,92,93,91,92]],float);r=engine.simulate(q,p,4*M);self.assertEqual(r['status'],'CLOSED');self.assertTrue(r['virtual_stop_removed']);self.assertEqual(r['initial_stop'],94.39999999999999);self.assertLess(r['price_R'],-1)
 def test_dca_without_qty_not_known(self):
  M=60000;p=dict(symbol='X',signal_ms=0,observed_ms=0,entry_type='MARKET',side=1,author_events=[dict(kind='UNRESOLVED_DCA',effective_ms=M,pub=0,post_key='a')]);q=np.array([[M,100,101,99,100],[2*M,100,110,99,106]],float);r=engine.simulate(q,p,3*M);self.assertEqual(r['status'],'UNRESOLVED_AUTHOR_ACTION')
 def test_fixed_midpoint_no_open_improvement(self):
  M=60000;p=dict(symbol='X',signal_ms=0,observed_ms=0,side=-1,entry_type='LIMIT',limit=100,fixed_limit_price=True);q=np.array([[M,101,102,99,100],[2*M,100,107,99,100]],float);r=engine.simulate(q,p,3*M);self.assertEqual(r['entry'],100)
 def test_scanner_rejects_ip_not_large_money(self):
  sp=importlib.util.spec_from_file_location('scan',P.parents[2]/'tools/scan_publication.py');s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s);self.assertTrue(s.inspect('x',b'.'.join([b'10',b'1',b'2',b'3'])));self.assertFalse(s.inspect('x',b'123.456.789.123$'))
if __name__=='__main__':unittest.main()
