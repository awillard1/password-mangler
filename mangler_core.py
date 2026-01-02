"""
Core password mangling functionality with optimized generators and best-in-class transformations.
"""

import itertools
import logging
from datetime import datetime
from collections import Counter
import re

# ===========================
# ENHANCED MANGLING RULES
# ===========================

# Comprehensive leet speak mappings (best-in-class)
leet_mappings = {
    "a": ["4", "@", "/\\", "/-\\", "^", "∀"],
    "b": ["8", "13", "|3", "ß", "6"],
    "c": ["(", "[", "{", "<", "©"],
    "d": ["|)", "|>", ")", "[)"],
    "e": ["3", "&", "€", "£"],
    "f": ["|=", "ph", "|#"],
    "g": ["9", "6", "&", "(_+"],
    "h": ["#", "|-|", "[-]", "}{"],
    "i": ["1", "!", "|", "¡"],
    "j": ["]", "_|", "_/"],
    "k": ["|<", "|{", "|("],
    "l": ["1", "|", "|_", "£"],
    "m": ["|v|", "(\\/)", "|\\/|"],
    "n": ["|\\|", "/\\/", "[\\]", "<\\>"],
    "o": ["0", "()", "[]", "{}"],
    "p": ["|>", "|*", "?"],
    "q": ["9", "0_", "()_"],
    "r": ["|2", "12", "®"],
    "s": ["5", "$", "§"],
    "t": ["7", "+", "†"],
    "u": ["|_|", "(_)", "\\_\\", "\\_/"],
    "v": ["\\/", "|/", "\\|"],
    "w": ["\\/\\/", "vv", "\\^/", "\\|/"],
    "x": ["><", "}{", ")(", "×"],
    "y": ["`/", "¥", "\\|/"],
    "z": ["2", "7_", ">_"],
}

# Common suffixes with years, special chars, and patterns
current_year = datetime.now().year
common_suffixes = [
    # Numbers
    "1", "12", "123", "1234", "12345", "123456", "1234567", "12345678", "123456789",
    "0", "01", "00", "007", "69", "666", "777", "888", "999",
    
    # Special characters
    "!", "!!", "!!!", "@", "#", "$", "$$", "%", "&", "*",
    ".", "..", "...", "_", "__", "-", "--",
    
    # Years and dates
    str(current_year), str(current_year-1), str(current_year+1),
    str(current_year)[-2:], str(current_year-1)[-2:], str(current_year+1)[-2:],
    "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027",
    "20", "21", "22", "23", "24", "25", "26", "27",
    
    # Common patterns
    "qwerty", "qwert", "admin", "password", "pass", "letmein", "welcome",
    "love", "baby", "princess", "master", "test", "root",
    
    # Gaming/Internet culture
    "pro", "noob", "pwn", "ftw", "gg", "ez", "xD", "lol",
]

# Common prefixes
common_prefixes = [
    "1", "12", "123", "@", "#", "!", "the", "my", "super", "ultra"
]

# Keyboard walks (spatial patterns)
keyboard_walks = [
    # Row walks
    "qwerty", "qwert", "qwe", "wert", "erty",
    "asdfg", "asdf", "sdfg", "dfgh",
    "zxcvb", "zxcv", "xcvb", "cvbn",
    
    # Column walks
    "qaz", "wsx", "edc", "rfv", "tgb", "yhn", "ujm",
    "qazwsx", "wsxedc", "edcrfv",
    
    # Diagonal walks
    "1qaz2wsx", "1q2w3e", "1q2w3e4r",
    
    # Number pad
    "147", "258", "369", "159", "357", "789456123",
    
    # Popular patterns
    "123456", "654321", "111111", "000000",
]

# Special character sets for combinations
special_chars = "!@#$%^&*()-_=+[]{}|;:,'\".<>?/\\`~"

# Phonetic substitutions (comprehensive)
phonetic_replacements = {
    "love": ["luv", "<3", "lv", "♥", "❤"],
    "you": ["u", "yu", "yoo"],
    "are": ["r", "ar"],
    "for": ["4", "four"],
    "to": ["2", "too", "two"],
    "at": ["@", "att"],
    "and": ["&", "n", "nd"],
    "the": ["da", "de", "teh"],
    "ate": ["8", "eat"],
    "great": ["gr8", "grate"],
    "forever": ["4ever", "4eva"],
    "before": ["b4", "be4"],
    "see": ["c", "sea"],
    "why": ["y"],
    "because": ["cuz", "coz", "bcuz", "bc"],
    "though": ["tho", "tho"],
    "through": ["thru", "thro"],
    "night": ["nite", "nyte"],
    "light": ["lite"],
    "please": ["plz", "pls"],
    "thanks": ["thx", "thnx", "tnx"],
    "okay": ["ok", "k"],
    "cool": ["kool", "kewl"],
}

# Years generation (extended range)
years = [str(y) for y in range(current_year - 30, current_year + 10)] + \
        [str(y)[-2:] for y in range(current_year - 30, current_year + 10)]

