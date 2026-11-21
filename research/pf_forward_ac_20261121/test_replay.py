"""Synthetic unit fixtures only. These are not research prices or evidence of profitability."""
import copy,json,unittest
from pathlib import Path
from replay import *
P=json.loads(Path(__file__).with_name('FROZEN_PROTOCOL.json').read_text())
def signal():return dict(id='unit',symbol='UNITUSDT',model_sha='unit-model',signal_ms=M,first_received_ms=M,reference_price=100.,ml_passed=True,filter_keep='top50')
def bar(t,o=100.,h=101.3,l=100.,c=100.):return dict(ts=t,open=o,high=h,low=l,close=c)
def run(b,v='A',s=None,mode='historical',obs=None):return replay(s or signal(),b,v,P,0,mode,obs)
class ExecutionTests(unittest.TestCase):
 def test_no_prices(self):self.assertEqual(run([])['status'],'DATA_GAP_PRICES')
 def test_bad_ohlc(self):
  with self.assertRaises(ValueError):run([bar(0,h=90)])
 def test_duplicate_prices(self):
  with self.assertRaises(ValueError):run([bar(0),bar(0)])
 def test_nonfinite_price(self):
  with self.assertRaises(ValueError):run([bar(0,o=float('nan'))])
 def test_unaligned(self):
  with self.assertRaises(ValueError):run([bar(1)])
 def test_receive_before_signal(self):
  s=signal();s['first_received_ms']=0
  with self.assertRaises(ValueError):run([],s=s)
 def test_future_cohort(self):
  self.assertEqual(replay(signal(),[],'A',P,M,'forward')['status'],'EXPOSED_NOT_FORWARD')
 def test_B_not_forward(self):
  with self.assertRaises(ValueError):run([],v='B',mode='forward')
 def test_ml_not_relaxed(self):
  s=signal();s['ml_passed']=False;self.assertEqual(run([],s=s)['status'],'EXCLUDED_ML')
 def test_wrong_keep(self):
  s=signal();s['filter_keep']='top100'
  with self.assertRaises(ValueError):run([],s=s)
 def test_TP_before_order(self):self.assertEqual(run([bar(0,o=98,c=98,h=98,l=98),bar(M)])['status'],'PRICE_ALREADY_AT_TP1')
 def test_stop_before_order(self):self.assertEqual(run([bar(0,o=108,c=108,h=108,l=108),bar(M)])['status'],'PRICE_ALREADY_AT_STOP')
 def test_no_fill_before_acceptance(self):
  r=run([bar(0),bar(M,o=110,h=111,l=109,c=110)])
  self.assertEqual(r['attempts'][0]['status'],'WAIT_ZONE');self.assertNotIn('entry',r)
 def test_all_three_targets(self):
  r=run([bar(0),bar(M),bar(2*M,o=100,h=100.5,l=90,c=95)])
  self.assertEqual(r['status'],'CLOSED_PRICE_MODEL');self.assertEqual([e['fraction']for e in r['events']],[.5,.3,.2])
 def test_SL_before_TP(self):
  r=run([bar(0),bar(M,h=120,l=80)])
  self.assertEqual(r['events'][0]['kind'],'SL');self.assertEqual(len(r['events']),1)
 def test_TP_fill_minute_banned(self):
  r=run([bar(0),bar(M,l=90),bar(2*M,o=100,h=100.5,l=90,c=95)])
  self.assertTrue(r['fill_minute_TP_banned']);self.assertEqual(r['events'][0]['time_ms'],3*M)
 def test_BE_only_next_minute(self):
  # TP1 in minute2, high above future BE still cannot trigger BE in that same minute.
  r=run([bar(0),bar(M),bar(2*M,o=100,h=102,l=98.5,c=99),bar(3*M,o=101.2,h=102,l=90,c=95)])
  self.assertEqual([e['kind']for e in r['events']],['TP1','BE'])
  self.assertEqual(r['events'][1]['time_ms'],4*M)
 def test_gap_stop_at_open(self):
  r=run([bar(0),bar(M),bar(2*M,o=115,h=116,l=114,c=115)])
  self.assertEqual(r['events'][0]['price'],115)
 def test_expiry_not_new_order(self):
  s=signal();b=[bar(0)]+[bar(t,o=100,h=100.1,l=100,c=100)for t in range(M,M+8*H+M,M)]
  self.assertEqual(run(b,s=s)['status'],'NOFILL_EXPIRED')
 def test_gap_not_interpolated(self):self.assertEqual(run([bar(0),bar(2*M)])['status'],'DATA_GAP_MINUTE')
 def test_tail_pending(self):self.assertEqual(run([bar(0),bar(M)])['status'],'PENDING_DATA')
 def test_cost_denominator(self):
  r=run([bar(0),bar(M),bar(2*M,o=100,h=100.5,l=90,c=95)])
  self.assertAlmostEqual(r['price_R']['21']-r['price_R']['50'],.0029/.056)
  self.assertAlmostEqual(r['compatibility_R_0581']['21']*.0581,r['price_R']['21']*.056)
 def test_no_funding_zero_or_real_fill(self):
  r=run([bar(0),bar(M),bar(2*M,o=100,h=100.5,l=90,c=95)])
  self.assertIsNone(r['funding_R']);self.assertIsNone(r['true_net_R']);self.assertFalse(r['actual_fill_verified'])
 def test_gate_unknown(self):self.assertEqual(gate_evidence(None,M)['status'],'UNKNOWN')
 def test_future_gate(self):self.assertEqual(gate_evidence({'asof_ms':M+1},M)['status'],'UNKNOWN')
 def test_old_gate(self):self.assertEqual(gate_evidence({'asof_ms':0},2*M)['status'],'UNKNOWN')
 def test_blocked_egress(self):self.assertEqual(gate_evidence({'asof_ms':M,'flags':{'egress_safe':False}},M)['status'],'BLOCKED')
 def test_all_observed_gates(self):self.assertEqual(gate_evidence({'asof_ms':M,'flags':dict.fromkeys(FLAGS,True)},M)['status'],'OBSERVED_GATES_PASS')
 def test_partial_gate_unknown(self):self.assertEqual(gate_evidence({'asof_ms':M,'flags':{'egress_safe':True}},M)['status'],'UNKNOWN')
 def test_no_BTC_future(self):
  s=signal();s.update(btc_close_known=90,btc_close_24h_known=100,btc_close_known_ms=2*M,btc_close_24h_known_ms=2*M-24*H)
  self.assertEqual(signal_regime(s),'UNKNOWN')
 def test_regime_bounds(self):self.assertEqual(regime(97,100),'DOWN');self.assertEqual(regime(103,100),'UP');self.assertEqual(regime(None,100),'UNKNOWN')
 def test_summary_no_fake_zero(self):
  m=summarize([run([])])[0];self.assertIsNone(m['sum_price_R']);self.assertIsNone(m['price_R_per_trade']);self.assertEqual(m['true_net_R'],'НЕ ПРОВЕРЕНО')
if __name__=='__main__':unittest.main()
