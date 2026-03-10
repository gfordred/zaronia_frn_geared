"""
Regenerate Seed Portfolio with RN FRNs and Coupon-Aligned Repos
- Includes RN2027, RN2030, RN2032, RN2035 (within 5 years)
- Max maturity: 5 years from today
- Each repo linked to asset and expires before next coupon date
- Maintains 10x gearing
"""

import json
import random
from datetime import date, timedelta
import uuid

# Configuration
NUM_POSITIONS = 30  # Increased to include RN bonds
TARGET_TOTAL_NOTIONAL = 3_000_000_000  # R3 billion (increased for RN bonds)
GEARING_RATIO = 10.0
TARGET_REPO_OUTSTANDING = TARGET_TOTAL_NOTIONAL * GEARING_RATIO
NOTIONAL_INCREMENT = 5_000_000  # Round to nearest R5M

# Banks
BANKS = ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec']
BOOKS = ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec']

# RN Bonds (from INSTRUMENTS in app.py)
RN_BONDS = {
    'RN2027': {'spread': 130, 'issue': date(2022, 7, 11), 'maturity': date(2027, 7, 11), 'issuer': 'Republic of SA'},
    'RN2030': {'spread': 96, 'issue': date(2023, 4, 17), 'maturity': date(2030, 9, 17), 'issuer': 'Republic of SA'},
    'RN2032': {'spread': 147, 'issue': date(2025, 4, 7), 'maturity': date(2032, 3, 31), 'issuer': 'Republic of SA'},
    'RN2035': {'spread': 130, 'issue': date(2025, 8, 11), 'maturity': date(2035, 9, 30), 'issuer': 'Republic of SA'},
}

# Spread ranges
SPREAD_OPTIONS = [70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150]
REPO_SPREAD_BPS = 10  # All repos at JIBAR3M + 10bps

TODAY = date.today()
MAX_MATURITY_DATE = TODAY + timedelta(days=int(5 * 365.25))  # 5 years max


def get_next_coupon_date(position_start, current_date):
    """Calculate next quarterly coupon date after current_date"""
    # Coupons are quarterly from start date
    current = position_start
    while current <= current_date:
        current = current + timedelta(days=91)  # Approximately 3 months
    return current


def generate_portfolio():
    """Generate portfolio including RN bonds and bank FRNs"""
    positions = []
    
    # Add RN bonds (only those within 5 years)
    for rn_name, rn_data in RN_BONDS.items():
        if rn_data['maturity'] <= MAX_MATURITY_DATE:
            # Determine notional based on bond (rounded to nearest 5M)
            if rn_name == 'RN2027':
                notional = 500_000_000  # R500M (already multiple of 5M)
            elif rn_name == 'RN2030':
                notional = 300_000_000  # R300M (already multiple of 5M)
            else:
                continue  # Skip RN2032 and RN2035 (too far out)
            
            position = {
                'id': f'POS_{uuid.uuid4().hex[:8]}',
                'name': rn_name,
                'counterparty': rn_data['issuer'],
                'book': 'Government',
                'notional': notional,
                'start_date': rn_data['issue'].isoformat(),
                'maturity': rn_data['maturity'].isoformat(),
                'issue_spread': rn_data['spread'],
                'dm': rn_data['spread'],
                'index': 'JIBAR 3M',
                'lookback': 0
            }
            positions.append(position)
    
    # Calculate remaining notional for bank FRNs
    rn_total = sum(p['notional'] for p in positions)
    remaining_notional = TARGET_TOTAL_NOTIONAL - rn_total
    num_bank_frns = NUM_POSITIONS - len(positions)
    
    # Round to nearest 5M
    notional_per_frn = remaining_notional / num_bank_frns if num_bank_frns > 0 else 0
    notional_per_frn = round(notional_per_frn / NOTIONAL_INCREMENT) * NOTIONAL_INCREMENT
    
    # Add bank FRNs
    for i in range(num_bank_frns):
        bank_idx = i % len(BANKS)
        bank = BANKS[bank_idx]
        book = BOOKS[bank_idx]
        
        # Random maturity within 5 years
        years = random.uniform(1.5, 5.0)
        start_date = TODAY - timedelta(days=random.randint(30, 365))
        maturity = start_date + timedelta(days=int(years * 365.25))
        
        # Ensure within 5 year limit
        if maturity > MAX_MATURITY_DATE:
            maturity = MAX_MATURITY_DATE
        
        # Random spread
        issue_spread = random.choice(SPREAD_OPTIONS)
        dm = random.choice(SPREAD_OPTIONS)
        
        position = {
            'id': f'POS_{uuid.uuid4().hex[:8]}',
            'name': f'{bank}_FRN_{maturity.year}',
            'counterparty': bank,
            'book': book,
            'notional': notional_per_frn,
            'start_date': start_date.isoformat(),
            'maturity': maturity.isoformat(),
            'issue_spread': issue_spread,
            'dm': dm,
            'index': 'JIBAR 3M',
            'lookback': 0
        }
        positions.append(position)
    
    return positions


