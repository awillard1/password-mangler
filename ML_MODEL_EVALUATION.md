# ML Model Evaluation for Password Mangling

## The Core Question: What is the ML Task?

Before choosing a model, we need to clearly define what we're trying to predict/learn:

### Current Approach (Pattern Frequency Analysis)
- **Task**: Count frequency of suffixes, prefixes, and character substitutions
- **Method**: Simple Counter objects (not really "ML")
- **Model**: None (just statistics)
- **Output**: Lists of popular patterns ("123", "!", "2024", etc.)

### Current "ML" Component (MiniBatchKMeans)
- **Task**: Cluster passwords by character n-gram similarity
- **Purpose**: Discover leet speak patterns from clusters
- **Value**: Minimal (built-in rules already comprehensive)
- **Cost**: High (slow, memory intensive)

## Actual Use Cases for ML in Password Tools

### Use Case 1: Pattern Frequency Learning (Current)
**Goal**: Learn what suffixes/prefixes are most common in leaked passwords

**Best "Model"**: Counter-based statistics (not ML)
- Simple, fast, interpretable
- Already implemented correctly
- No model needed

**Conclusion**: Current approach is optimal for this task

### Use Case 2: Password Strength Prediction
**Goal**: Predict how strong/crackable a password is

**Best Models**:
1. **Random Forest Classifier** - Fast, interpretable
2. **Gradient Boosting (XGBoost/LightGBM)** - High accuracy
3. **Neural Network (LSTM)** - Can learn sequential patterns

**Implementation**:
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

# Features: length, character types, entropy, common patterns
# Label: weak (0) vs strong (1)
```

**Value for Password Mangling**: LOW - We're not predicting strength

### Use Case 3: Next-Character Prediction (Language Model)
**Goal**: Predict next character in password sequence

**Best Models**:
1. **Character-level RNN/LSTM** - Traditional approach
2. **GPT-2/GPT-3 (Small)** - Modern transformer approach
3. **MarkovChain** - Simple probabilistic model

**Example with LSTM**:
```python
import tensorflow as tf
from tensorflow.keras import layers

model = tf.keras.Sequential([
    layers.Embedding(vocab_size, 128),
    layers.LSTM(256, return_sequences=True),
    layers.LSTM(256),
    layers.Dense(vocab_size, activation='softmax')
])

# Train on password sequences
# Generate new passwords character by character
```

**Value for Password Mangling**: MEDIUM - Could generate novel variations

### Use Case 4: Password Generation (Generative Model)
**Goal**: Generate realistic passwords from scratch

**Best Models**:
1. **Variational Autoencoder (VAE)** - Learn password distribution
2. **GAN (Generative Adversarial Network)** - Generate realistic samples
3. **GPT-2 Fine-tuned** - Generate text sequences
4. **PassGAN** - Specialized GAN for passwords

**PassGAN Example** (Published Research):
```python
# Based on: "PassGAN: A Deep Learning Approach for Password Guessing"
# Uses Wasserstein GAN architecture
# Trains on RockYou dataset
# Generates novel, realistic passwords

# Architecture:
# Generator: Takes random noise → outputs password
# Discriminator: Classifies real vs generated passwords
```

**Value for Password Mangling**: HIGH for generation, LOW for rule-based mangling

### Use Case 5: Rule Learning (Sequence-to-Sequence)
**Goal**: Learn transformation rules (base_word → password)

**Best Models**:
1. **Seq2Seq with Attention** - Learn transformations
2. **Transformer (encoder-decoder)** - Modern approach
3. **Edit Distance Models** - Learn common edits

**Example**:
```python
# Input: "password"
# Output: "P@ssw0rd123!"
# Learn the transformation rules as a sequence mapping

from transformers import T5ForConditionalGeneration

