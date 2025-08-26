import os
import shutil

# Percorsi
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")

# File da gestire
TARGET_FILES = {
    'keep': [
        "Final.srt",          
        "whisper_adjusted.srt",  

    ],
    'cleanup': [
        "whisper.srt",
        "whisper.aac", 
        "vocali.wav",
        "scene_timestamps.srt",
        "scene_timestamps_adjusted.srt"
    ]
}

def find_existing_files(file_list, search_dir):
    return [f for f in file_list if os.path.exists(os.path.join(search_dir, f))]

def move_to_desktop(files, source_dir, dest_dir):
    for filename in files:
        try:
            shutil.move(os.path.join(source_dir, filename), 
                      os.path.join(dest_dir, filename))
        except Exception:
            pass

def cleanup_files(files, target_dir):
    for filename in files:
        try:
            os.remove(os.path.join(target_dir, filename))
        except Exception:
            pass

def main():
    # Cerca MKV
    mkv_files = [f for f in os.listdir(project_dir) if f.endswith('.mkv')]
    if not mkv_files:
        raise FileNotFoundError("Nessun file .mkv trovato nella directory.")
    mkv_filename = mkv_files[0]

    files_to_keep = TARGET_FILES['keep'] + [mkv_filename]

    # 1. Trova e sposta i file da conservare
    existing_to_keep = find_existing_files(files_to_keep, project_dir)
    move_to_desktop(existing_to_keep, project_dir, desktop_dir)
    
    # 2. Elimina i file residui
    existing_to_clean = find_existing_files(TARGET_FILES['cleanup'], project_dir)
    cleanup_files(existing_to_clean, project_dir)

if __name__ == "__main__":
    main()