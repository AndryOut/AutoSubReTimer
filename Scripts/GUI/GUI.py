import os
import threading
import customtkinter as ctk
import subprocess
from queue import Queue
from collections import deque
import sys
from tkinter import messagebox, filedialog
import re
import json
import time
import importlib
import shutil
import traceback
import webbrowser
import tkinter as tk


# ------------------------------------------------------------
# BASE / CONSTANTS
# ------------------------------------------------------------
loaded_modules = {}
PROGRESS_RE = re.compile(r'(\d+)%|\b(\d+)/(\d+)\b')
GUI_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_config.json")

INTERMEDI_PIPELINE = [
    "Sub.srt",
    "vocali.wav",
    "temp_demucs.wav",
    "adjusted_Sub.srt",
    "scene_timestamps.srt",
    "scene_timestamps_adjusted.srt",
    "Final.srt",
    "Final.ass",
    "Dialoghi.ass",
    "On Top.ass",
    "On Top.srt",
    "Comments.ass",
    "Signs.ass",
    ".asr_pipeline_paths.json",
]

WHISPER_LANGUAGES = [
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs",
    "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi",
    "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy",
    "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb",
    "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
    "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru",
    "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw",
    "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi",
    "yi", "yo", "yue", "zh"
]

WHISPER_MODELS = [
    "tiny", "tiny.en", "base", "base.en", "small", "small.en",
    "medium", "medium.en", "large-v1", "large-v2", "large-v3", "large"
]


# ------------------------------------------------------------
# GUI CONFIG
# ------------------------------------------------------------
def _load_gui_config():
    try:
        with open(GUI_CONFIG_PATH, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_gui_config_key(key, value):
    cfg = _load_gui_config()
    cfg[key] = value
    try:
        with open(GUI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass


# ------------------------------------------------------------
# CLEAN INTERMEDIATE FILES
# ------------------------------------------------------------
def pulisci_intermedi(project_root):
    for name in INTERMEDI_PIPELINE:
        path = os.path.join(project_root, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError as e:
                log_message(f"[Warn] Cannot delete {name}: {e}\n")

    shutil.rmtree(os.path.join(project_root, "htdemucs"), ignore_errors=True)


# ------------------------------------------------------------
# ORIGINAL PALETTE (surface ladder)
# ------------------------------------------------------------
BG_ROOT   = "#08080B"
BG_PANEL  = "#0F0F14"
BG_CARD   = "#141419"
BG_INPUT  = "#1A1A21"

BORDER    = "#232329"
BORDER_ACC= "#3A3252"

ACCENT    = "#7C5CFA"
ACCENT_H  = "#9580FF"
ACCENT_DIM= "#221D38"

SUCCESS   = "#2ED191"
SUCCESS_H = "#3EE6A2"
DANGER    = "#F5566B"
DANGER_H  = "#FF6E82"
WARNING   = "#E6C25A"

TEXT_1    = "#EBEBF2"
TEXT_2    = "#63636F"
TEXT_A    = "#B9A8FF"

P_DONE_BG = "#122A20"
P_DONE_T  = "#2ED191"
P_ACT_BG  = "#221D38"
P_ACT_T   = "#B9A8FF"
P_IDLE_BG = "#0F0F14"
P_IDLE_T  = "#3C3C46"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ------------------------------------------------------------
# GLOBAL STATE
# ------------------------------------------------------------
config_fase2_visible = False
config_fase4_visible = False
config_whisper_visible = False
config_fase3_visible = False

config_fase3 = {}
config_entries = {}

is_running = False
funzione_selezionata = None
paths = None
start_time = None
execution_time_label = None

debug_armed = False
debug_file = None
debug_path = None
debug_started = None
debug_lock = threading.Lock()
DEBUG_PROGRESS_EVERY = 10

_body_mode = "dashboard"

_pending_status = ("Status: Inactive", "idle")
_display_dirty = False
_start_btn_req = None

STATUS_STYLES = {
    "idle":    (BG_INPUT, TEXT_2),
    "running": (P_ACT_BG, P_ACT_T),
    "done":    (P_DONE_BG, P_DONE_T),
    "fail":    ("#2A1218", DANGER),
    "debug":   ("#2A2112", WARNING),
}


def set_status(text, kind="idle"):
    global _pending_status, _display_dirty
    _pending_status = (text, kind)
    _display_dirty = True


def set_start_button(state):
    global _start_btn_req
    _start_btn_req = state


# ------------------------------------------------------------
# PHASE MAP
# ------------------------------------------------------------
PHASE_MAP = {
    "Auto Sub ReTimer": ["F0\nSetup", "F1\nDemucs", "F2\nImprove", "F3\nScene", "F4\nRefine", "F5\nASS", "F6\nMerge"],
    "Auto Sub ReTimer CR": ["F0\nSetup", "F2\nImprove", "F3\nScene", "F4\nRefine", "F5\nASS", "F6\nMerge"],
    "Whisper": ["Setup", "Transcription"],
    "Whisper ReTimer": ["Demucs", "Improve", "Scene", "Refine", "Final"]
}


# ------------------------------------------------------------
# MAIN WINDOW
# ------------------------------------------------------------
root = ctk.CTk()
root.title("Auto Sub ReTimer")
root.configure(fg_color=BG_ROOT)
root.geometry("1020x680")
root.minsize(900, 600)

def _center_window_engine(window):
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi
        hwnd = user32.GetAncestor(wintypes.HWND(window.winfo_id()), 2)

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi))

        outer, vis = wintypes.RECT(), wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(outer))
        dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(vis), ctypes.sizeof(vis))

        x = mi.rcWork.left + (mi.rcWork.right - mi.rcWork.left - (vis.right - vis.left)) // 2 - (vis.left - outer.left)
        y = mi.rcWork.top + (mi.rcWork.bottom - mi.rcWork.top - (vis.bottom - vis.top)) // 2 - (vis.top - outer.top)

        user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0001 | 0x0004)
    except Exception:
        pass

# ------------------------------------------------------------
# GENERIC UI HELPERS
# ------------------------------------------------------------
def center_window(window, width, height):
    window.geometry(f"{width}x{height}")
    window.update_idletasks()
    _center_window_engine(window)


def _fade_border(frame):
    def _apply():
        try:
            frame.configure(border_color=BORDER_ACC)
        except Exception:
            pass

    try:
        frame.configure(border_color=BORDER)
        frame.after(70, _apply)
    except Exception:
        pass


# ------------------------------------------------------------
# CONFIG PANEL HELPERS
# ------------------------------------------------------------
def _config_shell(title, close_cmd):
    frame = ctk.CTkFrame(
        dynamic_area,
        fg_color=BG_PANEL,
        corner_radius=14,
        border_width=1,
        border_color=BORDER
    )
    frame.pack(fill="x", padx=6, pady=(0, 8), before=_log_header_row)

    header = ctk.CTkFrame(frame, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(10, 4))

    ctk.CTkLabel(
        header,
        text=title,
        font=("Segoe UI", 13, "bold"),
        text_color=TEXT_A
    ).pack(side="left")

    ctk.CTkButton(
        header,
        text="✕",
        command=close_cmd,
        width=26,
        height=26,
        corner_radius=7,
        fg_color="transparent",
        hover_color=ACCENT_DIM,
        text_color=TEXT_2,
        font=("Segoe UI", 11)
    ).pack(side="right")

    ctk.CTkFrame(frame, height=1, fg_color=BORDER, corner_radius=0).pack(fill="x", padx=12, pady=(0, 6))

    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.pack(fill="x", padx=8)
    body.columnconfigure((0, 1), weight=1, uniform="cfg")

    actions = ctk.CTkFrame(frame, fg_color="transparent")
    actions.pack(fill="x", padx=12, pady=(6, 10))

    _fade_border(frame)

    return frame, body, actions


def _config_entry_cell(body, r, c, label_text, key, value, colspan=1):
    cell = ctk.CTkFrame(
        body,
        fg_color=BG_CARD,
        corner_radius=10,
        border_width=1,
        border_color=BORDER
    )
    cell.grid(row=r, column=c, columnspan=colspan, sticky="ew", padx=4, pady=4)

    ctk.CTkLabel(
        cell,
        text=label_text,
        text_color=TEXT_2,
        font=("Segoe UI", 12),
        anchor="w",
        justify="left",
        wraplength=240
    ).pack(side="left", padx=10, pady=7)

    entry = ctk.CTkEntry(
        cell,
        width=55,
        height=30,
        fg_color=BG_INPUT,
        text_color=TEXT_1,
        border_color=BORDER_ACC,
        corner_radius=8,
        justify="right",
        font=("Consolas", 11)
    )
    entry.insert(0, str(value))
    entry.pack(side="right", padx=10, pady=7)

    config_entries[key] = entry


def _config_option_cell(body, r, c, label_text, values, current, colspan=1, menu_side="right"):
    cell = ctk.CTkFrame(
        body,
        fg_color=BG_CARD,
        corner_radius=10,
        border_width=1,
        border_color=BORDER
    )
    cell.grid(row=r, column=c, columnspan=colspan, sticky="ew", padx=4, pady=4)

    ctk.CTkLabel(
        cell,
        text=label_text,
        text_color=TEXT_2,
        font=("Segoe UI", 12),
        anchor="w",
        justify="left",
        wraplength=500
    ).pack(side="left", padx=10, pady=7)

    var = ctk.StringVar(value=current)

    ctk.CTkOptionMenu(
        cell,
        variable=var,
        values=values,
        width=150,
        height=30,
        fg_color=BG_INPUT,
        button_color=ACCENT,
        button_hover_color=ACCENT_H,
        text_color=TEXT_1,
        corner_radius=8
    ).pack(side=menu_side, padx=10, pady=7)

    return var


def _config_action_buttons(actions, save_cmd, cancel_cmd):
    ctk.CTkButton(
        actions,
        text="Save",
        command=save_cmd,
        width=96,
        height=32,
        corner_radius=9,
        fg_color=SUCCESS,
        hover_color=SUCCESS_H,
        text_color="#07130D",
        font=("Segoe UI", 11, "bold")
    ).pack(side="left")

    ctk.CTkButton(
        actions,
        text="Cancel",
        command=cancel_cmd,
        width=96,
        height=32,
        corner_radius=9,
        fg_color=DANGER,
        hover_color=DANGER_H,
        text_color="#FFFFFF",
        font=("Segoe UI", 11, "bold")
    ).pack(side="right")


