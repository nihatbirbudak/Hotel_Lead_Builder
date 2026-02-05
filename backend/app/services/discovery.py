import requests
from bs4 import BeautifulSoup
import tldextract
import time
from urllib.parse import urlparse, parse_qs, urlsplit
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Tuple

# Import new modules
from .cache import (
    get_dns_cache, set_dns_cache,
    get_domain_cache, set_domain_cache,
    get_validation_cache, set_validation_cache,
    get_search_cache, set_search_cache
)
from .dns_check import check_domain_exists, filter_existing_domains
from .circuit_breaker import ddg_circuit, http_circuit, CircuitOpenError

# OTA and Social Media Blacklist
BLACKLIST_DOMAINS = {
    'booking.com', 'tripadvisor', 'trivago', 'etstur.com', 'hotels.com',
    'expedia', 'tatilbudur.com', 'agoda.com', 'facebook.com', 'instagram.com',
    'twitter.com', 'linkedin.com', 'youtube.com', 'google.com', 'wikipedia',
    'enuygun.com', 'obilet.com', 'skyscanner.com', 'skyscanner.com.tr',
    'hotel-istanbul.net', 'hotel-of-istanbul.com', 'hotel-tr.com',
    'otelz.com', 'otelz.com.tr', 'jollytur.com', 'tatilsepeti.com',
    'setur.com.tr', 'neredekal.com', 'gezimanya.com', 'trip.com'
}

