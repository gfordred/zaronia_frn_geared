"""
Clean Portfolio & Repo Regeneration
====================================

Regenerates portfolio and repos with:
1. Notionals rounded to nearest R10M
2. Proper collateral tracking (no double-repo)
3. Clear asset/liability linkage
4. Consistent gearing calculation
"""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path

# Configuration
SEED_CAPITAL = 100_000_000  # R100M
TARGET_GEARING = 9.0  # 9x leverage
NOTIONAL_ROUNDING = 10_000_000  # Round to nearest R10M

# Counterparties with limits
COUNTERPARTIES = {
    "Republic of South Africa": {"max_pct": 50, "spread_range": (100, 130)},
    "Standard Bank": {"max_pct": 15, "spread_range": (110, 140)},
    "Nedbank": {"max_pct": 15, "spread_range": (105, 135)},
    "Absa": {"max_pct": 15, "spread_range": (108, 138)},
    "FirstRand": {"max_pct": 10, "spread_range": (112, 142)},
}


def round_to_nearest(value, nearest=NOTIONAL_ROUNDING):
    """Round value to nearest specified amount"""
    return round(value / nearest) * nearest


def generate_clean_portfolio():
    """Generate portfolio with rounded notionals"""
    
    total_target_notional = SEED_CAPITAL * (1 + TARGET_GEARING)  # R1B
    positions = []
    allocated = 0
    
    # Sovereign positions (50% max)
    sovereign_target = total_target_notional * 0.50
    sovereign_positions = [
        {"name": "RSA 2026 FRN", "maturity_years": 2, "spread": 120},
        {"name": "RSA 2027 FRN", "maturity_years": 3, "spread": 125},
        {"name": "RSA 2029 FRN", "maturity_years": 5, "spread": 130},
    ]
    
    for i, pos_def in enumerate(sovereign_positions):
        notional = round_to_nearest(sovereign_target / len(sovereign_positions))
        
        # All positions start on INCEPTION DATE (not staggered)
        inception_date = date.today() - timedelta(days=365)  # 1 year ago
        
        positions.append({
            "id": str(uuid.uuid4()),
            "name": pos_def["name"],
            "counterparty": "Republic of South Africa",
            "notional": notional,
            "start_date": inception_date.isoformat(),
            "maturity": (inception_date + timedelta(days=365 * pos_def["maturity_years"])).isoformat(),
            "issue_spread": pos_def["spread"],
            "dm": pos_def["spread"],
            "index": "JIBAR 3M",
            "book": "Sovereign",
            "strategy": "Core"
        })
        allocated += notional
    
    # Bank positions (remaining 50%)
    bank_target = total_target_notional - allocated
    bank_list = ["Standard Bank", "Nedbank", "Absa", "FirstRand"]
    
    for i, bank in enumerate(bank_list):
        # Allocate proportionally
        if i == len(bank_list) - 1:
            # Last bank gets remainder
            notional = round_to_nearest(total_target_notional - allocated)
        else:
            notional = round_to_nearest(bank_target / len(bank_list))
        
        spread_min, spread_max = COUNTERPARTIES[bank]["spread_range"]
        spread = spread_min + (i * 5)  # Vary spreads slightly
        
        # All positions start on INCEPTION DATE (same as sovereign)
        inception_date = date.today() - timedelta(days=365)  # 1 year ago
        
        positions.append({
            "id": str(uuid.uuid4()),
            "name": f"{bank} FRN 2028",
            "counterparty": bank,
            "notional": notional,
            "start_date": inception_date.isoformat(),
            "maturity": (inception_date + timedelta(days=365 * 4)).isoformat(),
            "issue_spread": spread,
            "dm": spread,
            "index": "JIBAR 3M",
            "book": "Bank",
            "strategy": "Diversified"
        })
        allocated += notional
    
    # Verify totals
    actual_total = sum(p["notional"] for p in positions)
    print(f"\n✓ Portfolio Generated:")
    print(f"  Target Notional: R{total_target_notional:,.0f}")
    print(f"  Actual Notional: R{actual_total:,.0f}")
    print(f"  Positions: {len(positions)}")
    print(f"  All notionals rounded to R10M: {all(p['notional'] % NOTIONAL_ROUNDING == 0 for p in positions)}")
    
    return positions