# Learned patterns (will be populated by ML)
learned_appends = []
learned_prefixes = []
learned_leet = {}
learned_weights = {}

# ===========================
# OPTIMIZED MANGLE FUNCTIONS (GENERATORS)
# ===========================

def apply_casing(word):
    """Generate all common casing variations."""
    if not word:
        return
    
    yield word  # Original
    yield word.lower()  # lowercase
    yield word.upper()  # UPPERCASE
    yield word.capitalize()  # Capitalized
    yield word.swapcase()  # sWAPcASE
    
    # Additional intelligent casing
    if len(word) > 1:
        yield word[0].upper() + word[1:].lower()  # First upper, rest lower
        yield word[:-1].lower() + word[-1].upper()  # Last upper
    
    if len(word) > 2:
        # Alternating case
        alt1 = ''.join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(word))
        alt2 = ''.join(c.lower() if i % 2 == 0 else c.upper() for i, c in enumerate(word))
        yield alt1
        yield alt2


def apply_leet(word, max_depth=3, max_variants=50):
    """
    Generate leet speak variations with depth control.
    Uses generators for memory efficiency.
    """
    if not word:
        return
    
    # Merge base and learned leet mappings
    mappings = {**leet_mappings, **learned_leet}
    
    # Find all positions that can be leetified
    positions = [(i, c.lower()) for i, c in enumerate(word) if c.lower() in mappings]
    
    if not positions:
        yield word
        return
    
    # Original word
    yield word
    
    variant_count = 0
    # Generate combinations up to max_depth
    for r in range(1, min(max_depth + 1, len(positions) + 1)):
        if variant_count >= max_variants:
            break
            
        for combo in itertools.combinations(positions, r):
            if variant_count >= max_variants:
                break
                
            # Generate all possible replacements for this combination
            replacement_lists = [mappings[c][:3] for _, c in combo]  # Limit to top 3 per char
            
            for repls in itertools.product(*replacement_lists):
                if variant_count >= max_variants:
                    break
                    
                variant = list(word)
                for (idx, orig_char), repl in zip(combo, repls):
                    # Preserve original case
                    if word[idx].isupper():
                        variant[idx] = repl.upper() if repl.isalpha() else repl
                    else:
                        variant[idx] = repl
                
                yield "".join(variant)
                variant_count += 1


def apply_phonetic(word):
    """Generate phonetic substitutions."""
    if not word:
        return
    
    w = word.lower()
    generated = False
    
    for key, repls in phonetic_replacements.items():
        if key in w:
            for repl in repls:
                yield w.replace(key, repl)
                generated = True
    
    if not generated:
        yield word


def apply_appends(word, max_appends=30):
    """Generate variations with appended suffixes (Hashcat-compatible)."""
    if not word:
        return
    
    # Combine all suffix sources
    all_suffixes = list(set(
        common_suffixes[:20] +
        learned_appends[:15] +
        years[:15] +
        list(special_chars)[:10]
    ))
    
    seen = set()
    count = 0
    
    for suffix in all_suffixes:
        if count >= max_appends:
            break

        # Generate Hashcat-compatible append rules ($1$2$3 for suffix "123")
        rule_sequence = "".join(f"${char}" for char in suffix)
        
        # Check if this rule sequence is unique
        if rule_sequence not in seen:
            seen.add(rule_sequence)
            yield rule_sequence
            count += 1


def apply_prepends(word, max_prepends=15):
    """Generate Hashcat-compatible prepend rules (prefix appears in forward order)."""
    if not word:
        return
    
    all_prefixes = list(set(common_prefixes[:10] + learned_prefixes[:10]))
    
    seen = set()
    count = 0

    for prefix in all_prefixes:
        if count >= max_prepends:
            break

        # Reverse the prefix so that ^3^2^1 results in "123" at the front
        rule_sequence = "".join(f"^{char}" for char in reversed(prefix))

        if rule_sequence not in seen:
            seen.add(rule_sequence)
            yield rule_sequence
            count += 1


def apply_keyboard_walks(word):
    """Generate keyboard walk patterns."""
    if not word:
        return
    
    for walk in keyboard_walks[:20]:  # Limit to top 20
        yield word + walk
        yield walk + word


def apply_character_mutations(word):
    """Apply character-level mutations like doubling, deletion."""
    if not word or len(word) < 2:
        return
    
    # Character doubling at various positions
    for i in range(min(3, len(word))):
        if word[i].isalpha():
            yield word[:i] + word[i] * 2 + word[i+1:]
    
    # Character tripling
    if word[0].isalpha():
        yield word[0] * 3 + word[1:]


def apply_middle_injections(word):
    """Inject special characters in the middle of words."""
    if not word or len(word) < 4:
        return
    
    mid = len(word) // 2
    for char in ["!", "1", "@", "_", "-"]:
        yield word[:mid] + char + word[mid:]


def apply_reversals(word):
    """Generate reversed variations."""
    if not word:
        return
    
    yield word[::-1]  # Full reverse
    
    if len(word) > 3:
        # Reverse halves
        mid = len(word) // 2
        yield word[mid:] + word[:mid]


