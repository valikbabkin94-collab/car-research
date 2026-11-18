from parser import *
def row(t,n=1,**kw):return dict(id=n,date=1700000000+n,text=t,**kw)
def test_oleg_card_levels_and_risk():
 p=parse_one('OLEG',row('#JCT/USDT SHORT\nДиапазон входа: 0.002130-0.002055$\nTP: 0.001951$, 0.001733$\nSL:0.002442$\nРиск:1%'))
 assert p['label']=='SIGNAL'and p['kind']=='STRUCTURED';assert p['entry_zone']==[.002055,.00213];assert p['targets']==[.001951,.001733];assert p['risk_signature_pct']==1
 defignore=0
def test_entry_targets_not_takeprofits():
 p=parse_one('C',row('BTC/USDT Long\nEntry Targets:\n1)100\nTake-Profit Targets:\n1)110\n2)120\nStop Loss:90'))
 assert p['entry_zone']==[100,100]and p['targets']==[110,120]
def test_edited_snapshot_not_available_at_original_date():
 p=parse_one('OLEG',row('#Q/USDT SHORT\nEntry:10-11\nTP:8,7\nSL:12',edit_date=1700001000));assert p['available_ms']==1700001000000
 defignore=0
def test_report_is_not_fresh_signal():
 p=parse_one('C',row('COIN:BTCUSDT\nDirection:LONG\nSTOP LOSS:90\nProfit:63%\nclosed'));assert p['label']=='REPORT'
def test_tp_report_is_not_exit_command():
 p=parse_one('C',row('#BTC target1 reached +22%'));assert not p['actions']
def test_partial_requires_explicit_fraction():
 assert parse_one('C',row('#BTC фиксирую часть'))['actions'][0]['kind']=='UNRESOLVED_FRACTION'
 assert parse_one('C',row('#BTC фиксирую половину'))['actions'][0]['fraction']==.5
 defignore=0
def test_reply_chain_links_without_coin_but_only_past():
 a=row('#Q/USDT SHORT\nДиапазон входа:10-11\nTP:8,7\nSL:12');b=row('вышел в мелкий плюс',2,reply_to=1);s,c,st,r=build('OLEG',[a,b]);assert len(s)==1 and s[0]['events'][0]['kind']=='CLOSE_ALL'
def test_multicoin_is_ambiguous():
 p=parse_one('C',row('#BTC #ETH беру лонг'));assert p['symbol']is None
 defignore=0
def test_short_term_analytics_not_trade():
 p=parse_one('C',row('#BTC Short-Term Trend Downgrade. entry analysis'));assert p['label']=='OTHER'
def test_no_raw_text_in_public_output():
 s,c,st,r=build('OLEG',[row('#Q/USDT SHORT\nДиапазон входа:10-11\nTP:8,7\nSL:12')]);assert 'text'not in s[0]and'text'not in r[0]
