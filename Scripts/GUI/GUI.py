import os
import threading
import customtkinter as ctk
import subprocess
from queue import Queue
import sys
from tkinter import messagebox
import re
import json
import time

# Configurazione della GUI
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Variabili globali
config_fase2_visible = False
config_fase4_visible = False
config_whisper_visible = False
config_entries = {}
is_running = False
funzione_selezionata = None
paths = None
start_time = None
execution_time_label = None

# Finestra principale
root = ctk.CTk()
root.title("Auto Sub ReTimer")
root.geometry("1000x700")
root.update_idletasks()
x = (root.winfo_screenwidth() // 2) - (1000 // 2)
y = (root.winfo_screenheight() // 2) - (700 // 2)
root.geometry(f"1000x700+{x}+{y}")

# --------------------------------------------------
# FUNZIONI PER LA GESTIONE DELLA CONFIGURAZIONE
# --------------------------------------------------
def mostra_config_fase2():
    global config_fase2_visible
    
    if funzione_selezionata != "Auto Sub ReTimer":
        return
    
    config_fase2_visible = not config_fase2_visible
    
    if config_fase2_visible:
        if config_fase4_visible:
            nascondi_config_fase4()
        if config_whisper_visible:
            nascondi_config_whisper()
        
        config_path = os.path.join(paths['project_root'], "Scripts", "Migliora il Timing Dei Sub", "Config_Fase2.json")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                "picco_audio_threshold": 400,
                "max_range_picco": 700,
                "lead_in": 175,
                "lead_out": 410
            }
        
        config_frame = ctk.CTkFrame(frame_center)
        config_frame.pack(fill="x", padx=10, pady=(0, 10), before=log_text)
        
        ctk.CTkLabel(config_frame, text="Fase2 Configuration", font=("Arial", 14, "bold")).pack(pady=5)
        
        fields = [
            ("Peak detection margin after initial timestamp (ms):", "picco_audio_threshold", config["picco_audio_threshold"]),
            ("Peak detection margin before final timestamp (ms):", "max_range_picco", config["max_range_picco"]),
            ("Add Lead-in, don't set too high value (ms):", "lead_in", config["lead_in"]),
            ("Add Lead-out, don't set too high value (ms):", "lead_out", config["lead_out"])
        ]
        
        for label, key, value in fields:
            frame = ctk.CTkFrame(config_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(frame, text=label, width=180).pack(side="left")
            entry = ctk.CTkEntry(frame, width=80)
            entry.insert(0, str(value))
            entry.pack(side="right")
            
            config_entries[key] = entry
        
        btn_frame = ctk.CTkFrame(config_frame)
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, 
            text="Save", 
            command=salva_config_fase2,
            width=80,
            fg_color="#2FA572"
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            command=nascondi_config_fase2,
            width=80,
            fg_color="#D35F5F"
        ).pack(side="right", padx=10)
        
        config_entries["fase2_frame"] = config_frame
        
    else:
        nascondi_config_fase2()

def nascondi_config_fase2():
    global config_fase2_visible
    if "fase2_frame" in config_entries:
        config_entries["fase2_frame"].pack_forget()
        config_entries["fase2_frame"].destroy()
        for key in [k for k in config_entries.keys() if k != "fase4_frame"]:
            config_entries.pop(key)
    config_fase2_visible = False

def mostra_config_fase4():
    global config_fase4_visible
    
    if funzione_selezionata != "Auto Sub ReTimer":
        return
    
    config_fase4_visible = not config_fase4_visible
    
    if config_fase4_visible:
        if config_fase2_visible:
            nascondi_config_fase2()
        if config_whisper_visible:
            nascondi_config_whisper()
        
        config_path = os.path.join(paths['project_root'], "Scripts", "Migliora il Timing Dei Sub", "Config_Fase4.json")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                "max_range_next_scene": 300,
                "gap_threshold": 280,
                "scene_change_before_threshold": 240,
                "scene_change_after_threshold": 200
            }
        
        config_frame = ctk.CTkFrame(frame_center)
        config_frame.pack(fill="x", padx=10, pady=(0, 10), before=log_text)
        
        ctk.CTkLabel(config_frame, text="Fase4 Configuration", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Campo per max_range_next_scene
        frame1 = ctk.CTkFrame(config_frame)
        frame1.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(frame1, text="Max range to detect a scene change from the final timestamp (ms):", width=180).pack(side="left")
        entry1 = ctk.CTkEntry(frame1, width=80)
        entry1.insert(0, str(config["max_range_next_scene"]))
        entry1.pack(side="right")
        config_entries["max_range_next_scene"] = entry1
        
        # NUOVO CAMPO per gap_threshold
        frame2 = ctk.CTkFrame(config_frame)
        frame2.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(frame2, text="Max gap 'empty' between two lines to attach (ms):", width=180).pack(side="left")
        entry2 = ctk.CTkEntry(frame2, width=80)
        entry2.insert(0, str(config.get("gap_threshold", 200)))
        entry2.pack(side="right")
        config_entries["gap_threshold"] = entry2

        # NUOVO CAMPO per scene_change_before_threshold
        frame3 = ctk.CTkFrame(config_frame)
        frame3.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(frame3, text="Max range to detect scene change before the initial timestamp (ms):", width=180).pack(side="left")
        entry3 = ctk.CTkEntry(frame3, width=80)
        entry3.insert(0, str(config.get("scene_change_before_threshold", 200)))
        entry3.pack(side="right")
        config_entries["scene_change_before_threshold"] = entry3

        # NUOVO CAMPO per scene_change_after_threshold
        frame4 = ctk.CTkFrame(config_frame)
        frame4.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(frame4, text="Max range to detect scene change after the initial timestamp (ms):", width=180).pack(side="left")
        entry4 = ctk.CTkEntry(frame4, width=80)
        entry4.insert(0, str(config.get("scene_change_after_threshold", 200)))
        entry4.pack(side="right")
        config_entries["scene_change_after_threshold"] = entry4
        
        # Pulsanti Save/Cancel
        btn_frame = ctk.CTkFrame(config_frame)
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, 
            text="Save", 
            command=salva_config_fase4,
            width=80,
            fg_color="#2FA572"
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            command=nascondi_config_fase4,
            width=80,
            fg_color="#D35F5F"
        ).pack(side="right", padx=10)
        
        config_entries["fase4_frame"] = config_frame
        
    else:
        nascondi_config_fase4()