def generate_variations(word, ruleset="advanced", max_per_word=1000):
    """
    Main variation generator with lazy evaluation.
    Generates variations on-the-fly without storing all in memory.
    """
    if not word or not word.strip():
        return
    
    word = word.strip()
    seen = set()
    variant_count = 0
    
    # Helper to track and yield unique variants
    def yield_unique(variant):
        nonlocal variant_count
        if variant and variant not in seen and variant_count < max_per_word:
            seen.add(variant)
            variant_count += 1
            return True
        return False
    
    # Base casing variations
    base_variants = list(apply_casing(word))
    for var in base_variants:
        if yield_unique(var):
            yield var
    
    if ruleset == "simple":
        return
    
    # Advanced and extreme rules
    if ruleset in ["advanced", "extreme"]:
        # Apply transformations to a limited set of base variants
        transform_base = base_variants[:5]  # Limit to avoid explosion
        
        # Leet speak
        for var in transform_base:
            for leet_var in apply_leet(var, max_depth=2 if ruleset == "advanced" else 3):
                if yield_unique(leet_var):
                    yield leet_var
        
        # Appends (high value)
        for var in base_variants[:3]:
            for append_var in apply_appends(var, max_appends=20 if ruleset == "advanced" else 30):
                if yield_unique(append_var):
                    yield append_var
        
        # Prepends
        for var in base_variants[:3]:
            for prepend_var in apply_prepends(var, max_prepends=10 if ruleset == "advanced" else 15):
                if yield_unique(prepend_var):
                    yield prepend_var
        
        # Phonetic
        for var in base_variants[:3]:
            for phon_var in apply_phonetic(var):
                if yield_unique(phon_var):
                    yield phon_var
        
        # Character mutations
        for var in base_variants[:2]:
            for mut_var in apply_character_mutations(var):
                if yield_unique(mut_var):
                    yield mut_var
        
        # Middle injections
        for var in base_variants[:2]:
            for inj_var in apply_middle_injections(var):
                if yield_unique(inj_var):
                    yield inj_var
        
        # Reversals
        for var in base_variants[:2]:
            for rev_var in apply_reversals(var):
                if yield_unique(rev_var):
                    yield rev_var
        
        if ruleset == "extreme":
            # Keyboard walks (expensive, extreme only)
            for var in base_variants[:2]:
                for walk_var in apply_keyboard_walks(var):
                    if yield_unique(walk_var):
                        yield walk_var
            
            # Combined transformations (leet + append)
            for var in base_variants[:2]:
                leet_vars = list(itertools.islice(apply_leet(var, max_depth=2), 10))
                for leet_var in leet_vars:
                    for suffix in common_suffixes[:10]:
                        combined = leet_var + suffix
                        if yield_unique(combined):
                            yield combined
    
    # Always force some critical high-value patterns
    for suffix in ["123", "!", "!!", str(current_year), str(current_year)[-2:], 
                   str(current_year-1)[-2:], "1234", "@"]:
        for base in [word, word.capitalize(), word.lower()]:
            if yield_unique(base + suffix):
                yield base + suffix


def process_word(args):
    """Process a single word (used by worker threads)."""
    word, ruleset, max_vars = args
    return list(generate_variations(word.strip(), ruleset, max_vars))


# ===========================
# STATISTICS AND ANALYSIS
# ===========================

def analyze_patterns(passwords, top_n=50):
    """
    Analyze common patterns in passwords for ML learning.
    Returns: appends, prepends, substitutions
    """
    if not passwords or len(passwords) < 100:
        return [], [], {}
    
    append_counter = Counter()
    prepend_counter = Counter()
    char_subs = {}
    
    # Analyze suffixes and prefixes
    for pwd in passwords:
        if len(pwd) < 4:
            continue
            
        # Check various lengths
        for length in [1, 2, 3, 4, 5]:
            if len(pwd) > length:
                suffix = pwd[-length:]
                prefix = pwd[:length]
                
                # Count numeric or special suffixes
                if suffix.isdigit() or any(c in suffix for c in special_chars):
                    append_counter[suffix] += 1
                
                # Count numeric or special prefixes
                if prefix.isdigit() or any(c in prefix for c in special_chars):
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
    
    # Extract top patterns
    top_appends = [item[0] for item in append_counter.most_common(top_n)]
    top_prepends = [item[0] for item in prepend_counter.most_common(top_n)]
    
    # Extract meaningful substitutions
    learned_subs = {}
    for char, subs in char_subs.items():
        if len(subs) > 0:
            top_subs = [s for s, count in subs.most_common(5) if count > 2]
            if top_subs:
                learned_subs[char] = top_subs
    
    return top_appends, top_prepends, learned_subs


# Export main functions
__all__ = [
    'generate_variations',
    'process_word',
    'analyze_patterns',
    'learned_appends',
    'learned_prefixes',
    'learned_leet',
    'learned_weights',
]
