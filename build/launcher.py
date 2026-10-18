#   AutoSubReTimer.exe                      avvia Scripts\GUI\GUI.py
#   AutoSubReTimer.exe script.py [args]     esegue uno script
#   AutoSubReTimer.exe -m modulo [args]     esegue un modulo
# PYTHONPATH viene letto a mano: l'exe congelato lo ignorerebbe.
import multiprocessing
import json
import os
import runpy
import sys

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

IGNORED_FLAGS = ("-u", "-B", "-E", "-s", "-I", "-O", "-OO")


def app_root():
    if getattr(sys, "frozen", False):
        # exe: <root>\AutoSubReTimer.exe -> <root>
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pythonpath_entries():
    return [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]


def run_script(path, args):
    path = os.path.abspath(path)
    sys.argv = [path, *args]
    sys.path[0:0] = [os.path.dirname(path), *pythonpath_entries()]
    runpy.run_path(path, run_name="__main__")

def console_window(action):
    if os.name != "nt":
        return
    import ctypes
    kernel32 = ctypes.windll.kernel32
    if action == "title":
        kernel32.SetConsoleTitleW("Auto Sub ReTimer")
    elif action == "minimize":
        import threading
        import time
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return
        user32.ShowWindow(hwnd, 0)

        def hide_pseudo_console():
            for _ in range(20):
                time.sleep(0.05)
                if user32.IsWindowVisible(hwnd):
                    user32.ShowWindow(hwnd, 0)
                    break

        threading.Thread(target=hide_pseudo_console, daemon=True).start()

def engine_is_ready(root):
    engine_dir = os.path.join(root, "engine")

    if os.path.isdir(engine_dir + ".new") or os.path.isdir(engine_dir + ".old"):
        return False
    if not os.path.isfile(os.path.join(engine_dir, "python.exe")):
        return False

    try:
        with open(os.path.join(engine_dir, "engine.json"), "r", encoding="utf-8") as f:
            state = json.load(f)
        with open(os.path.join(root, "Scripts", "Engine", "engine_spec.json"),
                  "r", encoding="utf-8") as f:
            spec = json.load(f)
    except (OSError, ValueError):
        return False

    if state.get("engine_version") != spec.get("engine_version"):
        return False
    backend = state.get("backend")
    if backend not in ("cpu", "cu126", "cu128"):
        return False
    if backend == "cpu" and not state.get("gpu_asked"):
        return False
    return True


# Controllo finito con un avviso, il programma parte lo stesso
RC_WARNING = 3


def full_engine_check(root):
    manager_dir = os.path.join(root, "Scripts", "Engine")
    sys.path.insert(0, manager_dir)
    try:
        import engine_manager
        return engine_manager.main(["check"])
    except Exception as e:
        print(f"[Warn] engine check failed: {e}")
        return RC_WARNING
    finally:
        try:
            sys.path.remove(manager_dir)
        except ValueError:
            pass


def start_program():
    root = app_root()
    os.chdir(root)
    console_window("title")

    if engine_is_ready(root):
        pass  # fast path: niente check
    else:
        rc = full_engine_check(root)
        if rc == RC_WARNING:
            # La console si minimizza subito dopo: prima si lascia leggere l'avviso
            try:
                input("\nPress Enter to continue...")
            except EOFError:
                pass
        elif rc != 0:
            try:
                input("\nPress Enter to close...")
            except EOFError:
                pass
            sys.exit(rc)

    console_window("minimize")
    gui_dir = os.path.join(root, "Scripts", "GUI")
    sys.path[0:0] = [gui_dir, *pythonpath_entries()]
    sys.argv = ["GUI"]
    runpy.run_module("GUI", run_name="__main__", alter_sys=True)


def main():
    multiprocessing.freeze_support()
    argv = sys.argv[1:]
    while argv and argv[0] in IGNORED_FLAGS:
        argv.pop(0)

    if not argv:
        start_program()
    elif argv[0] == "-m" and len(argv) > 1:
        sys.argv = [argv[1], *argv[2:]]
        sys.path[0:0] = [os.getcwd(), *pythonpath_entries()]
        runpy.run_module(argv[1], run_name="__main__", alter_sys=True)
    elif argv[0] == "-c" and len(argv) > 1:
        sys.argv = ["-c", *argv[2:]]
        sys.path[0:0] = ["", *pythonpath_entries()]
        exec(compile(argv[1], "<string>", "exec"), {"__name__": "__main__"})
    else:
        run_script(argv[0], argv[1:])


if __name__ == "__main__":
    main()
