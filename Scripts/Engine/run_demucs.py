import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ENGINE_DIR = os.path.dirname(os.path.abspath(sys.executable))
MODELS_DIR = os.path.join(ENGINE_DIR, "models")


def engine_backend():
    try:
        with open(os.path.join(ENGINE_DIR, "engine.json"), "r", encoding="utf-8") as f:
            return json.load(f).get("backend", "cpu")
    except (OSError, ValueError):
        return "cpu"

def gpu_probe_cached(env):
    cache_file = os.path.join(HERE, "gpu_probe_cache.json")

    # Chiave cache: cambia quando engine.json cambia (rebuild, cambio backend)
    try:
        with open(os.path.join(ENGINE_DIR, "engine.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cache_key = f"{cfg.get('backend', 'cpu')}-{cfg.get('built', '')}-{cfg.get('engine_version', '')}"
    except (OSError, ValueError):
        cache_key = None

    # Cache hit
    if cache_key:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("key") == cache_key:
                debug_print(f"[debug] GPU probe cache hit: {cached.get('result')}")
                return cached.get("rc", 1), cached.get("result", "cached")
        except (OSError, ValueError):
            pass

    # Cache miss: esegue il probe
    probe_env = env.copy()
    existing_pp = probe_env.get("PYTHONPATH", "")
    probe_env["PYTHONPATH"] = HERE + (os.pathsep + existing_pp if existing_pp else "")

    probe = subprocess.run(
        [sys.executable, "-m", "gpu_probe"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=probe_env,
    )
    lines = (probe.stdout or "").strip().splitlines()
    result = lines[-1] if lines else f"GPU check failed (code {probe.returncode})"
    result = result.split(" ", 1)[1] if result.startswith(("OK ", "ERR ")) else result

    # Salva in cache
    if cache_key:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"key": cache_key, "rc": probe.returncode, "result": result}, f)
        except OSError:
            pass

    return probe.returncode, result

def demucs_env():
    env = os.environ.copy()
    env["TORCH_HOME"] = MODELS_DIR
    env["HF_HOME"] = os.path.join(MODELS_DIR, "hf")
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    # Modello gia' presente nel motore: niente controlli online a ogni avvio
    if os.path.isdir(os.path.join(MODELS_DIR, "hf", "hub", "models--adefossez--HTDemucs")):
        env["HF_HUB_OFFLINE"] = "1"
    ffmpeg_bin = os.path.join(PROJECT_ROOT, "ffmpeg", "bin")
    if ffmpeg_bin not in env.get("PATH", ""):
        env["PATH"] = env.get("PATH", "") + os.pathsep + ffmpeg_bin
    return env


def strip_device(args):
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in ("-d", "--device"):
            skip = True
            continue
        if a.startswith("--device="):
            continue
        out.append(a)
    return out


def cpu_has_avx():
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(39))  # PF_AVX_INSTRUCTIONS_AVAILABLE
    except (AttributeError, OSError):
        return True


# Su CPU senza AVX (es. AMD Phenom II) oneDNN di torch va in crash. Lo spegne prima di avviare Demucs.
NO_ONEDNN_LAUNCH = (
    "import torch; torch.backends.mkldnn.enabled = False; "
    "from demucs.separate import main; main()"
)


STREAM_PATCH = """
import demucs.api, demucs.audio

class _SkipSphn:
    @staticmethod
    def read(*args, **kwargs):
        raise RuntimeError("audio track chosen by Auto Sub ReTimer")

demucs.api.sphn = _SkipSphn
_read = demucs.audio.AudioFile.read

def _read_track(self, *args, streams=slice(None), **kwargs):
    if isinstance(streams, int) and streams == 0:
        streams = STREAM
    return _read(self, *args, streams=streams, **kwargs)

demucs.audio.AudioFile.read = _read_track
"""


def audio_stream():
    try:
        return max(0, int(os.environ.get("AUTOSUB_AUDIO_STREAM", "0")))
    except ValueError:
        return 0


def run(args, device, env):
    stream = audio_stream()
    patch = STREAM_PATCH.replace("STREAM", str(stream)) + "\n" if stream else ""
    if device == "cpu" and not cpu_has_avx():
        print("Old CPU without AVX: oneDNN disabled", flush=True)
        launch = ["-c", patch + NO_ONEDNN_LAUNCH]
    elif stream:
        launch = ["-c", patch + "from demucs.separate import main; main()"]
    else:
        launch = ["-m", "demucs"]
    cmd = [sys.executable, *launch, *args, "-d", device]
    debug_print(f"[debug] Demucs command: {cmd}")
    debug_print(f"[debug] TORCH_HOME={env.get('TORCH_HOME')} HF_HUB_OFFLINE={env.get('HF_HUB_OFFLINE')}")
    rc = subprocess.run(cmd, env=env).returncode
    debug_print(f"[debug] Demucs exit code {rc} (0x{rc & 0xFFFFFFFF:08X})")
    return rc


def debug_print(msg):
    # Solo durante un Debug run della GUI.
    if os.environ.get("AUTOSUB_DEBUG"):
        try:
            print(msg, flush=True)
        except UnicodeEncodeError:
            print(ascii(msg), flush=True)


def main():
    args = strip_device(sys.argv[1:])
    env = demucs_env()

    if engine_backend() != "cpu":
        rc, result = gpu_probe_cached(env)
        if rc == 0:
            print(f"Demucs on GPU: {result}", flush=True)
            if run(args, "cuda", env) == 0:
                return 0
            print("GPU error: Demucs failed on GPU, retrying on CPU", flush=True)
        else:
            print(f"GPU error: {result} - using CPU", flush=True)

    print("Demucs on CPU", flush=True)
    return run(args, "cpu", env)


if __name__ == "__main__":
    sys.exit(main())
