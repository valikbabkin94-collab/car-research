import sys,importlib.util,numpy as np
from pathlib import Path
import os
prior=os.environ.get('PRIOR_ENGINE_ROOT','inputs_v1');sys.path.insert(0,prior)
from lab.common import Market,model
from lab.engine import H,M
spec=importlib.util.spec_from_file_location('prior_engine',str(Path(prior)/'engine_v1_1.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class FixtureMarket:
 def __init__(self,q):self.q=q;self.hour=Market.hours(q)
 def get(self,sy):return self.q
 def atr(self,t):return Market.atr(self,t)
 def funding(self,sy):return np.array([],float),np.array([],float),np.empty((0,2))
fail=[];n=0
for seed in range(5):
 rng=np.random.default_rng(seed);nbar=24*60*5;op=100*np.exp(np.r_[0,np.cumsum(rng.normal(0,.001,nbar-1))]);cl=np.r_[op[1:],op[-1]];hi=np.maximum(op,cl)*(1+rng.uniform(0,.0005,nbar));lo=np.minimum(op,cl)*(1-rng.uniform(0,.0005,nbar));q=np.column_stack([np.arange(nbar)*M,op,hi,lo,cl]);m=FixtureMarket(q)
 for side in[-1,1]:
  for code in['X'+str(i)for i in range(1,10)]:
   e=dict(key='0'*64,scenario='TEST',symbol='SYNTHETIC_UNIT_FIXTURE',side=side,entry_ms=24*H,signal_ms=24*H,entry=float(op[24*60]),entry_type='MARKET');a=v.simulate(q,e,code);b=model(m,e,code)
   n+=1
   if a['status']=='CLOSED'and b[0]==1:
    if abs(a['price_R']-b[1])>1e-8 or a['exit_ms']!=b[7]:fail.append(dict(seed=seed,side=side,code=code,oldR=a['price_R'],newR=b[1],oldExit=a['exit_ms'],newExit=b[7]))
   elif (a['status']=='CLOSED')!=(b[0]==1):fail.append(dict(seed=seed,side=side,code=code,old=a['status'],new=b[0]))
print('SYNTHETIC_PARITY',n,'cases',len(fail),'mismatches');print(fail[:5]);assert not fail
