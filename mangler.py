import argparse
import os
import sys
import tempfile
import subprocess
import itertools
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging
from collections import Counter
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cluster import KMeans
import threading
import queue

# ===========================
# ETHICAL WARNING & LOGGING
# ===========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.warning("This tool is for authorized penetration testing and security research only. Unauthorized use is illegal.")

# ===========================
# CONFIGURABLE RULES (BASE + ENHANCED BY ML)
# ===========================
leet_mappings = {
    "a": ["4", "@", "/\\", "/-\\", "^"],
    "b": ["8", "13", "|3"],
    "e": ["3", "&"],
    "i": ["1", "!", "|"],
    "o": ["0", "()"],
    "s": ["5", "$"],
    "t": ["7", "+"],
    "g": ["9"],
    "l": ["1", "|"],
}

common_suffixes = [
    "123", "1234", "12345", "123456", "123456789", "!", "!!", "@", "#", "$",
    "2024", "2025", "2026", "2027", "24", "25", "26", "27",
    "qwerty", "admin", "password", "letmein"
]

keyboard_walks = [
    "qwerty", "qwert", "asdfg", "zxcvb", "qazwsx", "1qaz2wsx", "123456"
]

special_chars = "!@#$%^&*()-_=+[]{}|;:,'\".<>?/\\`~"

current_year = datetime.now().year
years = [str(y) for y in range(current_year - 20, current_year + 5)] + \
        [str(y)[-2:] for y in range(current_year - 20, current_year + 5)]

learned_appends = []
learned_leet = {}
learned_weights = {}

