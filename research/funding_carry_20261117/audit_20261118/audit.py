import pathlib,json,hashlib,os
root=pathlib.Path('research/funding_carry_20261117');final=root/'final';hashes=json.loads((final/'ARTIFACT_HASHES.json').read_text());checks=[]
for name,h in hashes.items():
 p=final/name;actual=hashlib.sha256(p.read_bytes()).hexdigest();assert actual==h,(name,actual,h);checks.append(name)
s=json.loads((final/'SELECTION_FROZEN.json').read_text());v=json.loads((final/'VERDICT.json').read_text());assert s['H1_only'] and s['H2_not_used'] and s['winner']==v['winner'];assert not v['economic_paper_candidate'];assert json.loads((final/'variants.json').read_text())==[]
metrics=json.loads((final/'ALL_VARIANTS_ALL_PERIODS.json').read_text())
out=root/'audit_20261118';out.mkdir(exist_ok=True);(out/'CHECKPOINT.json').write_text(json.dumps(dict(status='SAVED_RESULTS_INTEGRITY_PASS',checked_hashes=checks,selection=s,verdict=v,source_commit='70afcbff8d9d40e1cf9e7d452fadf9f89ddbe963',audit_code_sha=os.environ['GITHUB_SHA'],new_pnl_runs=0,live_changes=0),ensure_ascii=False,indent=2))
print(v['headline']);print('All saved final hashes verified:',len(checks))
