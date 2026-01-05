"""
Output reporting utilities for password mangler.

Generates human-readable reports for various operations including
generation statistics, filtering results, and pattern analysis.
"""

import logging
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any


def write_generation_stats(output_file: str, stats: Dict[str, Any]):
    """
    Write generation statistics report.
    
    Args:
        output_file: Path to output statistics file
        stats: Dictionary containing generation statistics
    """
    try:
        report_file = output_file.replace('.txt', '_stats.txt')
        if report_file == output_file:
            report_file = output_file + '_stats.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("PASSWORD GENERATION STATISTICS\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if 'input_file' in stats:
                f.write(f"Input: {stats['input_file']}")
                if 'input_words' in stats:
                    f.write(f" ({stats['input_words']} words)")
                f.write("\n")
            f.write(f"Output: {stats.get('output_file', 'N/A')}\n\n")
            
            # Generation summary
            f.write("GENERATION SUMMARY\n")
            f.write("-"*70 + "\n")
            f.write(f"  Total Generated:      {stats.get('total_generated', 0):,} passwords\n")
            
            if 'unique_count' in stats:
                unique_pct = (stats['unique_count'] * 100.0 / stats['total_generated']) if stats['total_generated'] > 0 else 0
                f.write(f"  Unique Passwords:     {stats['unique_count']:,} ({unique_pct:.2f}%)\n")
                dupe_count = stats['total_generated'] - stats['unique_count']
                dupe_pct = 100.0 - unique_pct
                f.write(f"  Duplicates Removed:   {dupe_count:,} ({dupe_pct:.2f}%)\n")
            
            f.write("\n")
            
            # Length distribution
            if 'length_distribution' in stats:
                f.write("LENGTH DISTRIBUTION\n")
                f.write("-"*70 + "\n")
                length_dist = stats['length_distribution']
                
                if length_dist:
                    lengths = sorted(length_dist.keys())
                    f.write(f"  Min: {min(lengths)} characters\n")
                    f.write(f"  Max: {max(lengths)} characters\n")
                    
                    if 'avg_length' in stats:
                        f.write(f"  Average: {stats['avg_length']:.1f} characters\n")
                    
                    # Most common length
                    most_common_len = max(length_dist.items(), key=lambda x: x[1])
                    f.write(f"  Most Common: {most_common_len[0]} characters ({most_common_len[1]:,} passwords)\n")
                    
                    f.write("\n  Distribution:\n")
                    for length in lengths[:15]:  # Show top 15
                        count = length_dist[length]
                        pct = (count * 100.0 / stats['total_generated']) if stats['total_generated'] > 0 else 0
                        f.write(f"    {length:2d} chars: {count:6,} ({pct:5.2f}%)\n")
                
                f.write("\n")
            
            # Charset analysis
            if 'charset_stats' in stats:
                f.write("CHARSET ANALYSIS\n")
                f.write("-"*70 + "\n")
                charset = stats['charset_stats']
                total = stats['total_generated']
                
                for key, count in charset.items():
                    pct = (count * 100.0 / total) if total > 0 else 0
                    f.write(f"  {key:25s}: {count:6,} ({pct:5.2f}%)\n")
                
                f.write("\n")
            
            # Transformation usage
            if 'transformation_stats' in stats:
                f.write("TRANSFORMATION USAGE\n")
                f.write("-"*70 + "\n")
                trans = stats['transformation_stats']
                total = stats['total_generated']
                
                for key, count in trans.items():
                    pct = (count * 100.0 / total) if total > 0 else 0
                    f.write(f"  {key:25s}: {count:6,} ({pct:5.2f}%)\n")
                
                f.write("\n")
            
            # Processing info
            if 'processing_time' in stats:
                f.write("PROCESSING INFORMATION\n")
                f.write("-"*70 + "\n")
                f.write(f"  Total Time: {stats['processing_time']:.2f} seconds\n")
                
                if 'passwords_per_second' in stats:
                    f.write(f"  Speed: {stats['passwords_per_second']:,.0f} passwords/second\n")
                
                if 'threads_used' in stats:
                    f.write(f"  Threads: {stats['threads_used']}\n")
                
                f.write("\n")
            
            f.write("="*70 + "\n")
        
        logging.info(f"[Report] Wrote generation statistics to {report_file}")
        return report_file
        
    except Exception as e:
        logging.warning(f"[Report] Could not write generation statistics: {e}")
        return None