def nascondi_config_fase4():
    global config_fase4_visible
    if "fase4_frame" in config_entries:
        config_entries["fase4_frame"].pack_forget()
        config_entries["fase4_frame"].destroy()
        for key in [k for k in config_entries.keys() if k != "fase2_frame"]:
            config_entries.pop(key)
    config_fase4_visible = False

def salva_config_fase2():
    try:
        config_path = os.path.join(paths['project_root'], "Scripts", "Migliora il Timing Dei Sub", "Config_Fase2.json")
        new_config = {
            "picco_audio_threshold": int(config_entries["picco_audio_threshold"].get()),
            "max_range_picco": int(config_entries["max_range_picco"].get()),
            "lead_in": int(config_entries["lead_in"].get()),
            "lead_out": int(config_entries["lead_out"].get())
        }
        
        with open(config_path, "w") as f:
            json.dump(new_config, f, indent=4)
        
        messagebox.showinfo("Success", "Configuration saved successfully!")
        nascondi_config_fase2()
        
    except ValueError:
        messagebox.showerror("Error", "Please enter only integer numbers")
    except Exception as e:
        messagebox.showerror("Error", f"Error while saving: {str(e)}")

def mostra_config_whisper():
    global config_whisper_visible
    
    if funzione_selezionata != "Whisper":
        return
    
    config_whisper_visible = not config_whisper_visible
    
    if config_whisper_visible:
        if config_fase2_visible:
            nascondi_config_fase2()
        if config_fase4_visible:
            nascondi_config_fase4()
        
        config_path = os.path.join(paths['project_root'], "Scripts", "Whisper", "whisper_config.json")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                "default_values": {
                    "language": "ja",
                    "model": "medium"
                },
                "options": {
                    "languages": ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"],
                    "models": ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2", "large-v3", "large"]
                }
            }
        
        config_frame = ctk.CTkFrame(frame_center)
        config_frame.pack(fill="x", padx=10, pady=(0, 10), before=log_text)
        
        ctk.CTkLabel(config_frame, text="Whisper Configuration", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Language selection
        lang_frame = ctk.CTkFrame(config_frame)
        lang_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(lang_frame, text="Language:", width=120).pack(side="left")
        lang_var = ctk.StringVar(value=config["default_values"]["language"])
        lang_menu = ctk.CTkOptionMenu(
            lang_frame, 
            variable=lang_var,
            values=config["options"]["languages"],
            width=120
        )
        lang_menu.pack(side="right")
        config_entries["language"] = lang_var
        
        # Model selection
        model_frame = ctk.CTkFrame(config_frame)
        model_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(model_frame, text="Model:", width=120).pack(side="left")
        model_var = ctk.StringVar(value=config["default_values"]["model"])
        model_menu = ctk.CTkOptionMenu(
            model_frame, 
            variable=model_var,
            values=config["options"]["models"],
            width=120
        )
        model_menu.pack(side="right")
        config_entries["model"] = model_var
        
        # Buttons
        btn_frame = ctk.CTkFrame(config_frame)
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, 
            text="Save", 
            command=salva_config_whisper,
            width=80,
            fg_color="#2FA572"
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            command=nascondi_config_whisper,
            width=80,
            fg_color="#D35F5F"
        ).pack(side="right", padx=10)
        
        config_entries["whisper_frame"] = config_frame
        
    else:
        nascondi_config_whisper()

