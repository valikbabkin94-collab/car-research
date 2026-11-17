"""Train-only selector, committed before validation jobs are allowed to start."""
import json,hashlib,subprocess
from pathlib import Path
from engine import save
from publish import publish
B=Path("research/funding_carry_20261117");out=B/"selection";rows=[]
for p in Path("train_artifacts").rglob("SUMMARIES.json"):rows+=json.load(p.open())
assert {r["variant"]for r in rows}=={"FC1","FC2","FC3","FC4","FC5","FC6"}
raw=[r for r in rows if r["leverage"]==1];eligible=[r for r in raw if r["status"]=="COMPLETE"and r["full_observed_months"]==6 and r["funding_unknown_position_hours"]/max(1,r["position_hours"])<=.01]
winner=max(eligible,key=lambda r:(r["net_USD"],r["variant"]))["variant"]if eligible else None
save(out/"H1_ALL_VARIANTS.json",rows);save(out/"SELECTION_FROZEN.json",dict(winner=winner,raw_H1_max=max(raw,key=lambda r:r["net_USD"])["variant"],selection_metric="netUSDT on100USDT capital at1x, baseline costs only",eligible=[r["variant"]for r in eligible],H1_only=True,H2_not_used=True,code_sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),train_scores_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),FC5_execution_upper_bound_only=winner=="FC5"));publish(out);print("FROZEN_WINNER",winner)
