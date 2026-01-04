"""
Mask attack support for password generation.

Implements Hashcat-style mask attack patterns for structured password generation.
Supports custom charsets and efficient generation of large mask spaces.
"""

import logging
import itertools
from typing import List, Dict, Generator


# Default charset definitions (Hashcat-compatible)
DEFAULT_CHARSETS = {
    'l': 'abcdefghijklmnopqrstuvwxyz',  # lowercase
    'u': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',  # uppercase
    'd': '0123456789',  # digits
    's': '!@#$%^&*()-_=+[]{}|;:,.<>?/\\`~"\' ',  # special characters
    'a': None,  # all printable (will be computed)
    'h': '0123456789abcdef',  # hexadecimal lowercase
    'H': '0123456789ABCDEF',  # hexadecimal uppercase
    'b': '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',  # binary
}


def _get_charset(charset_code: str, custom_charsets: Dict[str, str] = None) -> str:
    """
    Get character set for a given charset code.
    
    Args:
        charset_code: Single character charset code (l, u, d, s, a, h, H, or custom 1-4)
        custom_charsets: Optional custom charset definitions {1: 'abc', 2: 'xyz', ...}
    
    Returns:
        String containing all characters in the charset
    """
    # Check custom charsets first (1-4)
    if custom_charsets and charset_code in custom_charsets:
        return custom_charsets[charset_code]
    
    # Check default charsets
    if charset_code in DEFAULT_CHARSETS:
        charset = DEFAULT_CHARSETS[charset_code]
        
        # Compute 'all' charset on demand
        if charset_code == 'a' and charset is None:
            charset = DEFAULT_CHARSETS['l'] + DEFAULT_CHARSETS['u'] + \
                     DEFAULT_CHARSETS['d'] + DEFAULT_CHARSETS['s']
            DEFAULT_CHARSETS['a'] = charset
        
        return charset
    
    raise ValueError(f"Unknown charset code: {charset_code}")


def parse_mask(mask: str, custom_charsets: Dict[str, str] = None) -> List:
    """
    Parse mask string into list of (type, value) tuples.
    
    Args:
        mask: Mask string (e.g., "?l?l?l?d?d?d")
        custom_charsets: Optional custom charset definitions
    
    Returns:
        List of (type, charset) tuples where type is 'static' or 'dynamic'
    
    Examples:
        parse_mask("?l?l?d?d") → [('dynamic', 'abc...z'), ('dynamic', 'abc...z'), 
                                   ('dynamic', '012...9'), ('dynamic', '012...9')]
        parse_mask("test?d?d") → [('static', 't'), ('static', 'e'), ('static', 's'), 
                                   ('static', 't'), ('dynamic', '012...9'), ('dynamic', '012...9')]
    """
    result = []
    i = 0
    
    while i < len(mask):
        if mask[i] == '?':
            # Charset placeholder
            if i + 1 >= len(mask):
                raise ValueError(f"Invalid mask: '?' at end of mask")
            
            charset_code = mask[i + 1]
            charset = _get_charset(charset_code, custom_charsets)
            result.append(('dynamic', charset))
            i += 2
        else:
            # Static character
            result.append(('static', mask[i]))
            i += 1
    
    return result


def estimate_mask_size(mask: str, custom_charsets: Dict[str, str] = None) -> int:
    """
    Estimate total number of passwords that will be generated from mask.
    
    Args:
        mask: Mask string
        custom_charsets: Optional custom charset definitions
    
    Returns:
        Total number of possible passwords
    """
    parsed = parse_mask(mask, custom_charsets)
    size = 1
    
    for typ, value in parsed:
        if typ == 'dynamic':
            size *= len(value)
    
    return size