def nascondi_config_whisper():
    global config_whisper_visible
    if "whisper_frame" in config_entries:
        config_entries["whisper_frame"].pack_forget()
        config_entries["whisper_frame"].destroy()
        for key in ["language", "model", "whisper_frame"]:
            if key in config_entries:
                config_entries.pop(key)
    config_whisper_visible = False

def salva_config_fase4():
    try:
        config_path = os.path.join(paths['project_root'], "Scripts", "Migliora il Timing Dei Sub", "Config_Fase4.json")
        new_config = {
            "max_range_next_scene": int(config_entries["max_range_next_scene"].get()),
            "gap_threshold": int(config_entries["gap_threshold"].get()),
            "scene_change_before_threshold": int(config_entries["scene_change_before_threshold"].get()),
            "scene_change_after_threshold": int(config_entries["scene_change_after_threshold"].get())
        }
        
        with open(config_path, "w") as f:
            json.dump(new_config, f, indent=4)
        
        messagebox.showinfo("Success", "Configuration saved successfully!")
        nascondi_config_fase4()
        
    except ValueError:
        messagebox.showerror("Error", "Please enter only integer numbers")
    except Exception as e:
        messagebox.showerror("Error", f"Error while saving: {str(e)}")

def salva_config_whisper():
    try:
        config_path = os.path.join(paths['project_root'], "Scripts", "Whisper", "whisper_config.json")
        new_config = {
            "default_values": {
                "language": config_entries["language"].get(),
                "model": config_entries["model"].get()
            },
            "options": {
                "languages": ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"],
                "models": ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2", "large-v3", "large"]
            }
        }
        
        with open(config_path, "w") as f:
            json.dump(new_config, f, indent=4)
        
        messagebox.showinfo("Success", "Whisper configuration saved successfully!")
        nascondi_config_whisper()
        
    except Exception as e:
        messagebox.showerror("Error", f"Error while saving: {str(e)}")

def aggiorna_visibilita_pulsanti_config():
    if funzione_selezionata == "Auto Sub ReTimer":
        btn_config_fase2.pack(side="left", padx=5)
        btn_config_fase4.pack(side="left", padx=5)
        btn_config_whisper.pack_forget()
        btn_config_fase2.configure(state="normal")
        btn_config_fase4.configure(state="normal")
    elif funzione_selezionata == "Whisper":
        btn_config_fase2.pack_forget()
        btn_config_fase4.pack_forget()
        btn_config_whisper.pack(side="left", padx=5)
        btn_config_whisper.configure(state="normal")
    else:
        btn_config_fase2.pack_forget()
        btn_config_fase4.pack_forget()
        btn_config_whisper.pack_forget()
    
    # Hide all config panels when switching functions
    nascondi_config_fase2()
    nascondi_config_fase4()
    nascondi_config_whisper()