# ------------------------------------------------------------
# CONFIG FUNCTIONS
# ------------------------------------------------------------
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
        if config_fase3_visible:
            nascondi_config_fase3()

        btn_config_fase2.configure(
            fg_color=ACCENT_DIM,
            border_width=1,
            border_color=ACCENT,
            text_color=TEXT_A
        )

        config_path = os.path.join(paths['project_root'], "Scripts", "Auto Sub ReTimer", "Config_Fase2.json")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                "picco_audio_threshold": 500,
                "max_range_picco": 800,
                "lead_in": 180,
                "lead_out": 395
            }

        frame, body, actions = _config_shell("Fase2 Configuration", nascondi_config_fase2)

        fields = [
            ("Peak detection margin after initial timestamp (ms):", "picco_audio_threshold", config["picco_audio_threshold"]),
            ("Peak detection margin before final timestamp (ms):", "max_range_picco", config["max_range_picco"]),
            ("Add Lead-in, don't set too high value (ms):", "lead_in", config["lead_in"]),
            ("Add Lead-out, don't set too high value (ms):", "lead_out", config["lead_out"])
        ]

        for i, (label, key, value) in enumerate(fields):
            _config_entry_cell(body, i // 2, i % 2, label, key, value)

        _config_action_buttons(actions, salva_config_fase2, nascondi_config_fase2)
        config_entries["fase2_frame"] = frame

    else:
        nascondi_config_fase2()


def nascondi_config_fase2():
    global config_fase2_visible

    btn_config_fase2.configure(
        fg_color=BG_PANEL,
        border_width=1,
        border_color=BORDER,
        text_color=TEXT_2
    )

    if "fase2_frame" in config_entries:
        config_entries["fase2_frame"].pack_forget()
        config_entries["fase2_frame"].destroy()

    for key in ["picco_audio_threshold", "max_range_picco", "lead_in", "lead_out", "fase2_frame"]:
        config_entries.pop(key, None)

    config_fase2_visible = False


def salva_config_fase2():
    try:
        config_path = os.path.join(paths['project_root'], "Scripts", "Auto Sub ReTimer", "Config_Fase2.json")

        new_config = {
            "picco_audio_threshold": int(config_entries["picco_audio_threshold"].get()),
            "max_range_picco": int(config_entries["max_range_picco"].get()),
            "lead_in": int(config_entries["lead_in"].get()),
            "lead_out": int(config_entries["lead_out"].get())
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4)

        messagebox.showinfo("Success", "Configuration saved successfully!")
        nascondi_config_fase2()

    except ValueError:
        messagebox.showerror("Error", "Please enter only integer numbers")

    except Exception as e:
        messagebox.showerror("Error", f"Error while saving: {str(e)}")


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
        if config_fase3_visible:
            nascondi_config_fase3()

        btn_config_fase4.configure(
            fg_color=ACCENT_DIM,
            border_width=1,
            border_color=ACCENT,
            text_color=TEXT_A
        )

        config_path = os.path.join(paths['project_root'], "Scripts", "Auto Sub ReTimer", "Config_Fase4.json")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                "max_range_next_scene": 300,
                "gap_threshold": 280,
                "scene_change_before_threshold": 240,
                "scene_change_after_threshold": 200
            }

        frame, body, actions = _config_shell("Fase4 Configuration", nascondi_config_fase4)

        fields4 = [
            ("Max range to detect a scene change from the final timestamp (ms):", "max_range_next_scene", config["max_range_next_scene"]),
            ("Max gap 'empty' between two lines to attach (ms):", "gap_threshold", config.get("gap_threshold", 200)),
            ("Max range to detect scene change before the initial timestamp (ms):", "scene_change_before_threshold", config.get("scene_change_before_threshold", 200)),
            ("Max range to detect scene change after the initial timestamp (ms):", "scene_change_after_threshold", config.get("scene_change_after_threshold", 200)),
        ]

        for i, (label, key, value) in enumerate(fields4):
            _config_entry_cell(body, i // 2, i % 2, label, key, value)

        _config_action_buttons(actions, salva_config_fase4, nascondi_config_fase4)
        config_entries["fase4_frame"] = frame

    else:
        nascondi_config_fase4()


def nascondi_config_fase4():
    global config_fase4_visible

    btn_config_fase4.configure(
        fg_color=BG_PANEL,
        border_width=1,
        border_color=BORDER,
        text_color=TEXT_2
    )

    if "fase4_frame" in config_entries:
        config_entries["fase4_frame"].pack_forget()
        config_entries["fase4_frame"].destroy()

    for key in [
        "max_range_next_scene",
        "gap_threshold",
        "scene_change_before_threshold",
        "scene_change_after_threshold",
        "fase4_frame"
    ]:
        config_entries.pop(key, None)

    config_fase4_visible = False


def salva_config_fase4():
    try:
        config_path = os.path.join(paths['project_root'], "Scripts", "Auto Sub ReTimer", "Config_Fase4.json")

        new_config = {
            "max_range_next_scene": int(config_entries["max_range_next_scene"].get()),
            "gap_threshold": int(config_entries["gap_threshold"].get()),
            "scene_change_before_threshold": int(config_entries["scene_change_before_threshold"].get()),
            "scene_change_after_threshold": int(config_entries["scene_change_after_threshold"].get())
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4)

        messagebox.showinfo("Success", "Configuration saved successfully!")
        nascondi_config_fase4()

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
        if config_fase3_visible:
            nascondi_config_fase3()

        btn_config_whisper.configure(
            fg_color=ACCENT_DIM,
            border_width=1,
            border_color=ACCENT,
            text_color=TEXT_A
        )

        config_path = os.path.join(paths['project_root'], "Scripts", "Whisper", "whisper_config.json")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                "default_values": {"language": "ja", "model": "medium"},
                "options": {
                    "languages": WHISPER_LANGUAGES,
                    "models": WHISPER_MODELS
                }
            }

        frame, body, actions = _config_shell("Whisper Configuration", nascondi_config_whisper)

        lang_var = _config_option_cell(
            body, 0, 0,
            "Language:",
            config["options"]["languages"],
            config["default_values"]["language"]
        )

        model_var = _config_option_cell(
            body, 0, 1,
            "Model:",
            config["options"]["models"],
            config["default_values"]["model"]
        )

        config_entries["language"] = lang_var
        config_entries["model"] = model_var

        _config_action_buttons(actions, salva_config_whisper, nascondi_config_whisper)
        config_entries["whisper_frame"] = frame

    else:
        nascondi_config_whisper()


def nascondi_config_whisper():
    global config_whisper_visible

    btn_config_whisper.configure(
        fg_color=BG_PANEL,
        border_width=1,
        border_color=BORDER,
        text_color=TEXT_2
    )

    if "whisper_frame" in config_entries:
        config_entries["whisper_frame"].pack_forget()
        config_entries["whisper_frame"].destroy()

    for key in ["language", "model", "whisper_frame"]:
        config_entries.pop(key, None)

    config_whisper_visible = False


def salva_config_whisper():
    try:
        config_path = os.path.join(paths['project_root'], "Scripts", "Whisper", "whisper_config.json")

        new_config = {
            "default_values": {
                "language": config_entries["language"].get(),
                "model": config_entries["model"].get()
            },
            "options": {
                "languages": WHISPER_LANGUAGES,
                "models": WHISPER_MODELS
            }
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4)

        messagebox.showinfo("Success", "Whisper configuration saved successfully!")
        nascondi_config_whisper()

    except Exception as e:
        messagebox.showerror("Error", f"Error while saving: {str(e)}")


# ------------------------------------------------------------
# FASE3 CONFIG
# ------------------------------------------------------------
FASE3_CONFIG_DIRS = {
    "Auto Sub ReTimer": "Auto Sub ReTimer",
    "Auto Sub ReTimer CR": "Auto Sub ReTimer CR",
    "Whisper ReTimer": "Whisper ReTimer",
}

FASE3_DETECTORS = [
    ("pyscenedetect", "PySceneDetect"),
    ("transnetv2", "TransNetV2"),
]


def _config_fase3_path():
    return os.path.join(paths['project_root'], "Scripts", FASE3_CONFIG_DIRS[funzione_selezionata], "Config_Fase3.json")


def mostra_config_fase3():
    global config_fase3_visible

    if funzione_selezionata not in FASE3_CONFIG_DIRS:
        return

    config_fase3_visible = not config_fase3_visible

    if config_fase3_visible:
        if config_fase2_visible:
            nascondi_config_fase2()
        if config_fase4_visible:
            nascondi_config_fase4()
        if config_whisper_visible:
            nascondi_config_whisper()

        btn_config_fase3.configure(
            fg_color=ACCENT_DIM,
            border_width=1,
            border_color=ACCENT,
            text_color=TEXT_A
        )

        try:
            with open(_config_fase3_path(), "r", encoding="utf-8") as f:
                current = json.load(f).get("scene_detector", "pyscenedetect")
        except (OSError, ValueError, AttributeError):
            current = "pyscenedetect"

        labels = dict(FASE3_DETECTORS)

        frame, body, actions = _config_shell("Fase3 Configuration", nascondi_config_fase3)

        detector_var = _config_option_cell(
            body, 0, 0,
            "Scene detection model (use TransNetV2 if PyScene fails shot changes):",
            [label for _, label in FASE3_DETECTORS],
            labels.get(current, labels["pyscenedetect"]),
            colspan=2
        )

        _config_action_buttons(actions, salva_config_fase3, nascondi_config_fase3)

        config_fase3["frame"] = frame
        config_fase3["detector"] = detector_var

    else:
        nascondi_config_fase3()


def nascondi_config_fase3():
    global config_fase3_visible

    btn_config_fase3.configure(
        fg_color=BG_PANEL,
        border_width=1,
        border_color=BORDER,
        text_color=TEXT_2
    )

    if "frame" in config_fase3:
        config_fase3["frame"].pack_forget()
        config_fase3["frame"].destroy()

    config_fase3.clear()
    config_fase3_visible = False


def salva_config_fase3():
    try:
        label = config_fase3["detector"].get()
        detector = next(key for key, text in FASE3_DETECTORS if text == label)

        with open(_config_fase3_path(), "w", encoding="utf-8") as f:
            json.dump({"scene_detector": detector}, f, indent=4)

        messagebox.showinfo("Success", "Configuration saved successfully!")
        nascondi_config_fase3()

    except Exception as e:
        messagebox.showerror("Error", f"Error while saving: {str(e)}")


