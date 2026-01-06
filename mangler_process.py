"""
Main processing orchestration with optimized threading and memory management.
"""

import os
import sys
import tempfile
import subprocess
import logging
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import mangler_core
import mangler_ml
import mangler_hashcat
import mangler_ml_query


# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    global _shutdown_requested
    if not _shutdown_requested:
        _shutdown_requested = True
        logging.warning("\n[Signal] Ctrl+C detected. Finishing current operations and saving progress...")
        logging.warning("[Signal] Press Ctrl+C again to force quit (may lose data)")
    else:
        logging.error("[Signal] Force quit requested. Exiting immediately.")
        sys.exit(1)


def is_shutdown_requested():
    """Check if shutdown has been requested."""
    return _shutdown_requested


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
    
    # Install signal handler for graceful shutdown
    global _shutdown_requested
    _shutdown_requested = False
    signal.signal(signal.SIGINT, signal_handler)
    
    # Track if we're analyzing leaks for potential cache saving
    cache_hash = None
    base_word_transforms = None
    
    # Step 1: ML Analysis - Now supports directory of leak files with streaming
    if leak_path and os.path.exists(leak_path):
        # Check if cache already exists
        cache_exists, existing_hash, existing_cache_file = mangler_ml_query.check_cache_exists(leak_path)
        
        if cache_exists:
            logging.info(f"[Cache] Found existing cache for {leak_path}")
            logging.info(f"[Cache] Cache hash: {existing_hash}")
            logging.info(f"[Cache] Loading cached patterns instead of re-analyzing...")
            
            try:
                # Load patterns from cache
                cached_patterns = mangler_ml_query.load_ml_patterns(cache_hash=existing_hash)
                
                # Apply loaded patterns to mangler_core
                appends_dict = cached_patterns.get('appends', {})
                prepends_dict = cached_patterns.get('prepends', {})
                leet_dict = cached_patterns.get('leet', {})
                
                # Convert appends/prepends back to lists
                mangler_core.learned_appends[:] = list(appends_dict.keys())
                mangler_core.learned_prefixes[:] = list(prepends_dict.keys())
                
                # Convert leet back to the expected format
                mangler_core.learned_leet.clear()
                for leet_key in leet_dict.keys():
                    if '->' in leet_key:
                        char, sub = leet_key.split('->')
                        if char not in mangler_core.learned_leet:
                            mangler_core.learned_leet[char] = []
                        if sub not in mangler_core.learned_leet[char]:
                            mangler_core.learned_leet[char].append(sub)
                
                cache_hash = existing_hash
                base_word_transforms = cached_patterns.get('base_word_transforms', {})
                
                logging.info(f"[Cache] Loaded {len(mangler_core.learned_appends)} appends, {len(mangler_core.learned_prefixes)} prepends")
                logging.info(f"[Cache] Use 'python3 ml_query.py --cache {cache_hash}' to query patterns")
                
            except Exception as e:
                logging.warning(f"[Cache] Failed to load cache, will re-analyze: {e}")
                cache_exists = False
        
        # Only analyze if cache doesn't exist or failed to load
        if not cache_exists:
            logging.info("[Main] Starting ML-based rule learning...")
            if progress_callback:
                progress_callback("status", "Analyzing leak data with ML...")

            # Collect all passwords for base word analysis
            all_passwords_for_base = []
            passwords_processed = 0
            
            # For parallel file reading
            from queue import Queue
            from threading import Thread, Lock
            
            password_queue = Queue(maxsize=10000)  # Buffer for passwords
            stats_lock = Lock()
    
            def read_file_worker(filepath, file_num):
                """Worker to read a single file and add passwords to queue."""
                nonlocal passwords_processed
                local_count = 0
                
                try:
                    # Use larger buffer for faster reading (1MB buffer)
                    with open(filepath, "r", encoding="utf-8", errors="ignore", buffering=1024*1024) as f:
                        # Read in chunks for better performance
                        lines_buffer = []
                        for line in f:
                            if _shutdown_requested:
                                break
                            
                            pwd = line.strip()
                            if 4 <= len(pwd) <= 40:
                                lines_buffer.append(pwd.lower())
                                local_count += 1
                                
                                # Batch insert for efficiency
                                if len(lines_buffer) >= 1000:
                                    for p in lines_buffer:
                                        try:
                                            password_queue.put(p, timeout=1.0)
                                        except:
                                            if _shutdown_requested:
                                                break
                                    lines_buffer = []
                        
                        # Add remaining
                        for p in lines_buffer:
                            try:
                                password_queue.put(p, timeout=1.0)
                            except:
                                if _shutdown_requested:
                                    break
                        
                    with stats_lock:
                        passwords_processed += local_count
                        
                    logging.info(f"[ML] File {file_num} complete: {os.path.basename(filepath)} - {local_count:,} passwords")
                    
                except Exception as e:
                    logging.warning(f"[ML] Failed to read {filepath}: {e}")
    
            def password_iterator():
                """Generator that yields passwords from files without loading all into memory."""
                nonlocal passwords_processed
                
                if os.path.isdir(leak_path):
                    logging.info(f"[ML] Parallel streaming analysis of directory: {leak_path}")
                    
                    # Get all files to process
                    files_to_process = []
                    for fname in os.listdir(leak_path):
                        fpath = os.path.join(leak_path, fname)
                        if os.path.isfile(fpath):
                            files_to_process.append(fpath)
                    
                    if not files_to_process:
                        logging.warning(f"[ML] No files found in directory: {leak_path}")
                        return
                    
                    logging.info(f"[ML] Found {len(files_to_process)} files to process in parallel")
                    
                    # Start reader threads (limit to CPU count for IO-bound tasks)
                    max_readers = min(os.cpu_count() or 4, len(files_to_process), 8)
                    reader_threads = []
                    
                    def file_reader_dispatcher():
                        """Dispatch files to reader threads."""
                        for idx, fpath in enumerate(files_to_process):
                            if _shutdown_requested:
                                break
                            # Start reader in thread pool fashion
                            t = Thread(target=read_file_worker, args=(fpath, idx + 1))
                            t.daemon = True
                            t.start()
                            reader_threads.append(t)
                            
                            # Limit concurrent readers
                            active = [t for t in reader_threads if t.is_alive()]
                            while len(active) >= max_readers and not _shutdown_requested:
                                # Wait for one to finish
                                reader_threads[0].join(timeout=0.1)
                                active = [t for t in reader_threads if t.is_alive()]
                        
                        # Wait for all readers to complete
                        for t in reader_threads:
                            t.join()
                        
                        # Signal completion
                        password_queue.put(None)
                    
                    # Start dispatcher thread
                    dispatcher = Thread(target=file_reader_dispatcher)
                    dispatcher.daemon = True
                    dispatcher.start()
                    
                    # Yield passwords as they arrive
                    sample_count = 0
                    while True:
                        pwd = password_queue.get()
                        if pwd is None:  # Completion signal
                            break
                        
                        # Collect sample for base word analysis
                        if sample_count < 10000:
                            all_passwords_for_base.append(pwd)
                            sample_count += 1
                        
                        yield pwd
                    
                    # Wait for dispatcher to complete
                    dispatcher.join()
                    
                    logging.info(f"[ML] Finished parallel processing. Total: {passwords_processed:,} passwords from {len(files_to_process)} files")
                    
                else:
                    # Single file processing - optimized with larger buffer
                    logging.info(f"[ML] Fast streaming analysis of file: {leak_path}")
                    try:
                        # Use 1MB buffer for faster reading
                        with open(leak_path, "r", encoding="utf-8", errors="ignore", buffering=1024*1024) as f:
                            for line in f:
                                if _shutdown_requested:
                                    logging.warning(f"[ML] Shutdown requested while reading file. Saving partial results...")
                                    break
                                
                                pwd = line.strip()
                                if 4 <= len(pwd) <= 40:
                                    passwords_processed += 1
                                    # Collect sample for base word analysis
                                    if len(all_passwords_for_base) < 10000:
                                        all_passwords_for_base.append(pwd.lower())
                                    yield pwd.lower()
                    except Exception as e:
                        logging.error(f"[ML] Failed to read leak file: {e}")
            
            # Use streaming analysis to process all data without memory exhaustion
            try:
                top_appends, top_prepends, learned_subs = mangler_core.analyze_patterns_streaming(
                    password_iterator(), batch_size=50000, top_n=50
                )
                
                # Analyze base words from collected sample
                if all_passwords_for_base and not _shutdown_requested:
                    logging.info(f"[ML] Analyzing base words from {len(all_passwords_for_base)} password sample...")
                    base_word_transforms = mangler_core.analyze_base_word_transformations(
                        all_passwords_for_base, max_base_words=500, min_occurrences=2
                    )
                    logging.info(f"[ML] Identified {len(base_word_transforms)} unique base words")
                
                mangler_core.learned_appends[:] = [a for a in top_appends if a not in mangler_core.common_suffixes and len(a) <= 6]
                mangler_core.learned_prefixes[:] = [p for p in top_prepends if p not in mangler_core.common_prefixes and len(p) <= 6]
                
                for char, subs in learned_subs.items():
                    if char not in mangler_core.learned_leet:
                        mangler_core.learned_leet[char] = []
                    for sub in subs:
                        if sub not in mangler_core.learned_leet[char]:
                            mangler_core.learned_leet[char].append(sub)
                
                logging.info(f"[ML] Learned {len(mangler_core.learned_appends)} appends, {len(mangler_core.learned_prefixes)} prepends")
                
                # Save ML patterns to cache (even if shutdown was requested - save what we have)
                if passwords_processed > 0:
                    try:
                        # Convert learned patterns to format expected by save function
                        appends_dict = {a: top_appends.count(a) if isinstance(top_appends, list) else 1 
                                       for a in mangler_core.learned_appends}
                        prepends_dict = {p: top_prepends.count(p) if isinstance(top_prepends, list) else 1 
                                        for p in mangler_core.learned_prefixes}
                        
                        # Save to cache
                        cache_hash = mangler_ml_query.save_ml_patterns(
                            appends=appends_dict,
                            prepends=prepends_dict,
                            leet=mangler_core.learned_leet,
                            source_file=leak_path,
                            base_word_transforms=base_word_transforms,
                            ml_model="streaming_counter"
                        )
                        
                        logging.info(f"[ML] Successfully saved patterns to cache: {cache_hash}")
                        logging.info(f"[ML] Use 'python3 ml_query.py --cache {cache_hash}' to query patterns")
                        
                    except Exception as e:
                        logging.error(f"[ML] Failed to save patterns to cache: {e}")
                        import traceback
                        traceback.print_exc()
                
                if _shutdown_requested:
                    logging.warning("[ML] Analysis interrupted but partial results were saved to cache")
                    return False
                
            except Exception as e:
                logging.error(f"[ML] Analysis failed: {e}")
                import traceback
                traceback.print_exc()
    
    # Check for shutdown before continuing
    if _shutdown_requested:
        logging.warning("[Main] Shutdown requested. Exiting before main processing.")
        return False
    
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
    
    # Check for shutdown
    if _shutdown_requested:
        logging.warning("[Main] Shutdown requested before processing base words")
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
                        # Check for shutdown
                        if _shutdown_requested:
                            logging.warning("[Main] Shutdown requested during word processing. Saving partial results...")
                            break
                        
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
        
        # Step 6: Deduplicate and sort (even if interrupted, save what we have)
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
        
        if _shutdown_requested:
            logging.warning("[Main] Processing interrupted but partial results were saved")
            return False
        
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