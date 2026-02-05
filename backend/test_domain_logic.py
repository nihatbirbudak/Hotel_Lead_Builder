#!/usr/bin/env python3
"""
Direct test of domain generation function
"""
import re
import sys
sys.path.insert(0, 'app')

hotel_name = "PEARL ISTANBUL HOUSE"
raw_name = hotel_name

# Cleanup like in the function
type_suffixes = ["HOTEL", "OTEL", "RESORT", "SPA", "APART", "PANSIYON", "MOTEL", "PENSION"]
clean_name = raw_name.upper()
for suffix in type_suffixes:
    if clean_name.endswith(' ' + suffix):
        clean_name = clean_name[:-len(' ' + suffix)]

print(f"Step 1 - After removing suffix: {clean_name}")

# Build tokens
raw_tokens_original = re.split(r"\s+", raw_name)
raw_tokens = re.split(r"\s+", clean_name)
raw_tokens = [t for t in raw_tokens if t]
raw_tokens_original = [t for t in raw_tokens_original if t]

print(f"Step 2 - Tokens: {raw_tokens}")

stopwords = {"special", "class", "boutique", "luxury", "deluxe"}
type_words = {"hotel", "otel", "resort", "spa", "apart", "pansiyon", "motel"}

core_tokens = [t.lower() for t in raw_tokens if t.lower() not in stopwords and t.lower() not in type_words]
print(f"Step 3 - Core tokens: {core_tokens}")

progressive_tokens = []
start_len = 2 if len(core_tokens) >= 2 else 1
for i in range(start_len, len(core_tokens) + 1):
    progressive_tokens.append(core_tokens[:i])
if raw_tokens:
    progressive_tokens.append([t.lower() for t in raw_tokens])

print(f"Step 4 - Progressive tokens: {progressive_tokens}")

domain_variants = []
for token_list in progressive_tokens:
    if not token_list:
        continue
    has_type = any(t in type_words for t in token_list)
    print(f"  Token list {token_list}: has_type={has_type}")
    if not has_type:
        token_list = token_list + ["hotel"]
        print(f"    After adding 'hotel': {token_list}")
    
    # Concatenated
    variant = "".join(token_list)
    variant = variant.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ç', 'c').replace('ö', 'o')
    if len(variant) >= 3:
        domain_variants.append(variant)
        print(f"    Generated: {variant}")

print(f"\nFinal domain variants: {domain_variants}")
