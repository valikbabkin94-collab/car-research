import numpy as np
from types import SimpleNamespace
from hedge import *
def event(t=2*F,frac=1,kind=2):
 r=np.zeros(40);r[0]=1;r[7]=t;r[12]=1;r[13:17]=[t,90,frac,kind];r[31]=0;r[32]=100;r[2]=.1;r[1]=1;return r
def data():
 d=SimpleNamespace(times=np.arange(0,10*F,F),q=np.full((1,10),100.),index={'X':0},unknown=np.zeros((1,10),int),missing=np.zeros((1,10),int),fc=np.zeros((1,10)),sy=['BTCUSDT']);d.ix=lambda t:int(t//F);d.basket=lambda t,k,s:[0];d.rawfund=[(np.array([]),np.array([0.]),np.array([0.]),np.array([0]))];return d
def test_flat_before_hedge():
 r=event(F);a,ev=schedule({'entry_ms':0},r);assert a==F and ev==[];assert evaluate(data(),{'entry_ms':0,'symbol':'X'},r,'BTC')['n_members']==0
def test_time_exit_open_maps_next_close():
 assert schedule({'entry_ms':0},event(2*F,kind=4))[1]==[(3*F,1)]
def test_partial_same_entry_bucket_not_hedged_retroactively():
 r=event();r[12]=2;r[13:17]=[F,90,.5,2];r[17:21]=[2*F,90,.5,2];assert schedule({'entry_ms':0},r)[1]==[(2*F,.5)]
def test_long_cost_four_leg_cash_identity_and_scale():
 d=data();d.q[0,2]=110;r=evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'BTC');assert abs(r['long_gross_R']-.1/R)<1e-10;assert abs(r['long_fee_R']-.00105*2.1/R)<1e-10
 a=scaled(r,.5);b=scaled(r,1);assert abs(a['long_R']*2-b['long_R'])<1e-10;assert b['netR']==b['short_R']+b['long_R'];assert abs(b['short_fee_R']-.00105*1.9/R)<1e-10
def test_positive_funding_paid_by_long():
 d=data();d.fc[0,2]=.2;v=evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'BTC');assert abs(v['long_funding_R']+.002/R)<1e-10
 d.fc[0,2]=-.2;assert evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'BTC')['long_funding_R']>0
def test_missing_held_price_is_gap():
 d=data();d.q[0,2]=np.nan;assert evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'BTC')['status']=='HELD_HEDGE_PRICE_DATA_GAP'
def test_missing_basket_not_zero_profit():
 d=data();d.basket=lambda *a:None;assert evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'ALT')['status']=='HEDGE_BASKET_DATA_GAP'
def test_pump_small_cohort_explicit_nohedge():
 d=data();d.basket=lambda *a:[];assert evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'PUMP')['no_hedge_reason']=='PUMP_COHORT_LT3'
def test_bh_family_six():
 assert len(bh([.01,.02,.04,.2,.4,.8]))==6;assert abs(bh([.01,.02,.04,.2,.4,.8])[0]-.06)<1e-12
def test_short_gaps_not_counted_as_missing_hedge_coverage():
 d=data();r=scaled(evaluate(d,{'entry_ms':0,'symbol':'X'},event(),'BTC'),1);m=metrics([r,{'status':'SHORT_DATA_GAP'}]);assert m['coverage']==1 and m['overall_coverage']==.5
