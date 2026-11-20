import unittest,copy,math
import ledger_audit as a

def row(key='a',R=1,entry=100,stop=95,start=1,end=2,symbol='X'):
 return dict(key=key,source_status='MATCHED',model_status='TRADE',entry=entry,initial_stop=stop,side='LONG',fill_ms=start,exit_ms=end,source_post21bp_R=R,symbol=symbol)
class LedgerAuditTests(unittest.TestCase):
 def test_incremental_cost_is_not_double_charged(self):
  r=row();self.assertEqual(a.adjust(r,21),1);self.assertAlmostEqual(a.adjust(r,35),1-.0014/.05);self.assertAlmostEqual(a.adjust(r,50),1-.0029/.05)
 def test_geometry_uses_initial_sl_not_fee_or_leverage(self):
  self.assertEqual(a.width(row(entry=100,stop=90)),.1)
  with self.assertRaises(ValueError):a.width(row(stop=100))
  with self.assertRaises(ValueError):a.width(row(stop=101))
 def test_unknown_funding_never_zero_net(self):
  x=a.metric([row()],35);self.assertIsNone(x['true_net_R']);self.assertEqual(x['unknown_funding_closed_n'],1)
 def test_nofill_and_data_gap_not_losses(self):
  r=row();nf=dict(r,model_status='NOFILL');gap=dict(r,source_status='DATA_GAP')
  x=a.metric([r,nf,gap],21);self.assertEqual(x['model_closed_n'],1);self.assertEqual(x['no_fill_n'],1);self.assertEqual(x['all_source_opportunities'],3)
 def test_close_before_same_time_entry_for_concurrency(self):
  x=a.concurrency([row('a',start=1,end=2),row('b',start=2,end=3)]);self.assertEqual(x['peak_open_model_positions'],1);self.assertIsNone(x['actual_remaining_risk_USDT'])
 def test_drawdown_uses_exit_order(self):
  x=a.metric([row('a',R=2,start=0,end=10),row('b',R=-1,start=1,end=2)],21);self.assertEqual(x['close_order_maxDD_R'],1)
 def test_coin_concentration_is_posthoc_diagnostic(self):
  x=a.concentration([row('a',R=3,symbol='X'),row('b',R=-1,symbol='Y')],21,'symbol');self.assertEqual(x['best1_share_of_net'],1.5);self.assertEqual(x['without_best1_R'],-1)
 def test_empty_cluster_not_a_significance_claim(self):
  x=a.bootstrap([],35,'week');self.assertIsNone(x['meanR_q05']);self.assertEqual(x['nonempty_blocks'],0)
if __name__=='__main__':unittest.main()