# --------------------------------------------------
# GESTIONE PERCORSI E STATO
# --------------------------------------------------
def setup_paths():
    try:
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(gui_dir, "..", ".."))
        
        paths = {
            'project_root': project_root,
            'retimer_scripts': {
                'fase0': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase0.py"),
                'fase1': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase1.py"),
                'fase2': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase2.py"),
                'fase3': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase3.py"),
                'fase4': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase4.py"),
                'fase5': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase5.py"),
                'fase6': os.path.join(project_root, "Scripts", "Migliora il Timing Dei Sub", "Fase6.py")
            },
            'whisper_scripts': {
                'fase0': os.path.join(project_root, "Scripts", "Whisper", "Fase0.py"),
                'fase1': os.path.join(project_root, "Scripts", "Whisper", "Fase1.py"),
                'venv_python': os.path.join(project_root, "main", "Scripts", "python.exe"),
                'exe_folder': os.path.join(project_root, "Faster-Whisper-XXL"),
                'exe_file': os.path.join(project_root, "Faster-Whisper-XXL", "faster-whisper-xxl.exe"),
                'input_file': os.path.join(project_root, "whisper.aac")
            },
            'whisper_retimer': {
                'fase0': os.path.join(project_root, "Scripts", "Whisper Miglioramento Timing", "Fase0.py"),
                'whispertiming': os.path.join(project_root, "Scripts", "Whisper Miglioramento Timing", "whispertiming.py"),
                'fase3': os.path.join(project_root, "Scripts", "Whisper Miglioramento Timing", "Fase3.py"),
                'fase4': os.path.join(project_root, "Scripts", "Whisper Miglioramento Timing", "Fase4.py"),
                'fase5': os.path.join(project_root, "Scripts", "Whisper Miglioramento Timing", "Fase5.py")
            },
            'available': {
                'whisper': True,
                'retimer': True,
                'autosub': True
            }
        }

        missing_paths = []
        
        for script in paths['retimer_scripts'].values():
            if not os.path.exists(script):
                missing_paths.append(f"Auto Sub ReTimer script not found: {script}")
                paths['available']['autosub'] = False
                
        for name, path in paths['whisper_retimer'].items():
            if not os.path.exists(path):
                missing_paths.append(f"Whisper ReTimer script not found: {path}")
                paths['available']['retimer'] = False
                
        if not os.path.exists(paths['whisper_scripts']['fase0']):
            missing_paths.append(f"Whisper script not found: {paths['whisper_scripts']['fase0']}")
            paths['available']['whisper'] = False
            
        if not os.path.exists(paths['whisper_scripts']['exe_file']):
            missing_paths.append(f"Faster-Whisper file not found: {paths['whisper_scripts']['exe_file']}")
            paths['available']['whisper'] = False
            paths['available']['retimer'] = False
            
        if not os.path.exists(paths['whisper_scripts']['venv_python']):
            missing_paths.append(f"Python virtualenv not found: {paths['whisper_scripts']['venv_python']}")
            paths['available']['whisper'] = False
            paths['available']['retimer'] = False

        if paths['available']['whisper']:
            for name, path in paths['whisper_retimer'].items():
                if not os.path.exists(path):
                    missing_paths.append(f"Whisper ReTimer script not found: {path}")
                    paths['available']['retimer'] = False

        if missing_paths:
            messagebox.showwarning("Warning", 
                "Some paths were not found:\n\n" + 
                "\n".join(missing_paths) + 
                "\n\nRelated features might not be available.")

        return paths

    except Exception as e:
        messagebox.showerror("Error", f"Path configuration error: {str(e)}")
        return None

paths = setup_paths()
if paths is None:
    sys.exit(1)

# --------------------------------------------------
# GESTIONE INPUT UTENTE
# --------------------------------------------------
class InputHandler:
    def __init__(self, root):
        self.root = root
        self.response = None
        self.event = threading.Event()
    
    def ask_question(self, question, options):
        self.response = None
        self.root.after(0, self._create_dialog, question, options)
        self.event.wait()
        return self.response
    
    def _create_dialog(self, question, options):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Input Required")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(dialog, text=question, font=("Arial", 12))
        label.pack(pady=20)
        
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        
        for idx, option in enumerate(options, 1):
            btn = ctk.CTkButton(
                btn_frame,
                text=option,
                command=lambda opt=idx: self._set_response(opt, dialog),
                width=120
            )
            btn.pack(side="left", padx=5)
    
    def _set_response(self, response, dialog):
        self.response = response
        dialog.destroy()
        self.event.set()

input_handler = InputHandler(root)

# --------------------------------------------------
# GESTIONE PROGRESSO
# --------------------------------------------------
class ProgressManager:
    def __init__(self):
        self.total_phases = 7
        self.current_phase = 0
        self.phase_progress = 0
        self.phase_weights = {
            0: 15,  # Fase0
            1: 20,  # Fase1 
            2: 15,  # Fase2
            3: 15,  # Fase3
            4: 15,  # Fase4
            5: 15,  # Fase5
            6: 5    # Fase6
        }
        
    def update_phase(self, phase_num):
        self.current_phase = phase_num
        self.phase_progress = 0
        self._update_display()
        
    def update_progress(self, progress):
        self.phase_progress = progress
        self._update_display()
        
    def complete_all(self):
        self.current_phase = self.total_phases
        self.phase_progress = 100
        self._update_display()
        
    def _update_display(self):
        completed_weight = sum(
            weight for phase, weight in self.phase_weights.items() 
            if phase < self.current_phase
        )
        
        current_phase_weight = self.phase_weights.get(self.current_phase, 0)
        current_progress = (self.phase_progress / 100) * current_phase_weight
        
        total_progress = min(completed_weight + current_progress, 100)
        percent = total_progress
        
        progress_bar.set(percent / 100)
        progress_label.configure(text=f"Completion: {int(percent)}%")
        status_label.configure(text=f"Status: Fase {self.current_phase} ({int(self.phase_progress)}%)")

