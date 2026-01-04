"""
Rule Optimization Module

Remove redundant Hashcat rules by testing them on a sample wordlist
and eliminating rules that produce identical results.
"""

import logging
import subprocess
import tempfile
import os
from collections import defaultdict
from typing import List, Set, Tuple

def test_rule_on_words(rule: str, test_words: List[str]) -> Set[str]:
    """
    Test a single Hashcat rule on test words to see what outputs it produces.
    
    Args:
        rule: Hashcat rule string
        test_words: List of words to test the rule on
    
    Returns:
        Set of output passwords the rule produces
    """
    results = set()
    
    # Simple rule engine for common operations (fallback if hashcat not available)
    for word in test_words:
        try:
            output = apply_simple_rule(word, rule)
            if output:
                results.add(output)
        except:
            pass  # Skip rules we can't parse
    
    return results


def apply_simple_rule(word: str, rule: str) -> str:
    """
    Apply a simple Hashcat rule to a word (subset of Hashcat rule syntax).
    
    Supports common rule functions:
    - : (do nothing)
    - l (lowercase all)
    - u (uppercase all)
    - c (capitalize)
    - C (lowercase first, uppercase rest)
    - t (toggle case)
    - r (reverse)
    - d (duplicate)
    - $ (append)
    - ^ (prepend)
    - s (substitute)
    - @ (purge character)
    - z (duplicate first char)
    - Z (duplicate last char)
    """
    result = word
    
    i = 0
    while i < len(rule):
        op = rule[i]
        
        if op == ':':
            # No-op
            pass
        
        elif op == 'l':
            # Lowercase all
            result = result.lower()
        
        elif op == 'u':
            # Uppercase all
            result = result.upper()
        
        elif op == 'c':
            # Capitalize first letter
            if result:
                result = result[0].upper() + result[1:].lower()
        
        elif op == 'C':
            # Lowercase first, uppercase rest
            if result:
                result = result[0].lower() + result[1:].upper()
        
        elif op == 't':
            # Toggle case
            result = result.swapcase()
        
        elif op == 'r':
            # Reverse
            result = result[::-1]
        
        elif op == 'd':
            # Duplicate
            result = result + result
        
        elif op == '$' and i + 1 < len(rule):
            # Append character
            result += rule[i + 1]
            i += 1
        
        elif op == '^' and i + 1 < len(rule):
            # Prepend character
            result = rule[i + 1] + result
            i += 1
        
        elif op == 's' and i + 2 < len(rule):
            # Substitute character
            old_char = rule[i + 1]
            new_char = rule[i + 2]
            result = result.replace(old_char, new_char)
            i += 2
        
        elif op == '@' and i + 1 < len(rule):
            # Purge/remove character
            char_to_remove = rule[i + 1]
            result = result.replace(char_to_remove, '')
            i += 1
        
        elif op == 'z':
            # Duplicate first character
            if result:
                result = result[0] + result
        
        elif op == 'Z':
            # Duplicate last character
            if result:
                result = result + result[-1]
        
        i += 1
    
    return result


def generate_test_wordlist(size: int = 100) -> List[str]:
    """
    Generate a diverse test wordlist for rule optimization.
    
    Args:
        size: Number of test words to generate
    
    Returns:
        List of test words with diverse characteristics
    """
    test_words = [
        # Common base words
        'password', 'admin', 'user', 'test', 'root', 'guest', 'demo',
        'login', 'welcome', 'hello', 'master', 'system', 'super',
        
        # Single letters (for testing multiplications)
        'a', 'b', 'c', 'x', 'y', 'z',
        
        # Short words
        'cat', 'dog', 'sun', 'fun', 'run', 'top', 'hot',
        
        # Medium words
        'apple', 'table', 'chair', 'mouse', 'keyboard',
        
        # Long words
        'corporation', 'administrator', 'technology', 'development',
        
        # Mixed case
        'PassWord', 'AdmiN', 'TeSt', 'RoOt',
        
        # With numbers
        'test123', 'admin456', 'pass789', 'user000',
        
        # With special chars
        'pass!', 'admin@', 'test#', 'user$',
        
        # Common names
        'john', 'mary', 'david', 'sarah', 'michael', 'jennifer',
        
        # Years
        '2020', '2021', '2022', '2023', '2024', '2025',
        
        # Single chars that might be duplicated
        '!', '@', '#', '$', '1', '2', '3'
    ]
    
    return test_words[:size]


