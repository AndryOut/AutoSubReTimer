import os
import subprocess
import sys
import json
from pathlib import Path
import shutil

def setup_console_encoding():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def load_config():
    config_path = Path(__file__).parent / "whisper_config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {str(e)}")
        return None

def process_batch(project_root, exe_file, exe_folder, config):
    batch_dir = project_root / "Batch"
    aac_files = sorted(batch_dir.glob("whisper*.aac"))
    
    whisper_cmd = [
        str(exe_file),
        "--language", config["default_values"]["language"],
        "--model", config["default_values"]["model"],
        "--standard_asia",
        "--vad_method", "pyannote_v3",
        "--sentence",
        "--patience", "1.5",
        "--output_dir", str(batch_dir)
    ]
    
    for aac_file in aac_files:
        whisper_cmd.append(str(aac_file))
    
    print("Executing batch command:", " ".join(whisper_cmd))
    
    process = subprocess.Popen(
        whisper_cmd,
        cwd=str(exe_folder),
        stdout=sys.stdout,
        stderr=sys.stderr,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace',
        shell=True
    )
    
    process.communicate()
    
    if process.returncode == 3221226505:
        print("[SUCCESS] Batch transcription completed (output might be truncated)")
    elif process.returncode != 0:
        print(f"[ERROR] Whisper failed with code {process.returncode}")
        return False
    
    for i, aac_file in enumerate(aac_files, 1):
        base_name = aac_file.stem  # "whisper1", "whisper2", ecc.
        output_files = list(batch_dir.glob(f"{base_name}.*"))
        
        dest_dir = batch_dir / str(i)
        
        for output_file in output_files:
            if output_file.suffix != ".aac": 
                dest_path = dest_dir / output_file.name
                try:
                    shutil.move(str(output_file), str(dest_path))
                except Exception as e:
                    print(f"Error to move {output_file.name}: {e}")
    
    for aac_file in aac_files:
        try:
            aac_file.unlink()
        except Exception as e:
            print(f"Error deleting {aac_file.name}: {e}")
    
    return True

def main():
    setup_console_encoding()
    
    try:
        config = load_config()
        if config is None:
            return False
            
        # Percorsi
        project_root = Path(__file__).parent.parent.parent
        exe_file = project_root / "Faster-Whisper-XXL" / "faster-whisper-xxl.exe"
        exe_folder = project_root / "Faster-Whisper-XXL"  
        
        if not exe_file.exists():
            print("Error: faster-whisper-xxl.exe not found!")
            return False
        
        batch_dir = project_root / "Batch"
    
        if batch_dir.exists() and batch_dir.is_dir():
            # Modalità batch
            print("Batch folder found, batch processing...")
            return process_batch(project_root, exe_file, exe_folder, config)
        else:
            # Modalità singolo file
            input_file = project_root / "whisper.aac" 
        
        if not input_file.exists():
            print("Error: whisper.aac not found!")
            return False
        
        whisper_cmd = [
            str(exe_file),
            str(input_file),
            "--language", config["default_values"]["language"],
            "--model", config["default_values"]["model"],
            "--standard_asia",
            "--vad_method", "pyannote_v3",
            "--sentence",
            "--patience", "1.5",
            "--output_dir", str(project_root)
        ]
        
        print("Executing command:", " ".join(whisper_cmd))
        
        process = subprocess.Popen(
            whisper_cmd,
            cwd=str(exe_folder),
            stdout=sys.stdout,
            stderr=sys.stderr,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            shell=True
        )
        
        process.communicate()
        
        if process.returncode == 3221226505:
            print("[SUCCESS] Transcription completed (output might be truncated)")
            return True
        elif process.returncode != 0:
            print(f"[ERROR] Whisper failed with code {process.returncode}")
            return False
        
        print("[SUCCESS] Transcription completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)