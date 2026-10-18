import os
import re
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox

def get_output_dir(input_file):
    # 1. Preferenza GUI
    gui_config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "GUI", "gui_config.json"
    )
    try:
        with open(gui_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        out = cfg.get("output_dir")
        if out and os.path.isdir(out):
            return os.path.abspath(out)
    except (OSError, json.JSONDecodeError):
        pass

    # 2. Cartella del file di input scelto dall'utente
    if input_file:
        d = os.path.dirname(os.path.abspath(input_file))
        if os.path.isdir(d):
            return d

    # 3. Fallback: Desktop
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            folderid_desktop = GUID(0xB4BFCC3A, 0xDB2C, 0x424C,
                                    (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folderid_desktop), 0, None,
                                                          ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    path = os.path.join(os.path.expanduser("~"), "Desktop")
    return path if os.path.isdir(path) else None

def timestamp_to_ms(timestamp):
    h, m, s_ms = timestamp.split(':')
    s, ms = s_ms.split('.')
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms) * 10

def ms_to_timestamp(ms):
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms = (ms % 1000) // 10
    return f"{h}:{m:02d}:{s:02d}.{ms:02d}"

def is_cartello(text):
    clean_text = re.sub(r'\{.*?\}', '', text)
    clean_text = re.sub(r'[^\w\s]', '', clean_text)
    clean_text = re.sub(r'\s+', '', clean_text)
    if len(clean_text) < 3:
        return False
    return clean_text.isupper()

def clean_empty_lines(events):
    changed = True
    while changed:
        changed = False
        for i in range(len(events) - 2):
            if '\\N\\N' not in events[i]:
                continue
            
            parts_curr = events[i].split(',', 9)
            if len(parts_curr) < 10:
                continue
            
            text_parts = parts_curr[9].split('\\N\\N')
            if len(text_parts) < 2:
                continue
            
            parts_next = events[i + 1].split(',', 9)
            if len(parts_next) < 10:
                continue
            next_text = parts_next[9]
            
            # ---- PATTERN A ----
            if not next_text:
                if len(text_parts) == 2:
                    parts_curr[9] = text_parts[0]
                    events[i] = ','.join(parts_curr)
                    parts_next[9] = text_parts[1]
                    events[i + 1] = ','.join(parts_next)
                    changed = True
                    break
                elif len(text_parts) >= 3:
                    last_text = text_parts.pop()
                    parts_curr[9] = '\\N\\N'.join(text_parts)
                    events[i] = ','.join(parts_curr)
                    parts_next[9] = last_text
                    events[i + 1] = ','.join(parts_next)
                    changed = True
                    break
            
            # ---- PATTERN B ----
            elif next_text:
                parts_next2 = events[i + 2].split(',', 9)
                if len(parts_next2) < 10:
                    continue
                next2_text = parts_next2[9]
                
                if next2_text:
                    continue
                
                if is_cartello(next_text):
                    continue
                
                if '\\N\\N' in next_text:
                    text_parts_next = next_text.split('\\N\\N')
                    if len(text_parts_next) >= 2:
                        if len(text_parts_next) == 2:
                            parts_next[9] = text_parts_next[0]
                            events[i + 1] = ','.join(parts_next)
                            parts_next2[9] = text_parts_next[1]
                            events[i + 2] = ','.join(parts_next2)
                            changed = True
                            break
                        elif len(text_parts_next) >= 3:
                            last_text = text_parts_next.pop()
                            parts_next[9] = '\\N\\N'.join(text_parts_next)
                            events[i + 1] = ','.join(parts_next)
                            parts_next2[9] = last_text
                            events[i + 2] = ','.join(parts_next2)
                            changed = True
                            break
                    continue
                
                # --- CASO NORMALE ---
                if len(text_parts) == 2:
                    parts_curr[9] = text_parts[0]
                    events[i] = ','.join(parts_curr)
                    parts_next[9] = text_parts[1]
                    events[i + 1] = ','.join(parts_next)
                    parts_next2[9] = next_text
                    events[i + 2] = ','.join(parts_next2)
                    changed = True
                    break
                elif len(text_parts) >= 3:
                    parts_curr[9] = text_parts[0]
                    events[i] = ','.join(parts_curr)
                    last_text = text_parts.pop()
                    parts_next[9] = last_text
                    events[i + 1] = ','.join(parts_next)
                    parts_next2[9] = next_text
                    events[i + 2] = ','.join(parts_next2)
                    changed = True
                    break
    
    return events

def sync_ass_files(source_path, target_path, output_path):
    if not os.path.exists(source_path) or not os.path.exists(target_path):
        print("One or both files do not exist.")
        return False, 0

    with open(source_path, 'r', encoding='utf-8') as f:
        source_content = f.readlines()
    
    with open(target_path, 'r', encoding='utf-8') as f:
        target_content = f.readlines()
    
    source_events = []
    for line in source_content:
        if line.startswith('Dialogue:'):
            parts = line.strip().split(',', 9)
            if len(parts) >= 10:
                start_ms = timestamp_to_ms(parts[1])
                end_ms = timestamp_to_ms(parts[2])
                source_events.append({
                    'start': start_ms,
                    'end': end_ms,
                    'text': parts[9],
                    'original': line.strip()
                })
    source_events.sort(key=lambda e: e['start'])

    target_events = []
    for line in target_content:
        if line.startswith('Dialogue:'):
            parts = line.strip().split(',', 9)
            if len(parts) >= 10:
                start_ms = timestamp_to_ms(parts[1])
                end_ms = timestamp_to_ms(parts[2])
                target_events.append({
                    'start': start_ms,
                    'end': end_ms,
                    'parts': parts,
                    'original': line.strip()
                })
    
    MIN_OVERLAP_RATIO = 0.25
    MIN_OVERLAP_MS = 300

    new_events = []
    source_index = 0
    n_targets = len(target_events)
    
    for i, target_event in enumerate(target_events):
        start_time = target_event['start']
        end_time = target_event['end']
        t_dur = max(end_time - start_time, 1)
        next_target = target_events[i + 1] if i + 1 < n_targets else None
        
        combined_lines = []
        
        while (source_index < len(source_events) and 
               source_events[source_index]['start'] < end_time):
            s = source_events[source_index]
            overlap_current = max(0, min(s['end'], end_time) - max(s['start'], start_time))
            ratio = overlap_current / t_dur
            
            if ratio < MIN_OVERLAP_RATIO and overlap_current < MIN_OVERLAP_MS:
                if next_target is not None:
                    overlap_next = max(0, min(s['end'], next_target['end']) - max(s['start'], next_target['start']))
                    if overlap_next > overlap_current:
                        break
            
            combined_lines.append(s['text'])
            source_index += 1
        
        if combined_lines:
            formatted_text = '\\N\\N'.join(combined_lines)
        else:
            formatted_text = ""
        
        new_parts = target_event['parts'].copy()
        new_parts[9] = formatted_text
        new_events.append(','.join(new_parts))

    unassigned = len(source_events) - source_index

    new_events = clean_empty_lines(new_events)

    target_has_format = False
    in_events = False
    for line in target_content:
        s = line.strip()
        if s.startswith('['):
            in_events = (s == '[Events]')
        elif in_events and s.startswith('Format:'):
            target_has_format = True
            break

    output_lines = []
    in_events_section = False
    events_written = False

    for line in target_content:
        line_stripped = line.strip()

        if line_stripped == '[Events]':
            in_events_section = True
            output_lines.append(line)
            if not target_has_format:
                output_lines.append('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
            continue
        
        if in_events_section and line_stripped.startswith('Dialogue:'):
            if not events_written:
                for event in new_events:
                    output_lines.append(event + '\n')
                events_written = True
            continue
        
        if in_events_section and line_stripped.startswith('[') and events_written:
            in_events_section = False
            output_lines.append(line)
        elif not in_events_section or not line_stripped.startswith('Dialogue:'):
            output_lines.append(line)
    
    if not events_written:
        for event in new_events:
            output_lines.append(event + '\n')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    if unassigned:
        print(f"Warning: {unassigned} source line(s) start after the last target line and were not assigned.")
    return True, unassigned

def select_file(title="Select an ASS file", parent=None):
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[("ASS Files", "*.ass"), ("All Files", "*.*")],
        parent=parent
    )
    return file_path

def main():
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.focus_force()

    # Primo popup
    messagebox.showinfo(
        "Select Source Subtitle",
        "Select the subtitle whose timing you want to improve.",
        parent=root
    )
    source = select_file("Select the source subtitle (texts to take)", parent=root)
    if not source:
        print("Operation canceled.")
        root.destroy()
        return

    # Secondo popup
    messagebox.showinfo(
        "Select Target Subtitle",
        "Select the subtitle with the correct timing.",
        parent=root
    )
    target = select_file("Select the target subtitle (timing to keep)", parent=root)
    if not target:
        print("Operation canceled.")
        root.destroy()
        return

    # Percorso di output
    output_dir = get_output_dir(target)
    if output_dir is None:
        messagebox.showerror("Error", "Output folder unreachable, unable to save the file.", parent=root)
        root.destroy()
        return
    output = os.path.join(output_dir, "sincronizzato.ass")
    
    if os.path.exists(output):
        overwrite = messagebox.askyesno(
            "File exists",
            f"The file '{output}' already exists.\nDo you want to overwrite it?",
            parent=root
        )
        if not overwrite:
            print("Operation canceled.")
            root.destroy()
            return

    try:
        success, unassigned = sync_ass_files(source, target, output)
    except UnicodeDecodeError:
        messagebox.showerror(
            "Error",
            "The subtitle file is not UTF-8 encoded.\n"
            "Open it (e.g. in Aegisub or Notepad), save it as UTF-8 and try again.",
            parent=root
        )
        root.destroy()
        sys.exit(1)
    if success:
        warning = ""
        if unassigned:
            warning = (f"\n\nWarning: {unassigned} source line(s) start after the last "
                       "target line and were not assigned.")
        messagebox.showinfo(
            "Success",
            f"File successfully synchronized and saved to:\n{output}{warning}",
            parent=root
        )
    else:
        messagebox.showerror(
            "Error",
            "An error occurred during synchronization.",
            parent=root
        )

    root.destroy()

if __name__ == "__main__":
    main()