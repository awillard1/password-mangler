"""
Main processing orchestration with optimized threading and memory management.
"""

import os
import sys
import tempfile
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

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
               hashcat_rules=False, leak_path=None, progress_callback=None):
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
    
    Returns:
        True if successful, False otherwise
    """
    
    # Step 1: ML Analysis - Now supports directory of leak files
    if leak_path and os.path.exists(leak_path):
        logging.info("[Main] Starting ML-based rule learning...")
        if progress_callback:
            progress_callback("status", "Analyzing leak data with ML...")

        passwords = []
        sample_limit = None

        if os.path.isdir(leak_path):
            logging.info(f"[ML] Loading leaks from directory: {leak_path}")
            files_processed = 0
            total_passwords_added = 0

            for fname in os.listdir(leak_path):
                fpath = os.path.join(leak_path, fname)
                if not os.path.isfile(fpath):
                    continue

                files_processed += 1
                logging.info(f"[ML] Reading file {files_processed}: {fpath}")

                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines_read = 0
                        for line in f:
                            pwd = line.strip()
                            if 4 <= len(pwd) <= 40:
                                passwords.append(pwd.lower())
                                total_passwords_added += 1
                                lines_read += 1

                                # Only check limit if one is set
                                if sample_limit is not None and len(passwords) >= sample_limit:
                                    logging.info(f"[ML] Reached sample limit of {sample_limit:,} passwords after adding {lines_read} from this file.")
                                    logging.info(f"[ML] Total passwords collected: {len(passwords):,}. Stopping early.")
                                    break

                        if sample_limit is not None and len(passwords) >= sample_limit:
                            logging.info(f"[ML] Sample limit reached after {files_processed} files. Skipping remaining files.")
                            break

                    logging.info(f"[ML] Added {lines_read:,} valid passwords from this file (total so far: {len(passwords):,})")

                except Exception as e:
                    logging.warning(f"[ML] Failed to read {fpath}: {e}")

            logging.info(f"[ML] Finished processing directory. Total files read: {files_processed}")
            logging.info(f"[ML] Total passwords collected for analysis: {len(passwords):,}")

        if passwords:
            # Use core analysis directly (more efficient than full clustering)
            top_appends, top_prepends, learned_subs = mangler_core.analyze_patterns(passwords, top_n=50)

            mangler_core.learned_appends[:] = [a for a in top_appends if a not in mangler_core.common_suffixes and len(a) <= 6]
            mangler_core.learned_prefixes[:] = [p for p in top_prepends if p not in mangler_core.common_prefixes and len(p) <= 6]

            for char, subs in learned_subs.items():
                if char not in mangler_core.learned_leet:
                    mangler_core.learned_leet[char] = []
                for sub in subs:
                    if sub not in mangler_core.learned_leet[char]:
                        mangler_core.learned_leet[char].append(sub)

            logging.info(f"[ML] Learned {len(mangler_core.learned_appends)} appends, {len(mangler_core.learned_prefixes)} prepends")
        else:
            logging.warning("[Main] No valid passwords found in leak source")
    
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


# Export main functions
__all__ = [
    'parse_file',
    'interactive_profile',
]