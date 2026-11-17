import numpy as np
from minute_engine import *
def fixture():
 q=np.column_stack([np.arange(4320)*M,np.full((4320,4),100.)]);q[:,2]=100.5;q[:,3]=99.5;r=dict(status='CLOSED',entry_ms=0,entry=100.);return q,r
def test_tp_after_limit_later_in_same_hour():
 q,r=fixture();q[5,2]=107;q[5,3]=100.1;q[5,1]=101.;q[5,4]=106.;v=replay(q,r);assert v['events'][0]['kind']=='TP1';assert v['events'][2]['kind']=='TP3';assert v['exit_ms']==6*M
 defignore=0
def test_high_before_fill_does_not_count():
 q,r=fixture();q[:10,1:]=101.;q[1,2]=110.;q[10,3]=99.5;v=replay(q,r);assert v['entry_ms']==10*M and all(e['kind']=='TIME'for e in v['events'])
def test_entry_minute_high_is_ambiguous():
 q,r=fixture();q[0,2]=107;v=replay(q,r);assert v['entry_minute_TP_ambiguous'];assert all(e['kind']=='TIME'for e in v['events'])
def test_same_minute_stop_first():
 q,r=fixture();q[4,2]=110;q[4,3]=90;v=replay(q,r);assert v['events'][0]['kind']=='SL'and v['R']<-0.99
 defignore=0
def test_new_be_bound_and_secondary():
 q,r=fixture();q[5,2]=105;v=replay(q,r);assert v['new_BE_same_minute_ambiguous'];assert v['events'][1]['kind']=='BE_SAME_MINUTE_BOUND'
 a=replay(q,r,delayed_new_BE=True);assert a['R']>=v['R']
def test_gap_is_not_filled_synthetically():
 q,r=fixture();assert replay(np.delete(q,20,axis=0),r)['status']=='DATA_GAP_MINUTES'
def test_original_price_not_reachable_is_gap():
 q,r=fixture();q[:,1:]=110.;assert replay(q,r)['status']=='DATA_GAP_ORIGINAL_ENTRY_PRICE_NOT_REACHED'
def test_unchanged_flat_cost_and_r():
 q,r=fixture();v=replay(q,r);assert abs(v['R']+COST/DEN)<1e-12
