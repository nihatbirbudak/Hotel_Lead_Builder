import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import random

# Standard email regex
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Priority pages for email search
PRIORITY_KEYWORDS = ['contact', 'iletisim', 'about', 'hakkimizda', 'info', 'ulasim', 'bize-ulasin', 'bizeulasin', 'communication']

# Common email obfuscation patterns to detect
OBFUSCATION_PATTERNS = [
    # [at] and [dot] variants
    (r'([a-zA-Z0-9._%+-]+)\s*\[\s*at\s*\]\s*([a-zA-Z0-9.-]+)\s*\[\s*dot\s*\]\s*([a-zA-Z]{2,})', r'\1@\2.\3'),
    (r'([a-zA-Z0-9._%+-]+)\s*\(\s*at\s*\)\s*([a-zA-Z0-9.-]+)\s*\(\s*dot\s*\)\s*([a-zA-Z]{2,})', r'\1@\2.\3'),
    (r'([a-zA-Z0-9._%+-]+)\s*\{\s*at\s*\}\s*([a-zA-Z0-9.-]+)\s*\{\s*dot\s*\}\s*([a-zA-Z]{2,})', r'\1@\2.\3'),
    
    # AT and DOT written out
    (r'([a-zA-Z0-9._%+-]+)\s+at\s+([a-zA-Z0-9.-]+)\s+dot\s+([a-zA-Z]{2,})', r'\1@\2.\3'),
    (r'([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+)\s+DOT\s+([a-zA-Z]{2,})', r'\1@\2.\3'),
    
    # Turkish variants
    (r'([a-zA-Z0-9._%+-]+)\s*\[\s*et\s*\]\s*([a-zA-Z0-9.-]+)\s*\[\s*nokta\s*\]\s*([a-zA-Z]{2,})', r'\1@\2.\3'),
    (r'([a-zA-Z0-9._%+-]+)\s+et\s+([a-zA-Z0-9.-]+)\s+nokta\s+([a-zA-Z]{2,})', r'\1@\2.\3'),
    
    # HTML entity variants (&#64; = @, &#46; = .)
    (r'([a-zA-Z0-9._%+-]+)&#64;([a-zA-Z0-9.-]+)&#46;([a-zA-Z]{2,})', r'\1@\2.\3'),
    (r'([a-zA-Z0-9._%+-]+)&commat;([a-zA-Z0-9.-]+)&period;([a-zA-Z]{2,})', r'\1@\2.\3'),
    
    # Spaced out emails: i n f o @ h o t e l . c o m
    (r'([a-zA-Z0-9])\s+([a-zA-Z0-9])\s+([a-zA-Z0-9])\s+([a-zA-Z0-9])\s*@', r'\1\2\3\4@'),
]

