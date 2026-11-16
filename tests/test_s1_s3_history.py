"""Execution causality tests use synthetic fixtures only, never research inputs."""
import importlib.util, pathlib, unittest
spec=importlib.util.spec_from_file_location('history',pathlib.Path(__file__).resolve().parents[1]/'research/s1_s3_history_20261116/history.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
class ReplayTests(unittest.TestCase):
 def setUp(self):
  self.fund={'rows':[],'coverage':[[0,100*h.H]]}
 def test_samebar_sl_wins_and_no_entrybar_tp(self):
  b=[[0,100,100,100,100,1,100],[h.B,100,140,80,110,1,100]]
  r=h.simulate(b,0,1,90,48*h.H,self.fund)
  self.assertEqual(r['events'][0]['kind'],'SL');self.assertLess(r['net_R'],0)
  b[1][3]=95;r=h.simulate(b,0,1,90,48*h.H,self.fund);self.assertEqual(r['status'],'CENSORED');self.assertEqual(r['events'],[])
 def test_gap_stop_uses_worse_open(self):
  b=[[0,100,100,100,100,1,100],[h.B,100,101,95,100,1,100],[2*h.B,80,85,79,81,1,100]]
  r=h.simulate(b,0,1,90,48*h.H,self.fund);self.assertEqual(r['events'][0]['price'],80)
 def test_funding_money_sign_and_exit_inclusive(self):
  b=[[0,100,100,100,100,1,100],[h.B,100,101,99,100,1,100],[2*h.B,100,101,99,100,1,100]]
  f={'coverage':[[0,h.H]],'rows':[{'ts':h.B,'rate':.02},{'ts':2*h.B,'rate':-.01}]}
  r=h.simulate(b,0,1,90,2*h.B,f);self.assertGreater(r['funding_R'],0)
  r2=h.simulate(b,0,-1,110,2*h.B,f);self.assertLess(r2['funding_R'],0)
 def test_unknown_funding_not_zero(self):
  b=[[0,100,100,100,100,1,100],[h.B,100,101,99,100,1,100],[2*h.B,100,101,99,100,1,100]]
  r=h.simulate(b,0,1,90,2*h.B,{'rows':[],'coverage':[]});self.assertEqual(r['status'],'FUNDING_UNKNOWN');self.assertIsNone(r['net_R'])
 def test_price_gap_invalid_stop_and_censor(self):
  b=[[h.B,100,101,99,100,1,100],[3*h.B,100,101,99,100,1,100]]
  self.assertEqual(h.simulate(b,0,1,90,48*h.H,self.fund)['status'],'DATA_GAP_PRICE')
  self.assertEqual(h.simulate(b,0,1,110,48*h.H,self.fund)['status'],'REJECTED_INVALID_STOP')
 def test_metrics_drawdown_and_best3(self):
  rows=[dict(status='CLOSED',net_R=v,exit_ms=i,hold_hours=1) for i,v in enumerate([2,-1,-2,4])]
  m=h.metrics(rows);self.assertEqual(m['maxDD_R'],3);self.assertEqual(m['netR'],3);self.assertEqual(m['PF'],2);self.assertEqual(m['best3_share_net'],2)
class PointInTimeTests(unittest.TestCase):
 def test_future_volume_cannot_change_earlier_rank(self):
  import tempfile, json
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);(root/'h1').mkdir()
   h.write(root/'H1_MANIFEST.json',{'archive_catalog_size':2,'symbols':[{'symbol':'AAAUSDT','errors':[]},{'symbol':'BBBUSDT','errors':[]}]})
   for sym,q in [('AAAUSDT',2),('BBBUSDT',1)]:
    bars=[[h.WARM+i*h.H,100,101,99,100,1,q if i<30 else 10000 if sym=='BBBUSDT' else q] for i in range(32)]
    h.gzwrite(root/'h1'/(sym+'.json.gz'),{'bars':bars})
   _,idx,rank=h.make_ranks(root)
   self.assertEqual(int(rank[idx['AAAUSDT'],29]),1)
   self.assertEqual(int(rank[idx['BBBUSDT'],29]),2)
   self.assertEqual(int(rank[idx['BBBUSDT'],30]),1)
   self.assertEqual(int(rank[idx['AAAUSDT'],22]),0)
