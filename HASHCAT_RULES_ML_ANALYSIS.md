# Hashcat Rules Generation - ML Approach Analysis

## Understanding the Real Problem

**The True Purpose**: Given a large corpus of leaked passwords, learn the **transformation patterns** people actually use, then generate Hashcat rules that can apply those transformations to crack passwords.

### Example Workflow

```
Input: Leaked passwords like:
- password123
- P@ssw0rd!
- admin2024
- Welcome1

Goal: Learn what transformations were applied to base words
- "password" → "password123" = append "123"
- "password" → "P@ssw0rd!" = capitalize + leet(a→@,o→0) + append "!"
- "admin" → "admin2024" = append "2024"
- "welcome" → "Welcome1" = capitalize + append "1"

Output: Hashcat rules that recreate these transformations
- $1$2$3         (append 123)
- cs@so0$!       (capitalize + substitute a→@, o→0 + append !)
- $2$0$2$4       (append 2024)
- c$1            (capitalize + append 1)
```

## Current Problems

### 1. Missing: Base Word Extraction
The current code doesn't identify what the "base word" was before transformation.

**Example**:
- Password: "password123"
- Base: "password"
- Transformation: append "123"
- Rule: `$1$2$3`

**Challenge**: How do we know "password" was the base and not "password12" or "passwor"?

### 2. Missing: Transformation Inference
The code counts suffixes but doesn't learn the actual transformation sequence.

**Example**:
- From: "password" 
- To: "P@ssw0rd!"
- Transformations: 
  1. Capitalize first letter
  2. Substitute a→@
  3. Substitute o→0
  4. Append !
- Hashcat rule: `csa@so0$!`

### 3. Current Approach is Incomplete
- ✓ Counts suffixes/prefixes (statistical)
- ✗ Doesn't extract base words
- ✗ Doesn't infer transformation sequences
- ✗ Doesn't generate learned rules

## Best Approach for Hashcat Rule Learning

### Option 1: Dictionary-Based Rule Extraction (Recommended)

**Concept**: Use a known dictionary to identify base words, then extract transformations.

**Algorithm**:
```python
def learn_rules_from_leak(passwords, dictionary):
    """
    Learn Hashcat rules by comparing passwords to dictionary words.
    
    Args:
        passwords: List of leaked passwords
        dictionary: List of common words (rockyou, common-passwords, etc.)
    
    Returns:
        List of Hashcat rules ranked by frequency
    """
    rule_counter = Counter()
    
    for password in passwords:
        pwd_lower = password.lower()
        
        # Try to find matching base word
        for base_word in dictionary:
            if base_word in pwd_lower or pwd_lower.startswith(base_word):
                # Extract transformation
                rule = infer_transformation(base_word, password)
                if rule:
                    rule_counter[rule] += 1
                    break
    
    # Return top rules
    return [rule for rule, count in rule_counter.most_common(1000)]
```

**Advantages**:
- Accurate transformation inference
- Works with real-world patterns
- Generates immediately usable Hashcat rules

**Implementation Complexity**: Medium

### Option 2: Edit Distance + Pattern Matching

**Concept**: Use edit distance to find likely base words, then categorize transformations.

**Algorithm**:
```python
from difflib import SequenceMatcher

def find_base_and_transform(password, dictionary):
    """
    Find most likely base word using similarity matching.
    """
    best_match = None
    best_ratio = 0
    
    pwd_lower = password.lower()
    
    for word in dictionary:
        # Quick length filter
        if len(word) > len(password):
            continue
            
        ratio = SequenceMatcher(None, word, pwd_lower).ratio()
        if ratio > best_ratio and ratio > 0.6:
            best_ratio = ratio
            best_match = word
    
    if best_match:
        return best_match, extract_rule(best_match, password)
    return None, None
```

**Advantages**:
- Handles fuzzy matches
- Can discover unknown base words
- More flexible than exact matching

**Disadvantages**:
- Slower (O(n*m) comparisons)
- May miss exact patterns

### Option 3: Reverse Engineering (No Dictionary)

**Concept**: Analyze password structure to guess base vs transformation.

**Heuristics**:
```python
def extract_base_word(password):
    """
    Extract likely base word from password using heuristics.
    
    Rules:
    1. Strip trailing digits (123, 2024, etc.)
    2. Strip trailing special chars (!, @, #)
    3. Strip leading special chars
    4. Remove common leet substitutions
    5. Remaining text is likely base
    """
    pwd = password
    
    # Strip trailing numbers
    pwd = re.sub(r'\d+$', '', pwd)
    
    # Strip trailing special chars
    pwd = re.sub(r'[!@#$%^&*()]+$', '', pwd)
    
    # Strip leading special chars
    pwd = re.sub(r'^[!@#$%^&*()]+', '', pwd)
    
    # Reverse common leet speak
    pwd = pwd.replace('@', 'a').replace('3', 'e').replace('0', 'o')
    pwd = pwd.replace('1', 'i').replace('$', 's').replace('7', 't')
    
    return pwd.lower()
```

**Advantages**:
- No dictionary needed
- Fast
- Works on any password set

**Disadvantages**:
- Less accurate
- May miss complex transformations
- Heuristics can fail

### Option 4: ML Sequence-to-Sequence Model

**Concept**: Train a neural network to learn (base_word → password) mappings.

**Model**: LSTM or Transformer

**Training Data**:
```
Input: "password"  → Output: "Password123!"
Input: "admin"     → Output: "Admin2024"
Input: "welcome"   → Output: "W3lc0m3!"
```

**Advantages**:
- Learns complex patterns automatically
- Can generalize to new words
- State-of-the-art approach

**Disadvantages**:
- Requires large training set with labeled base words
- Slow training (hours/days)
- Doesn't directly output Hashcat rules
- Overkill for this task