# Invalid email patterns to filter out
INVALID_EMAIL_PATTERNS = [
    r'.*\.png$', r'.*\.jpg$', r'.*\.gif$', r'.*\.jpeg$',  # Image files
    r'.*\.js$', r'.*\.css$',  # Code files
    r'.*@example\.com$', r'.*@test\.com$',  # Example domains
    r'^noreply@', r'^no-reply@',  # No-reply addresses
    r'.*@sentry\.io$', r'.*@google\.com$',  # Service emails
    r'^[0-9]+@',  # Numeric usernames (usually not real)
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def get_headers():
    """Return headers with random user-agent"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
    }

def is_valid_email(email: str) -> bool:
    """Check if email is valid and not a false positive."""
    email = email.lower().strip()
    
    # Check against invalid patterns
    for pattern in INVALID_EMAIL_PATTERNS:
        if re.match(pattern, email, re.IGNORECASE):
            return False
    
    # Basic sanity checks
    if len(email) < 5 or len(email) > 254:
        return False
    
    # Must have exactly one @
    if email.count('@') != 1:
        return False
    
    # Domain must have at least one dot
    domain = email.split('@')[1]
    if '.' not in domain:
        return False
    
    return True

def decode_obfuscated_emails(text: str) -> set:
    """
    Decode obfuscated email addresses.
    Handles common anti-scraping patterns.
    """
    emails = set()
    
    for pattern, replacement in OBFUSCATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                email = re.sub(pattern, replacement, f"{match[0]}@{match[1]}.{match[2]}" if len(match) >= 3 else "", re.IGNORECASE)
            else:
                email = match
            
            # Clean and validate
            email = email.strip().lower()
            if is_valid_email(email):
                emails.add(email)
    
    return emails

def extract_emails_from_text(text: str) -> set:
    """
    Extract all valid emails from text.
    Handles both standard and obfuscated formats.
    """
    emails = set()
    
    # 1. Standard regex
    standard_emails = re.findall(EMAIL_REGEX, text)
    for email in standard_emails:
        email = email.lower().strip()
        if is_valid_email(email):
            emails.add(email)
    
    # 2. Obfuscated emails
    obfuscated = decode_obfuscated_emails(text)
    emails.update(obfuscated)
    
    return emails

def extract_emails_from_html(soup: BeautifulSoup) -> set:
    """
    Extract emails from HTML using multiple methods.
    """
    emails = set()
    
    # 1. Get emails from visible text
    text_emails = extract_emails_from_text(soup.get_text())
    emails.update(text_emails)
    
    # 2. Check mailto: links
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('mailto:'):
            email = href.replace('mailto:', '').split('?')[0].strip()
            if is_valid_email(email):
                emails.add(email.lower())
    
    # 3. Check data attributes (some sites hide emails in data-* attributes)
    for elem in soup.find_all(attrs={"data-email": True}):
        email = elem.get('data-email', '').strip()
        if is_valid_email(email):
            emails.add(email.lower())
    
    for elem in soup.find_all(attrs={"data-mail": True}):
        email = elem.get('data-mail', '').strip()
        if is_valid_email(email):
            emails.add(email.lower())
    
    # 4. Check meta tags
    for meta in soup.find_all('meta', attrs={"name": "email"}):
        email = meta.get('content', '').strip()
        if is_valid_email(email):
            emails.add(email.lower())
    
    # 5. Check structured data (JSON-LD)
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            import json
            data = json.loads(script.string or '{}')
            if isinstance(data, dict):
                email = data.get('email', '')
                if email and is_valid_email(email):
                    emails.add(email.lower())
        except:
            pass
    
    return emails

def score_email(email: str, domain: str) -> int:
    """
    Score an email based on quality and relevance.
    Higher score = better email candidate.
    """
    score = 0
    email_lower = email.lower()
    
    # Prefer emails with the same domain as the website
    email_domain = email.split('@')[1] if '@' in email else ''
    website_domain = domain.replace('www.', '')
    
    if email_domain == website_domain:
        score += 50  # Same domain = very relevant
    elif website_domain in email_domain or email_domain in website_domain:
        score += 30  # Related domain
    
    # Prefer info@, contact@, reservations@, etc.
    preferred_prefixes = ['info', 'contact', 'rezervasyon', 'reservation', 'booking', 'sales', 'satis', 'reception', 'resepsiyon']
    email_prefix = email_lower.split('@')[0]
    
    if email_prefix in preferred_prefixes:
        score += 40
    elif any(pref in email_prefix for pref in preferred_prefixes):
        score += 20
    
    # Penalize generic email providers (might not be business email)
    generic_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'yandex.com']
    if email_domain in generic_domains:
        score -= 20
    
    return score

def crawl_for_email(start_url: str, max_pages: int = 10) -> str:
    """
    Crawl a website to find email addresses.
    Uses priority-based crawling to check contact pages first.
    
    Args:
        start_url: Website URL to crawl
        max_pages: Maximum pages to crawl
    
    Returns:
        Best email found, or None
    """
    visited = set()
    queue = [start_url]
    found_emails = {}  # email -> score
    domain = urlparse(start_url).netloc
    
    pages_crawled = 0
    
    logging.debug(f"[CRAWLER] Starting crawl of {start_url}")
    
    while queue and pages_crawled < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        
        # Skip non-HTML resources
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.css', '.js', '.zip', '.doc']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            continue
            
        try:
            resp = requests.get(url, headers=get_headers(), timeout=10, allow_redirects=True)
            
            # Only process HTML
            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower() and 'application/xhtml' not in content_type.lower():
                continue
            
            visited.add(url)
            pages_crawled += 1
            
            try:
                soup = BeautifulSoup(resp.text, 'lxml')
            except:
                soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract emails using all methods
            page_emails = extract_emails_from_html(soup)
            
            # Also extract from raw HTML (catches some edge cases)
            raw_emails = extract_emails_from_text(resp.text)
            page_emails.update(raw_emails)
            
            # Score and store emails
            for email in page_emails:
                email = email.lower().strip()
                if is_valid_email(email):
                    email_score = score_email(email, domain)
                    # Add bonus if found on contact page
                    if any(k in url.lower() for k in PRIORITY_KEYWORDS):
                        email_score += 15
                    
                    if email not in found_emails or found_emails[email] < email_score:
                        found_emails[email] = email_score
                        logging.debug(f"[CRAWLER] Found email: {email} (score: {email_score})")
            
            # Queue internal links
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                # Skip mailto and javascript links
                if href.startswith('mailto:') or href.startswith('javascript:'):
                    continue
                
                # Build full URL
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                
                # Only follow internal links
                if parsed.netloc == domain and full_url not in visited:
                    # Remove fragment
                    full_url = full_url.split('#')[0]
                    
                    if full_url in visited:
                        continue
                    
                    # Priority sorting - contact pages first
                    is_priority = any(k in full_url.lower() for k in PRIORITY_KEYWORDS)
                    
                    if is_priority:
                        queue.insert(0, full_url)
                    else:
                        queue.append(full_url)
            
            # Early return if we found a high-quality email
            if found_emails:
                best_email = max(found_emails.keys(), key=lambda e: found_emails[e])
                if found_emails[best_email] >= 70:  # High confidence
                    logging.info(f"[CRAWLER] High-confidence email found: {best_email}")
                    return best_email
                
        except requests.RequestException as e:
            logging.debug(f"[CRAWLER] Request error for {url}: {e}")
        except Exception as e:
            logging.debug(f"[CRAWLER] Error processing {url}: {e}")
    
    # Return best email found (if any)
    if found_emails:
        best_email = max(found_emails.keys(), key=lambda e: found_emails[e])
        logging.info(f"[CRAWLER] Best email: {best_email} (score: {found_emails[best_email]})")
        return best_email
    
    logging.debug(f"[CRAWLER] No emails found on {start_url}")
    return None