# ===========================
# ML-BASED RULE INDUCTION
# ===========================
def analyze_leak_with_ml(leak_file, sample_size=50000):
    logging.info(f"[ML] Analyzing leak file: {leak_file} (sample: {sample_size})")
    passwords = []
    try:
        with open(leak_file, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                pwd = line.strip()
                if 6 <= len(pwd) <= 30:
                    passwords.append(pwd.lower())
    except Exception as e:
        logging.error(f"[ML] Could not read leak file: {e}")
        return

    if len(passwords) < 100:
        logging.warning("[ML] Not enough passwords for analysis.")
        return

    global learned_appends, learned_leet, learned_weights
    append_lengths = [1, 2, 3, 4, 5, 6]
    append_counter = Counter()

    for pwd in passwords:
        for length in append_lengths:
            if len(pwd) > length:
                suffix = pwd[-length:]
                prefix = pwd[:length]
                if suffix.isdigit() or any(c in suffix for c in "!@#$%"):
                    append_counter[suffix] += 1
                if prefix.isdigit() or any(c in prefix for c in "!@#$%"):
                    append_counter[prefix] += 1

    top_appends = [item[0] for item in append_counter.most_common(50)]
    learned_appends.extend([a for a in top_appends if a not in common_suffixes])
    logging.info(f"[ML] Learned {len(learned_appends)} new appends")

    vectorizer = CountVectorizer(analyzer='char', ngram_range=(2, 3), lowercase=True)
    try:
        X = vectorizer.fit_transform(passwords[:10000])
        features = vectorizer.get_feature_names_out()
        kmeans = KMeans(n_clusters=20, random_state=42, n_init=10)
        kmeans.fit(X)
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        for i in range(10):
            for ind in order_centroids[i, :10]:
                pattern = features[ind]
                base_char = re.sub(r'[^a-z]', '', pattern)
                leet_char = re.sub(r'[a-z]', '', pattern)
                if len(base_char) == 1 and leet_char:
                    char = base_char[0]
                    if char not in learned_leet:
                        learned_leet[char] = []
                    for lc in set(leet_char):
                        if lc not in learned_leet[char]:
                            learned_leet[char].append(lc)
    except Exception as e:
        logging.warning(f"[ML] Clustering skipped: {e}")

    total = len(passwords)
    for append in top_appends:
        learned_weights[f"append_{append}"] = append_counter[append] / total

    logging.info(f"[ML] Rule induction complete!")

# ===========================
# MANGLE FUNCTIONS
# ===========================
def apply_casing(word):
    yield word
    yield word.lower()
    yield word.upper()
    yield word.capitalize()
    yield word.swapcase()

def apply_leet(word, max_depth=3):
    mappings = {**leet_mappings, **learned_leet}
    positions = [(i, c.lower()) for i, c in enumerate(word) if c.lower() in mappings]
    if not positions:
        yield word
        return
    for r in range(1, min(max_depth + 1, len(positions) + 1)):
        for combo in itertools.combinations(positions, r):
            for repls in itertools.product(*[mappings[c] for _, c in combo]):
                variant = list(word)
                for (idx, _), repl in zip(combo, repls):
                    variant[idx] = repl.upper() if word[idx].isupper() else repl
                yield "".join(variant)

def apply_phonetic(word):
    w = word.lower()
    replacements = {
        "love": ["luv", "<3", "lv"],
        "you": ["u", "yu"],
        "ate": ["8", "eat"],
        "for": ["4"],
        "to": ["2"],
        "great": ["gr8"],
        "forever": ["4ever"]
    }
    for key, repls in replacements.items():
        if key in w:
            for repl in repls:
                yield w.replace(key, repl)

def apply_appends(word):
    all_suffixes = common_suffixes + learned_appends + years[:30] + list(special_chars)[:20]
    seen = set()
    for suffix in all_suffixes:
        cand = word + suffix
        if cand not in seen:
            seen.add(cand)
            yield cand
        if len(suffix) <= 3:
            cand2 = word + suffix * 2
            if cand2 not in seen:
                seen.add(cand2)
                yield cand2

def apply_keyboard_walks(word):
    for walk in keyboard_walks:
        yield word + walk
        yield walk + word

def generate_variations(word, ruleset="advanced", max_per_word=1000):
    if not word or not word.strip():
        return

    base = set(apply_casing(word))
    all_variants = set(base)

    if ruleset in ["advanced", "extreme"]:
        for var in base:
            all_variants.update(set(apply_leet(var)))
            all_variants.update(set(apply_appends(var)))
            all_variants.update(set(apply_phonetic(var)))
        if ruleset == "extreme":
            for var in list(base)[:100]:
                all_variants.update(set(apply_keyboard_walks(var)))

    # Force common useful patterns
    for suffix in ["123", "!", "!!", "2026", "26", "2025", "25"]:
        all_variants.add(word + suffix)
        all_variants.add(word.capitalize() + suffix)

    sorted_variants = sorted(all_variants, key=lambda x: (len(x), x))[:max_per_word]

    for v in sorted_variants:
        yield v

# ===========================
# HASHCAT RULES
# ===========================
def generate_hashcat_rules(output_file, ruleset="advanced"):
    rules = ["l", "u", "c", "t"]
    mappings = {**leet_mappings, **learned_leet}
    for char, subs in mappings.items():
        for sub in subs[:4]:
            rules.append(f"s{char}{sub}")
    for suffix in (common_suffixes + learned_appends)[:40]:
        if len(suffix) <= 10:
            rules.append(f"l{suffix}")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(set(rules)))
    logging.info(f"Generated {len(set(rules))} Hashcat rules → {output_file}")

# ===========================
# TARGETED PROFILING
# ===========================
def interactive_profile():
    logging.info("Starting targeted profiling...")
    info = {}
    prompts = [
        ("Full name", "john"),
        ("Nickname", "johnny"),
        ("Birth year", "1990"),
        ("Partner's name", "jane"),
        ("Pet's name", "max"),
        ("Company", "acme")
    ]
    print("\n--- Targeted Profiling ---")
    for p, ex in prompts:
        value = input(f"{p} [{ex}]: ").strip()
        if value:
            info[p.lower().replace(" ", "_")] = value.lower()
    print("---\n")
    return list(info.values())

# ===========================
# FULL PROCESSING (USED BY BOTH CLI AND GUI)
# ===========================
def parse_file(input_file=None, output_file=None, ruleset="advanced", threads=8, max_variations=1000,
               targeted=False, hashcat_rules=False, leak_file=None):
    if leak_file and os.path.exists(leak_file):
        analyze_leak_with_ml(leak_file)

    if hashcat_rules:
        generate_hashcat_rules(output_file, ruleset)
        return

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    base_words = []
    if targeted:
        base_words = interactive_profile()
    else:
        with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
            base_words = [line.strip() for line in f if line.strip()]

    if not base_words:
        logging.warning("No base words to process.")
        return

    temp_filename = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False).name

    try:
        with open(temp_filename, "w", encoding="utf-8") as temp_file:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                tasks = [(w, ruleset, max_variations) for w in base_words]
                futures = [executor.submit(process_word, task) for task in tasks]

                with tqdm(total=len(tasks), desc="Mangling (ML-Enhanced)", unit="word") as pbar:
                    for future in as_completed(futures):
                        for variant in future.result():
                            temp_file.write(variant + "\n")
                        pbar.update(1)

        logging.info("Deduplicating and sorting...")
        subprocess.run(["sort", "-u", temp_filename, "-o", output_file], check=True)
        logging.info(f"SUCCESS! Output saved: {output_file}")

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

