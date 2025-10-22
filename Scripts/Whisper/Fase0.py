import os
import subprocess
import shutil

# Percorso
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# MKV
mkv_files = sorted([f for f in os.listdir(project_path) if f.endswith('.mkv')])
if not mkv_files:
    print(f"Error: No .mkv file found in directory '{project_path}'.")
    exit()

is_batch = len(mkv_files) > 1

if is_batch:
    print(f"Found {len(mkv_files)} MKV files, BATCH mode enabled...")
    # Crea cartella Batch
    batch_dir = os.path.join(project_path, "Batch")
    os.makedirs(batch_dir, exist_ok=True)
else:
    print(f"Found 1 MKV file, single mode...")
    input_file = mkv_files[0]
    input_path = os.path.join(project_path, input_file)
    output_dir = project_path

ffmpeg_path = os.path.join(project_path, "ffmpeg", "bin", "ffmpeg.exe")
ffprobe_path = os.path.join(project_path, "ffmpeg", "bin", "ffprobe.exe")

# Verifica che FFmpeg e ffprobe esistano
if not os.path.isfile(ffmpeg_path):
    print(f"Error: FFmpeg not found in path '{ffmpeg_path}'.")
    exit()
if not os.path.isfile(ffprobe_path):
    print(f"Error: FFprobe not found in path '{ffprobe_path}'.")
    exit()

if is_batch:
    # PROCESSAMENTO BATCH
    for i, mkv_file in enumerate(mkv_files, 1):
        print(f"\nProcessing files {i}/{len(mkv_files)}: {mkv_file}")
        
        # Crea cartella numerata
        episode_dir = os.path.join(batch_dir, str(i))
        os.makedirs(episode_dir, exist_ok=True)
        
        # Copia l'MKV nella cartella numerata
        mkv_src = os.path.join(project_path, mkv_file)
        mkv_dest = os.path.join(episode_dir, mkv_file)        
        
        audio_file = f"whisper{i}.aac"
        audio_path = os.path.join(batch_dir, audio_file) 
        
        input_path = os.path.join(project_path, mkv_file)
        
        # Comando ffprobe per verificare il codec audio
        ffprobe_command = f'"{ffprobe_path}" -hide_banner -select_streams a -show_entries stream=codec_name -of csv=p=0 "{input_path}"'
        
        try:
            print("Checking the audio codec of the input file...")
            result = subprocess.run(ffprobe_command, check=True, stdout=subprocess.PIPE, text=True)
            codec = result.stdout.strip()
            print(f"Codec detected: {codec}")

            # Se il file è già in formato AAC, lo estrae
            if codec == "aac":
                print("Audio is already in AAC format. Extracting without conversion...")
                ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -vn -sn -dn -threads 0 -i "{input_path}" -acodec copy "{audio_path}"'
            else:
                # Converte l'audio in formato AAC
                print("Converting audio to AAC format...")
                ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -i "{input_path}" -vn -sn -dn -acodec aac -b:a 192k -ac 2 -threads 0 "{audio_path}"'

            subprocess.run(ffmpeg_command, check=True)
            print(f"Audio file saved as: {audio_path}")

        except subprocess.CalledProcessError as e:
            print(f"Error during extraction/conversion process: {e}")
            continue
        shutil.move(mkv_src, mkv_dest)

    print(f"\nBATCH operation completed. Files processed: {len(mkv_files)}")

else:
    # PROCESSAMENTO SINGOLO
    print(f"Found file: {input_file}")
    
    audio_file = "whisper.aac"
    audio_path = os.path.join(output_dir, audio_file)

    ffprobe_command = f'"{ffprobe_path}" -hide_banner -select_streams a -show_entries stream=codec_name -of csv=p=0 "{input_path}"'

    try:
        print("Checking the audio codec of the input file...")
        result = subprocess.run(ffprobe_command, check=True, stdout=subprocess.PIPE, text=True)
        codec = result.stdout.strip()
        print(f"Codec detected: {codec}")

        if codec == "aac":
            print("Audio is already in AAC format. Extracting without conversion...")
            ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -vn -sn -dn -threads 0 -i "{input_path}" -acodec copy "{audio_path}"'
        else:
            # Converte l'audio in formato AAC
            print("Converting audio to AAC format...")
            ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -i "{input_path}" -vn -sn -dn -acodec aac -b:a 192k -ac 2 -threads 0 "{audio_path}"'

        subprocess.run(ffmpeg_command, check=True)
        print(f"Operation completed. Audio file saved as: {audio_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error during extraction/conversion process: {e}")
        exit()