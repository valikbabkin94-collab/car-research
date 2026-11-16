"""Synthetic unit fixtures only; not market evidence."""
import importlib.util,json,unittest
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]/'research/scenario_factory_20261116';spec=importlib.util.spec_from_file_location('research_rules',LAB/'rules.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class ScenarioResearchTests(unittest.TestCase):
 def test_normalized_squeeze_funding(self):
  b=[[i*r.H,100,101,90 if i==10 else 95,100,10,1000] for i in range(24)]
  self.assertIsNotNone(r.squeeze_signal(b,{'fundingRate':'-0.0005'},240));self.assertIsNone(r.squeeze_signal(b,{'fundingRate':'-0.0005'},480));self.assertIsNone(r.squeeze_signal(b,{'fundingRate':'-0.001'},None))
 def test_no_new_low_required(self):
  b=[[i*r.H,100,101,95,100,10,1000] for i in range(24)];b[-1][3]=90;self.assertIsNone(r.squeeze_signal(b,{'fundingRate':'-0.001'},480))
 def test_announcement_missing_exact_timestamp_blocked(self):
  x=r.parse_delisting({'url':'https://announcements.bybit.com/en/article/test','dateTimestamp':0},'',1794820620000);self.assertEqual(x['status'],'DATA_GAP_EXACT_PUBLICATION_TIME')
 def test_announcement_official_domain_only(self):
  self.assertEqual(r.parse_delisting({'url':'https://example.invalid/en/article/test'},'',0)['status'],'REJECTED_UNOFFICIAL_SOURCE')
 def test_paired_accounting_never_claims_verified_maker(self):
  cfg=json.loads((LAB/'EXPERIMENT_S5.json').read_text());self.assertFalse(cfg['maker_fill_verified']);self.assertEqual(cfg['maker_per_leg'],.0002);self.assertEqual(cfg['taker_per_leg'],.00055)
if __name__=='__main__':unittest.main()
