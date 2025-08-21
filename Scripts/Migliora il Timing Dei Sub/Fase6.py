import os
from tkinter import messagebox
import tkinter as tk

def chiedi_unione():
    temp_root = tk.Tk()
    temp_root.withdraw()
    
    response = None
    dialog = tk.Toplevel(temp_root)
    dialog.title("Merge Subtitles")
    
    dialog.grab_set()
    dialog.focus_force()
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)
    
    msg = """Do you want to merge all files into one sub?

Yes: you will have one final file.

No: 'On Top', 'Comments' and 'Signs' will remain separated from 'Final' with adjusted timing."""
    
    tk.Label(dialog, text=msg, justify=tk.LEFT, padx=20, pady=20).pack()
    
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)
    
    def on_yes():
        nonlocal response
        response = True
        dialog.destroy()
        temp_root.quit()
    
    def on_no():
        nonlocal response
        response = False
        dialog.destroy()
        temp_root.quit()
    
    tk.Button(btn_frame, text="Yes", command=on_yes, width=10).pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="No", command=on_no, width=10).pack(side=tk.LEFT, padx=10)
    
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f'+{x}+{y}')
    
    temp_root.mainloop()
    temp_root.destroy()
    
    return response

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
        messagebox.showerror("Errore", f"Errore nell'unione dei file ASS: {str(e)}")

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
        messagebox.showerror("Errore", f"Errore nell'unione dei file SRT: {str(e)}")

def elimina_file(files_to_delete, base_path):
    for file in files_to_delete:
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                messagebox.showerror("Errore", f"Errore nel rimuovere {file_path}: {e}")

def sposta_file(files_to_move, base_path, desktop_path):
    for file in files_to_move:
        src_path = os.path.join(base_path, file)
        dest_path = os.path.join(desktop_path, file)
        if os.path.exists(src_path):
            try:
                os.rename(src_path, dest_path)
            except Exception as e:
                messagebox.showerror("Errore", f"Errore nello spostare {src_path}: {e}")

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
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

files_to_delete_option_1 = [
    "adjusted_Sub.srt",
    "scene_timestamps.srt",
    "scene_timestamps_adjusted.srt",
    "Sub.srt",
    "vocali.wav",
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
    "vocali.wav",
    "On Top.srt"
]

# MKV
mkv_files = [f for f in os.listdir(project_path) if f.endswith('.mkv')]
if not mkv_files:
    raise FileNotFoundError("Nessun file .mkv trovato nella directory.")
mkv_filename = mkv_files[0]

files_to_move_option_1 = [
    mkv_filename,
    "Final.ass"
]

files_to_move_option_2 = [
    mkv_filename,
    "Final.srt"
]

try:
    unisci_files = chiedi_unione()
    
    if verifica_file(["Final.ass", "On Top.ass", "Comments.ass", "Signs.ass"], project_path):
        if unisci_files:
            unisci_ass(project_path)
            sposta_file(files_to_move_option_1, project_path, desktop_path)
            elimina_file(files_to_delete_option_1, project_path)
        else:
            files_to_move = [mkv_filename, "Final.ass"]
            for file in ["On Top.ass", "Comments.ass", "Signs.ass"]:
                file_path = os.path.join(project_path, file)
                if not is_file_empty(file_path):
                    files_to_move.append(file)
                else:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        messagebox.showerror("Errore", f"Errore nell'eliminare {file}: {e}")
            
            sposta_file(files_to_move, project_path, desktop_path)
            elimina_file(files_to_delete_option_1[:-3], project_path)
    
    elif verifica_file(["Final.srt", "On Top.srt"], project_path):
        if unisci_files:
            unisci_srt(project_path)
            sposta_file(files_to_move_option_2, project_path, desktop_path)
            elimina_file(files_to_delete_option_2, project_path)
        else:
            files_to_move = [mkv_filename, "Final.srt"]
            on_top_path = os.path.join(project_path, "On Top.srt")
            if not is_file_empty(on_top_path):
                files_to_move.append("On Top.srt")
            else:
                try:
                    os.remove(on_top_path)
                except Exception as e:
                    messagebox.showerror("Errore", f"Errore nell'eliminare On Top.srt: {e}")
            
            sposta_file(files_to_move, project_path, desktop_path)
            elimina_file(files_to_delete_option_2[:-1], project_path)
    
    else:
        messagebox.showinfo("Info", "Nessun set di file trovato per lo spostamento.")

except Exception as e:
    messagebox.showerror("Errore", f"Si è verificato un errore generale: {e}")