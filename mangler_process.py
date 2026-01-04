"""
Main processing orchestration with optimized threading and memory management.
"""

import os
import sys
import tempfile
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional progress bar
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Simple fallback
    def tqdm(iterable, **kwargs):
        return iterable

import mangler_core
import mangler_ml
import mangler_hashcat


def interactive_profile():
    """
    Interactive profiling to gather personal information for targeted wordlist.
    """
    logging.info("Starting targeted profiling...")
    info = {}
    
    prompts = [
        ("Full name", "john doe"),
        ("Nickname", "johnny"),
        ("Birth year", "1990"),
        ("Birth month", "january"),
        ("Birth day", "15"),
        ("Partner's name", "jane"),
        ("Pet's name", "max"),
        ("Company", "acme corp"),
        ("Favorite team", "eagles"),
        ("Favorite color", "blue"),
        ("Street name", "oak"),
        ("City", "seattle"),
    ]
    
    print("\n" + "=" * 50)
    print("   TARGETED PROFILING - Personal Information")
    print("=" * 50)
    print("Enter information to generate personalized wordlist.")
    print("Press Enter to skip any field.\n")
    
    for prompt, example in prompts:
        value = input(f"{prompt} (e.g., {example}): ").strip()
        if value:
            key = prompt.lower().replace(" ", "_").replace("'", "")
            info[key] = value.lower()
            
            # Add variations for names
            if "name" in key:
                parts = value.split()
                info[f"{key}_parts"] = " ".join(parts)
                for part in parts:
                    if len(part) >= 2:
                        info[f"{key}_{part}"] = part.lower()
    
    print("\n" + "=" * 50)
    print(f"Collected {len(info)} data points for profiling")
    print("=" * 50 + "\n")
    
    # Extract all values (including sub-parts)
    all_values = []
    for key, value in info.items():
        if " " in value:
            # Split multi-word values
            all_values.extend(value.split())
        else:
            all_values.append(value)
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for val in all_values:
        if val and val not in seen:
            seen.add(val)
            result.append(val)
    
    return result


def parse_file(input_file=None, output_file=None, ruleset="advanced", 
               threads=8, max_variations=1000, targeted=False, 
               hashcat_rules=False, leak_path=None, progress_callback=None,
               use_cache=True, chunk_size=10000):
    """
    Main processing function that orchestrates the mangling operation.
    
    Args:
        input_file: Input wordlist file
        output_file: Output file for results
        ruleset: Complexity level ("simple", "advanced", "extreme")
        threads: Number of worker threads
        max_variations: Maximum variations per word
        targeted: Use interactive profiling mode
        hashcat_rules: Generate Hashcat rules instead of wordlist
        leak_path: Password leak file or directory for ML learning
        progress_callback: Optional callback for progress updates (for GUI)
        use_cache: Use cached ML patterns if available
        chunk_size: Chunk size for streaming analysis of leak files
    
    Returns:
        True if successful, False otherwise
    """
    
    # Step 1: ML Analysis - Now supports directory of leak files with streaming
    if leak_path and os.path.exists(leak_path):
        logging.info("[Main] Starting ML-based rule learning...")
        if progress_callback:
            progress_callback("status", "Analyzing leak data with ML...")

        if os.path.isdir(leak_path):
            # Process directory with streaming for each file
            success = _analyze_leak_directory_streaming(leak_path, use_cache, chunk_size, progress_callback)
        else:
            # Single file - use new streaming API
            success = mangler_ml.analyze_leak_with_ml(
                leak_path, 
                sample_size=None,  # No limit for streaming
                streaming=True,
                use_cache=use_cache,
                chunk_size=chunk_size
            )
        
        if not success:
            logging.warning("[Main] ML analysis completed with issues, continuing anyway")
    
    # Step 2: Hashcat Rules Generation (if requested)
    if hashcat_rules:
        logging.info("[Main] Generating Hashcat rules...")
        if progress_callback:
            progress_callback("status", "Generating Hashcat rules...")
        
        count = mangler_hashcat.generate_hashcat_rules(output_file, ruleset)
        if count > 0:
            logging.info(f"[Main] SUCCESS! Generated {count} Hashcat rules → {output_file}")
            return True
        else:
            logging.error("[Main] Failed to generate Hashcat rules")
            return False
    
    # Step 3: Prepare base wordlist
    base_words = []
    
    if targeted:
        logging.info("[Main] Using targeted profiling mode")
        if progress_callback:
            progress_callback("status", "Collecting profile information...")
        base_words = interactive_profile()
    else:
        if not input_file or not os.path.exists(input_file):
            logging.error(f"[Main] Input file not found: {input_file}")
            return False
        
        logging.info(f"[Main] Reading input wordlist: {input_file}")
        if progress_callback:
            progress_callback("status", "Reading input wordlist...")
        
        try:
            with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
                base_words = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logging.error(f"[Main] Failed to read input file: {e}")
            return False
    
    if not base_words:
        logging.warning("[Main] No base words to process")
        return False
    
    logging.info(f"[Main] Processing {len(base_words)} base words with ruleset '{ruleset}'")
    
    # Step 4: Create output directory if needed
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Step 5: Process words with multi-threading
    temp_filename = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False).name
    
    try:
        logging.info(f"[Main] Starting parallel processing with {threads} threads...")
        if progress_callback:
            progress_callback("status", f"Mangling with {threads} threads...")
            progress_callback("progress_max", len(base_words))
        
        with open(temp_filename, "w", encoding="utf-8") as temp_file:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                # Prepare tasks
                tasks = [(word, ruleset, max_variations) for word in base_words]
                
                # Submit all tasks
                futures = [executor.submit(mangler_core.process_word, task) for task in tasks]
                
                # Process results with progress bar
                with tqdm(total=len(tasks), desc="Mangling (ML-Enhanced)", unit="word", 
                         disable=(progress_callback is not None)) as pbar:
                    
                    for idx, future in enumerate(as_completed(futures)):
                        try:
                            variants = future.result()
                            
                            # Write variants to temp file
                            for variant in variants:
                                temp_file.write(variant + "\n")
                            
                            # Update progress
                            pbar.update(1)
                            if progress_callback:
                                progress_callback("progress", idx + 1)
                                
                        except Exception as e:
                            logging.error(f"[Main] Error processing word: {e}")
        
        # Step 6: Deduplicate and sort
        logging.info("[Main] Deduplicating and sorting results...")
        if progress_callback:
            progress_callback("status", "Deduplicating and sorting...")
        
        try:
            # Use system sort for efficiency (works on Linux/Mac)
            subprocess.run(
                ["sort", "-u", temp_filename, "-o", output_file],
                check=True,
                capture_output=True
            )
            logging.info(f"[Main] SUCCESS! Output saved: {output_file}")
        except subprocess.CalledProcessError as e:
            # Fallback to Python sorting if system sort fails
            logging.warning("[Main] System sort failed, using Python sort...")
            with open(temp_filename, "r", encoding="utf-8") as f:
                lines = set(line.strip() for line in f if line.strip())
            
            with open(output_file, "w", encoding="utf-8") as f:
                for line in sorted(lines):
                    f.write(line + "\n")
            
            logging.info(f"[Main] SUCCESS! Output saved: {output_file}")
        
        # Count output lines
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
            logging.info(f"[Main] Generated {count:,} unique variations")
        except:
            pass
        
        return True
        
    except Exception as e:
        logging.error(f"[Main] Processing failed: {e}")
        return False
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass


