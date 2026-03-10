"""
Regenerate Portfolio with Seed Capital and 9x Gearing
=====================================================

Concept:
1. Start with R100M seed capital at inception
2. Use seed capital to purchase initial FRN positions
3. Repo those initial positions to raise cash
4. Use repo proceeds to buy more FRNs
5. Continue gearing up to ~9x target
6. Align repo maturities with coupon dates for realistic cash management

Target Structure:
- Seed Capital: R100M
- Target Gearing: 9x
- Total Portfolio: ~R1B (R100M equity + R900M borrowed)
- Mix: Government bonds + Bank FRNs
"""

import json
import random
from datetime import date, datetime, timedelta
import uuid

# Configuration
SEED_CAPITAL = 100_000_000  # R100M
TARGET_GEARING = 9.0
INCEPTION_DATE = date(2022, 7, 11)  # Start date
JIBAR_RATE = 6.63
REPO_SPREAD_BPS = 10  # 10 bps over JIBAR

# Counterparties and spreads
GOVERNMENT_SPREAD = 130  # bps
BANK_SPREADS = {
    'Standard Bank': 75,
    'ABSA': 95,
    'Nedbank': 110,
    'FirstRand': 125,
    'Investec': 130
}

def generate_id(prefix='POS'):
    """Generate unique ID"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def random_date_between(start, end):
    """Generate random date between start and end"""
    delta = (end - start).days
    random_days = random.randint(0, delta)
    return start + timedelta(days=random_days)

def generate_seed_positions():
    """
    Generate initial positions purchased with seed capital
    Start with 2 government bonds totaling ~R100M
    """
    positions = []
    
    # Position 1: RN2027 - R50M
    positions.append({
        'id': generate_id('POS'),
        'name': 'RN2027',
        'counterparty': 'Republic of SA',
        'book': 'Government',
        'notional': 50_000_000,
        'start_date': INCEPTION_DATE.isoformat(),
        'maturity': (INCEPTION_DATE + timedelta(days=5*365)).isoformat(),
        'issue_spread': GOVERNMENT_SPREAD,
        'dm': GOVERNMENT_SPREAD,
        'index': 'JIBAR 3M',
        'lookback': 0,
        'tier': 'Seed'
    })
    
    # Position 2: RN2030 - R50M
    positions.append({
        'id': generate_id('POS'),
        'name': 'RN2030',
        'counterparty': 'Republic of SA',
        'book': 'Government',
        'notional': 50_000_000,
        'start_date': INCEPTION_DATE.isoformat(),
        'maturity': (INCEPTION_DATE + timedelta(days=8*365)).isoformat(),
        'issue_spread': 96,
        'dm': 96,
        'index': 'JIBAR 3M',
        'lookback': 0,
        'tier': 'Seed'
    })
    
    return positions

def generate_geared_positions(seed_positions, target_total_notional):
    """
    Generate additional positions purchased with repo proceeds
    Target: ~R900M additional (to reach R1B total with R100M seed)
    """
    positions = []
    
    current_notional = sum(p['notional'] for p in seed_positions)
    remaining_notional = target_total_notional - current_notional
    
    # Generate bank FRN positions in R30M-R50M chunks
    banks = list(BANK_SPREADS.keys())
    position_count = 0
    
    while remaining_notional > 0:
        # Random bank
        bank = random.choice(banks)
        spread = BANK_SPREADS[bank]
        
        # Random notional between R30M-R50M
        notional = min(random.randint(30_000_000, 50_000_000), remaining_notional)
        
        # Start date: within first 6 months after inception
        start_date = random_date_between(INCEPTION_DATE, INCEPTION_DATE + timedelta(days=180))
        
        # Maturity: 2-5 years from start
        years_to_mat = random.uniform(2, 5)
        maturity = start_date + timedelta(days=int(years_to_mat * 365))
        
        position_count += 1
        positions.append({
            'id': generate_id('POS'),
            'name': f'{bank} FRN {position_count}',
            'counterparty': bank,
            'book': bank,
            'notional': notional,
            'start_date': start_date.isoformat(),
            'maturity': maturity.isoformat(),
            'issue_spread': spread + random.randint(-10, 10),  # Slight variation
            'dm': spread,
            'index': 'JIBAR 3M',
            'lookback': 0,
            'tier': 'Geared'
        })
        
        remaining_notional -= notional
    
    return positions

def generate_repos_for_gearing(all_positions, target_repo_amount):
    """
    Generate repo trades to achieve target gearing
    
    Strategy:
    1. Repo seed positions first (R100M collateral -> R90M cash at 90% haircut)
    2. Use proceeds to buy more FRNs
    3. Repo those new FRNs
    4. Continue until target gearing reached
    
    Repo terms: 1-3 months, rolling to maintain ~9x gearing
    """
    repos = []
    
    # Sort positions by start date to repo in chronological order
    sorted_positions = sorted(all_positions, key=lambda x: x['start_date'])
    
    total_repo_raised = 0
    position_repo_map = {}  # Track which positions have been repo'd
    
    for pos in sorted_positions:
        if total_repo_raised >= target_repo_amount:
            break
        
        # Determine how much to repo against this position
        # Use 85-92% of notional (haircut)
        haircut = random.uniform(0.85, 0.92)
        repo_amount = int(pos['notional'] * haircut)
        
        # Don't exceed target
        if total_repo_raised + repo_amount > target_repo_amount:
            repo_amount = target_repo_amount - total_repo_raised
        
        if repo_amount < 1_000_000:  # Skip if less than R1M
            continue
        
        # Repo start: shortly after position start (need to own it first)
        pos_start = datetime.strptime(pos['start_date'], '%Y-%m-%d').date()
        repo_start = pos_start + timedelta(days=random.randint(2, 10))
        
        # Repo term: 2-3 months
        repo_term_days = random.randint(60, 90)
        repo_end = repo_start + timedelta(days=repo_term_days)
        
        # Trade date: 2 days before spot
        trade_date = repo_start - timedelta(days=2)
        
        repo_id = generate_id('REPO')
        repos.append({
            'id': repo_id,
            'trade_date': trade_date.isoformat(),
            'spot_date': repo_start.isoformat(),
            'end_date': repo_end.isoformat(),
            'cash_amount': repo_amount,
            'repo_spread_bps': REPO_SPREAD_BPS,
            'direction': 'borrow_cash',
            'collateral_id': pos['id'],
            'coupon_to_lender': False
        })
        
        position_repo_map[pos['id']] = repo_id
        total_repo_raised += repo_amount
    
    # Generate rolling repos to maintain gearing over time
    # Only roll repos that matured, keeping total outstanding ~constant
    today = date.today()
    initial_repos = repos.copy()
    
    for old_repo in initial_repos:
        old_end = datetime.strptime(old_repo['end_date'], '%Y-%m-%d').date()
        
        # If repo matured before today, create 1-2 rolling repos
        if old_end < today:
            num_rolls = random.randint(1, 2)
            last_end = old_end
            
            for i in range(num_rolls):
                new_start = last_end + timedelta(days=random.randint(0, 3))  # Small gap
                new_term = random.randint(60, 90)
                new_end = new_start + timedelta(days=new_term)
                
                # Stop if we're too far in the future
                if new_end > today + timedelta(days=120):
                    break
                
                new_trade = new_start - timedelta(days=2)
                
                # Keep amount similar (98-102% of original)
                new_amount = int(old_repo['cash_amount'] * random.uniform(0.98, 1.02))
                
                repos.append({
                    'id': generate_id('REPO'),
                    'trade_date': new_trade.isoformat(),
                    'spot_date': new_start.isoformat(),
                    'end_date': new_end.isoformat(),
                    'cash_amount': new_amount,
                    'repo_spread_bps': REPO_SPREAD_BPS,
                    'direction': 'borrow_cash',
                    'collateral_id': old_repo['collateral_id'],
                    'coupon_to_lender': False
                })
                
                last_end = new_end
    
    return repos

def main():
    """Generate complete portfolio with seed capital and gearing"""
    
    print("=" * 70)
    print("REGENERATING PORTFOLIO WITH SEED CAPITAL & 9X GEARING")
    print("=" * 70)
    print()
    
    # Step 1: Generate seed positions (R100M)
    print("Step 1: Generating seed positions with R100M capital...")
    seed_positions = generate_seed_positions()
    seed_notional = sum(p['notional'] for p in seed_positions)
    print(f"  ✓ Created {len(seed_positions)} seed positions")
    print(f"  ✓ Total seed notional: R{seed_notional:,.0f}")
    print()
    
    # Step 2: Calculate target portfolio size
    target_total_notional = SEED_CAPITAL * (1 + TARGET_GEARING)
    target_repo_amount = SEED_CAPITAL * TARGET_GEARING
    
    print(f"Step 2: Calculating target structure...")
    print(f"  Seed Capital: R{SEED_CAPITAL:,.0f}")
    print(f"  Target Gearing: {TARGET_GEARING}x")
    print(f"  Target Total Notional: R{target_total_notional:,.0f}")
    print(f"  Target Repo Amount: R{target_repo_amount:,.0f}")
    print()
    
    # Step 3: Generate geared positions
    print("Step 3: Generating geared positions (purchased with repo proceeds)...")
    geared_positions = generate_geared_positions(seed_positions, target_total_notional)
    geared_notional = sum(p['notional'] for p in geared_positions)
    print(f"  ✓ Created {len(geared_positions)} geared positions")
    print(f"  ✓ Total geared notional: R{geared_notional:,.0f}")
    print()
    
    # Combine all positions
    all_positions = seed_positions + geared_positions
    total_notional = sum(p['notional'] for p in all_positions)
    
    # Step 4: Generate repos
    print("Step 4: Generating repo trades for gearing...")
    repos = generate_repos_for_gearing(all_positions, target_repo_amount)
    total_repo = sum(r['cash_amount'] for r in repos)
    actual_gearing = total_repo / SEED_CAPITAL
    
    print(f"  ✓ Created {len(repos)} repo trades")
    print(f"  ✓ Total repo cash: R{total_repo:,.0f}")
    print(f"  ✓ Actual gearing: {actual_gearing:.2f}x")
    print()
    
    # Step 5: Save to files
    print("Step 5: Saving to files...")
    
    portfolio_data = {'positions': all_positions}
    with open('portfolio.json', 'w') as f:
        json.dump(portfolio_data, f, indent=2)
    print(f"  ✓ Saved {len(all_positions)} positions to portfolio.json")
    
    repo_data = {'trades': repos}
    with open('repo_trades.json', 'w') as f:
        json.dump(repo_data, f, indent=2)
    print(f"  ✓ Saved {len(repos)} repos to repo_trades.json")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Seed Capital:        R{SEED_CAPITAL:>15,}")
    print(f"Total Portfolio:     R{total_notional:>15,}")
    print(f"Total Repo Debt:     R{total_repo:>15,}")
    print(f"Actual Gearing:      {actual_gearing:>15.2f}x")
    print(f"Equity:              R{SEED_CAPITAL:>15,}")
    print()
    print(f"Positions by Tier:")
    print(f"  Seed:              {len(seed_positions):>3} positions, R{seed_notional:>12,}")
    print(f"  Geared:            {len(geared_positions):>3} positions, R{geared_notional:>12,}")
    print()
    print(f"Positions by Counterparty:")
    cpty_summary = {}
    for pos in all_positions:
        cpty = pos['counterparty']
        if cpty not in cpty_summary:
            cpty_summary[cpty] = {'count': 0, 'notional': 0}
        cpty_summary[cpty]['count'] += 1
        cpty_summary[cpty]['notional'] += pos['notional']
    
    for cpty, data in sorted(cpty_summary.items()):
        print(f"  {cpty:20} {data['count']:>3} positions, R{data['notional']:>12,}")
    print()
    
    print(f"Repo Summary:")
    print(f"  Total repos:       {len(repos):>3}")
    print(f"  Avg repo size:     R{total_repo/len(repos):>12,.0f}")
    print(f"  Avg spread:        {REPO_SPREAD_BPS:>12.1f} bps")
    print()
    
    # Active repos
    today = date.today()
    active_repos = [r for r in repos if datetime.strptime(r['end_date'], '%Y-%m-%d').date() >= today]
    active_repo_cash = sum(r['cash_amount'] for r in active_repos)
    
    print(f"Active Repos (as of {today}):")
    print(f"  Active repos:      {len(active_repos):>3}")
    print(f"  Active cash:       R{active_repo_cash:>12,}")
    print(f"  Current gearing:   {active_repo_cash/SEED_CAPITAL:>12.2f}x")
    print()
    
    print("✓ Portfolio regeneration complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
