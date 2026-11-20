"""Whitelist-only extraction from private saved outcomes. No network or account access."""
import argparse,gzip,json,hashlib,math
from pathlib import Path
TARGETS={'Whalesguide':'M1','WolfxCrypto_VIP':'M0_PROXY'}
def extract(source):
 out=[];seen=set();ranks={}
 for line in gzip.open(source,'rt'):
  r=json.loads(line);channel=r.get('channel')
  if channel not in TARGETS:continue
  key=hashlib.sha256((channel+':'+str(r['id'])).encode()).hexdigest()
  if key in seen:raise ValueError('DUPLICATE_SOURCE_ID')
  seen.add(key);ranks[channel]=ranks.get(channel,0)+1;v=(r.get('variants') or {}).get(TARGETS[channel],{})
  p={'key':key,'cohort':channel+'_'+TARGETS[channel],'channel':channel,'model':TARGETS[channel],
     'symbol':r.get('symbol'),'side':r.get('side'),'publication_ms':r['pub'],'source_channel_order':ranks[channel],
     'source_status':r['status'],'model_status':v.get('status'),'edited_visible':bool(r.get('edited_visible')),
     'first_received_ms':None,'funding_cash':None}
  for old,new in [('R','source_post21bp_R'),('entry','entry'),('stop','initial_stop'),('fill_ms','fill_ms'),('exit_ms','exit_ms'),('duration_h','duration_h')]:p[new]=v.get(old)
  out.append(p)
 if len(out)>300:raise ValueError('FROZEN_INPUT_BUDGET_EXCEEDED')
 return sorted(out,key=lambda x:(x['channel'],x['publication_ms'],x['key']))
def main():
 a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();v.out.parent.mkdir(parents=True,exist_ok=True);v.out.write_text(json.dumps(extract(v.source),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