def process_word(args):
    word, ruleset, max_vars = args
    return list(generate_variations(word.strip(), ruleset, max_vars))

# ===========================
# RESPONSIVE GUI WITH REAL-TIME PREVIEW
# ===========================
class ManglerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate Password Mangler 2026 - ML Enhanced")
        self.root.geometry("900x750")
        self.root.minsize(800, 600)

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

        # Settings (same as before)
        controls = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        controls.pack(fill="x", pady=10)

        row = 0
        ttk.Label(controls, text="Input Wordlist:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.input_file, width=60).grid(row=row, column=1, pady=5)
        ttk.Button(controls, text="Browse", command=self.browse_input).grid(row=row, column=2, padx=5)

        row += 1
        ttk.Label(controls, text="Leak File for ML Rules:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.leak_file, width=60).grid(row=row, column=1, pady=5)
        ttk.Button(controls, text="Browse", command=self.browse_leak).grid(row=row, column=2, padx=5)
        ttk.Label(controls, text="(Optional - greatly improves quality)", foreground="gray").grid(row=row+1, column=1, sticky="w")

        row += 2
        ttk.Label(controls, text="Output File:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.output_file, width=60).grid(row=row, column=1, pady=5)
        ttk.Button(controls, text="Save As", command=self.browse_output).grid(row=row, column=2, padx=5)

        row += 1
        ttk.Label(controls, text="Ruleset:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Combobox(controls, textvariable=self.ruleset, values=["simple", "advanced", "extreme"], state="readonly").grid(row=row, column=1, sticky="w")

        ttk.Label(controls, text="Threads:").grid(row=row, column=2, sticky="w", padx=20)
        ttk.Spinbox(controls, from_=1, to=os.cpu_count() or 32, textvariable=self.threads, width=8).grid(row=row, column=3, sticky="w")

        row += 1
        ttk.Label(controls, text="Max Variations per Word:").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(controls, textvariable=self.max_vars, width=15).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Checkbutton(controls, text="Targeted Profiling Mode", variable=self.targeted).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(controls, text="Generate Hashcat Rules Only", variable=self.hashcat_rules).grid(row=row, column=2, columnspan=2, sticky="w", pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        self.start_btn = ttk.Button(btn_frame, text="Start Mangling", command=self.start_task)
        self.start_btn.pack(side="left", padx=10)
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_task, state="disabled")
        self.stop_btn.pack(side="left", padx=10)

        # Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=5)
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="green", font=("Helvetica", 11, "bold"))
        self.status_label.pack(side="left")
        self.progress = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress.pack(side="right", fill="x", expand=True, padx=10)

        # Preview
        preview_frame = ttk.LabelFrame(main_frame, text="Real-Time Preview (sample variations)", padding="10")
        preview_frame.pack(fill="both", expand=True, pady=10)
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=15, font=("Consolas", 10))
        self.preview_text.pack(fill="both", expand=True)

        # Log
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.pack(fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # === FIXED: Custom logging handler with reference to log_text ===
        class GUIHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert(tk.END, msg + "\n")
                self.text_widget.see(tk.END)

        # Add the handler using the correct widget reference
        logging.getLogger().addHandler(GUIHandler(self.log_text))

    def browse_input(self):
        file = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file: self.input_file.set(file)

    def browse_leak(self):
        file = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file: self.leak_file.set(file)

    def browse_output(self):
        file = filedialog.asksaveasfilename(defaultextension=".txt")
        if file: self.output_file.set(file)

    def start_task(self):
        try:
            if self.targeted.get() and self.input_file.get():
                messagebox.showerror("Error", "Cannot use targeted mode with input file.")
                return
            if not self.targeted.get() and not self.input_file.get() and not self.hashcat_rules.get():
                messagebox.showerror("Error", "Provide input or enable targeted/hashcat mode.")
                return
            if not self.output_file.get():
                messagebox.showerror("Error", "Select output file.")
                return

            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.stop_event.clear()
            self.preview_text.delete(1.0, tk.END)
            self.log_text.delete(1.0, tk.END)
            self.status_label.config(text="Starting...", foreground="blue")
            self.progress["value"] = 0

            threading.Thread(target=self.run_mangling, daemon=True).start()
            self.root.after(100, self.check_queue)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_task(self):
        self.stop_event.set()
        self.status_label.config(text="Stopping...", foreground="orange")

    def run_mangling(self):
        try:
            leak = self.leak_file.get() if self.leak_file.get() else None
            if leak and os.path.exists(leak):
                self.task_queue.put(("log", "[ML] Starting leak analysis..."))
                analyze_leak_with_ml(leak)
                self.task_queue.put(("log", "[ML] Analysis complete!"))

            if self.hashcat_rules.get():
                self.task_queue.put(("status", "Generating Hashcat rules..."))
                generate_hashcat_rules(self.output_file.get(), self.ruleset.get())
                self.task_queue.put(("done", "Hashcat rules generated!"))
                return

            base_words = []
            if self.targeted.get():
                self.task_queue.put(("log", "Targeted mode active"))
                base_words = interactive_profile()
            else:
                with open(self.input_file.get(), "r", encoding="utf-8", errors="ignore") as f:
                    base_words = [line.strip() for line in f if line.strip()]

            total = len(base_words)
            if total == 0:
                self.task_queue.put(("error", "No words to process"))
                return

            self.task_queue.put(("progress_max", total))

            preview_samples = []
            processed = 0
            for word in base_words:
                if self.stop_event.is_set():
                    break
                variations = list(generate_variations(word, self.ruleset.get(), self.max_vars.get()))
                processed += 1
                self.task_queue.put(("progress", processed))
                if variations:
                    sample = variations[:15]
                    preview_samples.extend([f"{word} → {v}" for v in sample])
                if len(preview_samples) > 300:
                    preview_samples = preview_samples[-300:]
                self.task_queue.put(("preview", "\n".join(preview_samples)))

            # Full processing
            parse_file(
                input_file=self.input_file.get() if not self.targeted.get() else None,
                output_file=self.output_file.get(),
                ruleset=self.ruleset.get(),
                threads=self.threads.get(),
                max_variations=self.max_vars.get(),
                targeted=self.targeted.get(),
                hashcat_rules=False,
                leak_file=leak
            )
            self.task_queue.put(("done", "Mangling complete! Check your output file."))

        except Exception as e:
            self.task_queue.put(("error", str(e)))

    def check_queue(self):
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
                    self.progress["value"] = (content / self.progress["maximum"]) * 100 if self.progress["maximum"] > 0 else 0
                elif typ == "progress_max":
                    self.progress["maximum"] = content
                    self.progress["value"] = 0
                elif typ == "preview":
                    self.preview_text.delete(1.0, tk.END)
                    self.preview_text.insert(tk.END, content)
                elif typ == "done":
                    self.status_label.config(text="Completed!", foreground="green")
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
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
# MAIN
# ===========================
def main():
    parser = argparse.ArgumentParser(description="Ultimate Password Mangler 2026 with ML Rule Induction")
    parser.add_argument("-i", "--input", help="Input base wordlist")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument("--rules", choices=["simple", "advanced", "extreme"], default="advanced")
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 8)
    parser.add_argument("--max-variations", type=int, default=1000)
    parser.add_argument("--targeted", action="store_true")
    parser.add_argument("--hashcat-rules", action="store_true")
    parser.add_argument("--leak-file", help="Password leak for ML-based rule learning")
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if args.gui:
        root = tk.Tk()
        app = ManglerGUI(root)
        root.mainloop()
        return

    try:
        parse_file(
            input_file=args.input,
            output_file=args.output,
            ruleset=args.rules,
            threads=args.threads,
            max_variations=args.max_variations,
            targeted=args.targeted,
            hashcat_rules=args.hashcat_rules,
            leak_file=args.leak_file
        )
    except Exception as e:
        logging.error(f"Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()