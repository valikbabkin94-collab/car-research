import unittest,copy
from ingest import ingest,verify
from test_replay import signal,M
class IngestTests(unittest.TestCase):
 def test_hash_chain(self):
  a=signal();b=dict(a,id='second');r=ingest([a,b],{'registration_ms':0,'model_snapshot_verified':False},{'repository':'unit'})
  self.assertEqual(verify(r),r[-1]['sha256']);self.assertEqual(r[0]['cohort'],'FORWARD_MODEL_NOT_PINNED')
 def test_old_never_oos(self):self.assertEqual(ingest([signal()],{'registration_ms':M},{})[0]['cohort'],'EXPOSED_NOT_OOS')
 def test_conflicting_duplicate_rejected(self):
  a=signal();b=dict(a,reference_price=90)
  with self.assertRaises(ValueError):ingest([a,b],{'registration_ms':0},{})
 def test_identical_duplicate_once(self):self.assertEqual(len(ingest([signal(),signal()],{'registration_ms':0},{})),1)
 def test_tamper_rejected(self):
  r=ingest([signal()],{'registration_ms':0},{});r[0]['signal']['reference_price']=1
  with self.assertRaises(ValueError):verify(r)
 def test_key_not_copied(self):
  a=dict(signal(),api_key='unit-secret');r=ingest([a],{'registration_ms':0},{})
  self.assertNotIn('api_key',r[0]['signal'])
if __name__=='__main__':unittest.main()
