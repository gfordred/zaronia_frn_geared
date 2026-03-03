#!/usr/bin/env python3
"""Generate seed portfolio with 25 FRN positions and repo trades."""

import json
import random
from datetime import date, timedelta

# Configuration
counterparties = ['ABSA', 'RMBH', 'NEDBANK', 'SBSA', 'INVESTEC', 'SOAF']
books = ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec']
traders = ['GF', 'JM', 'TS', 'NK', 'PL']
terms_years = [1, 3, 5]

# Generate 25 FRN positions
positions = []
today = date(2026, 3, 3)

random.seed(42)  # For reproducibility

for i in range(25):
    # Random parameters
    term = random.choice(terms_years)
    days_back = random.randint(0, 730)  # 0-2 years back
    start_date = today - timedelta(days=days_back)
    maturity = start_date + timedelta(days=int(term * 365.25))
    
    notional = random.choice([50_000_000, 75_000_000, 100_000_000, 150_000_000, 200_000_000])
    issue_spread = round(random.uniform(80, 150), 1)
    dm = round(issue_spread + random.uniform(-30, 30), 1)
    
    cpty = random.choice(counterparties)
    book = random.choice(books)
    
    pos = {
        'id': f'POS_{i+1:03d}',
        'name': f'FRN_{cpty}_{term}Y_{i+1:02d}',
        'notional': float(notional),
        'start_date': start_date.isoformat(),
        'maturity': maturity.isoformat(),
        'index_type': 'JIBAR 3M',
        'issue_spread': issue_spread,
        'dm': dm,
        'lookback': 0,
        'book': book,
        'counterparty': cpty,
        'trader': random.choice(traders)
    }
    positions.append(pos)

# Save portfolio
with open('portfolio.json', 'w', encoding='utf-8') as f:
    json.dump({'positions': positions}, f, indent=2)

print(f'✓ Created {len(positions)} FRN positions')
print(f'  Total notional: R{sum(p["notional"] for p in positions):,.0f}')
print(f'  Notional range: R{min(p["notional"] for p in positions):,.0f} - R{max(p["notional"] for p in positions):,.0f}')
print(f'  Issue spread range: {min(p["issue_spread"] for p in positions):.1f} - {max(p["issue_spread"] for p in positions):.1f} bps')
print(f'  DM range: {min(p["dm"] for p in positions):.1f} - {max(p["dm"] for p in positions):.1f} bps')
print()
print('Positions by term:')
for term in [1, 3, 5]:
    count = len([p for p in positions if (date.fromisoformat(p['maturity']) - date.fromisoformat(p['start_date'])).days // 365 == term])
    print(f'  {term}Y: {count} positions')
print()
print('Positions by counterparty:')
for cpty in counterparties:
    count = len([p for p in positions if p['counterparty'] == cpty])
    notional = sum(p['notional'] for p in positions if p['counterparty'] == cpty)
    print(f'  {cpty}: {count} positions, R{notional:,.0f}')

# Generate 50 repo trades (2x gearing)
repo_trades = []
total_portfolio_notional = sum(p['notional'] for p in positions)
target_repo_notional = total_portfolio_notional * 2  # 2x gearing

# Select random positions to use as collateral
collateral_positions = random.sample(positions, min(15, len(positions)))

current_repo_notional = 0
repo_id = 1

while current_repo_notional < target_repo_notional and repo_id <= 50:
    # Random repo parameters
    days_back = random.randint(0, 730)  # 0-2 years back
    trade_dt = today - timedelta(days=days_back)
    spot_dt = trade_dt + timedelta(days=3)
    
    # Repo term: 1 week to 6 months
    repo_days = random.choice([7, 14, 30, 60, 90, 180])
    end_dt = spot_dt + timedelta(days=repo_days)
    
    # Only create repo if end date is in the past or near future
    if end_dt > today + timedelta(days=180):
        repo_id += 1
        continue
    
    # Cash amount: 50-200M
    cash_amount = random.choice([50_000_000, 75_000_000, 100_000_000, 150_000_000, 200_000_000])
    
    # Repo spread: 5-25 bps
    repo_spread = round(random.uniform(5, 25), 1)
    
    # Haircut: 0-5%
    haircut = round(random.uniform(0, 5), 1)
    
    # Direction: mostly borrow cash (financing)
    direction = random.choice(['borrow_cash', 'borrow_cash', 'borrow_cash', 'lend_cash'])
    
    # Collateral: random from selected positions
    collateral = random.choice(collateral_positions) if collateral_positions else None
    
    repo = {
        'id': f'REPO_{repo_id:03d}',
        'trade_date': trade_dt.isoformat(),
        'spot_date': spot_dt.isoformat(),
        'end_date': end_dt.isoformat(),
        'cash_amount': float(cash_amount),
        'repo_spread_bps': repo_spread,
        'haircut': haircut,
        'direction': direction,
        'collateral_id': collateral['id'] if collateral else None,
        'coupon_to_lender': random.choice([True, False])
    }
    
    repo_trades.append(repo)
    current_repo_notional += cash_amount
    repo_id += 1

# Save repo trades
with open('repo_trades.json', 'w', encoding='utf-8') as f:
    json.dump({'trades': repo_trades}, f, indent=2)

print()
print(f'✓ Created {len(repo_trades)} repo trades')
print(f'  Total repo cash: R{sum(r["cash_amount"] for r in repo_trades):,.0f}')
print(f'  Gearing ratio: {sum(r["cash_amount"] for r in repo_trades) / total_portfolio_notional:.2f}x')
print(f'  Repo spread range: {min(r["repo_spread_bps"] for r in repo_trades):.1f} - {max(r["repo_spread_bps"] for r in repo_trades):.1f} bps')
print()
print('Repo trades by direction:')
for direction in ['borrow_cash', 'lend_cash']:
    count = len([r for r in repo_trades if r['direction'] == direction])
    notional = sum(r['cash_amount'] for r in repo_trades if r['direction'] == direction)
    print(f'  {direction}: {count} trades, R{notional:,.0f}')
print()
print('Repo trades with collateral: ', len([r for r in repo_trades if r['collateral_id']]))

print()
print('='*60)
print('SEED PORTFOLIO CREATED SUCCESSFULLY')
print('='*60)
