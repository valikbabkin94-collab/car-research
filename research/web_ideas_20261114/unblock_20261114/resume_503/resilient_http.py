"""Bounded public HTTP: 2 workers, shared pacing, six attempts, cooldown."""
import urllib.request,urllib.error,urllib.parse,time,threading,json,email.utils
from pathlib import Path
class NetworkPause(RuntimeError):pass
class FileFailed(RuntimeError):pass
def ascii_url(url):
 """Percent-encode Unicode object keys once, keeping existing escapes/query separators."""
 parts=urllib.parse.urlsplit(url)
 if parts.scheme!='https' or not parts.netloc or parts.fragment:
  raise ValueError('Expected an absolute public HTTPS URL without fragment')
 host=parts.netloc.encode('idna').decode('ascii')
 path=urllib.parse.quote(parts.path,safe='/%:@!$&\'()*+,;=-._~')
 query=urllib.parse.quote(parts.query,safe='=&%+/:,;')
 result=urllib.parse.urlunsplit((parts.scheme,host,path,query,''))
 result.encode('ascii')
 return result

class Client:
 def __init__(self,log,spacing=1.0,clock=time.monotonic,sleep=time.sleep,opener=urllib.request.urlopen,max_cooldowns=1):
  self.log=Path(log);self.log.parent.mkdir(parents=True,exist_ok=True);self.spacing=spacing;self.clock=clock;self.sleep=sleep;self.opener=opener;self.lock=threading.Lock();self.io=threading.BoundedSemaphore(2);self.next_at=0.;self.pause_until=0.;self.failed_files=set();self.cooldowns=0;self.max_cooldowns=max_cooldowns
 def event(self,**kw):
  with self.lock:
   with self.log.open('a',encoding='utf-8') as f:f.write(json.dumps({'at_utc':time.time(),**kw})+'\n')
 def wait(self,seconds):
  end=self.clock()+seconds
  while self.clock()<end:self.sleep(min(1,end-self.clock()))
 def retry_after(self,value):
  if not value:return 0
  try:return max(0,float(value))
  except ValueError:
   try:return max(0,email.utils.parsedate_to_datetime(value).timestamp()-time.time())
   except (ValueError,TypeError):return 0
 def get(self,url,file_id=None):
  file_id=file_id or url
  url=ascii_url(url)
  for attempt in range(6):
   with self.io:
    with self.lock:
     now=self.clock();slot=max(now,self.next_at,self.pause_until);self.next_at=slot+self.spacing
    self.wait(slot-self.clock())
    with self.lock:remaining=self.pause_until-self.clock()
    if remaining>0:self.wait(remaining)
    try:
     with self.opener(url,timeout=30) as r:b=r.read();code=r.status
     with self.lock:self.failed_files.clear()
     self.event(url=url,status=code,attempt=attempt+1,bytes=len(b));return b
    except urllib.error.HTTPError as e:
     code=e.code;body=e.read().decode(errors='replace')[:500];retry=self.retry_after(e.headers.get('Retry-After'));self.event(url=url,status=code,attempt=attempt+1,retry_after=retry,body=body)
     if code not in (429,503):raise
    except (OSError,TimeoutError) as e:
     code=None;retry=0;self.event(url=url,status=None,attempt=attempt+1,error=str(e))
   with self.lock:
    self.failed_files.add(file_id);need_cooldown=len(self.failed_files)>=3
    if need_cooldown:
     if self.cooldowns>=self.max_cooldowns:raise NetworkPause('Repeated failures after 10-minute cooldown; checkpoint required')
     self.pause_until=max(self.pause_until,self.clock()+600);self.cooldowns+=1;self.failed_files.clear()
   if need_cooldown:self.event(event='COOLDOWN',seconds=600)
   if attempt==5:raise FileFailed('Six attempts exhausted for '+file_id)
   delay=max(5*(2**attempt),retry);self.event(event='BACKOFF',url=url,seconds=delay);self.wait(delay)
