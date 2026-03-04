"""
Final Portfolio Regeneration: R100M Seed Capital with 9x Gearing
================================================================

Clean approach:
1. R100M seed capital at inception
2. Purchase R100M of government bonds (seed positions)
3. Repo those bonds to raise ~R90M (90% haircut)
4. Use R90M to buy more FRNs
5. Repo those FRNs to raise more cash
6. Continue until total portfolio = R1B (R100M equity + R900M debt)
7. Maintain ~R900M of active repos at any given time (9x gearing)
"""

import json
import random
from datetime import date, datetime, timedelta
import uuid

# Configuration
SEED_CAPITAL = 100_000_000
TARGET_GEARING = 9.0
INCEPTION_DATE = date(2022, 7, 11)
JIBAR_RATE = 6.63
REPO_SPREAD_BPS = 10

# Spreads
GOVERNMENT_SPREAD = 130
BANK_SPREADS = {
    'Standard Bank': 75,
    'ABSA': 95,
    'Nedbank': 110,
    'FirstRand': 125,
    'Investec': 130
}

def generate_id(prefix='POS'):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def random_date_between(start, end):
    delta = (end - start).days
    random_days = random.randint(0, delta)
    return start + timedelta(days=random_days)

def generate_portfolio_with_seed():
    """Generate complete portfolio starting from seed capital"""
    
    positions = []
    
    # SEED POSITIONS (R100M total - purchased with seed capital)
    positions.append({
        'id': generate_id('POS'),
        'name': 'RN2027',
        'counterparty': 'Republic of SA',
        'book': 'Government',
        'notional': 50_000_000,
        'start_date': INCEPTION_DATE.isoformat(),
        'maturity': (INCEPTION_DATE + timedelta(days=5*365)).isoformat(),
        'issue_spread': 130,
        'dm': 130,
        'index': 'JIBAR 3M',
        'lookback': 0,
        'tier': 'Seed'
    })
    
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
    
    # GEARED POSITIONS (R900M total - purchased with repo proceeds)
    # Spread across banks in R30-50M chunks
    banks = list(BANK_SPREADS.keys())
    remaining = 900_000_000
    position_num = 1
    
    while remaining > 0:
        bank = random.choice(banks)
        spread = BANK_SPREADS[bank]
        notional = min(random.randint(30_000_000, 50_000_000), remaining)
        
        # Start date: within 6 months of inception
        start = random_date_between(INCEPTION_DATE, INCEPTION_DATE + timedelta(days=180))
        
        # Maturity: 2-5 years
        maturity = start + timedelta(days=int(random.uniform(2, 5) * 365))
        
        positions.append({
            'id': generate_id('POS'),
            'name': f'{bank} FRN {position_num}',
            'counterparty': bank,
            'book': bank,
            'notional': notional,
            'start_date': start.isoformat(),
            'maturity': maturity.isoformat(),
            'issue_spread': spread + random.randint(-10, 10),
            'dm': spread,
            'index': 'JIBAR 3M',
            'lookback': 0,
            'tier': 'Geared'
        })
        
        remaining -= notional
        position_num += 1
    
    return positions

def generate_repos_9x_gearing(positions):
    """
    Generate repos to achieve and maintain 9x gearing
    
    Key: At any point in time, total outstanding repos should be ~R900M
    """
    
    repos = []
    today = date.today()
    
    # Target: R900M of repos outstanding at any given time
    target_outstanding = 900_000_000
    
    # Strategy: Repo each position once, with staggered maturities
    # Then roll repos as they mature to maintain R900M outstanding
    
    # Phase 1: Initial repos (inception to 6 months)
    # Repo positions as they are purchased
    sorted_positions = sorted(positions, key=lambda x: x['start_date'])
    
    initial_repo_total = 0
    position_repo_map = {}
    
    for pos in sorted_positions:
        # Repo 88-92% of notional
        haircut = random.uniform(0.88, 0.92)
        repo_amount = int(pos['notional'] * haircut)
        
        # Cap total at target
        if initial_repo_total + repo_amount > target_outstanding:
            repo_amount = target_outstanding - initial_repo_total
        
        if repo_amount < 1_000_000:
            continue
        
        pos_start = datetime.strptime(pos['start_date'], '%Y-%m-%d').date()
        
        # Repo starts 3-7 days after position purchase
        repo_spot = pos_start + timedelta(days=random.randint(3, 7))
        repo_trade = repo_spot - timedelta(days=2)
        
        # Repo term: 60-90 days
        repo_term = random.randint(60, 90)
        repo_end = repo_spot + timedelta(days=repo_term)
        
        repo_id = generate_id('REPO')
        repos.append({
            'id': repo_id,
            'trade_date': repo_trade.isoformat(),
            'spot_date': repo_spot.isoformat(),
            'end_date': repo_end.isoformat(),
            'cash_amount': repo_amount,
            'repo_spread_bps': REPO_SPREAD_BPS,
            'direction': 'borrow_cash',
            'collateral_id': pos['id'],
            'coupon_to_lender': False
        })
        
        position_repo_map[pos['id']] = {
            'last_repo_id': repo_id,
            'last_end': repo_end,
            'amount': repo_amount
        }
        
        initial_repo_total += repo_amount
        
        if initial_repo_total >= target_outstanding:
            break
    
    # Phase 2: Rolling repos to maintain R900M outstanding
    # For each initial repo that matured, create 1-2 rolling repos
    # But keep total outstanding at ~R900M
    
    for pos_id, repo_info in position_repo_map.items():
        last_end = repo_info['last_end']
        amount = repo_info['amount']
        
        # Roll repos until today
        while last_end < today:
            # New repo starts when old one ends (or 1-2 days later)
            new_spot = last_end + timedelta(days=random.randint(0, 2))
            new_trade = new_spot - timedelta(days=2)
            new_term = random.randint(60, 90)
            new_end = new_spot + timedelta(days=new_term)
            
            # Stop if we go too far into future
            if new_end > today + timedelta(days=120):
                break
            
            # Amount stays similar (97-103% variation)
            new_amount = int(amount * random.uniform(0.97, 1.03))
            
            repos.append({
                'id': generate_id('REPO'),
                'trade_date': new_trade.isoformat(),
                'spot_date': new_spot.isoformat(),
                'end_date': new_end.isoformat(),
                'cash_amount': new_amount,
                'repo_spread_bps': REPO_SPREAD_BPS,
                'direction': 'borrow_cash',
                'collateral_id': pos_id,
                'coupon_to_lender': False
            })
            
            last_end = new_end
            amount = new_amount
    
    return repos

