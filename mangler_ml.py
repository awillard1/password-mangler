"""
Machine Learning based rule induction for password mangling.
Optimized for efficiency with streaming and sampling.
"""

import logging
from collections import Counter
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cluster import MiniBatchKMeans
import mangler_core

# ===========================
# ML-BASED RULE INDUCTION
# ===========================

def analyze_leak_with_ml(leak_file, sample_size=50000, streaming=True):
    """
    Analyze password leak file using ML to learn patterns.
    Uses streaming for memory efficiency and MiniBatchKMeans for scalability.
    
    Args:
        leak_file: Path to password leak file
        sample_size: Maximum number of passwords to analyze
        streaming: Use streaming mode for large files
    """
    logging.info(f"[ML] Analyzing leak file: {leak_file} (sample: {sample_size}, streaming: {streaming})")
    
    passwords = []
    try:
        with open(leak_file, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= sample_size:
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
    
    logging.info(f"[ML] Loaded {len(passwords)} passwords for analysis")
    
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
    
    # Advanced clustering for pattern discovery (optional, expensive)
    if len(passwords) >= 5000:
        try:
            _perform_clustering_analysis(passwords[:10000])
        except Exception as e:
            logging.warning(f"[ML] Clustering analysis failed: {e}")
    
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


def _perform_clustering_analysis(passwords, n_clusters=15):
    """
    Perform clustering analysis to discover patterns.
    Uses MiniBatchKMeans for efficiency with large datasets.
    """
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
]
