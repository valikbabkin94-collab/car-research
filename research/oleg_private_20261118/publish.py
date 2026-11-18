"""CAS publication of research files only. No runtime or trading endpoints."""
import os,json,base64,time,urllib.request,urllib.error
from pathlib import Path
def publish(folder):
 repo=os.environ["GITHUB_REPOSITORY"];branch="research/oleg-and-private-20261118";root=Path("research/oleg_private_20261118");folder=Path(folder);assert repo=="valikbabkin94-collab/car-research"and folder.is_relative_to(root)
 headers={"Authorization":"Bearer "+os.environ["GH_TOKEN"],"Accept":"application/vnd.github+json","User-Agent":"CAR-offline-carry"}
 def api(p,method="GET",data=None):
  req=urllib.request.Request("https://api.github.com/repos/"+repo+"/"+p,data=json.dumps(data).encode()if data is not None else None,headers=headers,method=method)
  with urllib.request.urlopen(req,timeout=90)as r:return json.load(r)
 entries=[]
 for p in sorted(folder.rglob("*")):
  if not p.is_file()or "__pycache__"in str(p)or p.suffix not in[".json",".md",".csv",".gz",".npz"]:continue
  if p.stat().st_size>80*1024*1024:raise ValueError("RESULT_FILE_TOO_LARGE")
  blob=api("git/blobs","POST",dict(encoding="base64",content=base64.b64encode(p.read_bytes()).decode()));entries.append(dict(path=str(p),mode="100644",type="blob",sha=blob["sha"]))
 for attempt in range(20):
  head=api("git/ref/heads/"+branch)["object"]["sha"];tree=api("git/commits/"+head)["tree"]["sha"];t=api("git/trees","POST",dict(base_tree=tree,tree=entries));c=api("git/commits","POST",dict(tree=t["sha"],parents=[head],message="research: "+folder.name+" OLEG/private19 results and checkpoint [skip ci]"))
  try:api("git/refs/heads/"+branch,"PATCH",dict(sha=c["sha"],force=False));print("RESULT_COMMIT",c["sha"]);return c["sha"]
  except urllib.error.HTTPError as e:
   if e.code not in[409,422]or attempt==19:raise
   time.sleep(1+attempt)
if __name__=="__main__":publish(os.environ["LAB_OUTPUT"])
