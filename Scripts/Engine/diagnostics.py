import ctypes
import hashlib
import json
import locale
import os
import platform
import shutil
import subprocess
import sys
import time

# Diagnostica per la modalita' debug (Help -> Debug run). I test di girano in processi separati

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

CPU_FEATURES = {13: "SSE3", 36: "SSSE3", 37: "SSE4.1", 38: "SSE4.2", 39: "AVX", 40: "AVX2", 41: "AVX512F"}


def desktop_path():
    if sys.platform == "win32":
        try:
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            folderid_desktop = GUID(0xB4BFCC3A, 0xDB2C, 0x424C,
                                    (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folderid_desktop), 0, None,
                                                          ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    path = os.path.join(os.path.expanduser("~"), "Desktop")
    return path if os.path.isdir(path) else os.path.expanduser("~")


def _run(cmd, timeout=30, env=None):
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                           env=env, creationflags=NO_WINDOW)
        return r.returncode, r.stdout.decode("utf-8", errors="replace").strip()
    except subprocess.TimeoutExpired:
        return None, f"TIMEOUT after {timeout} s"
    except Exception as e:
        return None, f"cannot run: {e}"


def _powershell(command, timeout=30):
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + command], timeout)[1]


def _reg(path, name):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except Exception:
        return None


def cpu_features():
    try:
        k = ctypes.windll.kernel32
        return {n: bool(k.IsProcessorFeaturePresent(i)) for i, n in CPU_FEATURES.items()}
    except Exception:
        return {}


def _memory_mb():
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullTotalPhys // 2**20, m.ullAvailPhys // 2**20
    except Exception:
        return None, None


def _size_mb(path):
    total = 0
    for base, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    return total / 2**20


def _mtime(path):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))


