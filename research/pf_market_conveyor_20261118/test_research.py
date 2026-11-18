import unittest
import research as r
class Causality(unittest.TestCase):
 def test_future_pnl_never_selects(self):
  week=r.monday(r.START)+50*r.D
  closed=[dict(status='CLOSED',exit_ms=week-1,net_R=1.) for _ in range(10)]
  future=[dict(status='CLOSED',exit_ms=week+1,net_R=1000.) for _ in range(20)]
  self.assertEqual(r.choose({'A':closed,'B':future},week),'A')
 def test_negative_or_small_n_cash(self):
  w=r.START+40*r.D
  rs=[dict(status='CLOSED',exit_ms=w-1,net_R=-1.) for _ in range(10)]
  self.assertIsNone(r.choose({'A':rs},w));self.assertIsNone(r.choose({'A':[dict(x,net_R=1.) for x in rs[:9]]},w))
 def test_exit_exact_decision_not_known(self):
  w=r.START+40*r.D
  rs=[dict(status='CLOSED',exit_ms=w,net_R=1.) for _ in range(10)]
  self.assertIsNone(r.choose({'A':rs},w))
 def test_close_entry_no_preentry_wick(self):
  t=r.START;s=dict(id='fixture',symbol='X',signal_ms=t,limit=101.3,selected=True)
  frame={bt:(100,100,99.9,100) for bt in range(t,t+81*r.H,r.S)};frame[t]=(100,1000,1,100)
  p=r.replay(frame,s,'market');self.assertEqual(p['entry_ms'],t+r.S);self.assertEqual(p['events'][-1]['kind'],'TIME')
 def test_chase_rejects_already_tp2(self):
  t=r.START;s=dict(id='fixture',symbol='X',signal_ms=t,limit=101.3,selected=True)
  p=r.replay({t:(100,100,90,94)},s,'chase_tp2');self.assertEqual(p['status'],'REJECTED_CHASE_GEOMETRY')
 def test_missing_not_zero_trade(self):
  s=dict(id='fixture',symbol='X',signal_ms=r.START,limit=101.3,selected=True)
  p=r.replay({},s,'market');self.assertEqual(p['status'],'DATA_GAP_ENTRY_5M');self.assertNotIn('net_R',p)
 def test_boundary_h1_future_close_excluded(self):
  p=dict(status='CLOSED',signal_ms=r.HALF-1,exit_ms=r.HALF+1,net_R=100.,net_R_adverse=99.,funding_known=True)
  m=r.metrics([p],r.START,r.HALF);self.assertEqual(m['n'],0);self.assertEqual(m['boundary_censored'],1)
 def test_zero_vector_control(self):self.assertEqual(r.sign_p({1:0},{1:0}),1.)
