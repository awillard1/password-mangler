"""
Hashcat rules generation module.
Supports both built-in rules and ML-learned rules from password leaks.
"""

import logging
import re
from collections import Counter
import mangler_core


def infer_hashcat_rule(base_word, password):
    """
    Infer Hashcat rule that transforms base_word into password.
    
    Args:
        base_word: Original base word (e.g., "password")
        password: Transformed password (e.g., "P@ssw0rd123")
    
    Returns:
        Hashcat rule string or None if transformation is too complex
    
    Examples:
        base_word="password", password="Password123" → "c$1$2$3"
        base_word="admin", password="@dmin2024" → "sa@$2$0$2$4"
    """
    if not base_word or not password:
        return None
    
    rule_parts = []
    base_lower = base_word.lower()
    
    # Find where base word appears in password (may have prefix/suffix)
    pwd_lower = password.lower()
    base_start = pwd_lower.find(base_lower)
    
    if base_start == -1:
        # Base word not found, try with leet speak reversed
        pwd_deleet = pwd_lower
        for leet_char, orig_char in [('@', 'a'), ('3', 'e'), ('0', 'o'), 
                                      ('1', 'i'), ('$', 's'), ('7', 't'), ('4', 'a')]:
            pwd_deleet = pwd_deleet.replace(leet_char, orig_char)
        base_start = pwd_deleet.find(base_lower)
        
        if base_start == -1:
            return None  # Can't find base word
    
    # Step 1: Handle prefix
    if base_start > 0:
        prefix = password[:base_start]
        # Add prepend rules (in reverse order for Hashcat)
        for char in reversed(prefix):
            rule_parts.append(f'^{char}')
    
    # Step 2: Handle case changes
    base_in_pwd = password[base_start:base_start + len(base_word)]
    
    if base_in_pwd[0].isupper() and base_lower[0].islower():
        if base_in_pwd[1:].islower():
            rule_parts.append('c')  # Capitalize first
        elif base_in_pwd.isupper():
            rule_parts.append('u')  # All uppercase
        else:
            rule_parts.append('C')  # First upper, rest lower
    elif base_in_pwd.isupper():
        rule_parts.append('u')
    elif base_in_pwd.islower() and base_word.isupper():
        rule_parts.append('l')
    
    # Step 3: Character substitutions (leet speak)
    for i, (orig_char, pwd_char) in enumerate(zip(base_lower, pwd_lower[base_start:base_start+len(base_lower)])):
        if orig_char != pwd_char:
            # Common leet substitutions
            leet_map = {
                ('a', '@'): 'sa@', ('a', '4'): 'sa4',
                ('e', '3'): 'se3',
                ('i', '1'): 'si1', ('i', '!'): 'si!',
                ('o', '0'): 'so0',
                ('s', '$'): 'ss$', ('s', '5'): 'ss5',
                ('t', '7'): 'st7',
                ('l', '1'): 'sl1',
            }
            
            sub_rule = leet_map.get((orig_char, pwd_char))
            if sub_rule and sub_rule not in rule_parts:
                rule_parts.append(sub_rule)
    
    # Step 4: Handle suffix
    if len(password) > base_start + len(base_word):
        suffix = password[base_start + len(base_word):]
        # Add append rules
        for char in suffix:
            rule_parts.append(f'${char}')
    
    # Combine all parts into single rule
    if rule_parts:
        return ''.join(rule_parts)
    
    return ':'  # Identity rule (no change)


def learn_rules_from_passwords(passwords, dictionary=None, max_rules=5000):
    """
    Learn Hashcat rules from leaked passwords using dictionary matching.
    
    Args:
        passwords: List of leaked passwords
        dictionary: List of common base words (optional, uses built-in if None)
        max_rules: Maximum number of rules to return
    
    Returns:
        List of (rule, frequency) tuples sorted by frequency
    """
    logging.info(f"[Hashcat] Learning rules from {len(passwords)} passwords")
    
    # Use built-in common words if no dictionary provided
    if dictionary is None:
        dictionary = _get_builtin_dictionary()
    
    logging.info(f"[Hashcat] Using dictionary with {len(dictionary)} words")
    
    rule_counter = Counter()
    matched_count = 0
    
    # Process passwords
    for password in passwords:
        if len(password) < 3:
            continue
        
        pwd_lower = password.lower()
        
        # Try to find matching base word
        best_match = None
        best_match_len = 0
        
        for base_word in dictionary:
            if base_word in pwd_lower:
                # Prefer longer matches
                if len(base_word) > best_match_len:
                    best_match = base_word
                    best_match_len = len(base_word)
        
        if best_match:
            # Infer transformation rule
            rule = infer_hashcat_rule(best_match, password)
            if rule and rule != ':':  # Skip identity
                rule_counter[rule] += 1
                matched_count += 1
    
    logging.info(f"[Hashcat] Matched {matched_count}/{len(passwords)} passwords ({matched_count*100/len(passwords):.1f}%)")
    logging.info(f"[Hashcat] Discovered {len(rule_counter)} unique transformation rules")
    
    # Return top rules
    top_rules = rule_counter.most_common(max_rules)
    return top_rules


