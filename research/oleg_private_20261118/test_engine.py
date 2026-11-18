import numpy as np
from engine import simulate,M,H
from policies import plan,entry_start,translated_control

def quotes():return np.column_stack([np.arange(10)*M,np.full((10,4),100.)])
def p(**kw):return dict(symbol='XUSDT',signal_ms=0,observed_ms=0,entry_type='MARKET',side=1,stop_fraction=.1,tp_dist=[.1],weights=[1.],move_be=False,hold_hours=72,**kw)
def test_author_open_exit_precedes_later_intraminute_stop():
 q=quotes();q[2,3]=80;r=simulate(q,p(author_events=[dict(kind='CLOSE_ALL',effective_ms=2*M,post_key='a')]),10*M);assert r['events'][0]['kind']=='AUTHOR_CLOSE'
def test_gap_protection_precedes_author_close():
 q=quotes();q[2,1]=80;q[2,3]=79;r=simulate(q,p(author_events=[dict(kind='CLOSE_ALL',effective_ms=2*M,post_key='a')]),10*M);assert r['events'][0]['kind']=='SL'
def test_entry_candle_tp_not_allowed():
 q=quotes();q[1,2]=120;r=simulate(q,p(),10*M);assert r['status']!='CLOSED'
def test_absolute_targets_and_taker_every_fill():
 q=quotes();q[2,2]=111;r=simulate(q,p(absolute_targets=[110]),10*M);assert r['status']=='CLOSED';assert abs(r['execution_cost_R']-(.00105+.00055*1.1)/.1)<1e-10
 defignore=0
def test_o4_needs_second_target():
 s=dict(channel='OLEG',available_ms=0,pub=0,side='LONG',symbol='XUSDT',stop=90,stop_percent=None,targets=[110],events=[],entry_zone=[99,101]);r,e=plan(s,'O4',quotes());assert e=='MISSING_SECOND_AUTHOR_TARGET'
def test_o3_is_midpoint12h():
 s=dict(channel='OLEG',available_ms=0,pub=0,side='LONG',symbol='XUSDT',stop=90,stop_percent=None,targets=[110,120],events=[],entry_zone=[98,100]);r,e=plan(s,'O3',quotes());assert r['limit']==99 and r['ttl_hours']==12
 defignore=0

def test_funding_string_values_are_normalized_before_cash_math():
 from run import normalize_funding_rows
 x=normalize_funding_rows([dict(ts='2',rate='-0.0001'),dict(ts='1',rate='0.0002')]);assert x[0]['ts']==1 and x[0]['rate']==.0002 and x[1]['rate']==-.0001
def test_structured_be_is_source_entry_without_fee_offset():
 s=dict(channel='C',kind='STRUCTURED',available_ms=0,pub=0,side='LONG',symbol='XUSDT',stop=90,stop_percent=None,targets=[110,120],events=[],entry_zone=None);r,e=plan(s,'P2',quotes());assert r['be_offset']==0
 defignore=0
def test_original_all_author_target_gate_rejects_stale_first_even_if_final_ahead():
 q=quotes();r=simulate(q,p(absolute_targets=[120],all_author_targets=[99,120]),10*M);assert r['status']=='REJECTED_INVALID_TARGETS'
def test_side_filter_does_not_count_opposite_side_as_price_gap():
 s=dict(channel='OLEG',side='LONG',stop=90,stop_percent=None,targets=[110,120],entry_zone=[99,100]);p,e=plan(s,'O1',np.empty((0,5)));assert e=='DIRECTION_FILTER_LONG'
def test_nonapplicable_cohort_does_not_become_price_gap():
 s=dict(channel='C',side='LONG',kind='TEXT');p,e=plan(s,'P2',np.empty((0,5)));assert e=='NOT_APPLICABLE_TEXT_COHORT'
