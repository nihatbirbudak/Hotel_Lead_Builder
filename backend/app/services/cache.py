"""
SQLite-based caching for discovery results.
Prevents redundant HTTP requests and speeds up repeated searches.
"""
import sqlite3
import json
import time
import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cache')
CACHE_DB = os.path.join(CACHE_DIR, 'discovery_cache.db')
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def init_cache_db():
    """Initialize cache database with required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # DNS cache - stores domain existence checks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dns_cache (
                domain TEXT PRIMARY KEY,
                domain_exists INTEGER,
                checked_at REAL
            )
        ''')
        
        # Website validation cache - stores validation results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_cache (
                url TEXT PRIMARY KEY,
                is_hotel INTEGER,
                confidence REAL,
                indicators TEXT,
                checked_at REAL
            )
        ''')
        
        # Domain check cache - stores HTTP HEAD results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS domain_cache (
                domain TEXT PRIMARY KEY,
                status_code INTEGER,
                final_url TEXT,
                checked_at REAL
            )
        ''')
        
        # Search results cache
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                results TEXT,
                searched_at REAL
            )
        ''')
        
        conn.commit()

@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(CACHE_DB, timeout=10)
    try:
        yield conn
    finally:
        conn.close()

def is_cache_valid(checked_at: float, ttl: int = CACHE_TTL_SECONDS) -> bool:
    """Check if cache entry is still valid."""
    return (time.time() - checked_at) < ttl

# ============================================================
# DNS CACHE
# ============================================================

def get_dns_cache(domain: str) -> Optional[bool]:
    """Get cached DNS result. Returns None if not cached or expired."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT domain_exists, checked_at FROM dns_cache WHERE domain = ?',
                (domain.lower(),)
            )
            row = cursor.fetchone()
            
            if row and is_cache_valid(row[1]):
                return bool(row[0])
    except Exception as e:
        logging.debug(f"[CACHE] DNS cache read error: {e}")
    return None

def set_dns_cache(domain: str, exists: bool):
    """Cache DNS lookup result."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO dns_cache (domain, domain_exists, checked_at)
                   VALUES (?, ?, ?)''',
                (domain.lower(), int(exists), time.time())
            )
            conn.commit()
    except Exception as e:
        logging.debug(f"[CACHE] DNS cache write error: {e}")

# ============================================================
# DOMAIN HTTP CACHE
# ============================================================

def get_domain_cache(domain: str) -> Optional[Dict]:
    """Get cached domain HTTP check result."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT status_code, final_url, checked_at FROM domain_cache WHERE domain = ?',
                (domain.lower(),)
            )
            row = cursor.fetchone()
            
            if row and is_cache_valid(row[2]):
                return {
                    'status_code': row[0],
                    'final_url': row[1]
                }
    except Exception as e:
        logging.debug(f"[CACHE] Domain cache read error: {e}")
    return None

def set_domain_cache(domain: str, status_code: int, final_url: str = None):
    """Cache domain HTTP check result."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO domain_cache (domain, status_code, final_url, checked_at)
                   VALUES (?, ?, ?, ?)''',
                (domain.lower(), status_code, final_url, time.time())
            )
            conn.commit()
    except Exception as e:
        logging.debug(f"[CACHE] Domain cache write error: {e}")

# ============================================================
# VALIDATION CACHE
# ============================================================

def get_validation_cache(url: str) -> Optional[Dict]:
    """Get cached validation result."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT is_hotel, confidence, indicators, checked_at FROM validation_cache WHERE url = ?',
                (url.lower(),)
            )
            row = cursor.fetchone()
            
            if row and is_cache_valid(row[3]):
                return {
                    'is_hotel': bool(row[0]),
                    'confidence': row[1],
                    'indicators': json.loads(row[2]) if row[2] else []
                }
    except Exception as e:
        logging.debug(f"[CACHE] Validation cache read error: {e}")
    return None

def set_validation_cache(url: str, is_hotel: bool, confidence: float, indicators: list):
    """Cache validation result."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO validation_cache (url, is_hotel, confidence, indicators, checked_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (url.lower(), int(is_hotel), confidence, json.dumps(indicators), time.time())
            )
            conn.commit()
    except Exception as e:
        logging.debug(f"[CACHE] Validation cache write error: {e}")

# ============================================================
# SEARCH CACHE
# ============================================================

def get_search_cache(query: str) -> Optional[list]:
    """Get cached search results."""
    import hashlib
    query_hash = hashlib.md5(query.lower().encode()).hexdigest()
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT results, searched_at FROM search_cache WHERE query_hash = ?',
                (query_hash,)
            )
            row = cursor.fetchone()
            
            # Search cache expires faster (1 day)
            if row and is_cache_valid(row[1], ttl=24*60*60):
                return json.loads(row[0]) if row[0] else []
    except Exception as e:
        logging.debug(f"[CACHE] Search cache read error: {e}")
    return None

def set_search_cache(query: str, results: list):
    """Cache search results."""
    import hashlib
    query_hash = hashlib.md5(query.lower().encode()).hexdigest()
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO search_cache (query_hash, results, searched_at)
                   VALUES (?, ?, ?)''',
                (query_hash, json.dumps(results), time.time())
            )
            conn.commit()
    except Exception as e:
        logging.debug(f"[CACHE] Search cache write error: {e}")

# ============================================================
# CACHE MANAGEMENT
# ============================================================

def clear_expired_cache():
    """Remove expired cache entries."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cutoff = time.time() - CACHE_TTL_SECONDS
            
            cursor.execute('DELETE FROM dns_cache WHERE checked_at < ?', (cutoff,))
            cursor.execute('DELETE FROM domain_cache WHERE checked_at < ?', (cutoff,))
            cursor.execute('DELETE FROM validation_cache WHERE checked_at < ?', (cutoff,))
            
            # Search cache has shorter TTL
            search_cutoff = time.time() - (24 * 60 * 60)
            cursor.execute('DELETE FROM search_cache WHERE searched_at < ?', (search_cutoff,))
            
            conn.commit()
            logging.info(f"[CACHE] Expired entries cleared")
    except Exception as e:
        logging.debug(f"[CACHE] Clear expired error: {e}")

def get_cache_stats() -> Dict:
    """Get cache statistics."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            for table in ['dns_cache', 'domain_cache', 'validation_cache', 'search_cache']:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[table] = cursor.fetchone()[0]
            
            return stats
    except Exception as e:
        return {'error': str(e)}

# Initialize database on module load
init_cache_db()
