"""
yfinance Cache Module
Caches yfinance API calls using local SQLite database with 30-minute TTL.
"""

import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta
from functools import wraps
from decimal import Decimal
import pandas as pd

# Cache configuration
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DB = os.path.join(CACHE_DIR, 'yfinance_cache.db')
CACHE_TTL_MINUTES = 30


def _get_db_connection():
    """Get SQLite database connection, creating db if needed."""
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """Initialize cache database and table if they don't exist."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS yfinance_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def _make_cache_key(prefix, *args, **kwargs):
    """Generate a unique cache key from function name and arguments."""
    key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()


def _serialize_data(data):
    """Serialize data for JSON storage, handling pandas DataFrames and datetime objects."""
    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to dict with serializable types
        result = data.to_dict(orient='records')
        return [_serialize_data(row) for row in result]
    elif isinstance(data, pd.Series):
        return _serialize_data(data.to_dict())
    elif isinstance(data, dict):
        return {k: _serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_serialize_data(item) for item in data]
    elif isinstance(data, (datetime, pd.Timestamp)):
        return data.isoformat()
    elif isinstance(data, (float, int, str, bool, type(None))):
        return data
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return str(data)


def _get_from_cache(cache_key):
    """Retrieve data from cache if it exists and hasn't expired."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT data, created_at FROM yfinance_cache WHERE cache_key = ?',
        (cache_key,)
    )
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        return None
    
    data = row[0]
    created_at = datetime.fromisoformat(row[1])
    conn.close()
    
    # Check if expired
    if datetime.now() - created_at > timedelta(minutes=CACHE_TTL_MINUTES):
        return None
    
    return json.loads(data)


def _save_to_cache(cache_key, data):
    """Save data to cache with current timestamp."""
    # Serialize data (handle pandas DataFrames)
    serialized_data = _serialize_data(data)
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR REPLACE INTO yfinance_cache (cache_key, data, created_at) VALUES (?, ?, ?)',
        (cache_key, json.dumps(serialized_data), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def cached_yfinance(prefix):
    """
    Decorator to cache yfinance function calls.
    
    Usage:
        @cached_yfinance("stock_info")
        def get_stock_info(ticker):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _make_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_data = _get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Call the original function
            result = func(*args, **kwargs)
            
            # Save to cache (only if result is not None)
            if result is not None:
                _save_to_cache(cache_key, result)
            
            return result
        return wrapper
    return decorator


# Initialize database on module import
_init_db()