def aggiorna_visibilita_pulsanti_config():
    for btn in (btn_config_fase2, btn_config_fase3, btn_config_fase4, btn_config_whisper):
        btn.pack_forget()

    if funzione_selezionata == "Auto Sub ReTimer":
        btn_config_fase2.pack(side="left", padx=5)
        btn_config_fase3.pack(side="left", padx=5)
        btn_config_fase4.pack(side="left", padx=5)

        btn_config_fase2.configure(state="normal")
        btn_config_fase3.configure(state="normal")
        btn_config_fase4.configure(state="normal")

    elif funzione_selezionata == "Whisper":
        btn_config_whisper.pack(side="left", padx=5)
        btn_config_whisper.configure(state="normal")

    elif funzione_selezionata in ("Auto Sub ReTimer CR", "Whisper ReTimer"):
        btn_config_fase3.pack(side="left", padx=5)
        btn_config_fase3.configure(state="normal")

    nascondi_config_fase2()
    nascondi_config_fase3()
    nascondi_config_fase4()
    nascondi_config_whisper()


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
def setup_paths():
    try:
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(gui_dir, "..", ".."))

        paths = {
            'project_root': project_root,

            'retimer_scripts': {
                'fase0': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase0.py"),
                'fase1': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase1.py"),
                'fase2': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase2.py"),
                'fase3': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase3.py"),
                'fase4': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase4.py"),
                'fase5': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase5.py"),
                'fase6': os.path.join(project_root, "Scripts", "Auto Sub ReTimer", "Fase6.py")
            },

            'whisper_scripts': {
                'fase0': os.path.join(project_root, "Scripts", "Whisper", "Fase0.py"),
                'fase1': os.path.join(project_root, "Scripts", "Whisper", "Fase1.py"),
                'venv_python': sys.executable,
                'exe_folder': os.path.join(project_root, "Faster-Whisper-XXL"),
                'exe_file': os.path.join(project_root, "Faster-Whisper-XXL", "faster-whisper-xxl.exe"),
                'input_file': os.path.join(project_root, "whisper.aac")
            },

            'whisper_retimer': {
                'fase0': os.path.join(project_root, "Scripts", "Whisper ReTimer", "Fase0.py"),
                'whispertiming': os.path.join(project_root, "Scripts", "Whisper ReTimer", "whispertiming.py"),
                'fase3': os.path.join(project_root, "Scripts", "Whisper ReTimer", "Fase3.py"),
                'fase4': os.path.join(project_root, "Scripts", "Whisper ReTimer", "Fase4.py"),
                'fase5': os.path.join(project_root, "Scripts", "Whisper ReTimer", "Fase5.py")
            },

            'auto_sub_retimer_cr': {
                'base': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR"),
                'long_leads': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Long leads"),
                'short_leads': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Short leads"),
                'scripts': {
                    'fase0': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Fase0.py"),
                    'fase2': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Fase2.py"),
                    'fase3': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Fase3.py"),
                    'fase5': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Fase5.py"),
                    'fase6': os.path.join(project_root, "Scripts", "Auto Sub ReTimer CR", "Fase6.py")
                }
            },

            'timing_swap': {
                'script': os.path.join(project_root, "Scripts", "Tools", "TimingSwap.py")
            },

            'tools': {
                'text_correction': os.path.join(project_root, "Scripts", "Tools", "TextCorrection.py"),
                'oona_fix': os.path.join(project_root, "Scripts", "Tools", "OoonaFix.py")
            },

            'available': {
                'whisper': True,
                'retimer': True,
                'autosub': True,
                'autosub_cr': True,
                'timing_swap': True,
                'text_correction': True,
                'oona_fix': True
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

        cr_scripts = paths['auto_sub_retimer_cr']['scripts']
        all_cr_scripts_exist = True

        for script in cr_scripts.values():
            if not os.path.exists(script):
                missing_paths.append(f"Auto Sub ReTimer CR script not found: {script}")
                all_cr_scripts_exist = False
                break

        if all_cr_scripts_exist:
            paths['available']['autosub_cr'] = True
        else:
            paths['available']['autosub_cr'] = False

        if paths['available']['autosub_cr']:
            for folder in [paths['auto_sub_retimer_cr']['long_leads'], paths['auto_sub_retimer_cr']['short_leads']]:
                if not os.path.exists(os.path.join(folder, "Fase4.py")):
                    missing_paths.append(f"Missing Fase4.py in {folder}")
                    paths['available']['autosub_cr'] = False
                    break

                if not os.path.exists(os.path.join(folder, "Config_Fase4.json")):
                    missing_paths.append(f"Missing Config_Fase4.json in {folder}")
                    paths['available']['autosub_cr'] = False
                    break

        if not os.path.exists(paths['timing_swap']['script']):
            missing_paths.append(f"TimingSwap script not found: {paths['timing_swap']['script']}")
            paths['available']['timing_swap'] = False

        if not os.path.exists(paths['tools']['text_correction']):
            missing_paths.append(f"TextCorrection script not found: {paths['tools']['text_correction']}")
            paths['available']['text_correction'] = False

        if not os.path.exists(paths['tools']['oona_fix']):
            missing_paths.append(f"OoonaFix script not found: {paths['tools']['oona_fix']}")
            paths['available']['oona_fix'] = False

        if missing_paths:
            show_path_warning(missing_paths, gui_dir)

        return paths

    except Exception as e:
        messagebox.showerror("Error", f"Path configuration error: {str(e)}")
        return None


def show_path_warning(missing_paths, gui_dir):
    config_file = os.path.join(gui_dir, "gui_config.json")

    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                if config.get("suppress_path_warning", False):
                    return
        except Exception:
            pass

    dialog = ctk.CTkToplevel(root)
    dialog.title("Warning - Missing Paths")
    dialog.configure(fg_color=BG_PANEL)
    dialog.transient(root)
    dialog.grab_set()

    msg = "Some paths were not found:\n\n" + "\n".join(missing_paths) + "\n\nRelated features might not be available."

    ctk.CTkLabel(
        dialog,
        text=msg,
        justify="left",
        wraplength=560,
        text_color=TEXT_1,
        font=("Segoe UI", 15)
    ).pack(padx=20, pady=20, fill="both", expand=True)

    var = ctk.BooleanVar(value=False)

    check = ctk.CTkCheckBox(
        dialog,
        text="Don't show again",
        variable=var,
        text_color=TEXT_1,
        font=("Segoe UI", 15),
        fg_color=ACCENT,
        hover_color=ACCENT_H
    )
    check.pack(pady=8)

    def on_ok():
        if var.get():
            config = {}
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception:
                    pass

            config["suppress_path_warning"] = True

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

        dialog.destroy()

    ctk.CTkButton(
        dialog,
        text="OK",
        command=on_ok,
        fg_color=ACCENT,
        hover_color=ACCENT_H,
        font=("Segoe UI", 12, "bold")
    ).pack(pady=10)
    center_window(dialog, 550, 250)

    dialog.wait_window()


def precompile_modules():
    try:
        import py_compile
        import glob

        script_files = list(paths['retimer_scripts'].values())
        script_files += list(paths['auto_sub_retimer_cr']['scripts'].values())

        for folder in [paths['auto_sub_retimer_cr']['long_leads'], paths['auto_sub_retimer_cr']['short_leads']]:
            script_files.append(os.path.join(folder, "Fase4.py"))

        script_files.append(paths['whisper_scripts']['fase0'])
        script_files.append(paths['whisper_scripts']['fase1'])
        script_files.append(paths['timing_swap']['script'])
        script_files.append(paths['tools']['text_correction'])
        script_files.append(paths['tools']['oona_fix'])
        script_files.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "GUI.py"))
        script_files.append(os.path.join(paths['project_root'], "Scripts", "Engine", "run_transnet.py"))
        script_files.append(os.path.join(paths['project_root'], "Scripts", "Engine", "run_demucs.py"))

        for module_file in script_files:
            try:
                if not module_file.endswith(".py") or not os.path.exists(module_file):
                    continue

                module_dir = os.path.dirname(module_file)
                module_base = os.path.splitext(os.path.basename(module_file))[0]
                pyc_pattern = os.path.join(module_dir, "__pycache__", f"{module_base}.*.pyc")
                existing_pyc = glob.glob(pyc_pattern)

                if not existing_pyc:
                    py_compile.compile(module_file, doraise=True)

            except Exception as e:
                print(f"Precompilation error {os.path.basename(module_file)}: {e}")

    except Exception as e:
        print(f"Precompilation error: {e}")


paths = setup_paths()

if paths is None:
    sys.exit(1)

root.after(2000, lambda: threading.Thread(target=precompile_modules, daemon=True).start())
sys.path.insert(0, os.path.join(paths['project_root'], "Scripts", "Auto Sub ReTimer"))


# ------------------------------------------------------------
# INPUT HANDLER
# ------------------------------------------------------------
class InputHandler:
    def __init__(self, root):
        self.root = root
        self.response = None
        self.event = threading.Event()
        self._dialog = None

    def ask_question(self, question, options):
        self.response = None
        self.event.clear()
        self.root.after(0, self._create_dialog, question, options)
        self.event.wait()
        return self.response

    def _create_dialog(self, question, options):
        dialog = ctk.CTkToplevel(self.root)
        self._dialog = dialog

        dialog.title("Input Required")
        dialog.configure(fg_color=BG_PANEL)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_response(None, dialog))

        ctk.CTkLabel(
            dialog,
            text=question,
            font=("Segoe UI", 13),
            text_color=TEXT_1,
            wraplength=500
        ).pack(pady=28, padx=18)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=8)

        for idx, option in enumerate(options, 1):
            btn = ctk.CTkButton(
                btn_frame,
                text=option,
                command=lambda opt=idx: self._set_response(opt, dialog),
                width=150,
                height=38,
                fg_color=ACCENT,
                hover_color=ACCENT_H,
                font=("Segoe UI", 12, "bold"),
                corner_radius=10
            )
            btn.pack(side="left", padx=6)
        center_window(dialog, 460, 180)

    def _set_response(self, response, dialog):
        self.response = response
        self._dialog = None
        dialog.destroy()
        self.event.set()

    def cancel(self):
        self.response = None
        d = getattr(self, "_dialog", None)

        if d is not None:
            try:
                d.destroy()
            except Exception:
                pass
            self._dialog = None

        self.event.set()


input_handler = InputHandler(root)


# ------------------------------------------------------------
# PROGRESS MANAGER
# ------------------------------------------------------------
class ProgressManager:
    def __init__(self):
        self.total_phases = 7
        self.current_phase = 0
        self.phase_progress = 0
        self.phase_weights = {
            0: 15,
            1: 20,
            2: 15,
            3: 15,
            4: 15,
            5: 15,
            6: 5
        }
        self.is_idle = True
        self.active_phases = set()
        self.completed_phases = set()

    def update_phase(self, phase_num):
        self.phase_progress = 0
        self.current_phase = phase_num
        self.is_idle = False
        self.active_phases = {phase_num}
        self._update_display()

    def update_progress(self, progress):
        self.phase_progress = progress
        self._update_display()

    def complete_all(self):
        self.current_phase = self.total_phases
        self.phase_progress = 100
        self.is_idle = False
        self.active_phases = set()
        self._update_display()

    def reset(self):
        self.current_phase = 0
        self.phase_progress = 0
        self.is_idle = True
        self.active_phases = set()
        self.completed_phases = set()
        self._update_display()

    def set_parallel_active(self, phases, display_phase):
        self.active_phases = set(phases)
        self.completed_phases = set()
        self.current_phase = display_phase
        self.phase_progress = 0
        self.is_idle = False
        self._update_display()

    def mark_done(self, phase_num):
        self.active_phases.discard(phase_num)
        self.completed_phases.add(phase_num)
        self._update_display()

    def _update_display(self):
        if self.is_idle:
            set_status("Status: Inactive", "idle")
        else:
            set_status(
                f"Status: Fase {self.current_phase} ({int(self.phase_progress)}%)",
                "running"
            )


phase_pill_labels = []
progress_manager = ProgressManager()
output_queue = Queue()

_LOG_CLEAR = object()


# ------------------------------------------------------------
# INSTRUCTIONS / MENU STATE
# ------------------------------------------------------------
instructions_visible = _load_gui_config().get("instructions_visible", False)
DASH_MAX_WIDTH = 750


# ------------------------------------------------------------
# CUSTOM DROPDOWN
# ------------------------------------------------------------
def open_dropdown(anchor_widget, options):
    dropdown = tk.Toplevel(root)
    dropdown.overrideredirect(True)
    dropdown.configure(bg=BORDER)
    dropdown.attributes("-topmost", True)

    x = anchor_widget.winfo_rootx()
    y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 2
    dropdown.geometry(f"+{x}+{y}")

    inner = tk.Frame(dropdown, bg=BG_CARD)
    inner.pack(padx=1, pady=1)

    _open_time = time.time()

    def close(event=None):
        if not dropdown.winfo_exists():
            return

        for seq in ("<Button-1>", "<Escape>"):
            try:
                root.unbind_all(seq)
            except Exception:
                pass

        dropdown.destroy()

    def _on_any_click(event):
        if not dropdown.winfo_exists():
            return

        if time.time() - _open_time < 0.15:
            return

        try:
            under = dropdown.winfo_containing(event.x_root, event.y_root)
        except Exception:
            under = None

        if under is None or not str(under).startswith(str(dropdown)):
            close()

    root.bind_all("<Button-1>", _on_any_click, add="+")
    root.bind_all("<Escape>", close, add="+")

    def close_now():
        close()

    for opt in options:
        reset_cmd = opt.get("reset_command")

        if reset_cmd is None:
            item = tk.Label(
                inner,
                text="     " + opt["label"],
                bg=BG_CARD,
                fg=TEXT_1,
                font=("Segoe UI", 11),
                anchor="w",
                padx=14,
                pady=9,
                width=28
            )
            item.pack(fill="x")

            def on_enter(e, w=item):
                w.configure(bg=ACCENT, fg="#FFFFFF")

            def on_leave(e, w=item):
                w.configure(bg=BG_CARD, fg=TEXT_1)

            def on_click(e, cmd=opt["command"]):
                close_now()
                if cmd is not None:
                    cmd()

            item.bind("<Enter>", on_enter)
            item.bind("<Leave>", on_leave)
            item.bind("<Button-1>", on_click)

        else:
            row = tk.Frame(inner, bg=BG_CARD)
            row.pack(fill="x")

            main = tk.Label(
                row,
                text="     " + opt["label"],
                bg=BG_CARD,
                fg=TEXT_1,
                font=("Segoe UI", 11),
                anchor="w",
                padx=14,
                pady=9,
                width=25
            )
            main.pack(side="left", fill="x", expand=True)

            reset = tk.Label(
                row,
                text=" ↺ ",
                bg=BG_CARD,
                fg=TEXT_2,
                font=("Segoe UI", 12, "bold"),
                padx=4,
                pady=9
            )
            reset.pack(side="right")

            def _hover_on(e=None):
                row.configure(bg=ACCENT)
                main.configure(bg=ACCENT, fg="#FFFFFF")
                reset.configure(bg=ACCENT, fg="#FFFFFF")

            def _hover_off(e=None):
                row.configure(bg=BG_CARD)
                main.configure(bg=BG_CARD, fg=TEXT_1)
                reset.configure(bg=BG_CARD, fg=TEXT_2)

            def _click_main(e, cmd=opt["command"]):
                close_now()
                if cmd is not None:
                    cmd()

            def _click_reset(e, cmd=reset_cmd):
                close_now()
                if cmd is not None:
                    cmd()

            main.bind("<Enter>", _hover_on)
            main.bind("<Leave>", _hover_off)
            main.bind("<Button-1>", _click_main)

            reset.bind("<Enter>", _hover_on)
            reset.bind("<Leave>", _hover_off)
            reset.bind("<Button-1>", _click_reset)


