"""
Advanced wordlist analysis and high-quality Hashcat rule generation.

This module analyzes password wordlists to extract transformation patterns
and generate optimal Hashcat rules based on actual usage patterns.
"""

import logging
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import itertools


class WordlistAnalyzer:
    """
    Comprehensive wordlist analyzer that extracts patterns for rule generation.
    """
    
    def __init__(self):
        self.total_passwords = 0
        self.length_distribution = Counter()
        self.charset_usage = defaultdict(int)
        self.position_chars = defaultdict(lambda: defaultdict(int))
        self.common_prefixes = Counter()
        self.common_suffixes = Counter()
        self.leet_patterns = defaultdict(lambda: defaultdict(int))
        self.case_patterns = Counter()
        self.digit_patterns = Counter()
        self.special_patterns = Counter()
        self.transformations = []
        
    def analyze(self, passwords, base_dictionary=None):
        """
        Perform comprehensive analysis of password list.
        
        Args:
            passwords: List of passwords to analyze
            base_dictionary: Optional list of base words to detect transformations
        
        Returns:
            Analysis results dictionary
        """
        logging.info(f"[Analyzer] Analyzing {len(passwords)} passwords...")
        
        self.total_passwords = len(passwords)
        
        for pwd in passwords:
            self._analyze_single(pwd)
            
            # If base dictionary provided, try to infer transformations
            if base_dictionary:
                transformation = self._infer_transformation(pwd, base_dictionary)
                if transformation:
                    self.transformations.append(transformation)
        
        return self._compile_results()
    
    def _analyze_single(self, pwd):
        """Analyze a single password for patterns."""
        # Length distribution
        self.length_distribution[len(pwd)] += 1
        
        # Charset usage
        has_lower = any(c.islower() for c in pwd)
        has_upper = any(c.isupper() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_special = any(not c.isalnum() for c in pwd)
        
        if has_lower:
            self.charset_usage['lowercase'] += 1
        if has_upper:
            self.charset_usage['uppercase'] += 1
        if has_digit:
            self.charset_usage['digits'] += 1
        if has_special:
            self.charset_usage['special'] += 1
        
        # Position-based character analysis
        for i, c in enumerate(pwd):
            pos = min(i, 10)  # Group positions 10+ together
            if c.islower():
                self.position_chars[pos]['lower'] += 1
            elif c.isupper():
                self.position_chars[pos]['upper'] += 1
            elif c.isdigit():
                self.position_chars[pos]['digit'] += 1
            else:
                self.position_chars[pos]['special'] += 1
        
        # Prefix/suffix analysis (1-6 characters)
        for length in range(1, min(7, len(pwd))):
            prefix = pwd[:length]
            suffix = pwd[-length:]
            
            # Only count if numeric or special
            if suffix.isdigit() or any(not c.isalnum() for c in suffix):
                self.common_suffixes[suffix] += 1
            
            if prefix.isdigit() or any(not c.isalnum() for c in prefix):
                self.common_prefixes[prefix] += 1
        
        # Leet speak pattern detection
        self._detect_leet_patterns(pwd)
        
        # Case pattern analysis
        self._analyze_case_pattern(pwd)
        
        # Digit pattern analysis
        self._analyze_digit_pattern(pwd)
        
        # Special character pattern analysis
        self._analyze_special_pattern(pwd)
    
    def _detect_leet_patterns(self, pwd):
        """Detect leet speak substitution patterns."""
        leet_map = {
            '@': 'a', '4': 'a',
            '3': 'e',
            '1': 'i', '!': 'i',
            '0': 'o',
            '$': 's', '5': 's',
            '7': 't',
        }
        
        for leet_char, base_char in leet_map.items():
            if leet_char in pwd:
                # Check if it's likely a substitution (has other letters)
                if any(c.isalpha() for c in pwd):
                    self.leet_patterns[base_char][leet_char] += 1
    
    def _analyze_case_pattern(self, pwd):
        """Analyze capitalization patterns."""
        if not any(c.isalpha() for c in pwd):
            return
        
        if pwd.isupper():
            self.case_patterns['all_upper'] += 1
        elif pwd.islower():
            self.case_patterns['all_lower'] += 1
        elif pwd[0].isupper() and pwd[1:].islower():
            self.case_patterns['capitalize'] += 1
        elif pwd[0].islower() and any(c.isupper() for c in pwd[1:]):
            self.case_patterns['mixed'] += 1
        elif any(c.isupper() for c in pwd):
            self.case_patterns['has_upper'] += 1
    
    def _analyze_digit_pattern(self, pwd):
        """Analyze where and how digits appear."""
        digits = ''.join(c for c in pwd if c.isdigit())
        if not digits:
            return
        
        # Trailing digits (most common)
        if pwd[-1].isdigit():
            trailing = re.search(r'\d+$', pwd)
            if trailing:
                self.digit_patterns[f'trailing_{len(trailing.group())}'] += 1
                self.digit_patterns[f'value_{trailing.group()}'] += 1
        
        # Leading digits
        if pwd[0].isdigit():
            leading = re.search(r'^\d+', pwd)
            if leading:
                self.digit_patterns[f'leading_{len(leading.group())}'] += 1
    
    def _analyze_special_pattern(self, pwd):
        """Analyze special character usage patterns."""
        specials = ''.join(c for c in pwd if not c.isalnum())
        if not specials:
            return
        
        # Trailing special chars
        if not pwd[-1].isalnum():
            trailing = re.search(r'[^a-zA-Z0-9]+$', pwd)
            if trailing:
                self.special_patterns[f'trailing_{trailing.group()}'] += 1
        
        # Leading special chars
        if not pwd[0].isalnum():
            leading = re.search(r'^[^a-zA-Z0-9]+', pwd)
            if leading:
                self.special_patterns[f'leading_{leading.group()}'] += 1
    
    def _infer_transformation(self, pwd, base_dictionary):
        """
        Try to infer what base word and transformation produced this password.
        
        Returns:
            (base_word, transformation_rule) or None
        """
        pwd_lower = pwd.lower()
        
        # Remove common suffixes to find base
        for suffix_len in range(1, min(7, len(pwd))):
            suffix = pwd[-suffix_len:]
            if suffix.isdigit() or any(not c.isalnum() for c in suffix):
                potential_base = pwd[:-suffix_len].lower()
                
                # Check if potential base is in dictionary
                if potential_base in base_dictionary:
                    # Found likely base word, infer transformation
                    rule = self._generate_rule(potential_base, pwd)
                    return (potential_base, rule)
        
        # Check without suffix removal
        if pwd_lower in base_dictionary:
            rule = self._generate_rule(pwd_lower, pwd)
            return (pwd_lower, rule)
        
        return None
    
    def _generate_rule(self, base, result):
        """Generate Hashcat rule that transforms base → result."""
        rule_parts = []
        
        # Case transformations
        if result[0].isupper() and base[0].islower():
            if len(result) > 1 and result[1:].islower():
                rule_parts.append('c')  # Capitalize
            elif result.isupper():
                rule_parts.append('u')  # All uppercase
        
        # Leet substitutions
        leet_map = {
            'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '$', 't': '7'
        }
        result_lower = result.lower()
        for i, (b, r) in enumerate(zip(base, result_lower)):
            if b != r and b in leet_map and leet_map[b] == result[i]:
                rule_parts.append(f's{b}{result[i]}')
        
        # Appends (check if result is longer)
        if len(result) > len(base):
            suffix = result[len(base):]
            for char in suffix:
                rule_parts.append(f'${char}')
        
        return ''.join(rule_parts) if rule_parts else ':'
    
    def _compile_results(self):
        """Compile analysis results into structured format."""
        return {
            'total_passwords': self.total_passwords,
            'length_distribution': dict(self.length_distribution.most_common()),
            'charset_usage': dict(self.charset_usage),
            'top_suffixes': self.common_suffixes.most_common(50),
            'top_prefixes': self.common_prefixes.most_common(50),
            'leet_patterns': {k: dict(v) for k, v in self.leet_patterns.items()},
            'case_patterns': dict(self.case_patterns),
            'digit_patterns': dict(self.digit_patterns),
            'special_patterns': dict(self.special_patterns),
            'position_analysis': {
                pos: dict(chars) for pos, chars in self.position_chars.items()
            }
        }
    
    def generate_optimal_rules(self, analysis, max_rules=1000):
        """
        Generate optimal Hashcat rules based on analysis.
        
        Prioritizes rules by:
        1. Frequency in wordlist
        2. Simplicity (shorter rules preferred)
        3. Diversity (different transformation types)
        
        Returns:
            List of (rule, estimated_frequency) tuples
        """
        logging.info("[Analyzer] Generating optimal Hashcat rules...")
        
        rules = []
        rule_frequencies = Counter()
        
        # 1. Identity rule (always include)
        rules.append((':',  1.0))
        
        # 2. Case transformation rules (high value)
        if analysis['case_patterns'].get('capitalize', 0) > 0:
            freq = analysis['case_patterns']['capitalize'] / analysis['total_passwords']
            rules.append(('c', freq))
        
        if analysis['case_patterns'].get('all_upper', 0) > 0:
            freq = analysis['case_patterns']['all_upper'] / analysis['total_passwords']
            rules.append(('u', freq))
        
        if analysis['case_patterns'].get('all_lower', 0) > 0:
            freq = analysis['case_patterns']['all_lower'] / analysis['total_passwords']
            rules.append(('l', freq))
        
        # 3. Common suffix append rules (very high value)
        for suffix, count in analysis['top_suffixes'][:30]:
            freq = count / analysis['total_passwords']
            rule = ''.join(f'${c}' for c in suffix)
            rules.append((rule, freq))
        
        # 4. Common prefix prepend rules
        for prefix, count in analysis['top_prefixes'][:15]:
            freq = count / analysis['total_passwords']
            rule = ''.join(f'^{c}' for c in reversed(prefix))
            rules.append((rule, freq))
        
        # 5. Leet speak substitution rules (high value)
        for base_char, subs in analysis['leet_patterns'].items():
            for leet_char, count in subs.items():
                freq = count / analysis['total_passwords']
                rules.append((f's{base_char}{leet_char}', freq))
        
        # 6. Combined transformation rules (capitalize + append)
        for suffix, count in analysis['top_suffixes'][:20]:
            freq = count / analysis['total_passwords']
            # Capitalize + append
            rule = 'c' + ''.join(f'${c}' for c in suffix)
            rules.append((rule, freq * 0.7))  # Slightly lower probability
        
        # 7. Leet + append combinations (common pattern)
        common_leet = [('a', '@'), ('e', '3'), ('o', '0'), ('s', '$')]
        for base, leet in common_leet:
            for suffix, count in analysis['top_suffixes'][:10]:
                freq = count / analysis['total_passwords']
                rule = f's{base}{leet}' + ''.join(f'${c}' for c in suffix)
                rules.append((rule, freq * 0.5))
        
        # 8. Learned transformation rules (if available)
        if hasattr(self, 'transformations') and self.transformations:
            trans_rules = Counter(rule for _, rule in self.transformations)
            for rule, count in trans_rules.most_common(100):
                freq = count / len(self.transformations)
                rules.append((rule, freq))
        
        # Sort by frequency and remove duplicates
        unique_rules = {}
        for rule, freq in rules:
            if rule not in unique_rules or freq > unique_rules[rule]:
                unique_rules[rule] = freq
        
        # Sort by frequency, take top N
        sorted_rules = sorted(unique_rules.items(), key=lambda x: x[1], reverse=True)
        
        logging.info(f"[Analyzer] Generated {len(sorted_rules)} unique rules")
        
        return sorted_rules[:max_rules]


def analyze_and_generate_rules(wordlist_file, output_file, base_dict_file=None, 
                               max_rules=1000, streaming=True, chunk_size=100000):
    """
    Analyze wordlist and generate high-quality Hashcat rules.
    
    Args:
        wordlist_file: Password wordlist to analyze
        output_file: Output file for Hashcat rules
        base_dict_file: Optional base dictionary for transformation inference
        max_rules: Maximum number of rules to generate
        streaming: Use streaming mode for large files
        chunk_size: Number of passwords to process per chunk
    
    Returns:
        Analysis results and generated rules
    """
    logging.info(f"[Analyzer] Starting analysis of {wordlist_file}")
    
    analyzer = WordlistAnalyzer()
    
    # Load base dictionary if provided
    base_dictionary = set()
    if base_dict_file:
        logging.info(f"[Analyzer] Loading base dictionary from {base_dict_file}")
        try:
            with open(base_dict_file, 'r', encoding='utf-8', errors='ignore') as f:
                base_dictionary = set(line.strip().lower() for line in f if line.strip())
            logging.info(f"[Analyzer] Loaded {len(base_dictionary)} base words")
        except Exception as e:
            logging.warning(f"[Analyzer] Could not load base dictionary: {e}")
    
    # Analyze wordlist (streaming or full)
    passwords = []
    
    if streaming:
        logging.info(f"[Analyzer] Using streaming mode (chunk size: {chunk_size})")
        
        try:
            with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                chunk = []
                for line in f:
                    pwd = line.strip()
                    if 4 <= len(pwd) <= 40:  # Filter reasonable passwords
                        chunk.append(pwd)
                    
                    if len(chunk) >= chunk_size:
                        # Analyze chunk
                        analyzer.analyze(chunk, base_dictionary if base_dictionary else None)
                        chunk = []
                
                # Process remaining chunk
                if chunk:
                    analyzer.analyze(chunk, base_dictionary if base_dictionary else None)
        
        except Exception as e:
            logging.error(f"[Analyzer] Error analyzing wordlist: {e}")
            return None
    else:
        # Load all at once (for smaller files)
        logging.info("[Analyzer] Loading entire wordlist...")
        try:
            with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                passwords = [line.strip() for line in f 
                           if line.strip() and 4 <= len(line.strip()) <= 40]
            
            logging.info(f"[Analyzer] Loaded {len(passwords)} passwords")
            analysis = analyzer.analyze(passwords, base_dictionary if base_dictionary else None)
        
        except Exception as e:
            logging.error(f"[Analyzer] Error analyzing wordlist: {e}")
            return None
    
    # Compile results
    analysis = analyzer._compile_results()
    
    # Generate optimal rules
    rules = analyzer.generate_optimal_rules(analysis, max_rules)
    
    # Write rules to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for rule, freq in rules:
                # Write rule with frequency as comment
                f.write(f"{rule}\n")
        
        logging.info(f"[Analyzer] Wrote {len(rules)} rules to {output_file}")
        
        # Also write analysis report
        report_file = output_file.replace('.rule', '_analysis.txt')
        _write_analysis_report(analysis, rules, report_file)
        
    except Exception as e:
        logging.error(f"[Analyzer] Error writing rules: {e}")
        return None
    
    return {
        'analysis': analysis,
        'rules': rules,
        'rules_file': output_file,
        'report_file': report_file
    }


def _write_analysis_report(analysis, rules, report_file):
    """Write human-readable analysis report."""
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("WORDLIST ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Total passwords analyzed: {analysis['total_passwords']:,}\n\n")
            
            # Length distribution
            f.write("LENGTH DISTRIBUTION\n")
            f.write("-"*70 + "\n")
            for length, count in sorted(analysis['length_distribution'].items())[:15]:
                pct = (count / analysis['total_passwords']) * 100
                f.write(f"  {length:2d} characters: {count:6,} ({pct:5.2f}%)\n")
            f.write("\n")
            
            # Charset usage
            f.write("CHARSET USAGE\n")
            f.write("-"*70 + "\n")
            for charset, count in analysis['charset_usage'].items():
                pct = (count / analysis['total_passwords']) * 100
                f.write(f"  {charset:12s}: {count:6,} ({pct:5.2f}%)\n")
            f.write("\n")
            
            # Top suffixes
            f.write("TOP 20 SUFFIXES\n")
            f.write("-"*70 + "\n")
            for suffix, count in analysis['top_suffixes'][:20]:
                pct = (count / analysis['total_passwords']) * 100
                f.write(f"  '{suffix:10s}': {count:6,} ({pct:5.2f}%)\n")
            f.write("\n")
            
            # Case patterns
            f.write("CASE PATTERNS\n")
            f.write("-"*70 + "\n")
            for pattern, count in analysis['case_patterns'].items():
                pct = (count / analysis['total_passwords']) * 100
                f.write(f"  {pattern:15s}: {count:6,} ({pct:5.2f}%)\n")
            f.write("\n")
            
            # Top rules
            f.write("TOP 20 GENERATED RULES (by frequency)\n")
            f.write("-"*70 + "\n")
            for i, (rule, freq) in enumerate(rules[:20], 1):
                f.write(f"  {i:2d}. {rule:30s} (frequency: {freq:.4f})\n")
            f.write("\n")
            
            f.write("="*70 + "\n")
        
        logging.info(f"[Analyzer] Wrote analysis report to {report_file}")
    
    except Exception as e:
        logging.warning(f"[Analyzer] Could not write analysis report: {e}")


# Export main functions
__all__ = [
    'WordlistAnalyzer',
    'analyze_and_generate_rules',
]
