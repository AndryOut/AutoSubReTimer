import pysrt
from pydub import AudioSegment
import librosa
import os

# Percorso della directory principale
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# VERIFICA SE ESISTE LA CARTELLA BATCH
batch_dir = os.path.join(project_dir, "Batch")
is_batch = os.path.exists(batch_dir) and os.path.isdir(batch_dir)

# Funzione per convertire i millisecondi in SubRipTime
def milliseconds_to_subrip_time(milliseconds):
    hours = int(milliseconds // 3600000)
    minutes = int((milliseconds % 3600000) // 60000)
    seconds = int((milliseconds % 60000) // 1000)
    milliseconds = int(milliseconds % 1000)
    return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

# Funzione per rilevare i segmenti audio
def get_audio_segments(audio_file, silence_threshold=320):
    y, sr = librosa.load(audio_file, sr=None)

    intervals = librosa.effects.split(y, top_db=25)

    segments = []
    for start, end in intervals:
        segments.append((start / sr * 1000, end / sr * 1000))
    
    return segments

# Funzione cercare i picchi precedenti e aggiungere lead-in partendo dal picco trovato
def add_lead_in_to_peak_or_previous(subs, audio_file, lead_in=150):
    audio_segments = get_audio_segments(audio_file)
    for sub in subs:
        start_ms = sub.start.ordinal

        # Controlla se il timestamp iniziale coincide con un picco audio
        found_peak = False
        for segment_start, segment_end in audio_segments:
            if segment_start <= start_ms <= segment_end:
                sub.start = milliseconds_to_subrip_time(max(0, segment_start - lead_in))
                found_peak = True
                break

        # Se non è già su un picco, cerca un picco precedente 
        if not found_peak:
            for segment_start, segment_end in reversed(audio_segments):  # Itera al contrario per cercare i picchi precedenti
                if segment_start < start_ms and (start_ms - segment_start) <= 200:
                    sub.start = milliseconds_to_subrip_time(max(0, segment_start - lead_in))
                    break

    return subs

# Funzione per togliere lead-in partendo dal picco
def adjust_to_speech_peaks(subs, audio_file, max_gap=500):
    audio_segments = get_audio_segments(audio_file)
    for sub in subs:
        start_ms = sub.start.ordinal
        
        # Cerca il picco più vicino
        for segment_start, segment_end in audio_segments:
            if segment_start >= start_ms:
                if segment_start - start_ms <= max_gap:
                    sub.start = milliseconds_to_subrip_time(segment_start)
                else:
                    for closer_start, closer_end in audio_segments:
                        if start_ms <= closer_start <= start_ms + 100:
                            sub.start = milliseconds_to_subrip_time(closer_start)
                            break
                break
    return subs

# Funzione per aggiungere lead-in partendo dal picco
def add_lead_in(subs, lead_in=170):
    """Aggiunge l'anticipo (lead-in) dopo l'allineamento ai picchi"""
    for sub in subs:
        new_start = max(0, sub.start.ordinal - lead_in)
        sub.start = milliseconds_to_subrip_time(new_start)
    return subs

# Funzione per aggiungere lead-out partendo dal picco successivo
def add_lead_out_to_peak_or_next(subs, audio_file, lead_out=400, max_gap=300):
    audio_segments = get_audio_segments(audio_file)
    for sub in subs:
        end_ms = sub.end.ordinal

        # Controlla se il timestamp finale coincide con un picco audio
        found_peak = False
        for segment_start, segment_end in audio_segments:
            if segment_start <= end_ms <= segment_end:
                sub.end = milliseconds_to_subrip_time(min(segment_end + lead_out, audio_segments[-1][1]))
                found_peak = True
                break

        # Se non è già su un picco, cerca un picco successivo
        if not found_peak:
            for segment_start, segment_end in audio_segments:
                if segment_start > end_ms and (segment_start - end_ms) <= max_gap:
                    # Modifica il timestamp per estendere al picco successivo
                    sub.end = milliseconds_to_subrip_time(min(segment_end + lead_out, audio_segments[-1][1]))
                    break

    return subs

# Funzione per collegare segmenti senza overlap con spazio di 0,000 secondi
def adjust_segments_for_overlap(segments, max_lead_out=0, lead_in=0, max_lead_in=0, lead_out=0):
    adjusted_segments = []
    for i in range(len(segments) - 1):
        start, end = segments[i]
        next_start, next_end = segments[i + 1]

        if (next_start - end) <= max_lead_out:
            if (next_start - end) > lead_out:
                remaining_time = next_start - end - lead_out
                end = next_start - remaining_time  
            else:
                end = next_start  
        else:
            if (next_start - end) > lead_in and (next_start - end) < max_lead_in:
                end = next_start - lead_in

        adjusted_segments.append((start, end))

    adjusted_segments.append(segments[-1])
    return adjusted_segments

def process_srt_adjustment(audio_file, srt_file, output_file):
    if not os.path.exists(audio_file):
        print(f"Error: The audio file {audio_file} does not exist.")
        return False

    if not os.path.exists(srt_file):
        print(f"Error: The SRT file {srt_file} does not exist.")
        return False

    subs = pysrt.open(srt_file, encoding='utf-8')

    # Funzione cercare i picchi precedenti e aggiungere lead-in partendo dal picco trovato
    subs = add_lead_in_to_peak_or_previous(subs, audio_file)

    # Toglie e aggiunge lead-in partendo dal picco più vicino
    subs = adjust_to_speech_peaks(subs, audio_file) 
    subs = add_lead_in(subs, lead_in=170)        

    # Aggiunge il lead-out partendo dal picco successivo
    subs = add_lead_out_to_peak_or_next(subs, audio_file)

    # Ottiene i segmenti originali
    final_segments = [(sub.start.ordinal, sub.end.ordinal) for sub in subs]

    # Regola i segmenti per evitare sovrapposizioni
    adjusted_segments = adjust_segments_for_overlap(final_segments)

    # Applica i segmenti regolati ai sottotitoli
    for sub, (start, end) in zip(subs, adjusted_segments):
        sub.start = milliseconds_to_subrip_time(start)
        sub.end = milliseconds_to_subrip_time(end)

    # Salva l'SRT finale
    subs.save(output_file, encoding='utf-8')

    print(f"SRT file saved as {output_file}")
    return True

if is_batch:
    print("Batch folder found, batch processing...")
    # Trova tutte le cartelle numerate in Batch
    episode_dirs = sorted([d for d in os.listdir(batch_dir) if os.path.isdir(os.path.join(batch_dir, d)) and d.isdigit()])
    
    for episode_dir in episode_dirs:
        episode_path = os.path.join(batch_dir, episode_dir)
        
        audio_file = os.path.join(episode_path, "vocali.wav")
        srt_file = os.path.join(episode_path, f"whisper{episode_dir}.srt")
        output_file = os.path.join(episode_path, f'whisper{episode_dir}_adjusted.srt')
        
        print(f"\nProcessing {episode_dir}:")
        process_srt_adjustment(audio_file, srt_file, output_file)
        
else:
    # COMPORTAMENTO PER SINGOLO FILE
    # File di input
    audio_file = os.path.join(project_dir, "vocali.wav")
    srt_file = os.path.join(project_dir, "whisper.srt")
    output_file = os.path.join(project_dir, 'whisper_adjusted.srt')
    
    print("Single processing:")
    process_srt_adjustment(audio_file, srt_file, output_file)