# Build di Auto Sub ReTimer. Si lancia da build\build.bat, che prepara build\venv.
#   build.bat            tutto: exe (AutoSubReTimer.exe + app\), motore CPU (engine\) se manca o e' vecchio, pacchetto in dist\
#   build.bat app        solo l'exe (AutoSubReTimer.exe + app\)
#   build.bat engine     solo il motore in engine\ (aggiungi --force per rifarlo da zero)
#   build.bat release    solo il pacchetto dist\Auto Sub ReTimer\ e lo zip
#   build.bat scan       mostra gli import trovati nelle Fasi (quelli che finiscono nell'exe)
import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent
SCRIPTS = ROOT / "Scripts"
APP_DIR = ROOT / "app"
DIST_DIR = ROOT / "dist"
RELEASE_NAME = "Auto Sub ReTimer"
EXE_NAME = "AutoSubReTimer"
EXE_PATH = ROOT / f"{EXE_NAME}.exe"

sys.path.insert(0, str(SCRIPTS / "Engine"))
import engine_manager as em  # noqa: E402

# File in Scripts\Engine eseguiti da engine\python.exe e non dall'exe: i loro import non vanno nell'exe
ENGINE_ONLY = {"gpu_probe.py", "run_demucs.py"}

# Moduli della libreria standard inclusi comunque, cosi' una Fase modificata che li usa funziona senza ricompilare l'exe
STDLIB_EXTRA = [
    "argparse", "base64", "bisect", "calendar", "codecs", "collections", "concurrent.futures",
    "contextlib", "copy", "csv", "ctypes", "ctypes.wintypes", "dataclasses", "datetime",
    "decimal", "difflib", "enum", "fnmatch", "fractions", "functools", "gc", "glob", "hashlib",
    "heapq", "html", "importlib", "inspect", "io", "itertools", "json", "locale", "logging",
    "math", "multiprocessing", "operator", "pathlib", "pickle", "platform", "pprint",
    "py_compile", "queue", "random", "re", "runpy", "shlex", "shutil", "signal", "statistics",
    "string", "struct", "subprocess", "tempfile", "textwrap", "threading", "time", "tkinter",
    "tkinter.filedialog", "tkinter.font", "tkinter.messagebox", "tkinter.simpledialog",
    "tkinter.ttk", "traceback", "typing", "unicodedata", "uuid", "wave", "webbrowser",
    "winreg", "xml.etree.ElementTree", "zipfile",
]


def log(msg=""):
    print(msg, flush=True)


# --------------------------------------------------
# Import usati da GUI e Fasi
# --------------------------------------------------
def script_files():
    for py in SCRIPTS.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        if py.parent.name == "Engine" and py.name in ENGINE_ONLY:
            continue
        yield py


def scan_imports():
    files = list(script_files())
    local = {p.stem for p in SCRIPTS.rglob("*.py")}
    found = set()
    for py in files:
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except (SyntaxError, UnicodeDecodeError) as e:
            log(f"  [Warn] cannot parse {py.relative_to(ROOT)}: {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add((alias.name, py))
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add((node.module, py))
                for alias in node.names:
                    found.add((f"{node.module}.{alias.name}", py))

    modules, missing = set(), {}
    for name, py in found:
        if name.split(".")[0] in local:
            continue
        try:
            ok = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError, AttributeError):
            ok = False
        if ok:
            modules.add(name)
        elif "." not in name or importlib.util.find_spec(name.split(".")[0]) is None:
            # "from x import funzione" genera x.funzione: non e' un modulo, non e' un errore
            missing.setdefault(name, set()).add(str(py.relative_to(ROOT)))
    return sorted(modules), missing


def cmd_scan():
    modules, missing = scan_imports()
    log(f"{len(modules)} modules found in Scripts:")
    for m in modules:
        log(f"  {m}")
    for name, where in sorted(missing.items()):
        log(f"  [Missing] {name} (used in {', '.join(sorted(where))}) - add it to build\\requirements-app.txt")
    return 0


# --------------------------------------------------
# Exe (PyInstaller)
# --------------------------------------------------
def cmd_app():
    import PyInstaller.__main__

    modules, missing = scan_imports()
    for name, where in sorted(missing.items()):
        log(f"[Warn] {name} not installed in build\\venv (used in {', '.join(sorted(where))}): "
            f"add it to build\\requirements-app.txt if that script is used")
    hidden = sorted(set(modules) | set(STDLIB_EXTRA))

    work = BUILD_DIR / "pyi-work"
    out = BUILD_DIR / "pyi-dist"
    args = [
        str(BUILD_DIR / "launcher.py"),
        "--name", EXE_NAME,
        "--onedir", "--console", "--noconfirm", "--clean", "--contents-directory", "app",
        "--distpath", str(out), "--workpath", str(work), "--specpath", str(work),
        "--collect-submodules", "scenedetect",
        "--collect-data", "customtkinter",
        "--exclude-module", "torch",
        "--noupx",
        "--log-level", "WARN",
    ]
    for m in hidden:
        args += ["--hidden-import", m]

    log(f"PyInstaller: {len(hidden)} modules requested ...")
    PyInstaller.__main__.run(args)

    built = out / EXE_NAME
    if not (built / f"{EXE_NAME}.exe").is_file():
        log("ERROR: PyInstaller did not produce the exe.")
        return 1

    # PyInstaller produce AutoSubReTimer.exe + app\: vanno nella cartella del programma
    try:
        if EXE_PATH.exists():
            EXE_PATH.unlink()
        if APP_DIR.exists():
            shutil.rmtree(APP_DIR)
    except OSError as e:
        log(f"ERROR: cannot replace the exe or app\\ ({e}). Close Auto Sub ReTimer and try again.")
        return 1
    shutil.move(str(built / "app"), str(APP_DIR))
    shutil.move(str(built / f"{EXE_NAME}.exe"), str(EXE_PATH))

    log("Updating Visual C++ runtime DLLs in app\\ ...")
    em.update_runtime_dlls(str(APP_DIR))

    info = {"built": time.strftime("%Y-%m-%d %H:%M"), "python": sys.version.split()[0],
            "hidden_imports": len(hidden)}
    (APP_DIR / "build_info.json").write_text(json.dumps(info, indent=4), encoding="utf-8")
    log(f"Exe ready: {EXE_PATH}")
    return 0