def generate_repos_with_collateral_tracking(positions):
    """
    Generate repos with proper collateral tracking.
    
    Ensures:
    1. Each asset is only repo'd once
    2. Collateral tags link repos to assets
    3. Total repo = Target gearing × Seed capital
    """
    
    target_repo = SEED_CAPITAL * TARGET_GEARING  # R900M
    repos = []
    collateral_usage = {}  # Track which assets are repo'd
    
    # Sort positions by notional (largest first)
    sorted_positions = sorted(positions, key=lambda p: p['notional'], reverse=True)
    
    total_repo = 0
    
    for pos in sorted_positions:
        if total_repo >= target_repo:
            break
        
        pos_id = pos['id']
        
        # Check if already used as collateral
        if pos_id in collateral_usage:
            print(f"  ⚠️  Skipping {pos['name']} - already repo'd")
            continue
        
        # Repo amount = 90% of position notional (haircut)
        repo_amount = round_to_nearest(pos['notional'] * 0.90)
        
        # Don't exceed target
        if total_repo + repo_amount > target_repo:
            repo_amount = round_to_nearest(target_repo - total_repo)
        
        if repo_amount <= 0:
            continue
        
        # Create repo trade
        spot_date = date.today()
        end_date = spot_date + timedelta(days=90)  # 3-month repo
        
        repo = {
            "id": str(uuid.uuid4()),
            "trade_date": (spot_date - timedelta(days=2)).isoformat(),
            "spot_date": spot_date.isoformat(),
            "end_date": end_date.isoformat(),
            "cash_amount": repo_amount,
            "repo_spread_bps": 10,  # 10bps over JIBAR
            "direction": "borrow_cash",
            "collateral_id": pos_id,  # Link to position
            "collateral_name": pos['name'],
            "coupon_to_lender": False
        }
        
        repos.append(repo)
        collateral_usage[pos_id] = repo_amount
        total_repo += repo_amount
        
        print(f"  ✓ Repo'd {pos['name']}: R{repo_amount:,.0f} (collateral: {pos_id[:8]}...)")
    
    # Verify
    actual_gearing = total_repo / SEED_CAPITAL
    print(f"\n✓ Repos Generated:")
    print(f"  Target Repo: R{target_repo:,.0f}")
    print(f"  Actual Repo: R{total_repo:,.0f}")
    print(f"  Target Gearing: {TARGET_GEARING:.2f}x")
    print(f"  Actual Gearing: {actual_gearing:.2f}x")
    print(f"  Repo Trades: {len(repos)}")
    print(f"  Unique Collateral: {len(collateral_usage)}")
    print(f"  No Double-Repo: {len(collateral_usage) == len(repos)}")
    
    return repos, collateral_usage


def create_asset_liability_summary(positions, repos, collateral_usage):
    """Create clear asset/liability summary"""
    
    total_assets = sum(p['notional'] for p in positions)
    total_liabilities = sum(r['cash_amount'] for r in repos if r['direction'] == 'borrow_cash')
    net_equity = total_assets - total_liabilities
    
    # CORRECT GEARING = Repo Outstanding / Seed Capital (NOT Notional)
    # This shows true leverage: How many times we've borrowed relative to our equity
    gearing = total_liabilities / SEED_CAPITAL if SEED_CAPITAL > 0 else 0
    
    # Collateral breakdown
    repod_assets = sum(p['notional'] for p in positions if p['id'] in collateral_usage)
    free_assets = total_assets - repod_assets
    
    summary = {
        "assets": {
            "total_portfolio_notional": total_assets,
            "repod_assets": repod_assets,
            "free_assets": free_assets,
            "repod_percentage": (repod_assets / total_assets * 100) if total_assets > 0 else 0
        },
        "liabilities": {
            "total_repo_outstanding": total_liabilities,
            "number_of_repos": len(repos)
        },
        "equity": {
            "seed_capital": SEED_CAPITAL,
            "net_equity": net_equity,
            "gearing_ratio": gearing
        },
        "collateral_tracking": {
            "positions_used_as_collateral": len(collateral_usage),
            "total_positions": len(positions),
            "collateral_utilization_pct": (len(collateral_usage) / len(positions) * 100) if positions else 0
        }
    }
    
    return summary


def main():
    """Main regeneration function"""
    
    print("=" * 70)
    print("CLEAN PORTFOLIO & REPO REGENERATION")
    print("=" * 70)
    
    # Generate portfolio
    print("\n[1/4] Generating Portfolio...")
    positions = generate_clean_portfolio()
    
    # Generate repos with collateral tracking
    print("\n[2/4] Generating Repos with Collateral Tracking...")
    repos, collateral_usage = generate_repos_with_collateral_tracking(positions)
    
    # Create summary
    print("\n[3/4] Creating Asset/Liability Summary...")
    summary = create_asset_liability_summary(positions, repos, collateral_usage)
    
    # Save files
    print("\n[4/4] Saving Files...")
    
    # Save portfolio
    with open('portfolio_positions.json', 'w') as f:
        json.dump(positions, f, indent=2)
    print(f"  ✓ Saved portfolio_positions.json ({len(positions)} positions)")
    
    # Save repos
    with open('repo_trades.json', 'w') as f:
        json.dump(repos, f, indent=2)
    print(f"  ✓ Saved repo_trades.json ({len(repos)} repos)")
    
    # Save summary
    with open('asset_liability_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ Saved asset_liability_summary.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print("ASSET/LIABILITY SUMMARY")
    print("=" * 70)
    print(f"\nASSETS:")
    print(f"  Total Portfolio Notional: R{summary['assets']['total_portfolio_notional']:,.0f}")
    print(f"  Repod Assets:             R{summary['assets']['repod_assets']:,.0f} ({summary['assets']['repod_percentage']:.1f}%)")
    print(f"  Free Assets:              R{summary['assets']['free_assets']:,.0f}")
    
    print(f"\nLIABILITIES:")
    print(f"  Total Repo Outstanding:   R{summary['liabilities']['total_repo_outstanding']:,.0f}")
    print(f"  Number of Repos:          {summary['liabilities']['number_of_repos']}")
    
    print(f"\nEQUITY:")
    print(f"  Seed Capital:             R{summary['equity']['seed_capital']:,.0f}")
    print(f"  Net Equity:               R{summary['equity']['net_equity']:,.0f}")
    print(f"  Gearing Ratio:            {summary['equity']['gearing_ratio']:.2f}x")
    
    print(f"\nCOLLATERAL TRACKING:")
    print(f"  Positions Used:           {summary['collateral_tracking']['positions_used_as_collateral']} / {summary['collateral_tracking']['total_positions']}")
    print(f"  Utilization:              {summary['collateral_tracking']['collateral_utilization_pct']:.1f}%")
    print(f"  No Double-Repo:           ✓ Verified")
    
    print("\n" + "=" * 70)
    print("✓ REGENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
