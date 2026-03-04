"""
Pricing Module
==============

Canonical FRN pricing, risk calculations, and cashflow generation.

This is the SINGLE SOURCE OF TRUTH for all pricing logic.
"""

try:
    from .helpers import get_lookup_dict, get_historical_rate, to_ql_date
    from .cashflows import calculate_compounded_zaronia, generate_frn_cashflows
    from .frn import price_frn, calculate_accrued_interest
    from .risk import calculate_dv01_cs01, calculate_key_rate_dv01, solve_dm
    
    __all__ = [
        'price_frn',
        'calculate_accrued_interest',
        'calculate_dv01_cs01',
        'calculate_key_rate_dv01',
        'solve_dm',
        'calculate_compounded_zaronia',
        'generate_frn_cashflows',
        'get_lookup_dict',
        'get_historical_rate',
        'to_ql_date'
    ]
except ImportError as e:
    import sys
    print(f"Error importing pricing modules: {e}", file=sys.stderr)
    raise
