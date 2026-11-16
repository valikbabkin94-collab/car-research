"""Execution fixtures only; synthetic bars are never research history."""
import importlib.util,pathlib,unittest
sp=importlib.util.spec_from_file_location('pf_audit',pathlib.Path(__file__).resolve().parents[1]/'research/pf_live_vs_backtest_20261116/audit.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
class AuditTests(unittest.TestCase):
 def frame(self,t):return {u:(100.,100.5,99.5,100.) for u in range(t,t+80*a.H,a.S)}
 def test_partials_plus_be_remain_positive(self):
  t=a.START+a.H;f=self.frame(t);f[t]=(100,101,99,100);f[t+a.S]=(99,100,95,98);f[t+2*a.S]=(99.9,100.1,99.8,100)
  r=a.replay(f,t,100);self.assertEqual([e['kind'] for e in r['events']],['TP1','TP2','BE']);self.assertAlmostEqual(sum(e['fraction'] for e in r['events']),1)
  self.assertGreater(a.economics(r,{'known':True,'payments':[]})['net_R'],0)
 def test_sl_first_and_entry_bar_tp_exclusion(self):
  t=a.START+a.H;f=self.frame(t);f[t]=(100,107,90,100)
  r=a.replay(f,t,100);self.assertEqual(r['events'][0]['kind'],'SL')
  f[t]=(100,101,95,100);f[t+a.S]=(100,107,99,101);r=a.replay(f,t,100);self.assertTrue(r['fill_bar_tp_ambiguous']);self.assertEqual(r['events'][0]['kind'],'SL')
 def test_fee_be_can_reduce_future_tp_profit_not_profit_fitting(self):
  t=a.START+a.H;f=self.frame(t);f[t]=(100,100.1,99.9,100);f[t+a.S]=(99,99.5,97.8,98);f[t+2*a.S]=(99.8,99.95,98,99);f[t+3*a.S]=(97,97.2,93.6,94)
  old=a.replay(f,t,100);new=a.replay(f,t,100,.0011);self.assertEqual(new['entry'],old['entry']);self.assertLess(new['exit_ms'],old['exit_ms']);self.assertLess(new['gross_return'],old['gross_return'])
 def test_missing_funding_never_zero(self):
  t=a.START+a.H;f=self.frame(t);r=a.replay(f,t,100);self.assertIsNone(a.economics(r,{'known':False,'payments':[]})['net_R'])
 def test_ambiguous_signal_match_never_chooses_best_pnl(self):
  rows=[dict(symbol='ABCUSDT',signal_ms=t) for t in [2*a.H,3*a.H]];status,r=a.match(dict(symbol='ABCUSDT',created_ms=2*a.H+a.H//2),rows);self.assertEqual(status,'AMBIGUOUS');self.assertIsNone(r)
 def test_series_probability_and_partial_metric(self):
  p=a.series_probability(.5);self.assertAlmostEqual(p['at_least12'],14/8192);self.assertAlmostEqual(p['exact12'],13/8192);self.assertEqual(a.series_probability(1)['at_least12'],1);self.assertEqual(a.series_probability(0)['at_least12'],0)
if __name__=='__main__':unittest.main()
