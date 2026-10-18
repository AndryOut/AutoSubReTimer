# Gestione della cartella engine\ (Python portabile + torch + demucs).
#
# Uso (dalla cartella del programma):
#   AutoSubReTimer.exe Scripts\Engine\engine_manager.py check    controllo all'avvio (lo fa l'exe da solo)
#   AutoSubReTimer.exe Scripts\Engine\engine_manager.py gpu      attiva la GPU NVIDIA
#   AutoSubReTimer.exe Scripts\Engine\engine_manager.py cpu      torna alla sola CPU
#   AutoSubReTimer.exe Scripts\Engine\engine_manager.py repair   reinstalla tutto il motore
#   AutoSubReTimer.exe Scripts\Engine\engine_manager.py status   mostra lo stato
# Opzione --pause: aspetta Invio prima di chiudere (usata dal menu Options della GUI).
# Il motore nuovo si prepara sempre in engine.new\ e prende il posto di engine\ solo
# se la prova finale passa: un aggiornamento fallito lascia il motore vecchio com'era.
# Solo libreria standard: gira dentro AutoSubReTimer.exe e con qualsiasi Python 3.10.
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC_PATH = os.path.join(HERE, "engine_spec.json")

RUNTIME_DLLS = [
    "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "msvcp140_atomic_wait.dll",
    "msvcp140_codecvt_ids.dll", "vcruntime140.dll", "vcruntime140_1.dll", "concrt140.dll",
]
MIN_MSVCP = (14, 40)


class Paths:
    def __init__(self, engine_dir):
        self.engine = os.path.abspath(engine_dir)
        self.new = self.engine + ".new"
        self.old = self.engine + ".old"

    @property
    def python(self):
        return os.path.join(self.engine, "python.exe")


def log(msg=""):
    print(msg, flush=True)


