"""Conservative instruction extraction; reports never prove market execution."""
import re
NUMBER=r'(?:\d+(?:\.\d+)?)'
def actions(text):
 t=text.lower();out=[]
 claim=bool(re.search(r'(?i)(?:\btp\s*\d*\s*(?:hit|reached|achieved)|target.{0,25}(?:hit|reached)|тейк.{0,20}(?:достиг|взят)|цель.{0,20}достиг)',text))
 if claim:out.append(dict(kind='TP_REACHED_CLAIM'))
 close=bool(re.search(r'\bclose\b|\bclosing\b|закрываем|закрывайте|фиксируем|выходим',t))
 if close:
  half=bool(re.search(r'\bhalf\b|половин',t));percent=re.search(r'(?:close|closing|закрываем|фиксируем).{0,40}?(\d+(?:\.\d+)?)\s*%',t)
  if half:out.append(dict(kind='CLOSE_PART',fraction=.5))
  elif percent:
   f=float(percent[1])/100
   out.append(dict(kind='CLOSE_ALL')if f==1 else dict(kind='CLOSE_PART',fraction=f)if 0<f<1 else dict(kind='UNRESOLVED_FRACTION'))
  elif re.search(r'\ball\b|\bfull(?:y)?\b|всю|полностью|выходим',t):out.append(dict(kind='CLOSE_ALL'))
  else:out.append(dict(kind='UNRESOLVED_FRACTION'))
 be=re.search(r'(?:stop(?:.?loss)?|\bsl\b|стоп).{0,40}(?:break.?even|\bentry\b|\bbe\b|безубыт|\bб[у/е]\b)',t)
 if be:out.append(dict(kind='MOVE_BE'))
 else:
  st=re.search(r'(?:move|set|adjust|переносим|перенесите|ставим).{0,30}(?:stop(?:.?loss)?|\bsl\b|стоп).{0,12}?(?:to|at|на|:|=)\s*\$?('+NUMBER+r')',t)
  if st:out.append(dict(kind='MOVE_STOP',price=float(st[1])))
 if re.search(r'\bcancel\b.{0,20}(?:signal|order|trade|entry)|отменяем.{0,20}(?:сигнал|заявк|вход)',t):out.append(dict(kind='CANCEL_PENDING'))
 if re.search(r'(?:enter|entry|buy|sell|вход|входим).{0,20}(?:market|по рынку)',t):out.append(dict(kind='MARKET_ENTRY_INSTRUCTION'))
 return out
