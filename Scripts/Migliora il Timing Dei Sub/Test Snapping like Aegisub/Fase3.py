import os
import math
from scenedetect import open_video, SceneManager
from scenedetect.detectors import AdaptiveDetector
import pysrt
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from concurrent.futures import as_completed

# Percorso della directory principale del progetto
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Funzione per esportare i risultati in formato SRT con precisione al millisecondo
def export_srt(scene_list, output_path, fps):
    def frame_to_timecode(frame, fps):
        if math.isclose(fps, 24000/1001, rel_tol=1e-5):    
            total_milliseconds = round((frame * 1000 * 1001) / 24000)
        elif math.isclose(fps, 23.810, rel_tol=1e-5):       
            total_milliseconds = round(frame * 1000 / 23.810)
        elif math.isclose(fps, 24.0, rel_tol=1e-5):         
            total_milliseconds = round(frame * 1000 / 24)
        elif math.isclose(fps, 24.794, rel_tol=1e-5):      
            total_milliseconds = round(frame * 1000 / 24.794)
        elif math.isclose(fps, 25000/1001, rel_tol=1e-5):   
            total_milliseconds = round((frame * 1000 * 1001) / 25000)
        elif math.isclose(fps, 25.0, rel_tol=1e-5):         
            total_milliseconds = round(frame * 1000 / 25)
        elif math.isclose(fps, 30000/1001, rel_tol=1e-5):   
            total_milliseconds = round((frame * 1000 * 1001) / 30000)
        elif math.isclose(fps, 30.0, rel_tol=1e-5):         
            total_milliseconds = round(frame * 1000 / 30)
        elif math.isclose(fps, 15.0, rel_tol=1e-5):         
            total_milliseconds = round(frame * 1000 / 15.0)
        elif math.isclose(fps, 60000/1001, rel_tol=1e-5): 
            true_fps = 24000/1001  
            total_milliseconds = round(frame * 1000 / true_fps)
        else:
            total_milliseconds = round(frame * 1000 / fps)
        
        hrs = total_milliseconds // 3600000
        mins = (total_milliseconds % 3600000) // 60000
        secs = (total_milliseconds % 60000) // 1000
        millis = total_milliseconds % 1000
        
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

# Funzione per applicare un offset globale al file SRT
def apply_global_offset_to_srt(input_path, output_path, offset):
    def apply_offset(timecode, offset):
        timecode.ordinal += int(offset * 1000)
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
    # MKV
    mkv_files = [f for f in os.listdir(project_path) if f.endswith('.mkv')]
    if not mkv_files:
        raise FileNotFoundError("Nessun file .mkv trovato nella directory.")
    video_path = os.path.join(project_path, mkv_files[0])
    print(f"Trovato video: {mkv_files[0]}")

    # Percorso del file SRT dei sottotitoli
    srt_path = os.path.join(project_path, "adjusted_Sub.srt")
    if not os.path.exists(srt_path):
        raise FileNotFoundError("Il file SRT dei sottotitoli non è stato trovato.")
    
    # Ottiene il frame rate del video
    fps = get_video_framerate(video_path)
    print(f"Rilevato frame rate video: {fps:.3f} fps")

    with open(os.path.join(project_path, "fps.txt"), "w") as f:
        f.write(str(fps))
   
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
    export_srt(all_scenes, output_path=srt_output_path, fps=fps)

    # 2. Applica offset SPECIFICI:
    if abs(fps - 23.976) < 0.001:    # Per 23.976fps
        offset = -0.020000
    elif abs(fps - 24.0) < 0.001:    # Per 24.000fps
        offset = 0.0
    else:                            # Per altri FPS
        offset = 0.0

    # 3. Applica l'offset
    adjusted_srt_output_path = os.path.join(project_path, "scene_timestamps_adjusted.srt")
    apply_global_offset_to_srt(srt_output_path, adjusted_srt_output_path, offset)

    # Stampa risultati
    print(f"Scene rilevate: {len(all_scenes)}")
    for i, scene in enumerate(all_scenes):
        print(f"Scena {i+1}: Inizio: {scene[0].get_timecode()}, Fine: {scene[1].get_timecode()}")
    print(f"File SRT con offset globale applicato creato con successo: scene_timestamps_adjusted.srt")
    print(f"Offset applicato: {offset:.3f} secondi")
    print(f"Segmenti analizzati: {segments}")

if __name__ == '__main__':
    main()