def _toggle_instructions_view():
    global instructions_visible

    instructions_visible = not instructions_visible

    if instructions_visible:
        _build_instructions_panel()

    if _instr_switch is not None:
        try:
            if instructions_visible:
                _instr_switch.select()
            else:
                _instr_switch.deselect()
        except Exception:
            pass

    if _body_mode != "options":
        _layout_body("dashboard")

    _save_gui_config_key("instructions_visible", instructions_visible)


def _open_file_menu():
    open_dropdown(btn_menu_file, [
        {"label": "Exit", "command": lambda: root.destroy()},
    ])


def _toggle_debug_run():
    global debug_armed

    if is_running:
        messagebox.showwarning("Debug run", "Wait for the current process to finish.")
        return

    debug_armed = not debug_armed
    btn_menu_help.configure(text_color=DANGER if debug_armed else TEXT_2)

    if debug_armed:
        set_status("Status: Debug run armed", "debug")
        messagebox.showinfo(
            "Debug run",
            "Debug run enabled for the next START.\n\n"
            "The process runs as usual, but a detailed log is saved on your Desktop "
            "(AutoSubReTimer_debug ....txt).\n"
            "Before starting it checks the system and the engine: it can take a few minutes.\n\n"
            "When it finishes, send that file to the developers."
        )
    else:
        set_status("Status: Inactive", "idle")


def _open_help_menu():
    open_dropdown(btn_menu_help, [
        {
            "label": "Cancel debug run" if debug_armed else "Debug run (detailed log)",
            "command": _toggle_debug_run
        },
        {
            "label": "GitHub Repository",
            "command": lambda: webbrowser.open("https://github.com/AndryOut/AutoSubReTimer")
        },
        {
            "label": "About",
            "command": lambda: messagebox.showinfo(
                "About",
                "Auto Sub ReTimer\nby AndryOut · HonyakuSubs\n\nSubtitle timing improvement tool."
            )
        },
    ])


def _open_tools_menu():
    options = []

    if paths['available']['text_correction']:
        options.append({
            "label": "TextCorrection",
            "command": lambda: threading.Thread(target=esegui_text_correction, daemon=True).start()
        })

    if paths['available']['oona_fix']:
        options.append({
            "label": "OoonaFix",
            "command": lambda: threading.Thread(target=esegui_oona_fix, daemon=True).start()
        })

    if paths['available']['timing_swap']:
        options.append({
            "label": "TimingSwap",
            "command": lambda: threading.Thread(target=esegui_timing_swap, daemon=True).start()
        })

    if not options:
        options.append({"label": "No tools available", "command": None})

    open_dropdown(btn_menu_tools, options)


# ------------------------------------------------------------
# OUTPUT FOLDER / OPTIONS (internal page)
# ------------------------------------------------------------
def _get_output_state():
    cfg = _load_gui_config()
    out = cfg.get("output_dir")

    if out and os.path.isdir(out):
        return True, os.path.abspath(out)

    return False, None


def _refresh_options_output_ui():
    if _options_output_mode_label is None or _options_output_path_label is None:
        return

    custom, out = _get_output_state()

    if custom:
        _options_output_mode_label.configure(
            text="Custom",
            fg_color=ACCENT_DIM,
            text_color=TEXT_A
        )
        _options_output_path_label.configure(text=out)
    else:
        _options_output_mode_label.configure(
            text="Default",
            fg_color=P_DONE_BG,
            text_color=P_DONE_T
        )
        _options_output_path_label.configure(
            text="Files will be saved in the input/project folder."
        )


def scegli_output_dir():
    cfg = _load_gui_config()
    current = cfg.get("output_dir") or paths['project_root']

    chosen = filedialog.askdirectory(
        parent=root,
        title="Choose output folder (Cancel = keep current)",
        initialdir=current,
        mustexist=True,
    )

    if not chosen:
        return

    _save_gui_config_key("output_dir", os.path.abspath(chosen))
    _refresh_options_output_ui()

    messagebox.showinfo(
        "Output Folder",
        f"Output folder set to:\n{chosen}"
    )


def reset_output_dir():
    cfg = _load_gui_config()
    cfg.pop("output_dir", None)

    try:
        with open(GUI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        messagebox.showerror("Output Folder", f"Error while resetting: {e}")
        return

    _refresh_options_output_ui()

    messagebox.showinfo(
        "Output Folder",
        "Output folder reset to default (input folder)."
    )


# ------------------------------------------------------------
# ENGINE MANAGER
# ------------------------------------------------------------
ENGINE_CONFIRM = {
    "gpu": "Enable the NVIDIA GPU for Demucs and TransNetV2?\nIt downloads about 3.3 GB and rebuilds the engine.",
    "cpu": "Switch Demucs to CPU only?\nThe engine will be rebuilt.",
    "repair": "Reinstall the whole engine?\nIt can take several minutes.",
}


def esegui_engine_manager(command):
    if is_running and command != "status":
        messagebox.showwarning("Engine", "Wait for the current process to finish.")
        return

    if command in ENGINE_CONFIRM and not messagebox.askyesno("Engine", ENGINE_CONFIRM[command]):
        return

    manager = os.path.join(paths['project_root'], "Scripts", "Engine", "engine_manager.py")

    if not os.path.exists(manager):
        messagebox.showerror("Engine", f"Script not found: {manager}")
        return

    subprocess.Popen(
        [sys.executable, manager, command, "--pause"],
        cwd=paths['project_root'],
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    )


# ------------------------------------------------------------
# MENU BAR
# ------------------------------------------------------------
menu_strip = ctk.CTkFrame(
    root,
    height=40,
    corner_radius=0,
    fg_color=BG_PANEL,
    border_width=0
)
menu_strip.pack(side="top", fill="x")
menu_strip.pack_propagate(False)


def _menu_button(parent, text, command, width=56):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=30,
        corner_radius=8,
        fg_color="transparent",
        hover_color=ACCENT_DIM,
        text_color=TEXT_2,
        font=("Segoe UI", 12)
    )


btn_menu_file = _menu_button(menu_strip, "File", _open_file_menu)
btn_menu_file.pack(side="left", padx=(6, 2))

btn_menu_tools = _menu_button(menu_strip, "Tools", _open_tools_menu)
btn_menu_tools.pack(side="left", padx=2)

btn_menu_options = _menu_button(menu_strip, "Options", lambda: _open_options_panel(), width=66)
btn_menu_options.pack(side="left", padx=2)

btn_menu_help = _menu_button(menu_strip, "Help", _open_help_menu)
btn_menu_help.pack(side="left", padx=2)

_menu_strip_border = ctk.CTkFrame(
    root,
    height=1,
    fg_color=BORDER,
    corner_radius=0
)
_menu_strip_border.pack(side="top", fill="x")


# ------------------------------------------------------------
# ICON RAIL
# ------------------------------------------------------------
frame_left = ctk.CTkFrame(
    root,
    width=76,
    corner_radius=0,
    fg_color=BG_PANEL,
    border_width=0
)
frame_left.pack(side="left", fill="y")
frame_left.pack_propagate(False)

_rail_separator = ctk.CTkFrame(root, width=1, fg_color=BORDER, corner_radius=0)
_rail_separator.pack(side="left", fill="y")

_logo_badge = ctk.CTkLabel(
    frame_left,
    text="ASR",
    width=42,
    height=42,
    corner_radius=13,
    fg_color=ACCENT,
    text_color="#FFFFFF",
    font=("Segoe UI", 13, "bold")
)
_logo_badge.pack(pady=(18, 6))

ctk.CTkFrame(
    frame_left,
    height=1,
    fg_color=BORDER,
    corner_radius=0
).pack(fill="x", padx=14, pady=(4, 14))

button_autosub = ctk.CTkButton(
    frame_left,
    text="AS",
    command=lambda: seleziona_funzione("Auto Sub ReTimer"),
    width=52,
    height=52,
    corner_radius=10,
    font=("Segoe UI", 13, "bold"),
    fg_color="transparent",
    hover_color=ACCENT_DIM,
    text_color=TEXT_2,
    border_width=1,
    border_color=BG_PANEL
)
button_autosub.pack(pady=5)

button_autosub_cr = ctk.CTkButton(
    frame_left,
    text="CR",
    command=lambda: seleziona_funzione("Auto Sub ReTimer CR"),
    width=52,
    height=52,
    corner_radius=10,
    font=("Segoe UI", 13, "bold"),
    fg_color="transparent",
    hover_color=ACCENT_DIM,
    text_color=TEXT_2,
    border_width=1,
    border_color=BG_PANEL
)
button_autosub_cr.pack(pady=5)

button_whisper = ctk.CTkButton(
    frame_left,
    text="WH",
    command=lambda: seleziona_funzione("Whisper"),
    width=52,
    height=52,
    corner_radius=10,
    font=("Segoe UI", 13, "bold"),
    fg_color="transparent",
    hover_color=ACCENT_DIM,
    text_color=TEXT_2,
    border_width=1,
    border_color=BG_PANEL
)
button_whisper.pack(pady=5)

button_retimer = ctk.CTkButton(
    frame_left,
    text="WHR",
    command=lambda: seleziona_funzione("Whisper ReTimer"),
    width=52,
    height=52,
    corner_radius=10,
    font=("Segoe UI", 13, "bold"),
    fg_color="transparent",
    hover_color=ACCENT_DIM,
    text_color=TEXT_2,
    border_width=1,
    border_color=BG_PANEL
)
button_retimer.pack(pady=5)


# ------------------------------------------------------------
# BODY FRAMES
# ------------------------------------------------------------
frame_body = ctk.CTkFrame(root, fg_color=BG_ROOT, corner_radius=0)
frame_body.pack(side="left", fill="both", expand=True)

frame_center = ctk.CTkFrame(
    frame_body,
    corner_radius=12,
    fg_color=BG_CARD,
    border_width=1,
    border_color=BORDER
)

frame_right = ctk.CTkFrame(
    frame_body,
    width=280,
    corner_radius=12,
    fg_color=BG_CARD,
    border_width=1,
    border_color=BORDER_ACC
)
frame_right.pack_propagate(False)


# ------------------------------------------------------------
# INTERNAL OPTIONS PAGE
# ------------------------------------------------------------
options_page = ctk.CTkFrame(frame_body, fg_color=BG_ROOT, corner_radius=0)

_instr_switch = None
_options_output_mode_label = None
_options_output_path_label = None
_options_built = False


def _options_section(parent, title, subtitle=""):
    card = ctk.CTkFrame(
        parent,
        fg_color=BG_PANEL,
        corner_radius=14,
        border_width=1,
        border_color=BORDER
    )
    card.pack(fill="x", pady=(0, 12))

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=16, pady=12)

    ctk.CTkLabel(
        inner,
        text=title,
        font=("Segoe UI", 13, "bold"),
        text_color=TEXT_1,
        anchor="w"
    ).pack(fill="x")

    if subtitle:
        ctk.CTkLabel(
            inner,
            text=subtitle,
            font=("Segoe UI", 12),
            text_color=TEXT_2,
            justify="left",
            anchor="w",
            wraplength=600
        ).pack(fill="x", pady=(2, 0))

    return inner


def _options_button(parent, text, command, kind="neutral", width=170):
    styles = {
        "accent":  (ACCENT, ACCENT_H, "#FFFFFF", 0),
        "danger":  (DANGER, DANGER_H, "#FFFFFF", 0),
        "neutral": (BG_CARD, BG_INPUT, TEXT_1, 1),
    }

    fg, hover, txt, border = styles.get(kind, styles["neutral"])

    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=36,
        corner_radius=10,
        fg_color=fg,
        hover_color=hover,
        text_color=txt,
        font=("Segoe UI", 12, "bold"),
        border_width=border,
        border_color=BORDER,
        width=width
    )


