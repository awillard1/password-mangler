#!/usr/bin/env python3
"""
ML Pattern Query Tool

Standalone utility for querying and reusing learned ML patterns from password-mangler.
This tool works with cached ML patterns generated during password-mangler analysis.

Usage Examples:
    # List available ML caches
    python3 ml_query.py --list
    
    # Interactive query mode
    python3 ml_query.py --interactive
    
    # Query for specific word
    python3 ml_query.py --word "password" --cache <hash>
    
    # Generate wordlist from ML patterns
    python3 ml_query.py --generate base_words.txt -o output.txt --cache <hash>
    
    # Export as Hashcat rules
    python3 ml_query.py --export-rules output.rule --cache <hash>
    
    # Merge multiple ML caches
    python3 ml_query.py --merge cache1,cache2,cache3 -o merged_patterns.json
"""

import os
import sys
import argparse
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mangler_ml_query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def print_banner():
    """Print tool banner."""
    print("\n" + "="*70)
    print("ML PATTERN QUERY TOOL - Password Mangler")
    print("Query and reuse learned patterns from leak file analysis")
    print("="*70 + "\n")


def list_caches():
    """List all available ML caches."""
    caches = mangler_ml_query.list_cached_ml_patterns()
    
    if not caches:
        print("No ML pattern caches found.")
        print("\nTo create ML caches, run password-mangler with leak files:")
        print("  python3 mangler.py -i words.txt -o output.txt --leak leaks.txt")
        return
    
    print(f"Found {len(caches)} cached ML pattern(s):\n")
    
    for i, cache in enumerate(caches, 1):
        print(f"{i}. Cache Hash: {cache['cache_hash']}")
        print(f"   Source: {cache['source_file']}")
        print(f"   Cached: {cache['cache_time']}")
        print(f"   Model: {cache['ml_model']}")
        print(f"   Patterns: {cache['pattern_counts']['appends']} appends, "
              f"{cache['pattern_counts']['prepends']} prepends, "
              f"{cache['pattern_counts']['leet']} leet substitutions")
        print()


def query_word(word: str, cache_hash: str, top_n: int = 20):
    """Query ML patterns for a specific word."""
    try:
        patterns = mangler_ml_query.load_ml_patterns(cache_hash=cache_hash)
        
        print(f"Loaded patterns from: {patterns.get('source_file', 'Unknown')}\n")
        
        candidates = mangler_ml_query.generate_from_ml_patterns(
            word, patterns, top_n=top_n
        )
        
        print(f"Top {len(candidates)} password candidates for '{word}':")
        print("-" * 60)
        
        for i, (password, confidence) in enumerate(candidates, 1):
            print(f"  {i:2d}. {password:30s} (confidence: {confidence:.3f})")
        
        print()
        
    except Exception as e:
        logging.error(f"Query failed: {e}")
        sys.exit(1)


def generate_wordlist(input_file: str, output_file: str, cache_hash: str, 
                     top_variations: int = 10):
    """Generate wordlist from base words using ML patterns."""
    try:
        # Load base words
        logging.info(f"Loading base words from {input_file}")
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            base_words = [line.strip() for line in f if line.strip()]
        
        logging.info(f"Loaded {len(base_words)} base words")
        
        # Load ML patterns
        patterns = mangler_ml_query.load_ml_patterns(cache_hash=cache_hash)
        logging.info(f"Loaded patterns from: {patterns.get('source_file', 'Unknown')}")
        
        # Generate wordlist
        count = mangler_ml_query.generate_wordlist_from_ml(
            base_words, patterns, output_file, top_variations=top_variations
        )
        
        if count > 0:
            logging.info(f"SUCCESS! Generated {count:,} passwords to {output_file}")
            logging.info(f"Average {count / len(base_words):.1f} variations per base word")
        else:
            logging.error("Generation failed")
            sys.exit(1)
        
    except Exception as e:
        logging.error(f"Generation failed: {e}")
        sys.exit(1)


def export_rules(output_file: str, cache_hash: str, max_rules: int = 100):
    """Export ML patterns as Hashcat rules."""
    try:
        patterns = mangler_ml_query.load_ml_patterns(cache_hash=cache_hash)
        logging.info(f"Loaded patterns from: {patterns.get('source_file', 'Unknown')}")
        
        count = mangler_ml_query.export_patterns_to_hashcat_rules(
            patterns, output_file, max_rules=max_rules
        )
        
        if count > 0:
            logging.info(f"SUCCESS! Exported {count} Hashcat rules to {output_file}")
        else:
            logging.error("Export failed")
            sys.exit(1)
        
    except Exception as e:
        logging.error(f"Export failed: {e}")
        sys.exit(1)


