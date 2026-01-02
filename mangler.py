#!/usr/bin/env python3
"""
Ultimate Password Mangler 2026 - ML Enhanced
Refactored and optimized for performance and maintainability.

This tool generates advanced password variations for authorized security testing.
"""

import argparse
import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import logging
import threading
import queue

# Import refactored modules
import mangler_core
import mangler_ml
import mangler_hashcat
import mangler_process

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
        self.root.title("Ultimate Password Mangler 2026 - ML Enhanced (Refactored)")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.leak_file = tk.StringVar()
        self.ruleset = tk.StringVar(value="advanced")
        self.threads = tk.IntVar(value=os.cpu_count() or 8)
        self.max_vars = tk.IntVar(value=1000)
        self.targeted = tk.BooleanVar()
        self.hashcat_rules = tk.BooleanVar()

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
            text="🔐 Password Mangler - Best-in-Class Transformations",
            font=("Helvetica", 14, "bold")
        )
        title_label.pack()

        # Settings
        controls = ttk.LabelFrame(main_frame, text="⚙️ Configuration", padding="10")
        controls.pack(fill="x", pady=10)

        row = 0
        ttk.Label(controls, text="Input Wordlist:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.input_file, width=65).grid(row=row, column=1, pady=5, columnspan=2)
        ttk.Button(controls, text="Browse", command=self.browse_input).grid(row=row, column=3, padx=5)

        row += 1
        ttk.Label(controls, text="Leak File for ML:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.leak_file, width=65).grid(row=row, column=1, pady=5, columnspan=2)
        ttk.Button(controls, text="Browse", command=self.browse_leak).grid(row=row, column=3, padx=5)
        
        row += 1
        ttk.Label(controls, text="(Optional - ML learns from leaked passwords)", 
                 foreground="gray", font=("Helvetica", 8)).grid(row=row, column=1, sticky="w")

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
            controls, text="🎯 Targeted Profiling Mode", 
            variable=self.targeted
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(
            controls, text="⚡ Generate Hashcat Rules Only", 
            variable=self.hashcat_rules
        ).grid(row=row, column=2, columnspan=2, sticky="w", pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.start_btn = ttk.Button(
            btn_frame, text="▶️ Start Mangling", 
            command=self.start_task,
            width=20
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ttk.Button(
            btn_frame, text="⏹️ Stop", 
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
            main_frame, text="🔍 Real-Time Preview (sample variations)", 
            padding="10"
        )
        preview_frame.pack(fill="both", expand=True, pady=10)
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame, height=12, font=("Consolas", 9)
        )
        self.preview_text.pack(fill="both", expand=True)

        # Log
        log_frame = ttk.LabelFrame(main_frame, text="📋 Log Output", padding="10")
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

        # Add the handler
        gui_handler = GUIHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(gui_handler)

    def browse_input(self):
        file = filedialog.askopenfilename(
            title="Select Input Wordlist",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file:
            self.input_file.set(file)

    def browse_leak(self):
        file = filedialog.askopenfilename(
            title="Select Leak File for ML",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file:
            self.leak_file.set(file)

    def browse_output(self):
        file = filedialog.asksaveasfilename(
            title="Save Output As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
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
                messagebox.showerror("Error", "Select output file.")
                return

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
            # Callback for progress updates
            def progress_callback(msg_type, content):
                self.task_queue.put((msg_type, content))

            # Get parameters
            leak = self.leak_file.get() if self.leak_file.get() else None
            
            # Preview mode for GUI
            if not self.hashcat_rules.get() and not self.stop_event.is_set():
                # Generate preview samples
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
                
                # Generate preview
                preview_samples = []
                for word in base_words[:3]:
                    if self.stop_event.is_set():
                        break
                    variations = list(mangler_core.generate_variations(
                        word, self.ruleset.get(), max_per_word=20
                    ))
                    for v in variations[:15]:
                        preview_samples.append(f"{word} → {v}")
                
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
                leak_file=leak,
                progress_callback=progress_callback
            )

            if success and not self.stop_event.is_set():
                self.task_queue.put(("done", "✅ Mangling complete! Check your output file."))
            elif self.stop_event.is_set():
                self.task_queue.put(("error", "⚠️ Processing stopped by user"))
            else:
                self.task_queue.put(("error", "❌ Processing failed"))

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
                    
                elif typ == "progress":
                    if self.progress["maximum"] > 0:
                        self.progress["value"] = (content / self.progress["maximum"]) * 100
                        
                elif typ == "progress_max":
                    self.progress["maximum"] = content
                    self.progress["value"] = 0
                    
                elif typ == "preview":
                    self.preview_text.delete(1.0, tk.END)
                    self.preview_text.insert(tk.END, content)
                    self.preview_text.see(tk.END)
                    
                elif typ == "done":
                    self.status_label.config(text="✅ Completed!", foreground="green")
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.progress["value"] = 100
                    messagebox.showinfo("Success", content)
                    return
                    
                elif typ == "error":
                    self.status_label.config(text="❌ Error", foreground="red")
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
    """Main entry point for CLI and GUI modes."""
    parser = argparse.ArgumentParser(
        description="Ultimate Password Mangler 2026 with ML Rule Induction - Best-in-Class Transformations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate wordlist from input file
  %(prog)s -i wordlist.txt -o output.txt --rules advanced
  
  # Use ML learning from leaked passwords
  %(prog)s -i wordlist.txt -o output.txt --leak-file leaked.txt
  
  # Targeted profiling mode
  %(prog)s -o output.txt --targeted
  
  # Generate Hashcat rules
  %(prog)s -o rules.txt --hashcat-rules
  
  # Launch GUI
  %(prog)s --gui
        """
    )
    
    parser.add_argument("-i", "--input", help="Input base wordlist file")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("--rules", choices=["simple", "advanced", "extreme"], 
                       default="advanced", help="Mangling ruleset complexity (default: advanced)")
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 8,
                       help=f"Number of worker threads (default: {os.cpu_count() or 8})")
    parser.add_argument("--max-variations", type=int, default=1000,
                       help="Maximum variations per word (default: 1000)")
    parser.add_argument("--targeted", action="store_true",
                       help="Use interactive profiling for personalized wordlist")
    parser.add_argument("--hashcat-rules", action="store_true",
                       help="Generate Hashcat rules instead of wordlist")
    parser.add_argument("--leak-file", help="Password leak file for ML-based rule learning")
    parser.add_argument("--gui", action="store_true", help="Launch graphical user interface")
    
    args = parser.parse_args()

    # GUI mode
    if args.gui:
        logging.info("Starting GUI mode...")
        root = tk.Tk()
        app = ManglerGUI(root)
        root.mainloop()
        return

    # CLI mode
    try:
        logging.info("=" * 70)
        logging.info("🔐 Ultimate Password Mangler 2026 - ML Enhanced")
        logging.info("=" * 70)
        
        success = mangler_process.parse_file(
            input_file=args.input,
            output_file=args.output,
            ruleset=args.rules,
            threads=args.threads,
            max_variations=args.max_variations,
            targeted=args.targeted,
            hashcat_rules=args.hashcat_rules,
            leak_file=args.leak_file
        )
        
        if success:
            logging.info("=" * 70)
            logging.info("✅ SUCCESS! Operation completed successfully")
            logging.info("=" * 70)
            sys.exit(0)
        else:
            logging.error("=" * 70)
            logging.error("❌ FAILED! Operation did not complete successfully")
            logging.error("=" * 70)
            sys.exit(1)
            
    except KeyboardInterrupt:
        logging.warning("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()