def _build_options_page():
    global _instr_switch, _options_output_mode_label, _options_output_path_label
    global _options_built

    if _options_built:
        return

    _op_header = ctk.CTkFrame(options_page, fg_color=BG_PANEL, corner_radius=0)
    _op_header.pack(fill="x")

    ctk.CTkButton(
        _op_header,
        text="←  Back",
        command=lambda: _open_options_panel(),
        width=80,
        height=32,
        corner_radius=9,
        fg_color=BG_CARD,
        hover_color=ACCENT_DIM,
        text_color=TEXT_1,
        font=("Segoe UI", 11, "bold"),
        border_width=1,
        border_color=BORDER
    ).pack(side="left", padx=18, pady=12)

    ctk.CTkLabel(
        _op_header,
        text="Options",
        font=("Segoe UI", 16, "bold"),
        text_color=TEXT_1
    ).pack(side="left", padx=(10, 0))

    ctk.CTkFrame(options_page, height=1, fg_color=BORDER, corner_radius=0).pack(fill="x")

    _op_wrap = ctk.CTkFrame(options_page, fg_color="transparent", width=750)
    _op_wrap.pack(fill="y", expand=True, anchor="n", pady=(12, 0))
    _op_wrap.pack_propagate(False)

    # View card
    _view_inner = _options_section(
        _op_wrap,
        "View",
        "Interface visibility options."
    )

    _instr_switch = ctk.CTkSwitch(
        _view_inner,
        text="Show instructions panel",
        command=_toggle_instructions_view,
        text_color=TEXT_1,
        font=("Segoe UI", 11),
        fg_color=ACCENT,
        button_hover_color=ACCENT_H,
        progress_color=ACCENT
    )
    _instr_switch.pack(anchor="w", pady=(8, 4))

    if instructions_visible:
        _instr_switch.select()
    else:
        _instr_switch.deselect()

    # Output card
    _out_inner = _options_section(
        _op_wrap,
        "Output folder",
        "Choose where final files should be saved. Default uses the input/project folder."
    )

    _out_state_row = ctk.CTkFrame(_out_inner, fg_color="transparent")
    _out_state_row.pack(fill="x", pady=(10, 6))

    _options_output_mode_label = ctk.CTkLabel(
        _out_state_row,
        text="Default",
        width=80,
        height=24,
        corner_radius=999,
        fg_color=P_DONE_BG,
        text_color=P_DONE_T,
        font=("Segoe UI", 10, "bold")
    )
    _options_output_mode_label.pack(side="left")

    _options_output_path_label = ctk.CTkLabel(
        _out_inner,
        text="",
        font=("Consolas", 11),
        text_color=TEXT_1,
        justify="left",
        anchor="w",
        wraplength=620
    )
    _options_output_path_label.pack(fill="x", pady=(0, 10))

    _out_buttons = ctk.CTkFrame(_out_inner, fg_color="transparent")
    _out_buttons.pack(fill="x")

    _options_button(_out_buttons, "Choose folder…", scegli_output_dir, kind="accent", width=170).pack(side="left", padx=(0, 8))
    _options_button(_out_buttons, "Reset to default", reset_output_dir, kind="neutral", width=170).pack(side="left")

    # Engine card
    _engine_inner = _options_section(
        _op_wrap,
        "Engine",
        "Manage Demucs / TransNetV2 engine. These actions open a separate console."
    )

    _engine_grid = ctk.CTkFrame(_engine_inner, fg_color="transparent")
    _engine_grid.pack(fill="x", pady=(8, 0))
    _engine_grid.columnconfigure((0, 1), weight=1)

    _options_button(_engine_grid, "Enable GPU", lambda: esegui_engine_manager("gpu"), kind="accent", width=200).grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
    _options_button(_engine_grid, "CPU only", lambda: esegui_engine_manager("cpu"), kind="neutral", width=200).grid(row=0, column=1, sticky="ew", pady=(0, 8))
    _options_button(_engine_grid, "Repair engine", lambda: esegui_engine_manager("repair"), kind="danger", width=200).grid(row=1, column=0, sticky="ew", padx=(0, 8))
    _options_button(_engine_grid, "Engine status", lambda: esegui_engine_manager("status"), kind="neutral", width=200).grid(row=1, column=1, sticky="ew")

    _options_built = True

def _open_options_panel():
    global _body_mode

    if _body_mode == "options":
        _layout_body("dashboard")
    else:
        _build_options_page()
        _refresh_options_output_ui()
        _layout_body("options")

def _layout_body(mode):
    global _body_mode

    _body_mode = mode

    for w in (frame_center, frame_right, options_page):
        try:
            w.pack_forget()
        except Exception:
            pass

    if mode == "options":
        options_page.pack(side="left", fill="both", expand=True, padx=14, pady=14)
    else:
        if instructions_visible:
            frame_right.pack(side="right", fill="y", padx=(0, 14), pady=14)

        frame_center.pack(side="left", fill="both", expand=True, padx=14, pady=14)


# ------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------
content_wrap = ctk.CTkFrame(frame_center, fg_color="transparent", width=DASH_MAX_WIDTH)
content_wrap.pack(fill="y", expand=True, anchor="n")
content_wrap.pack_propagate(False)

hero_card = ctk.CTkFrame(
    content_wrap,
    fg_color=BG_PANEL,
    corner_radius=14,
    border_width=1,
    border_color=BORDER
)
hero_card.pack(fill="x", padx=6, pady=(14, 10))

_hero_head = ctk.CTkFrame(hero_card, fg_color="transparent")
_hero_head.pack(fill="x", padx=16, pady=(12, 2))

dash_title_label = ctk.CTkLabel(
    _hero_head,
    text="Auto Sub ReTimer",
    font=("Segoe UI", 18, "bold"),
    text_color=TEXT_1
)
dash_title_label.pack(side="left")

execution_time_label = ctk.CTkLabel(
    _hero_head,
    text="00:00:00",
    font=("Consolas", 11),
    text_color=TEXT_2,
    corner_radius=999,
    fg_color=BG_INPUT,
    width=84,
    height=26
)
execution_time_label.pack(side="right", padx=(8, 0))

status_label = ctk.CTkLabel(
    _hero_head,
    text="Status: Inactive",
    width=180,
    height=26,
    corner_radius=999,
    fg_color=BG_INPUT,
    text_color=TEXT_2,
    font=("Segoe UI", 11, "bold")
)
status_label.pack(side="right")

ctk.CTkLabel(
    hero_card,
    text="Pipeline progress",
    font=("Segoe UI", 10),
    text_color=TEXT_2
).pack(anchor="w", padx=16)

progress_bar = ctk.CTkProgressBar(
    hero_card,
    height=14,
    corner_radius=7,
    progress_color=ACCENT,
    fg_color=BG_INPUT
)
progress_bar.pack(fill="x", padx=16, pady=(2, 4))
progress_bar.set(0)

progress_label = ctk.CTkLabel(
    hero_card,
    text="Completion: 0%",
    font=("Segoe UI", 10),
    text_color=TEXT_2
)
progress_label.pack(anchor="e", padx=16)

pills_row = ctk.CTkFrame(hero_card, fg_color="transparent")
pills_row.pack(fill="x", padx=16, pady=(8, 14))


def rebuild_phase_pills(function_name):
    global phase_pill_labels

    for pill in phase_pill_labels:
        pill.destroy()

    phase_pill_labels.clear()

    phase_names = PHASE_MAP.get(
        function_name,
        ["F0", "F1", "F2", "F3", "F4", "F5", "F6"]
    )

    for name in phase_names:
        _pill = ctk.CTkLabel(
            pills_row,
            text=name,
            width=70,
            height=44,
            fg_color=P_IDLE_BG,
            text_color=P_IDLE_T,
            corner_radius=10,
            font=("Segoe UI", 10.5, "bold")
        )
        _pill.pack(side="left", padx=3, expand=True)
        phase_pill_labels.append(_pill)

    progress_manager.reset()

config_buttons_frame = ctk.CTkFrame(content_wrap, fg_color="transparent")
config_buttons_frame.pack(fill="x", padx=6, pady=(0, 4))


def _make_config_button(text, command, width=110):
    return ctk.CTkButton(
        config_buttons_frame,
        text=text,
        command=command,
        width=width,
        height=30,
        corner_radius=9,
        fg_color=BG_PANEL,
        hover_color=ACCENT_DIM,
        text_color=TEXT_2,
        font=("Segoe UI", 12),
        border_width=1,
        border_color=BORDER
    )


btn_config_fase2 = _make_config_button("⚙  Fase2", mostra_config_fase2, 110)
btn_config_fase3 = _make_config_button("⚙  Fase3", mostra_config_fase3, 110)
btn_config_fase4 = _make_config_button("⚙  Fase4", mostra_config_fase4, 110)
btn_config_whisper = _make_config_button("⚙  Whisper", mostra_config_whisper, 120)

btn_config_fase2.configure(state="disabled")
btn_config_fase3.configure(state="disabled")
btn_config_fase4.configure(state="disabled")
btn_config_whisper.configure(state="disabled")

def _on_start_click():
    if is_running:
        return
    button_avvia.configure(state="disabled")
    threading.Thread(target=avvia_processo, daemon=True).start()


button_avvia = ctk.CTkButton(
    content_wrap,
    text="START",
    command=_on_start_click,
    height=52,
    font=("Segoe UI", 14, "bold"),
    fg_color=SUCCESS,
    hover_color=SUCCESS_H,
    corner_radius=12,
    text_color="#0B0B12"
)
button_avvia.pack(side="bottom", pady=(0, 14), fill="x", padx=6)

# Elastic area.
dynamic_area = ctk.CTkFrame(content_wrap, fg_color="transparent")
dynamic_area.pack(fill="both", expand=True)

_log_header_row = ctk.CTkFrame(
    dynamic_area,
    fg_color=BG_PANEL,
    corner_radius=10,
    border_width=1,
    border_color=BORDER
)
_log_header_row.pack(fill="x", padx=6, pady=(4, 0))

ctk.CTkLabel(
    _log_header_row,
    text="●",
    font=("Segoe UI", 10),
    text_color=SUCCESS
).pack(side="left", padx=(12, 6), pady=6)

ctk.CTkLabel(
    _log_header_row,
    text="O U T P U T   L O G",
    font=("Segoe UI", 10, "bold"),
    text_color=TEXT_2
).pack(side="left", pady=6)

log_text = tk.Text(
    dynamic_area,
    height=4,
    font=("Consolas", 11),
    wrap="word",
    bg=BG_INPUT,
    fg=TEXT_1,
    insertbackground=TEXT_1,
    relief="flat",
    bd=0,
    highlightthickness=0,
    padx=10,
    pady=8,
    state="disabled"
)
log_text.pack(fill="both", expand=True, padx=6, pady=(6, 4))

log_text.tag_configure("info", foreground=TEXT_1)
log_text.tag_configure("success", foreground=SUCCESS)
log_text.tag_configure("warning", foreground=WARNING)
log_text.tag_configure("error", foreground=DANGER, font=("Consolas", 11, "bold"))
log_text.tag_configure("accent", foreground=ACCENT_H)

log_text.configure(state="normal")
log_text.insert("1.0", "Ready to start...\n", "info")
log_text.configure(state="disabled")


# ------------------------------------------------------------
# INSTRUCTIONS PANEL
# ------------------------------------------------------------
class _NullTextbox:
    def __init__(self):
        self.content = ""

    def delete(self, *args, **kwargs):
        self.content = ""

    def insert(self, position, text, *args, **kwargs):
        self.content = text

    def pack(self, *args, **kwargs):
        pass


instructions_text = _NullTextbox()
_instructions_built = False


