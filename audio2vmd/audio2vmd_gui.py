#=======================================
# audio2vmd_gui version 1
# Simple GUI for audio2vmd.py
#=======================================
# By Elise Windbloom

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml
import os
import subprocess
import threading
import queue
import sys
from collections import OrderedDict

AUDIO2VMD_FILENAME = "audio2vmd.py" #change this to the exe file if you're planning it to used the exe file.

class CommentedConfig(OrderedDict):
    def __init__(self, *args, **kwargs):
        self.comments = {}
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, tuple) and len(value) == 2:
                self[key] = value[0]
                self.comments[key] = value[1]

    def __setitem__(self, key, value):
        if isinstance(value, tuple) and len(value) == 2:
            super().__setitem__(key, value[0])
            self.comments[key] = value[1]
        else:
            super().__setitem__(key, value)

    def items(self):
        for key in self:
            yield key, (self[key], self.comments.get(key, ''))

class Audio2VMDGui:
    DEFAULT_CONFIG = CommentedConfig({
        'a_weight_multiplier': (1.2, "Intensity of the 'あ' (A) sound. Increase to make mouth generally open bigger."),
        'i_weight_multiplier': (0.8, "Intensity of the 'い' (I) sound. Increase to get general extra width mouth when talking."),
        'o_weight_multiplier': (1.1, "Intensity of the 'お' (O) sound. Increase to get more of a general wide medium circle shape."),
        'u_weight_multiplier': (0.9, "Intensity of the 'う' (U) sound. Increase to get more general small circle-shaped mouth."),
        'max_duration': (300, "Maximum duration for splitting audio in seconds. Set to 0 to disable splitting."),
        'optimize_vmd': (True, "Automatically optimize the VMD file True, highly recommended to keep this true.")
    })

    def __init__(self, master):
        self.a_weight_multiplier_entry = tk.Entry(master)
        self.i_weight_multiplier_entry = tk.Entry(master)
        self.o_weight_multiplier_entry = tk.Entry(master)
        self.u_weight_multiplier_entry = tk.Entry(master)
        self.max_duration_entry = tk.Entry(master)
        self.optimize_vmd_var = tk.BooleanVar()
        self.master = master
        master.title("Audio2VMD GUI")
        master.geometry("600x600")

        # Set the window icon
        icon_path = os.path.join(os.getcwd(), "icon.ico")
        master.iconbitmap(icon_path)

        self.config = self.load_config()

        # Create and set up the notebook (tabbed interface)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create tabs
        self.files_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.files_frame, text='Files')
        self.notebook.add(self.settings_frame, text='Settings')

        # Set Files tab as the default
        self.notebook.select(self.files_frame)

        self.create_files_widgets()
        self.create_settings_widgets()

        # Create a queue for inter-thread communication
        self.queue = queue.Queue()

        # Flag to track if processing is ongoing
        self.processing = False

    def create_settings_widgets(self):
        # Settings
        settings = [
            ('a_weight_multiplier', 'A Weight Multiplier'),
            ('i_weight_multiplier', 'I Weight Multiplier'),
            ('o_weight_multiplier', 'O Weight Multiplier'),
            ('u_weight_multiplier', 'U Weight Multiplier'),
            ('max_duration', 'Max Duration'),
        ]

        for i, (key, label) in enumerate(settings):
            ttk.Label(self.settings_frame, text=label).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(self.settings_frame)
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            entry.insert(0, str(self.config.get(key, '')))
            setattr(self, f'{key}_entry', entry)

        # Optimize VMD checkbox
        self.optimize_vmd_var = tk.BooleanVar(value=self.config.get('optimize_vmd', True))
        ttk.Checkbutton(self.settings_frame, text='Optimize VMD', variable=self.optimize_vmd_var).grid(row=len(settings), column=0, columnspan=2, sticky='w', padx=5, pady=5)

        # Save button
        ttk.Button(self.settings_frame, text="Save Settings", command=self.save_config).grid(row=len(settings)+1, column=0, columnspan=2, pady=10)

        self.settings_frame.columnconfigure(1, weight=1)

    def create_files_widgets(self):
        # Input files list
        self.files_listbox = tk.Listbox(self.files_frame, width=70, height=10)
        self.files_listbox.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(self.files_frame, orient='vertical', command=self.files_listbox.yview)
        scrollbar.grid(row=0, column=2, sticky='ns')
        self.files_listbox.configure(yscrollcommand=scrollbar.set)

        # Buttons for file operations
        ttk.Button(self.files_frame, text="Add Audio File(s)", command=self.add_files).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Button(self.files_frame, text="Remove Selected", command=self.remove_file).grid(row=1, column=1, padx=5, pady=5, sticky='e')

        # Output directory
        ttk.Label(self.files_frame, text="Output Directory:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.output_dir_entry = ttk.Entry(self.files_frame, width=50)
        self.output_dir_entry.grid(row=3, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.output_dir_entry.insert(0, os.path.join(os.path.dirname(os.getcwd()), "output"))
        ttk.Button(self.files_frame, text="Browse", command=self.browse_output_dir).grid(row=3, column=2, padx=5, pady=5)

        # Run button
        self.run_button = ttk.Button(self.files_frame, text="Run", command=self.run_audio2vmd)
        self.run_button.grid(row=4, column=0, columnspan=3, pady=10)

        # Output text widget
        self.output_text = tk.Text(self.files_frame, wrap=tk.WORD, bg="black", fg="white", height=10)
        self.output_text.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

        # Scrollbar for the output text
        output_scrollbar = ttk.Scrollbar(self.files_frame, orient='vertical', command=self.output_text.yview)
        output_scrollbar.grid(row=5, column=3, sticky='ns')
        self.output_text.configure(yscrollcommand=output_scrollbar.set)

        self.files_frame.columnconfigure(0, weight=1)
        self.files_frame.rowconfigure(5, weight=1)

    def load_config(self):
        config_path = 'config.yaml'

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                if loaded_config is None:
                    print("Warning: Configuration file is empty or invalid. Using default configuration.")
                    return self.DEFAULT_CONFIG
                return loaded_config
            except Exception as e:
                print(f"Error reading config file: {e}")
                print("Creating new config file with default settings.")
                self.save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG
        else:
            print("Config file not found. Creating new one with default settings.")
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
        
    def save_config(self, config=None):
        if config is None:
            config = CommentedConfig()
            for key, (default_value, comment) in self.DEFAULT_CONFIG.items():
                entry_widget = self.__dict__.get(f"{key}_entry")
                var_widget = self.__dict__.get(f"{key}_var")
                
                if isinstance(entry_widget, tk.Entry):
                    value = entry_widget.get()
                    if isinstance(default_value, int):
                        value = int(value)
                    elif isinstance(default_value, float):
                        value = float(value)
                elif isinstance(var_widget, tk.BooleanVar):
                    value = var_widget.get()
                else:
                    value = default_value  # Fallback in case of unexpected type

                config[key] = (value, comment)

        with open('config.yaml', 'w', encoding='utf-8') as f:
            f.write("# Configuration file for audio2vmd\n")
            f.write("# Adjust these values to fine-tune the lip sync:\n\n")
            for key, (value, comment) in config.items():
                f.write(f"{key}: {value}  # {comment}\n")

        messagebox.showinfo("Info", "Settings saved successfully!")

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio files", "*.mp3 *.wav *.mp4 *.mkv *.aac *.flac *.ogg *.wma *.m4a *.alac *.aiff *.pcm *.aa3 *.aax *.ac3 *.dts *.amr *.opus")])
        existing_files = self.files_listbox.get(0, tk.END)
        for file in files:
            if file not in existing_files:
                self.files_listbox.insert(tk.END, file)

    def remove_file(self):
        try:
            index = self.files_listbox.curselection()[0]
            self.files_listbox.delete(index)
        except IndexError:
            pass


    def browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)

    def run_audio2vmd(self):
        input_files = self.files_listbox.get(0, tk.END)
        output_dir = self.output_dir_entry.get()

        if not input_files:
            messagebox.showerror("Error", "No input files selected!")
            return

        if not output_dir:
            messagebox.showerror("Error", "No output directory specified!")
            return

        output_dir = os.path.normpath(output_dir)
        self.output_dir_entry.delete(0, tk.END)
        self.output_dir_entry.insert(0, output_dir)
        if not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Invalid output directory!")
            return

        # Clear the output text widget
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Starting audio2vmd and loading first audio file now...\n")
        self.output_text.see(tk.END)

        # Disable the Run button
        self.run_button.config(state='disabled')
        self.processing = True

        # Start the processing in a separate thread
        threading.Thread(target=self.process_files, args=(input_files, output_dir), daemon=True).start()

        # Start checking the queue for output
        self.master.after(100, self.check_queue)

    def process_files(self, input_files, output_dir):
        activate_cmd = r"call venv\Scripts\activate.bat"
        python_cmd = "python " + AUDIO2VMD_FILENAME

        # Join all input files into a single string with each file path quoted
        input_files_str = ' '.join([f'"{file}"' for file in input_files])
        full_cmd = f'{activate_cmd} && {python_cmd} {input_files_str} --output "{output_dir}"'

        process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True, shell=True)

        for line in iter(process.stdout.readline, ''):
            if not line.startswith("INFO:spleeter:File"):
                self.queue.put(line)
        for line in iter(process.stderr.readline, ''):
            if not line.startswith("INFO:spleeter:File"):
                self.queue.put(f"ERROR: {line}")

        process.wait()

        self.queue.put("DONE")


    def process_files_by_looping(self, input_files, output_dir):
        #alternate way to use audio2vmd, this doesn't use audio2vmd's build in restarting ablity
        #note using this way won't give you the total time taken for all files
        activate_cmd = r"call venv\Scripts\activate.bat"
        python_cmd = "python " + AUDIO2VMD_FILENAME

        for file in input_files:
            quoted_file = f'"{file}"'
            full_cmd = f"{activate_cmd} && {python_cmd} {quoted_file} --output {output_dir}"
            process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True, shell=True)

            for line in iter(process.stdout.readline, ''):
                if not line.startswith("INFO:spleeter:File"):
                    self.queue.put(line)
            for line in iter(process.stderr.readline, ''):
                if not line.startswith("INFO:spleeter:File"):
                    self.queue.put(f"ERROR: {line}")

            process.wait()

        self.queue.put("DONE")


    def check_queue(self):
        try:
            while True:
                line = self.queue.get_nowait()
                if line == "DONE":
                    self.processing = False
                    self.run_button.config(state='normal')
                else:
                    self.output_text.insert(tk.END, line)
                    self.output_text.see(tk.END)
        except queue.Empty:
            if self.processing:
                self.master.after(100, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = Audio2VMDGui(root)
    root.mainloop()
