import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research/text_signals_audit_20261116'))
from classifier import classify
class TextTests(unittest.TestCase):
 def test_evaa_text_call_without_prices(self):
  r=classify('EVAA SHORT — обновили все максимумы, есть полка ликвидности снизу, жду откат на фиксации 12ч',set());self.assertEqual(r['label'],'SIGNAL');self.assertEqual(r['symbol'],'EVAAUSDT')
 def test_stop_update(self):self.assertEqual(classify('AGI — словили стоп',{'AGI'})['label'],'UPDATE')
 def test_percent_report(self):self.assertEqual(classify('−18%',set())['label'],'REPORT')
 def test_price_observation_not_signal(self):self.assertEqual(classify('ушли выше 3$',set())['label'],'UPDATE')
 def test_narrative_long_is_not_direction(self):self.assertNotEqual(classify('BTC Market analysis: bullish as long as support holds',{'BTC'})['label'],'SIGNAL')
 def test_ads_not_signals(self):self.assertEqual(classify('Join our VIP group BTC LONG',{'BTC'})['label'],'OTHER')
 def test_direction_call(self):self.assertEqual(classify('Long LA market entry',{'LA'})['symbol'],'LAUSDT')
if __name__=='__main__':unittest.main()

class RegressionTests(unittest.TestCase):
 def test_unicode_side(self):self.assertEqual(classify('EVAA 𝗦𝗛𝗢𝗥𝗧',set())['side'],'SHORT')
 def test_profit_retrospective_not_new_signal(self):self.assertEqual(classify('CTSI Short has achieved target 200% Profit 200%',{'CTSI'})['label'],'REPORT')
 def test_label_words_not_coins(self):self.assertEqual(classify('COIN $BTC Direction LONG Entry 100',{'BTC','COIN'})['symbol'],'BTCUSDT')
 def test_short_term_is_not_short_side(self):self.assertNotIn('MULTIPLE_DIRECTIONS',classify('COIN $BTC Direction LONG Entry 100 Short term targets 110',{'BTC'})['flags'])