def generate_repos_aligned_to_coupons(portfolio):
    """Generate repos linked to assets, expiring before next coupon"""
    repos = []
    
    # Repo sizes (all multiples of 5M) - weighted towards larger sizes for 10x gearing
    repo_sizes = [50_000_000, 75_000_000, 100_000_000, 150_000_000, 200_000_000, 
                  250_000_000, 500_000_000, 750_000_000, 1_000_000_000]
    
    total_repo_so_far = 0
    base_date = TODAY - timedelta(days=30)  # Start repos 30 days ago
    
    # Create multiple repos per position to reach target
    position_cycle = 0
    skip_count = 0
    max_skips = len(portfolio) * 3  # Allow skipping but not too much
    
    while total_repo_so_far < TARGET_REPO_OUTSTANDING:
        # Cycle through positions for collateral
        collateral = portfolio[position_cycle % len(portfolio)]
        
        # Random repo size - weighted towards larger sizes
        repo_size = random.choice(repo_sizes)
        
        # Don't overshoot
        if total_repo_so_far + repo_size > TARGET_REPO_OUTSTANDING * 1.05:
            repo_size = TARGET_REPO_OUTSTANDING - total_repo_so_far
        
        if repo_size < 10_000_000:  # Minimum R10M
            break
        
        # Repo dates
        trade_date = base_date + timedelta(days=random.randint(0, 20))
        spot_date = trade_date + timedelta(days=3)
        
        # Calculate next coupon date for collateral
        collateral_start = date.fromisoformat(collateral['start_date'])
        next_coupon = get_next_coupon_date(collateral_start, spot_date)
        
        # Repo must end before next coupon (with buffer)
        max_repo_end = next_coupon - timedelta(days=5)  # 5 day buffer
        
        # Calculate repo term (max 90 days or until next coupon, whichever is shorter)
        days_to_coupon = (max_repo_end - spot_date).days
        max_days = min(90, days_to_coupon)
        
        if max_days < 7:  # Need at least 7 days
            position_cycle += 1
            skip_count += 1
            if skip_count > max_skips:
                # Reset skip count and try with smaller repos
                skip_count = 0
                repo_sizes = [5_000_000, 10_000_000, 15_000_000, 20_000_000, 25_000_000]
            continue
        
        # Random term within constraints - use flexible options
        term_options = [d for d in [7, 14, 30, 60, 90] if d <= max_days]
        if not term_options:
            # Use whatever days we have
            days = max(7, min(max_days, 30))
        else:
            days = random.choice(term_options)
        
        end_date = spot_date + timedelta(days=days)
        
        # Verify end_date is before next coupon
        if end_date >= next_coupon:
            end_date = next_coupon - timedelta(days=5)
        
        # Fixed spread: JIBAR3M + 10bps
        repo_spread = REPO_SPREAD_BPS
        
        repo = {
            'id': f'REPO_{uuid.uuid4().hex[:8]}',
            'trade_date': trade_date.isoformat(),
            'spot_date': spot_date.isoformat(),
            'end_date': end_date.isoformat(),
            'cash_amount': repo_size,
            'repo_spread_bps': repo_spread,
            'direction': 'borrow_cash',
            'collateral_id': collateral['id'],
            'coupon_to_lender': False
        }
        
        repos.append(repo)
        total_repo_so_far += repo_size
        position_cycle += 1
        
        # Safety limit (increased for 10x gearing)
        if len(repos) > 500:
            break
    
    return repos


