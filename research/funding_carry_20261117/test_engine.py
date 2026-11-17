"""Synthetic implementation fixtures only. Never research market history."""
import unittest
import numpy as np
import engine
H=engine.H
class Fixture:
 def __init__(self,n=10):
  self.times=np.arange(n+1,dtype=np.int64)*H;self.symbols=["BTCUSDT"];self.index={"BTCUSDT":0};self.hashes={};self.spot=np.full((1,n+1,4),100.);self.perp=self.spot.copy();self.mark=self.spot.copy();self.latest=np.full((n+1,1),.0001);self.previous=self.latest.copy();self.avg72=self.latest.copy();self.fresh=np.ones((n+1,1),bool);self.cover=self.fresh.copy();self.cashrate=np.zeros((n+1,1))
 def quote(self,kind,j,i):
  if i<0 or i>=len(self.times):return None
  a=getattr(self,kind)[j,i];return a if np.all(np.isfinite(a))else None
class CarryTests(unittest.TestCase):
 def setUp(self):engine.PERIODS["UNIT"]=(0,10*H)
 def runmodel(self,d=None,variant="FC4",L=1,**kw):return engine.simulate(d or Fixture(),variant,L,"UNIT",slip=0,**kw)
 def test_delta_cancels_common_price(self):self.assertAlmostEqual(engine.trade_return(2,100,101,150,151,0,0),0)
 def test_real_basis_change_cost(self):self.assertAlmostEqual(engine.trade_return(1,100,101,100,103,0,0),-2)
 def test_four_fees_not_two(self):
  r=self.runmodel();q=r["trades"][0]["quantity"];self.assertAlmostEqual(r["summary"]["fees"],q*100*(2*.001+2*.00055));self.assertAlmostEqual(r["summary"]["net_USD"],-r["summary"]["fees"])
 def test_new_pair_no_current_payment(self):
  d=Fixture();d.cashrate[0,0]=.1;r=self.runmodel(d);self.assertEqual(r["summary"]["funding_cash"],0)
 def test_actual_payment_not_eight_hour_normalized(self):
  d=Fixture();d.cashrate[4,0]=.0003;r=self.runmodel(d);q=r["trades"][0]["quantity"];self.assertAlmostEqual(r["summary"]["funding_cash"],q*100*.0003)
 def test_negative_payment_paid_before_exit(self):
  d=Fixture();d.cashrate[2,0]=-.003;d.latest[3:,0]=-.003;r=self.runmodel(d);self.assertLess(r["summary"]["negative_funding_cash"],0);self.assertEqual(r["trades"][0]["exit_ms"],3*H)
 def test_equal_underlying_quantity_and_no_borrow(self):
  r=self.runmodel();p=r["trades"][0];q=p["quantity"];self.assertLessEqual(q*100+q*100+p["fees"]/2,100+1e-10);self.assertAlmostEqual(p["initial_short_margin"],q*p["perp_entry"])
 def test_two_x_not_two_times_spot_size(self):
  q1=self.runmodel(L=1)["trades"][0]["quantity"];q2=self.runmodel(L=2)["trades"][0]["quantity"];self.assertGreater(q2/q1,1.3);self.assertLess(q2/q1,1.34)
 def test_margin50_real_account_not_combined_hedge(self):
  d=Fixture();d.mark[0,2,1]=126;d.perp[0,2,1]=126;r1=self.runmodel(d,L=1);r2=self.runmodel(d,L=2);self.assertEqual(r1["summary"]["margin_below50_episodes"],0);self.assertEqual(r2["summary"]["margin_below50_episodes"],1)
 def test_liquidation_spot_unwinds_next_hour(self):
  d=Fixture();d.mark[0,2,1]=180;d.perp[0,2,1]=180;r=self.runmodel(d,L=2);self.assertGreater(r["summary"]["proxy_liquidations"],0);self.assertTrue(any(t["reason"]=="PROXY_LIQUIDATION_SPOT_UNWIND_NEXT_HOUR"for t in r["trades"]))
 def test_held_price_gap_is_censored(self):
  d=Fixture();d.spot[0,3]=np.nan;r=self.runmodel(d);self.assertEqual(r["summary"]["status"],"INCONCLUSIVE_DATA_GAP");self.assertEqual(len(r["trades"]),0)
 def test_terminal_funding_not_claimed(self):
  d=Fixture();d.cashrate[10,0]=.2;r=self.runmodel(d);self.assertEqual(r["summary"]["funding_cash"],0)
 def test_basis_gate_does_not_select_sixth_coin(self):
  d=Fixture();d.perp[:]=101;d.mark[:]=101;r=self.runmodel(d,variant="FC6");self.assertEqual(r["summary"]["n_closed_pairs"],0)
 def test_cash_ledger_reconciles(self):
  d=Fixture();d.cashrate[4,0]=.001;r=self.runmodel(d);self.assertAlmostEqual(r["summary"]["cash_reconciliation_error"],0,places=10)
 def test_min_notional_is_separate_execution_audit(self):
  r=self.runmodel(min_notional=100);self.assertEqual(r["summary"]["n_closed_pairs"],0);self.assertGreater(r["summary"]["order_filter_rejected"],0)
 def test_maker_abort_reserved_cash_not_lost(self):
  d=Fixture();d.latest[:]=.0004;d.previous[:]=.0004;d.spot[0,1:,0]=101;d.spot[0,1:,1]=102;d.spot[0,1:,2]=99;d.spot[0,1:,3]=100;d.perp[0,1:,0]=101;d.perp[0,1:,1]=102;d.perp[0,1:,2]=99;d.perp[0,1:,3]=100
  r=self.runmodel(d,variant="FC5");self.assertGreater(r["summary"]["maker_unhedged_aborts"],0);self.assertGreater(min(x["equity"]for x in r["equity"]),90);self.assertAlmostEqual(r["summary"]["cash_reconciliation_error"],0,places=8)
 def test_future_payout_cannot_change_past_funding(self):
  d=Fixture();a=self.runmodel(d);d.cashrate[10,0]=.9;b=self.runmodel(d);self.assertEqual(a["summary"]["net_USD"],b["summary"]["net_USD"])
if __name__=="__main__":unittest.main()
