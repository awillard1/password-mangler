# ML Pattern Query Tool

Standalone utility for querying and reusing learned ML patterns from password-mangler.

## Overview

After password-mangler analyzes leak files, it caches learned patterns (appends, prepends, leet substitutions). This tool allows you to **query and reuse** those patterns without re-running the full analysis.

## What Can You Do With Learned ML Patterns?

1. **Query for password suggestions** - Get top candidates for any word
2. **Generate wordlists** - Apply learned patterns to new base words
3. **Export as Hashcat rules** - Convert patterns to Hashcat rule format
4. **Merge multiple caches** - Combine patterns from different leak files
5. **Interactive exploration** - Browse patterns interactively

## Quick Start

### 1. List Available ML Caches

```bash
python3 ml_query.py --list
```

Output:
```
Found 2 cached ML pattern(s):

1. Cache Hash: abc123def456
   Source: /data/rockyou.txt
   Cached: 2026-01-04 02:30:15
   Model: counter
   Patterns: 78 appends, 15 prepends, 12 leet substitutions

2. Cache Hash: xyz789ghi012
   Source: /data/linkedin_leak.txt
   Cached: 2026-01-04 03:15:42
   Model: counter
   Patterns: 65 appends, 10 prepends, 10 leet substitutions
```

### 2. Query for Password Suggestions

```bash
python3 ml_query.py --word "password" --cache abc123def456
```

Output:
```
Top 20 password candidates for 'password':
------------------------------------------------------------
   1. password123                    (confidence: 0.850)
   2. password2024                   (confidence: 0.680)
   3. Password123                    (confidence: 0.612)
   4. password!                      (confidence: 0.450)
   5. p@ssword123                    (confidence: 0.340)
   ...
```

### 3. Interactive Mode

```bash
python3 ml_query.py --interactive
```

Then type words to get instant suggestions:
```
Word: admin
Top password candidates for 'admin':
  1. admin123
  2. admin2024
  3. Admin123
  ...

Word: company
Top password candidates for 'company':
  1. company123
  2. Company2024
  ...
```

### 4. Generate Wordlist from ML Patterns

Apply learned patterns to new base words:

```bash
python3 ml_query.py --generate company_names.txt -o output.txt --cache abc123def456
```

This takes your base words and applies the most common patterns learned from leak files.

### 5. Export as Hashcat Rules

Convert learned patterns to Hashcat rule format:

```bash
python3 ml_query.py --export-rules custom.rule --cache abc123def456 --max-rules 200
```

Creates a Hashcat rule file with the most effective transformations.

### 6. Show Pattern Summary

View detailed statistics about learned patterns:

```bash
python3 ml_query.py --summary --cache abc123def456
```

### 7. Merge Multiple Caches

Combine patterns from different leak files:

```bash
python3 ml_query.py --merge abc123,xyz789,def456 -o merged_patterns.json
```

## Use Cases

### Use Case 1: Targeted Attack with Learned Patterns

1. Analyze a relevant leak file with password-mangler:
```bash
python3 mangler.py -i base.txt -o output.txt --leak industry_leak.txt
```

2. Later, apply those patterns to company-specific words:
```bash
python3 ml_query.py --generate company_words.txt -o targeted.txt --cache <hash>
```

### Use Case 2: Quick Password Candidate Check

During a pentest, quickly check if a username might have common variations:

```bash
python3 ml_query.py --word "jsmith" --cache <hash>
```

Get instant suggestions based on real-world patterns.

### Use Case 3: Build Custom Hashcat Rules

Create optimized rules from your leak file analysis:

```bash
python3 ml_query.py --export-rules industry_specific.rule --cache <hash>
hashcat -m 1000 hashes.txt wordlist.txt -r industry_specific.rule
```

### Use Case 4: Merge Patterns from Multiple Sources

Combine patterns from multiple industries/breaches:

```bash
python3 ml_query.py --merge tech_leak,finance_leak,edu_leak -o combined.json
```

Then use the combined patterns for broader coverage.

## Command Reference

### Listing and Exploration

| Command | Description |
|---------|-------------|
| `--list` | List all available ML pattern caches |
| `--summary --cache <hash>` | Show detailed pattern statistics |
| `--interactive` | Interactive query mode |

### Querying

| Command | Description |
|---------|-------------|
| `--word <word> --cache <hash>` | Get password suggestions for specific word |
| `--top-n N` | Number of suggestions (default: 20) |

