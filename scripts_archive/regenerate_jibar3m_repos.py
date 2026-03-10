"""
Regenerate Portfolio and Repos with JIBAR 3M Aligned Repo Terms

Requirements:
- Repo term = JIBAR 3M tenor (approximately 90 days)
- Repo end date must be before next coupon date
- Target gearing: 10x
- All notionals in R5M increments
- All repo spreads at 10 bps
"""

import json
import random
import uuid
from datetime import date, timedelta

# Configuration
TARGET_NOTIONAL = 3_000_000_000  # R3B
TARGET_GEARING = 10.0
NOTIONAL_INCREMENT = 5_000_000  # R5M
REPO_SPREAD_BPS = 10  # All repos at 10 bps
JIBAR_3M_DAYS = 90  # JIBAR 3M tenor

# Banks
BANKS = ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec']

# RN Bonds (within 5 year max maturity)
RN_BONDS = {
    'RN2027': {'spread': 130, 'issue': date(2022, 7, 11), 'maturity': date(2027, 7, 11), 'issuer': 'Republic of SA'},
    'RN2030': {'spread': 96, 'issue': date(2023, 4, 17), 'maturity': date(2030, 9, 17), 'issuer': 'Republic of SA'},
}

# Spread options (in bps, multiples of 5)
SPREAD_OPTIONS = [70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150]

TODAY = date.today()
MAX_MATURITY_DATE = TODAY + timedelta(days=int(5 * 365.25))


def get_next_coupon_date(position_start, current_date):
    """Calculate next quarterly coupon date after current_date"""
    current = position_start
    while current <= current_date:
        current = current + timedelta(days=91)
    return current


def generate_portfolio():
    """Generate portfolio with RN bonds and bank FRNs"""
    positions = []
    
    # Add RN bonds (2 positions)
    for bond_name, bond_data in RN_BONDS.items():
        if bond_data['maturity'] <= MAX_MATURITY_DATE:
            # Notional in R5M increments
            notional = random.choice([300_000_000, 500_000_000, 700_000_000])
            
            positions.append({
                'id': f'POS_{uuid.uuid4().hex[:8]}',
                'name': bond_name,
                'counterparty': bond_data['issuer'],
                'book': 'Government',
                'notional': notional,
                'start_date': bond_data['issue'].isoformat(),
                'maturity': bond_data['maturity'].isoformat(),
                'issue_spread': bond_data['spread'],
                'dm': bond_data['spread'],
                'index': 'JIBAR 3M',
                'lookback': 0
            })
    
    # Calculate remaining notional needed
    rn_total = sum(p['notional'] for p in positions)
    remaining = TARGET_NOTIONAL - rn_total
    
    # Generate bank FRNs to reach target
    num_bank_frns = 28
    avg_notional = remaining / num_bank_frns
    
    for i in range(num_bank_frns):
        # Round to nearest R5M
        notional = round(avg_notional / NOTIONAL_INCREMENT) * NOTIONAL_INCREMENT
        
        # Random parameters
        bank = random.choice(BANKS)
        spread = random.choice(SPREAD_OPTIONS)
        
        # Random start date (historical)
        days_back = random.randint(180, 1200)
        start_date = TODAY - timedelta(days=days_back)
        
        # Maturity: 2-5 years from start
        years = random.uniform(2, 5)
        maturity = start_date + timedelta(days=int(years * 365.25))
        
        # Ensure within max maturity
        if maturity > MAX_MATURITY_DATE:
            maturity = MAX_MATURITY_DATE
        
        positions.append({
            'id': f'POS_{uuid.uuid4().hex[:8]}',
            'name': f'{bank} FRN {i+1}',
            'counterparty': bank,
            'book': bank,
            'notional': notional,
            'start_date': start_date.isoformat(),
            'maturity': maturity.isoformat(),
            'issue_spread': spread,
            'dm': spread,
            'index': 'JIBAR 3M',
            'lookback': 0
        })
    
    return positions


