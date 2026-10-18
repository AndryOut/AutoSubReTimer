import os
import json
import time
import subprocess
import shutil
import sys

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
handshake_path = os.path.join(project_path, ".asr_pipeline_paths.json")

# Attende l'handshake di Fase0 (scritto subito dopo la scelta del video).
print("Waiting for video selection from Fase0...")
video_from_handshake = None
while True:
    if os.path.exists(handshake_path):
        try:
            with open(handshake_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "video_path" in data:
                video_from_handshake = data["video_path"]
                break
        except (OSError, json.JSONDecodeError):
            pass
    time.sleep(0.1)

if video_from_handshake and os.path.isfile(video_from_handshake):
    input_path = video_from_handshake
    input_file = os.path.basename(input_path)
    print(f"Video from Fase0: {input_file}")
else:
    mkv_files = [f for f in os.listdir(project_path) if f.endswith('.mkv')]
    if not mkv_files:
        print(f"Error: No .mkv file found in directory '{project_path}'.")
        sys.exit(1)
    input_file = mkv_files[0]
    input_path = os.path.join(project_path, input_file)
    print(f"Video from project: {input_file}")

# Directory input, output
output_dir = project_path

# Percorso FFmpeg
ffmpeg_path = os.path.join(project_path, "ffmpeg", "bin", "ffmpeg.exe")

# Verifica che FFmpeg esista
if not os.path.isfile(ffmpeg_path):
    print(f"Error: FFmpeg not found in PATH '{ffmpeg_path}'.")
    sys.exit(1)

def get_japanese_audio_stream(file_path, ffmpeg_path):
    try:
        ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream_tags=language",
            "-of", "csv=p=0",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            languages = [l.strip().lower() for l in result.stdout.decode(errors="replace").splitlines()]
            for i, lang in enumerate(languages):
                if lang in ("jpn", "ja", "jp"):
                    return i
            print("No Japanese audio track found: using the first audio track.")
    except Exception as e:
        print(f"Error ffprobe: {e}")
    return 0

def get_audio_channels(file_path, ffmpeg_path, stream=0):
    try:
        ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
        
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", f"a:{stream}", 
            "-show_entries", "stream=channels",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            channels_str = result.stdout.decode().strip()
            if channels_str.isdigit():
                return int(channels_str)
            else:
                print(f"Invalid ffprobe output: {channels_str}")
        else:
            print(f"FFprobe error: {result.stderr.decode()}")
            
    except Exception as e:
        print(f"Error ffprobe: {e}")
    
    return None

# Traccia audio giapponese (di solito la prima) e i suoi canali
audio_stream = get_japanese_audio_stream(input_path, ffmpeg_path)
if audio_stream:
    print(f"Japanese audio is track {audio_stream + 1}: using it.")
channels = get_audio_channels(input_path, ffmpeg_path, audio_stream)

if channels is None:
    print("Error: Unable to determine audio channels. Using file directly.")
    input_for_demucs = input_path
elif channels == 2:
    print("Audio is already 2-channel stereo. Using file directly.")
    input_for_demucs = input_path
else:  
    print(f"Audio has {channels} channels. Converting to 2-channel stereo...")
    temp_wav = os.path.join(output_dir, "temp_demucs.wav")

    ffmpeg_convert_cmd = [
        ffmpeg_path,
        "-hide_banner",
        "-i", input_path,
        "-map", f"0:a:{audio_stream}",
        "-vn", "-sn", "-dn",  
        "-c:a", "pcm_s16le",  
        "-ar", "44100",       
        "-ac", "2",       
        "-threads", "0",
        "-y",                 
        temp_wav
    ]

    subprocess.run(ffmpeg_convert_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    input_for_demucs = temp_wav

python_executable = os.path.join(project_path, "engine", "python.exe")
demucs_dir = os.path.join(project_path, "Scripts", "Engine")

# Comando per eseguire Demucs con device dinamico (GPU se la prova passa, altrimenti CPU)
os.environ['PATH'] += os.pathsep + os.path.join(project_path, "ffmpeg", "bin")
demucs_args = [
    python_executable, "-m", "run_demucs",
    "--two-stems=vocals", "--other-method", "none",
    "--clip-mode", "clamp", "--float32",
    "-o", output_dir, input_for_demucs
]
demucs_env = os.environ.copy()
existing_pp = demucs_env.get("PYTHONPATH", "")
demucs_env["PYTHONPATH"] = demucs_dir + (os.pathsep + existing_pp if existing_pp else "")
demucs_env["AUTOSUB_AUDIO_STREAM"] = str(audio_stream) if input_for_demucs == input_path else "0"

try:
    subprocess.run(demucs_args, check=True, env=demucs_env)

    # Percorso della cartella generata automaticamente da Demucs
    demucs_output_dir = os.path.join(output_dir, "htdemucs", os.path.splitext(os.path.basename(input_for_demucs))[0])

    # Sposta il file `vocals.wav` nella directory principale, rinominandolo in "vocali.wav"
    vocals_file = os.path.join(demucs_output_dir, "vocals.wav")
    renamed_vocals_file = os.path.join(output_dir, "vocali.wav")
    if os.path.exists(vocals_file):
        shutil.move(vocals_file, renamed_vocals_file)

    # Rimuove la cartella `htdemucs`
    shutil.rmtree(os.path.join(output_dir, "htdemucs"))

    # Pulizia file temporaneo solo se è stato creato
    if input_for_demucs != input_path and os.path.exists(input_for_demucs):
        os.remove(input_for_demucs)

except subprocess.CalledProcessError as e:
    print(f"Error executing Demucs: {e}")
    # Pulizia file temporaneo solo se è stato creato
    if input_for_demucs != input_path and os.path.exists(input_for_demucs):
        os.remove(input_for_demucs)
    sys.exit(1)