progress_manager = ProgressManager()
output_queue = Queue()

# --------------------------------------------------
# INTERFACCIA GRAFICA
# --------------------------------------------------
# Frame Sinistra
frame_left = ctk.CTkFrame(root, width=200, corner_radius=10)
frame_left.pack(side="left", fill="y", padx=10, pady=10)

ctk.CTkLabel(frame_left, text="Created by AndryOut\n[HonyakuSubs]\n\nFunctions", font=("Arial", 16, "bold")).pack(pady=15)

button_autosub = ctk.CTkButton(
    frame_left, 
    text="Auto Sub ReTimer", 
    command=lambda: seleziona_funzione("Auto Sub ReTimer"),
    height=40, 
    font=("Arial", 14)
)
button_autosub.pack(pady=10, fill="x")

button_whisper = ctk.CTkButton(
    frame_left, 
    text="Whisper", 
    command=lambda: seleziona_funzione("Whisper"),
    height=40, 
    font=("Arial", 14)
)
button_whisper.pack(pady=10, fill="x")

button_retimer = ctk.CTkButton(
    frame_left, 
    text="Whisper ReTimer", 
    command=lambda: seleziona_funzione("Whisper ReTimer"),
    height=40, 
    font=("Arial", 14)
)
button_retimer.pack(pady=10, fill="x")

# Frame Centrale
frame_center = ctk.CTkFrame(root, corner_radius=10)
frame_center.pack(side="left", fill="both", expand=True, padx=10, pady=10)

# Area progresso
progress_frame = ctk.CTkFrame(frame_center)
progress_frame.pack(fill="x", padx=10, pady=10)

status_label = ctk.CTkLabel(progress_frame, text="Status: Inactive", font=("Arial", 12))
status_label.pack(anchor="w")

progress_bar = ctk.CTkProgressBar(progress_frame, height=20)
progress_bar.pack(fill="x", pady=5)
progress_bar.set(0)

progress_label = ctk.CTkLabel(progress_frame, text="Completion: 0%", font=("Arial", 12))
progress_label.pack(anchor="e")
execution_time_label = ctk.CTkLabel(progress_frame, text="Time: 00:00:00", font=("Arial", 12))
execution_time_label.pack(anchor="e")

# Pulsanti configurazione
config_buttons_frame = ctk.CTkFrame(frame_center)
config_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

btn_config_fase2 = ctk.CTkButton(
    config_buttons_frame,
    text="Config Fase2",
    command=mostra_config_fase2,
    width=120,
    state="disabled"
)

btn_config_fase4 = ctk.CTkButton(
    config_buttons_frame,
    text="Config Fase4",
    command=mostra_config_fase4,
    width=120,
    state="disabled"
)

btn_config_whisper = ctk.CTkButton(
    config_buttons_frame,
    text="Config Whisper",
    command=mostra_config_whisper,
    width=120,
    state="disabled"
)

# Initially hide all config buttons
btn_config_whisper.pack_forget()

# Area log
log_text = ctk.CTkTextbox(
    frame_center, 
    height=150, 
    font=("Consolas", 12),
    wrap="word"
)
log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
log_text.insert("1.0", "Ready to start...\n")
log_text.configure(state="disabled")

# Start Button
button_avvia = ctk.CTkButton(
    frame_center,
    text="Start",
    command=lambda: threading.Thread(target=avvia_processo, daemon=True).start(),
    height=40,
    font=("Arial", 14, "bold")
)
button_avvia.pack(pady=10, fill="x")

# Frame Destra
frame_right = ctk.CTkFrame(root, width=250, corner_radius=10)
frame_right.pack(side="right", fill="y", padx=10, pady=10)

ctk.CTkLabel(frame_right, text="Instructions", font=("Arial", 16, "bold")).pack(pady=15)

instructions_text = ctk.CTkTextbox(
    frame_right, 
    font=("Arial", 12), 
    wrap="word"
)
instructions_text.pack(fill="both", expand=True, padx=10, pady=10)
instructions_text.insert("1.0",
    "Welcome to Auto Sub ReTimer\n\n"
    "1. Select a function\n"
    "2. Click 'Start'\n"
    "3. Answer the questions\n\n"
    "Monitor progress in the bar."
)

