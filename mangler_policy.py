"""
Policy-based password filtering.

Filter generated passwords based on password policy requirements like
minimum/maximum length, required character types, and blacklist patterns.
"""

import logging
import re
from typing import List, Set, Callable, Generator


class PasswordPolicy:
    """
    Password policy configuration for filtering.
    """
    
    def __init__(self,
                 min_length: int = 0,
                 max_length: int = 128,
                 require_lowercase: bool = False,
                 require_uppercase: bool = False,
                 require_digit: bool = False,
                 require_special: bool = False,
                 min_lowercase: int = 0,
                 min_uppercase: int = 0,
                 min_digits: int = 0,
                 min_special: int = 0,
                 blacklist_patterns: List[str] = None,
                 blacklist_words: List[str] = None,
                 allow_repeating: bool = True,
                 max_consecutive: int = None):
        """
        Initialize password policy.
        
        Args:
            min_length: Minimum password length
            max_length: Maximum password length
            require_lowercase: Must contain at least one lowercase letter
            require_uppercase: Must contain at least one uppercase letter
            require_digit: Must contain at least one digit
            require_special: Must contain at least one special character
            min_lowercase: Minimum number of lowercase letters
            min_uppercase: Minimum number of uppercase letters
            min_digits: Minimum number of digits
            min_special: Minimum number of special characters
            blacklist_patterns: List of regex patterns to reject
            blacklist_words: List of words that cannot appear in password
            allow_repeating: Allow repeating characters
            max_consecutive: Maximum consecutive identical characters
        """
        self.min_length = min_length
        self.max_length = max_length
        self.require_lowercase = require_lowercase
        self.require_uppercase = require_uppercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.min_lowercase = min_lowercase
        self.min_uppercase = min_uppercase
        self.min_digits = min_digits
        self.min_special = min_special
        self.blacklist_patterns = [re.compile(p, re.IGNORECASE) 
                                  for p in (blacklist_patterns or [])]
        self.blacklist_words = set(w.lower() for w in (blacklist_words or []))
        self.allow_repeating = allow_repeating
        self.max_consecutive = max_consecutive
        
        # Special characters definition
        self.special_chars = set('!@#$%^&*()-_=+[]{}|;:,.<>?/\\`~"\' ')
    
    def validate(self, password: str) -> bool:
        """
        Check if password meets policy requirements.
        
        Args:
            password: Password to validate
        
        Returns:
            True if password meets all policy requirements
        """
        # Length check
        if len(password) < self.min_length or len(password) > self.max_length:
            return False
        
        # Count character types
        lowercase_count = sum(1 for c in password if c.islower())
        uppercase_count = sum(1 for c in password if c.isupper())
        digit_count = sum(1 for c in password if c.isdigit())
        special_count = sum(1 for c in password if c in self.special_chars)
        
        # Require checks (at least one)
        if self.require_lowercase and lowercase_count == 0:
            return False
        if self.require_uppercase and uppercase_count == 0:
            return False
        if self.require_digit and digit_count == 0:
            return False
        if self.require_special and special_count == 0:
            return False
        
        # Minimum count checks
        if lowercase_count < self.min_lowercase:
            return False
        if uppercase_count < self.min_uppercase:
            return False
        if digit_count < self.min_digits:
            return False
        if special_count < self.min_special:
            return False
        
        # Blacklist pattern checks
        for pattern in self.blacklist_patterns:
            if pattern.search(password):
                return False
        
        # Blacklist word checks
        password_lower = password.lower()
        for word in self.blacklist_words:
            if word in password_lower:
                return False
        
        # Repeating character checks
        if not self.allow_repeating:
            for i in range(len(password) - 1):
                if password[i] == password[i + 1]:
                    return False
        
        # Max consecutive check
        if self.max_consecutive:
            count = 1
            for i in range(1, len(password)):
                if password[i] == password[i - 1]:
                    count += 1
                    if count > self.max_consecutive:
                        return False
                else:
                    count = 1
        
        return True
    
    def __str__(self) -> str:
        """String representation of policy."""
        parts = []
        parts.append(f"Length: {self.min_length}-{self.max_length}")
        
        reqs = []
        if self.require_lowercase or self.min_lowercase > 0:
            reqs.append(f"lowercase>={max(1 if self.require_lowercase else 0, self.min_lowercase)}")
        if self.require_uppercase or self.min_uppercase > 0:
            reqs.append(f"uppercase>={max(1 if self.require_uppercase else 0, self.min_uppercase)}")
        if self.require_digit or self.min_digits > 0:
            reqs.append(f"digits>={max(1 if self.require_digit else 0, self.min_digits)}")
        if self.require_special or self.min_special > 0:
            reqs.append(f"special>={max(1 if self.require_special else 0, self.min_special)}")
        
        if reqs:
            parts.append(f"Require: {', '.join(reqs)}")
        
        if self.blacklist_words:
            parts.append(f"Blacklist: {len(self.blacklist_words)} words")
        
        if self.blacklist_patterns:
            parts.append(f"Patterns: {len(self.blacklist_patterns)} regex")
        
        if not self.allow_repeating:
            parts.append("No repeating chars")
        elif self.max_consecutive:
            parts.append(f"Max consecutive: {self.max_consecutive}")
        
        return " | ".join(parts)


