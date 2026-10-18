import sys

try:
    import torch
except Exception as e:
    print(f"ERR cannot load torch: {e}")
    sys.exit(3)

if not torch.cuda.is_available():
    print("ERR CUDA not available (CPU build, NVIDIA driver missing or too old)")
    sys.exit(2)

try:
    x = torch.randn(256, 256, device="cuda")
    (x @ x).sum().item()
except RuntimeError as e:
    msg = str(e).strip().splitlines()[0] if str(e).strip() else repr(e)
    low = msg.lower()
    if "no kernel image" in low:
        hint = "this torch build does not support the GPU architecture"
    elif "out of memory" in low:
        hint = "not enough video memory"
    elif "driver" in low:
        hint = "NVIDIA driver needs an update"
    else:
        hint = "CUDA failure"
    print(f"ERR {hint}: {msg}")
    sys.exit(4)

print(f"OK {torch.cuda.get_device_name(0)}")
