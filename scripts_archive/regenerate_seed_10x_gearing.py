"""
Regenerate Seed Portfolio and Repo Trades with 10x Gearing
Creates balanced portfolio across 5 banks with sufficient repos for 10x leverage
"""

import json
import random
from datetime import date, timedelta
import uuid

# Configuration
NUM_POSITIONS = 25
TARGET_TOTAL_NOTIONAL = 2_500_000_000  # R2.5 billion
GEARING_RATIO = 10.0  # 10x gearing
TARGET_REPO_OUTSTANDING = TARGET_TOTAL_NOTIONAL * GEARING_RATIO  # R25 billion

# Banks
BANKS = ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec']
BOOKS = ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec']

# Spread ranges (rounded to 5 bps)
SPREAD_OPTIONS = [70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150]
REPO_SPREAD_OPTIONS = [5, 10, 15, 20, 25, 30, 35, 40]

# Maturity ranges
START_DATE = date(2022, 7, 11)
MATURITY_YEARS = [2, 3, 4, 5, 7, 10]

def generate_portfolio():
    """Generate balanced portfolio across 5 banks"""
    positions = []
    notional_per_position = TARGET_TOTAL_NOTIONAL / NUM_POSITIONS
    
    for i in range(NUM_POSITIONS):
        bank_idx = i % len(BANKS)
        bank = BANKS[bank_idx]
        book = BOOKS[bank_idx]
        
        # Random maturity
        years = random.choice(MATURITY_YEARS)
        start_date = START_DATE + timedelta(days=random.randint(0, 365))
        maturity = start_date + timedelta(days=int(years * 365.25))
        
        # Random spread (rounded to 5 bps)
        issue_spread = random.choice(SPREAD_OPTIONS)
        dm = random.choice(SPREAD_OPTIONS)
        
        position = {
            'id': f'POS_{uuid.uuid4().hex[:8]}',
            'name': f'{bank}_FRN_{maturity.year}',
            'counterparty': bank,
            'book': book,
            'notional': notional_per_position,
            'start_date': start_date.isoformat(),
            'maturity': maturity.isoformat(),
            'issue_spread': issue_spread,
            'dm': dm,
            'index': 'JIBAR 3M',
            'lookback': 0
        }
        
        positions.append(position)
    
    return positions


def generate_repos(portfolio):
    """Generate repo trades to achieve 10x gearing"""
    repos = []
    
    # Calculate how many repos needed
    # Use varying sizes to create realistic book
    repo_sizes = [
        100_000_000,  # R100M
        200_000_000,  # R200M
        500_000_000,  # R500M
        1_000_000_000  # R1B
    ]
    
    total_repo_so_far = 0
    repo_count = 0
    
    # Base date for repos
    base_date = date(2024, 10, 25)
    
    while total_repo_so_far < TARGET_REPO_OUTSTANDING:
        # Random repo size
        repo_size = random.choice(repo_sizes)
        
        # Don't overshoot target too much
        if total_repo_so_far + repo_size > TARGET_REPO_OUTSTANDING * 1.05:
            repo_size = TARGET_REPO_OUTSTANDING - total_repo_so_far
        
        # Random dates (max 90 days as per requirement)
        trade_date = base_date - timedelta(days=random.randint(0, 30))
        spot_date = trade_date + timedelta(days=3)
        days = random.choice([30, 60, 90])  # 1, 2, or 3 months
        end_date = spot_date + timedelta(days=days)
        
        # Random spread
        repo_spread = random.choice(REPO_SPREAD_OPTIONS)
        
        # Random collateral from portfolio
        collateral = random.choice(portfolio)
        
        repo = {
            'id': f'REPO_{uuid.uuid4().hex[:8]}',
            'trade_date': trade_date.isoformat(),
            'spot_date': spot_date.isoformat(),
            'end_date': end_date.isoformat(),
            'cash_amount': repo_size,
            'repo_spread_bps': repo_spread,
            'direction': 'borrow_cash',  # All borrowing for gearing
            'collateral_id': collateral['id'],
            'coupon_to_lender': False
        }
        
        repos.append(repo)
        total_repo_so_far += repo_size
        repo_count += 1
        
        # Safety limit
        if repo_count > 100:
            break
    
    return repos


def main():
    """Generate and save portfolio and repos"""
    
    print("Generating 10x Geared Portfolio...")
    print(f"Target Portfolio Notional: R{TARGET_TOTAL_NOTIONAL/1e9:.2f}B")
    print(f"Target Repo Outstanding: R{TARGET_REPO_OUTSTANDING/1e9:.2f}B")
    print(f"Target Gearing Ratio: {GEARING_RATIO}x")
    print()
    
    # Generate portfolio
    portfolio = generate_portfolio()
    total_notional = sum(p['notional'] for p in portfolio)
    
    print(f"Generated {len(portfolio)} portfolio positions")
    print(f"Total Notional: R{total_notional/1e9:.2f}B")
    print()
    
    # Count by bank
    bank_counts = {}
    for p in portfolio:
        bank = p['counterparty']
        if bank in bank_counts:
            bank_counts[bank] += 1
        else:
            bank_counts[bank] = 1
    
    print("Positions by Bank:")
    for bank, count in sorted(bank_counts.items()):
        print(f"  {bank}: {count}")
    print()
    
    # Generate repos
    repos = generate_repos(portfolio)
    total_repo = sum(r['cash_amount'] for r in repos)
    actual_gearing = total_repo / total_notional
    
    print(f"Generated {len(repos)} repo trades")
    print(f"Total Repo Outstanding: R{total_repo/1e9:.2f}B")
    print(f"Actual Gearing Ratio: {actual_gearing:.2f}x")
    print()
    
    # Save portfolio
    portfolio_data = {'positions': portfolio}
    with open('portfolio.json', 'w') as f:
        json.dump(portfolio_data, f, indent=2)
    print("✅ Saved portfolio.json")
    
    # Save repos
    repo_data = {'trades': repos}
    with open('repo_trades.json', 'w') as f:
        json.dump(repo_data, f, indent=2)
    print("✅ Saved repo_trades.json")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Portfolio Positions: {len(portfolio)}")
    print(f"Total Notional: R{total_notional/1e6:,.0f}M")
    print(f"Repo Trades: {len(repos)}")
    print(f"Total Repo Outstanding: R{total_repo/1e6:,.0f}M")
    print(f"Gearing Ratio: {actual_gearing:.2f}x")
    print(f"Net Financing: R{total_repo/1e6:,.0f}M")
    print("=" * 60)


if __name__ == '__main__':
    main()