### Generation

| Command | Description |
|---------|-------------|
| `--generate <input> -o <output> --cache <hash>` | Generate wordlist from base words |
| `--variations N` | Variations per word (default: 10) |

### Export

| Command | Description |
|---------|-------------|
| `--export-rules <output> --cache <hash>` | Export as Hashcat rules |
| `--max-rules N` | Maximum rules to export (default: 100) |

### Merging

| Command | Description |
|---------|-------------|
| `--merge <hash1,hash2,...> -o <output>` | Merge multiple caches |

## Integration with password-mangler

### Creating ML Caches

ML caches are automatically created when you run password-mangler with leak files:

```bash
# Analyze leak file (creates cache automatically)
python3 mangler.py -i base_words.txt -o output.txt --leak rockyou.txt
```

Cache location: `~/.cache/password-mangler/ml_patterns_<hash>.json`

### Workflow

```
┌─────────────────────┐
│ 1. password-mangler │ Analyze leak file
│    with --leak      │ → Creates ML cache
└──────────┬──────────┘
           │
           ↓ (cache saved)
┌─────────────────────┐
│ 2. ml_query.py      │ Query/reuse patterns
│    (anytime later)  │ → No re-analysis needed
└─────────────────────┘
```

## Benefits

✅ **No Re-analysis** - Query patterns instantly without re-processing GB files
✅ **Reusable** - Apply learned patterns to different wordlists
✅ **Flexible** - Generate passwords, Hashcat rules, or just explore patterns
✅ **Combinable** - Merge patterns from multiple sources
✅ **Fast** - Queries return in milliseconds

## Technical Details

### Cache Format

Caches are stored as JSON with:
- `appends`: Dictionary of suffix patterns with occurrence counts
- `prepends`: Dictionary of prefix patterns with occurrence counts
- `leet`: Dictionary of leet speak substitutions with counts
- `source_file`: Original leak file analyzed
- `cache_time`: When cache was created
- `ml_model`: Analysis method used

### Confidence Scores

Confidence scores are based on:
- **Frequency** in original leak file (higher = more common)
- **Pattern type** (appends score higher than complex transformations)
- **Combination complexity** (simple patterns score higher)

Scores range from 0.0 to 1.0 where:
- 0.8+ = Very common pattern
- 0.5-0.8 = Common pattern
- 0.3-0.5 = Moderate pattern
- <0.3 = Uncommon pattern

## Examples

### Example 1: Interactive Exploration

```bash
$ python3 ml_query.py --interactive

ML PATTERN QUERY TOOL - INTERACTIVE MODE
======================================================================

Available ML Pattern Caches:

1. /data/rockyou.txt
   Cache time: 2026-01-04 02:30:15
   Patterns: 78 appends, 15 prepends, 12 leet

Select cache (1-1): 1

Loaded patterns from: /data/rockyou.txt

Enter base words to get password suggestions (or 'quit' to exit):

Word: admin
Top password candidates for 'admin':
  1. admin123                    (confidence: 0.850)
  2. admin2024                   (confidence: 0.680)
  3. Admin123                    (confidence: 0.612)
  ...

Word: quit
Exiting interactive mode.
```

### Example 2: Batch Generation

```bash
$ cat company_terms.txt
acme
engineering
sales

$ python3 ml_query.py --generate company_terms.txt -o passwords.txt --cache abc123

[INFO] Loading base words from company_terms.txt
[INFO] Loaded 3 base words
[INFO] Loaded patterns from: /data/rockyou.txt
[INFO] SUCCESS! Generated 30 passwords to passwords.txt
[INFO] Average 10.0 variations per base word

$ head passwords.txt
acme123
acme2024
Acme123
acme!
@cme123
engineering123
engineering2024
Engineering2024
...
```

## Troubleshooting

**Q: No caches found**
A: Run password-mangler with `--leak` option first to create caches

**Q: How do I find the cache hash?**
A: Run `python3 ml_query.py --list` to see all caches with their hashes

**Q: Can I use multiple caches at once?**
A: Yes, use `--merge` to combine them first, then use the merged cache

**Q: Patterns seem outdated**
A: Re-run password-mangler analysis on updated leak files to refresh caches

## See Also

- `mangler.py` - Main password generation tool
- `mangler_analyzer.py` - Wordlist analysis and rule generation
- `README.md` - Main password-mangler documentation
