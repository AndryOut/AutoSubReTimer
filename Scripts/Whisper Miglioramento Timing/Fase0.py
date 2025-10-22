import os
import subprocess
import shutil
import torch

# Percorso
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# VERIFICA SE ESISTE LA CARTELLA BATCH
batch_dir = os.path.join(project_path, "Batch")
is_batch = os.path.exists(batch_dir) and os.path.isdir(batch_dir)

def get_audio_channels(file_path, ffmpeg_path):
    try:
        ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
        
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", "a:0", 
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

def process_video(input_path, output_dir, ffmpeg_path, project_path):
    # Verifica che il file esista
    if not os.path.isfile(input_path):
        print(f"Error: The file '{input_path}' does not exist.")
        return False

    # Verifica i canali audio
    channels = get_audio_channels(input_path, ffmpeg_path)

    if channels is None:
        print("Error: Unable to determine audio channels. Use file directly.")
        input_for_demucs = input_path
    elif channels == 2:
        print("Audio already in 2-channel stereo. Using the file directly.")
        input_for_demucs = input_path
    else:  
        print(f"Audio at {channels} channels. Converting to 2-channel stereo...")
        temp_wav = os.path.join(output_dir, "temp_demucs.wav")

        ffmpeg_convert_cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-i", input_path,
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

    python_executable = os.path.join(project_path, "main", "Scripts", "python.exe")

    # Verifica se CUDA è disponibile e imposta device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Comando per eseguire Demucs con device dinamico
    os.environ['PATH'] += os.pathsep + os.path.join(project_path, "ffmpeg", "bin")
    demucs_command = f'"{python_executable}" -m demucs --two-stems=vocals --clip-mode clamp --float32 --jobs 2 -d {device} -o "{output_dir}" "{input_for_demucs}"'

    try:
        subprocess.run(demucs_command, check=True)

        # Percorso della cartella generata automaticamente da Demucs
        base_name = os.path.splitext(os.path.basename(input_for_demucs))[0]
        demucs_output_dir = os.path.join(output_dir, "htdemucs", base_name)

        # Sposta il file `vocals.wav` nella directory output, rinominandolo in "vocali.wav"
        vocals_file = os.path.join(demucs_output_dir, "vocals.wav")
        renamed_vocals_file = os.path.join(output_dir, "vocali.wav")
        if os.path.exists(vocals_file):
            shutil.move(vocals_file, renamed_vocals_file)

        # Rimuove la cartella `htdemucs`
        shutil.rmtree(os.path.join(output_dir, "htdemucs"))

        # Pulizia file temporaneo solo se è stato creato
        if input_for_demucs != input_path and os.path.exists(input_for_demucs):
            os.remove(input_for_demucs)

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error running Demucs: {e}")
        # Pulizia file temporaneo solo se è stato creato
        if input_for_demucs != input_path and os.path.exists(input_for_demucs):
            os.remove(input_for_demucs)
        return False

# Percorso FFmpeg
ffmpeg_path = os.path.join(project_path, "ffmpeg", "bin", "ffmpeg.exe")

if not os.path.isfile(ffmpeg_path):
    print(f"Error: FFmpeg not found in path '{ffmpeg_path}'.")
    exit()

if is_batch:
    print("Batch folder found, batch processing...")
    # Trova tutte le cartelle numerate in Batch
    episode_dirs = sorted([d for d in os.listdir(batch_dir) if os.path.isdir(os.path.join(batch_dir, d)) and d.isdigit()])
    
    for episode_dir in episode_dirs:
        episode_path = os.path.join(batch_dir, episode_dir)
        mkv_files = [f for f in os.listdir(episode_path) if f.endswith('.mkv')]
        
        if not mkv_files:
            print(f"No MKV found in {episode_dir}, skipping...")
            continue
            
        input_file = mkv_files[0]
        input_path = os.path.join(episode_path, input_file)
        output_dir = episode_path  
        
        print(f"\nProcessing {episode_dir}: {input_file}")
        process_video(input_path, output_dir, ffmpeg_path, project_path)
        
else:
    # COMPORTAMENTO PER SINGOLO FILE
    mkv_files = [f for f in os.listdir(project_path) if f.endswith('.mkv')]
    if not mkv_files:
        print(f"Error: No .mkv file found in directory '{project_path}'.")
        exit()
    
    input_file = mkv_files[0]
    input_path = os.path.join(project_path, input_file)
    output_dir = project_path  
    
    print(f"Single processing: {input_file}")
    process_video(input_path, output_dir, ffmpeg_path, project_path)