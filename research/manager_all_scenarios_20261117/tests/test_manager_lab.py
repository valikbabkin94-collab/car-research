"""Synthetic unit fixtures only; never historical performance data."""
import unittest,sys,importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P));from engine_v1_1 import simulate,atr_at,MAN
from execute_v1_1 import features,periods,label,edge_tables,symbol_groups,causal_confirmation,closed_before
from vendor.pure_manager import geometry
class ManagerLabTests(unittest.TestCase):
 def quotes(self,n=4500):return np.column_stack([np.arange(n)*60000,np.full(n,100.),np.full(n,100.1),np.full(n,99.9),np.full(n,100.)])
 def entry(self,t=0):return dict(key='0'*64,scenario='TEST',symbol='X',entry_ms=t,entry=100.,side=1,entry_type='MARKET')
 def test_every_symbol_group_consumed_before_next(self):
  rows=[dict(self.entry(),symbol=x,key=str(i))for i,x in enumerate(['B','A','B','C','A'])];groups=list(symbol_groups(rows));self.assertEqual(sum(len(g)for s,g in groups),len(rows));self.assertEqual([s for s,g in groups],['A','B','C']);self.assertEqual([len(g)for s,g in groups],[2,2,1])
 def test_manager_atr_uses_original_publication_snapshot(self):
  q=self.quotes();pub=15*3600000;entry=17*3600000;q[900:1020,2]=102.;r=simulate(q,dict(self.entry(entry),signal_ms=pub),'X1');self.assertAlmostEqual(r['atr'],.2)
 def test_future_filled_confirmation_cannot_confirm_past_entry(self):
  e=dict(self.entry(10*3600000),lineage='A');b=dict(e,scenario='B',lineage='B',signal_ms=9*3600000,entry_ms=11*3600000);self.assertFalse(causal_confirmation(e,b));b['entry_ms']=9*3600000;self.assertTrue(causal_confirmation(e,b))
 def test_explicit_grid_limit_gets_maker_entry_fee(self):
  r=simulate(self.quotes(),dict(self.entry(),entry_type='GRID_MEAN_LIMIT_PROXY'),'X6');self.assertAlmostEqual(r['price_R'],-.125)
 def test_frozen_cutoff_discards_partial_and_future_candles(self):
  self.assertEqual(len(closed_before(self.quotes(10),5*60000)),5)
 def test_time_exit_preserves_entry_and_fees(self):
  r=simulate(self.quotes(),self.entry(),'X6');self.assertEqual(r['status'],'CLOSED');self.assertEqual(r['entry'],100.);self.assertEqual(r['exit_ms'],4*3600000);self.assertAlmostEqual(r['price_R'],-.21)
 def test_stop_before_tp_on_ambiguous_bar(self):
  q=self.quotes();q[1,2:4]=[102.,98.];r=simulate(q,self.entry(),'X3');self.assertEqual(r['ambiguous_sl_tp_bars'],1);self.assertEqual(r['events'][0]['kind'],'SL_OR_TRAIL')
 def test_no_tp_entry_bar(self):
  q=self.quotes();q[0,2]=102.;r=simulate(q,self.entry(),'X3');self.assertNotEqual(r['events'][0]['kind'],'TP1')
 def test_cannot_reprice_unreachable_frozen_entry(self):
  r=simulate(self.quotes(),dict(self.entry(),entry=101.),'X3');self.assertEqual(r['status'],'DATA_GAP');self.assertEqual(r['entry'],101.)
 def test_actual_live_manager_be_is_entry_not_fee_offset(self):
  t=SimpleNamespace(is_short=False,open_rate=100.,nr_of_successful_exits=1);self.assertEqual(MAN._desired_stop(t,{'stop':98.})[0],100.)
 def test_closed_hour_atr_and_geometry(self):
  q=self.quotes();t=16*3600000;atr=atr_at(q,t);self.assertAlmostEqual(atr,.2);self.assertEqual(len(geometry(atr,100.,1)[2]),3);q[960:,2]=150.;self.assertAlmostEqual(atr_at(q,t),atr)
 def test_window_extrema_and_forward_returns(self):
  q=self.quotes();q[59,2]=105.;q[60,1]=101.;q[60,2]=110.;r,m,a=features(q,np.array([0]),np.array([100.]),1);self.assertAlmostEqual(r[0,0],.01);self.assertAlmostEqual(m[0,0],5.);self.assertAlmostEqual(a[0,0],.1)
 def test_missing_middle_candle_invalidates_window(self):
  q=np.delete(self.quotes(),30,axis=0);r,m,a=features(q,np.array([0]),np.array([100.]),1);self.assertTrue(np.isnan(r[0,0]))
 def test_train_purge_seventy_two_hours(self):
  es=[self.entry(0),self.entry(100*3600000)];sp=periods(es);self.assertEqual(label(es[0],sp),'PURGED_H1_BOUNDARY');self.assertEqual(label(es[1],sp),'H2')
if __name__=='__main__':unittest.main()