def _build_instructions_panel():
    global instructions_text, _instructions_built

    if _instructions_built:
        return

    _instr_header_row = ctk.CTkFrame(frame_right, fg_color="transparent")
    _instr_header_row.pack(fill="x", padx=16, pady=(18, 4))

    ctk.CTkLabel(
        _instr_header_row,
        text="Instructions",
        font=("Segoe UI", 13, "bold"),
        text_color=TEXT_1
    ).pack(side="left")

    ctk.CTkButton(
        _instr_header_row,
        text="✕",
        command=lambda: _toggle_instructions_view(),
        width=24,
        height=24,
        corner_radius=6,
        fg_color="transparent",
        hover_color=ACCENT_DIM,
        text_color=TEXT_2,
        font=("Segoe UI", 12)
    ).pack(side="right")

    ctk.CTkFrame(
        frame_right,
        height=1,
        fg_color=BORDER,
        corner_radius=0
    ).pack(fill="x", padx=16, pady=(0, 10))

    pending = instructions_text.content

    instructions_text = ctk.CTkTextbox(
        frame_right,
        font=("Segoe UI", 11),
        wrap="word",
        fg_color=BG_INPUT,
        text_color=TEXT_1,
        corner_radius=10,
        border_width=1,
        border_color=BORDER
    )
    instructions_text.pack(fill="both", expand=True, padx=14, pady=(0, 16))

    if pending:
        instructions_text.insert("1.0", pending)

    _instructions_built = True


if instructions_visible:
    _build_instructions_panel()


# ------------------------------------------------------------
# DEBUG UTILITIES
# ------------------------------------------------------------
def debug_write(text):
    if debug_file is None or not text:
        return

    stamp = time.strftime("%H:%M:%S")

    with debug_lock:
        if debug_file is None:
            return

        try:
            for line in str(text).rstrip("\n").split("\n"):
                debug_file.write(f"[{stamp}] {line}\n")
            debug_file.flush()
        except Exception:
            pass


def debug_exception():
    if debug_file is not None:
        debug_write(traceback.format_exc())


def _debug_drain(stream, prefix):
    try:
        for line in iter(stream.readline, ''):
            debug_write(f"  {prefix}| {line}")
    except Exception:
        debug_exception()

    try:
        while stream.buffer.read(4096):
            pass
    except Exception:
        pass


def _stderr_drain(stream, prefix, tail):
    try:
        for line in iter(stream.readline, ''):
            if line.strip():
                tail.append(line.rstrip())
            debug_write(f"  {prefix}| {line}")
    except Exception:
        debug_exception()

    try:
        while stream.buffer.read(4096):
            pass
    except Exception:
        pass


class _DebugTee:
    def __init__(self, stream, prefix):
        self.stream = stream
        self.prefix = prefix
        self.buf = ""

    def write(self, s):
        try:
            if self.stream is not None:
                self.stream.write(s)
        except Exception:
            pass

        self.buf += s.replace("\r", "\n")

        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if line.strip():
                debug_write(f"  {self.prefix}| {line}")

        return len(s)

    def flush(self):
        try:
            if self.stream is not None:
                self.stream.flush()
        except Exception:
            pass


# ------------------------------------------------------------
# LOG / TIMER / DISPLAY APPLY
# ------------------------------------------------------------
def log_message(message):
    output_queue.put(message)
    debug_write(message)


def log_clear():
    output_queue.put(_LOG_CLEAR)