# Hotel content indicators
HOTEL_KEYWORDS = {
    'english': ['hotel', 'resort', 'motel', 'guest house', 'lodge', 'inn', 'villa', 'room', 'accommodation', 'booking', 'reserve', 'check-in', 'check-out'],
    'turkish': ['otel', 'resort', 'pansiyon', 'konuk evi', 'konak', 'yatakhane', 'apart', 'kamp', 'oda', 'konaklama', 'rezervasyon', 'giriş', 'çıkış', 'tur', 'turizm'],
    'location': ['türkiye', 'turkey', 'telefon', 'phone', '+90', 'adres', 'address', 'konum', 'location']
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def get_headers():
    """Return headers with random user-agent"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9',
        'Referer': 'https://duckduckgo.com/',
    }

def validate_hotel_content(url: str, hotel_name: str = None, city: str = None) -> dict:
    """
    CLEAN VALIDATION ALGORITHM - Priority-based scoring with caching
    
    Priority 1: Domain keywords (40 pts) - Most reliable
    Priority 2: City match (40 pts) - Second most reliable
    → If P1 + P2 >= 70 pts: IMMEDIATE PASS (skip HTML parsing)
    
    Fallback: HTML content analysis (only if needed)
    
    Args:
        url: Website URL to validate
        hotel_name: Hotel name for matching
        city: City name (şehir) - CRITICAL for validation
    
    Returns: {'is_hotel': bool, 'confidence': 0-100, 'indicators': [list]}
    """
    # Check cache first
    cached = get_validation_cache(url)
    if cached is not None:
        logging.debug(f"[VALIDATION] Cache hit for {url}")
        return cached
    
    indicators = []
    score = 0.0
    
    # ============================================================
    # PRIORITY 1: DOMAIN ANALYSIS (40 pts max)
    # ============================================================
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Hotel keywords in domain = VERY strong signal
        domain_keywords = ['hotel', 'otel', 'resort', 'apart', 'pansiyon', 'villa', 'lodge', 'inn', 'motel']
        has_hotel_keyword = any(kw in domain for kw in domain_keywords)
        
        # Hotel brand keywords = EQUALLY strong for chain hotels
        brand_keywords = ['hyatt', 'hilton', 'marriott', 'radisson', 'sheraton', 
                         'accor', 'ibis', 'novotel', 'mercure', 'sofitel',
                         'ramada', 'wyndham', 'holiday inn', 'crowne plaza',
                         'intercontinental', 'doubletree', 'hampton', 'embassy']
        has_brand_keyword = any(brand in domain for brand in brand_keywords)
        
        if has_hotel_keyword:
            score += 40
            indicators.append(f"✓ Hotel keyword in domain: {domain}")
        elif has_brand_keyword:
            score += 35
            indicators.append(f"✓ Hotel brand in domain: {domain}")
        
    except Exception as e:
        logging.debug(f"[VALIDATION] Domain analysis error: {str(e)[:50]}")
    
    # ============================================================
    # PRIORITY 2: CITY VALIDATION (40 pts max)
    # ============================================================
    # City match = Very strong signal (same name + same city = correct hotel)
    city_matched = False
    
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        if resp.status_code != 200:
            # If domain was good, accept even without content
            if score >= 40:
                result = {'is_hotel': True, 'confidence': 80, 'indicators': indicators + ['⚠ HTTP non-200 but domain is hotel']}
                set_validation_cache(url, result['is_hotel'], result['confidence'], result['indicators'])
                return result
            result = {'is_hotel': False, 'confidence': 0, 'indicators': ['✗ HTTP not 200']}
            set_validation_cache(url, result['is_hotel'], result['confidence'], result['indicators'])
            return result
        
        content = resp.text.lower()
        
        # Check city in content (case-insensitive)
        if city:
            city_lower = city.lower()
            # Try multiple variants: lowercase, Title Case, UPPERCASE
            city_variants = [city_lower, city.capitalize(), city.upper()]
            city_matched = any(variant in content for variant in city_variants)
            
            if city_matched:
                score += 40
                indicators.append(f"✓ City matched: {city}")
        
        # ============================================================
        # FAST DECISION: Domain (40) + City (40) = 80+ pts → PASS
        # ============================================================
        if score >= 70:
            indicators.append(f"✓ FAST PASS: Domain + City = {score} pts")
            result = {'is_hotel': True, 'confidence': min(score + 20, 100), 'indicators': indicators}
            set_validation_cache(url, result['is_hotel'], result['confidence'], result['indicators'])
            return result
        
        # ============================================================
        # FALLBACK: HTML CONTENT ANALYSIS (only if needed)
        # ============================================================
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Title check
        title = soup.find('title')
        title_text = title.get_text().lower() if title else ""
        if title_text and ('hotel' in title_text or 'otel' in title_text or 'resort' in title_text):
            score += 20
            indicators.append("✓ Hotel keyword in title")
        
        # Hotel keywords (English OR Turkish)
        english_kw = sum(1 for kw in HOTEL_KEYWORDS['english'] if kw in content)
        turkish_kw = sum(1 for kw in HOTEL_KEYWORDS['turkish'] if kw in content)
        
        if english_kw >= 2:
            score += 20
            indicators.append(f"✓ English keywords: {english_kw}")
        elif turkish_kw >= 2:
            score += 20
            indicators.append(f"✓ Turkish keywords: {turkish_kw}")
        
        # Phone validation (flexible patterns)
        import re
        phone_patterns = [
            r'\+90[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',  # +90 532 123 45 67
            r'0[2-5]\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',  # 0212 123 45 67
            r'444[\s\-]?\d{1}[\s\-]?\d{3}',  # 444 1 234
        ]
        has_phone = any(re.search(pattern, content) for pattern in phone_patterns)
        if has_phone:
            score += 15
            indicators.append("✓ Phone number found")
        
        # Final decision
        if score >= 50:
            result = {'is_hotel': True, 'confidence': min(score, 100), 'indicators': indicators}
            set_validation_cache(url, result['is_hotel'], result['confidence'], result['indicators'])
            return result
        else:
            result = {'is_hotel': False, 'confidence': score, 'indicators': indicators + ['✗ Score too low']}
            set_validation_cache(url, result['is_hotel'], result['confidence'], result['indicators'])
            return result
            
    except Exception as e:
        # If domain was good, accept even with content error
        if score >= 40:
            result = {'is_hotel': True, 'confidence': min(score + 10, 100), 'indicators': indicators + [f'⚠ Content error but domain is hotel']}
            set_validation_cache(url, result['is_hotel'], result['confidence'], result['indicators'])
            return result
        
        logging.debug(f"[VALIDATION] Content error for {url}: {str(e)[:50]}")
        result = {'is_hotel': False, 'confidence': 0, 'indicators': [f"✗ Error: {type(e).__name__}"]}
        # Don't cache errors - they might be temporary
        return result


def _normalize_name_for_search(name: str) -> str:
    """Normalize a hotel name for search and domain guessing."""
    # Prefer the part before a hyphen for relevance (e.g., "... - SULTANAHMET")
    base = name.split("-")[0].strip() if "-" in name else name
    # Remove bracketed content
    base = re.sub(r"\(.*?\)|\[.*?\]", "", base)
    # Collapse extra whitespace
    base = re.sub(r"\s+", " ", base).strip()
    return base

def _build_progressive_queries(hotel_name: str, city: str) -> list[str]:
    """
    Build progressively longer search queries using the most relevant tokens first.
    If no exact match found, expand with more tokens.
    """
    # Split on hyphen to capture location-like suffixes
    parts = [p.strip() for p in hotel_name.split("-")]
    base = parts[0].lower() if parts else hotel_name.lower()
    suffix = parts[1].lower() if len(parts) > 1 else ""
    tokens = re.split(r"\s+", base)
    tokens = [t for t in tokens if t]
    suffix_tokens = re.split(r"\s+", suffix) if suffix else []
    suffix_tokens = [t for t in suffix_tokens if t]

    # Remove generic words to keep high-relevance tokens
    stopwords = {
        "the", "a", "an", "and", "or", "in", "at", "by", "for", "of", "to",
        "special", "class", "boutique", "luxury", "deluxe"
    }
    type_words = {
        "hotel", "otel", "resort", "spa", "apart", "pansiyon", "motel",
        "pension", "guest", "house", "hostel", "lodge", "inn"
    }

    core_tokens = [t for t in tokens if t not in stopwords and t not in type_words]
    if not core_tokens:
        core_tokens = [t for t in tokens if t not in stopwords]

    # Progressive expansion: start with 1-2 core tokens, then add more
    progressive = []
    start_len = 2 if len(core_tokens) >= 2 else 1
    for i in range(start_len, len(core_tokens) + 1):
        progressive.append(core_tokens[:i])

    # Also try a numeric-stripped variant (useful for names like "1207 ...")
    core_no_numbers = [t for t in core_tokens if not t.isdigit()]
    if core_no_numbers and core_no_numbers != core_tokens:
        start_len = 2 if len(core_no_numbers) >= 2 else 1
        for i in range(start_len, len(core_no_numbers) + 1):
            progressive.append(core_no_numbers[:i])

    # Add full token list at the end as a fallback
    if tokens:
        progressive.append(tokens)

    queries = []
    location_hint = " ".join(suffix_tokens) if suffix_tokens else ""

    for token_list in progressive:
        if not token_list:
            continue
        # Ensure a type word exists at the end for better intent
        has_type = any(t in type_words for t in token_list)
        if not has_type:
            token_list = token_list + ["hotel"]
        phrase = " ".join(token_list)
        if len(phrase) < 3:
            continue
        queries.append(f"\"{phrase}\" {city} otel")
        queries.append(f"{phrase} {city} otel")

        if location_hint:
            queries.append(f"\"{phrase}\" {location_hint} otel")
            queries.append(f"{phrase} {location_hint} otel")

        # If we have a suffix (like SULTANAHMET), try with it appended
        if suffix_tokens:
            phrase_with_suffix = " ".join(token_list + suffix_tokens)
            if len(phrase_with_suffix) >= 3:
                queries.append(f"\"{phrase_with_suffix}\" {city} otel")
                queries.append(f"{phrase_with_suffix} {city} otel")

    # De-dup but preserve order
    seen = set()
    deduped = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)
    return deduped

def _is_relevant_domain(hotel_name: str, url: str) -> bool:
    """
    Check if domain is relevant to hotel name.
    Less restrictive - give domains a chance!
    If domain looks hotel-ish or has name tokens, accept it and let validation decide.
    """
    stopwords = {
        "the", "a", "an", "and", "or", "in", "at", "by", "for", "of", "to",
        "special", "class", "boutique", "luxury", "deluxe"
    }
    hotel_keywords = {
        "hotel", "hotels", "otel", "oteller", "resort", "spa", "apart",
        "pansiyon", "motel", "pension", "guest", "house", "hostel", "lodge", "inn"
    }

    try:
        ext = tldextract.extract(url)
        domain = ext.domain.lower()
    except Exception:
        return False

    # Strategy 1: Domain is purely generic type word (reject)
    if domain in hotel_keywords and len(domain) < 6:
        return False

    # Strategy 2: Domain has hotel keyword (accept - it's probably a hotel!)
    for kw in hotel_keywords:
        if kw in domain:
            return True

    # Strategy 3: Domain matches hotel name tokens (accept)
    tokens = re.split(r"\s+", hotel_name.lower())
    tokens = [t for t in tokens if len(t) > 2 and t not in stopwords and t not in hotel_keywords]

    for token in tokens:
        token_clean = re.sub(r"\d+", "", token)
        if len(token_clean) >= 3 and token_clean in domain:
            return True

    # Strategy 4: Domain is fairly long and doesn't look generic (accept and validate)
    # Examples: pearlhotelistanbul, alexiaresort, admiralotel = probably real
    if len(domain) >= 6:
        return True

    # Otherwise reject
    return False


def calculate_score(hotel_name: str, found_url: str, title: str) -> float:
    score = 0.0
    
    # Normalize - keep original and clean versions
    name_tokens = set(hotel_name.lower().split())
    # Filter out very short tokens and common words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'in', 'at', 'by', 'for', 'of', 'to', 'is'}
    name_tokens = set(t for t in name_tokens if len(t) > 2 and t not in stopwords)
    
    if not name_tokens:
        name_tokens = set(hotel_name.lower().split())
    
    # 1. Domain Token Overlap (IMPROVED)
    domain_info = tldextract.extract(found_url)
    domain_name = domain_info.domain.lower()
    
    # Remove numbers from domain for better matching (01novaotel -> novaotel)
    import re
    domain_name_clean = re.sub(r'\d+', '', domain_name)
    
    # Check match with multiple strategies
    matches = 0
    for token in name_tokens:
        token_clean = re.sub(r'\d+', '', token)
        
        # Strategy 1: Direct substring match
        if token in domain_name or token_clean in domain_name:
            matches += 1
        # Strategy 2: Clean domain match
        elif token_clean in domain_name_clean:
            matches += 1
        # Strategy 3: Partial match (at least 4 chars of token match)
        elif len(token_clean) >= 4:
            # Check if token starts with domain or vice versa
            if domain_name_clean.startswith(token_clean[:4]) or token_clean.startswith(domain_name_clean[:4]):
                matches += 0.5
    
    if name_tokens:
        score += (matches / len(name_tokens)) * 45  # Up to 45 points
    
    # 2. Keywords in Domain (higher weight for hotel-specific keywords)
    hotel_keywords = ['hotel', 'otel', 'resort', 'apart', 'pansiyon', 'villa', 'lodge', 'inn', 'motel', 'pension']
    for keyword in hotel_keywords:
        if keyword in domain_name:
            score += 20
            break  # Only count once
    
    # 3. Title Check - more lenient
    if title:
        title_lower = title.lower()
        hotel_name_lower = hotel_name.lower()
        
        # Check if hotel name is in title
        if hotel_name_lower in title_lower:
            score += 30
        else:
            # Check key word matches in title
            matches_in_title = sum(1 for token in name_tokens if len(token) > 3 and token in title_lower)
            if matches_in_title > 0:
                score += min(matches_in_title * 10, 25)
    
    # 4. Domain length bonus (longer domain = more specific)
    if len(domain_name) > 8:
        score += 10
    elif len(domain_name) > 5:
        score += 5
        
    return min(score, 100.0)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def search_ddg_html(query: str):
    """Search DuckDuckGo HTML endpoint with retry logic and circuit breaker"""
    
    def _do_search():
        url = "https://html.duckduckgo.com/html/"
        logging.debug(f"[DISCOVERY] DDG API'ye istek gönderiliyor: {query}")
        
        resp = requests.post(
            url, 
            data={'q': query}, 
            headers=get_headers(), 
            timeout=15
        )
        
        # Accept 200 or 202 (Accepted) responses
        if resp.status_code not in (200, 202):
            logging.warning(f"[DISCOVERY] DDG HTTP {resp.status_code}")
            resp.raise_for_status()
        
        return resp.text
    
    try:
        return ddg_circuit.call(_do_search)
    except CircuitOpenError:
        logging.warning("[DISCOVERY] DDG circuit breaker open, search skipped")
        return ""
    except Exception as e:
        logging.warning(f"[DISCOVERY] DDG search failed: {e}")
        raise

def find_website(hotel_name: str, city: str):
    """
    Find hotel website using strategies:
    1. Direct domain guessing (fastest, no network)
    2. DuckDuckGo search (reliable, bot-friendly)
    3. Alternative patterns
    """
    hotel_name = (hotel_name or "").strip()
    city = (city or "").strip().lower()
    
    if not hotel_name:
        return None

    reason = None
    domain_any_checked = False
    domain_any_relevant = False
    domain_any_valid = False
    ddg_any_candidates = False
    ddg_any_relevant = False
    ddg_any_valid = False
    alt_any_checked = False
    alt_any_relevant = False
    alt_any_valid = False
    
    # Strategy 1: Try direct domain guessing
    logging.info(f"[DISCOVERY] Aranıyor: {hotel_name} ({city})")
    
    # Clean hotel name for domain - improve cleaning
    base_name = _normalize_name_for_search(hotel_name)
    clean_name = base_name.lower()
    
    # Preserve original tokens before stripping numeric prefixes
    import re
    raw_name = clean_name
    # Remove numeric prefixes (01, 05, etc.)
    clean_name = re.sub(r'^\d+\s+', '', clean_name)
    
    # CRITICAL: Clean special characters that break tokenization
    # Replace & with empty string (removes it), remove other harmful special chars
    clean_name = clean_name.replace('&', '')  # Just remove &, don't replace with "and"
    clean_name = re.sub(r'[^a-zA-Z0-9\sşğıüçöŞĞİÜÇÖ-]', '', clean_name)
    
    # Remove ONLY "type" suffixes, NOT descriptive words
    # Type suffixes: otel, pansiyon, hotel, motel, etc. (these tell WHAT it is)
    # Descriptive words: mountain, beach, peak, hill (these are PART OF NAME)
    # CRITICAL: Handle Turkish characters - convert all to ASCII before suffix check
    temp_check_name = clean_name.lower()
    temp_check_name = temp_check_name.replace('İ', 'i').replace('Ş', 's').replace('Ğ', 'g').replace('Ü', 'u').replace('Ç', 'c').replace('Ö', 'o')
    temp_check_name = temp_check_name.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ç', 'c').replace('ö', 'o')
    
    type_suffixes = [
        'pansiyon', 'pansiyonu',
        'otel', 'oteli', 'oteller',
        'apart', 'apart-otel', 'apart otel',
        'spa', 'tesisi', 'hotel', 'hotels',
        'motel', 'pension', 'guest house', 'hostel'
    ]
    
    removed_suffix = None
    for suffix in type_suffixes:
        if temp_check_name.endswith(' ' + suffix):
            removed_suffix = suffix
            # Remove from actual clean_name (same number of chars)
            clean_name = clean_name[:-len(' ' + suffix)].strip()
            temp_check_name = temp_check_name[:-len(' ' + suffix)].strip()
            break  # Remove only the first matching suffix
    
    # Build progressive name variants before removing spaces
    raw_tokens_original = re.split(r"\s+", raw_name)
    raw_tokens = re.split(r"\s+", clean_name)
    raw_tokens = [t for t in raw_tokens if t]
    raw_tokens_original = [t for t in raw_tokens_original if t]
    
    # IMPORTANT: lowercase for comparison with type_words
    raw_tokens = [t.lower() for t in raw_tokens]
    
    # Cleanup Turkish characters for type_words comparison
    def clean_turkish(token):
        return token.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ç', 'c').replace('ö', 'o').replace('i̇', 'i')
    
    stopwords = {"special", "class", "boutique", "luxury", "deluxe"}
    type_words = {
        "hotel", "otel", "resort", "spa", "apart", "pansiyon", "motel", 
        "house", "guest", "inn", "lodge",
        # Turkish variants (already cleaned of Turkish chars)
        "oteli", "oteller", "pansiyonu", "resorts", "kabin", "kabins", 
        "vila", "villalar", "konaklama"
    }
    
    # Filter core tokens (check cleaned version)
    core_tokens = [t for t in raw_tokens if t not in stopwords and clean_turkish(t) not in type_words]
    if not core_tokens:
        core_tokens = [t for t in raw_tokens if t not in stopwords]
    
    # Build progressive tokens: balance between filtered (core) and unfiltered (raw) tokens
    # Strategy: Use core_tokens primarily (removes type words), but if core is too small,
    # also try combinations from raw_tokens to catch domain patterns like "alexiaresort"
    progressive_tokens = []
    if core_tokens:
        for i in range(1, len(core_tokens) + 1):
            progressive_tokens.append(core_tokens[:i])
    else:
        # No core tokens? Try raw tokens
        for i in range(1, len(raw_tokens) + 1):
            progressive_tokens.append(raw_tokens[:i])
    
    # If core_tokens filtered too much, also add intermediate raw_token combos
    # This catches cases like: raw=['alexia','resort','spa'] -> core=['alexia']
    # We want to try [alexia,resort] too
    if len(core_tokens) < len(raw_tokens) and len(raw_tokens) > 1:
        for i in range(len(core_tokens) + 1, len(raw_tokens) + 1):
            token_combo = raw_tokens[:i]
            if token_combo not in progressive_tokens:
                progressive_tokens.append(token_combo)
    
    # CRITICAL: If a type suffix was removed (e.g., "OTELI" from "ADMIRAL OTELI"),
    # add a variant with just core_tokens + the removed suffix
    # This ensures "admiralotel" domain gets generated
    if removed_suffix and core_tokens:
        core_with_suffix = core_tokens + [removed_suffix]
        if core_with_suffix not in progressive_tokens:
            progressive_tokens.insert(0, core_with_suffix)  # High priority
    
    # Turkish character cleanup - BEFORE lowercase
    clean_name = clean_name.replace('İ', 'I').replace('Ş', 'S').replace('Ğ', 'G').replace('Ü', 'U').replace('Ç', 'C').replace('Ö', 'O')
    clean_name = clean_name.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ç', 'c').replace('ö', 'o')
    clean_name = clean_name.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
    clean_name = clean_name.replace(' ', '').replace('.', '').replace(',', '').replace('/', '')
    
    # Only try if meaningful length
    if len(clean_name) < 3:
        logging.debug(f"[DISCOVERY] Cleaned name too short: {clean_name}")
    else:
        # Generate MORE domain candidates - try multiple combinations
        domain_variants = []

        # Progressive variants (most relevant first, then expand)
        for token_list in progressive_tokens:
            if not token_list:
                continue
            # Check for type words (with Turkish character cleanup)
            has_type = any(clean_turkish(t) in type_words for t in token_list)
            
            # If no type word, we'll add hotel, try different positions
            if not has_type:
                # Generate variants: [1] hotel-first, [2] hotel-middle, [3] hotel-last
                variants_to_try = [
                    ["hotel"] + token_list,  # HOTEL + PEARL + ISTANBUL
                    token_list + ["hotel"],  # PEARL + ISTANBUL + HOTEL
                ]
                # If 3+ tokens, also try: token[0] + hotel + rest
                if len(token_list) >= 2:
                    variants_to_try.append([token_list[0]] + ["hotel"] + token_list[1:])  # PEARL + HOTEL + ISTANBUL
            else:
                # Already has type, just use as-is
                variants_to_try = [token_list]
            
            # Generate domain variants for each ordering
            for variant_tokens in variants_to_try:
                # Create variants WITHOUT spaces (concat)
                variant = "".join(variant_tokens)
                variant = variant.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ç', 'c').replace('ö', 'o')
                variant = variant.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
                variant = variant.replace('.', '').replace(',', '').replace('/', '')
                if len(variant) >= 3:
                    domain_variants.append(variant)
                
                # Create variants WITH hyphens
                variant_hyphen = "-".join(variant_tokens)
                variant_hyphen = variant_hyphen.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ç', 'c').replace('ö', 'o')
                variant_hyphen = variant_hyphen.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
                variant_hyphen = variant_hyphen.replace('.', '').replace(',', '').replace('/', '')
                if len(variant_hyphen) >= 3 and variant_hyphen not in domain_variants:
                    domain_variants.append(variant_hyphen)

        # Numeric variants: hotel + number, number + hotel
        numeric_tokens = [t for t in raw_tokens_original if t.isdigit()]
        for num in numeric_tokens:
            domain_variants.append(f"hotel{num}")
            domain_variants.append(f"{num}hotel")
        
        # Primary variants (full clean name)
        domain_variants.append(clean_name)

        # De-dup while preserving order
        seen_variants = set()
        domain_variants = [v for v in domain_variants if not (v in seen_variants or seen_variants.add(v))]
        
        import sys
        print(f"[VARIANTS-BEFORE-PRIORITY] {hotel_name}: {domain_variants[:8]}", file=sys.stderr)
        
        # OPTIMIZATION: Prioritize variants by quality/relevance
        # 1. "oteli" (Turkish specific + exact match) - HIGHEST
        # 2. "otel" (Turkish specific) - HIGH
        # 3. Variants WITHOUT "hotel" (more specific domain patterns) - MEDIUM
        # 4. Variants WITH "hotel" (generic) - lower priority
        has_oteli = [v for v in domain_variants if v.endswith('oteli')]
        has_otel_not_oteli = [v for v in domain_variants if v.endswith('otel') and not v.endswith('oteli')]
        no_hotel_keyword = [v for v in domain_variants if 'hotel' not in v and not (v.endswith('otel') or v.endswith('oteli'))]
        has_hotel_keyword = [v for v in domain_variants if 'hotel' in v and not (v.endswith('otel') or v.endswith('oteli'))]
        
        # Sort each group by length (longer = more specific)
        has_oteli.sort(key=len, reverse=True)
        has_otel_not_oteli.sort(key=len, reverse=True)
        no_hotel_keyword.sort(key=len, reverse=True)
        has_hotel_keyword.sort(key=len, reverse=True)
        
        # Combine in priority order
        domain_variants = has_oteli + has_otel_not_oteli + no_hotel_keyword + has_hotel_keyword

        # DEBUG (remove for production): Show first 10 variants
        logging.info(f"[DISCOVERY] Variants for '{hotel_name}': {domain_variants[:10]}")
        import sys
        print(f"[VARIANTS-AFTER-PRIORITY] {hotel_name}: {domain_variants[:8]}", file=sys.stderr)

        # Build URLs from variants with EXPANDED TLD list
        url_variants = []
        tlds = [
            ".com.tr", ".org.tr", ".net.tr", ".biz.tr",
            ".com", ".net", ".org", ".biz", ".info", ".co"
        ]
        
        for variant in domain_variants:
            for tld in tlds:
                url_variants.append(f"http://www.{variant}{tld}")
                url_variants.append(f"http://{variant}{tld}")
        
        # Remove duplicates while preserving order
        seen = set()
        url_variants = [u for u in url_variants if not (u in seen or seen.add(u))]
        
        # ============================================================
        # DNS PRE-CHECK: Filter URLs to only those with valid DNS
        # This is MUCH faster than HTTP HEAD requests (ms vs seconds)
        # ============================================================
        logging.info(f"[DISCOVERY] DNS pre-check for {len(url_variants)} URLs...")
        url_variants = filter_existing_domains(url_variants)
        logging.info(f"[DISCOVERY] {len(url_variants)} URLs passed DNS check")
        
        best_result = None
        best_score = 0
        
        for domain in url_variants:
            try:
                domain_any_checked = True
                resp = requests.head(domain, timeout=2, allow_redirects=False)
                if resp.status_code in (200, 301, 302, 303, 307, 308):
                    # If redirect, check final location
                    if resp.status_code in (301, 302, 303, 307, 308):
                        final_url = resp.headers.get('location', domain)
                    else:
                        final_url = domain
                    
                    # Reject generic or unrelated domains
                    if not _is_relevant_domain(hotel_name, final_url):
                        logging.debug(f"[DISCOVERY] Domain not relevant: {final_url}")
                        continue
                    domain_any_relevant = True

                    # VALIDATION: Check if content is actually a hotel
                    logging.debug(f"[DISCOVERY] Domain check başarılı, content validasyon başlıyor: {final_url}")
                    validation = validate_hotel_content(final_url, hotel_name, city)
                    
                    if validation['is_hotel']:
                        score = calculate_score(hotel_name, final_url, hotel_name)
                        # Boost score if validation succeeded
                        score = min(score + validation['confidence']/2, 100)
                        
                        # Score weighting: exact domain matches get bonus
                        # This ensures "alexiaresort" is preferred over "alexia-hotel" when both valid
                        domain_quality = 0
                        if 'resort' in domain.lower() and 'resort' in hotel_name.lower():
                            domain_quality += 10
                        if 'otel' in domain.lower() and 'otel' in hotel_name.lower().replace('ı', 'i').replace('İ', 'i'):
                            domain_quality += 15  # Strong match for Turkish hotels
                        if any(kw in domain.lower() for kw in ['spa', 'beach', 'villa'] if kw in hotel_name.lower()):
                            domain_quality += 8
                        
                        score = min(score + domain_quality, 100)
                        
                        logging.info(f"[DISCOVERY] BAŞARILI (validated domain): {final_url} (score: {score:.1f})")
                        domain_any_valid = True
                        
                        # Track best result
                        if score > best_score:
                            best_score = score
                            best_result = {'url': final_url, 'score': score, 'source': 'domain_guess'}
                        
                        # Fast return if we found a high-confidence match
                        if score >= 85:
                            logging.info(f"[DISCOVERY] High-confidence match, returning early: {final_url}")
                            return best_result
                    else:
                        logging.debug(f"[DISCOVERY] Domain exists but NOT a hotel: {final_url} (conf: {validation['confidence']:.0f})")
                else:
                    logging.debug(f"[DISCOVERY] Domain {domain} HTTP {resp.status_code}")
            except Exception as e:
                logging.debug(f"[DISCOVERY] Domain {domain} başarısız: {type(e).__name__}")

        if domain_any_checked and not domain_any_valid:
            if domain_any_relevant:
                reason = "domain_not_hotel"
            else:
                reason = "domain_not_relevant"
        
        # If we found a valid domain, return it
        if best_result:
            logging.info(f"[DISCOVERY] Returning best domain guess: {best_result['url']} (score: {best_result['score']:.1f})")
            return best_result
    
    # Strategy 2: DuckDuckGo Search - Progressive queries
    try:
        # Check circuit breaker before DDG search
        if ddg_circuit.state.value == "open":
            logging.warning("[DISCOVERY] DDG circuit breaker is OPEN, skipping search")
            search_queries = []
        else:
            search_queries = _build_progressive_queries(hotel_name, city)
            
        for search_query in search_queries:
            logging.debug(f"[DISCOVERY] Search query: {search_query}")

            # Wait a bit before searching (to avoid rate limits)
            time.sleep(random.uniform(0.5, 1.5))

            html = search_ddg_html(search_query)
            soup = BeautifulSoup(html, 'html.parser')

            # Find all links that look like search results
            candidates = []

            # Try multiple ways to find results
            links = soup.find_all('a', href=True)
            logging.debug(f"[DISCOVERY] DDG toplam link sayısı: {len(links)}")

            for link in links[:50]:  # Check first 50 links
                href = link.get('href', '')
                title = link.get_text(strip=True)[:100]

                # Skip internal DDG links
                if not href or href.startswith('/') or 'duckduckgo' in href:
                    continue

                # Skip non-http links
                if not href.startswith('http'):
                    continue

                logging.debug(f"[DISCOVERY] DDG link: {href[:80]}... (title: {title[:50]})")

                # Clean redirect URLs from DDG
                if 'uddg=' in href or 'r=' in href:
                    try:
                        if 'uddg=' in href:
                            query_params = parse_qs(urlsplit(href).query)
                            if 'uddg' in query_params:
                                href = query_params['uddg'][0]
                        elif 'r=' in href:
                            query_params = parse_qs(urlsplit(href).query)
                            if 'r' in query_params:
                                href = query_params['r'][0]
                        logging.debug(f"[DISCOVERY] DDG decoded: {href[:80]}")
                    except Exception as e:
                        logging.debug(f"[DISCOVERY] Decode hatası: {e}")
                        continue

                # Skip if still not valid
                if not href.startswith('http'):
                    continue

                # Check blacklist
                try:
                    ext = tldextract.extract(href)
                    full_domain = f"{ext.domain}.{ext.suffix}"

                    if ext.domain in BLACKLIST_DOMAINS or full_domain in BLACKLIST_DOMAINS:
                        logging.debug(f"[DISCOVERY] Blacklist'te: {full_domain}")
                        continue
                except:
                    continue

                score = calculate_score(hotel_name, href, title)
                logging.debug(f"[DISCOVERY] Score: {score:.1f} - {href[:60]}")

                # Lower score threshold from 15 to 10 for better match
                if score > 10:
                    candidates.append({'url': href, 'score': score})
                    logging.info(f"[DISCOVERY] Aday bulundu: {href} (score: {score:.1f})")

            if candidates:
                ddg_any_candidates = True
                candidates.sort(key=lambda x: x['score'], reverse=True)

                for candidate in candidates:
                    if not _is_relevant_domain(hotel_name, candidate['url']):
                        continue
                    ddg_any_relevant = True
                    validation = validate_hotel_content(candidate['url'], hotel_name, city)
                    if validation['is_hotel']:
                        final_score = min(candidate['score'] + validation['confidence']/2, 100)
                        logging.info(f"[DISCOVERY] BAŞARILI (DuckDuckGo validated): {candidate['url']} (score: {final_score:.1f})")
                        ddg_any_valid = True
                        return {'url': candidate['url'], 'score': final_score, 'source': 'ddg_search'}

                # None of DDG results were valid hotels
                logging.warning(f"[DISCOVERY] DDG candidates found but none are valid hotels")
            else:
                logging.debug(f"[DISCOVERY] DDG'de aday bulunamadı (score > 10) - query: {search_query}")

    except Exception as e:
        logging.warning(f"[DISCOVERY] DDG arama hatası: {type(e).__name__}: {str(e)[:100]}")

    if reason is None:
        if ddg_any_candidates and not ddg_any_valid:
            reason = "ddg_no_valid" if ddg_any_relevant else "ddg_not_relevant"
        elif not ddg_any_candidates:
            reason = "ddg_no_candidates"
    
    # Strategy 3: Alternative domain patterns (if direct guessing missed)
    try:
        logging.info(f"[DISCOVERY] Alternative domain pattern'leri deneniyor...")
        
        alternative_names = [
            clean_name,
        ]
        
        alternative_tlds = ['.biz', '.info', '.mobi']
        
        for alt_name in alternative_names:
            alt_name = alt_name.strip()
            if len(alt_name) < 2:
                continue
                
            for tld in alternative_tlds:
                domain = f"http://{alt_name}{tld}"
                try:
                    alt_any_checked = True
                    resp = requests.head(domain, timeout=2, allow_redirects=False)
                    if resp.status_code in (200, 301, 302, 307, 308):
                        final_url = resp.headers.get('location', domain) if resp.status_code != 200 else domain
                        
                        # Reject generic or unrelated domains
                        if not _is_relevant_domain(hotel_name, final_url):
                            continue
                        alt_any_relevant = True

                        # VALIDATION: Check if content is actually a hotel
                        validation = validate_hotel_content(final_url, hotel_name, city)
                        
                        if validation['is_hotel']:
                            score = calculate_score(hotel_name, final_url, hotel_name)
                            # Boost score if validation succeeded
                            score = min(score + validation['confidence']/2, 100)
                            logging.info(f"[DISCOVERY] BAŞARILI (validated alternative): {final_url} (score: {score:.1f})")
                            alt_any_valid = True
                            return {'url': final_url, 'score': score, 'source': 'alternative_tld'}
                        else:
                            logging.debug(f"[DISCOVERY] Alternative domain exists but NOT a hotel: {final_url}")
                except:
                    pass
    except:
        pass
    
    if alt_any_checked and not alt_any_valid and reason is None:
        if alt_any_relevant:
            reason = "alternative_not_hotel"
        else:
            reason = "alternative_not_relevant"

    logging.warning(f"[DISCOVERY] BULUNAMADI: {hotel_name}")
    return {"url": None, "reason": reason or "no_match"}