def generate_repos(portfolio):
    """Generate repo trades with JIBAR 3M tenor, ending before next coupon"""
    repos = []
    
    total_notional = sum(p['notional'] for p in portfolio)
    target_repo = total_notional * TARGET_GEARING
    
    current_repo = 0
    attempts = 0
    max_attempts = 500  # Increased attempts
    
    # Track repo usage per collateral to allow multiple repos
    collateral_usage = {p['id']: 0 for p in portfolio}
    
    while current_repo < target_repo and attempts < max_attempts:
        attempts += 1
        
        # Select random collateral
        collateral = random.choice(portfolio)
        
        # Allow up to 10x leverage per position (can repo same collateral multiple times)
        max_usage = collateral['notional'] * 10
        if collateral_usage[collateral['id']] >= max_usage:
            continue
        
        # Repo size: larger sizes to reach 10x gearing faster
        # Use 50% to 200% of collateral notional
        base_size = collateral['notional']
        repo_size = random.choice([
            int(base_size * 0.5),
            int(base_size * 0.7),
            int(base_size * 1.0),
            int(base_size * 1.5),
            int(base_size * 2.0)
        ])
        repo_size = round(repo_size / NOTIONAL_INCREMENT) * NOTIONAL_INCREMENT
        
        # Trade date: recent (last 30 days)
        days_back = random.randint(1, 30)
        trade_date = TODAY - timedelta(days=days_back)
        spot_date = trade_date + timedelta(days=2)
        
        # Get next coupon date for this collateral
        coll_start = date.fromisoformat(collateral['start_date'])
        next_coupon = get_next_coupon_date(coll_start, spot_date)
        
        # Repo term = JIBAR 3M (90 days), but must end before next coupon
        max_days_to_coupon = (next_coupon - spot_date).days - 5  # 5 day buffer
        
        if max_days_to_coupon < 7:
            continue  # Skip if too close to coupon
        
        # Use JIBAR 3M tenor (90 days) or max to coupon, whichever is smaller
        repo_days = min(JIBAR_3M_DAYS, max_days_to_coupon)
        end_date = spot_date + timedelta(days=repo_days)
        
        # Create repo
        repo = {
            'id': f'REPO_{uuid.uuid4().hex[:8]}',
            'trade_date': trade_date.isoformat(),
            'spot_date': spot_date.isoformat(),
            'end_date': end_date.isoformat(),
            'cash_amount': repo_size,
            'repo_spread_bps': REPO_SPREAD_BPS,
            'direction': 'borrow_cash',
            'collateral_id': collateral['id'],
            'coupon_to_lender': False
        }
        
        repos.append(repo)
        current_repo += repo_size
        collateral_usage[collateral['id']] += repo_size
    
    actual_gearing = current_repo / total_notional if total_notional > 0 else 0
    
    print(f"\nGenerated {len(repos)} repos")
    print(f"Total Repo Outstanding: R{current_repo/1e9:.2f}B")
    print(f"Actual Gearing: {actual_gearing:.2f}x")
    
    return repos


def main():
    print("="*70)
    print("Regenerating Portfolio with JIBAR 3M Aligned Repos")
    print("="*70)
    
    # Generate portfolio
    portfolio = generate_portfolio()
    total_notional = sum(p['notional'] for p in portfolio)
    
    print(f"\nPortfolio:")
    print(f"  Positions: {len(portfolio)}")
    print(f"  Total Notional: R{total_notional/1e9:.2f}B")
    
    # Generate repos
    repos = generate_repos(portfolio)
    
    # Save
    with open('portfolio.json', 'w') as f:
        json.dump({'positions': portfolio}, f, indent=2)
    print("\n✅ Saved portfolio.json")
    
    with open('repo_trades.json', 'w') as f:
        json.dump({'trades': repos}, f, indent=2)
    print("✅ Saved repo_trades.json")
    
    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