def debug_begin(function_name):
    global debug_file, debug_path, debug_started

    diagnostics = None
    engine_dir = os.path.join(paths['project_root'], "Scripts", "Engine")

    if engine_dir not in sys.path:
        sys.path.insert(0, engine_dir)

    try:
        import diagnostics
        desktop = diagnostics.desktop_path()
    except Exception:
        desktop = os.path.expanduser("~")

    debug_path = os.path.join(desktop, time.strftime("AutoSubReTimer_debug_%Y-%m-%d_%H-%M-%S.txt"))

    try:
        debug_file = open(debug_path, "w", encoding="utf-8", errors="replace")
    except OSError as e:
        debug_file = None
        log_message(f"[Warn] Cannot create the debug log: {e}\n")
        return

    debug_started = time.time()

    debug_write(f"Auto Sub ReTimer debug log - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    debug_write(f"Function: {function_name}")
    debug_write(f"GUI: {sys.executable} (python {sys.version.split()[0]}, frozen={getattr(sys, 'frozen', False)})")
    debug_write(f"GUI config: {json.dumps(_load_gui_config())}")
    debug_write("")

    if diagnostics is None:
        debug_write("diagnostics.py not available: system check skipped")
        debug_exception()
    else:
        log_message("Debug: checking system and engine (it can take a few minutes)...\n")
        try:
            diagnostics.full_report(paths['project_root'], debug_write)
        except Exception:
            debug_exception()

    debug_write("")
    debug_write("=== RUN ===")


def debug_end():
    global debug_file, debug_armed

    if debug_file is None:
        return

    debug_write("")
    debug_write(f"=== END: {_pending_status[0]}, {time.time() - debug_started:.0f} s ===")

    with debug_lock:
        try:
            debug_file.close()
        except Exception:
            pass

    debug_file = None
    debug_armed = False
    btn_menu_help.configure(text_color=TEXT_2)

    log_message(f"Debug log saved on the Desktop: {os.path.basename(debug_path)}\n")

    root.after(0, lambda: messagebox.showinfo(
        "Debug run",
        f"Debug log saved:\n{debug_path}\n\nSend this file to the developers."
    ))


def update_timer():
    if start_time:
        elapsed = int(time.time() - start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        execution_time_label.configure(text=f"{hours:02}:{minutes:02}:{seconds:02}")

    root.after(1000, update_timer)


def _log_tag_for_line(line):
    s = line.strip().lower()

    if not s:
        return "info"

    if "error" in s or "traceback" in s or "failed" in s or "exception" in s:
        return "error"

    if "[warn]" in s or "warning" in s:
        return "warning"

    if "completed successfully" in s or "success" in s:
        return "success"

    if "[wait]" in s or "user input" in s:
        return "accent"

    return "info"


def update_log():
    while not output_queue.empty():
        msg = output_queue.get()

        if msg is _LOG_CLEAR:
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            log_text.configure(state="disabled")
            continue

        log_text.configure(state="normal")

        for raw_line in str(msg).splitlines(True):
            tag = _log_tag_for_line(raw_line)
            log_text.insert("end", raw_line, tag)

        log_text.see("end")
        log_text.configure(state="disabled")

    root.after(100, update_log)


def _apply_status():
    text, kind = _pending_status

    fg, tx = STATUS_STYLES.get(kind, STATUS_STYLES["idle"])
    status_label.configure(text=text, fg_color=fg, text_color=tx)


def _apply_progress_display():
    pm = progress_manager

    if pm.is_idle:
        progress_bar.set(0)
        progress_label.configure(text="Completion: 0%")

        for pill in phase_pill_labels:
            pill.configure(fg_color=P_IDLE_BG, text_color=P_IDLE_T)

        return

    completed_weight = sum(
        weight for phase, weight in pm.phase_weights.items()
        if phase < pm.current_phase
    )

    current_phase_weight = pm.phase_weights.get(pm.current_phase, 0)
    current_progress = (pm.phase_progress / 100) * current_phase_weight
    total_progress = min(completed_weight + current_progress, 100)

    progress_bar.set(total_progress / 100)
    progress_label.configure(text=f"Completion: {int(total_progress)}%")

    active_phases = [p for p, w in pm.phase_weights.items() if w > 0]

    for i, pill in enumerate(phase_pill_labels):
        if i < len(active_phases):
            phase_num = active_phases[i]

            if phase_num in pm.active_phases:
                pill.configure(fg_color=P_ACT_BG, text_color=P_ACT_T)
            elif phase_num in pm.completed_phases or phase_num < pm.current_phase:
                pill.configure(fg_color=P_DONE_BG, text_color=P_DONE_T)
            else:
                pill.configure(fg_color=P_IDLE_BG, text_color=P_IDLE_T)
        else:
            pill.configure(fg_color=P_IDLE_BG, text_color=P_IDLE_T)


def _display_poll_loop():
    global _display_dirty, _start_btn_req

    if _start_btn_req is not None:
        state = _start_btn_req
        _start_btn_req = None

        try:
            button_avvia.configure(state=state)
        except Exception:
            pass

    if _display_dirty:
        _display_dirty = False

        try:
            _apply_status()
            _apply_progress_display()
        except Exception:
            pass

    root.after(30 if is_running else 100, _display_poll_loop)


# ------------------------------------------------------------
# PROCESS HELPERS
# ------------------------------------------------------------
def parse_progress(output):
    match = PROGRESS_RE.search(output)

    if match:
        if match.group(1):
            return float(match.group(1))
        elif match.group(2) and match.group(3):
            return (float(match.group(2)) / float(match.group(3))) * 100

    return None


def _module_launch_args(python_exe, script_path):
    module_dir = os.path.dirname(script_path)
    module_name, ext = os.path.splitext(os.path.basename(script_path))

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = ":replace"

    if debug_file is not None:
        env["PYTHONFAULTHANDLER"] = "1"
        env["AUTOSUB_DEBUG"] = "1"

    if ext.lower() == ".py":
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = module_dir + (os.pathsep + existing_pp if existing_pp else "")
        return [python_exe, "-m", module_name], env

    return [python_exe, script_path], env


def kill_process_tree(pid):
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except Exception:
            pass
    else:
        try:
            os.kill(pid, 9)
        except Exception:
            pass


def run_interactive_phase(phase_num, phase_path, proc_registry=None, cancel_event=None, update_progress=True):
    global start_time

    phase_name = f"Fase {phase_num}"

    if update_progress:
        progress_manager.update_phase(phase_num)

    log_message(f"Running {phase_name}\n")

    process = None
    phase_start = time.time()
    stderr_tail = deque(maxlen=15)
    stderr_thread = None

    try:
        _args, _env = _module_launch_args(sys.executable, phase_path)
        debug_write(f"=== {phase_name}: {_args} ===")

        process = subprocess.Popen(
            _args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            bufsize=4096,
            universal_newlines=True,
            cwd=paths['project_root'],
            env=_env
        )

        stderr_thread = threading.Thread(
            target=_stderr_drain,
            args=(process.stderr, f"F{phase_num} stderr", stderr_tail),
            daemon=True
        )
        stderr_thread.start()

        if proc_registry is not None:
            proc_registry[phase_num] = process

        while True:
            if cancel_event is not None and cancel_event.is_set():
                break

            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                break

            if output:
                if "cartelli" in output.lower() or "scegli" in output.lower():
                    question = output.strip()
                    options = ["Sì", "No"] if "cartelli" in output.lower() else ["Option 1", "Option 2"]

                    if phase_num == 6:
                        start_time = None

                    answer = input_handler.ask_question(question, options)

                    if answer is None:
                        try:
                            process.terminate()
                        except Exception:
                            pass
                        return False

                    try:
                        process.stdin.write(f"{answer}\n")
                        process.stdin.flush()
                    except Exception:
                        pass

                progress = parse_progress(output)

                if progress is not None:
                    progress_manager.update_progress(progress)

                log_message(output)

        ok = process.returncode == 0

        if not ok and not (cancel_event is not None and cancel_event.is_set()):
            stderr_thread.join(2)
            if stderr_tail:
                log_message(f"{phase_name} error output:\n" + "\n".join(stderr_tail) + "\n")

        return ok

    except Exception as e:
        log_message(f"Error in {phase_name}: {str(e)}\n")
        debug_exception()
        return False

    finally:
        if process is not None:
            debug_write(f"=== {phase_name} exit code {process.returncode} ({time.time() - phase_start:.1f} s) ===")

        if proc_registry is not None and process is not None:
            proc_registry.pop(phase_num, None)

        if cancel_event is not None and cancel_event.is_set() and process is not None:
            try:
                process.terminate()
            except Exception:
                pass
            kill_process_tree(process.pid)


def run_normal_phase(phase_num, phase_path, proc_registry=None, cancel_event=None, update_progress=True):
    phase_name = f"Fase {phase_num}"

    if update_progress:
        progress_manager.update_phase(phase_num)

    log_message(f"Running {phase_name}\n")

    process = None
    phase_start = time.time()
    last_debug_progress = 0.0

    try:
        _args, _env = _module_launch_args(sys.executable, phase_path)
        debug_write(f"=== {phase_name}: {_args} ===")

        process = subprocess.Popen(
            _args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=4096,
            universal_newlines=True,
            cwd=paths['project_root'],
            env=_env
        )

        if proc_registry is not None:
            proc_registry[phase_num] = process

        while True:
            if cancel_event is not None and cancel_event.is_set():
                break

            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                break

            if output:
                progress = parse_progress(output)

                if debug_file is not None and output.strip() and (
                        progress is None or time.time() - last_debug_progress >= DEBUG_PROGRESS_EVERY):
                    if progress is not None:
                        last_debug_progress = time.time()
                    debug_write(f"  F{phase_num}| {output}")

                if progress is not None:
                    progress_manager.update_progress(progress)
                elif "error" in output.lower():
                    log_message(f"[Warn] {output}")

        return process.returncode == 0

    except Exception as e:
        log_message(f"Error in {phase_name}: {str(e)}\n")
        debug_exception()
        return False

    finally:
        if process is not None:
            debug_write(f"=== {phase_name} exit code {process.returncode} ({time.time() - phase_start:.1f} s) ===")

        if proc_registry is not None and process is not None:
            proc_registry.pop(phase_num, None)

        if cancel_event is not None and cancel_event.is_set() and process is not None:
            try:
                process.terminate()
            except Exception:
                pass
            kill_process_tree(process.pid)


# ------------------------------------------------------------
# MAIN EXECUTION FUNCTIONS
# ------------------------------------------------------------
def esegui_auto_sub_retimer():
    global is_running, start_time

    if is_running:
        return

    is_running = True
    completed = False

    set_start_button("disabled")
    log_clear()

    try:
        log_message("Starting Auto Sub ReTimer process\n")

        fase0_path = paths['retimer_scripts']['fase0']
        fase1_path = paths['retimer_scripts']['fase1']

        active_procs = {}
        cancel_event = threading.Event()
        results = {}

        pulisci_intermedi(paths['project_root'])

        sentinel_sub = os.path.join(paths['project_root'], "Sub.srt")
        sentinel_vocals = os.path.join(paths['project_root'], "vocali.wav")

        progress_manager.set_parallel_active([0, 1], display_phase=1)
        start_time = None

        def _kill_other_proc(phase_num):
            p = active_procs.get(phase_num)
            if p is not None:
                try:
                    p.terminate()
                except Exception:
                    pass
                try:
                    kill_process_tree(p.pid)
                except Exception:
                    pass

        def _run_fase0():
            global start_time

            results[0] = run_interactive_phase(
                0,
                fase0_path,
                active_procs,
                cancel_event,
                update_progress=False
            )

            if results[0] and not os.path.exists(sentinel_sub):
                results[0] = False

            if results[0]:
                start_time = time.time()
                progress_manager.mark_done(0)
            else:
                cancel_event.set()
                _kill_other_proc(1)

        def _run_fase1():
            results[1] = run_normal_phase(
                1,
                fase1_path,
                active_procs,
                cancel_event,
                update_progress=False
            )

            if results[1] and not os.path.exists(sentinel_vocals):
                results[1] = False

            if results[1]:
                progress_manager.mark_done(1)
            else:
                cancel_event.set()
                input_handler.cancel()
                _kill_other_proc(0)

        t0 = threading.Thread(target=_run_fase0, daemon=True)
        t1 = threading.Thread(target=_run_fase1, daemon=True)

        t0.start()
        t1.start()

        t0.join()
        t1.join()

        if not results.get(0) or not results.get(1):
            cancel_event.set()
            input_handler.cancel()

            for p in list(active_procs.values()):
                try:
                    p.terminate()
                except Exception:
                    pass

            log_message("Fase0/Fase1 failed — aborting.\n")
            return

        root_dir = paths['project_root']

        fasi = [
            (2, paths['retimer_scripts']['fase2'], ["adjusted_Sub.srt"]),
            (3, paths['retimer_scripts']['fase3'], ["scene_timestamps_adjusted.srt"]),
            (4, paths['retimer_scripts']['fase4'], ["Final.srt"]),
            (5, paths['retimer_scripts']['fase5'], []),
            (6, paths['retimer_scripts']['fase6'], []),
        ]

        for phase_num, phase_path, expected in fasi:
            if phase_num == 5 and os.path.exists(os.path.join(root_dir, "Dialoghi.ass")):
                expected = ["Final.ass"]

            if phase_num == 6:
                start_time = None
                success = run_interactive_phase(phase_num, phase_path)
            else:
                success = run_normal_phase(phase_num, phase_path)

            missing = [f for f in expected if not os.path.exists(os.path.join(root_dir, f))]

            if not success or missing:
                detail = f" (missing output: {', '.join(missing)})" if missing else ""
                log_message(
                    f"Fase {phase_num} failed{detail} — aborting. "
                    f"Intermediate files were left in the project folder.\n"
                )
                return

        completed = True
        log_message("Process completed successfully.\n")
        progress_manager.complete_all()

    finally:
        is_running = False
        start_time = None
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")


def esegui_auto_sub_retimer_cr():
    global is_running, start_time

    if is_running:
        return

    is_running = True
    completed = False

    set_start_button("disabled")
    log_clear()

    old_weights = progress_manager.phase_weights.copy()

    try:
        pulisci_intermedi(paths['project_root'])

        risposta = input_handler.ask_question(
            "Are these subtitle leads natively long or short?",
            ["Long leads [Default]", "Short leads"]
        )

        if risposta is None:
            return

        if risposta == 1:
            fase4_folder = paths['auto_sub_retimer_cr']['long_leads']
        else:
            fase4_folder = paths['auto_sub_retimer_cr']['short_leads']

        progress_manager.phase_weights = {0: 15, 2: 20, 3: 15, 4: 20, 5: 20, 6: 10}

        log_message("Starting Auto Sub ReTimer CR process\n")

        fase0_path = paths['auto_sub_retimer_cr']['scripts']['fase0']
        success = run_interactive_phase(0, fase0_path)

        if not success:
            return

        start_time = time.time()

        progress_manager.update_phase(1)
        progress_manager.update_progress(100)

        fase2_path = paths['auto_sub_retimer_cr']['scripts']['fase2']
        success = run_normal_phase(2, fase2_path)

        if not success:
            return

        fase3_path = paths['auto_sub_retimer_cr']['scripts']['fase3']
        success = run_normal_phase(3, fase3_path)

        if not success:
            return

        fase4_path = os.path.join(fase4_folder, "Fase4.py")
        success = run_normal_phase(4, fase4_path)

        if not success:
            return

        fase5_path = paths['auto_sub_retimer_cr']['scripts']['fase5']
        success = run_normal_phase(5, fase5_path)

        if not success:
            return

        start_time = None

        fase6_path = paths['auto_sub_retimer_cr']['scripts']['fase6']
        success = run_interactive_phase(6, fase6_path)

        if not success:
            return

        completed = True
        log_message("Process completed successfully.\n")
        progress_manager.complete_all()

    except Exception as e:
        log_message(f"Error in Unexpected error: {str(e)}\n")
        debug_exception()

    finally:
        is_running = False
        start_time = None
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")
        progress_manager.phase_weights = old_weights


def esegui_whisper():
    global is_running, start_time

    if is_running:
        return

    is_running = True
    completed = False
    start_time = time.time()

    set_start_button("disabled")
    log_clear()

    try:
        progress_manager.update_phase(0)
        log_message("Running Fase0.py...\n")

        _args0, _env0 = _module_launch_args(
            paths['whisper_scripts']['venv_python'],
            paths['whisper_scripts']['fase0']
        )

        debug_write(f"=== Whisper Fase0: {_args0} ===")

        fase0_result = subprocess.run(
            _args0,
            cwd=paths['project_root'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=_env0
        )

        debug_write(f"  F0 stdout| {fase0_result.stdout}")
        debug_write(f"  F0 stderr| {fase0_result.stderr}")
        debug_write(f"=== Whisper Fase0 exit code {fase0_result.returncode} ===")

        if fase0_result.returncode != 0:
            log_message(f"Error in Fase0.py:\n{fase0_result.stderr}\n")
            return False

        log_message("Fase0.py completed successfully\n")

        progress_manager.update_progress(100)
        progress_manager.update_phase(1)

        log_message("Running Fase1.py...\n")

        _args1, _env1 = _module_launch_args(
            paths['whisper_scripts']['venv_python'],
            paths['whisper_scripts']['fase1']
        )

        debug_write(f"=== Whisper Fase1: {_args1} ===")

        process = subprocess.Popen(
            _args1,
            cwd=paths['project_root'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=4096,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            env=_env1
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

        debug_write(f"=== Whisper Fase1 exit code {process.returncode} ===")

        if process.returncode == 0 or process.returncode == 3221226505:
            log_message("Whisper execution completed successfully\n")
            progress_manager.complete_all()
            completed = True
            return True
        else:
            log_message(f"Error in Fase1.py (code {process.returncode})\n")
            return False

    except Exception as e:
        log_message(f"Error in Execution: {str(e)}\n")
        debug_exception()
        return False

    finally:
        is_running = False
        start_time = None
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")


def esegui_modulo_retimer(key, module_name):
    if debug_file is None:
        _esegui_modulo_retimer(key, module_name)
        return

    debug_write(f"=== Whisper ReTimer {module_name} ===")

    t0 = time.time()
    old_out, old_err = sys.stdout, sys.stderr

    sys.stdout, sys.stderr = _DebugTee(old_out, module_name), _DebugTee(old_err, f"{module_name} stderr")

    try:
        _esegui_modulo_retimer(key, module_name)
    finally:
        sys.stdout, sys.stderr = old_out, old_err

    debug_write(f"=== Whisper ReTimer {module_name} done ({time.time() - t0:.1f} s) ===")


def _esegui_modulo_retimer(key, module_name):
    if key in loaded_modules:
        module = importlib.reload(loaded_modules[key])
    else:
        module = importlib.import_module(module_name)

    loaded_modules[key] = module

    if hasattr(module, 'main'):
        module.main()


def esegui_whisper_retimer():
    global is_running, start_time

    if is_running:
        return

    is_running = True
    completed = False
    start_time = time.time()

    set_start_button("disabled")
    input_handler.response = None
    input_handler.event.clear()
    log_clear()

    try:
        retimer_dir = os.path.join(paths['project_root'], "Scripts", "Whisper ReTimer")

        if retimer_dir not in sys.path:
            sys.path.insert(0, retimer_dir)

        progress_manager.update_phase(0)
        log_message("Running Fase0.py...\n")
        esegui_modulo_retimer("Fase0_retimer", "Fase0")

        progress_manager.update_phase(1)
        log_message("Running whispertiming.py...\n")
        esegui_modulo_retimer("whispertiming", "whispertiming")

        log_message("[Wait] User input required...\n")

        risposta = input_handler.ask_question(
            "Do you want subtitles to respect scene changes?",
            ["Yes", "No"]
        )

        if risposta is None:
            return

        if risposta == 1:
            progress_manager.update_phase(2)
            log_message("Running Fase3.py...\n")
            esegui_modulo_retimer("Fase3_retimer", "Fase3")

            progress_manager.update_phase(3)
            log_message("Running Fase4.py...\n")
            esegui_modulo_retimer("Fase4_retimer", "Fase4")

            progress_manager.update_phase(4)
            log_message("Running Fase5.py...\n")
            esegui_modulo_retimer("Fase5_retimer", "Fase5")
        else:
            progress_manager.update_phase(2)
            progress_manager.update_progress(100)

            progress_manager.update_phase(3)
            progress_manager.update_progress(100)

            progress_manager.update_phase(4)
            log_message("Running Fase5.py...\n")
            esegui_modulo_retimer("Fase5_retimer", "Fase5")

        log_message("Whisper ReTimer process completed successfully.\n")
        progress_manager.complete_all()

        completed = True
        return True

    except Exception as e:
        log_message(f"Error in Execution: {str(e)}\n")
        debug_exception()
        return False

    finally:
        is_running = False
        start_time = None
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")


# ------------------------------------------------------------
# TOOLS
# ------------------------------------------------------------
def esegui_text_correction():
    global is_running

    if is_running:
        return

    is_running = True
    completed = False

    set_start_button("disabled")
    log_clear()

    try:
        log_message("Starting TextCorrection...\n")

        script_path = paths['tools']['text_correction']

        if not os.path.exists(script_path):
            log_message(f"Script not found: {script_path}\n")
            return

        _args, _env = _module_launch_args(sys.executable, script_path)

        process = subprocess.Popen(
            _args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=4096,
            universal_newlines=True,
            cwd=paths['project_root'],
            env=_env
        )

        while True:
            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                break

            if output:
                log_message(output)

        if process.returncode == 0:
            log_message("TextCorrection completed successfully.\n")
            completed = True
        else:
            log_message(f"TextCorrection failed with code {process.returncode}\n")

    except Exception as e:
        log_message(f"Error in TextCorrection: {str(e)}\n")

    finally:
        is_running = False
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")


def esegui_oona_fix():
    global is_running

    if is_running:
        return

    is_running = True
    completed = False

    set_start_button("disabled")
    log_clear()

    try:
        log_message("Starting OoonaFix...\n")

        script_path = paths['tools']['oona_fix']

        if not os.path.exists(script_path):
            log_message(f"Script not found: {script_path}\n")
            return

        _args, _env = _module_launch_args(sys.executable, script_path)

        process = subprocess.Popen(
            _args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=4096,
            universal_newlines=True,
            cwd=paths['project_root'],
            env=_env
        )

        while True:
            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                break

            if output:
                log_message(output)

        if process.returncode == 0:
            log_message("OoonaFix completed successfully.\n")
            completed = True
        else:
            log_message(f"OoonaFix failed with code {process.returncode}\n")

    except Exception as e:
        log_message(f"Error in OoonaFix: {str(e)}\n")

    finally:
        is_running = False
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")


def esegui_timing_swap():
    global is_running

    if is_running:
        return

    is_running = True
    completed = False

    set_start_button("disabled")
    log_clear()

    try:
        log_message("Starting TimingSwap...\n")

        script_path = paths['timing_swap']['script']

        if not os.path.exists(script_path):
            log_message(f"Script not found: {script_path}\n")
            return

        _args, _env = _module_launch_args(sys.executable, script_path)

        process = subprocess.Popen(
            _args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=4096,
            universal_newlines=True,
            cwd=paths['project_root'],
            env=_env
        )

        while True:
            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                break

            if output:
                log_message(output)

        if process.returncode == 0:
            log_message("TimingSwap completed successfully.\n")
            completed = True
        else:
            log_message(f"TimingSwap failed with code {process.returncode}\n")

    except Exception as e:
        log_message(f"Error in TimingSwap: {str(e)}\n")

    finally:
        is_running = False
        set_start_button("normal")
        set_status("Status: Completed" if completed else "Status: Failed", "done" if completed else "fail")


# ------------------------------------------------------------
# LAUNCH SELECTED FUNCTION
# ------------------------------------------------------------
def avvia_processo():
    if debug_armed and not is_running and debug_file is None:
        set_start_button("disabled")
        set_status("Status: Debug check...", "debug")

        try:
            debug_begin(funzione_selezionata)
        except Exception:
            debug_exception()

        set_status("Status: Running (debug)", "debug")

    try:
        _avvia_processo()
    finally:
        if debug_file is not None and not is_running:
            debug_end()
        if not is_running:
            set_start_button("normal")


def _avvia_processo():
    if funzione_selezionata == "Auto Sub ReTimer":
        if paths['available']['autosub']:
            esegui_auto_sub_retimer()
        else:
            messagebox.showwarning(
                "Function not available",
                "Some Auto Sub ReTimer scripts were not found."
            )

    elif funzione_selezionata == "Whisper":
        if paths['available']['whisper']:
            esegui_whisper()
        else:
            messagebox.showwarning(
                "Function not available",
                "Whisper function requires 'Faster-Whisper-XXL' folder.\n"
                "Please add it to the main 'Auto Sub ReTimer' directory."
            )

    elif funzione_selezionata == "Whisper ReTimer":
        if paths['available']['retimer']:
            esegui_whisper_retimer()
        else:
            messagebox.showwarning(
                "Function not available",
                "Some Whisper ReTimer scripts were not found."
            )

    elif funzione_selezionata == "Auto Sub ReTimer CR":
        if paths['available']['autosub_cr']:
            esegui_auto_sub_retimer_cr()
        else:
            messagebox.showwarning(
                "Function not available",
                "Some Auto Sub ReTimer CR scripts were not found.\n"
                "Check folder 'Scripts/Auto Sub ReTimer CR' and its subfolders."
            )

    else:
        log_message("Select a valid function\n")


# ------------------------------------------------------------
# FUNCTION SELECTION
# ------------------------------------------------------------
def seleziona_funzione(funzione):
    global funzione_selezionata

    if is_running:
        messagebox.showwarning("Function", "Wait for the current process to finish.")
        return

    funzione_selezionata = funzione

    if funzione == "Auto Sub ReTimer":
        progress_manager.phase_weights = {0: 15, 1: 20, 2: 15, 3: 15, 4: 15, 5: 15, 6: 5}

    elif funzione == "Auto Sub ReTimer CR":
        progress_manager.phase_weights = {0: 15, 2: 20, 3: 15, 4: 20, 5: 20, 6: 10}

    elif funzione == "Whisper":
        progress_manager.phase_weights = {0: 50, 1: 50}

    elif funzione == "Whisper ReTimer":
        progress_manager.phase_weights = {0: 20, 1: 20, 2: 20, 3: 20, 4: 20}

    else:
        progress_manager.phase_weights = {0: 15, 1: 20, 2: 15, 3: 15, 4: 15, 5: 15, 6: 5}

    buttons = {
        "Auto Sub ReTimer": button_autosub,
        "Auto Sub ReTimer CR": button_autosub_cr,
        "Whisper": button_whisper,
        "Whisper ReTimer": button_retimer
    }

    for name, btn in buttons.items():
        btn.configure(
            fg_color="transparent",
            text_color=TEXT_2,
            border_width=1,
            border_color=BG_PANEL
        )

        if name == "Whisper" and not paths['available']['whisper']:
            btn.configure(state="disabled", fg_color="transparent", text_color=P_IDLE_T)

        elif name == "Whisper ReTimer" and not paths['available']['retimer']:
            btn.configure(state="disabled", fg_color="transparent", text_color=P_IDLE_T)

        elif name == "Auto Sub ReTimer" and not paths['available']['autosub']:
            btn.configure(state="disabled", fg_color="transparent", text_color=P_IDLE_T)

        elif name == "Auto Sub ReTimer CR" and not paths['available']['autosub_cr']:
            btn.configure(state="disabled", fg_color="transparent", text_color=P_IDLE_T)

        else:
            btn.configure(state="normal")

    if funzione in buttons and buttons[funzione].cget("state") == "normal":
        buttons[funzione].configure(
            fg_color=ACCENT_DIM,
            text_color=TEXT_A,
            border_width=1,
            border_color=ACCENT
        )

    dash_title_label.configure(text=funzione)

    instructions_text.delete("1.0", "end")

    if funzione == "Auto Sub ReTimer":
        if paths['available']['autosub']:
            instructions_text.insert(
                "1.0",
                "Auto Sub ReTimer\n\n"
                "A tool to fine-tune timing.\n\n"
                "REQUIREMENTS\n"
                "The line of spoken audio in the sub must be within the lines and not partially outside the line (audio spectrum).\n"
                "There must not be the start of spoken audio that begins before the line, for example.\n"
                "Even a quick sync that's the same for all lines is sufficient, for example -0.050 or -0.100.\n\n"
                "1. When prompted, select the .mkv video file and then the subtitles.\n\n"
                "2. In Fase0, you will be asked to upload the subtitle.\n"
                "It will automatically separate Signs, Comments and On Top to avoid conflicts with the timing adjustment of dialogues.\n"
                "If the program can't figure out where certain lines go, you'll be asked to select where to put them.\n"
                "If the separation does not work as expected, you can always manually separate everything to leave only the dialogues.\n"
                "\n"
                "3. Fase3 detects scene changes with PySceneDetect or TransNetV2 (Best on GPU): choose it in the Fase3 configuration.\n"
                "If the video codec is AV1 and PySceneDetect fails in Fase3, use TransNetV2.\n\n"
                "4. Read the instructions on GitHub."
            )
        else:
            instructions_text.insert(
                "1.0",
                "AUTO SUB RETIMER NOT AVAILABLE\n\n"
                "Required scripts not found.\n"
                "Check folder:\n"
                "'Scripts/Auto Sub ReTimer'"
            )

    elif funzione == "Whisper":
        if paths['available']['whisper']:
            instructions_text.insert(
                "1.0",
                "Whisper\n\n"
                "A tool to automatically transcribe audio into subtitles using Faster-Whisper.\n\n"
                "1. Make sure you have the video .mkv in the Auto Sub ReTimer folder.\n"
                "\n\n"
                "2. Select the language and model from the configuration settings.\n"
            )
        else:
            instructions_text.insert(
                "1.0",
                "WHISPER NOT AVAILABLE\n\n"
                "To use this function:\n"
                "1. Add 'Faster-Whisper-XXL' folder\n"
                "2. Ensure it contains 'faster-whisper-xxl.exe'\n"
                "3. Restart application"
            )

    elif funzione == "Whisper ReTimer":
        if paths['available']['retimer']:
            instructions_text.insert(
                "1.0",
                "Whisper ReTimer\n\n"
                "A tool to refine and fix timing for subtitles generated by Whisper.\n\n"
                "1. Requires a Whisper-generated subtitle file and the original video.\n\n"
                "2. Asks if you want the new timing to respect Scene Changes.\n\n"
                "3. Automatically applies snap-to-scene transitions based on your choice.\n"
            )
        else:
            instructions_text.insert(
                "1.0",
                "WHISPER RETIMER NOT AVAILABLE\n\n"
                "Required scripts not found.\n"
                "Check folder:\n"
                "'Scripts/Whisper ReTimer'"
            )

    elif funzione == "Auto Sub ReTimer CR":
        if paths['available']['autosub_cr']:
            instructions_text.insert(
                "1.0",
                "Auto Sub ReTimer CR\n\n"
                "A more conservative tool compared to Auto Sub ReTimer (AS).\n"
                "It preserves original lead-ins/outs while improving timing through line-linking and scene-change snapping.\n\n"
                "1. When prompted, select the .mkv video file and then the subtitles.\n"
                "\n"
                "2. The script will ask if the subtitle leads are natively long or short.\n"
                "Choose accordingly to use the correct Fase4 configuration automatically.\n\n"
                "If you're not sure what to choose, use Long leads [Default].\n"
            )
        else:
            instructions_text.insert(
                "1.0",
                "AUTO SUB RETIMER CR NOT AVAILABLE\n\n"
                "Required scripts not found.\n"
                "Check folder:\n"
                "'Scripts/Auto Sub ReTimer CR' and its subfolders."
            )

    else:
        instructions_text.insert(
            "1.0",
            "Welcome to Auto Sub ReTimer\n\n"
            "1. Select a function\n"
            "2. Click 'Start'\n"
            "3. Answer questions\n\n"
            "Monitor progress in the bar."
        )

    rebuild_phase_pills(funzione)
    aggiorna_visibilita_pulsanti_config()


# ------------------------------------------------------------
# STARTUP
# ------------------------------------------------------------
def _porta_in_primo_piano():
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    root.after(0, lambda: root.attributes("-topmost", False))


_layout_body("dashboard")
_refresh_options_output_ui()

seleziona_funzione("Auto Sub ReTimer")

root.after(0, _porta_in_primo_piano)
root.after(100, _display_poll_loop)
root.after(500, update_log)
root.after(1000, update_timer)

def _centra_su_monitor():
    _center_window_engine(root)


def _on_first_map(event=None):
    root.unbind("<Map>")
    root.after(0, _centra_su_monitor)


root.bind("<Map>", _on_first_map)

root.mainloop()