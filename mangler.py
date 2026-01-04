#!/usr/bin/env python3
"""
Password Mangler 2026 - ML Enhanced
Refactored and optimized for performance and maintainability.

This tool generates advanced password variations for authorized security testing.
"""

import argparse
import os
import sys
import logging
import threading
import queue

# Try to import tkinter (optional for GUI mode)
try:
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox, scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Import refactored modules
import mangler_core
import mangler_ml
import mangler_hashcat
import mangler_process
import mangler_analyzer
import mangler_mask
import mangler_policy
import mangler_ml_query
import mangler_reports

# ===========================
# ETHICAL WARNING & LOGGING
# ===========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.warning("⚠️  This tool is for authorized penetration testing and security research only. Unauthorized use is illegal.")


# ===========================
# RESPONSIVE GUI WITH REAL-TIME PREVIEW
# ===========================
class ManglerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Password Mangler 2026 - ML Enhanced")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.leak_path = tk.StringVar()  # Unified: file or directory
        self.ruleset = tk.StringVar(value="advanced")
        self.threads = tk.IntVar(value=os.cpu_count() or 8)
        self.max_vars = tk.IntVar(value=1000)
        self.targeted = tk.BooleanVar()
        self.hashcat_rules = tk.BooleanVar(value=True)
        self.leak_is_directory = tk.BooleanVar(value=False)  # Toggle for directory selection

        self.task_queue = queue.Queue()
        self.stop_event = threading.Event()

        # Main frame
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=5)
        title_label = ttk.Label(
            title_frame, 
            text="Password Mangler 2026",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack()

        # Settings
        controls = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        controls.pack(fill="x", pady=10)

        row = 0
        ttk.Label(controls, text="Input Wordlist:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.input_file, width=65).grid(row=row, column=1, pady=5, columnspan=2)
        ttk.Button(controls, text="Browse", command=self.browse_input).grid(row=row, column=3, padx=5)

        row += 1
        ttk.Label(controls, text="ML Leak Source:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.leak_path, width=65).grid(row=row, column=1, pady=5, columnspan=2)
        ttk.Button(controls, text="Browse", command=self.browse_leak).grid(row=row, column=3, padx=5)

        row += 1
        ttk.Checkbutton(
            controls, 
            text="Select Directory (multiple leak files)", 
            variable=self.leak_is_directory
        ).grid(row=row, column=1, columnspan=2, sticky="w", pady=5)
        row += 1
        ttk.Label(controls, text="(Optional - ML learns from leaked passwords)", 
                 foreground="gray", font=("Helvetica", 8)).grid(row=row, column=1, sticky="w", pady=(0,10))

        row += 1
        ttk.Label(controls, text="Output File:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.output_file, width=65).grid(row=row, column=1, pady=5, columnspan=2)
        ttk.Button(controls, text="Save As", command=self.browse_output).grid(row=row, column=3, padx=5)

        row += 1
        ttk.Label(controls, text="Ruleset:").grid(row=row, column=0, sticky="w", pady=5)
        ruleset_combo = ttk.Combobox(
            controls, textvariable=self.ruleset, 
            values=["simple", "advanced", "extreme"], 
            state="readonly",
            width=20
        )
        ruleset_combo.grid(row=row, column=1, sticky="w", pady=5)

        ttk.Label(controls, text="Threads:").grid(row=row, column=2, sticky="e", padx=10)
        ttk.Spinbox(
            controls, from_=1, to=os.cpu_count() or 32, 
            textvariable=self.threads, width=10
        ).grid(row=row, column=3, sticky="w")

        row += 1
        ttk.Label(controls, text="Max Variations/Word:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.max_vars, width=20).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Checkbutton(
            controls, text="Targeted Profiling Mode", 
            variable=self.targeted
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(
            controls, text="Generate Hashcat Rules Only", 
            variable=self.hashcat_rules
        ).grid(row=row, column=2, columnspan=2, sticky="w", pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.start_btn = ttk.Button(
            btn_frame, text="Start Mangling", 
            command=self.start_task,
            width=20
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ttk.Button(
            btn_frame, text="Stop", 
            command=self.stop_task, 
            state="disabled",
            width=15
        )
        self.stop_btn.pack(side="left", padx=10)

        # Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=5)
        self.status_label = ttk.Label(
            status_frame, text="Ready", 
            foreground="green", font=("Helvetica", 11, "bold")
        )
        self.status_label.pack(side="left")
        
        self.progress = ttk.Progressbar(
            status_frame, orient="horizontal", mode="determinate"
        )
        self.progress.pack(side="right", fill="x", expand=True, padx=10)

        # Preview
        preview_frame = ttk.LabelFrame(
            main_frame, text="Real-Time Preview (sample variations)", 
            padding="10"
        )
        preview_frame.pack(fill="both", expand=True, pady=10)
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame, height=12, font=("Consolas", 9)
        )
        self.preview_text.pack(fill="both", expand=True)

        # Log
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.pack(fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=10, font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True)

        # Custom logging handler for GUI
        class GUIHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                try:
                    self.text_widget.insert(tk.END, msg + "\n")
                    self.text_widget.see(tk.END)
                except:
                    pass

        gui_handler = GUIHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(gui_handler)

    def browse_input(self):
        file = filedialog.askopenfilename(
            title="Select Input Wordlist",
            filetypes=[["Text Files", "*.txt"], ["All Files", "*.*"]]
        )
        if file:
            self.input_file.set(file)

    def browse_leak(self):
        if self.leak_is_directory.get():
            path = filedialog.askdirectory(
                title="Select Directory Containing Leak Files"
            )
        else:
            path = filedialog.askopenfilename(
                title="Select Leak File for ML",
                filetypes=[["Text Files", "*.txt"], ["All Files", "*.*"]]
            )
        if path:
            self.leak_path.set(path)

    def browse_output(self):
        default_ext = ".rule" if self.hashcat_rules.get() else ".txt"
        file = filedialog.asksaveasfilename(
            title="Save Output As",
            defaultextension=default_ext,
            filetypes=[["Rule Files", "*.rule"], ["Text Files", "*.txt"], ["All Files", "*.*"]]
        )
        if file:
            self.output_file.set(file)

    def start_task(self):
        try:
            # Validation
            if self.targeted.get() and self.input_file.get():
                messagebox.showerror("Error", "Cannot use targeted mode with input file.")
                return
            if not self.targeted.get() and not self.input_file.get() and not self.hashcat_rules.get():
                messagebox.showerror("Error", "Provide input file or enable targeted/hashcat mode.")
                return
            if not self.output_file.get():
                default = "mangled.rule" if self.hashcat_rules.get() else "mangled.txt"
                self.output_file.set(default)

            # UI updates
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.stop_event.clear()
            self.preview_text.delete(1.0, tk.END)
            self.log_text.delete(1.0, tk.END)
            self.status_label.config(text="Starting...", foreground="blue")
            self.progress["value"] = 0

            # Start processing thread
            threading.Thread(target=self.run_mangling, daemon=True).start()
            self.root.after(100, self.check_queue)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            logging.error(f"GUI Error: {e}")

    def stop_task(self):
        self.stop_event.set()
        self.status_label.config(text="Stopping...", foreground="orange")
        logging.warning("User requested stop")

    def run_mangling(self):
        """Background processing thread."""
        try:
            def progress_callback(msg_type, content):
                self.task_queue.put((msg_type, content))

            leak = self.leak_path.get() if self.leak_path.get() else None

            # Preview generation
            if not self.hashcat_rules.get() and not self.stop_event.is_set():
                base_words = []
                if self.targeted.get():
                    self.task_queue.put(("log", "Starting targeted profiling..."))
                    base_words = mangler_process.interactive_profile()
                else:
                    try:
                        with open(self.input_file.get(), "r", encoding="utf-8", errors="ignore") as f:
                            base_words = [line.strip() for i, line in enumerate(f) if i < 5 and line.strip()]
                    except:
                        pass
                
                preview_samples = []
                for word in base_words[:3]:
                    if self.stop_event.is_set():
                        break
                    variations = list(mangler_core.generate_variations(
                        word, self.ruleset.get(), max_per_word=20
                    ))
                    for v in variations[:15]:
                        preview_samples.append(f"{word} --> {v}")
                
                if preview_samples:
                    self.task_queue.put(("preview", "\n".join(preview_samples)))

            # Full processing
            success = mangler_process.parse_file(
                input_file=self.input_file.get() if not self.targeted.get() else None,
                output_file=self.output_file.get(),
                ruleset=self.ruleset.get(),
                threads=self.threads.get(),
                max_variations=self.max_vars.get(),
                targeted=self.targeted.get(),
                hashcat_rules=self.hashcat_rules.get(),
                leak_path=leak,  # Now supports file or directory
                progress_callback=progress_callback
            )

            if success and not self.stop_event.is_set():
                self.task_queue.put(("done", "Mangling complete! Check your output file."))
            elif self.stop_event.is_set():
                self.task_queue.put(("error", "Processing stopped by user"))
            else:
                self.task_queue.put(("error", "Processing failed"))

        except Exception as e:
            logging.error(f"Processing error: {e}")
            self.task_queue.put(("error", f"Error: {str(e)}"))

    def check_queue(self):
        """Check for messages from processing thread."""
        try:
            while True:
                msg = self.task_queue.get_nowait()
                typ, content = msg
                
                if typ == "log":
                    self.log_text.insert(tk.END, content + "\n")
                    self.log_text.see(tk.END)
                    
                elif typ == "status":
                    self.status_label.config(text=content, foreground="blue")
                    
                elif typ == "progress_max":
                    self.progress["maximum"] = content
                    self.progress["value"] = 0
                    
                elif typ == "progress":
                    self.progress["value"] = content
                    
                elif typ == "preview":
                    self.preview_text.delete(1.0, tk.END)
                    self.preview_text.insert(tk.END, content)
                    self.preview_text.see(tk.END)
                    
                elif typ == "done":
                    self.status_label.config(text="Completed!", foreground="green")
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.progress["value"] = 100
                    messagebox.showinfo("Success", content)
                    return
                    
                elif typ == "error":
                    self.status_label.config(text="Error", foreground="red")
                    messagebox.showerror("Error", content)
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    return
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)


# ===========================
# MAIN ENTRY POINT
# ===========================
def main():
    parser = argparse.ArgumentParser(
        description="Password Mangler 2026 with ML Rule Induction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --gui
  %(prog)s -i rockyou.txt -o mangled.txt --leak leaks_dir/ --rules advanced
  %(prog)s -o custom.rules --hashcat-rules --leak single_leak.txt
  %(prog)s --targeted -o personal.txt
        """
    )
    
    parser.add_argument("--gui", action="store_true", help="Launch the graphical user interface")
    parser.add_argument("-i", "--input", help="Input base wordlist file")
    parser.add_argument("-o", "--output", required=False, help="Output file path (required in CLI mode)")
    parser.add_argument("--leak", dest="leak_path", help="Leak file or directory for ML training (optional - enables ML mode)")
    parser.add_argument("--rules", choices=["simple", "advanced", "extreme"], default="advanced")
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 8)
    parser.add_argument("--max-variations", type=int, default=1000)
    parser.add_argument("--targeted", action="store_true")
    parser.add_argument("--hashcat-rules", action="store_true")
    parser.add_argument("--no-cache", action="store_true", help="Disable ML pattern caching")
    parser.add_argument("--enable-clustering", action="store_true", 
                       help="Enable expensive ML clustering analysis (slow, minimal benefit)")
    parser.add_argument("--chunk-size", type=int, default=10000,
                       help="Chunk size for streaming large leak files (default: 10000)")
    parser.add_argument("--analyze", metavar="WORDLIST", 
                       help="Analyze wordlist and generate high-quality Hashcat rules")
    parser.add_argument("--base-dict", metavar="FILE",
                       help="Base dictionary for transformation inference (use with --analyze)")
    parser.add_argument("--max-rules", type=int, default=1000,
                       help="Maximum number of rules to generate (default: 1000)")
    
    # Mask attack options
    parser.add_argument("--mask", metavar="PATTERN",
                       help="Generate passwords from mask (e.g., ?l?l?l?d?d?d)")
    parser.add_argument("--mask-hybrid", metavar="PATTERN",
                       help="Hybrid attack: base words + mask pattern")
    parser.add_argument("--mask-position", choices=['append', 'prepend'], default='append',
                       help="Position for hybrid mask attack")
    parser.add_argument("--estimate-mask", metavar="PATTERN",
                       help="Estimate number of passwords from mask pattern")
    
    # Policy filtering options
    parser.add_argument("--policy", choices=['basic', 'moderate', 'strong', 'enterprise'],
                       help="Apply common password policy filter")
    parser.add_argument("--min-length", type=int,
                       help="Minimum password length")
    parser.add_argument("--max-length", type=int,
                       help="Maximum password length")
    parser.add_argument("--require-lowercase", action="store_true",
                       help="Require at least one lowercase letter")
    parser.add_argument("--require-uppercase", action="store_true",
                       help="Require at least one uppercase letter")
    parser.add_argument("--require-digit", action="store_true",
                       help="Require at least one digit")
    parser.add_argument("--require-special", action="store_true",
                       help="Require at least one special character")
    parser.add_argument("--blacklist", metavar="WORDS",
                       help="Comma-separated list of blacklisted words")
    parser.add_argument("--filter-file", metavar="INPUT",
                       help="Filter existing wordlist file by policy")
    
    # ML query and reuse options
    parser.add_argument("--list-ml-caches", action="store_true",
                       help="List all cached ML patterns")
    parser.add_argument("--query-ml", metavar="WORD",
                       help="Query ML patterns for password suggestions")
    parser.add_argument("--ml-cache-hash", metavar="HASH",
                       help="ML cache hash to use (from --list-ml-caches)")
    parser.add_argument("--generate-from-ml", metavar="WORDLIST",
                       help="Generate passwords from base words using cached ML patterns")
    parser.add_argument("--export-ml-rules", metavar="OUTPUT",
                       help="Export cached ML patterns as Hashcat rules")
    parser.add_argument("--ml-interactive", action="store_true",
                       help="Interactive ML query mode")
    
    # Rule optimization
    parser.add_argument("--optimize-rules", metavar="INPUT",
                       help="Optimize Hashcat rules file (remove redundant rules)")
    parser.add_argument("--test-wordlist", metavar="FILE",
                       help="Test wordlist for rule optimization (optional)")
    
    args = parser.parse_args()

    # Handle rule optimization
    if args.optimize_rules:
        import mangler_rule_optimizer
        
        if not args.output:
            logging.error("Must specify --output for rule optimization")
            sys.exit(1)
        
        logging.info(f"[RuleOptimizer] Optimizing rules from {args.optimize_rules}")
        stats = mangler_rule_optimizer.optimize_rule_file(
            args.optimize_rules,
            args.output,
            test_wordlist=args.test_wordlist
        )
        logging.info(f"[RuleOptimizer] SUCCESS! Reduction: {stats['reduction_percent']}%")
        sys.exit(0)

    if args.list_ml_caches:
        # List all cached ML patterns
        caches = mangler_ml_query.list_cached_ml_patterns()
        
        if not caches:
            logging.info("No ML pattern caches found.")
            logging.info("Run analysis on leak files first with --leak option")
            sys.exit(0)
        
        print("\n" + "="*70)
        print("CACHED ML PATTERNS")
        print("="*70 + "\n")
        
        for cache in caches:
            print(f"Cache Hash: {cache['cache_hash']}")
            print(f"Source: {cache['source_file']}")
            print(f"Cached: {cache['cache_time']}")
            print(f"Model: {cache['ml_model']}")
            print(f"Patterns: {cache['pattern_counts']['appends']} appends, "
                  f"{cache['pattern_counts']['prepends']} prepends, "
                  f"{cache['pattern_counts']['leet']} leet")
            print()
        
        sys.exit(0)
    
    elif args.ml_interactive:
        # Interactive ML query mode
        mangler_ml_query.query_ml_interactive(cache_hash=args.ml_cache_hash)
        sys.exit(0)
    
    elif args.query_ml:
        # Query ML for specific word
        if not args.ml_cache_hash:
            logging.error("Must specify --ml-cache-hash for ML queries")
            logging.info("Use --list-ml-caches to see available caches")
            sys.exit(1)
        
        try:
            patterns = mangler_ml_query.load_ml_patterns(cache_hash=args.ml_cache_hash)
            candidates = mangler_ml_query.generate_from_ml_patterns(
                args.query_ml, patterns, top_n=20
            )
            
            print(f"\nPassword candidates for '{args.query_ml}':")
            print("-" * 60)
            for i, (password, confidence) in enumerate(candidates, 1):
                print(f"  {i:2d}. {password:30s} (confidence: {confidence:.3f})")
            print()
            
            sys.exit(0)
        except Exception as e:
            logging.error(f"ML query failed: {e}")
            sys.exit(1)
    
    elif args.export_ml_rules:
        # Export ML patterns as Hashcat rules
        if not args.ml_cache_hash:
            logging.error("Must specify --ml-cache-hash to export rules")
            logging.info("Use --list-ml-caches to see available caches")
            sys.exit(1)
        
        try:
            patterns = mangler_ml_query.load_ml_patterns(cache_hash=args.ml_cache_hash)
            count = mangler_ml_query.export_patterns_to_hashcat_rules(
                patterns, args.export_ml_rules, max_rules=args.max_rules
            )
            
            if count > 0:
                logging.info(f"SUCCESS! Exported {count} rules to {args.export_ml_rules}")
                sys.exit(0)
            else:
                logging.error("Failed to export rules")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Export failed: {e}")
            sys.exit(1)
    
    elif args.generate_from_ml:
        # Generate wordlist from base words using ML patterns
        if not args.output:
            logging.error("Output file required (-o/--output)")
            sys.exit(1)
        
        if not args.ml_cache_hash:
            logging.error("Must specify --ml-cache-hash to use ML patterns")
            logging.info("Use --list-ml-caches to see available caches")
            sys.exit(1)
        
        try:
            # Load base words
            with open(args.generate_from_ml, 'r', encoding='utf-8', errors='ignore') as f:
                base_words = [line.strip() for line in f if line.strip()]
            
            # Load ML patterns
            patterns = mangler_ml_query.load_ml_patterns(cache_hash=args.ml_cache_hash)
            
            # Generate wordlist
            count = mangler_ml_query.generate_wordlist_from_ml(
                base_words, patterns, args.output,
                top_variations=args.max_variations if args.max_variations != 1000 else 10
            )
            
            if count > 0:
                logging.info(f"SUCCESS! Generated {count} passwords to {args.output}")
                sys.exit(0)
            else:
                logging.error("Generation failed")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Generation failed: {e}")
            sys.exit(1)
    
    elif args.gui:
        if not TKINTER_AVAILABLE:
            logging.error("GUI mode requires tkinter, which is not installed")
            logging.error("Install tkinter: sudo apt-get install python3-tk (Ubuntu/Debian)")
            logging.error("Or run in CLI mode without --gui flag")
            sys.exit(1)
        
        root = tk.Tk()
        ManglerGUI(root)
        root.mainloop()
    
    elif args.estimate_mask:
        # Estimate mask size
        size = mangler_mask.estimate_mask_size(args.estimate_mask)
        logging.info(f"Mask pattern: {args.estimate_mask}")
        logging.info(f"Estimated passwords: {size:,}")
        sys.exit(0)
    
    elif args.mask:
        # Mask attack mode
        if not args.output:
            logging.error("Output file required for mask mode (-o/--output)")
            sys.exit(1)
        
        logging.info(f"Mask attack: {args.mask}")
        count = mangler_mask.generate_mask_file(
            mask=args.mask,
            output_file=args.output,
            max_passwords=args.max_variations if args.max_variations != 1000 else None
        )
        
        if count > 0:
            logging.info(f"SUCCESS! Generated {count:,} passwords")
            sys.exit(0)
        else:
            logging.error("Mask generation failed")
            sys.exit(1)
    
    elif args.filter_file:
        # Policy filtering mode
        if not args.output:
            logging.error("Output file required for filter mode (-o/--output)")
            sys.exit(1)
        
        # Build policy
        if args.policy:
            policy = mangler_policy.create_common_policy(args.policy)
        else:
            policy = mangler_policy.PasswordPolicy(
                min_length=args.min_length or 0,
                max_length=args.max_length or 128,
                require_lowercase=args.require_lowercase,
                require_uppercase=args.require_uppercase,
                require_digit=args.require_digit,
                require_special=args.require_special,
                blacklist_words=args.blacklist.split(',') if args.blacklist else None
            )
        
        count = mangler_policy.filter_file_by_policy(
            input_file=args.filter_file,
            output_file=args.output,
            policy=policy
        )
        
        if count > 0:
            logging.info(f"SUCCESS! Filtered {count:,} passwords")
            sys.exit(0)
        else:
            logging.error("Filtering produced no results")
            sys.exit(1)
    
    elif args.analyze:
        # Analysis mode: generate high-quality rules from wordlist
        if not args.output:
            args.output = args.analyze.replace('.txt', '_optimized.rule')
        
        logging.info(f"Analyzing wordlist: {args.analyze}")
        logging.info(f"Output rules: {args.output}")
        
        result = mangler_analyzer.analyze_and_generate_rules(
            wordlist_file=args.analyze,
            output_file=args.output,
            base_dict_file=args.base_dict,
            max_rules=args.max_rules,
            streaming=True,
            chunk_size=args.chunk_size
        )
        
        if result:
            logging.info(f"SUCCESS! Generated {len(result['rules'])} high-quality rules")
            logging.info(f"Rules written to: {result['rules_file']}")
            logging.info(f"Analysis report: {result['report_file']}")
            sys.exit(0)
        else:
            logging.error("Analysis failed")
            sys.exit(1)
    else:
        if not args.output:
            parser.error("--output is required in CLI mode")
        
        success = mangler_process.parse_file(
            input_file=args.input,
            output_file=args.output,
            ruleset=args.rules,
            threads=args.threads,
            max_variations=args.max_variations,
            targeted=args.targeted,
            hashcat_rules=args.hashcat_rules,
            leak_path=args.leak_path,
            progress_callback=lambda t, c: logging.info(c) if t == "status" else None
        )
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()