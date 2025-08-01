import os
from scenedetect import open_video, SceneManager
from scenedetect.detectors import AdaptiveDetector
import pysrt
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from concurrent.futures import as_completed

# Percorso della directory principale del progetto
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Funzione per esportare i risultati in formato SRT con precisione al millisecondo
def export_srt(scene_list, output_path='scene_timestamps.srt', fps=23.976):
    def frame_to_timecode(frame, fps):
        total_seconds = frame / fps
        hrs = int(total_seconds // 3600)
        mins = int((total_seconds % 3600) // 60)
        secs = int(total_seconds % 60)
        millis = int((total_seconds % 1) * 1000)
        return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

    with open(output_path, 'w') as f:
        for i, scene in enumerate(scene_list):
            start_frame = scene[0].get_frames()
            end_frame = scene[1].get_frames()
            start_timecode = frame_to_timecode(start_frame, fps)
            if i < len(scene_list) - 1:
                next_start_frame = scene_list[i+1][0].get_frames()
                end_timecode = frame_to_timecode(next_start_frame, fps)
            else:
                end_timecode = frame_to_timecode(end_frame - 1, fps)
            
            f.write(f"{i+1}\n")
            f.write(f"{start_timecode} --> {end_timecode}\n")
            f.write(f"Scene {i+1}\n\n")

def get_video_framerate(video_path):
    video = open_video(video_path)
    fps = video.frame_rate
    return fps

# Conversione fps sub
def convert_framerate_like_subtitleedit(input_path, output_path, from_fps=23.976, to_fps=24.0):
    subs = pysrt.open(input_path)
    
    if abs(from_fps - to_fps) < 0.001:
        subs.save(output_path)
        return
    
    ratio = from_fps / to_fps
    for sub in subs:
        sub.start.ordinal = int(round(sub.start.ordinal * ratio))
        sub.end.ordinal = int(round(sub.end.ordinal * ratio))
    subs.save(output_path)

# Funzione per calcolare la discrepanza costante
def calculate_discrepancy(scene_list, srt_path):
    subs = pysrt.open(srt_path, encoding='utf-8')
    discrepancies = []
    count = min(len(scene_list), len(subs))
    for i in range(count):
        scene_start = scene_list[i][0].get_seconds()
        subtitle_start = subs[i].start.ordinal / 1000
        discrepancy = scene_start - subtitle_start
        discrepancies.append(discrepancy)
    return sum(discrepancies) / len(discrepancies)

# Funzione per trovare l'offset più vicino ai valori predefiniti
def find_closest_offset(discrepancy, possible_offsets):
    return min(possible_offsets, key=lambda x: abs(x - discrepancy))

# Funzione per applicare un offset globale al file SRT
def apply_global_offset_to_srt(input_path, output_path, offset):
    def apply_offset(timecode, offset):
        timecode.ordinal += int(offset * 1000)  # Converte i secondi in millisecondi
        return timecode

    subs = pysrt.open(input_path, encoding='utf-8')
    for sub in subs:
        sub.start = apply_offset(sub.start, offset)
        sub.end = apply_offset(sub.end, offset)
    subs.save(output_path, encoding='utf-8')

# Funzione per trovare i segmenti del video da analizzare basati sui sottotitoli
def get_segments_to_analyze(srt_path, min_gap=5.0, margin=2.0):
    subs = pysrt.open(srt_path, encoding='utf-8')
    segments = []
    
    if not subs:
        return segments
    
    # Estende il primo inizio e l'ultima fine per catturare le scene ai bordi
    first_start = max(0, subs[0].start.ordinal / 1000 - margin * 2)  # Margine doppio all'inizio
    last_end = subs[-1].end.ordinal / 1000 + margin * 2  # Margine doppio alla fine
    
    current_start = first_start
    last_end = subs[0].end.ordinal / 1000
    
    for i in range(1, len(subs)):
        current_sub = subs[i]
        gap = (current_sub.start.ordinal / 1000) - (subs[i-1].end.ordinal / 1000)
        
        if gap >= min_gap:
            # Estende il segmento corrente con margine abbondante
            segments.append((current_start, subs[i-1].end.ordinal / 1000 + margin))
            # Inizia nuovo segmento con margine abbondante
            current_start = current_sub.start.ordinal / 1000 - margin
        
        last_end = current_sub.end.ordinal / 1000
    
    # Aggiunge l'ultimo segmento esteso
    segments.append((current_start, last_end + margin))
    
    return segments

# Funzione per processare un singolo segmento
def process_segment(args):
    segment, video_path, adaptive_threshold = args
    start_time, end_time = segment
    
    try:
        video = open_video(video_path)
        video.seek(max(0, start_time - 0.5))
        
        scene_manager = SceneManager()
        adaptive_detector = AdaptiveDetector(
            adaptive_threshold=adaptive_threshold,
            min_content_val=20
        )
        scene_manager.add_detector(adaptive_detector)
        
        scene_manager.detect_scenes(video, end_time=end_time + 0.5)
        
        segment_scenes = []
        for scene in scene_manager.get_scene_list():
            scene_start = scene[0].get_seconds()
            scene_end = scene[1].get_seconds()
            if scene_end > start_time and scene_start < end_time:
                segment_scenes.append(scene)
        
        return segment_scenes
    except Exception as e:
        print(f"Errore durante l'elaborazione del segmento {start_time}-{end_time}: {str(e)}")
        return []

def main():
    # Percorso del file video
    video_path = os.path.join(project_path, "ep.mkv")
    if not os.path.exists(video_path):
        raise FileNotFoundError("Il file video non è stato trovato.")

    # Percorso del file SRT dei sottotitoli
    srt_path = os.path.join(project_path, "adjusted_Sub.srt")
    if not os.path.exists(srt_path):
        raise FileNotFoundError("Il file SRT dei sottotitoli non è stato trovato.")
    
    # Ottiene il frame rate del video
    fps = get_video_framerate(video_path)
    print(f"Rilevato frame rate video: {fps:.3f} fps")

    # Ottiene i segmenti del video da analizzare
    segments = get_segments_to_analyze(srt_path, min_gap=5.0, margin=1.0)

    # Parametri per i detector
    adaptive_threshold = 3

    # Pool
    process_args = [(segment, video_path, adaptive_threshold) for segment in segments]

    # Rilevamento parallelo delle scene
    print("Analisi parallela delle scene in corso...")
    total_segments = len(segments)
    num_threads = min(cpu_count(), len(segments)) if segments else 1  
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_segment, arg) for arg in process_args]
        
        for i, _ in enumerate(as_completed(futures), 1):
            progress = int((i / total_segments) * 50)
            print("\rAnalisi scene: [{}{}] {:>3}%".format(
                '=' * progress,
                ' ' * (50 - progress),
                int((i / total_segments) * 100)), 
                end='', flush=True)
    
    print("\nAnalisi completata!")
    results = [future.result() for future in futures] 

    # Unisce i risultati
    all_scenes = []
    for segment_scenes in results:
        all_scenes.extend(segment_scenes)
    all_scenes.sort(key=lambda x: x[0].get_seconds())

    # Esporta i risultati
    srt_output_path = os.path.join(project_path, "scene_timestamps.srt")
    export_srt(all_scenes, output_path=srt_output_path)

    # 1. Converte SEMPRE all'FPS del video
    temp_converted_path = os.path.join(project_path, "temp_converted.srt")
    if abs(fps - 23.976) >= 0.001:  # Se FPS diverso da 23.976
        convert_framerate_like_subtitleedit(
            srt_output_path,
            temp_converted_path,
            from_fps=23.976,
            to_fps=fps
        )
        working_srt = temp_converted_path
    else:
        working_srt = srt_output_path

    # 2. Applica offset SPECIFICI:
    if abs(fps - 23.976) < 0.001:    # Per 23.976fps
        offset = -0.020854
    elif abs(fps - 24.0) < 0.001:    # Per 24.000fps, Non testato per ora
        offset = 0.0
    else:                            # Per altri FPS
        offset = 0.0

    # 3. Applica l'offset
    adjusted_srt_output_path = os.path.join(project_path, "scene_timestamps_adjusted.srt")
    apply_global_offset_to_srt(working_srt, adjusted_srt_output_path, offset)

    # 4. Pulisce il file temporaneo
    if os.path.exists(temp_converted_path):
        os.remove(temp_converted_path)

    # Stampa risultati
    print(f"Scene rilevate: {len(all_scenes)}")
    for i, scene in enumerate(all_scenes):
        print(f"Scena {i+1}: Inizio: {scene[0].get_timecode()}, Fine: {scene[1].get_timecode()}")
    print(f"File SRT con offset globale applicato creato con successo: scene_timestamps_adjusted.srt")
    print(f"Offset applicato: {offset:.3f} secondi")
    print(f"Segmenti analizzati: {segments}")

if __name__ == '__main__':
    main()