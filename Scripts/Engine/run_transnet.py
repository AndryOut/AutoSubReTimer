# Rilevamento cambi scena con TransNetV2, avviato da Fase3 con engine\python.exe.
# Uso: engine\python.exe Scripts\Engine\run_transnet.py <video> <srt> <cartella output>
# Scrive scene_timestamps.srt e scene_timestamps_adjusted.srt nella cartella di output,
# come la Fase3 con PySceneDetect. Usa la GPU se il motore e' CUDA, altrimenti la CPU.
import os
import sys
import math
import re
import subprocess
import warnings
import cv2
import torch
import numpy as np
import pysrt
import ffmpeg
from concurrent.futures import ThreadPoolExecutor, as_completed
from transnetv2_pytorch import TransNetV2

_PTS_RE = re.compile(r'pts_time:([0-9.]+)')

warnings.filterwarnings("ignore", message=".*Deterministic behavior was enabled.*")
warnings.filterwarnings("ignore", message=".*not writable.*")

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Aggiunge ffmpeg del progetto al PATH
ffmpeg_bin = os.path.join(project_path, "ffmpeg", "bin")
if not os.path.isfile(os.path.join(ffmpeg_bin, "ffmpeg.exe")):
    raise FileNotFoundError(
        f"ffmpeg.exe non trovato in '{ffmpeg_bin}'. "
        "Controlla che la cartella 'ffmpeg/bin' esista nel progetto."
    )
os.environ['PATH'] = ffmpeg_bin + os.pathsep + os.environ.get('PATH', '')

# Input size di TransNetV2
INPUT_H, INPUT_W = 27, 48
SCENE_THRESHOLD = 0.4

def cpu_has_avx():
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(39))  # PF_AVX_INSTRUCTIONS_AVAILABLE
    except (AttributeError, OSError):
        return True


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
            total_milliseconds = round((frame * 1000 * 1001) / 60000)
        else:
            total_milliseconds = round(frame * 1000 / fps)

        hrs = total_milliseconds // 3600000
        mins = (total_milliseconds % 3600000) // 60000
        secs = (total_milliseconds % 60000) // 1000
        millis = total_milliseconds % 1000

        return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

    with open(output_path, 'w') as f:
        for i, (start_frame, end_frame) in enumerate(scene_list):
            start_timecode = frame_to_timecode(start_frame, fps)
            if i < len(scene_list) - 1:
                next_start_frame = scene_list[i + 1][0]
                end_timecode = frame_to_timecode(next_start_frame, fps)
            else:
                end_timecode = frame_to_timecode(end_frame - 1, fps)

            f.write(f"{i+1}\n")
            f.write(f"{start_timecode} --> {end_timecode}\n")
            f.write(f"Scene {i+1}\n\n")