# --------------------------------------------------
# GESTIONE ESECUZIONE
# --------------------------------------------------
# Timer
def update_timer():
    if start_time:
        elapsed = int(time.time() - start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        execution_time_label.configure(text=f"Time: {hours:02}:{minutes:02}:{seconds:02}")
    root.after(1000, update_timer)

def update_log():
    while not output_queue.empty():
        msg = output_queue.get()
        log_text.configure(state="normal")
        log_text.insert("end", msg)
        log_text.see("end")
        log_text.configure(state="disabled")
    root.after(100, update_log)

def log_message(message):
    output_queue.put(message)

def parse_progress(output):
    match = re.search(r'(\d+)%|\b(\d+)/(\d+)\b', output)
    if match:
        if match.group(1):
            return float(match.group(1))
        elif match.group(2) and match.group(3):
            return (float(match.group(2)) / float(match.group(3))) * 100
    return None

def run_interactive_phase(phase_num, phase_path):
    phase_name = f"Fase {phase_num}"
    progress_manager.update_phase(phase_num)
    log_message(f"▶ Starting {phase_name}\n")
    
    try:
        process = subprocess.Popen(
            [sys.executable, phase_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=4096,
            universal_newlines=True,
            cwd=paths['project_root']
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output:
                if "cartelli" in output.lower() or "scegli" in output.lower():
                    question = output.strip()
                    options = ["Sì", "No"] if "cartelli" in output.lower() else ["Option 1", "Option 2"]
                    
                    # Per Fase6, ferma il timer prima del popup
                    if phase_num == 6:
                        global start_time
                        start_time = None
                    
                    answer = input_handler.ask_question(question, options)
                    
                    if answer is not None:
                        process.stdin.write(f"{answer}\n")
                        process.stdin.flush()
                
                progress = parse_progress(output)
                if progress is not None:
                    progress_manager.update_progress(progress)
                
                log_message(output)
        
        return process.returncode == 0
        
    except Exception as e:
        log_message(f"⚠ Error in {phase_name}: {str(e)}\n")
        return False

def run_normal_phase(phase_num, phase_path):
    phase_name = f"Fase {phase_num}"
    progress_manager.update_phase(phase_num)
    log_message(f"▶ Starting {phase_name}\n")
    
    try:
        process = subprocess.Popen(
            [sys.executable, phase_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=paths['project_root']
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output:
                progress = parse_progress(output)
                if progress is not None:
                    progress_manager.update_progress(progress)
                elif "error" in output.lower():
                    log_message(f"⚠ {output}")
        
        return process.returncode == 0
        
    except Exception as e:
        log_message(f"⚠ Error in {phase_name}: {str(e)}\n")
        return False

def esegui_auto_sub_retimer():
    global is_running, start_time
    
    if is_running:
        return
    
    is_running = True
    button_avvia.configure(state="disabled")
    log_text.configure(state="normal")
    log_text.delete("1.0", "end")
    log_text.configure(state="disabled")
    
    try:
        fasi = [
            (0, paths['retimer_scripts']['fase0'], True),
            (1, paths['retimer_scripts']['fase1'], False),
            (2, paths['retimer_scripts']['fase2'], False),
            (3, paths['retimer_scripts']['fase3'], False),
            (4, paths['retimer_scripts']['fase4'], False),
            (5, paths['retimer_scripts']['fase5'], False),
            (6, paths['retimer_scripts']['fase6'], True)
        ]
        
        log_message("🚀 Starting Auto Sub ReTimer process\n")
        
        for phase_num, phase_path, is_interactive in fasi:
            # Per Fase0, avvia il timer solo dopo che la finestra di selezione file è chiusa
            if phase_num == 0:
                success = run_interactive_phase(phase_num, phase_path)
                if success:
                    start_time = time.time()  # Avvia timer solo dopo selezione file
            else:
                if is_interactive:
                    success = run_interactive_phase(phase_num, phase_path)
                else:
                    success = run_normal_phase(phase_num, phase_path)
                
            if not success:
                log_message("❌ Process interrupted\n")
                break
                
            # Ferma il timer dopo Fase5 invece che Fase6
            if phase_num == 5:
                start_time = None
                
        else:
            log_message("🎉 Process completed successfully!\n")
        
        progress_manager.complete_all()
            
    finally:
        is_running = False
        start_time = None
        button_avvia.configure(state="normal")
        status_label.configure(text="Status: Completed")

def esegui_whisper():
    global is_running
    
    if is_running:
        return
    
    is_running = True
    button_avvia.configure(state="disabled")
    log_text.configure(state="normal")
    log_text.delete("1.0", "end")
    log_text.insert("end", "🚀 Starting Whisper process...\n")
    log_text.configure(state="disabled")
    
    try:
        progress_manager.update_phase(0)
        log_message("▶ Running Fase0.py (preparation)...\n")
        
        # Esegui Fase0.py
        fase0_result = subprocess.run(
            [paths['whisper_scripts']['venv_python'], paths['whisper_scripts']['fase0']],
            cwd=paths['project_root'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if fase0_result.returncode != 0:
            log_message(f"✖ Error in Fase0.py:\n{fase0_result.stderr}\n")
            return False
        
        log_message("✔ Fase0.py completed successfully\n")
        progress_manager.update_progress(100)
        
        progress_manager.update_phase(1)
        log_message("▶ Running Fase1.py (Whisper execution)...\n")
        
        # Esegui Fase1.py con gestione output in tempo reale
        process = subprocess.Popen(
            [paths['whisper_scripts']['venv_python'], paths['whisper_scripts']['fase1']],
            cwd=paths['project_root'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output:
                progress = parse_progress(output)
                if progress is not None:
                    progress_manager.update_progress(progress)
                log_message(output)
        
        if process.returncode == 0 or process.returncode == 3221226505:
            log_message("✔ Whisper execution completed successfully\n")
            progress_manager.complete_all()
            return True
        else:
            log_message(f"✖ Error in Fase1.py (code {process.returncode})\n")
            return False
        
    except Exception as e:
        log_message(f"⚠ Error during execution: {str(e)}\n")
        return False
    finally:
        is_running = False
        button_avvia.configure(state="normal")
        status_label.configure(text="Status: Completed")

def esegui_whisper_retimer():
    global is_running
    
    if is_running:
        return
    
    is_running = True
    button_avvia.configure(state="disabled")
    input_handler.response = None
    input_handler.event.clear()
    log_text.configure(state="normal")
    log_text.delete("1.0", "end")
    log_text.insert("end", "🚀 Starting Whisper ReTimer process...\n")
    log_text.configure(state="disabled")
    
    try:
        progress_manager.update_phase(0)
        log_message("▶ Running Fase0.py (preparation)...\n")
        
        if not run_normal_phase(0, paths['whisper_retimer']['fase0']):
            log_message("✖ Error in Fase0.py\n")
            return False
        
        progress_manager.update_phase(1)
        log_message("▶ Running whispertiming.py...\n")
        
        if not run_normal_phase(1, paths['whisper_retimer']['whispertiming']):
            log_message("✖ Error in whispertiming.py\n")
            return False
        
        progress_manager.update_phase(2)
        log_message("▶ Waiting for user input...\n")
        
        risposta = input_handler.ask_question("Do you want subtitles to respect scene changes?", ["Yes", "No"])
        
        if risposta == 1:
            progress_manager.update_phase(3)
            log_message("▶ Running Fase3.py...\n")
            
            if not run_normal_phase(3, paths['whisper_retimer']['fase3']):
                log_message("✖ Error in Fase3.py\n")
                return False
            
            progress_manager.update_phase(4)
            log_message("▶ Running Fase4.py...\n")
            
            if not run_normal_phase(4, paths['whisper_retimer']['fase4']):
                log_message("✖ Error in Fase4.py\n")
                return False
            
            progress_manager.update_phase(5)
            log_message("▶ Running Fase5.py...\n")
            
            if not run_normal_phase(5, paths['whisper_retimer']['fase5']):
                log_message("✖ Error in Fase5.py\n")
                return False
            
        else:
            progress_manager.update_phase(5)
            log_message("▶ Running Fase5.py...\n")
            
            if not run_normal_phase(5, paths['whisper_retimer']['fase5']):
                log_message("✖ Error in Fase5.py\n")
                return False
        
        log_message("🎉 Whisper ReTimer process completed successfully!\n")
        progress_manager.complete_all()
        return True
        
    except Exception as e:
        log_message(f"⚠ Error during execution: {str(e)}\n")
        return False
    finally:
        is_running = False
        button_avvia.configure(state="normal")
        status_label.configure(text="Status: Completed")

def avvia_processo():
    if funzione_selezionata == "Auto Sub ReTimer":
        if paths['available']['autosub']:
            esegui_auto_sub_retimer()
        else:
            messagebox.showwarning("Function not available", 
                "Some Auto Sub ReTimer scripts were not found.")
    elif funzione_selezionata == "Whisper":
        if paths['available']['whisper']:
            esegui_whisper()
        else:
            messagebox.showwarning("Function not available", 
                "Whisper function requires 'Faster-Whisper-XXL' folder.\n"
                "Please add it to the main 'Auto Sub ReTimer' directory.")
    elif funzione_selezionata == "Whisper ReTimer":
        if paths['available']['retimer']:
            esegui_whisper_retimer()
        else:
            messagebox.showwarning("Function not available", 
                "Some Whisper ReTimer scripts were not found.")
    else:
        log_message("Select a valid function\n")

def seleziona_funzione(funzione):
    global funzione_selezionata
    funzione_selezionata = funzione
    
    buttons = {
        "Auto Sub ReTimer": button_autosub,
        "Whisper": button_whisper,
        "Whisper ReTimer": button_retimer
    }
    
    for name, btn in buttons.items():
        btn.configure(fg_color=("#3B8ED0", "#1F6AA5"))
        if name == "Whisper" and not paths['available']['whisper']:
            btn.configure(state="disabled", fg_color=("#666666", "#333333"))
        elif name == "Whisper ReTimer" and not paths['available']['retimer']:
            btn.configure(state="disabled", fg_color=("#666666", "#333333"))
        elif name == "Auto Sub ReTimer" and not paths['available']['autosub']:
            btn.configure(state="disabled", fg_color=("#666666", "#333333"))
        else:
            btn.configure(state="normal")
    
    if funzione in buttons and buttons[funzione].cget("state") == "normal":
        buttons[funzione].configure(fg_color=("#2FA572", "#2FA572"))
    
    instructions_text.delete("1.0", "end")
    if funzione == "Auto Sub ReTimer":
        if paths['available']['autosub']:
            instructions_text.insert("1.0",
                "Auto Sub ReTimer\n\n"
                "1. Make sure you have the video .mkv in the Auto Sub ReTimer folder.\n"
                "\n"
                "2. The line of spoken audio in the sub must be within the lines and not partially outside the line (audio spectrum).\n"
                "There must not be the start of spoken audio that begins before the line, for example.\n"
                "Even a quick sync that's the same for all lines is sufficient, for example -0.050 or -0.100.\n"
                "\n"
                "3. In Fase0, you will be asked to upload the subtitle.\n"
                "It will automatically separate Signs, Comments and On Top to avoid conflicts with the timing adjustment of dialogues.\n"
                "If the program can't figure out where certain lines go, you'll be asked to select where to put them.\n"
                "If the separation does not work as expected, you can always manually separate everything to leave only the dialogues.\n"
                "\n"
                "4. If the video codec is Av1, PySceneDetect will not work in Fase3.\n"
                "\n"
                "5. Read the instructions on GitHub.\n\n"     
            )
        else:
            instructions_text.insert("1.0",
                "AUTO SUB RETIMER NOT AVAILABLE\n\n"
                "Required scripts not found.\n"
                "Check folder:\n"
                "'Scripts/Migliora il Timing Dei Sub'"
            )
    elif funzione == "Whisper":
        if paths['available']['whisper']:
            instructions_text.insert("1.0",
                "Whisper\n\n"
                "Automatic audio transcription:\n"
                "\n"
                "1. Make sure you have the video .mkv in the Auto Sub ReTimer folder.\n"
                "\n"
                "2. Faster-Whisper execution.\n"
                "\n"
                "3. Subtitles generation.\n\n"
            )
        else:
            instructions_text.insert("1.0",
                "WHISPER NOT AVAILABLE\n\n"
                "To use this function:\n"
                "1. Add 'Faster-Whisper-XXL' folder\n"
                "2. Ensure it contains 'faster-whisper-xxl.exe'\n"
                "3. Restart application"
            )
    elif funzione == "Whisper ReTimer":
        if paths['available']['retimer']:
            instructions_text.insert("1.0",
                "Whisper ReTimer\n\n"
                "Timing improvement process:\n"
                "\n"
                "1. First of all, it will improve the timing of the sub generated by Whisper.\n"
                "\n"
                "2. It will ask you if you also want the newly fixed Whisper sub to respect Scene Changes as well.\n"
                "\n"
                "3. It will automatically adapt to your choice.\n"       
            )
        else:
            instructions_text.insert("1.0",
                "WHISPER RETIMER NOT AVAILABLE\n\n"
                "Required scripts not found.\n"
                "Check folder:\n"
                "'Scripts/Whisper Miglioramento Timing'"
            )
    else:
        instructions_text.insert("1.0",
            "Welcome to Auto Sub ReTimer\n\n"
            "1. Select a function\n"
            "2. Click 'Start'\n"
            "3. Answer questions\n\n"
            "Monitor progress in the bar."
        )
    
    aggiorna_visibilita_pulsanti_config()

# --------------------------------------------------
# AVVIO APPLICAZIONE
# --------------------------------------------------
seleziona_funzione("Auto Sub ReTimer")
root.after(500, update_log)
root.after(1000, update_timer)
root.mainloop()