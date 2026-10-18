import os
import json
import shutil
from tkinter import messagebox
import tkinter as tk

def get_output_dir(project_path):
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

    # 2. Cartella del sub scelto in Fase0
    handshake_path = os.path.join(project_path, ".asr_pipeline_paths.json")
    try:
        with open(handshake_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sp = data.get("sub_path")
        if sp:
            d = os.path.dirname(os.path.abspath(sp))
            if os.path.isdir(d):
                return d
    except (OSError, json.JSONDecodeError):
        pass

    # 3. Fallback: project_root
    return project_path

def get_sub_path(project_path):
    handshake_path = os.path.join(project_path, ".asr_pipeline_paths.json")
    try:
        with open(handshake_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sp = data.get("sub_path")
        if sp and os.path.isfile(sp) and sp.lower().endswith('.ass'):
            return sp
    except (OSError, json.JSONDecodeError):
        pass
    return None


def crea_copia_originale_timata(sub_path, dialoghi_path, final_ass_path, output_path):
    if not (os.path.isfile(sub_path) and os.path.isfile(dialoghi_path) and os.path.isfile(final_ass_path)):
        return False

    with open(dialoghi_path, 'r', encoding='utf-8-sig') as f:
        dialoghi_lines = [l for l in f if l.startswith('Dialogue:')]

    with open(final_ass_path, 'r', encoding='utf-8-sig') as f:
        final_lines = [l for l in f if l.startswith('Dialogue:')]

    if len(dialoghi_lines) != len(final_lines) or len(final_lines) == 0:
        return False

    key_to_newtimes = {}
    for orig_line, new_line in zip(dialoghi_lines, final_lines):
        orig_parts = orig_line.rstrip('\r\n').split(',', 9)
        new_parts = new_line.rstrip('\r\n').split(',', 9)
        if len(orig_parts) < 10 or len(new_parts) < 10:
            continue
        key = (orig_parts[9].strip(), orig_parts[1].strip(), orig_parts[2].strip())
        key_to_newtimes.setdefault(key, []).append(
            (new_parts[1].strip(), new_parts[2].strip())
        )

    if not key_to_newtimes:
        return False

    with open(sub_path, 'r', encoding='utf-8-sig') as f:
        original_lines = f.readlines()

    updated_lines = []
    matched = 0
    for line in original_lines:
        if line.startswith('Dialogue:'):
            if line.endswith('\r\n'):
                ending, content = '\r\n', line[:-2]
            elif line.endswith('\n'):
                ending, content = '\n', line[:-1]
            else:
                ending, content = '', line

            parts = content.split(',', 9)
            if len(parts) == 10:
                key = (parts[9].strip(), parts[1].strip(), parts[2].strip())
                queue = key_to_newtimes.get(key)
                if queue:
                    new_start, new_end = queue.pop(0)
                    parts[1] = new_start
                    parts[2] = new_end
                    line = ','.join(parts) + ending
                    matched += 1
        updated_lines.append(line)

    if matched == 0:
        return False

    remaining = sum(len(v) for v in key_to_newtimes.values())
    if remaining > 0:
        return False

    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(updated_lines)
    except Exception:
        return False

    return True

def chiedi_output_mode():
    BG_PANEL = "#0F0F14"
    BG_CARD  = "#141419"
    TEXT_1   = "#EBEBF2"
    TEXT_2   = "#63636F"
    ACCENT   = "#7C5CFA"
    SUCCESS  = "#2ED191"

    result = {"mode": "recomposed"}

    root = tk.Tk()
    root.title("Output mode")
    root.configure(bg=BG_PANEL)
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", root.destroy)

    tk.Label(
        root, text="Which output do you want?",
        bg=BG_PANEL, fg=TEXT_1,
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w", padx=24, pady=(20, 12))

    card_copy = tk.Frame(root, bg=BG_CARD, padx=18, pady=14)
    card_copy.pack(fill="x", padx=20, pady=(0, 10))

    tk.Label(card_copy, text="Copy original",
             bg=BG_CARD, fg=SUCCESS,
             font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w")
    tk.Label(card_copy,
             text="Your original subtitle with updated timing.\nOrder, styles and tags are preserved.",
             bg=BG_CARD, fg=TEXT_2, font=("Segoe UI", 10),
             justify="left", anchor="w").pack(anchor="w", pady=(4, 0))

    card_rec = tk.Frame(root, bg=BG_CARD, padx=18, pady=14)
    card_rec.pack(fill="x", padx=20, pady=(0, 16))

    tk.Label(card_rec, text="Recomposed",
             bg=BG_CARD, fg=ACCENT,
             font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w")
    tk.Label(card_rec,
             text="The files produced during the process\n(Signs, Comments, Dialogues, On Top)\nare merged into a single file.",
             bg=BG_CARD, fg=TEXT_2, font=("Segoe UI", 10),
             justify="left", anchor="w").pack(anchor="w", pady=(4, 0))

    def choose(mode):
        result["mode"] = mode
        root.quit()

    btn_frame = tk.Frame(root, bg=BG_PANEL)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))

    tk.Button(btn_frame, text="Copy original",
              command=lambda: choose("copy"),
              bg=SUCCESS, fg="#0B0B12",
              activebackground="#3EE6A2", activeforeground="#0B0B12",
              font=("Segoe UI", 11, "bold"),
              relief="flat", borderwidth=0,
              padx=20, pady=10, cursor="hand2"
    ).pack(side="left", expand=True, fill="x", padx=(0, 6))

    tk.Button(btn_frame, text="Recomposed",
              command=lambda: choose("recomposed"),
              bg=ACCENT, fg="#0B0B12",
              activebackground="#9580FF", activeforeground="#0B0B12",
              font=("Segoe UI", 11, "bold"),
              relief="flat", borderwidth=0,
              padx=20, pady=10, cursor="hand2"
    ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass

    return result["mode"]

def unisci_ass(base_path):
    final_path = os.path.join(base_path, "Final.ass")
    on_top_path = os.path.join(base_path, "On Top.ass")
    comments_path = os.path.join(base_path, "Comments.ass")
    signs_path = os.path.join(base_path, "Signs.ass")
    
    try:
        final_header = []
        final_dialogues = []
        if os.path.exists(final_path):
            with open(final_path, 'r', encoding='utf-8-sig') as f:
                in_header = True
                for line in f:
                    if in_header:
                        final_header.append(line)
                        if line.strip().lower() == '[events]':
                            in_header = False
                            next_line = next(f, '').strip()
                            if next_line.lower().startswith('format:'):
                                final_header.append(next_line + '\n')
                                continue
                    else:
                        if line.strip() and not line.startswith(';') and 'dialogue' in line.lower():
                            final_dialogues.append(line)

        def extract_timed_lines(filepath):
            timed_lines = []
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    in_events = False
                    for line in f:
                        if line.strip().lower() == '[events]':
                            in_events = True
                            continue
                        if in_events and line.strip() and not line.startswith(';'):
                            if line.lower().startswith('format:'):
                                continue
                            if ',' in line:
                                start_time = line.split(',')[1]
                                timed_lines.append((start_time, line))
            return timed_lines

        comments_lines = []
        if os.path.exists(comments_path):
            with open(comments_path, 'r', encoding='utf-8-sig') as f:
                in_events = False
                for line in f:
                    if line.strip().lower() == '[events]':
                        in_events = True
                        continue
                    if in_events and line.strip() and not line.startswith(';'):
                        if line.lower().startswith('format:'):
                            continue
                        if 'comment' in line.lower():
                            comments_lines.append(line)

        on_top_lines = extract_timed_lines(on_top_path)
        on_top_lines.sort(key=lambda x: x[0])

        signs_lines = []
        if os.path.exists(signs_path):
            with open(signs_path, 'r', encoding='utf-8-sig') as f:
                in_events = False
                for line in f:
                    if line.strip().lower() == '[events]':
                        in_events = True
                        continue
                    if in_events and line.strip() and not line.startswith(';'):
                        if line.lower().startswith('format:'):
                            continue
                        if 'dialogue' in line.lower():
                            signs_lines.append(line)

        final_timed = extract_timed_lines(final_path)
        final_timed.sort(key=lambda x: x[0])

        all_lines = []
        all_lines.extend(comments_lines)
        
        merged_dialogues = []
        i = j = 0
        while i < len(on_top_lines) and j < len(final_timed):
            if on_top_lines[i][0] <= final_timed[j][0]:
                merged_dialogues.append(on_top_lines[i][1])
                i += 1
            else:
                merged_dialogues.append(final_timed[j][1])
                j += 1
        
        merged_dialogues.extend([line[1] for line in on_top_lines[i:]])
        merged_dialogues.extend([line[1] for line in final_timed[j:]])
        
        all_lines.extend(merged_dialogues)
        all_lines.extend(signs_lines)

        with open(final_path, 'w', encoding='utf-8-sig') as f:
            f.writelines(final_header)
            f.writelines(all_lines)

    except Exception as e:
        messagebox.showerror("Error", f"Error merging ASS files: {str(e)}")

def unisci_srt(base_path):
    final_path = os.path.join(base_path, "Final.srt")
    on_top_path = os.path.join(base_path, "On Top.srt")
    
    try:
        final_blocks = []
        if os.path.exists(final_path):
            with open(final_path, 'r', encoding='utf-8-sig') as f:
                current_block = []
                for line in f:
                    if line.strip() == '' and current_block:
                        final_blocks.append(current_block)
                        current_block = []
                    else:
                        current_block.append(line)
                if current_block:
                    final_blocks.append(current_block)

        on_top_blocks = []
        if os.path.exists(on_top_path):
            with open(on_top_path, 'r', encoding='utf-8-sig') as f:
                current_block = []
                for line in f:
                    if line.strip() == '' and current_block:
                        on_top_blocks.append(current_block)
                        current_block = []
                    else:
                        current_block.append(line)
                if current_block:
                    on_top_blocks.append(current_block)
            
            def get_start_time(block):
                if len(block) > 1:
                    time_line = block[1]
                    if '-->' in time_line:
                        return time_line.split('-->')[0].strip()
                return '99:59:59,999'
            
            on_top_blocks.sort(key=get_start_time)

        merged_blocks = []
        i = j = 0
        while i < len(on_top_blocks) and j < len(final_blocks):
            time_on_top = get_start_time(on_top_blocks[i])
            time_final = get_start_time(final_blocks[j])
            
            if time_on_top <= time_final:
                merged_blocks.append(on_top_blocks[i])
                i += 1
            else:
                merged_blocks.append(final_blocks[j])
                j += 1
        
        merged_blocks.extend(on_top_blocks[i:])
        merged_blocks.extend(final_blocks[j:])

        with open(final_path, 'w', encoding='utf-8-sig') as f:
            for block in merged_blocks:
                f.writelines(block)
                f.write('\n')

    except Exception as e:
        messagebox.showerror("Error", f"Error merging SRT files: {str(e)}")

def elimina_file(files_to_delete, base_path):
    for file in files_to_delete:
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error removing {file_path}: {e}")

def sposta_file(files_to_move, base_path, desktop_path):
    if desktop_path is None:
        return
    if os.path.abspath(base_path) == os.path.abspath(desktop_path):
        return
    for file in files_to_move:
        src_path = os.path.join(base_path, file)
        dest_path = os.path.join(desktop_path, file)
        if os.path.exists(src_path):
            try:
                shutil.move(src_path, dest_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error moving {src_path}: {e}")

def is_file_empty(filepath):
    if not os.path.exists(filepath):
        return True
    
    if filepath.lower().endswith('.ass'):
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            in_events = False
            for line in f:
                if line.strip().lower() == '[events]':
                    in_events = True
                    continue
                if in_events and line.strip() and not line.startswith(';'):
                    if 'dialogue' in line.lower() or 'comment' in line.lower():
                        return False
        return True
    
    elif filepath.lower().endswith('.srt'):
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            has_content = False
            current_block = []
            for line in f:
                if line.strip() == '' and current_block:
                    if len(current_block) >= 2:
                        has_content = True
                        break
                    current_block = []
                else:
                    current_block.append(line)
            if current_block and len(current_block) >= 2:
                has_content = True
        return not has_content
    
    return True

def verifica_file(files, base_path):
    return all(os.path.exists(os.path.join(base_path, file)) for file in files)

project_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
desktop_path = get_output_dir(project_path)

mkv_in_root = None
try:
    for f in os.listdir(project_path):
        if f.lower().endswith('.mkv'):
            mkv_in_root = f
            break
except OSError:
    pass

files_to_delete_option_1 = [
    "adjusted_Sub.srt",
    "scene_timestamps.srt",
    "scene_timestamps_adjusted.srt",
    "Sub.srt",
    "Dialoghi.ass",
    "Final.srt",
    "On Top.ass",
    "Comments.ass",
    "Signs.ass"
]

files_to_delete_option_2 = [
    "adjusted_Sub.srt",
    "scene_timestamps.srt",
    "scene_timestamps_adjusted.srt",
    "Sub.srt",
    "On Top.srt"
]

# MKV
files_to_move_option_1 = ["Final.ass"]
files_to_move_option_2 = ["Final.srt"]

if mkv_in_root:
    files_to_move_option_1.append(mkv_in_root)
    files_to_move_option_2.append(mkv_in_root)

sub_path = get_sub_path(project_path)
dialoghi_path = os.path.join(project_path, "Dialoghi.ass")
final_ass_path = os.path.join(project_path, "Final.ass")

can_offer_copy = (
    sub_path is not None
    and os.path.isfile(dialoghi_path)
    and os.path.isfile(final_ass_path)
)

output_mode = chiedi_output_mode() if can_offer_copy else "recomposed"

try:
    if output_mode == "copy":
        original_out = os.path.join(project_path, "Original_timed.ass")
        ok = crea_copia_originale_timata(sub_path, dialoghi_path, final_ass_path, original_out)

        if ok:
            files_to_move = ["Original_timed.ass"]
            if mkv_in_root:
                files_to_move.append(mkv_in_root)
            sposta_file(files_to_move, project_path, desktop_path)

            to_delete = [
                "adjusted_Sub.srt", "scene_timestamps.srt", "scene_timestamps_adjusted.srt",
                "Sub.srt",
                "Dialoghi.ass", "Final.srt", "Final.ass",
                "On Top.ass", "Comments.ass", "Signs.ass"
            ]
            elimina_file(to_delete, project_path)
        else:
            messagebox.showwarning(
                "Copy original",
                "Could not create the original-timed copy.\n"
                "Falling back to Recomposed."
            )
            output_mode = "recomposed"

    if output_mode == "recomposed":
        if verifica_file(["Final.ass", "On Top.ass", "Comments.ass", "Signs.ass"], project_path):
            unisci_ass(project_path)
            sposta_file(files_to_move_option_1, project_path, desktop_path)
            elimina_file(files_to_delete_option_1, project_path)
        elif verifica_file(["Final.srt", "On Top.srt"], project_path):
            unisci_srt(project_path)
            sposta_file(files_to_move_option_2, project_path, desktop_path)
            elimina_file(files_to_delete_option_2, project_path)
        else:
            messagebox.showinfo("Info", "No file set found to move.")

except Exception as e:
    messagebox.showerror("Error", f"General error: {e}")

finally:
    try:
        os.remove(os.path.join(project_path, ".asr_pipeline_paths.json"))
    except OSError:
        pass