def get_video_framerate(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps


def apply_global_offset_to_srt(input_path, output_path, offset):
    subs = pysrt.open(input_path, encoding='utf-8')
    for sub in subs:
        sub.start.ordinal += int(offset * 1000)
        sub.end.ordinal += int(offset * 1000)
    subs.save(output_path, encoding='utf-8')


def get_segments_to_analyze(srt_path, min_gap=5.0, margin=1.0):
    subs = pysrt.open(srt_path, encoding='utf-8')
    segments = []

    if not subs:
        return segments

    first_start = max(0, subs[0].start.ordinal / 1000 - margin * 2)
    last_end = subs[0].end.ordinal / 1000
    current_start = first_start

    for i in range(1, len(subs)):
        current_sub = subs[i]
        gap = (current_sub.start.ordinal / 1000) - (subs[i-1].end.ordinal / 1000)

        if gap >= min_gap:
            segments.append((current_start, subs[i-1].end.ordinal / 1000 + margin))
            current_start = current_sub.start.ordinal / 1000 - margin

        last_end = current_sub.end.ordinal / 1000

    segments.append((current_start, last_end + margin))
    return segments

def get_first_frame_pts(video_path, start_sec):
    ffmpeg_exe = os.path.join(ffmpeg_bin, "ffmpeg.exe")
    cmd = [
        ffmpeg_exe,
        "-hide_banner",
        "-nostats",
        "-ss", str(start_sec),
        "-i", video_path,
        "-copyts",
        "-vf", "showinfo",
        "-loglevel", "info",
        "-frames:v", "1",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True)
    stderr_text = result.stderr.decode(errors="replace")
    m = _PTS_RE.search(stderr_text)
    if m:
        return float(m.group(1))
    return None

def extract_frames_from_segment(video_path, start_sec, end_sec, fps):
    duration = end_sec - start_sec
    if duration <= 0:
        return np.empty((0, INPUT_H, INPUT_W, 3), dtype=np.uint8), round(start_sec * fps)

    def _extract():
        raw = ffmpeg.input(video_path, ss=start_sec, t=duration)\
            .output('pipe:', format='rawvideo', pix_fmt='rgb24',
                    s=f'{INPUT_W}x{INPUT_H}', vsync='0', threads=1)\
            .run(capture_stdout=True, capture_stderr=True)[0]
        n = len(raw) // (INPUT_H * INPUT_W * 3)
        return np.frombuffer(raw, np.uint8).reshape([n, INPUT_H, INPUT_W, 3])

    def _pts():
        return get_first_frame_pts(video_path, start_sec)

    with ThreadPoolExecutor(max_workers=2) as tp:
        f_frames = tp.submit(_extract)
        f_pts = tp.submit(_pts)
        frames = f_frames.result()
        pts_val = f_pts.result()

    if pts_val is not None:
        start_frame = round(pts_val * fps)
    else:
        start_frame = round(start_sec * fps)

    return frames, start_frame


def extract_segment_worker(args):
    idx, video_path, start_sec, end_sec, fps = args
    for attempt in (1, 2):
        try:
            frames, start_frame = extract_frames_from_segment(video_path, start_sec, end_sec, fps)
            return idx, frames, start_frame
        except Exception as e:
            detail = ""
            if isinstance(e, ffmpeg.Error) and e.stderr:
                detail = " - " + e.stderr.decode(errors="replace").strip().splitlines()[-1]
            print(f"Errore estrazione segmento {idx}: {e}{detail}")
            if attempt == 1:
                print(f"Nuovo tentativo sul segmento {idx}...", flush=True)
    return idx, np.empty((0, INPUT_H, INPUT_W, 3), dtype=np.uint8), 0


def process_segment_frames(model, frames, start_frame, fps):
    n_frames = frames.shape[0]
    if n_frames == 0:
        return []

    VALID = 300    # frame tenuti per blocco
    MARGIN = 100   # NON scendere sotto ~98
    BATCH = 1      # blocchi per forward (VRAM in volo = BATCH * (VALID + 2*MARGIN) frame)

    frames = frames.copy()
    single_pred_np = np.empty(n_frames, dtype=np.float32)

    # elenco blocchi: (lo, hi, pos, end)
    jobs = []
    pos = 0
    while pos < n_frames:
        end = min(n_frames, pos + VALID)
        jobs.append((max(0, pos - MARGIN), min(n_frames, end + MARGIN), pos, end))
        pos = end

    # raggruppa per lunghezza identica
    groups = {}
    for j in jobs:
        groups.setdefault(j[1] - j[0], []).append(j)

    for group in groups.values():
        for i in range(0, len(group), BATCH):
            part = group[i:i + BATCH]
            batch = torch.from_numpy(np.stack([frames[lo:hi] for lo, hi, _, _ in part])).to(model.device)
            with torch.no_grad():
                pred, _ = model.predict_raw(batch)              # [B, T, 1]
            pred = pred.squeeze(-1).cpu().numpy()               # [B, T]
            for b, (lo, hi, pos, end) in enumerate(part):
                single_pred_np[pos:end] = pred[b, pos - lo: pos - lo + (end - pos)]

    scenes = model.predictions_to_scenes(single_pred_np, threshold=SCENE_THRESHOLD)
    return [(int(s) + start_frame, int(e) + start_frame) for s, e in scenes]

def run(video_path, srt_path, output_dir):
    print(f"Trovato video: {os.path.basename(video_path)}")

    if not os.path.exists(srt_path):
        raise FileNotFoundError("Il file SRT dei sottotitoli non è stato trovato.")

    fps = get_video_framerate(video_path)
    print(f"Rilevato frame rate video: {fps:.3f} fps")

    segments = get_segments_to_analyze(srt_path, min_gap=5.0, margin=1.0)
    print(f"Segmenti da analizzare: {len(segments)}")

    # ============================================
    # FASE 1: estrazione parallela dei frame (CPU)
    # ============================================
    print("Estrazione frame in parallelo...")
    extract_args = [(i, video_path, s, e, fps) for i, (s, e) in enumerate(segments)]

    num_workers = min(os.cpu_count() or 1, len(segments)) if segments else 1
    extracted = [None] * len(segments)

    last_pct = -1
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(extract_segment_worker, arg) for arg in extract_args]
        for i, future in enumerate(as_completed(futures), 1):
            idx, frames, start_frame = future.result()
            extracted[idx] = (frames, start_frame)
            pct = int((i / len(segments)) * 50)  # estrazione = 0-50%
            if pct != last_pct:
                print(f"Estrazione: {pct}%", flush=True)
                last_pct = pct

    # ============================================
    # FASE 2: inferenza sequenziale (GPU)
    # ============================================
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cpu' and not cpu_has_avx():
        # Su CPU senza AVX oneDNN di torch va in crash (come per Demucs in run_demucs.py)
        torch.backends.mkldnn.enabled = False
    print(f"Uso device: {device}")
    model = TransNetV2(device=device)
    model.eval()

    all_scenes = []
    for i, (frames, start_frame) in enumerate(extracted, 1):
        pct = 50 + int((i / len(extracted)) * 50)  # analisi = 50-100%
        n = frames.shape[0]
        print(f"Analisi: {pct}% ({n} frame, start_frame={start_frame})", flush=True)
        segment_scenes = process_segment_frames(model, frames, start_frame, fps)
        all_scenes.extend(segment_scenes)

    all_scenes.sort(key=lambda x: x[0])
    print(f"Scene rilevate: {len(all_scenes)}")

    srt_output_path = os.path.join(output_dir, "scene_timestamps.srt")
    export_srt(all_scenes, output_path=srt_output_path, fps=fps)

    if abs(fps - 23.976) < 0.001:
        offset = -0.020000
    elif abs(fps - 24.0) < 0.001:
        offset = 0.0
    else:
        offset = 0.0

    adjusted_srt_output_path = os.path.join(output_dir, "scene_timestamps_adjusted.srt")
    apply_global_offset_to_srt(srt_output_path, adjusted_srt_output_path, offset)

    print(f"File SRT creato: scene_timestamps.srt")
    print(f"File SRT con offset globale applicato: scene_timestamps_adjusted.srt")
    print(f"Offset applicato: {offset:.3f} secondi")


def main():
    if len(sys.argv) != 4:
        print("Uso: run_transnet.py <video> <srt> <cartella output>")
        return 2
    run(sys.argv[1], sys.argv[2], sys.argv[3])
    return 0


if __name__ == '__main__':
    sys.exit(main())