def system_report(root=PROJECT_ROOT):
    out = []
    add = out.append

    add("=== SYSTEM ===")
    cv = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    add(f"Windows: {_reg(cv, 'ProductName')} {_reg(cv, 'DisplayVersion') or ''} "
        f"build {_reg(cv, 'CurrentBuild')}.{_reg(cv, 'UBR')} ({platform.machine()})")
    cpu = _reg(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString") or platform.processor()
    add(f"CPU: {cpu.strip()}  ({os.cpu_count()} threads)")
    feats = cpu_features()
    add("CPU features: " + (", ".join(f"{n}={'yes' if v else 'NO'}" for n, v in feats.items()) or "unknown"))
    total, free = _memory_mb()
    add(f"RAM: {total} MB total, {free} MB free")
    add("GPU:")
    for line in _powershell("Get-CimInstance Win32_VideoController | ForEach-Object "
                            "{ $_.Name + ' | driver ' + $_.DriverVersion + ' | ' + $_.DriverDate }").splitlines():
        add(f"  {line}")
    if shutil.which("nvidia-smi"):
        add("nvidia-smi: " + _run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used",
                                   "--format=csv,noheader"])[1])
    else:
        add("nvidia-smi: not found")
    add("Antivirus: " + (_powershell("(Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct)"
                                     ".displayName -join ', '") or "unknown"))
    try:
        acp = ctypes.windll.kernel32.GetACP()
        oem = ctypes.windll.kernel32.GetOEMCP()
    except Exception:
        acp = oem = "?"
    add(f"Encoding: ANSI cp{acp}, OEM cp{oem}, preferred {locale.getpreferredencoding(False)}, "
        f"filesystem {sys.getfilesystemencoding()}" + ("  (Windows UTF-8 beta ON)" if acp == 65001 else ""))
    add(f"Language: {locale.getlocale()}")

    add("")
    add("=== FOLDER ===")
    add(f"Path: {root}")
    add(f"Path length: {len(root)}, non-ASCII: {'YES' if any(ord(c) > 127 for c in root) else 'no'}, "
        f"OneDrive: {'YES' if 'onedrive' in root.lower() else 'no'}")
    try:
        du = shutil.disk_usage(root)
        add(f"Disk: {du.free // 2**30} GB free of {du.total // 2**30} GB")
    except OSError as e:
        add(f"Disk: {e}")
    try:
        probe = os.path.join(root, "_debug_write_test.tmp")
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        add("Write permission: ok")
    except OSError as e:
        add(f"Write permission: NO ({e})")
    try:
        entries = sorted(os.listdir(root))
    except OSError as e:
        entries = []
        add(f"Cannot list folder: {e}")
    for name in entries:
        p = os.path.join(root, name)
        if os.path.isdir(p):
            add(f"  [dir]  {name}")
        else:
            add(f"  {os.path.getsize(p) / 2**20:10.1f} MB  {_mtime(p)}  {name}")

    add("")
    add("=== PROGRAM ===")
    exe = os.path.join(root, "AutoSubReTimer.exe")
    add(f"AutoSubReTimer.exe: " + (f"{os.path.getsize(exe) / 2**20:.1f} MB, {_mtime(exe)}" if os.path.isfile(exe) else "MISSING"))
    for d in ("app", "engine", "ffmpeg", "Scripts", "Faster-Whisper-XXL"):
        p = os.path.join(root, d)
        add(f"{d}\\: " + (f"{_size_mb(p):.0f} MB" if os.path.isdir(p) else "missing"))
    try:
        with open(os.path.join(root, "engine", "engine.json"), "r", encoding="utf-8") as f:
            add(f"engine.json: {json.dumps(json.load(f))}")
    except Exception as e:
        add(f"engine.json: {e}")
    for d in ("engine.new", "engine.old"):
        if os.path.isdir(os.path.join(root, d)):
            add(f"WARNING: leftover folder {d}\\")
    try:
        with open(os.path.join(root, "Scripts", "Engine", "engine_spec.json"), "r", encoding="utf-8") as f:
            add(f"engine_spec version: {json.load(f).get('engine_version')}")
    except Exception as e:
        add(f"engine_spec.json: {e}")
    ffmpeg = os.path.join(root, "ffmpeg", "bin", "ffmpeg.exe")
    ffprobe = os.path.join(root, "ffmpeg", "bin", "ffprobe.exe")
    add("ffmpeg: " + (_run([ffmpeg, "-version"])[1].splitlines()[0] if os.path.isfile(ffmpeg) else "MISSING"))
    add("ffprobe: " + ("ok" if os.path.isfile(ffprobe) else "MISSING"))
    interesting = [k for k in sorted(os.environ) if k.upper().startswith(("PYTHON", "CUDA", "TORCH", "HF_", "OMP", "MKL", "KMP"))]
    add("Environment: " + (", ".join(f"{k}={os.environ[k]}" for k in interesting) or "nothing relevant"))

    add("")
    add("=== VIDEO ===")
    mkvs = [f for f in entries if f.lower().endswith(".mkv")]
    if not mkvs:
        add("No .mkv in the folder")
    for mkv in mkvs:
        add(f"{mkv}:")
        if os.path.isfile(ffprobe):
            code, text = _run([ffprobe, "-v", "error", "-show_entries",
                               "stream=index,codec_type,codec_name,channels,sample_rate,width,height,r_frame_rate:"
                               "format=duration,size", "-of", "compact", os.path.join(root, mkv)], timeout=60)
            for line in text.splitlines():
                add(f"  {line}")
            if code not in (0, None):
                add(f"  ffprobe exit code {code}")
    return out


def scripts_report(root=PROJECT_ROOT):
    out = ["=== SCRIPTS (.py) ==="]
    base = os.path.join(root, "Scripts")
    for d, dirs, files in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        for f in sorted(files):
            if not f.endswith((".py", ".json")):
                continue
            p = os.path.join(d, f)
            try:
                with open(p, "rb") as fh:
                    digest = hashlib.sha1(fh.read()).hexdigest()[:10]
                out.append(f"  {_mtime(p)}  {os.path.getsize(p):7d}  {digest}  {os.path.relpath(p, base)}")
            except OSError as e:
                out.append(f"  {os.path.relpath(p, base)}: {e}")
    return out


def config_report(root=PROJECT_ROOT):
    out = ["=== CONFIG ==="]
    base = os.path.join(root, "Scripts")
    for d, dirs, files in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        for f in sorted(files):
            if f.lower().endswith(".json") and "config" in f.lower():
                p = os.path.join(d, f)
                try:
                    with open(p, "r", encoding="utf-8-sig") as fh:
                        text = json.dumps(json.load(fh), ensure_ascii=False)
                except Exception as e:
                    text = f"unreadable: {e}"
                out.append(f"  {os.path.relpath(p, base)}: {text}")
    return out