def merge_caches(cache_hashes: list, output_file: str):
    """Merge multiple ML caches into one."""
    try:
        logging.info(f"Merging {len(cache_hashes)} caches...")
        
        pattern_list = []
        for cache_hash in cache_hashes:
            patterns = mangler_ml_query.load_ml_patterns(cache_hash=cache_hash.strip())
            pattern_list.append(patterns)
            logging.info(f"  Loaded: {patterns.get('source_file', 'Unknown')}")
        
        merged = mangler_ml_query.merge_ml_patterns(pattern_list)
        
        # Save merged patterns
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, indent=2)
        
        logging.info(f"SUCCESS! Merged patterns saved to {output_file}")
        logging.info(f"  Total appends: {len(merged['appends'])}")
        logging.info(f"  Total prepends: {len(merged['prepends'])}")
        logging.info(f"  Total leet: {len(merged['leet'])}")
        
    except Exception as e:
        logging.error(f"Merge failed: {e}")
        sys.exit(1)


def show_pattern_summary(cache_hash: str):
    """Show detailed summary of patterns in a cache."""
    try:
        patterns = mangler_ml_query.load_ml_patterns(cache_hash=cache_hash)
        
        print(f"Pattern Summary for: {patterns.get('source_file', 'Unknown')}")
        print("="*70 + "\n")
        
        print(f"ML Model: {patterns.get('ml_model', 'N/A')}")
        print(f"Cache Time: {patterns.get('cache_time', 'N/A')}\n")
        
        # Appends
        appends = patterns.get('appends', {})
        if appends:
            print(f"TOP 20 APPEND PATTERNS ({len(appends)} total)")
            print("-"*70)
            sorted_appends = sorted(appends.items(), key=lambda x: x[1], reverse=True)[:20]
            for pattern, count in sorted_appends:
                print(f"  '{pattern:15s}' - {count:,} occurrences")
            print()
        
        # Prepends
        prepends = patterns.get('prepends', {})
        if prepends:
            print(f"TOP 10 PREPEND PATTERNS ({len(prepends)} total)")
            print("-"*70)
            sorted_prepends = sorted(prepends.items(), key=lambda x: x[1], reverse=True)[:10]
            for pattern, count in sorted_prepends:
                print(f"  '{pattern:15s}' - {count:,} occurrences")
            print()
        
        # Leet
        leet = patterns.get('leet', {})
        if leet:
            print(f"LEET SPEAK SUBSTITUTIONS ({len(leet)} total)")
            print("-"*70)
            sorted_leet = sorted(leet.items(), key=lambda x: x[1], reverse=True)
            for substitution, count in sorted_leet:
                print(f"  {substitution:20s} - {count:,} occurrences")
            print()
        
    except Exception as e:
        logging.error(f"Failed to load patterns: {e}")
        sys.exit(1)


def validate(cache_hash: str):
    """Validate cache integrity."""
    try:
        print_banner()
        print(f"Validating cache: {cache_hash}\n")
        
        results = mangler_ml_query.validate_cache(cache_hash=cache_hash)
        
        # Show results
        if results['valid']:
            print("✓ Cache is VALID\n")
        else:
            print("✗ Cache is INVALID\n")
        
        # Show info
        if results['info']:
            print("Cache Information:")
            print("-" * 50)
            for key, value in results['info'].items():
                print(f"  {key}: {value}")
            print()
        
        # Show errors
        if results['errors']:
            print("Errors:")
            print("-" * 50)
            for error in results['errors']:
                print(f"  ✗ {error}")
            print()
        
        # Show warnings
        if results['warnings']:
            print("Warnings:")
            print("-" * 50)
            for warning in results['warnings']:
                print(f"  ⚠ {warning}")
            print()
        
        return results['valid']
    
    except Exception as e:
        logging.error(f"Validation failed: {e}")
        return False


def cleanup(older_than: int = None, force: bool = False):
    """Clean up old caches."""
    try:
        print_banner()
        
        if older_than:
            print(f"Cleaning caches older than {older_than} days...\n")
        else:
            print("Cleaning ALL caches...\n")
        
        count = mangler_ml_query.cleanup_caches(
            older_than_days=older_than,
            confirm=not force
        )
        
        if count > 0:
            logging.info(f"Cleaned up {count} cache(s)")
        
    except Exception as e:
        logging.error(f"Cleanup failed: {e}")
        sys.exit(1)


