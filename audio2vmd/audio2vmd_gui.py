#=======================================
# audio2vmd_gui version 16
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
from collections import OrderedDict
import psutil
from pathlib import Path
import time

AUDIO2VMD_FILENAME = "audio2vmd.py" #change this to the exe file if you're planning it to used the exe file.

def format_time(seconds):
    """Format time in seconds to a human-readable string"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    else:
        minutes, secs = divmod(seconds, 60)
        return f"{int(minutes)} minutes and {secs:.2f} seconds"

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
        'model_name': ("Model", "Name of the model the VMD is for. (max length of 20 characters)"),
        'separate_vocals': ("automatic", "Controls vocal separation behavior: 'automatic' (detect and separate if needed), 'always' (skip detection and always separate), or 'never' (skip detection and assume file is already vocals-only). 'automatic' recommended if any of your files have music/background noise, otherwise 'never' is recommended for a big speed boost."),
        'a_weight_multiplier': (1.2, "Intensity of the 'あ' (A) sound. Increase to make mouth generally open bigger."),
        'i_weight_multiplier': (0.8, "Intensity of the 'い' (I) sound. Increase to get general extra width mouth when talking."),
        'o_weight_multiplier': (1.1, "Intensity of the 'お' (O) sound. Increase to get more of a general wide medium circle shape."),
        'u_weight_multiplier': (0.9, "Intensity of the 'う' (U) sound. Increase to get more general small circle-shaped mouth."),
        'max_duration': (300, "Maximum duration for splitting audio in seconds. Set to 0 to disable splitting."),
        'optimize_vmd': (True, "Automatically optimize the VMD file if True, highly recommended to keep this true."),
        'extras_optimize_vmd_bone_position_tolerance': (0.005, "For Optimizing a VMD (in Extras) with bone position data. Use a tolerance of 0.001 for very high fidelity, but it might not reduce the file size much."),
        'extras_optimize_vmd_bone_rotation_tolerance': (0.005, "For Optimizing a VMD (in Extras) with bone rotation data. Use a tolerance of 0.001 for very high fidelity, but it might not reduce the file size much.")
    })


    def __init__(self, master):
        self.a_weight_multiplier_entry = tk.Entry(master)
        self.i_weight_multiplier_entry = tk.Entry(master)
        self.o_weight_multiplier_entry = tk.Entry(master)
        self.u_weight_multiplier_entry = tk.Entry(master)
        self.max_duration_entry = tk.Entry(master)
        self.optimize_vmd_var = tk.BooleanVar(value=True)  # Set default value to True
        self.separate_vocals_var = tk.StringVar(value="automatic")  # Add variable for separate_vocals
        self.last_optimize_vmd_directory = None #remembers your last given directories for the files
        self.last_input_vmd_directory = None #remembers your last given directories for the files
        self.last_target_vmd_directory = None #remembers your last given directories for the files
        self.master = master
        master.title("Audio2VMD GUI")
        master.geometry("600x600")

        # Set the window icon
        icon_path = os.path.join(os.getcwd(), "icon.ico")
        master.iconbitmap(icon_path)

        self.config = self.load_config()
        
        # Update variables with loaded config values
        self.optimize_vmd_var.set(self.config.get('optimize_vmd', True))
        self.separate_vocals_var.set(self.config.get('separate_vocals', 'automatic'))

        self.process = None

        # Create and set up the notebook (tabbed interface)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create tabs
        self.files_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.extras_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.files_frame, text='Files')
        self.notebook.add(self.settings_frame, text='Settings')
        self.notebook.add(self.extras_frame, text='Extras')

        # Set Files tab as the default
        self.notebook.select(self.files_frame)

        self.create_files_widgets()
        self.create_settings_widgets()
        self.create_extras_widgets()

        # Create a queue for inter-thread communication
        self.queue = queue.Queue()

        # Flag to track if processing is ongoing
        self.processing = False

    def create_tooltip(self, widget, text):
        def enter(event):
            x = y = 0
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=text, justify='left',
                            background="#ffffff", relief='solid', borderwidth=1,
                            wraplength=300)  # Increase wraplength to 300 (or your preferred width)
            label.pack(ipadx=1)
        
        def leave(event):
            if self.tooltip:
                self.tooltip.destroy()
        
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)


    def create_settings_widgets(self):
        # Settings
        settings = [
            ('model_name', 'Model Name'),
            ('separate_vocals', 'Separate Vocals'),
            ('a_weight_multiplier', 'A Weight Multiplier'),
            ('i_weight_multiplier', 'I Weight Multiplier'),
            ('o_weight_multiplier', 'O Weight Multiplier'),
            ('u_weight_multiplier', 'U Weight Multiplier'),
            ('max_duration', 'Max Duration for splitting (in seconds), 0=No splitting'),
            ('optimize_vmd', 'Optimize VMD'),
            ('extras_optimize_vmd_bone_position_tolerance', 'VMD Optimize Position Tolerance'),
            ('extras_optimize_vmd_bone_rotation_tolerance', 'VMD Optimize Rotation Tolerance')
        ]

        for i, (key, label) in enumerate(settings):
            label_widget = ttk.Label(self.settings_frame, text=label)
            label_widget.grid(row=i, column=0, sticky='w', padx=5, pady=5)
            self.create_tooltip(label_widget, self.get_tooltip_text(key))

            if key == 'optimize_vmd':
                checkbox = ttk.Checkbutton(self.settings_frame, variable=self.optimize_vmd_var)
                checkbox.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            elif key == 'separate_vocals':
                widget = ttk.Combobox(self.settings_frame, textvariable=self.separate_vocals_var, 
                                    values=["automatic", "always", "never"], 
                                    state="readonly")
                widget.set(self.config.get('separate_vocals', 'automatic'))
                widget.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            else:
                entry = ttk.Entry(self.settings_frame)
                entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
                entry.insert(0, str(self.config.get(key, '')))
                setattr(self, f'{key}_entry', entry)

        # Save button
        ttk.Button(self.settings_frame, text="Save Settings", command=self.save_config).grid(row=len(settings), column=0, columnspan=2, pady=10)

        self.settings_frame.columnconfigure(1, weight=1)

    def get_tooltip_text(self, key):
        for keytest, (default_value, comment) in self.DEFAULT_CONFIG.items():
            if keytest == key:
                return comment


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
        ttk.Button(self.files_frame, text="Browse", command=lambda: self.browse_output_dir(self.output_dir_entry.get())).grid(row=3, column=2, padx=5, pady=5)

        # Merge lip data into existing VMD
        self.lips_data_frame = ttk.Frame(self.files_frame)
        self.lips_data_frame.grid(row=4, column=0, columnspan=3, sticky='w', padx=5, pady=(15, 0))
        self.lips_data_frame.grid_remove()  # Hide by default

        ttk.Label(self.lips_data_frame, text="Send Lips Data To Replace Existing VMD's Lips Data (Optional):").grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=(15, 0))
        self.send_lips_data_entry = ttk.Entry(self.lips_data_frame, width=50)
        self.send_lips_data_entry.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        ttk.Button(self.lips_data_frame, text="Browse", command=self.browse_send_lips_data).grid(row=1, column=2, padx=5, pady=5)

        # More/Less link
        self.more_link = tk.Label(self.files_frame, text="More...", fg="blue", cursor="hand2")
        #self.more_link.grid(row=5, column=0, columnspan=3, pady=5, sticky='w')
        self.more_link.grid(row=5, column=0, columnspan=3, pady=5, padx=(2, 0), sticky='w')
        self.more_link.bind("<Button-1>", self.toggle_lips_data_frame)

        # Run button
        self.run_button = ttk.Button(self.files_frame, text="Run", command=self.run_audio2vmd)
        self.run_button.grid(row=6, column=0, columnspan=3, pady=20)

        # Output text widget
        self.output_text = tk.Text(self.files_frame, wrap=tk.WORD, bg="black", fg="white", height=10)
        self.output_text.grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

        # Scrollbar for the output text
        output_scrollbar = ttk.Scrollbar(self.files_frame, orient='vertical', command=self.output_text.yview)
        output_scrollbar.grid(row=7, column=3, sticky='ns')
        self.output_text.configure(yscrollcommand=output_scrollbar.set)

        self.files_frame.columnconfigure(0, weight=1)
        self.files_frame.rowconfigure(7, weight=1)

        self.master.geometry("600x730")  # Increased height by 50 pixels

    def create_extras_widgets(self):
        # Center the buttons
        self.extras_frame.columnconfigure(0, weight=1)
        self.extras_frame.columnconfigure(1, weight=1)
        self.extras_frame.columnconfigure(2, weight=1)

        self.optimize_vmd_button = ttk.Button(self.extras_frame, text="Optimize VMD", command=self.optimize_vmd)
        self.optimize_vmd_button.grid(row=0, column=1, padx=5, pady=5)

        self.send_vmd_data_button = ttk.Button(self.extras_frame, text="Send VMD lips data to another VMD", command=self.send_vmd_data)
        self.send_vmd_data_button.grid(row=1, column=1, padx=5, pady=5)

        # Add the output text widget
        self.extras_output_text = tk.Text(self.extras_frame, wrap=tk.WORD, bg="black", fg="white", height=10)
        self.extras_output_text.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')

        # Scrollbar for the output text
        extras_output_scrollbar = ttk.Scrollbar(self.extras_frame, orient='vertical', command=self.extras_output_text.yview)
        extras_output_scrollbar.grid(row=2, column=3, sticky='ns')
        self.extras_output_text.configure(yscrollcommand=extras_output_scrollbar.set)

        self.extras_frame.rowconfigure(2, weight=1)

    def toggle_lips_data_frame(self, event=None):
        if self.lips_data_frame.winfo_ismapped():
            self.lips_data_frame.grid_remove()
            self.more_link.config(text="More...")
        else:
            self.lips_data_frame.grid()
            self.more_link.config(text="Less...")

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
            # Initialize with DEFAULT_CONFIG instead of empty CommentedConfig
            config = CommentedConfig(self.DEFAULT_CONFIG)

        # Copy comments from DEFAULT_CONFIG
        for key, (default_value, comment) in self.DEFAULT_CONFIG.items():
            try:
                if key == 'optimize_vmd':
                    value = self.optimize_vmd_var.get()
                elif key == 'separate_vocals':
                    value = self.separate_vocals_var.get()
                elif hasattr(self, f'{key}_entry'):
                    var_widget = getattr(self, f'{key}_entry')
                    value = var_widget.get() if var_widget.get() != '' else default_value  # Use default if empty
                    if key == 'model_name' and len(value) > 20:
                        messagebox.showerror("Error", "Model Name must be 20 characters or less. Please make the name shorter.")
                        return  # Exit the method without saving
                    if isinstance(default_value, int):
                        value = int(value) if value != '' else default_value
                    elif isinstance(default_value, float):
                        value = float(value) if value != '' else default_value
                else:
                    value = default_value  # Fallback in case of unexpected type

                config[key] = (value, comment)
            except (ValueError, AttributeError) as e:
                messagebox.showerror("Error", f"Invalid value for {key}: {str(e)}")
                return

        with open('config.yaml', 'w', encoding='utf-8') as f:
            f.write("# Configuration file for audio2vmd\n")
            f.write("# Adjust these values to fine-tune the lip sync:\n\n")
            for key, (value, comment) in config.items():
                f.write(f"{key}: {value}  # {comment}\n")

        messagebox.showinfo("Info", "Settings saved successfully!")


    def add_files(self):
        initial_dir = None
        selected_indices = self.files_listbox.curselection()
        
        if selected_indices:
            # Use the directory of the last selected item
            selected_file = self.files_listbox.get(selected_indices[-1])
            initial_dir = os.path.dirname(selected_file)
        elif self.files_listbox.size() > 0:
            # If no selection but list is not empty, use the last item's directory
            last_file = self.files_listbox.get(tk.END)
            initial_dir = os.path.dirname(last_file)
        
        files = filedialog.askopenfilenames(
            filetypes=[("Audio files", "*.mp3 *.wav *.mp4 *.mkv *.aac *.flac *.ogg *.wma *.m4a *.alac *.aiff *.pcm *.aa3 *.aax *.ac3 *.dts *.amr *.opus")],
            initialdir=initial_dir
        )
        
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

    def browse_output_dir(self, initial_dir=None):
        if initial_dir is None:
            initial_dir = self.output_dir_entry.get()
        
        directory = filedialog.askdirectory(
            title="Select an Output Folder to save the files at",
            initialdir=initial_dir
        )
        if directory:
            directory_path = Path(directory)
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, str(directory_path))

    def browse_send_lips_data(self):
        file = filedialog.askopenfilename(title="Select a VMD file that will receive the lips data",filetypes=[("VMD files", "*.vmd")])
        if file:
            file_path = Path(file)
            self.send_lips_data_entry.delete(0, tk.END)
            self.send_lips_data_entry.insert(0, str(file_path))
  
    def run_audio2vmd(self):
        if self.processing:
            # Stop the process
            self.stop_process()
        else:
            input_files = self.files_listbox.get(0, tk.END)
            output_dir = self.output_dir_entry.get()
            send_lips_data_to = self.send_lips_data_entry.get()

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

            # Change the Run button to Force Stop
            self.run_button.config(text="Force Stop")
            self.processing = True

            # Start the processing in a separate thread
            self.process_thread = threading.Thread(target=self.process_files, args=(input_files, output_dir, send_lips_data_to), daemon=True)
            self.process_thread.start()

            # Start checking the queue for output
            self.master.after(100, self.check_queue)

    def optimize_vmd(self):
        initial_dir = self.last_optimize_vmd_directory if self.last_optimize_vmd_directory else None
        input_file = filedialog.askopenfilename(
            title="Select a VMD file to optimize",
            filetypes=[("VMD files", "*.vmd")],
            initialdir=initial_dir
        )
        if input_file:
            self.last_optimize_vmd_directory = os.path.dirname(input_file)
            output_dir = os.path.join(os.path.dirname(input_file), "output")
            #os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"optimized_{os.path.basename(input_file)}")
            self.run_audio2vmd_extras("OPTIMIZE_VMD", input_file, output_file)

    def send_vmd_data(self):
        # Select input VMD file
        initial_input_dir = self.last_input_vmd_directory if self.last_input_vmd_directory else None
        input_file = filedialog.askopenfilename(
            title="Select the input VMD file containing lips data",
            filetypes=[("VMD files", "*.vmd")],
            initialdir=initial_input_dir
        )
        if input_file:
            self.last_input_vmd_directory = os.path.dirname(input_file)

            # Select target VMD file
            initial_target_dir = self.last_target_vmd_directory if self.last_target_vmd_directory else None
            target_file = filedialog.askopenfilename(
                title="Select the target VMD file to receive the lips data",
                filetypes=[("VMD files", "*.vmd")],
                initialdir=initial_target_dir
            )
            if target_file:
                self.last_target_vmd_directory = os.path.dirname(target_file)

                output_dir = os.path.join(os.path.dirname(input_file), "output")
                #os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"merged_{os.path.basename(input_file)}")
                self.run_audio2vmd_extras("REPLACE_LIPS", input_file, output_file, target_file)


    def run_audio2vmd_extras(self, mode, input_file, output_file, target_file=None):
        activate_cmd = str(Path("venv") / "Scripts" / "activate.bat")
        python_cmd = "python"
        audio2vmd_script = AUDIO2VMD_FILENAME

        cmd = [
            "cmd", "/c",
            "call", activate_cmd, "&&",
            python_cmd,
            audio2vmd_script,
            str(Path(input_file)),
            "--extras-mode", mode
        ]

        if target_file:
            target_file_path = str(Path(target_file))
            if target_file_path == ".":
                target_file_path = ""
            cmd.extend(["--send-lips-data-to", target_file_path])

        self.extras_output_text.delete(1.0, tk.END)
        self.extras_output_text.insert(tk.END, f"Running {mode} mode...\n")
        self.extras_output_text.see(tk.END)

        # Disable buttons
        self.optimize_vmd_button.config(state='disabled')
        self.send_vmd_data_button.config(state='disabled')

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW  # This flag prevents the CMD window from appearing
        )
        self.processing = True
        self.master.after(100, self.check_extras_queue)


    def check_extras_queue(self):
        if self.process:
            try:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    self.processing = False
                    # Re-enable buttons
                    self.optimize_vmd_button.config(state='normal')
                    self.send_vmd_data_button.config(state='normal')
                    # Add completion message
                    self.extras_output_text.insert(tk.END, "Process completed.\n")
                    self.extras_output_text.see(tk.END)
                    return
                if output:
                    self.extras_output_text.insert(tk.END, output)
                    self.extras_output_text.see(tk.END)
            except Exception as e:
                self.extras_output_text.insert(tk.END, f"Error: {str(e)}\n")
                self.extras_output_text.see(tk.END)
                self.processing = False
                self.optimize_vmd_button.config(state='normal')
                self.send_vmd_data_button.config(state='normal')
                return
        
        if self.processing:
            self.master.after(100, self.check_extras_queue)
        else:
            # Ensure buttons are re-enabled if process ends unexpectedly
            self.optimize_vmd_button.config(state='normal')
            self.send_vmd_data_button.config(state='normal')

    def stop_process(self):
        if self.processing and self.process:
            self.output_text.insert(tk.END, "Stopping the process...\n")
            self.output_text.see(tk.END)
            
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass  # Process already terminated
            except Exception as e:
                self.output_text.insert(tk.END, f"Error while stopping process: {str(e)}\n")
            
            self.process = None
            self.processing = False
            self.run_button.config(state='normal', text="Run")
            
            self.output_text.insert(tk.END, "Process stopped. (You may need to press \"Run\" twice to start again.)\n")
            self.output_text.see(tk.END)

    def process_files_with_debug_messages(self, input_files, output_dir, send_lips_data_to):
        # Unused, for debugging
        activate_cmd = r"call venv\Scripts\activate.bat"
        python_cmd = "python " + AUDIO2VMD_FILENAME

        start_time = time.time()

        for file in input_files:
            input_file_str = f'"{file}"'
            full_cmd = f'{activate_cmd} && {python_cmd} {input_file_str} --output "{output_dir}"'

            if send_lips_data_to:
                full_cmd += f' --send-lips-data-to "{send_lips_data_to}"'

            full_cmd += f' --show-final-complete-message "False"'

            self.queue.put(f"Processing file: {file}")

            try:
                self.process = subprocess.Popen(
                    full_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace',
                    shell=True
                )

                while self.process:
                    output = self.process.stdout.readline()
                    error = self.process.stderr.readline()

                    if output == '' and error == '' and self.process.poll() is not None:
                        break

                    if output:
                        self.queue.put(output.strip())
                    if error:
                        self.queue.put(f"ERROR: {error.strip()}")

                if self.process:
                    return_code = self.process.wait()
                    if return_code != 0:
                        self.queue.put(f"Process exited with return code {return_code}")
            except Exception as e:
                self.queue.put(f"An error occurred while processing {file}: {str(e)}")
            finally:
                self.process = None

        self.queue.put(f"Complete! All Audio to VMD conversion completed in {format_time(time.time() - start_time)}")
        self.queue.put("DONE")

    def process_files(self, input_files, output_dir, send_lips_data_to):
        activate_cmd = str(Path("venv") / "Scripts" / "activate.bat")
        python_cmd = "python"
        audio2vmd_script = AUDIO2VMD_FILENAME

        start_time = time.time()

        for file in input_files:
            if not self.processing:
                break

            cmd = [
                "cmd", "/c",
                "call", activate_cmd, "&&",
                python_cmd,
                audio2vmd_script,
                str(Path(file)),
                "--output", str(Path(output_dir)),
                "--show-final-complete-message", "False"
            ]

            if send_lips_data_to:
                cmd.extend(["--send-lips-data-to", str(Path(send_lips_data_to))])

            self.queue.put(f"Processing file: {file}")

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                while self.process:
                    output = self.process.stdout.readline()
                    if output == '' and self.process.poll() is not None:
                        break
                    if output and not output.startswith("INFO:spleeter:"):
                        self.queue.put(output.strip())

                if self.process:
                    return_code = self.process.wait()
                    if return_code != 0:
                        self.queue.put(f"Process exited with return code {return_code}")
            except Exception as e:
                self.queue.put(f"An error occurred while processing {file}: {str(e)}")
            finally:
                self.process = None

        if self.processing:
            self.queue.put(f"Complete! All Audio to VMD conversion completed in {format_time(time.time() - start_time)}")
        self.queue.put("DONE")


    #uses more computer resources using restart
    def process_files_one_by_one(self, input_files, output_dir, send_lips_data_to):
        # unused, for restarting but seems to use more resources
        activate_cmd = r"call venv\Scripts\activate.bat"
        python_cmd = "python " + AUDIO2VMD_FILENAME

        input_files_str = ' '.join([f'"{file}"' for file in input_files])
        full_cmd = f'{activate_cmd} && {python_cmd} {input_files_str} --output "{output_dir}"'

        # Add the send-lips-data-to option if provided
        if send_lips_data_to:
            full_cmd += f' --send-lips-data-to "{send_lips_data_to}"'

        self.queue.put(f"Executing command: {full_cmd}\n")

        try:
            # Use subprocess.Popen with universal_newlines=True and encoding='utf-8'
            self.process = subprocess.Popen(
                full_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                bufsize=1, 
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                shell=True
            )

            while self.process:
                output = self.process.stdout.readline() 
                error = self.process.stderr.readline() #shows errors

                if output == '' and error == '' and self.process.poll() is not None:
                    break

                if output:
                    self.queue.put(output.strip())
                if error:
                    self.queue.put(f"ERROR: {error.strip()}")

            if self.process:
                return_code = self.process.wait()
                if return_code != 0:
                    self.queue.put(f"Process exited with return code {return_code}")
        except Exception as e:
            self.queue.put(f"An error occurred: {str(e)}")
        finally:
            self.queue.put("DONE")
            self.process = None



    def process_files_by_looping(self, input_files, output_dir):
        # unused
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
                    self.run_button.config(text="Run", state='normal')
                else:
                    self.output_text.insert(tk.END, line + '\n')
                    self.output_text.see(tk.END)
        except queue.Empty:
            if self.processing:
                self.master.after(100, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = Audio2VMDGui(root)
    root.mainloop()
