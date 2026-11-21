"""Source-only checks: AST/hash; no strategy imports, no market data or PnL.
Use --source-dir with GitHub source files saved under the documented aliases.
"""
import argparse,ast,hashlib,json
from pathlib import Path
LAB=Path(__file__).resolve().parent
SHA='bde8d93461238697e6f769e2282943b382875235'
ALIASES={'strategy_source.py':'fastpath/freqtrade/strategies/CarFastPathV1.py',
         'report.py':'fastpath/report.py','ingest.py':'fastpath/ingest.py',
         'shadow_pump_fade.py':'fastpath/tools/shadow_pump_fade.py',
         'shadow_altcoin_clone.py':'fastpath/tools/shadow_altcoin_clone.py'}
def main():
    a=argparse.ArgumentParser();a.add_argument('--source-dir',required=True,type=Path);args=a.parse_args()
    manifest=json.loads((LAB/'CODE_SOURCE_MANIFEST.json').read_text())
    sources={}
    for alias,path in ALIASES.items():
        r=next(r for r in manifest if r['path']==path and r['commit']==SHA)
        b=(args.source_dir/alias).read_bytes()
        assert hashlib.sha256(b).hexdigest()==r['sha256'],alias
        sources[alias]=b.decode();ast.parse(sources[alias])
    strategy=sources['strategy_source.py'];tree=ast.parse(strategy)
    fn={n.name:n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)}
    returns=[n.value.value for n in ast.walk(fn['_check_price'])if isinstance(n,ast.Return)and isinstance(n.value,ast.Constant)]
    assert 'PRICE_ALREADY_AT_TP1'in returns and 'PRICE_ALREADY_AT_STOP'in returns
    assert ast.unparse(fn['_crossed'].body[-1].value)=='price >= level if side == \'long\' else price <= level'
    assert 'dataframe.at[last, "close"]'in strategy
    assert 'self._check_price(s, rate)'in strategy
    assert '{"reason": reason, "at": _ms(datetime.now(timezone.utc))}'in strategy
    ingest=sources['ingest.py'];report=sources['report.py'];producer=sources['shadow_pump_fade.py']
    assert 'tps=(0.021, 0.042, 0.063)'in sources['shadow_altcoin_clone.py']
    assert '0 <= now_ms - created < 120_000'in ingest
    assert 'handle_own(own_signal_row(row, src, now), src, store, tg)'in ingest
    assert 'str((v or {}).get("reason") or "?").split(":")[0]'in report
    assert '"PRICE_ALREADY_AT_TP1": "цена уже прошла TP1"'in report
    assert '"PRICE_ALREADY_AT_STOP": "цена уже у стопа"'in report
    assert '"signal_ms"'not in producer or 'signal_ms=rec["t"] + H'in producer
    print(json.dumps({'source_SHA256_and_AST_checked':True,'price_gate_and_input_sources_checked':True,
     'mark_has_reason_time_not_price':True,'ingest_freshness_120s_checked':True,
     'report_reason_translation_and_colon_grouping_checked':True,
     'not_a_runtime_regression_or_trading_test':True,'new_PnL_runs':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
