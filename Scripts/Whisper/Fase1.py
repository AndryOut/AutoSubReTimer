import os
import subprocess
import sys
import json
from pathlib import Path

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

def main():
    setup_console_encoding()
    
    try:
        # Carica configurazione
        config = load_config()
        if config is None:
            return False
            
        # Percorsi
        project_root = Path(__file__).parent.parent.parent
        exe_file = project_root / "Faster-Whisper-XXL" / "faster-whisper-xxl.exe"
        input_file = project_root / "whisper.aac"
        exe_folder = project_root / "Faster-Whisper-XXL"
        
        if not exe_file.exists():
            print("Error: faster-whisper-xxl.exe not found!")
            return False
        
        # Comando Whisper con parametri dalla config
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
        
        # Esecuzione
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