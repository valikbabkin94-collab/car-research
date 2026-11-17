"""Arithmetic display-unit audit from immutable saved metrics; no candles/backtest/selection."""
import json,subprocess,base64
from pathlib import Path
repo='valikbabkin94-collab/car-research';ref='36067a68c01aba878cc04917d120961b00b289d3'
p='research/paket_20261117/part6_coverage_fix/TABLES.json';d=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/contents/{p}?ref={ref}']));rows=json.loads(base64.b64decode(d['content']));out=[]
for r in rows:
 if r['variant']!='T0S1B0':continue
 factor=.056/.12;wins=round(r['n']*r['WR']/100);losses=r['n']-wins;loss_total=r['netR']/(r['PF']-1)if r['PF']!=1 else None;win_total=loss_total*r['PF']if loss_total is not None else None
 out.append(dict(period=r['period'],n=r['n'],signal_unit_R_price_fraction=.056,model_stop_price_fraction=.12,model_stop_in_signal_R=.12/.056,net_signal_R=r['netR'],USD_at_5_per_signal_R=r['netR']*5,USD_at_5_nominal_model_stop_risk=r['netR']*factor*5,model_stop_risk_R=r['netR']*factor,PF=r['PF'],WR=r['WR'],average_win_signal_R=win_total/wins if wins and win_total is not None else None,average_loss_signal_R=loss_total/losses if losses and loss_total is not None else None))
result=dict(source_commit=ref,source_path=p,selector_unchanged=True,no_new_PnL_runs=True,rows=out,meaning='SignalR5.6% differs from changed stop12%. Old USD_at_5risk column is 5 dollars per SIGNAL R, not fixed5-dollar modelSL risk. Supplementary fixed-stop projection rescales same saved outcomes, not actual LIVE profit or a different parameter winner. Gaps/fees can exceed nominal stop risk; concurrent capital constraints absent. S1=12% is requested counterfactual, not verified actual strategySL. In LIVE export initial_stop is safety, never assumed financial1R.')
p=Path('research/paket_20261117/PF_RISK_UNITS_AUDIT.json');p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