# --------------------------------------------------
# Motore (engine\)
# --------------------------------------------------
def cmd_engine(force=False, engine_dir=None, backend=None, reset_gpu_question=False):
    spec = em.load_spec()
    paths = em.Paths(str(engine_dir or (ROOT / "engine")))
    em.recover(paths)
    state = em.read_state(paths.engine)
    backend = backend or state.get("backend", "cpu")
    up_to_date = (os.path.isfile(paths.python)
                  and state.get("engine_version") == spec["engine_version"]
                  and state.get("backend") == backend)
    if up_to_date and not force:
        log(f"Engine up to date: {paths.engine} ({backend}, {spec['engine_version']})")
        return 0
    base = ROOT / "python"
    if not (base / "python.exe").is_file():
        log(f"ERROR: base Python not found in {base}")
        return 1
    gpu_asked = False if reset_gpu_question else state.get("gpu_asked", False)
    ok = em.build_engine(paths, str(base), backend, spec, force=force, use_cache=True,
                         extra_state={"gpu_asked": gpu_asked})
    return 0 if ok else 1


# --------------------------------------------------
# Pacchetto (dist\)
# --------------------------------------------------
def robocopy(src, dst, extra=()):
    r = subprocess.run(["robocopy", str(src), str(dst), "/E", "/NFL", "/NDL", "/NJH", "/NJS",
                        "/NP", "/R:1", "/W:1", *extra],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode >= 8:
        raise OSError(f"robocopy {src} -> {dst} failed (code {r.returncode})")


def cmd_release(make_zip=True):
    if not EXE_PATH.is_file() or not APP_DIR.is_dir():
        log("ERROR: AutoSubReTimer.exe or app\\ is missing: run 'build.bat app' first.")
        return 1

    stage = DIST_DIR / RELEASE_NAME
    log(f"Preparing {stage} ...")
    em.remove_tree(str(stage))
    stage.mkdir(parents=True)

    shutil.copy2(EXE_PATH, stage / EXE_PATH.name)
    robocopy(APP_DIR, stage / "app")
    # gui_config.json resta fuori: e' la configurazione di chi compila (pannelli, avvisi gia' chiusi, cartella di output)
    robocopy(SCRIPTS, stage / "Scripts", ["/XD", "__pycache__", "/XF", "gpu_probe_cache.json", "gui_config.json"])
    robocopy(ROOT / "ffmpeg", stage / "ffmpeg")
    shutil.copy2(ROOT / "Yamato.bat", stage / "Yamato.bat")

    # Il pacchetto contiene sempre il motore CPU, con la domanda sulla GPU ancora da fare
    spec = em.load_spec()
    root_state = em.read_state(str(ROOT / "engine"))
    if (root_state.get("backend") == "cpu"
            and root_state.get("engine_version") == spec["engine_version"]
            and (ROOT / "engine" / "python.exe").is_file()):
        log("Copying CPU engine ...")
        robocopy(ROOT / "engine", stage / "engine")
        root_state["gpu_asked"] = False
        em.write_state(str(stage / "engine"), root_state)
    else:
        # Il motore del progetto e' GPU (o vecchio): per il pacchetto si usa un motore CPU tenuto
        # in build\engine-cpu, creato una volta sola e rifatto solo quando cambia engine_version
        cpu_cache = BUILD_DIR / "engine-cpu"
        log(f"The engine in the project folder is not the current CPU one: using {cpu_cache} ...")
        if cmd_engine(force=False, engine_dir=cpu_cache, backend="cpu") != 0:
            return 1
        log("Copying CPU engine ...")
        robocopy(cpu_cache, stage / "engine")
        state = em.read_state(str(stage / "engine"))
        state["gpu_asked"] = False
        em.write_state(str(stage / "engine"), state)

    if make_zip:
        zip_base = DIST_DIR / RELEASE_NAME
        log(f"Creating {zip_base}.zip (a few minutes) ...")
        zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=DIST_DIR, base_dir=RELEASE_NAME)
        size = os.path.getsize(zip_path) / (1024 ** 3)
        log(f"Package ready: {zip_path} ({size:.2f} GB)")
    log(f"Folder ready: {stage}")
    return 0


def main(argv):
    command = argv[0] if argv else "all"
    force = "--force" in argv
    started = time.time()
    if command == "scan":
        rc = cmd_scan()
    elif command == "app":
        rc = cmd_app()
    elif command == "engine":
        rc = cmd_engine(force=force)
    elif command == "release":
        rc = cmd_release(make_zip="--no-zip" not in argv)
    elif command == "all":
        rc = cmd_app()
        if rc == 0:
            rc = cmd_engine(force=force)
        if rc == 0:
            rc = cmd_release(make_zip="--no-zip" not in argv)
    else:
        log(f"Unknown command: {command} (use: all, app, engine, release, scan)")
        rc = 2
    log(f"\n{'DONE' if rc == 0 else 'FAILED'} in {int(time.time() - started)} s")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
