import gzip,hashlib,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from car_research_export import Exporter,regular

class ExportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  self.src=self.p/'source';self.src.mkdir();self.db=self.src/'snapshot.sqlite'
  c=sqlite3.connect(self.db)
  c.execute('create table trades(id integer,enter_tag text,realized_profit real,close_profit_abs real,initial_stop_loss real,stop_loss real,funding_fees real)')
  c.execute("insert into trades values(7,'PUMP_FADE:example',0,-9,100,110,0)")
  c.execute('create table orders(id integer,ft_trade_id integer,order_id text,filled real,fee real)')
  c.execute("insert into orders values(8,7,'ord1',0,0)")
  c.execute('create table trade_custom_data(ft_trade_id integer,cd_key text,cd_value text)')
  c.execute('insert into trade_custom_data values(?,?,?)',(7,'signal',json.dumps({'id':'PUMP_FADE:example','risk_usdt':5,'api_key':'never-export','text':'private post'})))
  c.commit();c.close()
 def ex(self,**kw):return Exporter(self.p/'out',[],[self.db],**kw)
 def test_sqlite_source_bytes_unchanged_and_no_sidecars(self):
  before=self.db.read_bytes();e=self.ex();e.db(self.db,'live');e.finish()
  self.assertEqual(before,self.db.read_bytes());self.assertEqual(sorted(x.name for x in self.src.iterdir()),['snapshot.sqlite'])
 def test_cash_zero_preserved_no_close_profit_fallback(self):
  e=self.ex();e.db(self.db,'live');t=json.loads((e.out/'live_trades.json').read_text())[0]
  self.assertEqual(t['realized_profit'],0);self.assertEqual(t['close_profit_abs'],-9)
  self.assertNotIn('net_R',t);self.assertEqual(t['source'],'PUMP_FADE')
 def test_foreign_keys_join_and_source_label_survives(self):
  e=self.ex();e.db(self.db,'live');t=json.loads((e.out/'live_trades.json').read_text())[0];o=json.loads((e.out/'live_orders.json').read_text())[0]
  self.assertEqual(t['id'],o['ft_trade_id']);self.assertNotEqual(t['id'],7);self.assertEqual(o['filled'],0)
 def test_custom_signal_private_fields_redacted(self):
  e=self.ex();e.db(self.db,'live');v=json.loads((e.out/'live_trade_custom_data.json').read_text())[0]['cd_value']
  self.assertEqual(v['api_key'],'[REDACTED_FIELD]');self.assertEqual(v['text'],'[REDACTED_FIELD]');self.assertEqual(v['risk_usdt'],5)
 def test_wal_rejected_without_opening_database(self):
  Path(str(self.db)+'-wal').write_bytes(b'not a safe snapshot');e=self.ex();e.db(self.db,'live')
  self.assertEqual(e.manifest['records'][0]['status'],'BLOCKED');self.assertFalse((e.out/'live_trades.json').exists())
 def test_missing_funding_is_none_not_zero(self):
  e=self.ex();e.db(self.db,'live');f=e.manifest['records'][0]['tables']['funding_payments']
  self.assertEqual(f,{'status':'MISSING','rows':None})
 def test_unknown_columns_preserved_with_redaction(self):
  c=sqlite3.connect(self.db);c.execute('alter table trades add column API_SECRET text');c.execute("update trades set API_SECRET='nope'");c.commit();c.close()
  e=self.ex();e.db(self.db,'live');t=json.loads((e.out/'live_trades.json').read_text())[0];self.assertEqual(t['API_SECRET'],'[REDACTED_FIELD]')
 def test_output_in_source_forbidden(self):
  with self.assertRaisesRegex(ValueError,'OUTSIDE'):Exporter(self.src/'out',[],[self.db])
 def test_output_existing_forbidden(self):
  out=self.p/'out';out.mkdir()
  with self.assertRaisesRegex(ValueError,'NOT_EXIST'):self.ex()
 def test_symlink_input_forbidden(self):
  link=self.p/'link.sqlite';link.symlink_to(self.db)
  with self.assertRaisesRegex(ValueError,'SYMLINK'):regular(link)
 def test_env_input_not_read(self):
  p=self.p/'.env';p.write_text('secret')
  with self.assertRaisesRegex(ValueError,'SENSITIVE'):regular(p)
 def test_sensitive_logs_drop_whole_line(self):
  p=self.src/'trace.log';p.write_text('UTC decision WAIT\nAuthorization: Bearer secret\nhttps://api.telegram.org/bot123456:ABC/sendMessage\n')
  e=self.ex();e.artifact(p,'log');text=(e.out/'log.json').read_text();self.assertIn('UTC decision WAIT',text);self.assertNotIn('secret',text);self.assertNotIn('ABC',text)
 def test_gzip_bounded_decompression(self):
  p=self.src/'rows.jsonl.gz';p.write_bytes(gzip.compress(b'x'*5000));e=self.ex(max_bytes=1000);e.artifact(p,'rows')
  self.assertEqual(e.manifest['records'][0]['error'],'DECOMPRESSED_SIZE_LIMIT')
 def test_artifact_rows_limit_and_malformed_visible(self):
  p=self.src/'feed.jsonl';p.write_text('{bad}\n{"source":"PF"}\n{"third":3}\n');e=self.ex(max_rows=2);e.artifact(p,'feed')
  r=e.manifest['records'][0];self.assertEqual(r['status'],'TRUNCATED');self.assertEqual(r['output_records'],2)
 def test_file_missing_is_blocked_not_empty_success(self):
  e=self.ex();e.artifact(self.src/'missing.json','missing');self.assertEqual(e.manifest['records'][0]['status'],'BLOCKED')
 def test_source_config_forbidden(self):
  p=self.src/'config.fastpath.json';p.write_text('{}');e=self.ex();e.artifact(p,'cfg');self.assertEqual(e.manifest['records'][0]['error'],'SENSITIVE_INPUT_FORBIDDEN')
 def test_readonly_bundle_manifest_hashes(self):
  e=self.ex();e.db(self.db,'live');m=e.finish()
  for name,d in m['output_sha256'].items():self.assertEqual(hashlib.sha256((e.out/name).read_bytes()).hexdigest(),d)
  self.assertEqual(m['network_calls'],0)
 def test_sqlite_truncation_not_complete(self):
  c=sqlite3.connect(self.db);c.execute("insert into trades values(9,'X:a',1,1,1,2,0)");c.commit();c.close()
  e=self.ex(max_rows=1);e.db(self.db,'live');self.assertEqual(e.manifest['records'][0]['tables']['trades']['status'],'TRUNCATED')
 def test_code_hash_only_no_contents(self):
  p=self.src/'strategy.py';p.write_text('print("not executed")')
  e=self.ex();e.code_digest(p,'code');r=e.manifest['records'][0]
  self.assertEqual(r['status'],'EXPORTED');self.assertFalse(r['contents_exported']);self.assertFalse((e.out/'code.json').exists())
 def test_code_digest_rejects_env(self):
  p=self.src/'.env';p.write_text('password=value');e=self.ex();e.code_digest(p,'env')
  self.assertEqual(e.manifest['records'][0]['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
