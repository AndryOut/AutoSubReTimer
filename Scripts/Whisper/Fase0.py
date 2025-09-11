import os
import subprocess
import shutil

# Percorso
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# MKV
mkv_files = sorted([f for f in os.listdir(project_path) if f.endswith('.mkv')])
if not mkv_files:
    print(f"Errore: Nessun file .mkv trovato nella directory '{project_path}'.")
    exit()

is_batch = len(mkv_files) > 1

if is_batch:
    print(f"Trovati {len(mkv_files)} file MKV, modalità BATCH attivata...")
    # Crea cartella Batch
    batch_dir = os.path.join(project_path, "Batch")
    os.makedirs(batch_dir, exist_ok=True)
else:
    print(f"Trovato 1 file MKV, modalità singola...")
    input_file = mkv_files[0]
    input_path = os.path.join(project_path, input_file)
    output_dir = project_path

ffmpeg_path = os.path.join(project_path, "ffmpeg", "bin", "ffmpeg.exe")
ffprobe_path = os.path.join(project_path, "ffmpeg", "bin", "ffprobe.exe")

# Verifica che FFmpeg e ffprobe esistano
if not os.path.isfile(ffmpeg_path):
    print(f"Errore: FFmpeg non trovato nel percorso '{ffmpeg_path}'.")
    exit()
if not os.path.isfile(ffprobe_path):
    print(f"Errore: FFprobe non trovato nel percorso '{ffprobe_path}'.")
    exit()

if is_batch:
    # PROCESSAMENTO BATCH
    for i, mkv_file in enumerate(mkv_files, 1):
        print(f"\nElaborazione file {i}/{len(mkv_files)}: {mkv_file}")
        
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
            print("Verifica del codec audio del file di input...")
            result = subprocess.run(ffprobe_command, check=True, stdout=subprocess.PIPE, text=True)
            codec = result.stdout.strip()
            print(f"Codec rilevato: {codec}")

            # Se il file è già in formato AAC, lo estrae
            if codec == "aac":
                print("L'audio è già in formato AAC. Estrazione senza conversione...")
                ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -vn -sn -dn -threads 0 -i "{input_path}" -acodec copy "{audio_path}"'
            else:
                # Converte l'audio in formato AAC
                print("Convertendo l'audio in formato AAC...")
                ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -i "{input_path}" -vn -sn -dn -acodec aac -b:a 192k -ac 2 -threads 0 "{audio_path}"'

            subprocess.run(ffmpeg_command, check=True)
            print(f"File audio salvato come: {audio_path}")

        except subprocess.CalledProcessError as e:
            print(f"Errore durante il processo di estrazione/conversione: {e}")
            continue
        shutil.move(mkv_src, mkv_dest)

    print(f"\nOperazione BATCH completata. File elaborati: {len(mkv_files)}")

else:
    # PROCESSAMENTO SINGOLO
    print(f"Trovato file: {input_file}")
    
    audio_file = "whisper.aac"
    audio_path = os.path.join(output_dir, audio_file)

    ffprobe_command = f'"{ffprobe_path}" -hide_banner -select_streams a -show_entries stream=codec_name -of csv=p=0 "{input_path}"'

    try:
        print("Verifica del codec audio del file di input...")
        result = subprocess.run(ffprobe_command, check=True, stdout=subprocess.PIPE, text=True)
        codec = result.stdout.strip()
        print(f"Codec rilevato: {codec}")

        if codec == "aac":
            print("L'audio è già in formato AAC. Estrazione senza conversione...")
            ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -vn -sn -dn -threads 0 -i "{input_path}" -acodec copy "{audio_path}"'
        else:
            # Converte l'audio in formato AAC
            print("Convertendo l'audio in formato AAC...")
            ffmpeg_command = f'"{ffmpeg_path}" -hide_banner -y -i "{input_path}" -vn -sn -dn -acodec aac -b:a 192k -ac 2 -threads 0 "{audio_path}"'

        subprocess.run(ffmpeg_command, check=True)
        print(f"Operazione completata. File audio salvato come: {audio_path}")

    except subprocess.CalledProcessError as e:
        print(f"Errore durante il processo di estrazione/conversione: {e}")
        exit()