def batch_query(input_file: str, output_file: str, cache_hash: str, 
               top_n: int = 10, min_conf: float = 0.01):
    """Batch query multiple words."""
    try:
        # Load words
        logging.info(f"Loading words from {input_file}")
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            words = [line.strip() for line in f if line.strip()]
        
        logging.info(f"Loaded {len(words)} words")
        
        # Load patterns
        patterns = mangler_ml_query.load_ml_patterns(cache_hash=cache_hash)
        logging.info(f"Loaded patterns from: {patterns.get('source_file', 'Unknown')}")
        
        # Batch query
        logging.info(f"Querying patterns...")
        results = mangler_ml_query.batch_query_words(
            words, patterns, top_n=top_n, min_confidence=min_conf
        )
        
        # Write results
        with open(output_file, 'w', encoding='utf-8') as f:
            for word, candidates in results.items():
                f.write(f"# {word}\n")
                for pwd, conf in candidates:
                    f.write(f"{pwd}\t{conf:.3f}\n")
                f.write("\n")
        
        total_candidates = sum(len(c) for c in results.values())
        logging.info(f"SUCCESS! Generated {total_candidates} candidates for {len(words)} words")
        logging.info(f"Results written to: {output_file}")
        
    except Exception as e:
        logging.error(f"Batch query failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ML Pattern Query Tool - Query and reuse learned patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available caches
  %(prog)s --list
  
  # Interactive mode
  %(prog)s --interactive
  
  # Query specific word
  %(prog)s --word "password" --cache abc123def
  
  # Generate wordlist from ML patterns
  %(prog)s --generate base_words.txt -o output.txt --cache abc123def
  
  # Export as Hashcat rules
  %(prog)s --export-rules custom.rule --cache abc123def --max-rules 200
  
  # Show pattern summary
  %(prog)s --summary --cache abc123def
  
  # Merge multiple caches
  %(prog)s --merge abc123,def456,ghi789 -o merged.json
        """
    )
    
    parser.add_argument("--list", action="store_true",
                       help="List all available ML pattern caches")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive query mode")
    parser.add_argument("--word", "-w", metavar="WORD",
                       help="Query patterns for specific word")
    parser.add_argument("--generate", "-g", metavar="INPUT",
                       help="Generate wordlist from base words using ML patterns")
    parser.add_argument("--export-rules", "-r", metavar="OUTPUT",
                       help="Export ML patterns as Hashcat rules")
    parser.add_argument("--merge", "-m", metavar="HASHES",
                       help="Merge multiple caches (comma-separated hashes)")
    parser.add_argument("--summary", "-s", action="store_true",
                       help="Show detailed pattern summary")
    parser.add_argument("--cache", "-c", metavar="HASH",
                       help="ML cache hash to use")
    parser.add_argument("--output", "-o", metavar="FILE",
                       help="Output file")
    parser.add_argument("--top-n", type=int, default=20,
                       help="Number of candidates to show (default: 20)")
    parser.add_argument("--max-rules", type=int, default=100,
                       help="Maximum rules to export (default: 100)")
    parser.add_argument("--variations", type=int, default=10,
                       help="Variations per word in generation (default: 10)")
    
    args = parser.parse_args()
    
    # Show banner for interactive modes
    if args.interactive or args.list or args.summary:
        print_banner()
    
    # List caches
    if args.list:
        list_caches()
        return
    
    # Interactive mode
    if args.interactive:
        mangler_ml_query.query_ml_interactive(cache_hash=args.cache)
        return
    
    # Query specific word
    if args.word:
        if not args.cache:
            logging.error("Must specify --cache for word queries")
            logging.info("Use --list to see available caches")
            sys.exit(1)
        
        query_word(args.word, args.cache, args.top_n)
        return
    
    # Generate wordlist
    if args.generate:
        if not args.cache:
            logging.error("Must specify --cache for generation")
            logging.info("Use --list to see available caches")
            sys.exit(1)
        
        if not args.output:
            logging.error("Must specify --output for generation")
            sys.exit(1)
        
        generate_wordlist(args.generate, args.output, args.cache, args.variations)
        return
    
    # Export rules
    if args.export_rules:
        if not args.cache:
            logging.error("Must specify --cache for rule export")
            logging.info("Use --list to see available caches")
            sys.exit(1)
        
        export_rules(args.export_rules, args.cache, args.max_rules)
        return
    
    # Merge caches
    if args.merge:
        if not args.output:
            logging.error("Must specify --output for merge")
            sys.exit(1)
        
        cache_hashes = args.merge.split(',')
        merge_caches(cache_hashes, args.output)
        return
    
    # Show summary
    if args.summary:
        if not args.cache:
            logging.error("Must specify --cache for summary")
            logging.info("Use --list to see available caches")
            sys.exit(1)
        
        print_banner()
        show_pattern_summary(args.cache)
        return
    
    # No action specified
    parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
