"""Pure long sizing guard shared by research entry paths; no I/O."""
import math


def long_quantity(entry, stop, risk_usd, fee_buffer=0.0021):
    """Reject invalid/gapped entries before division; never return negative qty.
    ValueError remains active under python -O, unlike a bare assert.
    """
    if not all(math.isfinite(v) for v in (entry, stop, risk_usd, fee_buffer)):
        raise ValueError('NONFINITE_LONG_SIZING_INPUT')
    if entry <= 0 or stop <= 0 or entry <= stop:
        raise ValueError('INVALID_LONG_ENTRY_STOP')
    if risk_usd <= 0 or fee_buffer < 0:
        raise ValueError('INVALID_LONG_RISK')
    qty = risk_usd / (entry - stop + entry * fee_buffer)
    if not math.isfinite(qty) or qty <= 0:
        raise ValueError('INVALID_LONG_QUANTITY')
    return qty