def filter_by_policy(passwords: List[str], policy: PasswordPolicy) -> List[str]:
    """
    Filter password list by policy.
    
    Args:
        passwords: List of passwords to filter
        policy: Password policy to apply
    
    Returns:
        Filtered list of passwords meeting policy
    """
    logging.info(f"[Policy] Filtering {len(passwords)} passwords")
    logging.info(f"[Policy] Policy: {policy}")
    
    filtered = [pwd for pwd in passwords if policy.validate(pwd)]
    
    logging.info(f"[Policy] Passed: {len(filtered)} ({len(filtered)*100/len(passwords):.1f}%)")
    
    return filtered


def filter_generator(password_generator: Generator[str, None, None], 
                    policy: PasswordPolicy) -> Generator[str, None, None]:
    """
    Filter password generator by policy (memory-efficient).
    
    Args:
        password_generator: Generator yielding passwords
        policy: Password policy to apply
    
    Yields:
        Passwords that meet policy requirements
    """
    logging.info(f"[Policy] Filtering with policy: {policy}")
    
    passed = 0
    total = 0
    
    for password in password_generator:
        total += 1
        if policy.validate(password):
            passed += 1
            yield password
        
        # Progress logging
        if total % 100000 == 0:
            pass_rate = (passed * 100 / total) if total > 0 else 0
            logging.info(f"[Policy] Processed {total:,} | Passed {passed:,} ({pass_rate:.1f}%)")


def create_common_policy(policy_type: str) -> PasswordPolicy:
    """
    Create common password policies.
    
    Args:
        policy_type: Type of policy - 'basic', 'moderate', 'strong', 'enterprise'
    
    Returns:
        PasswordPolicy instance
    """
    if policy_type == 'basic':
        return PasswordPolicy(
            min_length=6,
            max_length=128
        )
    
    elif policy_type == 'moderate':
        return PasswordPolicy(
            min_length=8,
            max_length=128,
            require_lowercase=True,
            require_uppercase=True,
            require_digit=True
        )
    
    elif policy_type == 'strong':
        return PasswordPolicy(
            min_length=12,
            max_length=128,
            require_lowercase=True,
            require_uppercase=True,
            require_digit=True,
            require_special=True,
            blacklist_words=['password', 'admin', 'user', 'test']
        )
    
    elif policy_type == 'enterprise':
        return PasswordPolicy(
            min_length=14,
            max_length=128,
            min_lowercase=1,
            min_uppercase=1,
            min_digits=1,
            min_special=1,
            blacklist_words=['password', 'admin', 'user', 'test', 'guest', 
                           'root', 'administrator'],
            max_consecutive=3
        )
    
    else:
        raise ValueError(f"Unknown policy type: {policy_type}")


# Alias for backward compatibility and clearer naming
get_preset_policy = create_common_policy


def filter_file_by_policy(input_file: str, output_file: str, 
                         policy: PasswordPolicy) -> int:
    """
    Filter password file by policy.
    
    Args:
        input_file: Input password file
        output_file: Output file for filtered passwords
        policy: Password policy to apply
    
    Returns:
        Number of passwords that passed filter
    """
    logging.info(f"[Policy] Filtering file: {input_file}")
    logging.info(f"[Policy] Output: {output_file}")
    logging.info(f"[Policy] Policy: {policy}")
    
    passed = 0
    total = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as inf:
            with open(output_file, 'w', encoding='utf-8') as outf:
                for line in inf:
                    password = line.strip()
                    total += 1
                    
                    if policy.validate(password):
                        outf.write(password + '\n')
                        passed += 1
                    
                    # Progress logging
                    if total % 100000 == 0:
                        pass_rate = (passed * 100 / total) if total > 0 else 0
                        logging.info(f"[Policy] Processed {total:,} | Passed {passed:,} ({pass_rate:.1f}%)")
        
        pass_rate = (passed * 100 / total) if total > 0 else 0
        logging.info(f"[Policy] Complete: {passed:,} / {total:,} passed ({pass_rate:.1f}%)")
        
        return passed
    
    except Exception as e:
        logging.error(f"[Policy] Error filtering file: {e}")
        return 0


# Export main functions
__all__ = [
    'PasswordPolicy',
    'filter_by_policy',
    'filter_generator',
    'filter_file_by_policy',
    'create_common_policy',
]
