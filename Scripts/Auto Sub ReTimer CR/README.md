# Auto Sub ReTimer CR

> Conservative retimer for subtitles that already have solid base timing but suffer from scene‑change misalignment or small gaps. Preserves the original lead‑in/out instead of rebuilding them from audio peaks.

---

## CR vs AS: what changes?

| Aspect | Auto Sub ReTimer (AS) | Auto Sub ReTimer CR |
|---|---|---|
| **Audio separation** | Yes (Demucs Phase1) | No |
| **Lead‑in/out** | Removed and reapplied based on audio peaks (Phase2) | Preserved from the original file |
| **Gap closing** | Handled inside Phase2 with audio‑aware logic | Simple hardcoded gap closer (Phase2) |
| **Phase4 presets** | Values hardcoded | Two presets: **Long leads** (default) and **Short leads** |
| **Best for** | Subtitles with completely wrong timing that need a full dialogue overhaul | Subtitles with solid base timing but scene‑change misalignment or standardisation gaps (e.g. some Crunchyroll, Disney, Amazon exports) |

---

## Overview of the Phases

| Script | Main Function | Editable Values |
|---|---|---|
| Phase0.py | Separates subtitles into categories (.ass and .srt) | No |
| Phase2.py | Closes small gaps between consecutive lines | No (threshold hardcoded) |
| Phase3.py | Detects scene changes using [PySceneDetect](https://github.com/Breakthrough/PySceneDetect)/[TransNetV2](https://github.com/soCzech/TransNetV2) | No |
| Phase4.py | Aligns subtitles to scene changes | No (**Long leads** / **Short leads** presets) |
| Phase5.py | Rebuilds the final .ass with updated timings | No |
| Phase6.py | Cleans up and moves final files | No |

> **Note:** CR has no Phase1 (Demucs). It does not separate vocals or analyse audio peaks. All timing adjustments are based on the existing subtitle timestamps and the detected scene changes.

---

## What exactly do the "Phases.py" scripts do?

### Phase0.py
Separates the loaded subtitles into different categories:

- For **.ass** files:
  - **Signs**: signs, opening, and ending.
  - **Comments**: commented and empty lines.
  - **On Top**: dialogues positioned at the top of the screen.
- For **.srt** files:
  - **On Top**: dialogues positioned at the top of the screen.

Editable values: **None**.

---

### Phase2.py
- Closes gaps of **150 ms or less** between consecutive lines by extending the current line’s end timestamp to the next line’s start timestamp.
- Unlike AS, it **does not** remove or reapply lead‑in/lead‑out. The original lead‑in/out values are preserved.
- This is a conservative “glue” pass: it only removes tiny empty spaces that would cause flicker.
- The threshold is hardcoded.

Editable values: **None**.  

---

### Phase3.py
- Detects scene changes.
- Uses [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) by default, or [TransNetV2](https://github.com/soCzech/TransNetV2) if selected in `Config_Phase3.json` (NVIDIA GPU usage requires CUDA. Upon first launch, the program will prompt you to install it. If you skipped the setup, you can install it later via Options > Engine > Enable GPU).
- Editable values: **None** (the detector choice is the only setting, stored in `Config_Phase3.json`).

---

### Phase4.py
- Ensures that lines respect scene changes where possible, while preserving the original lead‑in/out as much as possible.
- Has **two presets**, selectable from the GUI when starting CR:
  - **Long leads [Default]**: assumes the source timing already has generous leads. Uses conservative search ranges to minimise misalignments and avoid false snaps.
  - **Short leads**: designed for subtitles with tight/short leads. Uses broader search ranges to snap lines more aggressively and also bridges nearby gaps (up to 300 ms) when no scene change is in between.

  Editable values: **None**.

> **Tip:** If the lead‑in is a bit tight on certain episodes, you can apply a -41 ms or -82 ms (-1 or -2 frames) shift beforehand. This gives the opening speech more breathing room while CR keeps all scene snaps aligned.

---

### Phase5.py
- If you uploaded an **.ass** file, the final `.ass` keeps the original header and styles for every line, but with updated timing.
- If you uploaded an **.srt** file, this phase is skipped and the final file remains `.srt`.

Editable values: **None**.

---

### Phase6.py
- Deletes unnecessary temporary files after processing.
- Saves the processed file in the input folder (where you selected the subtitles) or in a custom directory set via the GUI’s **Options**.
- Prompts you on how to save the final file. Simply follow the on‑screen instructions.

Editable values: **None**.

---

## Quick start

1. Launch **Auto Sub ReTimer CR** from the main GUI (select the **CR** button, then click **START**).
2. When the prompt appears, choose the subtitle leads type: **Long leads** (default) or **Short leads**.
3. A window will pop up asking you to select the **video file** (`.mkv`).
4. A second window will ask you to select the **subtitle file** (`.ass` or `.srt`).
5. Wait for the phases to complete.
6. The final file will be saved according to your GUI output settings.