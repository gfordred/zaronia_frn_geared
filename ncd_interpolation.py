"""
NCD Pricing Interpolation Logic for FRN Valuation

This module provides functions to interpolate FRN trading spreads from NCD pricing data.

LOGIC:
1. Load NCD pricing for valuation date (from ncd_pricing.json)
2. Determine FRN maturity bucket (years to maturity)
3. Interpolate spread from NCD curve for the FRN's counterparty/issuer
4. Apply interpolation method:
   - Linear interpolation between two nearest tenors
   - Extrapolation if outside range (flat extrapolation)

EXAMPLE:
FRN: ABSA, 2.5 years to maturity
NCD Pricing: ABSA 2Y = 70bps, ABSA 3Y = 85bps
Interpolated Spread = 70 + (85-70) * (2.5-2)/(3-2) = 70 + 7.5 = 77.5 bps

This spread is then used as the DM (discount margin) for FRN valuation.
"""

import json
from datetime import date
import numpy as np


def load_ncd_pricing_for_date(ncd_file, valuation_date):
    """
    Load NCD pricing data for a specific valuation date.
    
    Args:
        ncd_file: Path to ncd_pricing.json
        valuation_date: date object or ISO string
        
    Returns:
        dict: {bank: {tenor: spread_bps}}
    """
    with open(ncd_file, 'r', encoding='utf-8') as f:
        ncd_data = json.load(f)
    
    # Convert valuation_date to string if needed
    if isinstance(valuation_date, date):
        val_date_str = valuation_date.isoformat()
    else:
        val_date_str = str(valuation_date)
    
    # Try to get historical pricing for exact date
    historical = ncd_data.get('historical_pricing', {})
    
    if val_date_str in historical:
        return historical[val_date_str]
    
    # Fallback: find nearest date
    available_dates = sorted(historical.keys())
    if available_dates:
        # Find closest date
        nearest = min(available_dates, key=lambda d: abs((date.fromisoformat(d) - date.fromisoformat(val_date_str)).days))
        return historical[nearest]
    
    # Ultimate fallback: use current/default pricing
    return ncd_data.get('banks', {})


def parse_tenor_to_years(tenor_str):
    """
    Convert tenor string to years.
    
    Examples:
        "1Y" -> 1.0
        "1.5Y" -> 1.5
        "2Y" -> 2.0
    """
    return float(tenor_str.replace('Y', ''))


def interpolate_ncd_spread(bank, years_to_maturity, ncd_pricing):
    """
    Interpolate NCD spread for a given bank and maturity.
    
    Args:
        bank: Bank name (e.g., "ABSA", "Standard Bank")
        years_to_maturity: Float, years to FRN maturity
        ncd_pricing: dict from load_ncd_pricing_for_date
        
    Returns:
        tuple: (interpolated_spread_bps, calculation_steps)
    """
    if bank not in ncd_pricing:
        # Fallback: use average of all banks
        all_spreads = []
        for b in ncd_pricing.values():
            all_spreads.extend(b.values())
        if all_spreads:
            avg_spread = np.mean(all_spreads)
            return avg_spread, f"Bank '{bank}' not found. Using market average: {avg_spread:.2f} bps"
        else:
            return 100.0, f"No NCD pricing available. Using default: 100 bps"
    
    bank_curve = ncd_pricing[bank]
    
    # Parse tenors and create sorted arrays
    tenors = []
    spreads = []
    for tenor_str, spread in bank_curve.items():
        tenors.append(parse_tenor_to_years(tenor_str))
        spreads.append(spread)
    
    # Sort by tenor
    sorted_pairs = sorted(zip(tenors, spreads))
    tenors = [t for t, s in sorted_pairs]
    spreads = [s for t, s in sorted_pairs]
    
    # Interpolation logic
    steps = []
    steps.append(f"Bank: {bank}")
    steps.append(f"Years to Maturity: {years_to_maturity:.2f}")
    steps.append(f"Available NCD Tenors: {', '.join([f'{t}Y={s}bps' for t, s in zip(tenors, spreads)])}")
    
    # Check if exact match
    if years_to_maturity in tenors:
        idx = tenors.index(years_to_maturity)
        spread = spreads[idx]
        steps.append(f"Exact match found: {years_to_maturity}Y = {spread} bps")
        return spread, "\n".join(steps)
    
    # Check if below minimum (flat extrapolation)
    if years_to_maturity < tenors[0]:
        spread = spreads[0]
        steps.append(f"Below minimum tenor. Using flat extrapolation: {tenors[0]}Y = {spread} bps")
        return spread, "\n".join(steps)
    
    # Check if above maximum (flat extrapolation)
    if years_to_maturity > tenors[-1]:
        spread = spreads[-1]
        steps.append(f"Above maximum tenor. Using flat extrapolation: {tenors[-1]}Y = {spread} bps")
        return spread, "\n".join(steps)
    
    # Linear interpolation between two nearest points
    for i in range(len(tenors) - 1):
        if tenors[i] < years_to_maturity <= tenors[i+1]:
            t1, s1 = tenors[i], spreads[i]
            t2, s2 = tenors[i+1], spreads[i+1]
            
            # Linear interpolation formula
            weight = (years_to_maturity - t1) / (t2 - t1)
            spread = s1 + (s2 - s1) * weight
            
            steps.append(f"Interpolating between {t1}Y ({s1}bps) and {t2}Y ({s2}bps)")
            steps.append(f"Weight = ({years_to_maturity:.2f} - {t1}) / ({t2} - {t1}) = {weight:.4f}")
            steps.append(f"Spread = {s1} + ({s2} - {s1}) × {weight:.4f} = {spread:.2f} bps")
            
            return spread, "\n".join(steps)
    
    # Fallback (should not reach here)
    avg_spread = np.mean(spreads)
    steps.append(f"Interpolation failed. Using average: {avg_spread:.2f} bps")
    return avg_spread, "\n".join(steps)


