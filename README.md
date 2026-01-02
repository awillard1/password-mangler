# Ultimate Password Mangler 2026 - ML Enhanced

A powerful, optimized password wordlist generator with ML-based rule induction for penetration testing and security research.

⚠️ **ETHICAL USE ONLY**: This tool is intended for authorized security testing and research purposes only. Unauthorized use is illegal.

## 🚀 Features

### Core Functionality
- **GUI Interface**: User-friendly Tkinter-based graphical interface
- **CLI Interface**: Command-line interface for automation and scripting
- **Interactive Profiling**: Targeted wordlist generation from personal information
- **Hashcat Rules**: Generate Hashcat-compatible rule files
- **ML Learning**: Analyze leaked passwords to learn common patterns

### Best-in-Class Transformations

#### 🔤 Leet Speak (30+ character mappings)
- Comprehensive character substitutions: a→@, e→3, o→0, s→$, etc.
- Multi-level substitutions for thorough coverage
- Context-aware case preservation

#### ⌨️ Keyboard Patterns (20+ patterns)
- Row walks: qwerty, asdfg, zxcvb
- Column walks: qaz, wsx, edc
- Diagonal walks: 1qaz2wsx, 1q2w3e4r
- Number pad patterns

#### 🗣️ Phonetic Substitutions (20+ patterns)
- love→luv, you→u, for→4
- are→r, to→2, at→@
- Extended phonetic mapping for common words

#### 📅 Date/Year Patterns (40+ variations)
- Current year and adjacent years
- Two-digit and four-digit formats
- Common year suffixes (2024, 2025, 2026, etc.)

#### 💪 Advanced Mutations
- **Case Variations**: 8 different casing styles per word
- **Character Doubling/Tripling**: password → passsword
- **Reversals**: password → drowssap
- **Middle Injections**: password → pass!word
- **Prefix/Suffix Combinations**: 50+ common patterns

### 🧠 ML-Based Learning
- Analyzes leaked password databases
- Learns common append/prepend patterns
- Discovers leet speak substitutions
- Weights patterns by frequency
- MiniBatchKMeans clustering for scalability

### ⚡ Performance Optimizations
- **Generators & Lazy Evaluation**: Minimal memory footprint
- **Multi-threading**: Parallel processing with configurable threads
- **Efficient Deduplication**: System-level sorting when available
- **Progress Tracking**: Real-time feedback with tqdm

## 📦 Installation

### Requirements
- Python 3.8+
- tkinter (for GUI)
- Required packages:

```bash
pip install -r requirements.txt
```

### Dependencies
- scikit-learn >= 1.3.0
- tqdm >= 4.66.0
- numpy >= 1.24.0

## 🎯 Usage

### GUI Mode
```bash
python3 mangler.py --gui
```

### CLI Mode

#### Basic Usage
```bash
# Generate wordlist with advanced rules
python3 mangler.py -i wordlist.txt -o output.txt --rules advanced

# Use ML learning from leaked passwords
python3 mangler.py -i wordlist.txt -o output.txt --leak-file leaked.txt

# Extreme mode with maximum variations
python3 mangler.py -i wordlist.txt -o output.txt --rules extreme --max-variations 2000
```

#### Targeted Profiling
```bash
# Interactive mode - generates wordlist from personal info
python3 mangler.py -o output.txt --targeted
```

#### Hashcat Rules Generation
```bash
# Generate Hashcat-compatible rules
python3 mangler.py -o rules.txt --hashcat-rules --rules advanced
```

### Command-Line Options

```
-i, --input              Input wordlist file
-o, --output            Output file path (required)
--rules                 Ruleset: simple, advanced, extreme (default: advanced)
--threads               Number of worker threads (default: CPU count)
--max-variations        Maximum variations per word (default: 1000)
--targeted              Interactive profiling mode
--hashcat-rules         Generate Hashcat rules instead of wordlist
--leak-file             Password leak file for ML learning
--gui                   Launch graphical interface
```

## 📊 Performance

### Test Results (3 base words)
- **Simple**: 18 variations in <0.1s
- **Advanced**: 300 variations in <0.1s
- **Extreme**: 1000+ variations per word

### ML Learning (244 password sample)
- Learned: 38 appends, 3 prefixes
- Discovered: 6 character leet substitutions
- Processing time: <1s

## 🏗️ Architecture

### Modular Design
```
mangler.py           # Main entry point, GUI, CLI
mangler_core.py      # Core transformation functions (generators)
mangler_ml.py        # ML-based pattern learning
mangler_hashcat.py   # Hashcat rules generation
mangler_process.py   # Processing orchestration, threading
```

### Key Improvements
1. **Separation of Concerns**: Each module has a single responsibility
2. **Memory Efficiency**: Generator-based variation production
3. **Scalability**: MiniBatchKMeans for large datasets
4. **Maintainability**: Clear structure with comprehensive logging

## 🔬 Example Transformations

Input: `password`

Sample outputs:
```
password
Password
PASSWORD
p@ssword
p4ssw0rd
passw0rd
password123
password!
password2025
Password123
P@ssw0rd!
p@ssw0rd123
drowssap
pass!word
qwertypassword
123password
```

## 🛡️ Security Notes

- Always use for authorized testing only
- Respect privacy and legal boundaries
- Follow responsible disclosure practices
- Keep generated wordlists secure
- Do not share passwords or sensitive data

## 📝 License

For authorized security testing and research only.

## 🤝 Contributing

This is a security tool - ensure all contributions follow ethical guidelines.

## 📧 Contact

For security research collaboration only.

---

**Remember**: With great power comes great responsibility. Use wisely! 🔐
