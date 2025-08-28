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

    existing_keep_files = find_existing_files(TARGET_FILES['keep'], project_dir)
    
    files_to_move = []
    cleanup_list = TARGET_FILES['cleanup'].copy() 
    
    if "Final.srt" in existing_keep_files:
        files_to_move = ["Final.srt"]
        if "whisper_adjusted.srt" in existing_keep_files:
            cleanup_list.append("whisper_adjusted.srt") 
    else:
        files_to_move = existing_keep_files
    
    files_to_move.append(mkv_filename)
    
    move_to_desktop(files_to_move, project_dir, desktop_dir)
    
    existing_to_clean = find_existing_files(cleanup_list, project_dir)
    cleanup_files(existing_to_clean, project_dir)

if __name__ == "__main__":
    main()