"""
Hashcat rules generation module.
"""

import logging
import mangler_core

def generate_hashcat_rules(output_file, ruleset="advanced"):
    """
    Generate Hashcat-compatible rules file.
    
    Args:
        output_file: Path to output rules file
        ruleset: Rule complexity level ("simple", "advanced", "extreme")
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
        # Append rules
        all_appends = (
            mangler_core.common_suffixes[:30] +
            mangler_core.learned_appends[:20]
        )
        
        for suffix in all_appends:
            # Limit to reasonable lengths for Hashcat
            if len(suffix) <= 8 and suffix.strip():
                rules.add(f"${suffix}")  # Append
                
                # Character duplication
                if len(suffix) == 1:
                    rules.add(f"${suffix}${suffix}")  # Double append
        
        # Prepend rules
        all_prepends = (
            mangler_core.common_prefixes[:15] +
            mangler_core.learned_prefixes[:15]
        )
        
        for prefix in all_prepends:
            if len(prefix) <= 6 and prefix.strip():
                rules.add(f"^{prefix[::-1]}")  # Prepend (reversed for Hashcat)
        
        # Duplication rules
        rules.add("d")  # Duplicate entire word
        rules.add("f")  # Duplicate entire word reversed
        rules.add("r")  # Reverse
        
        # Character manipulation
        for i in range(5):
            rules.add(f"D{i}")  # Delete at position
            rules.add(f"[")     # Delete first char
            rules.add(f"]")     # Delete last char
        
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
]
