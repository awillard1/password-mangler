#!/usr/bin/env python3
"""
Comprehensive test suite for password-mangler functionality verification.
Tests all critical features and modules.
"""

import os
import sys
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_mask_attack():
    """Test mask attack module."""
    print("\n" + "="*70)
    print("TEST 1: Mask Attack Module")
    print("="*70)
    
    try:
        import mangler_mask
        
        # Test 1: Basic mask generation
        print("  [1.1] Basic mask generation (?l?l?d?d)")
        passwords = list(mangler_mask.generate_from_mask('?l?l?d?d', max_passwords=20))
        assert len(passwords) == 20, f"Expected 20 passwords, got {len(passwords)}"
        assert all(len(p) == 4 for p in passwords), "All passwords should be length 4"
        print(f"     ✅ Generated {len(passwords)} passwords")
        print(f"     Examples: {passwords[:5]}")
        
        # Test 2: Estimate mask size
        print("  [1.2] Mask size estimation")
        size = mangler_mask.estimate_mask_size('?l?l?l?d?d?d')
        assert size == 26*26*26*10*10*10, f"Expected 17,576,000, got {size:,}"
        print(f"     ✅ Estimated size: {size:,} passwords")
        
        # Test 3: Custom charsets
        print("  [1.3] Custom charsets")
        passwords = list(mangler_mask.generate_from_mask(
            '?1?1?d',
            custom_charsets={'1': 'abc'},
            max_passwords=18
        ))
        assert len(passwords) == 18, f"Expected 18, got {len(passwords)}"
        print(f"     ✅ Generated {len(passwords)} with custom charset")
        print(f"     Examples: {passwords[:5]}")
        
        print("  ✅ Mask Attack Module: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Mask Attack Module: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_policy_filtering():
    """Test policy filtering module."""
    print("\n" + "="*70)
    print("TEST 2: Policy Filtering Module")
    print("="*70)
    
    try:
        import mangler_policy
        
        # Test 1: Basic policy
        print("  [2.1] Basic length policy")
        policy = mangler_policy.PasswordPolicy(min_length=8)
        test_passwords = ['pass', 'password', 'admin', 'administrator']
        passed = mangler_policy.filter_by_policy(test_passwords, policy)
        assert len(passed) == 2, f"Expected 2 to pass, got {len(passed)}"
        print(f"     ✅ Filtered {len(test_passwords)} → {len(passed)} passed")
        
        # Test 2: Complex policy
        print("  [2.2] Complex policy (length + digit + special)")
        policy = mangler_policy.PasswordPolicy(
            min_length=8,
            require_digit=True,
            require_special=True
        )
        test_passwords = ['password', 'password1', 'Password!', 'Password1!', 'Admin123!']
        passed = mangler_policy.filter_by_policy(test_passwords, policy)
        assert 'Password1!' in passed and 'Admin123!' in passed
        print(f"     ✅ Complex policy: {len(passed)}/{len(test_passwords)} passed")
        print(f"     Passed: {passed}")
        
        # Test 3: Preset policies
        print("  [2.3] Preset policies")
        policy = mangler_policy.get_preset_policy('enterprise')
        test_passwords = ['password', 'Password1', 'Password1!', 'SecurePass123!']
        passed = mangler_policy.filter_by_policy(test_passwords, policy)
        print(f"     ✅ Enterprise policy: {len(passed)}/{len(test_passwords)} passed")
        
        print("  ✅ Policy Filtering Module: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Policy Filtering Module: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_wordlist_analyzer():
    """Test wordlist analyzer module."""
    print("\n" + "="*70)
    print("TEST 3: Wordlist Analyzer Module")
    print("="*70)
    
    try:
        import mangler_analyzer
        
        # Test 1: Basic analysis
        print("  [3.1] Basic wordlist analysis")
        analyzer = mangler_analyzer.WordlistAnalyzer()
        test_passwords = [
            'password123', 'admin2024', 'test!', 'P@ssw0rd',
            'Welcome1', 'Admin!', 'user2024', 'Password123!'
        ]
        result = analyzer.analyze(test_passwords)
        assert result['total_passwords'] == len(test_passwords)
        print(f"     ✅ Analyzed {result['total_passwords']} passwords")
        print(f"     Found {len(result.get('top_suffixes', []))} unique suffixes")
        
        # Test 2: Rule generation
        print("  [3.2] Hashcat rule generation")
        result = analyzer.analyze(test_passwords)
        rules = analyzer.generate_optimal_rules(result, max_rules=20)
        assert len(rules) > 0, "Should generate at least some rules"
        print(f"     ✅ Generated {len(rules)} Hashcat rules")
        print(f"     Examples: {rules[:5]}")
        
        print("  ✅ Wordlist Analyzer Module: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Wordlist Analyzer Module: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_rule_optimizer():
    """Test rule optimizer module."""
    print("\n" + "="*70)
    print("TEST 4: Rule Optimizer Module")
    print("="*70)
    
    try:
        import mangler_rule_optimizer
        
        # Test 1: Basic optimization
        print("  [4.1] Rule deduplication")
        test_rules = [':', 'c', 'l', 'u', '$1$2$3', ':$1$2$3', 'c$!', 'l$!']
        optimized, stats = mangler_rule_optimizer.optimize_rules(test_rules, verbose=False)
        assert stats['optimized_count'] < stats['original_count']
        print(f"     ✅ Optimized {stats['original_count']} → {stats['optimized_count']} rules")
        print(f"     Reduction: {stats['reduction_percent']}%")
        
        # Test 2: Rule application
        print("  [4.2] Rule application test")
        word = "password"
        rule = "c$1$2$3"
        result = mangler_rule_optimizer.apply_simple_rule(word, rule)
        assert result == "Password123", f"Expected 'Password123', got '{result}'"
        print(f"     ✅ Rule '{rule}' on '{word}' → '{result}'")
        
        print("  ✅ Rule Optimizer Module: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Rule Optimizer Module: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ml_query():
    """Test ML query and comparison module."""
    print("\n" + "="*70)
    print("TEST 5: ML Query & Comparison Module")
    print("="*70)
    
    try:
        import mangler_ml_query
        
        # Create mock patterns for testing
        patterns1 = {
            'source_file': 'test1.txt',
            'appends': {'123': 100, '456': 50, 'abc': 30},
            'prepends': {'the': 20, 'my': 10},
            'leet': {'a->@': 40, 'e->3': 35}
        }
        
        patterns2 = {
            'source_file': 'test2.txt',
            'appends': {'123': 80, '789': 60, 'xyz': 25},
            'prepends': {'the': 15, 'our': 12},
            'leet': {'a->@': 30, 'o->0': 28}
        }
        
        # Test 1: Pattern comparison
        print("  [5.1] Pattern comparison")
        comparison = mangler_ml_query.compare_ml_patterns(patterns1, patterns2)
        assert 'stats' in comparison
        assert comparison['stats']['total_common'] > 0
        print(f"     ✅ Similarity: {comparison['stats']['similarity_score']:.2%}")
        print(f"     Common: {comparison['stats']['total_common']}")
        print(f"     Unique to 1: {comparison['stats']['total_unique_to_1']}")
        print(f"     Unique to 2: {comparison['stats']['total_unique_to_2']}")
        
        # Test 2: Pattern intersection
        print("  [5.2] Pattern intersection")
        intersection = mangler_ml_query.find_pattern_intersections([patterns1, patterns2])
        common_count = sum(len(v) for v in intersection['common_patterns'].values())
        print(f"     ✅ Common patterns across both: {common_count}")
        
        # Test 3: Pattern merging
        print("  [5.3] Pattern merging")
        merged = mangler_ml_query.merge_ml_patterns([patterns1, patterns2])
        assert len(merged['appends']) >= len(patterns1['appends'])
        print(f"     ✅ Merged: {len(merged['appends'])} appends, {len(merged['prepends'])} prepends")
        
        print("  ✅ ML Query & Comparison Module: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ ML Query & Comparison Module: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ml_reports():
    """Test ML reports module."""
    print("\n" + "="*70)
    print("TEST 6: ML Reports Module")
    print("="*70)
    
    try:
        import mangler_reports
        
        # Test 1: Generation statistics
        print("  [6.1] Generation statistics report")
        stats = {
            'total_generated': 10000,
            'unique_generated': 9500,
            'processing_time': 5.2,
            'input_words': 100
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            report_file = f.name
        
        mangler_reports.write_generation_stats(stats, report_file)
        assert os.path.exists(report_file)
        print(f"     ✅ Generated statistics report")
        os.unlink(report_file)
        
        print("  ✅ ML Reports Module: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ ML Reports Module: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_cli_tools():
    """Test CLI tools."""
    print("\n" + "="*70)
    print("TEST 7: CLI Tools")
    print("="*70)
    
    try:
        import subprocess
        
        # Test 1: ml_query.py help
        print("  [7.1] ml_query.py --help")
        result = subprocess.run(
            [sys.executable, 'ml_query.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0
        assert '--compare' in result.stdout
        assert '--intersect' in result.stdout
        print(f"     ✅ ml_query.py CLI functional")
        
        # Test 2: mangler.py help
        print("  [7.2] mangler.py --help")
        result = subprocess.run(
            [sys.executable, 'mangler.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0
        assert '--optimize-rules' in result.stdout
        print(f"     ✅ mangler.py CLI functional with rule optimization")
        
        print("  ✅ CLI Tools: PASSED\n")
        return True
        
    except Exception as e:
        print(f"  ❌ CLI Tools: FAILED - {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("PASSWORD MANGLER - COMPREHENSIVE FUNCTIONALITY VERIFICATION")
    print("="*70)
    
    os.chdir('/home/runner/work/password-mangler/password-mangler')
    
    results = []
    
    results.append(('Mask Attack', test_mask_attack()))
    results.append(('Policy Filtering', test_policy_filtering()))
    results.append(('Wordlist Analyzer', test_wordlist_analyzer()))
    results.append(('Rule Optimizer', test_rule_optimizer()))
    results.append(('ML Query & Comparison', test_ml_query()))
    results.append(('ML Reports', test_ml_reports()))
    results.append(('CLI Tools', test_cli_tools()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name:30s} {status}")
    
    print("=" * 70)
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Codebase is fully functional.\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
