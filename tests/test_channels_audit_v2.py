import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/channels_audit_v2_20261116'))
from update_parser import actions
from engine import simulate,M
class AuditTests(unittest.TestCase):
 def signal(self):return dict(side='LONG',pub=1,stop=90,targets=[110,120],events=[])
 def bars(self):return np.array([[M,100,101,99,100],[2*M,105,106,104,105],[3*M,103,104,102,103]],float)
 def test_claim_not_instruction(self):self.assertEqual([x['kind']for x in actions('TP1 hit!')],['TP_REACHED_CLAIM']);self.assertNotIn('CLOSE_ALL',[x['kind']for x in actions('We closed all yesterday')])
 def test_conditional_and_negation_do_not_execute(self):
  self.assertEqual(actions('If TP1 is hit, move stop to entry')[0]['kind'],'UNRESOLVED_CONDITIONAL');self.assertEqual(actions('Do not close all')[0]['kind'],'UNRESOLVED_NEGATION')
 def test_explicit_actions_and_unresolved_fraction(self):self.assertEqual(actions('close half of position')[0]['fraction'],.5);self.assertEqual(actions('close part of position')[0]['kind'],'UNRESOLVED_FRACTION');self.assertEqual(actions('move stop loss to 94.2')[0]['price'],94.2);self.assertEqual(actions('stop loss at entry')[0]['kind'],'MOVE_BE')
 def test_partial_and_full_at_next_open(self):
  s=self.signal();s['events']=[dict(kind='CLOSE_PART',fraction=.5,effective_ms=2*M,post_key='a'),dict(kind='CLOSE_ALL',effective_ms=3*M,post_key='b')];r=simulate(self.bars(),s,'P1',4*M);self.assertEqual(r['status'],'TRADE');self.assertEqual([x['fraction']for x in r['events']],[.5,.5]);self.assertAlmostEqual(r['grossR'],.4);self.assertGreater(r['slippageR'],0)
 def test_future_message_not_visible(self):
  s=self.signal();s['events']=[dict(kind='CLOSE_ALL',effective_ms=8*M,post_key='x')];r=simulate(self.bars(),s,'P1',4*M);self.assertTrue(r['status'].startswith('CENSORED'));self.assertEqual(r['events'],[])
 def test_sl_first_and_no_tp_entry_bar(self):
  q=self.bars();q[0]=[M,100,125,89,100];r=simulate(q,self.signal(),'P3',4*M);self.assertEqual(r['events'][0]['kind'],'SL')
  q[0]=[M,100,125,99,100];r=simulate(q,self.signal(),'P3',4*M);self.assertTrue(r['status'].startswith('CENSORED'))
 def test_open_trade_is_not_time_closed(self):
  q=np.array([[i*M,100,101,99,100]for i in range(1,1502)],float);r=simulate(q,self.signal(),'P1',1503*M);self.assertTrue(r['status'].startswith('CENSORED'));self.assertIsNone(r['netR'])
 def test_data_gap_is_not_loss_or_nofill(self):
  q=self.bars()[1:];r=simulate(q,self.signal(),'P3',4*M);self.assertEqual(r['status'],'DATA_GAP_ENTRY');self.assertIsNone(r['netR'])
 def test_single_tp_p2(self):
  s=self.signal();s['targets']=[105];r=simulate(self.bars(),s,'P2',4*M);self.assertTrue(r['single_tp_fallback']);self.assertEqual(r['status'],'TRADE');self.assertEqual(r['events'][0]['fraction'],1.)
if __name__=='__main__':unittest.main()

class QualityTests(unittest.TestCase):
 def test_unknown_instruction_not_a_known_author_win_or_loss(self):
  from quality_review import gate
  a=[dict(policy='P1',status='TRADE',netR=v,unresolved_author_actions=1)for v in [2.,-2.]];b=gate(a)
  self.assertTrue(all(r['status']=='UNRESOLVED_AUTHOR_LOG'and r['netR']is None for r in b));self.assertEqual([r['counterfactual_netR']for r in b],[2.,-2.]);self.assertEqual(a[0]['status'],'TRADE')
 def test_quality_gate_preserves_other_policies(self):
  from quality_review import gate
  a=[dict(policy='P2',status='TRADE',netR=1.,unresolved_author_actions=3)];self.assertEqual(gate(a),a)

class ClaimTests(unittest.TestCase):
 def request(self):return dict(signal_pub=1,claim_pub=3*M+1,targets=[dict(index=1,price=110)],side='LONG')
 def test_future_candle_cannot_validate_old_claim(self):
  from claim_review import check_claim
  q=np.array([[M,100,101,99,100],[2*M,100,101,99,100],[3*M,100,150,99,120]],float);r=check_claim(q,self.request());self.assertFalse(r['levels'][0]['market_touch'])
 def test_missing_price_does_not_disprove_claim(self):
  from claim_review import check_claim
  q=np.array([[M,100,111,99,100]],float);self.assertEqual(check_claim(q,self.request())['verification'],'DATA_GAP_PROXY_PRICES')
