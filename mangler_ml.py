"""
Machine Learning based rule induction for password mangling.
Optimized for efficiency with streaming and sampling.
Supports chunked processing for large files and optional caching.

ML Model Options:
- 'counter': Simple frequency counting (fastest, default)
- 'markov': Lightweight Markov Chain for pattern generation
- 'clustering': MiniBatchKMeans clustering (slow, minimal benefit)
"""

import logging
from collections import Counter, defaultdict
import re
import os
import json
import hashlib
import random

# Optional ML dependencies
try:
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.cluster import MiniBatchKMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("sklearn not available. ML clustering disabled. Install with: pip install scikit-learn")

import mangler_core


# ===========================
# MARKOV CHAIN MODEL
# ===========================

class PasswordMarkovChain:
    """
    Lightweight Markov Chain for learning password patterns.
    Much faster than clustering with similar or better results.
    """
    
    def __init__(self, order=2):
        """
        Args:
            order: Length of context to consider (2 = bigram)
        """
        self.order = order
        self.transitions = defaultdict(lambda: defaultdict(int))
        self.total_transitions = defaultdict(int)
    
    def train(self, passwords):
        """Train on password list."""
        for pwd in passwords:
            # Add start/end markers
            augmented = '^' * self.order + pwd + '$'
            
            for i in range(len(augmented) - self.order):
                context = augmented[i:i+self.order]
                next_char = augmented[i+self.order]
                self.transitions[context][next_char] += 1
                self.total_transitions[context] += 1
        
        logging.info(f"[Markov] Trained on {len(passwords)} passwords, "
                    f"learned {len(self.transitions)} contexts")
    
    def generate_suffix(self, base_word, max_len=6):
        """
        Generate a likely suffix for the given base word.
        
        Args:
            base_word: Word to generate suffix for
            max_len: Maximum suffix length
        
        Returns:
            Generated suffix string
        """
        if len(base_word) < self.order:
            return ""
        
        context = base_word[-self.order:].lower()
        suffix = []
        
        for _ in range(max_len):
            if context not in self.transitions:
                break
            
            chars = self.transitions[context]
            total = self.total_transitions[context]
            
            # Weighted random selection
            r = random.randint(0, total - 1)
            cumsum = 0
            
            for char, count in chars.items():
                cumsum += count
                if cumsum > r:
                    if char == '$':  # End marker
                        break
                    suffix.append(char)
                    context = context[1:] + char
                    break
        
        return ''.join(suffix)
    
    def generate_variations(self, base_word, num_variations=20):
        """Generate multiple suffix variations."""
        variations = set()
        attempts = 0
        max_attempts = num_variations * 3
        
        while len(variations) < num_variations and attempts < max_attempts:
            suffix = self.generate_suffix(base_word)
            if suffix and len(suffix) > 0:
                variations.add(suffix)
            attempts += 1
        
        return list(variations)

# ===========================
# ML-BASED RULE INDUCTION
# ===========================

def _get_cache_path(leak_source):
    """Generate cache file path based on leak source hash."""
    cache_dir = os.path.expanduser("~/.cache/password-mangler")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create hash from leak source path and modification time
    if os.path.isfile(leak_source):
        mtime = os.path.getmtime(leak_source)
        cache_key = f"{leak_source}_{mtime}"
    else:
        # For directories, hash all file names and mtimes
        file_info = []
        for fname in sorted(os.listdir(leak_source)):
            fpath = os.path.join(leak_source, fname)
            if os.path.isfile(fpath):
                file_info.append(f"{fname}_{os.path.getmtime(fpath)}")
        cache_key = f"{leak_source}_{'_'.join(file_info)}"
    
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    return os.path.join(cache_dir, f"ml_patterns_{cache_hash}.json")


def _load_cached_patterns(cache_path):
    """Load patterns from cache if available."""
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.info(f"[ML] Loaded cached patterns from {cache_path}")
            return data
    except Exception as e:
        logging.warning(f"[ML] Failed to load cache: {e}")
        return None


def _save_cached_patterns(cache_path, patterns):
    """Save patterns to cache."""
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2)
            logging.info(f"[ML] Saved patterns to cache: {cache_path}")
        
        # Also write human-readable report
        report_path = cache_path.replace('.json', '_report.txt')
        _write_ml_patterns_report(report_path, patterns)
        
    except Exception as e:
        logging.warning(f"[ML] Failed to save cache: {e}")


