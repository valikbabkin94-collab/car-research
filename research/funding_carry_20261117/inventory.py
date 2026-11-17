"""Read only inventory of already saved Binance funding. No PnL."""
import json,gzip,hashlib,os,subprocess
from pathlib import Path
out=Path("research/funding_carry_20261117");out.mkdir(parents=True,exist_ok=True)
rows=[];errors=[]
for p in sorted(Path("source").rglob("funding/*.json.gz")):
 try:
  raw=p.read_bytes();d=json.loads(gzip.decompress(raw));rr=sorted(d.get("rows",[]),key=lambda r:int(r["ts"]));usable=[r for r in rr if r.get("interval_hours") and float(r["interval_hours"])>0]
  rows.append(dict(symbol=d.get("symbol",p.name.removesuffix(".json.gz")),path=str(p),sha256=hashlib.sha256(raw).hexdigest(),n=len(rr),normalized_n=len(usable),first_ms=int(rr[0]["ts"])if rr else None,last_ms=int(rr[-1]["ts"])if rr else None,interval_hours=sorted({float(r["interval_hours"])for r in usable}),coverage=d.get("coverage",[]),funding_positive_n=sum(float(r["rate"])>0 for r in rr)))
 except Exception as e:errors.append(dict(path=str(p),error=str(e)))
result=dict(status="INVENTORY_COMPLETE_NO_PNL",code_sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),sources=rows,errors=errors,funding_files=len(rows),funding_rows=sum(r["n"]for r in rows),private_data_access=False,live_changes=0)
p=out/"DATA_INVENTORY_FUNDING.json";p.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items()if k not in["sources","errors"]}))
# API-only publication, branch restricted, no token in command arguments.
import urllib.request
repo=os.environ["GITHUB_REPOSITORY"];assert repo=="valikbabkin94-collab/car-research"
headers={"Authorization":"Bearer "+os.environ["GH_TOKEN"],"Accept":"application/vnd.github+json","User-Agent":"CAR-offline-carry"}
def api(path,method="GET",data=None):
 req=urllib.request.Request("https://api.github.com/repos/"+repo+"/"+path,data=json.dumps(data).encode()if data is not None else None,headers=headers,method=method)
 with urllib.request.urlopen(req,timeout=60)as r:return json.load(r)
head=api("git/ref/heads/research/funding-carry")["object"]["sha"];tree=api("git/commits/"+head)["tree"]["sha"]
newtree=api("git/trees","POST",dict(base_tree=tree,tree=[dict(path=str(p),mode="100644",type="blob",content=p.read_text())]));commit=api("git/commits","POST",dict(tree=newtree["sha"],parents=[head],message="research: saved funding inventory only, no PnL [skip ci]"));api("git/refs/heads/research/funding-carry","PATCH",dict(sha=commit["sha"],force=False));print("INVENTORY_COMMIT",commit["sha"])
