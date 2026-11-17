"""Run only frozen carry profiles, persist each immediately for resumability."""
import os,sys,json,gzip,hashlib,subprocess,urllib.request,urllib.error,base64
from pathlib import Path
from engine import Data,simulate,save,finite
from publish import publish
B=Path("research/funding_carry_20261117")
def sha():return subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
def remote_file(path):
 url="https://api.github.com/repos/valikbabkin94-collab/car-research/contents/"+str(path)+"?ref=research/funding-carry";headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+os.environ["GH_TOKEN"],"User-Agent":"CAR-carry-resume"}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45)as r:d=json.load(r)
  if not d.get("content"):
   with urllib.request.urlopen(urllib.request.Request("https://api.github.com/repos/valikbabkin94-collab/car-research/git/blobs/"+d["sha"],headers=headers),timeout=45)as r:d=json.load(r)
  return base64.b64decode(d["content"])
 except urllib.error.HTTPError as e:
  if e.code==404:return None
  raise
def main():
 stage=sys.argv[1];variant=sys.argv[2]if len(sys.argv)>2 else None;folder=Path(os.environ["LAB_OUTPUT"]);folder.mkdir(parents=True,exist_ok=True)
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in[B/"engine.py",B/"PROTOCOL_PRE_PNL.json",B/"INTERPRETATIONS_PRE_PNL_RU.md"]};engine_fingerprint=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest();d=None;summaries=[];jobs=[]
 if stage=="train":jobs=[(variant,L,"H1",.0005,.005,0,"BASE")for L in[1,2]]
 elif stage=="validate":jobs=[(variant,L,p,.0005,.005,0,"BASE")for p in["H2","LAST40","FULL"]for L in[1,2]]
 else:
  selection=json.load((B/"selection/SELECTION_FROZEN.json").open());variant=selection["winner"]
  if variant:
   for L in[1,2]:
    jobs += [(variant,L,"H2",s,.005,0,"SLIP_"+str(s))for s in[0,.001]]
    jobs += [(variant,L,"H2",.0005,.01,0,"MMR1_PERCENT")]
    jobs += [(variant,L,"H2",.0005,.005,m,"MIN_NOTIONAL_"+str(m))for m in[5,10,25,100]]
 for variant,L,period,slip,mmr,minimum,label in jobs:
  key=period+"_L"+str(L)+"_"+label;target=folder/key;params=dict(variant=variant,leverage=L,period=period,slippage=slip,mmr=mmr,min_notional=minimum,engine_fingerprint=engine_fingerprint,data_run=44159556548);prior=remote_file(target/"PARAMS.json")
  if prior is not None and json.loads(prior)==params:
   existing=remote_file(target/"SUMMARY.json")
   if existing is not None:
    target.mkdir(parents=True,exist_ok=True);(target/"PARAMS.json").write_bytes(prior);(target/"SUMMARY.json").write_bytes(existing);summaries.append(json.loads(existing));print("REUSED_COMPLETED_PROFILE",key,flush=True);continue
  if d is None:d=Data()
  print("START_PROFILE",key,variant,flush=True);result=simulate(d,variant,L,period,slip=slip,mmr=mmr,min_notional=minimum);summary=dict(**result["summary"],profile_label=label,code_sha=sha(),engine_fingerprint=engine_fingerprint)
  if summary["status"]=="COMPLETE"and abs(summary["cash_reconciliation_error"])>1e-7:raise ValueError("CASH_RECONCILIATION_FAILED")
  save(target/"PARAMS.json",params);save(target/"SUMMARY.json",summary);save(target/"MONTHLY.json",result["monthly"]);(target/"LEDGER_AND_TRADES.json.gz").write_bytes(gzip.compress(json.dumps(finite(dict(events=result["events"],trades=result["trades"])),ensure_ascii=False,allow_nan=False).encode(),mtime=0));(target/"HOURLY_EQUITY.json.gz").write_bytes(gzip.compress(json.dumps(result["equity"],allow_nan=False).encode(),mtime=0));save(target/"INPUT_SHA.json",d.hashes);save(target/"CHECKPOINT.json",dict(status="PROFILE_SAVED",code_sha=sha(),parameters=params));publish(target);summaries.append(summary);print("COMPLETE_PROFILE",key,summary["net_USD"],summary["status"],flush=True)
 save(folder/"SUMMARIES.json",summaries);save(folder/"CHECKPOINT.json",dict(status="STAGE_COMPLETE",stage=stage,variant=variant,n_profiles=len(summaries),code_sha=sha(),engine_fingerprint=engine_fingerprint,live_changes=0));publish(folder)
if __name__=="__main__":main()