# Fine-tune T5-small on (base_word, password) pairs
# Model learns: capitalization, leet speak, appends
```

**Value for Password Mangling**: MEDIUM - Could learn novel transformations

## Recommendation: Best Model for THIS Tool

### Analysis of Tool's Actual Need

**What the tool does**:
1. Takes base words (e.g., "password", "admin")
2. Applies **deterministic transformation rules**
3. Generates all variations systematically

**What ML could add**:
- Learn additional transformation rules from data
- Prioritize likely variations over unlikely ones
- Generate novel transformations not in built-in rules

### Option 1: Keep It Simple (Recommended)
**Model**: None (pattern frequency only)

**Rationale**:
- Built-in rules are already comprehensive (30+ leet, 50+ suffixes, etc.)
- Deterministic rules ensure complete coverage
- ML adds complexity without clear benefit
- Users want speed and coverage, not "intelligence"

**Implementation**: Current counter-based approach is optimal

### Option 2: Lightweight Markov Chain
**Model**: Character-level Markov Chain

**Rationale**:
- Simple probabilistic model
- Fast training and inference
- Can generate variations based on learned transitions
- No heavy dependencies (numpy only)

**Implementation**:
```python
import numpy as np
from collections import defaultdict

class PasswordMarkovChain:
    def __init__(self, order=2):
        self.order = order
        self.transitions = defaultdict(lambda: defaultdict(int))
    
    def train(self, passwords):
        for pwd in passwords:
            pwd = '^' * self.order + pwd + '$'  # Start/end markers
            for i in range(len(pwd) - self.order):
                context = pwd[i:i+self.order]
                next_char = pwd[i+self.order]
                self.transitions[context][next_char] += 1
    
    def generate_suffix(self, base_word, max_len=5):
        """Generate likely suffix for base_word"""
        context = base_word[-self.order:]
        suffix = []
        for _ in range(max_len):
            if context not in self.transitions:
                break
            chars = self.transitions[context]
            # Sample weighted by frequency
            total = sum(chars.values())
            r = np.random.randint(total)
            for char, count in chars.items():
                r -= count
                if r < 0:
                    if char == '$':
                        break
                    suffix.append(char)
                    context = context[1:] + char
                    break
        return ''.join(suffix)

# Usage:
mc = PasswordMarkovChain(order=2)
mc.train(leaked_passwords)
suffix = mc.generate_suffix("password")  # Might generate "123" or "2024"
```

**Pros**:
- Fast (milliseconds)
- Lightweight (< 100 lines)
- No dependencies beyond numpy
- Learns actual character transitions from data

**Cons**:
- Generates somewhat random output
- May not respect common patterns
- Less comprehensive than rule-based approach

### Option 3: Fine-tuned GPT-2 Small (If Going Full ML)
**Model**: GPT-2 Small (124M parameters) fine-tuned on passwords

**Rationale**:
- Modern, proven architecture
- Can learn complex patterns
- Generates contextually appropriate variations
- Pre-trained on text, adapts to passwords

**Implementation**:
```python
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch

class PasswordGPT:
    def __init__(self):
        self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        self.model = GPT2LMHeadModel.from_pretrained('gpt2')
        # Add special token for password generation
        self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
        self.model.resize_token_embeddings(len(self.tokenizer))
    
    def train(self, passwords, epochs=3):
        """Fine-tune on password dataset"""
        # Prepare dataset
        inputs = self.tokenizer(passwords, return_tensors='pt', 
                                padding=True, truncation=True)
        
        # Train
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=5e-5)
        self.model.train()
        for epoch in range(epochs):
            outputs = self.model(**inputs, labels=inputs['input_ids'])
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
    
    def generate_variations(self, base_word, num=10):
        """Generate password variations for base_word"""
        prompt = f"Generate password variations for: {base_word}\n"
        inputs = self.tokenizer(prompt, return_tensors='pt')
        
        outputs = self.model.generate(
            inputs['input_ids'],
            max_length=50,
            num_return_sequences=num,
            temperature=0.8,
            do_sample=True
        )
        
        variations = [self.tokenizer.decode(out, skip_special_tokens=True) 
                     for out in outputs]
        return variations

