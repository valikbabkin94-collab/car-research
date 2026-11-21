"""Read-only GitHub evidence checks. No trading SDK, env-file, market call or PnL.
python verify_evidence.py --github
Requires gh authentication for the existing private source repository.
Prints only safe checks; never writes raw source payload to the public lab.
"""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
LAB=Path(__file__).resolve().parent
REPO='valikbabkin94-collab/Crypto-Auto-Radar'

def gh_get(path):
    # Fixed read-only endpoint prefix, no arbitrary method or external URL.
    if not path.startswith('repos/'+REPO+'/'):
        raise ValueError('OUT_OF_SCOPE_REPOSITORY')
    result=subprocess.run(['gh','api',path,'-X','GET'],capture_output=True,check=True)
    return json.loads(result.stdout)

def pinned_file(commit,path,expected):
    obj=gh_get(f'repos/{REPO}/contents/{path}?ref={commit}')
    if not obj.get('content'):
        obj=gh_get(f'repos/{REPO}/git/blobs/{obj["sha"]}')
    raw=base64.b64decode(obj['content'])
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('SOURCE_SHA_MISMATCH')
    return raw

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--github',action='store_true');args=parser.parse_args()
    f=json.loads((LAB/'FINDINGS.json').read_text())
    scans=f['source_scan']
    assert len(scans)==50 and all(not r['truncated'] for r in scans)
    assert not any(r['original_T1_path_hits'] or r['actual_paper_data_hits'] for r in scans)
    assert f['new_financial_tests']==0 and f['old_PnL_replays']==0
    checks={'saved_scope_and_data_gates_consistent':True,'new_financial_tests':0,'github_rechecked':args.github}
    if args.github:
        m=json.loads((LAB/'READ_SOURCE_MANIFEST.json').read_text())
        targets={r['path']:r for r in m}
        p='live_journal/week_2026-11-16.json';r=targets[p]
        journal=json.loads(pinned_file(r['commit'],p,r['sha256']))
        assert len(journal['closed'])==26 and all('realized_profit' not in x for x in journal['closed'])
        checks['journal26_no_raw_realized_profit']=True
        p='OPS/acer/q/export_live_trades.py';r=targets[p]
        code=pinned_file(r['commit'],p,r['sha256']).decode()
        assert "t['realized_profit'] if t['realized_profit'] is not None else" in code
        assert "t['initial_stop_loss'] or t['stop_loss']" in code
        checks['exporter_has_documented_fallbacks']=True
        tree=gh_get(f'repos/{REPO}/git/trees/919c1e9a19e61591a1d4d6d20229aedb5432e801?recursive=1')
        assert not tree.get('truncated')
        actual={r['path']:r['sha']for r in tree['tree']if r['type']=='blob'}
        for pair in f['T2']['stale_archive_pairs']:
            assert actual[pair['path_earlier']]==actual[pair['path_later']]==pair['earlier_blob']==pair['later_blob']
        checks['three_archive_pairs_have_identical_git_blobs']=True
    print(json.dumps(checks,ensure_ascii=False,indent=2))
if __name__=='__main__':
    main()
