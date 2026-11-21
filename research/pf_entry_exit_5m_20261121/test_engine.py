import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import numpy as np
from engine import replay,costs,funding_result,M,H

def fixture():
 t=np.arange(-M,81*H+M,M,dtype=float);a=np.column_stack([t,np.full(len(t),100.),np.full(len(t),100.1),np.full(len(t),99.9),np.full(len(t),100.)])
 p={'id':'unit','symbol':'UNIT','signal_ms':0,'C':100.,'split':'TRAIN','regime':'SIDEWAYS','archive_selected_exposed':False,'symbol_type':'test_only','coverage_status':'COMPLETE_80H'}
 return p,a
class FinancialEngineTests(unittest.TestCase):
 def test_stop_first_when_both_targets_and_stop_touch(self):
  p,a=fixture();a[3]=[2*M,100,107,95,100];r=replay(p,a,'MARKET_NEXT_OPEN','E0')
  self.assertEqual(r['events'][0]['kind'],'SL');self.assertAlmostEqual(r['gross_return'],-.056);self.assertEqual(r['SL_TP_same_bar'],1)
 def test_gap_stop_worse_than_one_R(self):
  p,a=fixture();a[3]=[2*M,108,109,107,108];r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertAlmostEqual(r['gross_return'],-.08)
 def test_no_profitable_fill_bar_take(self):
  p,a=fixture();a[2]=[M,100,100.1,97,100];r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertTrue(r['fill_bar_TP_banned']);self.assertEqual(r['events'][-1]['kind'],'TIME');self.assertAlmostEqual(r['gross_return'],0)
 def test_fractional_tp_and_next_bar_BE(self):
  p,a=fixture();a[3]=[2*M,100,100.1,97.5,98];r=replay(p,a,'MARKET_NEXT_OPEN','E0')
  self.assertEqual([x['kind']for x in r['events']],['TP1','BE']);self.assertAlmostEqual(sum(x['fraction']for x in r['events']),1)
 def test_three_partial_targets_total_reward(self):
  p,a=fixture();a[3]=[2*M,99,99.1,93,94];r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertEqual([x['kind']for x in r['events']],['TP1','TP2','TP3']);self.assertAlmostEqual(r['gross_return'],.021*.5+.042*.3+.063*.2)
 def test_far_targets_use_R_not_percent(self):
  p,a=fixture();a[3]=[2*M,99,99.1,77,78];r=replay(p,a,'MARKET_NEXT_OPEN','E2');self.assertAlmostEqual(r['gross_return']/.056,.5+2*.3+4*.2)
 def test_resting_nonfill_kept(self):
  p,a=fixture();r=replay(p,a,'RESTING_PLUS_1_3','E0');self.assertEqual(r['status'],'NOFILL')
 def test_actual_limit_touch_fill(self):
  p,a=fixture();a[3,2]=101.4;r=replay(p,a,'RESTING_PLUS_1_3','E0');self.assertAlmostEqual(r['entry'],101.3)
 def test_tp1_before_limit_known_at_decision_rejected(self):
  p,a=fixture();a[2]=[M,98,98.1,97.9,98];r=replay(p,a,'RESTING_PLUS_1_3','E0');self.assertEqual(r['status'],'PRICE_ALREADY_AT_TP1')
 def test_stop_before_limit_known_at_decision_rejected(self):
  p,a=fixture();a[2]=[M,108,108.1,107.9,108];r=replay(p,a,'RESTING_PLUS_1_3','E0');self.assertEqual(r['status'],'PRICE_ALREADY_AT_STOP')
 def test_live_proxy_checks_previous_close_and_clamped_rate(self):
  p,a=fixture();a[2,2]=101.25;r=replay(p,a,'LIVE_GATES_REPRICE_5M_PROXY','E0');self.assertAlmostEqual(r['entry'],100*1.013*.999)
 def test_market_can_have_original_take_passed_but_no_instant_TP(self):
  p,a=fixture();a[2:]=np.column_stack([a[2:,0],np.full(len(a)-2,98.),np.full(len(a)-2,98.1),np.full(len(a)-2,97.9),np.full(len(a)-2,98.)]);r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertTrue(r['original_TP1_already_passed_at_entry']);self.assertEqual(r['events'][-1]['kind'],'TIME')
 def test_hybrid_fixed_timeout(self):
  p,a=fixture();r=replay(p,a,'HYBRID_1H_1PCT','E0');self.assertEqual(r['entry_ms'],H);self.assertEqual(r['fill_kind'],'HYBRID_MARKET')
 def test_hybrid_distance_reject_not_parameter_search(self):
  p,a=fixture();k=np.searchsorted(a[:,0],H);a[k]=[H,101.5,102,101.4,101.5];r=replay(p,a,'HYBRID_1H_1PCT','E0');self.assertEqual(r['status'],'HYBRID_DISTANCE_REJECT')
 def test_missing_prices_not_zero_return(self):
  p,a=fixture();p['coverage_status']='DATA_GAP_5M';r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertNotIn('gross_return',r);self.assertIsNone(costs(r,.0021))
 def test_purged_training_outcomes_not_read(self):
  p,a=fixture();p['split']='TRAIN_PURGED';self.assertEqual(replay(p,a,'MARKET_NEXT_OPEN','E0')['status'],'TRAIN_PURGED_80H')
 def test_cost_views_use_geometric_same_denominator(self):
  p,a=fixture();r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertAlmostEqual(costs(r,.004)-costs(r,.0021),-.0019/.056)
 def test_unknown_funding_not_zero(self):
  p,a=fixture();r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertIsNone(funding_result(r,a,{})[0])
 def test_funding_gap_and_bracket_required(self):
  p,a=fixture();r=replay(p,a,'MARKET_NEXT_OPEN','E0');self.assertIsNone(funding_result(r,a,{'UNIT':[[0,.01],[20*H,.01],[80*H,.01]]})[0])
 def test_funding_zero_actual_rates_valid(self):
  p,a=fixture();r=replay(p,a,'MARKET_NEXT_OPEN','E0');f={'UNIT':[[x*H,0]for x in range(0,89,8)]};self.assertEqual(funding_result(r,a,f)[0],0)
 def test_trailing_has_partial_then_price_exit(self):
  p,a=fixture();a[3]=[2*M,99,99.1,97,98];r=replay(p,a,'MARKET_NEXT_OPEN','E5');self.assertEqual(r['events'][0]['fraction'],.5);self.assertEqual(sum(x['fraction']for x in r['events']),1)
if __name__=='__main__':unittest.main()