def load_spec():
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_state(engine_dir):
    try:
        with open(os.path.join(engine_dir, "engine.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_state(engine_dir, state):
    with open(os.path.join(engine_dir, "engine.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


# --------------------------------------------------
# GPU NVIDIA
# --------------------------------------------------
def nvidia_info():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    name, _, driver = r.stdout.strip().splitlines()[0].rpartition(",")
    try:
        major = int(driver.strip().split(".")[0])
    except ValueError:
        major = 0
    return name.strip(), major


def gpu_backend_for_driver(driver_major, spec):
    return "cu128" if driver_major >= spec.get("min_driver_cu128", 570) else "cu126"


# --------------------------------------------------
# DLL del runtime Visual C++
# --------------------------------------------------
def file_version(path):
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [(n, wintypes.DWORD) for n in (
            "dwSignature", "dwStrucVersion", "dwFileVersionMS", "dwFileVersionLS",
            "dwProductVersionMS", "dwProductVersionLS", "dwFileFlagsMask", "dwFileFlags",
            "dwFileOS", "dwFileType", "dwFileSubtype", "dwFileDateMS", "dwFileDateLS")]

    ver = ctypes.windll.version
    size = ver.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(path, 0, size, buf):
        return None
    ptr, length = ctypes.c_void_p(), wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)):
        return None
    info = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    ms, ls = info.dwFileVersionMS, info.dwFileVersionLS
    return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)


def update_runtime_dlls(target_dir):
    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    names = {n.lower() for n in RUNTIME_DLLS}
    for dirpath, _, files in os.walk(target_dir):
        for f in files:
            if f.lower() not in names:
                continue
            dst = os.path.join(dirpath, f)
            src = os.path.join(system32, f)
            if not os.path.isfile(src):
                continue
            v_src, v_dst = file_version(src), file_version(dst)
            if v_src and v_dst and v_src > v_dst:
                try:
                    shutil.copy2(src, dst)
                    rel = os.path.relpath(dst, target_dir)
                    log(f"  {rel}: {'.'.join(map(str, v_dst))} -> {'.'.join(map(str, v_src))}")
                except OSError as e:
                    log(f"  [Warn] cannot update {f}: {e}")


def old_msvcp_copies(target_dir):
    found = []
    for dirpath, _, files in os.walk(target_dir):
        for f in files:
            if f.lower() == "msvcp140.dll":
                v = file_version(os.path.join(dirpath, f))
                if v and v[:2] < MIN_MSVCP:
                    found.append((os.path.join(dirpath, f), v))
    return found


# --------------------------------------------------
# Costruzione del motore
# --------------------------------------------------
def copy_tree(src, dst):
    r = subprocess.run(
        ["robocopy", src, dst, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if r.returncode >= 8:
        raise OSError(f"robocopy failed (code {r.returncode})")


def remove_tree(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        if os.path.isdir(path):
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pip_install(python_exe, req_file, force=False, use_cache=False):
    cmd = [python_exe, "-m", "pip", "install", "--disable-pip-version-check",
           "--no-warn-script-location", "-r", req_file]
    if force:
        cmd.append("--force-reinstall")
    if not use_cache:
        cmd.append("--no-cache-dir")
    return subprocess.run(cmd).returncode == 0


def model_env(engine_dir):
    env = os.environ.copy()
    models = os.path.join(engine_dir, "models")
    env["TORCH_HOME"] = models
    env["HF_HOME"] = os.path.join(models, "hf")
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    return env


def ensure_model(engine_dir, model):
    code = f"from demucs.pretrained import get_model; get_model({model!r}); print('OK')"
    r = subprocess.run([os.path.join(engine_dir, "python.exe"), "-c", code],
                       env=model_env(engine_dir), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        log((r.stdout or "").strip()[-800:])
    return r.returncode == 0


def probe(engine_dir, backend):
    py = os.path.join(engine_dir, "python.exe")
    if backend == "cpu":
        code = "import torch, demucs, numpy; print('OK torch', torch.__version__)"
        r = subprocess.run([py, "-c", code], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
    else:
        r = subprocess.run([py, os.path.join(HERE, "gpu_probe.py")], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
    lines = (r.stdout or "").strip().splitlines()
    return r.returncode == 0, (lines[-1] if lines else f"exit code {r.returncode}")


def swap_in(paths):
    if os.path.isdir(paths.engine):
        try:
            os.rename(paths.engine, paths.old)
        except OSError as e:
            log(f"ERROR: cannot replace the engine folder ({e}).")
            log("Close Auto Sub ReTimer and any running Demucs, then try again.")
            return False
    try:
        os.rename(paths.new, paths.engine)
    except OSError as e:
        log(f"ERROR: cannot activate the new engine ({e}).")
        if os.path.isdir(paths.old) and not os.path.isdir(paths.engine):
            os.rename(paths.old, paths.engine)
        return False
    remove_tree(paths.old)
    return True


def build_engine(paths, base_dir, backend, spec, force=False, use_cache=False, extra_state=None):
    req = os.path.join(HERE, spec["backends"][backend])
    start = time.time()

    remove_tree(paths.new)
    log(f"[1/5] Copying base Python from {base_dir} ...")
    copy_tree(base_dir, paths.new)
    try:
        os.remove(os.path.join(paths.new, "engine.json"))
    except OSError:
        pass

    log(f"[2/5] Installing {backend} packages ({os.path.basename(req)}) ...")
    if backend != "cpu":
        log("      The CUDA build of torch is about 3.3 GB: it may take a while.")
    if not pip_install(os.path.join(paths.new, "python.exe"), req, force=force, use_cache=use_cache):
        log("ERROR: package installation failed. The current engine was not changed.")
        remove_tree(paths.new)
        return False

    log("[3/5] Updating Visual C++ runtime DLLs ...")
    update_runtime_dlls(paths.new)
    for path, v in old_msvcp_copies(paths.new):
        log(f"  [Warn] old runtime left: {path} ({'.'.join(map(str, v))})")

    log(f"[4/5] Checking Demucs model ({spec.get('demucs_model', 'htdemucs')}) ...")
    if not ensure_model(paths.new, spec.get("demucs_model", "htdemucs")):
        log("  [Warn] model not downloaded now: Demucs will download it on first use.")

    log(f"[5/5] Testing the engine ({backend}) ...")
    ok, detail = probe(paths.new, backend)
    log(f"      {detail}")
    if not ok:
        log("ERROR: the new engine did not pass the test. The current engine was not changed.")
        remove_tree(paths.new)
        return False

    state = {"engine_version": spec["engine_version"], "backend": backend,
             "built": time.strftime("%Y-%m-%d %H:%M")}
    state.update(extra_state or {})
    write_state(paths.new, state)

    if not swap_in(paths):
        remove_tree(paths.new)
        return False
    log(f"Engine ready: {backend}, version {spec['engine_version']} "
        f"({int(time.time() - start)} s).")
    return True


def recover(paths):
    if not os.path.isdir(paths.engine) and os.path.isdir(paths.old):
        os.rename(paths.old, paths.engine)
        log("Previous engine restored after an interrupted update.")
    remove_tree(paths.new)
    remove_tree(paths.old)


# --------------------------------------------------
# Comandi
# --------------------------------------------------
def ask_yes_no(question):
    try:
        answer = input(f"{question} [Y/N]: ").strip().lower()
    except EOFError:
        return None
    return answer in ("y", "yes", "s", "si", "sì")


def enable_gpu(paths, spec, state):
    info = nvidia_info()
    if info is None:
        log("No NVIDIA GPU found (nvidia-smi does not answer): the engine stays on CPU.")
        return False
    name, driver = info
    backend = gpu_backend_for_driver(driver, spec)
    log(f"GPU: {name}, driver {driver} -> torch {backend}")
    ok = build_engine(paths, paths.engine, backend, spec, extra_state={"gpu_asked": True})
    if not ok:
        log("The GPU could not be enabled: Demucs and TransNetV2 keep using the CPU.")
        state["gpu_asked"] = True
        if os.path.isdir(paths.engine):
            write_state(paths.engine, state)
    return ok


RC_WARNING = 3


def cmd_check(paths, spec, ask=True):
    recover(paths)
    if not os.path.isfile(paths.python):
        log("ERROR: the 'engine' folder is missing or incomplete.")
        log("Extract the full Auto Sub ReTimer package again (engine folder included).")
        return 1

    state = read_state(paths.engine)
    backend = state.get("backend", "cpu")

    if state.get("engine_version") != spec["engine_version"]:
        log(f"Engine update required ({state.get('engine_version') or 'unknown'} -> "
            f"{spec['engine_version']}, {backend}).")
        if not build_engine(paths, paths.engine, backend, spec,
                            extra_state={"gpu_asked": state.get("gpu_asked", False)}):
            if os.path.isfile(paths.python):
                log("[Warn] The previous engine is still in use.")
                return RC_WARNING
            return 1
        state = read_state(paths.engine)
        backend = state.get("backend", "cpu")

    if ask and backend == "cpu" and not state.get("gpu_asked"):
        info = nvidia_info()
        if info is None:
            # Nessuna NVIDIA: la domanda non serve, cosi' dal prossimo avvio parte il fast open
            state["gpu_asked"] = True
            write_state(paths.engine, state)
        else:
            log(f"NVIDIA GPU found: {info[0]}.")
            answer = ask_yes_no("Enable the GPU for Demucs and TransNetV2? (about 3.3 GB download, only once)")
            if answer is None:
                return 0
            if answer:
                if not enable_gpu(paths, spec, state):
                    return RC_WARNING
            else:
                state["gpu_asked"] = True
                write_state(paths.engine, state)
                log("OK, Demucs and TransNetV2 will use the CPU. You can enable the GPU later from Options.")
    return 0


def cmd_status(paths, spec):
    state = read_state(paths.engine)
    log(f"Engine folder : {paths.engine}")
    log(f"Installed     : {state.get('backend', '?')} {state.get('engine_version', '?')} "
        f"(built {state.get('built', '?')})")
    log(f"Expected      : {spec['engine_version']}")
    info = nvidia_info()
    log(f"NVIDIA GPU    : {'%s, driver %d' % info if info else 'not found'}")
    if os.path.isfile(paths.python):
        ok, detail = probe(paths.engine, state.get("backend", "cpu"))
        log(f"Test          : {detail}")
    return 0


def main(argv):
    pause = "--pause" in argv
    argv = [a for a in argv if a != "--pause"]
    command = argv[0] if argv else "check"
    engine_dir = os.path.join(PROJECT_ROOT, "engine")
    if "--engine-dir" in argv:
        engine_dir = argv[argv.index("--engine-dir") + 1]
    paths = Paths(engine_dir)
    spec = load_spec()

    try:
        if command == "check":
            rc = cmd_check(paths, spec, ask="--no-ask" not in argv)
        elif command == "status":
            rc = cmd_status(paths, spec)
        elif command in ("gpu", "cpu", "repair"):
            recover(paths)
            if not os.path.isfile(paths.python):
                log("ERROR: the 'engine' folder is missing: extract the full package again.")
                rc = 1
            else:
                state = read_state(paths.engine)
                if command == "gpu":
                    rc = 0 if enable_gpu(paths, spec, state) else 1
                elif command == "cpu":
                    rc = 0 if build_engine(paths, paths.engine, "cpu", spec,
                                           extra_state={"gpu_asked": True}) else 1
                else:
                    rc = 0 if build_engine(paths, paths.engine, state.get("backend", "cpu"), spec,
                                           force=True,
                                           extra_state={"gpu_asked": state.get("gpu_asked", False)}) else 1
        else:
            log(f"Unknown command: {command}")
            rc = 2
    except KeyboardInterrupt:
        log("\nInterrupted: the current engine was not changed.")
        remove_tree(paths.new)
        rc = 1

    if pause:
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