# Usage:
gpt = PasswordGPT()
gpt.train(leaked_passwords)
variations = gpt.generate_variations("password")
# Might generate: ["P@ssw0rd!", "password2024", "Password123!", ...]
```

**Pros**:
- State-of-the-art generation quality
- Learns complex patterns
- Can generate novel, realistic variations
- Impressive "ML" factor

**Cons**:
- SLOW (seconds per variation)
- LARGE (500MB+ model)
- Requires GPU for reasonable speed
- Overkill for deterministic mangling
- Requires transformers library

### Option 4: Specialized PassGAN
**Model**: PassGAN (GAN for password generation)

**Rationale**:
- Specifically designed for passwords
- Published, validated approach
- Generates realistic passwords

**Implementation**: Complex, requires:
- GAN training loop (generator + discriminator)
- Large dataset (millions of passwords)
- Multiple days of GPU training
- Careful hyperparameter tuning

**Pros**:
- Best for pure generation
- Research-backed approach

**Cons**:
- Massive overkill for rule-based tool
- Training complexity
- Not suitable for transformation task

## Final Recommendation

### For THIS Tool: No Traditional ML Model Needed

**Reasoning**:
1. **Task is rule-based, not prediction-based**
   - We want systematic coverage, not probabilistic generation
   - Deterministic rules ensure nothing is missed
   
2. **Built-in rules are already comprehensive**
   - 30+ leet mappings
   - 50+ suffixes
   - Keyboard walks, phonetic, etc.
   
3. **ML adds latency without clear benefit**
   - Training: seconds to minutes
   - Inference: slower than rules
   - Output: overlaps heavily with rules

### If You Insist on Using ML

**Best Choice: Lightweight Markov Chain (Option 2)**

**Why**:
- Fast training (<1 second)
- Fast inference (milliseconds)
- Learns from data
- No heavy dependencies
- Can augment existing rules

**Implementation Plan**:
1. Replace MiniBatchKMeans with Markov Chain
2. Train on leaked passwords (one-time)
3. Use to generate additional suffixes/prefixes
4. Combine with existing rule-based approach

**Code Example**:
```python
# Train once
mc = PasswordMarkovChain(order=2)
mc.train(leaked_passwords)

# Generate additional patterns
for base in ["password", "admin", "user"]:
    # Generate 10 likely suffixes
    for _ in range(10):
        suffix = mc.generate_suffix(base)
        learned_appends.append(suffix)
```

## Alternative: Hybrid Approach (Best of Both Worlds)

### Recommended Solution

**Keep rule-based as primary** (fast, comprehensive)
**Add optional Markov Chain** (learns from custom data)

```python
# Default mode: Rules only (instant)
mangler.py -i words.txt -o output.txt --rules advanced

# ML mode: Rules + learned patterns (few seconds extra)
mangler.py -i words.txt -o output.txt --leak rockyou.txt

# Model options:
--ml-model markov     # Lightweight Markov Chain (default)
--ml-model gpt2       # GPT-2 fine-tuning (slow, requires GPU)
--ml-model none       # Frequency counting only (current)
```

**Implementation**:
1. Rule-based transformations run first (always)
2. If `--leak` provided, train chosen model
3. Model generates additional variations
4. Combine and deduplicate

## Benchmark: Expected Performance

| Model | Training Time | Memory | Output Quality | Best For |
|-------|---------------|--------|----------------|----------|
| None (Counter) | <1s | <50MB | Good | Default use |
| Markov Chain | <5s | <100MB | Good | Custom patterns |
| GPT-2 Small | 5-30min | 2GB+ | Excellent | Research |
| PassGAN | Hours/Days | 4GB+ | Excellent | Pure generation |

## Conclusion

**For password mangling**: Use **Counter-based statistics** (current) or **lightweight Markov Chain**.

**NOT recommended**: GPT-2, PassGAN, or any deep learning model - they're designed for generation, not rule-based transformation.

**The tool's strength is systematic rule application, not intelligent prediction.**