ENGINE_TESTS = [
    ("versions", 120,
     "import sys, platform; print('python', sys.version.split()[0]);\n"
     "import numpy; print('numpy', numpy.__version__)\n"
     "import torch; print('torch', torch.__version__, '| cuda build', torch.version.cuda, '| cuda available', torch.cuda.is_available())\n"
     "print('threads', torch.get_num_threads(), '| mkldnn', torch.backends.mkldnn.is_available())\n"
     "import demucs; print('demucs', getattr(demucs, '__version__', '?'))\n"),
    ("matmul", 120, "import torch; torch.randn(64, 64) @ torch.randn(64, 64)"),
    ("fft", 120, "import torch; torch.fft.rfft(torch.randn(1, 2, 44100))"),
    ("conv1d", 120, "import torch; torch.nn.functional.conv1d(torch.randn(1, 2, 44100), torch.randn(4, 2, 8))"),
    ("conv1d without oneDNN", 120,
     "import torch; torch.backends.mkldnn.enabled = False\n"
     "torch.nn.functional.conv1d(torch.randn(1, 2, 44100), torch.randn(4, 2, 8))"),
    ("GPU probe", 180, None),
    ("Demucs model on 5 s of noise (CPU, like run_demucs)", 900,
     "import ctypes, torch\n"
     "if not ctypes.windll.kernel32.IsProcessorFeaturePresent(39): torch.backends.mkldnn.enabled = False\n"
     "from demucs.pretrained import get_model\n"
     "from demucs.apply import apply_model\n"
     "m = get_model('htdemucs'); m.eval()\n"
     "with torch.no_grad(): apply_model(m, torch.randn(1, 2, 44100 * 5) * 0.1, device='cpu', progress=False)\n"),
]


def engine_tests(root=PROJECT_ROOT, emit=print):
    emit("=== ENGINE TESTS ===")
    py = os.path.join(root, "engine", "python.exe")
    if not os.path.isfile(py):
        emit(f"engine\\python.exe missing: {py}")
        return
    models = os.path.join(root, "engine", "models")
    env = os.environ.copy()
    env.update({"TORCH_HOME": models, "HF_HOME": os.path.join(models, "hf"),
                "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONFAULTHANDLER": "1", "PYTHONIOENCODING": "utf-8"})
    if os.path.isdir(os.path.join(models, "hf", "hub", "models--adefossez--HTDemucs")):
        env["HF_HUB_OFFLINE"] = "1"
    try:
        with open(os.path.join(root, "engine", "engine.json"), "r", encoding="utf-8") as f:
            backend = json.load(f).get("backend", "cpu")
    except Exception:
        backend = "cpu"
    for name, timeout, code in ENGINE_TESTS:
        if code is None and backend == "cpu":
            emit(f"{name}: skipped (CPU engine)")
            continue
        cmd =[py, os.path.join(root, "Scripts", "Engine", "gpu_probe.py")] if code is None else [py, "-X", "faulthandler", "-c", code]
        t0 = time.time()
        rc, text = _run(cmd, timeout=timeout, env=env)
        dt = time.time() - t0
        if rc == 0:
            result = "OK"
        elif rc is None:
            result = "FAILED"
        else:
            result = f"FAILED (exit code {rc}, 0x{rc & 0xFFFFFFFF:08X})"
        emit(f"{name}: {result}  [{dt:.1f} s]")
        lines = [l for l in text.splitlines() if l.strip()]
        if rc != 0 or name in ("versions", "GPU probe"):
            for l in lines[-15:]:
                emit(f"    {l}")


def full_report(root=PROJECT_ROOT, emit=print):
    for line in system_report(root):
        emit(line)
    emit("")
    engine_tests(root, emit)
    emit("")
    for line in config_report(root) + [""] + scripts_report(root):
        emit(line)


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    path = os.path.join(desktop_path(), time.strftime("AutoSubReTimer_diagnostics_%Y-%m-%d_%H-%M-%S.txt"))
    print("Collecting diagnostics (it can take a few minutes)...", flush=True)
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        def emit(line):
            f.write(line + "\n")
            f.flush()
            print(line, flush=True)
        emit(f"Auto Sub ReTimer diagnostics - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        emit("")
        full_report(PROJECT_ROOT, emit)
    print(f"\nSaved: {path}", flush=True)


if __name__ == "__main__":
    main()
