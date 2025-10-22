import os
import shutil

# Percorsi
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")

# VERIFICA SE ESISTE LA CARTELLA BATCH
batch_dir = os.path.join(project_dir, "Batch")
is_batch = os.path.exists(batch_dir) and os.path.isdir(batch_dir)

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
    if is_batch:
        print("Batch folder found, batch cleanup...")
        
        # Pulisce i file in ogni cartella
        episode_dirs = sorted([d for d in os.listdir(batch_dir) if os.path.isdir(os.path.join(batch_dir, d)) and d.isdigit()])
        
        for episode_dir in episode_dirs:
            episode_path = os.path.join(batch_dir, episode_dir)
            
            mkv_files = [f for f in os.listdir(episode_path) if f.endswith('.mkv')]
            if mkv_files:
                mkv_filename = mkv_files[0]
            
            existing_keep_files = find_existing_files(["Final.srt", f"whisper{episode_dir}_adjusted.srt"], episode_path)
            
            files_to_move = []
            cleanup_list = [
                f"whisper{episode_dir}.srt",  
                f"whisper{episode_dir}.aac",  
                "vocali.wav",
                "scene_timestamps.srt", 
                "scene_timestamps_adjusted.srt"
            ]
            
            if "Final.srt" in existing_keep_files:
                files_to_move = ["Final.srt"]
                if f"whisper{episode_dir}_adjusted.srt" in existing_keep_files:
                    cleanup_list.append(f"whisper{episode_dir}_adjusted.srt") 
            else:
                files_to_move = existing_keep_files
            
            if mkv_files:
                files_to_move.append(mkv_filename)
            
            move_to_desktop(files_to_move, episode_path, episode_path)
            existing_to_clean = find_existing_files(cleanup_list, episode_path)
            cleanup_files(existing_to_clean, episode_path)
            print(f"Cleaning up folder {episode_dir}: kept {len(files_to_move)} files, deleted {len(existing_to_clean)} files")
        
        try:
            batch_on_desktop = os.path.join(desktop_dir, "Batch")
            if os.path.exists(batch_on_desktop):
                shutil.rmtree(batch_on_desktop)
            shutil.move(batch_dir, desktop_dir)
            print(f"Batch folder moved to Desktop: {batch_on_desktop}")
        except Exception as e:
            print(f"Error moving Batch folder: {e}")
        
        existing_to_clean = find_existing_files(TARGET_FILES['cleanup'], project_dir)
        cleanup_files(existing_to_clean, project_dir)
        
    else:
        # COMPORTAMENTO PER SINGOLO FILE
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