"""Publish only own research output; retry non-fast-forward concurrent job updates."""
import os,sys,json,base64,time,urllib.request,urllib.error
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];branch=os.environ['LAB_BRANCH'];folder=Path(os.environ['LAB_OUTPUT']);part=os.environ['LAB_PART'];root=Path(os.environ['LAB_ROOT'])
assert repo=='valikbabkin94-collab/car-research' and branch in ['research/paket-20261117','research/manager-all-scenarios']
assert folder.is_relative_to(root) and(folder/'CHECKPOINT.json').exists()
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'CAR-offline-results'}
def api(path,method='GET',data=None):
 request=urllib.request.Request('https://api.github.com/repos/'+repo+'/'+path,data=json.dumps(data).encode()if data is not None else None,headers=headers,method=method)
 with urllib.request.urlopen(request,timeout=90)as response:return json.load(response)
tree=[]
for p in sorted(folder.rglob('*')):
 if not p.is_file()or'__pycache__'in str(p)or p.suffix not in ['.json','.gz','.npz','.md']:continue
 if '/inputs/'in str(p):continue
 if p.stat().st_size>80*1024*1024:raise ValueError('OUTPUT_TOO_LARGE_USE_ARTIFACT')
 blob=api('git/blobs','POST',dict(content=base64.b64encode(p.read_bytes()).decode(),encoding='base64'))
 tree.append(dict(path=str(p),mode='100644',type='blob',sha=blob['sha']))
if branch=='research/manager-all-scenarios':
 reportpath='OTCHET_DLYA_CLAUDE_CODEX_MANAGER_ALL_SCENARIOS_20261117.md'
else:reportpath='OTCHET_DLYA_CLAUDE_CODEX_PAKET_20261117.md'
for attempt in range(20):
 head=api('git/ref/heads/'+branch)['object']['sha'];base=api('git/commits/'+head)['tree']['sha']
 try:
  d=api('contents/'+reportpath+'?ref='+head);body=base64.b64decode(d['content']).decode()
 except urllib.error.HTTPError as error:
  if error.code!=404:raise
  body='# Исследования17.11 — отчёты по готовности\n\n'
 marker='<!-- '+part+' -->';end='<!-- /'+part+' -->'
 if marker in body:
  start=body.index(marker);stop=body.index(end,start)+len(end);body=body[:start]+body[stop:]
 cp=json.loads((folder/'CHECKPOINT.json').read_text())
 body+='\n'+marker+'\n## '+part+'\n\n'+json.dumps(cp,ensure_ascii=False)+'\n\n[Отчёт и журналы]('+str(folder)+'/REPORT_RU.md). Код и сетка: `'+cp['code_sha']+'`.\n\n### ПРОСТЫМИ СЛОВАМИ ДЛЯ ВЛАДЕЛЬЦА\n\nВердикт и численные результаты находятся в отчёте части; DATA_GAP означает недостаток данных, а не проигрыш. Только enabled=false, включение после независимой проверки.\n\nDesktop Commander 0, Telegram-сессии 0, Bybit-ключи 0, LIVE изменений 0\n'+end+'\n'
 currenttree=tree+[dict(path=reportpath,mode='100644',type='blob',content=body)]
 t=api('git/trees','POST',dict(base_tree=base,tree=currenttree));c=api('git/commits','POST',dict(tree=t['sha'],parents=[head],message='research: '+part+' results, failures and checkpoint [skip ci]'))
 try:api('git/refs/heads/'+branch,'PATCH',dict(sha=c['sha'],force=False));print('RESULT_COMMIT',c['sha']);break
 except urllib.error.HTTPError as error:
  if error.code not in[409,422]or attempt==19:raise
  time.sleep(1+attempt)