def main():
    """Generate and save portfolio with RN bonds and aligned repos"""
    
    print("Generating Portfolio with RN FRNs and Coupon-Aligned Repos...")
    print(f"Target Portfolio Notional: R{TARGET_TOTAL_NOTIONAL/1e9:.2f}B")
    print(f"Target Repo Outstanding: R{TARGET_REPO_OUTSTANDING/1e9:.2f}B")
    print(f"Target Gearing: {GEARING_RATIO}x")
    print(f"Max Maturity: {MAX_MATURITY_DATE}")
    print()
    
    # Generate portfolio
    portfolio = generate_portfolio()
    total_notional = sum(p['notional'] for p in portfolio)
    
    print(f"Generated {len(portfolio)} positions")
    print(f"Total Notional: R{total_notional/1e9:.2f}B")
    print()
    
    # Show RN bonds
    rn_positions = [p for p in portfolio if p['name'].startswith('RN')]
    print(f"RN Bonds: {len(rn_positions)}")
    for rn in rn_positions:
        print(f"  {rn['name']}: R{rn['notional']/1e6:.0f}M, Maturity: {rn['maturity']}")
    print()
    
    # Count by counterparty
    cpty_counts = {}
    for p in portfolio:
        cpty = p['counterparty']
        if cpty in cpty_counts:
            cpty_counts[cpty] += 1
        else:
            cpty_counts[cpty] = 1
    
    print("Positions by Counterparty:")
    for cpty, count in sorted(cpty_counts.items()):
        print(f"  {cpty}: {count}")
    print()
    
    # Generate repos
    repos = generate_repos_aligned_to_coupons(portfolio)
    total_repo = sum(r['cash_amount'] for r in repos)
    actual_gearing = total_repo / total_notional
    
    print(f"Generated {len(repos)} repo trades")
    print(f"Total Repo Outstanding: R{total_repo/1e9:.2f}B")
    print(f"Actual Gearing: {actual_gearing:.2f}x")
    print()
    
    # Verify repo alignment
    print("Verifying repo-coupon alignment...")
    misaligned = 0
    for repo in repos[:5]:  # Check first 5
        collateral = next((p for p in portfolio if p['id'] == repo['collateral_id']), None)
        if collateral:
            spot = date.fromisoformat(repo['spot_date'])
            end = date.fromisoformat(repo['end_date'])
            coll_start = date.fromisoformat(collateral['start_date'])
            next_cpn = get_next_coupon_date(coll_start, spot)
            
            if end >= next_cpn:
                misaligned += 1
                print(f"  ⚠️ Repo {repo['id'][:12]} ends {end} >= next coupon {next_cpn}")
            else:
                print(f"  ✅ Repo {repo['id'][:12]} ends {end} < next coupon {next_cpn}")
    
    if misaligned == 0:
        print("✅ All repos aligned to coupon dates")
    print()
    
    # Save
    portfolio_data = {'positions': portfolio}
    with open('portfolio.json', 'w') as f:
        json.dump(portfolio_data, f, indent=2)
    print("✅ Saved portfolio.json")
    
    repo_data = {'trades': repos}
    with open('repo_trades.json', 'w') as f:
        json.dump(repo_data, f, indent=2)
    print("✅ Saved repo_trades.json")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Portfolio Positions: {len(portfolio)}")
    print(f"  - RN Bonds: {len(rn_positions)}")
    print(f"  - Bank FRNs: {len(portfolio) - len(rn_positions)}")
    print(f"Total Notional: R{total_notional/1e6:,.0f}M")
    print(f"Repo Trades: {len(repos)}")
    print(f"Total Repo Outstanding: R{total_repo/1e6:,.0f}M")
    print(f"Gearing Ratio: {actual_gearing:.2f}x")
    print(f"All repos expire before next coupon date: {'✅' if misaligned == 0 else '⚠️'}")
    print("=" * 70)


if __name__ == '__main__':
    main()