def optimize_rules(rules: List[str], test_words: List[str] = None, 
                   verbose: bool = True) -> Tuple[List[str], dict]:
    """
    Optimize Hashcat rules by removing redundant rules.
    
    Args:
        rules: List of Hashcat rule strings
        test_words: Optional list of test words (generated if None)
        verbose: Print progress information
    
    Returns:
        Tuple of (optimized_rules, stats_dict)
    """
    if test_words is None:
        test_words = generate_test_wordlist(100)
    
    if verbose:
        logging.info(f"[RuleOptimizer] Testing {len(rules)} rules on {len(test_words)} words")
    
    # Test each rule and collect outputs
    rule_outputs = {}
    output_to_rules = defaultdict(list)
    
    for i, rule in enumerate(rules):
        if verbose and i % 100 == 0:
            logging.info(f"[RuleOptimizer] Testing rule {i}/{len(rules)}")
        
        try:
            outputs = test_rule_on_words(rule, test_words)
            outputs_tuple = tuple(sorted(outputs))  # Make hashable
            
            rule_outputs[rule] = outputs_tuple
            output_to_rules[outputs_tuple].append(rule)
        except Exception as e:
            logging.debug(f"[RuleOptimizer] Failed to test rule '{rule}': {e}")
            # Keep rules we can't test
            rule_outputs[rule] = (f"UNIQUE_{i}",)
            output_to_rules[(f"UNIQUE_{i}",)].append(rule)
    
    # Find redundant rules
    optimized = []
    redundant_count = 0
    
    for outputs_tuple, rules_with_same_output in output_to_rules.items():
        if len(rules_with_same_output) == 1:
            # Unique rule, keep it
            optimized.append(rules_with_same_output[0])
        else:
            # Multiple rules produce same output, keep shortest/simplest
            redundant_count += len(rules_with_same_output) - 1
            
            # Sort by length, then alphabetically for consistency
            best_rule = sorted(rules_with_same_output, key=lambda r: (len(r), r))[0]
            optimized.append(best_rule)
            
            if verbose:
                logging.debug(f"[RuleOptimizer] Redundant rules (keeping '{best_rule}'):")
                for rule in rules_with_same_output:
                    if rule != best_rule:
                        logging.debug(f"  - {rule}")
    
    stats = {
        'original_count': len(rules),
        'optimized_count': len(optimized),
        'removed_count': len(rules) - len(optimized),
        'redundant_groups': len([r for r in output_to_rules.values() if len(r) > 1]),
        'reduction_percent': round((1 - len(optimized) / len(rules)) * 100, 1) if rules else 0
    }
    
    if verbose:
        logging.info(f"[RuleOptimizer] Optimization complete:")
        logging.info(f"  Original rules: {stats['original_count']}")
        logging.info(f"  Optimized rules: {stats['optimized_count']}")
        logging.info(f"  Removed: {stats['removed_count']} ({stats['reduction_percent']}% reduction)")
        logging.info(f"  Redundant groups: {stats['redundant_groups']}")
    
    return optimized, stats


def optimize_rule_file(input_file: str, output_file: str, 
                       test_wordlist: str = None) -> dict:
    """
    Optimize a Hashcat rule file.
    
    Args:
        input_file: Path to input rule file
        output_file: Path to output optimized rule file
        test_wordlist: Optional path to test wordlist file
    
    Returns:
        Statistics dictionary
    """
    logging.info(f"[RuleOptimizer] Loading rules from {input_file}")
    
    # Load rules
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        rules = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Load test wordlist if provided
    test_words = None
    if test_wordlist:
        logging.info(f"[RuleOptimizer] Loading test wordlist from {test_wordlist}")
        with open(test_wordlist, 'r', encoding='utf-8', errors='ignore') as f:
            test_words = [line.strip() for line in f if line.strip()][:1000]  # Max 1000 words
    
    # Optimize
    optimized_rules, stats = optimize_rules(rules, test_words=test_words, verbose=True)
    
    # Write optimized rules
    logging.info(f"[RuleOptimizer] Writing optimized rules to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Optimized Hashcat Rules\n")
        f.write(f"# Original: {stats['original_count']} rules\n")
        f.write(f"# Optimized: {stats['optimized_count']} rules\n")
        f.write(f"# Removed: {stats['removed_count']} redundant rules ({stats['reduction_percent']}% reduction)\n")
        f.write("#\n")
        
        for rule in optimized_rules:
            f.write(rule + '\n')
    
    logging.info(f"[RuleOptimizer] SUCCESS! Saved {stats['optimized_count']} optimized rules")
    
    return stats


def deduplicate_rules(rules: List[str]) -> List[str]:
    """
    Simple deduplication - remove exact duplicate rules.
    
    Args:
        rules: List of rule strings
    
    Returns:
        Deduplicated list maintaining order
    """
    seen = set()
    deduped = []
    
    for rule in rules:
        if rule not in seen:
            seen.add(rule)
            deduped.append(rule)
    
    return deduped


if __name__ == "__main__":
    # Test the optimizer
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample rules
    test_rules = [
        ':',  # No-op
        'c',  # Capitalize
        'l',  # Lowercase
        'u',  # Uppercase
        '$1$2$3',  # Append 123
        ':$1$2$3',  # No-op then append 123 (redundant with above)
        'c$1$2$3',  # Capitalize and append 123
        'l$!',  # Lowercase and append !
        'u$!',  # Uppercase and append !
        'sa@',  # Substitute a with @
        'se3',  # Substitute e with 3
        'so0',  # Substitute o with 0
    ]
    
    print("Testing rule optimizer...")
    optimized, stats = optimize_rules(test_rules, verbose=True)
    
    print(f"\nOptimized rules ({len(optimized)}):")
    for rule in optimized:
        print(f"  {rule}")
