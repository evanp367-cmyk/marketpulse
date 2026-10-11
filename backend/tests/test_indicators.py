import pytest
from backend.app.indicators.calculations import sma, ema, rsi, macd, bollinger, atr

def test_sma_known_values(): assert sma([1,2,3,4],3)==[None,None,2.0,3.0]
def test_ema_warmup_and_seed(): assert ema([1,2,3],2)==[None,1.5,2.5]
def test_rsi_monotonic_rise(): assert rsi([1,2,3,4],2)[-1]==100.0
def test_macd_length(): assert len(macd(list(range(40)))['histogram'])==40
def test_bollinger_order():
    b=bollinger([1,2,3,4,5],3);assert b['lower'][-1] < b['middle'][-1] < b['upper'][-1]
def test_atr_length(): assert len(atr([2,3,4],[1,2,3],[1.5,2.5,3.5],2))==3
def test_invalid_period():
    with pytest.raises(ValueError):sma([1,2],0)


def test_rsi_flat_series_is_neutral():
    assert rsi([5, 5, 5, 5, 5], 2)[-1] == 50.0

def test_rsi_monotonic_fall_is_zero():
    assert rsi([5, 4, 3, 2, 1], 2)[-1] == 0.0

def test_bollinger_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        bollinger([1, 2, 3], 0)
    with pytest.raises(ValueError):
        bollinger([1, 2, 3], 2, -1)

def test_atr_rejects_invalid_period():
    with pytest.raises(ValueError):
        atr([2, 3], [1, 2], [1.5, 2.5], 0)


def test_bollinger_rejects_non_finite_deviations():
    with pytest.raises(ValueError):
        bollinger([1, 2, 3], 2, float('inf'))