def write_filter_report(input_file: str, output_file: str, policy, 
                       passed: int, rejected: int, rejection_reasons: Dict[str, int] = None):
    """
    Write policy filtering report.
    
    Args:
        input_file: Input wordlist file
        output_file: Output filtered file
        policy: PasswordPolicy object
        passed: Number of passwords that passed
        rejected: Number of passwords rejected
        rejection_reasons: Optional dict of rejection reasons with counts
    """
    try:
        report_file = output_file.replace('.txt', '_filter_report.txt')
        if report_file == output_file:
            report_file = output_file + '_filter_report.txt'
        
        total = passed + rejected
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("POLICY FILTERING REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input: {input_file} ({total:,} passwords)\n")
            f.write(f"Output: {output_file} ({passed:,} passwords)\n")
            f.write(f"Policy: {str(policy)}\n\n")
            
            # Filtering results
            f.write("FILTERING RESULTS\n")
            f.write("-"*70 + "\n")
            pass_pct = (passed * 100.0 / total) if total > 0 else 0
            reject_pct = (rejected * 100.0 / total) if total > 0 else 0
            f.write(f"  Passed:    {passed:,} passwords ({pass_pct:.2f}%)\n")
            f.write(f"  Rejected:  {rejected:,} passwords ({reject_pct:.2f}%)\n\n")
            
            # Rejection reasons
            if rejection_reasons:
                f.write("REJECTION REASONS\n")
                f.write("-"*70 + "\n")
                sorted_reasons = sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)
                for reason, count in sorted_reasons:
                    reason_pct = (count * 100.0 / rejected) if rejected > 0 else 0
                    f.write(f"  {reason:30s}: {count:6,} ({reason_pct:5.2f}%)\n")
                f.write("\n")
            
            # Policy details
            f.write("POLICY REQUIREMENTS\n")
            f.write("-"*70 + "\n")
            f.write(f"  Length: {policy.min_length}-{policy.max_length} characters\n")
            
            if policy.require_lowercase or policy.min_lowercase > 0:
                f.write(f"  Lowercase: Required (min {max(1 if policy.require_lowercase else 0, policy.min_lowercase)})\n")
            if policy.require_uppercase or policy.min_uppercase > 0:
                f.write(f"  Uppercase: Required (min {max(1 if policy.require_uppercase else 0, policy.min_uppercase)})\n")
            if policy.require_digit or policy.min_digits > 0:
                f.write(f"  Digits: Required (min {max(1 if policy.require_digit else 0, policy.min_digits)})\n")
            if policy.require_special or policy.min_special > 0:
                f.write(f"  Special: Required (min {max(1 if policy.require_special else 0, policy.min_special)})\n")
            
            if policy.blacklist_words:
                f.write(f"  Blacklisted words: {len(policy.blacklist_words)}\n")
            
            if policy.blacklist_patterns:
                f.write(f"  Blacklist patterns: {len(policy.blacklist_patterns)}\n")
            
            if not policy.allow_repeating:
                f.write(f"  No repeating characters allowed\n")
            elif policy.max_consecutive:
                f.write(f"  Max consecutive: {policy.max_consecutive}\n")
            
            f.write("\n")
            f.write("="*70 + "\n")
        
        logging.info(f"[Report] Wrote filter report to {report_file}")
        return report_file
        
    except Exception as e:
        logging.warning(f"[Report] Could not write filter report: {e}")
        return None


def analyze_passwords_for_stats(passwords: List[str]) -> Dict[str, Any]:
    """
    Analyze a list of passwords and generate statistics.
    
    Args:
        passwords: List of passwords to analyze
    
    Returns:
        Dictionary of statistics
    """
    if not passwords:
        return {}
    
    stats = {
        'total_generated': len(passwords),
        'unique_count': len(set(passwords)),
    }
    
    # Length distribution
    length_dist = Counter(len(pwd) for pwd in passwords)
    stats['length_distribution'] = dict(length_dist)
    stats['avg_length'] = sum(len(pwd) for pwd in passwords) / len(passwords)
    
    # Charset analysis
    charset_stats = {
        'Lowercase only': 0,
        'Uppercase only': 0,
        'Mixed case': 0,
        'Alphanumeric': 0,
        'With digits': 0,
        'With special characters': 0,
    }
    
    for pwd in passwords:
        has_lower = any(c.islower() for c in pwd)
        has_upper = any(c.isupper() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_special = any(not c.isalnum() for c in pwd)
        
        if has_lower and not has_upper and not has_digit and not has_special:
            charset_stats['Lowercase only'] += 1
        if has_upper and not has_lower and not has_digit and not has_special:
            charset_stats['Uppercase only'] += 1
        if has_lower and has_upper:
            charset_stats['Mixed case'] += 1
        if (has_lower or has_upper) and has_digit:
            charset_stats['Alphanumeric'] += 1
        if has_digit:
            charset_stats['With digits'] += 1
        if has_special:
            charset_stats['With special characters'] += 1
    
    stats['charset_stats'] = charset_stats
    
    return stats


# Export main functions
__all__ = [
    'write_generation_stats',
    'write_filter_report',
    'analyze_passwords_for_stats',
]
