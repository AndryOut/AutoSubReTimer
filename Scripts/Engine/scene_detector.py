# Scelta del rilevatore di scene per Fase3 (AS, CR, Whisper ReTimer).
# Legge Config_Fase3.json nella cartella degli script della modalita':
# "pyscenedetect" (default, anche se il file manca) oppure "transnetv2".
# TransNetV2 richiede torch, che c'e' solo nel motore: lo si lancia con engine\python.exe
# su run_transnet.py e se ne ristampa l'output riga per riga (avanzamento nella GUI).
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ENGINE_PYTHON = os.path.join(PROJECT_ROOT, "engine", "python.exe")
TRANSNET_RUNNER = os.path.join(HERE, "run_transnet.py")

CONFIG_NAME = "Config_Phase3.json"
DETECTORS = ("pyscenedetect", "transnetv2")


def scene_detector(config_dir):
    try:
        with open(os.path.join(config_dir, CONFIG_NAME), "r", encoding="utf-8") as f:
            value = json.load(f).get("scene_detector", "pyscenedetect")
    except (OSError, ValueError, AttributeError):
        value = "pyscenedetect"
    return value if value in DETECTORS else "pyscenedetect"


FFPROBE = os.path.join(PROJECT_ROOT, "ffmpeg", "bin", "ffprobe.exe")
VFR_MIN_FRAMES = 24      # almeno ~1 s di frame con un'altra durata
VFR_TOLERANCE = 0.10     # scarto ammesso rispetto a un multiplo della durata normale di un frame


def video_is_vfr(video_path):
    try:
        r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "packet=pts_time", "-of", "csv=p=0", video_path],
                           capture_output=True, text=True, timeout=600)
        pts = sorted(float(x) for x in r.stdout.split() if x.strip() not in ("", "N/A"))
    except Exception as e:
        print(f"VFR check skipped ({e}): constant frame rate assumed", flush=True)
        return False
    if len(pts) < 100:
        return False

    step = (pts[-1] - pts[0]) / (len(pts) - 1)          # durata media di un frame
    tol = max(0.002, VFR_TOLERANCE * step)               # almeno 2 ms (arrotondamento al ms dell'mkv)
    off = 0
    for a, b in zip(pts, pts[1:]):
        d = b - a
        if d <= tol:
            continue
        k = round(d / step)
        if k < 1 or abs(d - k * step) > tol:             # non e' 1 frame ne' un salto di frame interi
            off += 1
    return off >= VFR_MIN_FRAMES


def run_transnet(video_path, srt_path, output_dir):
    if not os.path.isfile(ENGINE_PYTHON):
        raise RuntimeError("TransNetV2 error: engine not found (engine\\python.exe). "
                           "Use PySceneDetect in the Phase3 configuration.")
    print("Scene detector: TransNetV2", flush=True)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = os.path.dirname(TRANSNET_RUNNER)
    process = subprocess.Popen(
        [ENGINE_PYTHON, "-m", "run_transnet", video_path, srt_path, output_dir],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env,
    )
    for line in process.stdout:
        print(line, end="", flush=True)
    rc = process.wait()
    if rc != 0:
        raise RuntimeError(f"TransNetV2 error: run_transnet.py ended with code {rc}. "
                           "Update the engine or use PySceneDetect in the Phase3 configuration.")