class BinanceAnnouncementTests(unittest.TestCase):
 def test_exact_release_and_single_deadline(self):
  import sys
  sys.modules['history']=h
  spec=importlib.util.spec_from_file_location('fallback',pathlib.Path(__file__).resolve().parents[1]/'research/s1_s3_history_20261116/binance_delisting_fallback.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
  rec={'title':'Binance Futures Will Delist ABCUSDT Perpetual','releaseDate':h.START}
  detail={'body':'Binance Futures will close all positions and conduct automatic settlement at 2026-08-06 09:00 (UTC). ABCUSDT perpetual contracts will be delisted.'}
  r=f.parse(rec,detail);self.assertEqual(r['status'],'ELIGIBLE');self.assertEqual(r['symbols'],['ABCUSDT'])
  rec['releaseDate']='2026-08-01';self.assertEqual(f.parse(rec,detail)['status'],'REJECTED_PUBLICATION_WINDOW_OR_TIMESTAMP')
  rec['releaseDate']=h.START;detail['body']+=' Delisting at 2026-08-07 10:00 UTC.'
  self.assertEqual(f.parse(rec,detail)['status'],'DATA_GAP_UNAMBIGUOUS_SYMBOL_OR_DELIST_TIME')
class FundingAmbiguityTests(unittest.TestCase):
 def test_benefit_not_credited_after_possible_close_payer_stays_exposed(self):
  events=[dict(kind='TP1',time_ms=h.B,fraction=.5)]
  self.assertEqual(h.remaining_for_payment(events,h.B+1,1,-.001),.5)
  self.assertEqual(h.remaining_for_payment(events,h.B+1,1,.001),1.)
  self.assertEqual(h.remaining_for_payment(events,2*h.B,1,.001),.5)
  events=[dict(kind='TIME',time_ms=h.B,fraction=1)]
  self.assertEqual(h.remaining_for_payment(events,h.B,1,-.001),1.)
  self.assertEqual(h.remaining_for_payment(events,h.B+1,1,-.001),0.)
class SavedLedgerCorrectionTests(unittest.TestCase):
 def test_reprice_preserves_price_part_and_does_not_replay_fills(self):
  old=dict(status='CLOSED',direction=1,entry_ms=h.B,exit_ms=3*h.B,entry=100,price_net_R=.2,net_R=.21,risk_denominator=.1,events=[dict(kind='TP1',fraction=.5,time_ms=2*h.B),dict(kind='TIME',fraction=.5,time_ms=3*h.B)])
  bars=[[i*h.B,100,101,99,100,1,100] for i in range(4)]
  fund={'rows':[{'ts':2*h.B+1,'rate':-.001}], 'coverage':[[0,h.H]]}
  new=h.reprice_saved_funding(old,bars,fund)
  self.assertEqual(new['events'],old['events']);self.assertEqual(new['price_net_R'],.2)
  self.assertAlmostEqual(new['net_R'],.205);self.assertEqual(new['pre_correction_net_R'],.21)
class ActualPublicAnnouncementSchemaTests(unittest.TestCase):
 def test_saved_child_tree_separates_settlement_and_new_order_ban(self):
  import gzip,json,sys
  sys.modules['history']=h
  spec=importlib.util.spec_from_file_location('fallback',pathlib.Path(__file__).resolve().parents[1]/'research/s1_s3_history_20261116/binance_delisting_fallback.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
  root=pathlib.Path(__file__).resolve().parents[1]/'research/s1_s3_history_20261116/RESULTS/ANNOUNCEMENT_SOURCES'
  a=json.load(gzip.open(root/'c30e6891afa54651ba950f8af144f861.json.gz','rt'));r=f.parse(a['record'],a['detail'])
  self.assertEqual(r['status'],'REJECTED_NEW_POSITIONS_DISABLED');self.assertEqual(r['symbols'],['MITOUSDT','PTBUSDT'])
  self.assertLess(r['new_position_ban_ms'],r['publication_ms'])
  a=json.load(gzip.open(root/'2f1a743334f044abbd82e34093c7b771.json.gz','rt'));r=f.parse(a['record'],a['detail'])
  self.assertEqual(r['status'],'ELIGIBLE');self.assertEqual(r['symbols'],['1000000BOBUSDT','PROMPTUSDT','PUMPBTCUSDT'])
  self.assertEqual(r['exit_deadline_ms'],int(h.dt.datetime(2026,10,4,9,tzinfo=h.dt.timezone.utc).timestamp()*1000))
  self.assertGreater(r['document_last_update_ms'],(r['publication_ms']//h.B+1)*h.B)
if __name__=='__main__':unittest.main()