def _analyze_leak_directory_streaming(leak_dir, use_cache, chunk_size, progress_callback):
    """
    Analyze directory of leak files using streaming approach.
    Processes files one at a time to avoid loading all into memory.
    """
    logging.info(f"[ML] Streaming analysis of directory: {leak_dir}")
    
    # Get all files
    files = [f for f in os.listdir(leak_dir) if os.path.isfile(os.path.join(leak_dir, f))]
    
    if not files:
        logging.warning("[ML] No files found in directory")
        return False
    
    # Initialize counters for aggregating across all files
    append_counter = Counter()
    prepend_counter = Counter()
    char_subs = {}
    total_processed = 0
    
    logging.info(f"[ML] Found {len(files)} files to process")
    
    for idx, fname in enumerate(files, 1):
        fpath = os.path.join(leak_dir, fname)
        logging.info(f"[ML] Processing file {idx}/{len(files)}: {fname}")
        
        if progress_callback:
            progress_callback("status", f"Analyzing leak file {idx}/{len(files)}: {fname}")
        
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                chunk = []
                
                for line in f:
                    pwd = line.strip()
                    
                    if 4 <= len(pwd) <= 40:
                        chunk.append(pwd.lower())
                        total_processed += 1
                    
                    # Process chunk when full
                    if len(chunk) >= chunk_size:
                        mangler_ml._update_pattern_counters(chunk, append_counter, prepend_counter, char_subs)
                        chunk = []
                        
                        # Log progress periodically
                        if total_processed % (chunk_size * 10) == 0:
                            logging.info(f"[ML] Processed {total_processed:,} passwords so far...")
                
                # Process remaining chunk
                if chunk:
                    mangler_ml._update_pattern_counters(chunk, append_counter, prepend_counter, char_subs)
                    
        except Exception as e:
            logging.warning(f"[ML] Failed to read {fpath}: {e}")
            continue
    
    if total_processed < 100:
        logging.warning("[ML] Not enough passwords for meaningful analysis")
        return False
    
    logging.info(f"[ML] Completed directory analysis: {total_processed:,} passwords from {len(files)} files")
    
    # Apply learned patterns
    mangler_ml._apply_learned_patterns(append_counter, prepend_counter, char_subs, total_processed)
    
    # Save to cache
    if use_cache:
        cache_path = mangler_ml._get_cache_path(leak_dir)
        patterns = {
            "appends": mangler_core.learned_appends,
            "prefixes": mangler_core.learned_prefixes,
            "leet": mangler_core.learned_leet,
            "weights": mangler_core.learned_weights,
        }
        mangler_ml._save_cached_patterns(cache_path, patterns)
    
    return True


# Export main functions
__all__ = [
    'parse_file',
    'interactive_profile',
]