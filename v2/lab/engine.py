"""Virtual candle engine. Pure numeric functions; synthetic tests are separate.
No exchange clients, credentials, orders, processes, or runtime configuration.
"""
import numpy as np
try:
 from numba import njit
except ImportError:
 def njit(**kw):
  return lambda f:f # Local synthetic tests only; Actions explicitly installs numba.
M=60000;H=3600000
# plan: SLfrac,TPdist1/2/3,weights1/2/3,BEafter,BEoffset,trailFrac,
# trailAfterHit(-1=off),holdH,giveback,minMove,entryMaker,normR
@njit(cache=True)
def simulate(q,t,entry,side,p,ft,fr,coverage):
 out=np.zeros(40,np.float64);out[0]=-1;out[1]=np.nan;out[31]=t;out[32]=entry
 if len(q)==0 or entry<=0:return out
 k=np.searchsorted(q[:,0],(t//M)*M)
 if k>=len(q)or q[k,0]!=(t//M)*M:return out
 if entry<q[k,3]or entry>q[k,2]:out[0]=-2;return out
 width=p[0];unit=p[15]if p[15]>0 else width
 stop=entry*(1-side*width)
 if width<=0 or unit<=0 or stop<=0:out[0]=-4;return out
 for z in range(3):
  if p[4+z]>0 and(p[1+z]<=0 or entry*(1+side*p[1+z])<=0):out[0]=-4;return out
 left=1.;gross=0.;cost=.0002 if p[14]>0 else .00105;hit=0;best=entry;evn=0;be=False;exitcode=0;last=t
 for j in range(k,len(q)):
  ts=q[j,0]
  if ts!=q[k,0]+(j-k)*M:out[0]=-3;return out
  o=q[j,1];hi=q[j,2];lo=q[j,3];cl=q[j,4];kind=0;price=0.;fraction=0.
  if ts>=t+p[11]*H:kind=4;price=o;fraction=left;etime=ts
  else:
   out[9]=max(out[9],side*((hi if side==1 else lo)/entry-1)/unit)
   out[10]=max(out[10],-side*((lo if side==1 else hi)/entry-1)/unit)
   if (side==1 and lo<=stop)or(side==-1 and hi>=stop):
    kind=3 if be and abs(stop-entry*(1+side*p[8]))<1e-9*entry else 5 if p[10]>=0 and hit>=p[10] and abs(stop-entry*(1-side*width))>1e-9*entry else 1;price=min(o,stop)if side==1 else max(o,stop);fraction=left;etime=ts+M
    if hit<3 and p[4+hit]>0 and((side==1 and hi>=entry*(1+side*p[1+hit]))or(side==-1 and lo<=entry*(1+side*p[1+hit]))):out[34]+=1
  if kind:
   gross+=side*(price/entry-1)*fraction;cost+=.00105*price/entry*fraction;off=13+4*evn;out[off]=etime;out[off+1]=price;out[off+2]=fraction;out[off+3]=kind;evn+=1;left=0.;exitcode=kind;last=etime;break
  if j>k:
   while hit<3 and p[4+hit]>0:
    target=entry*(1+side*p[1+hit])
    if not((side==1 and hi>=target)or(side==-1 and lo<=target)):break
    fraction=min(left,p[4+hit]);gross+=side*(target/entry-1)*fraction;cost+=.0002*target/entry*fraction;off=13+4*evn;out[off]=ts+M;out[off+1]=target;out[off+2]=fraction;out[off+3]=2;evn+=1;left=max(0.,left-fraction);hit+=1;last=ts+M
    if left<1e-9:exitcode=2;break
  if left<1e-9:break
  if side==1:best=max(best,hi)
  else:best=min(best,lo)
  if p[7]>0 and hit>=p[7]:
   ns=entry*(1+side*p[8]);stop=max(stop,ns)if side==1 else min(stop,ns);be=True
  if p[10]>=0 and hit>=p[10]:
   ns=best*(1-side*p[9])if p[9]>=0 else best+side*p[9]*entry;stop=max(stop,ns)if side==1 else min(stop,ns)
  if p[12]>0 and hit>=1 and side*(best/entry-1)>=p[13]*width:
   move=side*(best-entry);back=side*(best-cl)
   if move>0 and back/move>=p[12]and j+1<len(q)and q[j+1,0]==ts+M:
    price=q[j+1,1];fraction=left;gross+=side*(price/entry-1)*fraction;cost+=.00105*price/entry*fraction;off=13+4*evn;out[off]=ts+M;out[off+1]=price;out[off+2]=fraction;out[off+3]=6;evn+=1;left=0.;exitcode=6;last=ts+M;break
 if left>1e-9:out[0]=0;return out
 known=False;cursor=t
 for z in range(len(coverage)):
  if coverage[z,0]<=cursor and coverage[z,1]>cursor:cursor=coverage[z,1]
  if cursor>=last:known=True;break
 cash=0.
 if known:
  for z in range(np.searchsorted(ft,t),np.searchsorted(ft,last,side='right')):
   pay=ft[z];rate=fr[z]
   if pay<t or pay>last or(pay==t and side*rate<=0):continue
   remain=1.
   for v in range(evn):
    eventt=out[13+4*v]
    if eventt<pay or(eventt==pay and side*rate<=0):remain-=out[15+4*v]
   qi=np.searchsorted(q[:,0],pay)-1
   if qi<0 or q[qi,0]+M!=pay:known=False;cash=0.;break
   cash+=-side*max(0.,remain)*rate*q[qi,4]/entry
 exposure=0.
 for v in range(evn):exposure+=out[15+4*v]*max(0.,out[13+4*v]-t)/(8*H)
 out[0]=1;out[1]=(gross-cost+cash)/unit;out[2]=gross;out[3]=cost;out[4]=cash;out[5]=int(known);out[6]=0. if known else .0001*exposure/unit;out[7]=last;out[8]=exitcode;out[11]=(last-t)/H;out[12]=evn;out[29]=width;out[30]=unit
 return out

@njit(cache=True)
def path_first(q,t,entry,side,width,hold_h=72):
 if width<=0 or len(q)==0:return -1
 k=np.searchsorted(q[:,0],t//M*M)
 if k>=len(q)or q[k,0]!=t//M*M:return -1
 up=entry*(1+side*width);down=entry*(1-side*width)
 for j in range(k,len(q)):
  if q[j,0]!=q[k,0]+(j-k)*M:return -1
  if q[j,0]>=t+hold_h*H:return 2
  if(side==1 and q[j,3]<=down)or(side==-1 and q[j,2]>=down):return 0
  if(side==1 and q[j,2]>=up)or(side==-1 and q[j,3]<=up):return 1
 return -1
