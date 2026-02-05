#!/usr/bin/env python3
"""
Test permutation logic
"""
import re

def test_permutation(hotel_name):
    print(f"\n{'='*80}")
    print(f"Testing: {hotel_name}")
    print(f"{'='*80}")
    
    raw_name = hotel_name
    type_suffixes = ["HOTEL", "OTEL", "RESORT", "SPA", "APART", "PANSIYON", "MOTEL", "PENSION"]
    clean_name = raw_name.upper()
    for suffix in type_suffixes:
        if clean_name.endswith(' ' + suffix):
            clean_name = clean_name[:-len(' ' + suffix)]
    
    # CRITICAL: Clean special characters BEFORE tokenization
    # Replace & with empty string (removes it), remove other harmful special chars
    clean_name = clean_name.replace('&', '')
    clean_name = re.sub(r'[^a-zA-Z0-9\sşğıüçöŞĞİÜÇÖ-]', '', clean_name)
    
    raw_tokens_original = re.split(r"\s+", raw_name)
    raw_tokens = re.split(r"\s+", clean_name)
    raw_tokens = [t for t in raw_tokens if t]
    raw_tokens = [t.lower() for t in raw_tokens]
    
    print(f"Raw tokens: {raw_tokens}")
    
    stopwords = {"special", "class", "boutique", "luxury", "deluxe"}
    type_words = {"hotel", "otel", "resort", "spa", "apart", "pansiyon", "motel"}
    
    core_tokens = [t for t in raw_tokens if t not in stopwords and t not in type_words]
    print(f"Core tokens (filtered): {core_tokens}")
    
    progressive_tokens = []
    start_len = 2 if len(core_tokens) >= 2 else 1
    for i in range(start_len, len(core_tokens) + 1):
        progressive_tokens.append(core_tokens[:i])
    if raw_tokens:
        progressive_tokens.append(raw_tokens)
    
    print(f"Progressive tokens: {progressive_tokens}")
    
    domain_variants = []
    
    for token_list in progressive_tokens:
        print(f"\n  Processing: {token_list}")
        if not token_list:
            continue
        
        has_type = any(t in type_words for t in token_list)
        print(f"    has_type={has_type}")
        
        orig_token_list = token_list.copy()
        if not has_type:
            token_list = token_list + ["hotel"]
            print(f"    Added hotel: {token_list}")
        
        # Standard variant
        variant = "".join(token_list)
        domain_variants.append(variant)
        print(f"    Standard: {variant}")
        
        # WITH HYPHEN
        variant_hyphen = "-".join(token_list)
        if len(variant_hyphen) >= 3 and variant_hyphen not in domain_variants:
            domain_variants.append(variant_hyphen)
            print(f"    Hyphen: {variant_hyphen}")
        
        # PERMUTATION
        if not has_type and len(token_list) >= 2:  # Only if we added hotel
            core = token_list[:-1]  # All tokens except "hotel"
            print(f"    Core (for permutation): {core}")
            if len(core) >= 2:
                for i in range(len(core)):
                    perm = core[:i+1] + ["hotel"] + core[i+1:]
                    variant_perm = "".join(perm)
                    if variant_perm not in domain_variants:
                        domain_variants.append(variant_perm)
                        print(f"    Permutation {i}: {variant_perm}")
    
    print(f"\n  Final variants ({len(domain_variants)}): {domain_variants}")
    return domain_variants

# Test
test_permutation("PEARL ISTANBUL HOUSE")
test_permutation("ALEXİA RESORT & SPA HOTEL")
test_permutation("ADMİRAL OTELİ")
