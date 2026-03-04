"""
Data Loaders
============

Load and save portfolio, repo, and market data with proper error handling.
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import logging

from ..core.config import HISTORICAL_DATA_FILE, PORTFOLIO_FILE, REPO_TRADES_FILE

logger = logging.getLogger(__name__)


def load_historical_jibar(filepath: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Load historical JIBAR and swap data from Excel.
    
    Args:
        filepath: Path to Excel file (default: JIBAR_FRA_SWAPS.xlsx)
    
    Returns:
        DataFrame with historical market data or None if error
    """
    if filepath is None:
        filepath = HISTORICAL_DATA_FILE
    
    try:
        df = pd.read_excel(filepath)
        df['Date'] = pd.to_datetime(df['Date'])
        logger.info(f"Loaded {len(df)} rows of historical data from {filepath}")
        return df
    except FileNotFoundError:
        logger.warning(f"Historical data file not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return None


def load_portfolio(filepath: Optional[str] = None) -> List[Dict]:
    """
    Load portfolio positions from JSON file.
    
    Args:
        filepath: Path to portfolio JSON (default: portfolio.json)
    
    Returns:
        List of position dictionaries
    """
    if filepath is None:
        filepath = PORTFOLIO_FILE
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        positions = data.get('positions', [])
        logger.info(f"Loaded {len(positions)} positions from {filepath}")
        return positions
    
    except FileNotFoundError:
        logger.warning(f"Portfolio file not found: {filepath}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in portfolio file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return []


def load_repo_trades(filepath: Optional[str] = None) -> List[Dict]:
    """
    Load repo trades from JSON file.
    
    Args:
        filepath: Path to repo trades JSON (default: repo_trades.json)
    
    Returns:
        List of repo trade dictionaries
    """
    if filepath is None:
        filepath = REPO_TRADES_FILE
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        repos = data.get('repos', [])
        logger.info(f"Loaded {len(repos)} repo trades from {filepath}")
        return repos
    
    except FileNotFoundError:
        logger.warning(f"Repo trades file not found: {filepath}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in repo trades file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading repo trades: {e}")
        return []


def save_portfolio(positions: List[Dict], filepath: Optional[str] = None) -> bool:
    """
    Save portfolio positions to JSON file.
    
    Args:
        positions: List of position dictionaries
        filepath: Path to save to (default: portfolio.json)
    
    Returns:
        bool: True if successful
    """
    if filepath is None:
        filepath = PORTFOLIO_FILE
    
    try:
        data = {'positions': positions}
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(positions)} positions to {filepath}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")
        return False


def save_repo_trades(repos: List[Dict], filepath: Optional[str] = None) -> bool:
    """
    Save repo trades to JSON file.
    
    Args:
        repos: List of repo trade dictionaries
        filepath: Path to save to (default: repo_trades.json)
    
    Returns:
        bool: True if successful
    """
    if filepath is None:
        filepath = REPO_TRADES_FILE
    
    try:
        data = {'repos': repos}
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(repos)} repo trades to {filepath}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving repo trades: {e}")
        return False


def get_data_status() -> Dict[str, bool]:
    """
    Check which data files are available.
    
    Returns:
        Dictionary with file availability status
    """
    return {
        'historical_data': Path(HISTORICAL_DATA_FILE).exists(),
        'portfolio': Path(PORTFOLIO_FILE).exists(),
        'repo_trades': Path(REPO_TRADES_FILE).exists()
    }
