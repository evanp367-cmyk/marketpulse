from math import sqrt
from typing import Sequence

def _valid(values: Sequence[float]):
    vals=[float(x) for x in values]
    if any(not (x == x and abs(x) != float("inf")) for x in vals): raise ValueError("Indicator input contains non-finite values")
    return vals
def sma(values: Sequence[float], period: int) -> list[float | None]:
    v=_valid(values)
    if period<1: raise ValueError("period must be >= 1")
    return [None if i+1<period else sum(v[i+1-period:i+1])/period for i in range(len(v))]
def ema(values: Sequence[float], period: int) -> list[float | None]:
    v=_valid(values)
    if period<1: raise ValueError("period must be >= 1")
    out=[None]*len(v)
    if len(v)<period:return out
    current=sum(v[:period])/period; out[period-1]=current; alpha=2/(period+1)
    for i in range(period,len(v)):
        current=v[i]*alpha+current*(1-alpha);out[i]=current
    return out
def rsi(values: Sequence[float], period: int=14) -> list[float | None]:
    v=_valid(values)
    if period<1: raise ValueError("period must be >= 1")
    out=[None]*len(v)
    if len(v)<=period:return out
    gains=[max(v[i]-v[i-1],0) for i in range(1,len(v))]; losses=[max(v[i-1]-v[i],0) for i in range(1,len(v))]
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    def score(avg_gain: float, avg_loss: float) -> float:
        # A perfectly flat series has no directional strength; use neutral RSI.
        if avg_gain == 0 and avg_loss == 0:
            return 50.0
        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0
        return 100 - 100 / (1 + avg_gain / avg_loss)
    out[period]=score(ag, al)
    for i in range(period+1,len(v)):
        ag=(ag*(period-1)+gains[i-1])/period;al=(al*(period-1)+losses[i-1])/period
        out[i]=score(ag, al)
    return out
def macd(values: Sequence[float], fast: int=12, slow: int=26, signal: int=9):
    if fast>=slow: raise ValueError("fast period must be less than slow period")
    a=ema(values,fast);b=ema(values,slow);line=[None if x is None or y is None else x-y for x,y in zip(a,b)]
    start=next((i for i,x in enumerate(line) if x is not None),len(line)); valid=[x for x in line[start:] if x is not None]
    sig=ema(valid,signal); signal_line=[None]*start+sig
    hist=[None if x is None or y is None else x-y for x,y in zip(line,signal_line)]
    return {"macd":line,"signal":signal_line,"histogram":hist}
def bollinger(values: Sequence[float], period: int=20, deviations: float=2.0):
    if period < 1:
        raise ValueError("period must be >= 1")
    if not (deviations >= 0 and deviations < float("inf")):
        raise ValueError("deviations must be finite and >= 0")
    v=_valid(values); mid=sma(v,period); upper=[];lower=[]
    for i,m in enumerate(mid):
        if m is None: upper.append(None);lower.append(None);continue
        sd=sqrt(sum((x-m)**2 for x in v[i+1-period:i+1])/period);upper.append(m+deviations*sd);lower.append(m-deviations*sd)
    return {"middle":mid,"upper":upper,"lower":lower}
def atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int=14):
    if period < 1:
        raise ValueError("period must be >= 1")
    h,l,c=map(_valid,(high,low,close))
    if not(len(h)==len(l)==len(c)):raise ValueError("high, low and close lengths differ")
    tr=[]
    for i in range(len(c)):tr.append(h[i]-l[i] if i==0 else max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])))
    return ema(tr,period)