def main():
    print("=" * 70)
    print("PORTFOLIO REGENERATION: R100M SEED + 9X GEARING")
    print("=" * 70)
    print()
    
    # Generate portfolio
    print("Generating portfolio...")
    positions = generate_portfolio_with_seed()
    
    seed_positions = [p for p in positions if p['tier'] == 'Seed']
    geared_positions = [p for p in positions if p['tier'] == 'Geared']
    
    total_notional = sum(p['notional'] for p in positions)
    seed_notional = sum(p['notional'] for p in seed_positions)
    geared_notional = sum(p['notional'] for p in geared_positions)
    
    print(f"  ✓ Total positions: {len(positions)}")
    print(f"  ✓ Seed positions: {len(seed_positions)} (R{seed_notional:,.0f})")
    print(f"  ✓ Geared positions: {len(geared_positions)} (R{geared_notional:,.0f})")
    print(f"  ✓ Total notional: R{total_notional:,.0f}")
    print()
    
    # Generate repos
    print("Generating repos for 9x gearing...")
    repos = generate_repos_9x_gearing(positions)
    
    total_repo = sum(r['cash_amount'] for r in repos)
    
    # Calculate active repos
    today = date.today()
    active_repos = [r for r in repos if datetime.strptime(r['end_date'], '%Y-%m-%d').date() >= today]
    active_repo_cash = sum(r['cash_amount'] for r in active_repos)
    
    print(f"  ✓ Total repo trades: {len(repos)}")
    print(f"  ✓ Total repo cash (all time): R{total_repo:,.0f}")
    print(f"  ✓ Active repos (today): {len(active_repos)}")
    print(f"  ✓ Active repo cash: R{active_repo_cash:,.0f}")
    print(f"  ✓ Current gearing: {active_repo_cash/SEED_CAPITAL:.2f}x")
    print()
    
    # Save files
    print("Saving to files...")
    
    with open('portfolio.json', 'w') as f:
        json.dump({'positions': positions}, f, indent=2)
    print(f"  ✓ Saved portfolio.json ({len(positions)} positions)")
    
    with open('repo_trades.json', 'w') as f:
        json.dump({'trades': repos}, f, indent=2)
    print(f"  ✓ Saved repo_trades.json ({len(repos)} repos)")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Seed Capital:          R{SEED_CAPITAL:>15,}")
    print(f"Total Portfolio:       R{total_notional:>15,}")
    print(f"Active Repo Debt:      R{active_repo_cash:>15,}")
    print(f"Current Gearing:       {active_repo_cash/SEED_CAPITAL:>15.2f}x")
    print(f"Target Gearing:        {TARGET_GEARING:>15.1f}x")
    print()
    
    print("Positions by Counterparty:")
    cpty_summary = {}
    for pos in positions:
        cpty = pos['counterparty']
        if cpty not in cpty_summary:
            cpty_summary[cpty] = {'count': 0, 'notional': 0}
        cpty_summary[cpty]['count'] += 1
        cpty_summary[cpty]['notional'] += pos['notional']
    
    for cpty, data in sorted(cpty_summary.items()):
        pct = (data['notional'] / total_notional) * 100
        print(f"  {cpty:20} {data['count']:>2} pos, R{data['notional']:>12,} ({pct:>5.1f}%)")
    print()
    
    print("✓ Regeneration complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