def _write_ml_patterns_report(report_path, patterns):
    """Write human-readable ML patterns report."""
    try:
        from datetime import datetime
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("ML PATTERN LEARNING REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if 'source_file' in patterns:
                f.write(f"Source: {patterns['source_file']}\n")
            f.write(f"Analysis Method: {patterns.get('ml_model', 'counter')}\n\n")
            
            # Learned patterns summary
            f.write("LEARNED PATTERNS SUMMARY\n")
            f.write("-"*70 + "\n")
            
            appends = patterns.get('appends', {})
            prepends = patterns.get('prepends', {})
            leet = patterns.get('leet', {})
            
            f.write(f"  Append patterns:  {len(appends)}\n")
            f.write(f"  Prepend patterns: {len(prepends)}\n")
            f.write(f"  Leet substitutions: {len(leet)}\n\n")
            
            # Top appends
            if appends:
                f.write("TOP 20 APPEND PATTERNS (most common)\n")
                f.write("-"*70 + "\n")
                sorted_appends = sorted(appends.items(), key=lambda x: x[1], reverse=True)[:20]
                for pattern, count in sorted_appends:
                    f.write(f"  '{pattern:15s}' - {count:,} occurrences\n")
                f.write("\n")
            
            # Top prepends
            if prepends:
                f.write("TOP 10 PREPEND PATTERNS (most common)\n")
                f.write("-"*70 + "\n")
                sorted_prepends = sorted(prepends.items(), key=lambda x: x[1], reverse=True)[:10]
                for pattern, count in sorted_prepends:
                    f.write(f"  '{pattern:15s}' - {count:,} occurrences\n")
                f.write("\n")
            
            # Leet substitutions
            if leet:
                f.write("LEET SPEAK SUBSTITUTIONS (discovered)\n")
                f.write("-"*70 + "\n")
                sorted_leet = sorted(leet.items(), key=lambda x: x[1], reverse=True)
                for substitution, count in sorted_leet:
                    if ' → ' in substitution:
                        f.write(f"  {substitution:15s} - {count:,} occurrences\n")
                f.write("\n")
            
            # Additional metadata
            if 'cache_time' in patterns:
                f.write("CACHE INFORMATION\n")
                f.write("-"*70 + "\n")
                f.write(f"  Cache created: {patterns['cache_time']}\n")
                if 'file_mtime' in patterns:
                    f.write(f"  Source modified: {patterns['file_mtime']}\n")
                f.write("\n")
            
            f.write("="*70 + "\n")
            f.write("This report shows patterns learned from leak file analysis.\n")
            f.write("Patterns are automatically applied to base words during generation.\n")
            f.write("="*70 + "\n")
        
        logging.info(f"[ML] Wrote patterns report to {report_path}")
        
    except Exception as e:
        logging.warning(f"[ML] Could not write patterns report: {e}")


def analyze_leak_with_ml(leak_file, sample_size=50000, streaming=True, 
                         use_cache=True, chunk_size=10000, ml_model='counter'):
    """
    Analyze password leak file using ML to learn patterns.
    Uses streaming for memory efficiency.
    
    Args:
        leak_file: Path to password leak file
        sample_size: Maximum number of passwords to analyze (None for unlimited)
        streaming: Use streaming mode for large files (recommended for >100MB)
        use_cache: Use cached patterns if available
        chunk_size: Number of passwords to process per chunk (for streaming)
        ml_model: ML model to use - 'counter' (default, fastest), 'markov' (better), 
                  or 'clustering' (slowest, minimal benefit)
    
    Note: For best performance, use streaming=True and ml_model='counter' or 'markov'
    """
    logging.info(f"[ML] Analyzing leak file: {leak_file} (model: {ml_model}, streaming: {streaming})")
    
    # Check cache first
    if use_cache:
        cache_path = _get_cache_path(leak_file)
        cached = _load_cached_patterns(cache_path)
        if cached:
            _apply_cached_patterns(cached)
            return True
    
    # Use streaming approach for large files
    if streaming:
        success = _analyze_leak_streaming(leak_file, sample_size, chunk_size, ml_model)
    else:
        success = _analyze_leak_full(leak_file, sample_size, ml_model)
    
    # Save to cache if successful
    if success and use_cache:
        patterns = {
            "appends": mangler_core.learned_appends,
            "prefixes": mangler_core.learned_prefixes,
            "leet": mangler_core.learned_leet,
            "weights": mangler_core.learned_weights,
        }
        _save_cached_patterns(cache_path, patterns)
    
    return success


def _apply_cached_patterns(cached):
    """Apply cached patterns to global state."""
    mangler_core.learned_appends.clear()
    mangler_core.learned_appends.extend(cached.get("appends", []))
    
    mangler_core.learned_prefixes.clear()
    mangler_core.learned_prefixes.extend(cached.get("prefixes", []))
    
    mangler_core.learned_leet.clear()
    mangler_core.learned_leet.update(cached.get("leet", {}))
    
    mangler_core.learned_weights.clear()
    mangler_core.learned_weights.update(cached.get("weights", {}))
    
    logging.info(f"[ML] Applied cached patterns: {len(mangler_core.learned_appends)} appends, "
                 f"{len(mangler_core.learned_prefixes)} prefixes")


def _analyze_leak_streaming(leak_file, sample_size, chunk_size, ml_model='counter'):
    """
    Streaming analysis that processes file in chunks to avoid memory issues.
    Suitable for multi-GB files.
    """
    logging.info(f"[ML] Using streaming mode (chunk size: {chunk_size}, model: {ml_model})")
    
    # Initialize counters for incremental updates
    append_counter = Counter()
    prepend_counter = Counter()
    char_subs = {}
    total_processed = 0
    
    # For Markov model, collect passwords
    passwords_for_markov = [] if ml_model == 'markov' else None
    
    try:
        with open(leak_file, "r", encoding="utf-8", errors="ignore") as f:
            chunk = []
            
            for line in f:
                pwd = line.strip()
                
                # Filter reasonable passwords
                if 4 <= len(pwd) <= 40:
                    chunk.append(pwd.lower())
                    total_processed += 1
                
                # Process chunk when full
                if len(chunk) >= chunk_size:
                    _update_pattern_counters(chunk, append_counter, prepend_counter, char_subs)
                    
                    # Collect for Markov if needed
                    if ml_model == 'markov' and passwords_for_markov is not None:
                        passwords_for_markov.extend(chunk[:min(1000, len(chunk))])  # Sample from chunk
                    
                    chunk = []
                    
                    # Log progress
                    if total_processed % (chunk_size * 5) == 0:
                        logging.info(f"[ML] Processed {total_processed:,} passwords...")
                    
                    # Check sample limit
                    if sample_size and total_processed >= sample_size:
                        logging.info(f"[ML] Reached sample limit of {sample_size:,}")
                        break
            
            # Process remaining chunk
            if chunk:
                _update_pattern_counters(chunk, append_counter, prepend_counter, char_subs)
                if ml_model == 'markov' and passwords_for_markov is not None:
                    passwords_for_markov.extend(chunk[:min(1000, len(chunk))])
        
        if total_processed < 100:
            logging.warning("[ML] Not enough passwords for meaningful analysis.")
            return False
        
        logging.info(f"[ML] Analyzed {total_processed:,} passwords in streaming mode")
        
        # Extract learned patterns
        _apply_learned_patterns(append_counter, prepend_counter, char_subs, total_processed)
        
        # Run Markov model if requested
        if ml_model == 'markov' and passwords_for_markov:
            _run_markov_learning(passwords_for_markov)
        
        return True
        
    except Exception as e:
        logging.error(f"[ML] Streaming analysis failed: {e}")
        return False


def _run_markov_learning(passwords):
    """
    Train Markov Chain model and generate additional patterns.
    Much faster than clustering with better results.
    """
    logging.info(f"[ML] Training Markov Chain on {len(passwords)} passwords...")
    
    try:
        markov = PasswordMarkovChain(order=2)
        markov.train(passwords)
        
        # Generate additional suffixes using common base words
        test_words = ["password", "admin", "user", "test", "welcome", "login"]
        discovered_suffixes = set()
        
        for word in test_words:
            variations = markov.generate_variations(word, num_variations=15)
            for suffix in variations:
                # Filter useful suffixes
                if 1 <= len(suffix) <= 6 and suffix not in mangler_core.common_suffixes:
                    discovered_suffixes.add(suffix)
        
        # Add discovered suffixes to learned patterns
        for suffix in discovered_suffixes:
            if suffix not in mangler_core.learned_appends:
                mangler_core.learned_appends.append(suffix)
        
        logging.info(f"[ML] Markov Chain discovered {len(discovered_suffixes)} additional suffixes")
        
    except Exception as e:
        logging.warning(f"[ML] Markov Chain learning failed: {e}")


def _analyze_leak_full(leak_file, sample_size, ml_model='counter'):
    """
    Original full-load analysis (kept for backward compatibility with small files).
    """
    passwords = []
    try:
        with open(leak_file, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if sample_size and i >= sample_size:
                    break
                pwd = line.strip()
                # Filter reasonable passwords
                if 4 <= len(pwd) <= 40:
                    passwords.append(pwd.lower())
    except Exception as e:
        logging.error(f"[ML] Could not read leak file: {e}")
        return False
    
    if len(passwords) < 100:
        logging.warning("[ML] Not enough passwords for meaningful analysis.")
        return False
    
    logging.info(f"[ML] Loaded {len(passwords)} passwords for analysis (model: {ml_model})")
    
    # Use the core module's analyze_patterns function
    top_appends, top_prepends, learned_subs = mangler_core.analyze_patterns(passwords, top_n=50)
    
    # Update global learned patterns
    mangler_core.learned_appends.clear()
    mangler_core.learned_appends.extend([
        a for a in top_appends 
        if a not in mangler_core.common_suffixes and len(a) <= 6
    ])
    
    mangler_core.learned_prefixes.clear()
    mangler_core.learned_prefixes.extend([
        p for p in top_prepends 
        if p not in mangler_core.common_prefixes and len(p) <= 6
    ])
    
    logging.info(f"[ML] Learned {len(mangler_core.learned_appends)} new appends")
    logging.info(f"[ML] Learned {len(mangler_core.learned_prefixes)} new prepends")
    
    # Update leet mappings
    for char, subs in learned_subs.items():
        if char not in mangler_core.learned_leet:
            mangler_core.learned_leet[char] = []
        for sub in subs:
            if sub not in mangler_core.learned_leet[char]:
                mangler_core.learned_leet[char].append(sub)
    
    logging.info(f"[ML] Learned leet substitutions for {len(learned_subs)} characters")
    
    # Run additional ML model if requested
    if ml_model == 'markov':
        _run_markov_learning(passwords)
    elif ml_model == 'clustering':
        # Advanced clustering for pattern discovery (OPTIONAL - expensive and minimal value)
        # Only run on smaller samples to avoid memory issues
        if len(passwords) >= 5000 and len(passwords) <= 50000:
            try:
                logging.info("[ML] Running optional clustering analysis (this may take a while)...")
                _perform_clustering_analysis(passwords[:10000])
            except Exception as e:
                logging.warning(f"[ML] Clustering analysis failed: {e}")
        else:
            logging.info("[ML] Skipping clustering (not enough or too many passwords)")
    
    # Calculate weights for learned patterns
    total = len(passwords)
    mangler_core.learned_weights.clear()
    
    for append in mangler_core.learned_appends[:30]:
        count = sum(1 for pwd in passwords if pwd.endswith(append))
        mangler_core.learned_weights[f"append_{append}"] = count / total
    
    for prepend in mangler_core.learned_prefixes[:30]:
        count = sum(1 for pwd in passwords if pwd.startswith(prepend))
        mangler_core.learned_weights[f"prepend_{prepend}"] = count / total
    
    logging.info(f"[ML] Rule induction complete! Total patterns learned: {len(mangler_core.learned_weights)}")
    return True


def _update_pattern_counters(passwords, append_counter, prepend_counter, char_subs):
    """
    Update pattern counters with a chunk of passwords.
    This enables streaming analysis without loading everything into memory.
    """
    for pwd in passwords:
        if len(pwd) < 4:
            continue
        
        # Analyze suffixes and prefixes
        for length in [1, 2, 3, 4, 5]:
            if len(pwd) > length:
                suffix = pwd[-length:]
                prefix = pwd[:length]
                
                # Count numeric or special suffixes
                if suffix.isdigit() or any(c in suffix for c in mangler_core.special_chars):
                    append_counter[suffix] += 1
                
                # Count numeric or special prefixes
                if prefix.isdigit() or any(c in prefix for c in mangler_core.special_chars):
                    prepend_counter[prefix] += 1
        
        # Analyze character substitutions (leet patterns)
        for i, c in enumerate(pwd):
            if not c.isalpha() and i > 0 and i < len(pwd) - 1:
                # Check surrounding context
                context = pwd[max(0, i-1):min(len(pwd), i+2)]
                for char in context:
                    if char.isalpha():
                        if char.lower() not in char_subs:
                            char_subs[char.lower()] = Counter()
                        char_subs[char.lower()][c] += 1


def _apply_learned_patterns(append_counter, prepend_counter, char_subs, total_processed):
    """Apply learned patterns from counters to global state."""
    # Extract top patterns
    top_appends = [item[0] for item in append_counter.most_common(50)]
    top_prepends = [item[0] for item in prepend_counter.most_common(50)]
    
    # Update global learned patterns
    mangler_core.learned_appends.clear()
    mangler_core.learned_appends.extend([
        a for a in top_appends 
        if a not in mangler_core.common_suffixes and len(a) <= 6
    ])
    
    mangler_core.learned_prefixes.clear()
    mangler_core.learned_prefixes.extend([
        p for p in top_prepends 
        if p not in mangler_core.common_prefixes and len(p) <= 6
    ])
    
    logging.info(f"[ML] Learned {len(mangler_core.learned_appends)} new appends")
    logging.info(f"[ML] Learned {len(mangler_core.learned_prefixes)} new prepends")
    
    # Update leet mappings
    for char, subs in char_subs.items():
        if len(subs) > 0:
            top_subs = [s for s, count in subs.most_common(5) if count > 2]
            if top_subs:
                if char not in mangler_core.learned_leet:
                    mangler_core.learned_leet[char] = []
                for sub in top_subs:
                    if sub not in mangler_core.learned_leet[char]:
                        mangler_core.learned_leet[char].append(sub)
    
    logging.info(f"[ML] Learned leet substitutions for {len(mangler_core.learned_leet)} characters")
    
    # Calculate weights for learned patterns
    mangler_core.learned_weights.clear()
    
    for append in mangler_core.learned_appends[:30]:
        count = append_counter.get(append, 0)
        mangler_core.learned_weights[f"append_{append}"] = count / total_processed
    
    for prepend in mangler_core.learned_prefixes[:30]:
        count = prepend_counter.get(prepend, 0)
        mangler_core.learned_weights[f"prepend_{prepend}"] = count / total_processed
    
    logging.info(f"[ML] Rule induction complete! Total patterns learned: {len(mangler_core.learned_weights)}")


def _perform_clustering_analysis(passwords, n_clusters=15):
    """
    Perform clustering analysis to discover patterns.
    Uses MiniBatchKMeans for efficiency with large datasets.
    Only called on moderate-sized samples to avoid memory issues.
    """
    if not SKLEARN_AVAILABLE:
        logging.warning("[ML] Clustering analysis skipped - sklearn not available")
        return
    
    logging.info("[ML] Performing clustering analysis for pattern discovery...")
    
    try:
        # Vectorize passwords using character n-grams
        vectorizer = CountVectorizer(
            analyzer='char',
            ngram_range=(2, 3),
            lowercase=True,
            max_features=5000,  # Limit features for efficiency
            min_df=2  # Ignore very rare patterns
        )
        
        X = vectorizer.fit_transform(passwords)
        features = vectorizer.get_feature_names_out()
        
        # Use MiniBatchKMeans for better scalability
        kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=42,
            batch_size=1000,
            max_iter=100,
            n_init=3
        )
        
        kmeans.fit(X)
        
        # Extract patterns from cluster centers
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        
        for i in range(min(n_clusters, 10)):
            for ind in order_centroids[i, :10]:
                pattern = features[ind]
                
                # Try to extract leet substitution patterns
                base_char = re.sub(r'[^a-z]', '', pattern)
                leet_char = re.sub(r'[a-z]', '', pattern)
                
                if len(base_char) == 1 and leet_char:
                    char = base_char[0]
                    if char not in mangler_core.learned_leet:
                        mangler_core.learned_leet[char] = []
                    
                    for lc in set(leet_char):
                        if lc not in mangler_core.learned_leet[char] and lc not in "0123456789":
                            mangler_core.learned_leet[char].append(lc)
        
        logging.info("[ML] Clustering analysis completed")
        
    except Exception as e:
        logging.warning(f"[ML] Clustering failed: {e}")


def get_ml_stats():
    """Return statistics about learned patterns."""
    return {
        "learned_appends": len(mangler_core.learned_appends),
        "learned_prefixes": len(mangler_core.learned_prefixes),
        "learned_leet": len(mangler_core.learned_leet),
        "total_weights": len(mangler_core.learned_weights),
    }


# Export main functions
__all__ = [
    'analyze_leak_with_ml',
    'get_ml_stats',
    'PasswordMarkovChain',
]