def generate_from_mask(mask: str, custom_charsets: Dict[str, str] = None, 
                       max_passwords: int = None) -> Generator[str, None, None]:
    """
    Generate passwords from mask pattern.
    
    Args:
        mask: Mask string (e.g., "?l?l?l?d?d?d" or "password?d?d")
        custom_charsets: Optional custom charset definitions {1: 'abc', 2: 'xyz', ...}
        max_passwords: Optional limit on number of passwords to generate
    
    Yields:
        Generated passwords matching the mask
    
    Examples:
        generate_from_mask("?l?d") → "a0", "a1", ..., "z9"
        generate_from_mask("test?d?d") → "test00", "test01", ..., "test99"
    """
    logging.info(f"[Mask] Generating from mask: {mask}")
    
    # Parse mask
    parsed = parse_mask(mask, custom_charsets)
    
    # Estimate size
    total_size = estimate_mask_size(mask, custom_charsets)
    logging.info(f"[Mask] Estimated passwords: {total_size:,}")
    
    # Extract dynamic positions and their charsets
    dynamic_positions = []
    static_chars = []
    
    for i, (typ, value) in enumerate(parsed):
        if typ == 'dynamic':
            dynamic_positions.append((i, value))
            static_chars.append(None)  # Placeholder
        else:
            static_chars.append(value)
    
    # Generate all combinations
    if not dynamic_positions:
        # No dynamic positions, just return static string
        yield ''.join(static_chars)
        return
    
    # Extract charsets for dynamic positions
    charsets = [charset for _, charset in dynamic_positions]
    
    # Generate cartesian product
    count = 0
    for combination in itertools.product(*charsets):
        # Build password by inserting dynamic characters
        password = static_chars.copy()
        for (pos, _), char in zip(dynamic_positions, combination):
            password[pos] = char
        
        yield ''.join(password)
        
        count += 1
        if max_passwords and count >= max_passwords:
            logging.info(f"[Mask] Reached max limit of {max_passwords:,} passwords")
            break
        
        # Progress logging
        if count % 1000000 == 0:
            logging.info(f"[Mask] Generated {count:,} / {total_size:,} passwords...")


def generate_mask_file(mask: str, output_file: str, custom_charsets: Dict[str, str] = None,
                      max_passwords: int = None) -> int:
    """
    Generate passwords from mask and write to file.
    
    Args:
        mask: Mask string
        output_file: Output file path
        custom_charsets: Optional custom charset definitions
        max_passwords: Optional limit on passwords to generate
    
    Returns:
        Number of passwords generated
    """
    logging.info(f"[Mask] Writing to file: {output_file}")
    
    count = 0
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for password in generate_from_mask(mask, custom_charsets, max_passwords):
                f.write(password + '\n')
                count += 1
        
        logging.info(f"[Mask] Generated {count:,} passwords")
        return count
    
    except Exception as e:
        logging.error(f"[Mask] Error generating passwords: {e}")
        return 0


def generate_hybrid_mask(base_words: List[str], mask: str, 
                        custom_charsets: Dict[str, str] = None,
                        position: str = 'append') -> Generator[str, None, None]:
    """
    Generate hybrid attack combining base words with mask patterns.
    
    Args:
        base_words: List of base words
        mask: Mask to apply to each word
        custom_charsets: Optional custom charset definitions
        position: Where to apply mask - 'append' or 'prepend'
    
    Yields:
        Generated passwords (base_word + mask_pattern or mask_pattern + base_word)
    
    Examples:
        generate_hybrid_mask(["admin"], "?d?d?d", position='append') 
            → "admin000", "admin001", ..., "admin999"
    """
    logging.info(f"[Mask] Hybrid attack: {len(base_words)} words × mask '{mask}'")
    
    for base_word in base_words:
        for mask_part in generate_from_mask(mask, custom_charsets):
            if position == 'append':
                yield base_word + mask_part
            elif position == 'prepend':
                yield mask_part + base_word
            else:
                raise ValueError(f"Invalid position: {position}")


def validate_mask(mask: str, custom_charsets: Dict[str, str] = None) -> bool:
    """
    Validate mask syntax.
    
    Args:
        mask: Mask string to validate
        custom_charsets: Optional custom charset definitions
    
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_mask(mask, custom_charsets)
        return True
    except Exception as e:
        logging.error(f"[Mask] Invalid mask '{mask}': {e}")
        return False


# Common mask patterns for reference
COMMON_MASKS = {
    'simple_4digit': '?d?d?d?d',
    'simple_6digit': '?d?d?d?d?d?d',
    'lower_4digit': '?l?l?l?l?d?d?d?d',
    'lower_2digit': '?l?l?l?l?l?l?d?d',
    'cap_lower_4digit': '?u?l?l?l?l?d?d?d?d',
    'cap_lower_2digit_special': '?u?l?l?l?l?d?d?s',
    'all_8': '?a?a?a?a?a?a?a?a',
    'hex_8': '?h?h?h?h?h?h?h?h',
}


def get_common_mask(name: str) -> str:
    """Get a common mask pattern by name."""
    return COMMON_MASKS.get(name, '')


def list_common_masks() -> Dict[str, str]:
    """List all common mask patterns."""
    return COMMON_MASKS.copy()


# Export main functions
__all__ = [
    'generate_from_mask',
    'generate_mask_file',
    'generate_hybrid_mask',
    'estimate_mask_size',
    'validate_mask',
    'parse_mask',
    'get_common_mask',
    'list_common_masks',
    'DEFAULT_CHARSETS',
    'COMMON_MASKS',
]