def get_frn_valuation_spread(frn_position, valuation_date, ncd_file='ncd_pricing.json'):
    """
    Get the valuation spread for an FRN position using NCD pricing.
    
    Args:
        frn_position: dict with 'counterparty', 'maturity' keys
        valuation_date: date object
        ncd_file: path to NCD pricing file
        
    Returns:
        tuple: (spread_bps, calculation_details)
    """
    # Load NCD pricing for valuation date
    ncd_pricing = load_ncd_pricing_for_date(ncd_file, valuation_date)
    
    # Calculate years to maturity
    maturity = frn_position['maturity']
    if isinstance(maturity, str):
        from datetime import datetime
        maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
    
    days_to_mat = (maturity - valuation_date).days
    years_to_mat = days_to_mat / 365.25
    
    # Get counterparty/issuer
    counterparty = frn_position.get('counterparty', 'Unknown')
    
    # Map counterparty to NCD bank name if needed
    # (e.g., "FirstRand" might need to map to "FirstRand" in NCD pricing)
    bank_mapping = {
        'ABSA': 'ABSA',
        'Standard Bank': 'Standard Bank',
        'Nedbank': 'Nedbank',
        'FirstRand': 'FirstRand',
        'Investec': 'Investec',
        'Capitec': 'Capitec',
        'RMBH': 'FirstRand',  # Rand Merchant Bank is part of FirstRand
    }
    
    bank = bank_mapping.get(counterparty, counterparty)
    
    # Interpolate spread
    spread, steps = interpolate_ncd_spread(bank, years_to_mat, ncd_pricing)
    
    return spread, steps


# Example usage and testing
if __name__ == "__main__":
    # Test interpolation
    test_ncd_pricing = {
        'ABSA': {
            '1Y': 50,
            '1.5Y': 60,
            '2Y': 70,
            '3Y': 85,
            '4Y': 95,
            '5Y': 110
        }
    }
    
    # Test cases
    test_cases = [
        (1.0, "Exact match at 1Y"),
        (1.25, "Between 1Y and 1.5Y"),
        (2.5, "Between 2Y and 3Y"),
        (0.5, "Below minimum (extrapolate)"),
        (6.0, "Above maximum (extrapolate)"),
    ]
    
    print("NCD Spread Interpolation Tests")
    print("=" * 60)
    
    for years, description in test_cases:
        spread, steps = interpolate_ncd_spread('ABSA', years, test_ncd_pricing)
        print(f"\n{description}:")
        print(steps)
        print(f"Result: {spread:.2f} bps")
        print("-" * 60)
