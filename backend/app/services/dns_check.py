"""
DNS Pre-check module for fast domain validation.
Uses socket-based DNS lookup which is much faster than HTTP requests.
"""
import socket
import logging
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .cache import get_dns_cache, set_dns_cache

# DNS timeout (very short since DNS is fast)
DNS_TIMEOUT = 2.0

def check_domain_exists(domain: str) -> bool:
    """
    Fast DNS check to see if domain exists.
    Much faster than HTTP HEAD request (typically <100ms vs 1-2s).
    
    Args:
        domain: Domain name without protocol (e.g., 'example.com')
    
    Returns:
        True if domain resolves, False otherwise
    """
    # Check cache first
    cached = get_dns_cache(domain)
    if cached is not None:
        logging.debug(f"[DNS] Cache hit for {domain}: {cached}")
        return cached
    
    # Clean domain - remove protocol if present
    domain = domain.replace('http://', '').replace('https://', '')
    domain = domain.replace('www.', '')
    domain = domain.split('/')[0]  # Remove path if present
    
    try:
        socket.setdefaulttimeout(DNS_TIMEOUT)
        socket.gethostbyname(domain)
        set_dns_cache(domain, True)
        return True
    except socket.gaierror:
        # Domain does not exist
        set_dns_cache(domain, False)
        return False
    except socket.timeout:
        # Timeout - don't cache, might be temporary
        return False
    except Exception as e:
        logging.debug(f"[DNS] Error checking {domain}: {e}")
        return False

def batch_check_domains(domains: List[str], max_workers: int = 10) -> List[Tuple[str, bool]]:
    """
    Check multiple domains in parallel for faster processing.
    
    Args:
        domains: List of domain names to check
        max_workers: Maximum concurrent checks
    
    Returns:
        List of (domain, exists) tuples
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {
            executor.submit(check_domain_exists, domain): domain 
            for domain in domains
        }
        
        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                exists = future.result()
                results.append((domain, exists))
            except Exception as e:
                logging.debug(f"[DNS] Batch check error for {domain}: {e}")
                results.append((domain, False))
    
    return results

def filter_existing_domains(url_list: List[str]) -> List[str]:
    """
    Filter a list of URLs to only those with existing domains.
    Uses batch DNS checking for speed.
    
    Args:
        url_list: List of URLs to check
    
    Returns:
        List of URLs with valid DNS
    """
    # Extract unique domains from URLs
    domain_to_urls = {}
    for url in url_list:
        domain = url.replace('http://', '').replace('https://', '')
        domain = domain.replace('www.', '').split('/')[0]
        
        if domain not in domain_to_urls:
            domain_to_urls[domain] = []
        domain_to_urls[domain].append(url)
    
    # Batch check all domains
    domains = list(domain_to_urls.keys())
    check_results = batch_check_domains(domains)
    
    # Filter to only existing domains
    existing_domains = {domain for domain, exists in check_results if exists}
    
    # Return only URLs with existing domains
    valid_urls = []
    for domain, urls in domain_to_urls.items():
        if domain in existing_domains:
            valid_urls.extend(urls)
    
    logging.info(f"[DNS] Filtered {len(url_list)} URLs to {len(valid_urls)} with valid DNS")
    return valid_urls

def get_dns_stats(domains: List[str]) -> dict:
    """
    Get statistics about domain DNS status.
    
    Returns:
        Dict with 'total', 'existing', 'not_found' counts
    """
    results = batch_check_domains(domains)
    existing = sum(1 for _, exists in results if exists)
    
    return {
        'total': len(domains),
        'existing': existing,
        'not_found': len(domains) - existing,
        'success_rate': existing / len(domains) * 100 if domains else 0
    }