def _get_builtin_dictionary():
    """
    Return built-in dictionary of common password base words.
    """
    return [
        # Common passwords
        'password', 'admin', 'user', 'root', 'test', 'guest', 'info',
        'welcome', 'master', 'login', 'default', 'letmein', 'passw0rd',
        'administrator', 'support', 'oracle', 'manager', 'supervisor',
        
        # Names
        'john', 'michael', 'david', 'james', 'robert', 'william', 'richard',
        'mary', 'patricia', 'jennifer', 'linda', 'barbara', 'elizabeth',
        'thomas', 'charles', 'daniel', 'matthew', 'anthony', 'mark',
        
        # Common words
        'love', 'monkey', 'dragon', 'master', 'princess', 'sunshine', 'shadow',
        'secret', 'baseball', 'football', 'basketball', 'superman', 'batman',
        'trustno', 'starwars', 'hello', 'freedom', 'whatever', 'qwerty',
        'abc', 'iloveyou', 'computer', 'internet', 'cookie', 'summer',
        
        # Tech terms
        'server', 'database', 'system', 'network', 'access', 'security',
        
        # Short common
        'pass', 'pw', 'pwd', 'temp', 'demo', 'work', 'home', 'mail'
    ]


def generate_hashcat_rules(output_file, ruleset="advanced", learned_rules=None):
    """
    Generate Hashcat-compatible rules file.
    
    Args:
        output_file: Path to output rules file
        ruleset: Rule complexity level ("simple", "advanced", "extreme")
        learned_rules: Optional list of (rule, frequency) from learn_rules_from_passwords()
    """
    logging.info(f"[Hashcat] Generating rules with ruleset: {ruleset}")
    
    rules = set()
    
    # Basic case transformations
    rules.add(":")  # Do nothing (identity)
    rules.add("l")  # Lowercase all
    rules.add("u")  # Uppercase all
    rules.add("c")  # Capitalize
    rules.add("C")  # Lowercase first, uppercase rest
    rules.add("t")  # Toggle case
    rules.add("T0") # Toggle position 0
    rules.add("T1") # Toggle position 1
    rules.add("T2") # Toggle position 2
    
    # Leet speak substitutions
    mappings = {**mangler_core.leet_mappings, **mangler_core.learned_leet}
    
    for char, subs in mappings.items():
        for sub in subs[:4 if ruleset == "advanced" else 2]:  # Limit substitutions
            # Only use single-char substitutions for Hashcat
            if len(sub) == 1:
                rules.add(f"s{char}{sub}")  # Substitute all occurrences
                rules.add(f"s{char.upper()}{sub}")  # Uppercase variant
    
    if ruleset in ["advanced", "extreme"]:
        # Append rules - per-character
        all_appends = mangler_core.common_suffixes[:30] + mangler_core.learned_appends[:20]
        for suffix in all_appends:
            if 1 <= len(suffix) <= 8:
                rule = "".join(f"${c}" for c in suffix)
                rules.add(rule)
                if len(suffix) == 1:
                    rules.add(f"${suffix}${suffix}")  # double common chars

        # Prepend rules - per-character, reversed order
        all_prepends = mangler_core.common_prefixes[:15] + mangler_core.learned_prefixes[:15]
        for prefix in all_prepends:
            if 1 <= len(prefix) <= 6:
                rule = "".join(f"^{c}" for c in reversed(prefix))
                rules.add(rule)
        
        # Delete rules
        rules.add("d")  # Duplicate entire word
        rules.add("f")  # Duplicate entire word reversed
        rules.add("r")  # Reverse
        
        # Character manipulation
        for i in range(5):
            rules.add(f"D{i}")  # Delete at position
            rules.add("[")     # Delete first char
            rules.add("]")     # Delete last char
        
        # Insert rules (common special chars)
        for pos in range(4):
            for char in ["!", "1", "@", "#", "$"]:
                rules.add(f"i{pos}{char}")  # Insert char at position
        
    if ruleset == "extreme":
        # More aggressive combinations
        for i in range(10):
            rules.add(f"${i}")  # Append digits
            rules.add(f"^{i}")  # Prepend digits
        
        # Special character appends
        for char in "!@#$%^&*":
            rules.add(f"${char}")
            rules.add(f"^{char}")
        
        # Position-specific replacements
        for pos in range(3):
            for char in ["1", "3", "4", "5", "7", "0"]:
                rules.add(f"o{pos}{char}")  # Overwrite at position
    
    # Add learned rules if provided
    if learned_rules:
        logging.info(f"[Hashcat] Adding {len(learned_rules)} learned rules from ML analysis")
        for rule, frequency in learned_rules:
            if len(rule) <= 50:  # Sanity check on rule length
                rules.add(rule)
    
    # Write rules to file
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Sort for consistency
            sorted_rules = sorted(rules)
            f.write("\n".join(sorted_rules))
            f.write("\n")  # Trailing newline
        
        logging.info(f"[Hashcat] Generated {len(rules)} rules → {output_file}")
        return len(rules)
        
    except Exception as e:
        logging.error(f"[Hashcat] Failed to write rules: {e}")
        return 0


# Export main functions
__all__ = [
    'generate_hashcat_rules',
    'learn_rules_from_passwords',
    'infer_hashcat_rule',
]
