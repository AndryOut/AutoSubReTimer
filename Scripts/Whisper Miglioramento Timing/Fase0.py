import os
import subprocess
import shutil
import torch

# Percorso relativo al progetto
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# MKV
mkv_files = [f for f in os.listdir(project_path) if f.endswith('.mkv')]
if not mkv_files:
    print(f"Errore: Nessun file .mkv trovato nella directory '{project_path}'.")
    exit()

input_file = mkv_files[0]
input_path = os.path.join(project_path, input_file)
output_dir = project_path

print(f"Trovato file: {input_file}")

# Percorso relativo per FFmpeg
ffmpeg_path = os.path.join(project_path, "ffmpeg", "bin", "ffmpeg.exe")

# Verifica che FFmpeg esista
if not os.path.isfile(ffmpeg_path):
    print(f"Errore: FFmpeg non trovato nel percorso '{ffmpeg_path}'.")
    exit()

input_for_demucs = input_path

# Percorso per l'eseguibile Python dell'ambiente virtuale
python_executable = os.path.join(project_path, "main", "Scripts", "python.exe")

# Verifica se CUDA è disponibile e imposta device
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    print("Elaborazione su GPU (CUDA)...")
else:
    print("CUDA non disponibile. Elaborazione su CPU (più lenta)...")

# Comando per eseguire Demucs con device dinamico
os.environ['PATH'] += os.pathsep + os.path.join(project_path, "ffmpeg", "bin")
demucs_command = f'"{python_executable}" -m demucs --two-stems=vocals --clip-mode clamp --float32 --jobs 2 -d {device} -o "{output_dir}" "{input_path}"'

try:
    print(f"Esecuzione di Demucs: {demucs_command}")
    subprocess.run(demucs_command, check=True)

    # Percorso della cartella generata automaticamente da Demucs
    demucs_output_dir = os.path.join(output_dir, "htdemucs", os.path.splitext(os.path.basename(input_path))[0])

    # Sposta il file `vocals.wav` nella directory principale, rinominandolo in "vocali.wav"
    vocals_file = os.path.join(demucs_output_dir, "vocals.wav")
    renamed_vocals_file = os.path.join(output_dir, "vocali.wav")
    if os.path.exists(vocals_file):
        shutil.move(vocals_file, renamed_vocals_file)
        print(f"`vocals.wav` rinominato in: {renamed_vocals_file}")

    # Rimuovi la cartella `htdemucs`
    shutil.rmtree(os.path.join(output_dir, "htdemucs"))
    print("Cartella `htdemucs` eliminata.")

    print("Operazione completata! Rimasto solo `vocali.wav` nella directory principale.")
except subprocess.CalledProcessError as e:
    print(f"Errore durante l'esecuzione di Demucs: {e}")
    exit()