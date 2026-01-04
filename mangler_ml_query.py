"""
ML Query and Pattern Reuse System

After ML analysis, this module allows querying learned patterns to:
1. Generate password candidates from learned patterns
2. Suggest variations for specific words
3. Export patterns in various formats
4. Merge patterns from multiple sources
5. Validate and manage caches
6. Batch process multiple words
"""

import os
import json
import logging
import time
from typing import List, Dict, Set, Tuple
from collections import Counter


def validate_cache(cache_hash: str = None, cache_file: str = None) -> Dict[str, any]:
    """
    Validate ML cache integrity and structure.
    
    Args:
        cache_hash: Cache hash
        cache_file: Direct path to cache file
    
    Returns:
        Dictionary with validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    try:
        # Load the cache
        if cache_file:
            filepath = cache_file
        elif cache_hash:
            cache_dir = os.path.expanduser("~/.cache/password-mangler")
            filepath = os.path.join(cache_dir, f"ml_patterns_{cache_hash}.json")
        else:
            results['valid'] = False
            results['errors'].append("Must provide cache_hash or cache_file")
            return results
        
        # Check file exists
        if not os.path.exists(filepath):
            results['valid'] = False
            results['errors'].append(f"Cache file not found: {filepath}")
            return results
        
        results['info']['file_path'] = filepath
        results['info']['file_size'] = os.path.getsize(filepath)
        
        # Check JSON structure
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            results['valid'] = False
            results['errors'].append(f"Invalid JSON: {e}")
            return results
        
        # Check required fields
        required_fields = ['appends', 'prepends', 'leet']
        for field in required_fields:
            if field not in data:
                results['valid'] = False
                results['errors'].append(f"Missing required field: {field}")
            else:
                # Check field is a dict
                if not isinstance(data[field], dict):
                    results['valid'] = False
                    results['errors'].append(f"Field '{field}' must be a dictionary")
                else:
                    results['info'][f'{field}_count'] = len(data[field])
        
        # Check optional but expected fields
        if 'source_file' not in data:
            results['warnings'].append("Missing 'source_file' metadata")
        else:
            results['info']['source_file'] = data['source_file']
        
        if 'cache_time' not in data:
            results['warnings'].append("Missing 'cache_time' metadata")
        else:
            results['info']['cache_time'] = data['cache_time']
        
        if 'ml_model' not in data:
            results['warnings'].append("Missing 'ml_model' metadata")
        else:
            results['info']['ml_model'] = data['ml_model']
        
        # Check data integrity
        for field in ['appends', 'prepends', 'leet']:
            if field in data and isinstance(data[field], dict):
                for key, value in data[field].items():
                    if not isinstance(value, (int, float)):
                        results['warnings'].append(f"Non-numeric value in {field}: {key} = {value}")
        
        # Check if empty
        total_patterns = sum(len(data.get(f, {})) for f in ['appends', 'prepends', 'leet'])
        if total_patterns == 0:
            results['warnings'].append("Cache contains no patterns")
        
        results['info']['total_patterns'] = total_patterns
        
    except Exception as e:
        results['valid'] = False
        results['errors'].append(f"Validation error: {e}")
    
    return results


def cleanup_caches(older_than_days: int = None, confirm: bool = True) -> int:
    """
    Clean up old or all ML caches.
    
    Args:
        older_than_days: Remove caches older than N days (None = all)
        confirm: Require user confirmation before deletion
    
    Returns:
        Number of caches removed
    """
    cache_dir = os.path.expanduser("~/.cache/password-mangler")
    
    if not os.path.exists(cache_dir):
        logging.info("No cache directory found")
        return 0
    
    # Find cache files
    cache_files = []
    for filename in os.listdir(cache_dir):
        if filename.startswith('ml_patterns_') and filename.endswith('.json'):
            filepath = os.path.join(cache_dir, filename)
            
            # Check age if specified
            if older_than_days is not None:
                age_days = (time.time() - os.path.getmtime(filepath)) / 86400
                if age_days < older_than_days:
                    continue
            
            cache_files.append(filepath)
    
    if not cache_files:
        logging.info("No caches found matching criteria")
        return 0
    
    # Show what will be deleted
    print(f"\nFound {len(cache_files)} cache(s) to remove:")
    for filepath in cache_files:
        age_days = (time.time() - os.path.getmtime(filepath)) / 86400
        size_kb = os.path.getsize(filepath) / 1024
        print(f"  - {os.path.basename(filepath)} (age: {age_days:.1f} days, size: {size_kb:.1f} KB)")
    
    # Confirm deletion
    if confirm:
        response = input(f"\nDelete {len(cache_files)} cache file(s)? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled")
            return 0
    
    # Delete files
    deleted = 0
    for filepath in cache_files:
        try:
            os.remove(filepath)
            # Also remove report if exists
            report_file = filepath.replace('.json', '_report.txt')
            if os.path.exists(report_file):
                os.remove(report_file)
            deleted += 1
        except Exception as e:
            logging.warning(f"Could not delete {filepath}: {e}")
    
    logging.info(f"Deleted {deleted} cache file(s)")
    return deleted


def batch_query_words(words: List[str], patterns: Dict, 
                     top_n: int = 10, min_confidence: float = 0.01) -> Dict[str, List[Tuple[str, float]]]:
    """
    Query multiple words at once (much faster than individual queries).
    
    Args:
        words: List of base words to query
        patterns: Loaded ML patterns
        top_n: Number of candidates per word
        min_confidence: Minimum confidence threshold
    
    Returns:
        Dictionary mapping word -> list of (password, confidence) tuples
    """
    results = {}
    
    for word in words:
        candidates = generate_from_ml_patterns(word, patterns, top_n, min_confidence)
        results[word] = candidates
    
    return results


def list_cached_ml_patterns(cache_dir: str = None) -> List[Dict]:
    """
    List all cached ML pattern files with metadata.
    
    Args:
        cache_dir: Cache directory (default: ~/.cache/password-mangler/)
    
    Returns:
        List of dicts with cache file info
    """
    if cache_dir is None:
        cache_dir = os.path.expanduser("~/.cache/password-mangler")
    
    if not os.path.exists(cache_dir):
        return []
    
    cached_files = []
    
    for filename in os.listdir(cache_dir):
        if filename.startswith('ml_patterns_') and filename.endswith('.json'):
            filepath = os.path.join(cache_dir, filename)
            
            try:
                # Load metadata
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cache_info = {
                    'cache_file': filepath,
                    'cache_hash': filename.replace('ml_patterns_', '').replace('.json', ''),
                    'source_file': data.get('source_file', 'Unknown'),
                    'cache_time': data.get('cache_time', 'Unknown'),
                    'ml_model': data.get('ml_model', 'counter'),
                    'pattern_counts': {
                        'appends': len(data.get('appends', {})),
                        'prepends': len(data.get('prepends', {})),
                        'leet': len(data.get('leet', {})),
                    }
                }
                
                cached_files.append(cache_info)
            
            except Exception as e:
                logging.warning(f"Could not read cache file {filename}: {e}")
    
    return cached_files


def load_ml_patterns(cache_hash: str = None, cache_file: str = None) -> Dict:
    """
    Load ML patterns from cache by hash or file path.
    
    Args:
        cache_hash: Cache hash (from list_cached_ml_patterns)
        cache_file: Direct path to cache file
    
    Returns:
        Dictionary of learned patterns
    """
    if cache_file:
        filepath = cache_file
    elif cache_hash:
        cache_dir = os.path.expanduser("~/.cache/password-mangler")
        filepath = os.path.join(cache_dir, f"ml_patterns_{cache_hash}.json")
    else:
        raise ValueError("Must provide either cache_hash or cache_file")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cache file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_from_ml_patterns(base_word: str, patterns: Dict, 
                              top_n: int = 20, min_confidence: float = 0.01) -> List[Tuple[str, float]]:
    """
    Generate password candidates for a base word using learned patterns.
    
    Args:
        base_word: Base word to generate variations from
        patterns: Loaded ML patterns dictionary
        top_n: Maximum number of candidates to generate
        min_confidence: Minimum confidence threshold (based on frequency)
    
    Returns:
        List of (password, confidence) tuples sorted by confidence
    """
    candidates = []
    
    appends = patterns.get('appends', {})
    prepends = patterns.get('prepends', {})
    leet = patterns.get('leet', {})
    
    # Calculate total occurrences for confidence
    total_appends = sum(appends.values()) if appends else 1
    total_prepends = sum(prepends.values()) if prepends else 1
    
    # 1. Base word with top appends
    for suffix, count in sorted(appends.items(), key=lambda x: x[1], reverse=True)[:top_n]:
        confidence = count / total_appends
        if confidence >= min_confidence:
            candidates.append((base_word + suffix, confidence))
    
    # 2. Base word with top prepends
    for prefix, count in sorted(prepends.items(), key=lambda x: x[1], reverse=True)[:10]:
        confidence = count / total_prepends
        if confidence >= min_confidence:
            candidates.append((prefix + base_word, confidence))
    
    # 3. Capitalize + appends (very common pattern)
    if base_word and base_word[0].islower():
        cap_word = base_word[0].upper() + base_word[1:]
        for suffix, count in sorted(appends.items(), key=lambda x: x[1], reverse=True)[:10]:
            confidence = (count / total_appends) * 0.8  # Slightly lower confidence
            if confidence >= min_confidence:
                candidates.append((cap_word + suffix, confidence))
    
    # 4. Leet speak variations with appends
    leet_map = {'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '$', 't': '7'}
    for char, replacement in leet_map.items():
        if char in base_word.lower():
            leet_word = base_word.replace(char, replacement)
            # Just the leet word
            candidates.append((leet_word, 0.5))
            # Leet word with top appends
            for suffix, count in sorted(appends.items(), key=lambda x: x[1], reverse=True)[:5]:
                confidence = (count / total_appends) * 0.4
                if confidence >= min_confidence:
                    candidates.append((leet_word + suffix, confidence))
    
    # Remove duplicates and sort by confidence
    unique_candidates = {}
    for pwd, conf in candidates:
        if pwd not in unique_candidates or conf > unique_candidates[pwd]:
            unique_candidates[pwd] = conf
    
    sorted_candidates = sorted(unique_candidates.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_candidates[:top_n]


def suggest_patterns_for_word(word: str, patterns: Dict) -> Dict[str, List]:
    """
    Suggest applicable patterns for a specific word.
    
    Args:
        word: Word to analyze
        patterns: Loaded ML patterns
    
    Returns:
        Dictionary of suggested transformations
    """
    suggestions = {
        'top_appends': [],
        'top_prepends': [],
        'leet_variations': [],
        'case_variations': [],
    }
    
    appends = patterns.get('appends', {})
    prepends = patterns.get('prepends', {})
    
    # Top 10 appends
    suggestions['top_appends'] = [
        (suffix, count) for suffix, count in 
        sorted(appends.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    # Top 5 prepends
    suggestions['top_prepends'] = [
        (prefix, count) for prefix, count in 
        sorted(prepends.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Applicable leet variations
    leet_map = {'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '$', 't': '7'}
    for char, replacement in leet_map.items():
        if char in word.lower():
            leet_word = word.replace(char, replacement)
            suggestions['leet_variations'].append(leet_word)
    
    # Case variations
    if word:
        suggestions['case_variations'] = [
            word.capitalize(),
            word.upper(),
            word.lower(),
        ]
    
    return suggestions


def merge_ml_patterns(pattern_list: List[Dict]) -> Dict:
    """
    Merge multiple ML pattern dictionaries into one.
    Useful for combining patterns from different leak files.
    
    Args:
        pattern_list: List of pattern dictionaries to merge
    
    Returns:
        Merged pattern dictionary
    """
    merged = {
        'appends': Counter(),
        'prepends': Counter(),
        'leet': Counter(),
        'ml_model': 'merged',
        'source_file': 'Multiple sources',
    }
    
    for patterns in pattern_list:
        # Merge appends
        for key, value in patterns.get('appends', {}).items():
            merged['appends'][key] += value
        
        # Merge prepends
        for key, value in patterns.get('prepends', {}).items():
            merged['prepends'][key] += value
        
        # Merge leet
        for key, value in patterns.get('leet', {}).items():
            merged['leet'][key] += value
    
    # Convert Counter back to dict
    merged['appends'] = dict(merged['appends'])
    merged['prepends'] = dict(merged['prepends'])
    merged['leet'] = dict(merged['leet'])
    
    return merged


def export_patterns_to_hashcat_rules(patterns: Dict, output_file: str, 
                                     max_rules: int = 100) -> int:
    """
    Export learned patterns as Hashcat rules.
    
    Args:
        patterns: Loaded ML patterns
        output_file: Output file for Hashcat rules
        max_rules: Maximum number of rules to generate
    
    Returns:
        Number of rules written
    """
    rules = set()
    
    appends = patterns.get('appends', {})
    prepends = patterns.get('prepends', {})
    
    # Base rules
    rules.add(':')  # Identity
    rules.add('c')  # Capitalize
    rules.add('u')  # Uppercase
    rules.add('l')  # Lowercase
    
    # Append rules (sorted by frequency)
    for suffix, count in sorted(appends.items(), key=lambda x: x[1], reverse=True)[:50]:
        rule = ''.join(f'${c}' for c in suffix)
        rules.add(rule)
        
        # Capitalize + append (common combo)
        rules.add('c' + rule)
    
    # Prepend rules
    for prefix, count in sorted(prepends.items(), key=lambda x: x[1], reverse=True)[:20]:
        rule = ''.join(f'^{c}' for c in reversed(prefix))
        rules.add(rule)
    
    # Leet speak rules
    leet_map = {'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '$', 't': '7'}
    for char, replacement in leet_map.items():
        rules.add(f's{char}{replacement}')
        
        # Leet + append combos
        for suffix, count in sorted(appends.items(), key=lambda x: x[1], reverse=True)[:10]:
            append_rule = ''.join(f'${c}' for c in suffix)
            rules.add(f's{char}{replacement}{append_rule}')
    
    # Write to file
    rules_list = sorted(list(rules))[:max_rules]
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for rule in rules_list:
                f.write(rule + '\n')
        
        logging.info(f"[ML Query] Exported {len(rules_list)} rules to {output_file}")
        return len(rules_list)
    
    except Exception as e:
        logging.error(f"[ML Query] Failed to export rules: {e}")
        return 0


def generate_wordlist_from_ml(base_words: List[str], patterns: Dict,
                              output_file: str, top_variations: int = 10) -> int:
    """
    Generate complete wordlist from base words and ML patterns.
    
    Args:
        base_words: List of base words
        patterns: Loaded ML patterns
        output_file: Output wordlist file
        top_variations: Number of variations per word
    
    Returns:
        Total passwords generated
    """
    try:
        total = 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for base_word in base_words:
                # Generate variations
                variations = generate_from_ml_patterns(
                    base_word, patterns, 
                    top_n=top_variations,
                    min_confidence=0.01
                )
                
                # Write to file
                for password, confidence in variations:
                    f.write(password + '\n')
                    total += 1
        
        logging.info(f"[ML Query] Generated {total} passwords from {len(base_words)} base words")
        return total
    
    except Exception as e:
        logging.error(f"[ML Query] Failed to generate wordlist: {e}")
        return 0


def query_ml_interactive(cache_hash: str = None):
    """
    Interactive ML query mode - ask for word suggestions.
    
    Args:
        cache_hash: Optional cache hash to use (or list and choose)
    """
    # List available caches
    caches = list_cached_ml_patterns()
    
    if not caches:
        print("No ML pattern caches found. Run analysis on leak files first.")
        return
    
    print("\n" + "="*70)
    print("ML PATTERN QUERY - INTERACTIVE MODE")
    print("="*70 + "\n")
    
    # Select cache if not provided
    if not cache_hash:
        print("Available ML Pattern Caches:\n")
        for i, cache in enumerate(caches, 1):
            print(f"{i}. {cache['source_file']}")
            print(f"   Cache time: {cache['cache_time']}")
            print(f"   Patterns: {cache['pattern_counts']['appends']} appends, "
                  f"{cache['pattern_counts']['prepends']} prepends, "
                  f"{cache['pattern_counts']['leet']} leet")
            print()
        
        try:
            choice = int(input("Select cache (1-{}): ".format(len(caches))))
            if 1 <= choice <= len(caches):
                cache_hash = caches[choice - 1]['cache_hash']
            else:
                print("Invalid choice")
                return
        except (ValueError, KeyboardInterrupt):
            return
    
    # Load patterns
    try:
        patterns = load_ml_patterns(cache_hash=cache_hash)
        print(f"\nLoaded patterns from: {patterns.get('source_file', 'Unknown')}\n")
    except Exception as e:
        print(f"Error loading patterns: {e}")
        return
    
    # Interactive query loop
    print("Enter base words to get password suggestions (or 'quit' to exit):\n")
    
    while True:
        try:
            word = input("Word: ").strip()
            
            if not word or word.lower() == 'quit':
                break
            
            # Generate candidates
            candidates = generate_from_ml_patterns(word, patterns, top_n=20)
            
            print(f"\nTop password candidates for '{word}':")
            print("-" * 50)
            
            for i, (password, confidence) in enumerate(candidates, 1):
                print(f"  {i:2d}. {password:25s} (confidence: {confidence:.3f})")
            
            print()
        
        except KeyboardInterrupt:
            break
    
    print("\nExiting interactive mode.")


# Export main functions
__all__ = [
    'list_cached_ml_patterns',
    'load_ml_patterns',
    'generate_from_ml_patterns',
    'suggest_patterns_for_word',
    'merge_ml_patterns',
    'export_patterns_to_hashcat_rules',
    'generate_wordlist_from_ml',
    'query_ml_interactive',
    'validate_cache',
    'cleanup_caches',
    'batch_query_words',
]