## Recommended Implementation

### Hybrid Approach: Dictionary + Heuristics + Statistics

**Phase 1: Dictionary-Based Rule Extraction**
```python
def learn_hashcat_rules(leaked_passwords, dictionary_file):
    """
    Learn Hashcat rules from leaked passwords using dictionary.
    
    Steps:
    1. Load common word dictionary
    2. For each password, find matching base word
    3. Extract transformation as Hashcat rule
    4. Count rule frequencies
    5. Return top N rules
    """
    
    # Load dictionary
    dictionary = load_dictionary(dictionary_file)
    
    # Build rule counter
    rule_counter = Counter()
    matched_count = 0
    
    for password in leaked_passwords:
        # Try to match with dictionary
        base_word, rule = find_best_match(password, dictionary)
        
        if rule:
            rule_counter[rule] += 1
            matched_count += 1
    
    logging.info(f"Matched {matched_count}/{len(leaked_passwords)} passwords")
    logging.info(f"Discovered {len(rule_counter)} unique rules")
    
    # Return top rules by frequency
    top_rules = [rule for rule, count in rule_counter.most_common(10000)]
    return top_rules
```

**Phase 2: Statistical Pattern Extraction**
```python
def extract_statistical_patterns(leaked_passwords):
    """
    Extract rules using statistical analysis (current approach).
    
    Good for:
    - Common appends (123, 2024, !)
    - Common prepends (1, @)
    - Leet substitutions (a→@, e→3)
    """
    # Current implementation is good for this
    append_counter = Counter()
    prepend_counter = Counter()
    
    for pwd in leaked_passwords:
        # Analyze suffixes
        for length in [1, 2, 3, 4]:
            if len(pwd) > length:
                suffix = pwd[-length:]
                if suffix.isdigit() or any(c in suffix for c in "!@#$"):
                    append_counter[suffix] += 1
    
    # Generate rules from statistics
    rules = []
    for suffix, count in append_counter.most_common(100):
        rule = "".join(f"${c}" for c in suffix)
        rules.append(rule)
    
    return rules
```

**Phase 3: Combine and Deduplicate**
```python
def generate_learned_hashcat_rules(leaked_passwords, dictionary_file, output_file):
    """
    Complete pipeline for learning Hashcat rules.
    """
    # Method 1: Dictionary-based (most accurate)
    dict_rules = learn_hashcat_rules(leaked_passwords, dictionary_file)
    
    # Method 2: Statistical (catches patterns without base words)
    stat_rules = extract_statistical_patterns(leaked_passwords)
    
    # Combine and deduplicate
    all_rules = set(dict_rules + stat_rules)
    
    # Write to file
    with open(output_file, 'w') as f:
        for rule in sorted(all_rules):
            f.write(rule + '\n')
    
    return len(all_rules)
```

## Transformation Inference Algorithm

### Converting Password → Hashcat Rule

```python
def infer_transformation(base_word, password):
    """
    Infer Hashcat rule that transforms base_word into password.
    
    Returns Hashcat rule string or None if too complex.
    """
    rule_parts = []
    current = base_word
    
    # Step 1: Case changes
    if password[0].isupper() and base_word[0].islower():
        rule_parts.append('c')  # Capitalize
        current = current.capitalize()
    elif password.isupper():
        rule_parts.append('u')  # Uppercase all
        current = current.upper()
    
    # Step 2: Character substitutions (leet speak)
    for i, (orig_char, pwd_char) in enumerate(zip(current.lower(), password.lower())):
        if orig_char != pwd_char:
            # Check if it's a known leet substitution
            if orig_char == 'a' and pwd_char == '@':
                rule_parts.append('sa@')
            elif orig_char == 'e' and pwd_char == '3':
                rule_parts.append('se3')
            elif orig_char == 'o' and pwd_char == '0':
                rule_parts.append('so0')
            # ... more mappings
    
    # Step 3: Appends
    if len(password) > len(base_word):
        suffix = password[len(base_word):]
        for char in suffix:
            rule_parts.append(f'${char}')
    
    # Step 4: Prepends
    if not password.lower().startswith(base_word.lower()):
        # Find prefix
        # This is more complex, skip for now
        pass
    
    # Combine all parts
    if rule_parts:
        return ''.join(rule_parts)
    return None

# Example:
# base_word = "password"
# password = "P@ssw0rd123!"
# Result: "csa@so0$1$2$3$!"
```

## Performance Comparison

| Approach | Speed | Accuracy | Dictionary Required | Complexity |
|----------|-------|----------|-------------------|------------|
| Current (stats only) | Fast | Low | No | Low |
| Dictionary-based | Medium | High | Yes | Medium |
| Edit distance | Slow | Medium | Yes | Medium |
| Heuristics only | Fast | Medium | No | Low |
| ML Seq2Seq | Very Slow | High | No | Very High |
| **Hybrid (Recommended)** | **Medium** | **High** | **Yes** | **Medium** |

## Implementation Priority

### Immediate (This PR):
1. ✅ Fix memory issues (streaming)
2. ✅ Add caching
3. ✅ Make ML optional
4. ➡️ **Add dictionary-based rule learning**
5. ➡️ **Improve Hashcat rule generation with learned patterns**

### Future Enhancements:
1. Advanced transformation inference
2. Edit distance matching
3. Rule ranking by frequency
4. Rule combination detection

## Conclusion

**Best approach for Hashcat rule generation from leaks**:
1. **Dictionary-based transformation inference** (70% of value)
2. **Statistical pattern extraction** (20% of value - already have this)
3. **Heuristic base word detection** (10% of value)

The current implementation does #2 well but is missing #1, which is the most important part.

**Next Steps**: Implement dictionary-based rule learning to actually learn transformations from leaked passwords.
