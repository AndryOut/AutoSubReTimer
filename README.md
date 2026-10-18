## Overview

Auto Sub ReTimer is a local tool designed to automatically improve subtitle timing for `.ass` and `.srt` files.  
It analyzes the audio track of your video to detect the exact start and end of spoken dialogue, then adjusts each subtitle line accordingly.  
The process can also take into account scene changes, ensuring that subtitles appear and disappear in sync with visual cuts for a smoother viewing experience.

Key features:
- **Automatic voice extraction** from the video to isolate speech.
- **Lead‑in/Lead‑out adjustment** based on detected audio peaks.
- **Scene change detection** to align subtitles with visual transitions.
- **Style preservation** for `.ass` files original formatting and styles are kept.
- **Local processing** no internet connection required for timing adjustments after the first run.
- **Optional GPU acceleration** with NVIDIA CUDA for faster processing.

<img width="1272" height="882" alt="GUI" src="https://github.com/user-attachments/assets/1c53dc94-f45b-4635-ba34-39f7c8a7176f" />

## Requirements

- Windows 10 / 11, 64 bit
- About 3 GB of free disk space (6 GB+ with the NVIDIA GPU engine)
- Optional: NVIDIA GPU for faster processing
- Optional: `Faster-Whisper-XXL` folder next to the exe for the Whisper functions

## Installation

1. Extract the rar into any folder (better not inside "Program Files").
2. Run `AutoSubReTimer.exe`.
3. If you have an NVIDIA graphics card, on first launch the program asks whether to use it (one-time download, about 3.3 GB). Otherwise everything runs on the CPU.

No Python or ffmpeg installation needed. Everything is included.

What exactly do the scripts do?  
Want to customize the settings to suit your preferences?  
[Read here](Scripts/Auto%20Sub%20ReTimer/README.md)
---

## How to use

- Run `AutoSubReTimer.exe`.

- Select AS or CR, press Start, select first your video and then the subtitles.
- For more information, open Options and enable Instruction panel.


---
## Input Alignment Guidelines (Important)

THE LINE OF SPOKEN AUDIO IN THE SUB MUST BE WITHIN THE LINES AND NOT PARTIALLY OUTSIDE THE LINE (Audio Spectrum).  
THERE MUST NOT BE THE START OF SPOKEN AUDIO THAT BEGINS BEFORE THE LINE, FOR EXAMPLE.  
WHEN UPLOADING YOUR `.ass` OR `.srt`, MAKE SURE TO FOLLOW THE INSTRUCTIONS.  
EVEN A QUICK SYNC THAT'S THE SAME FOR ALL LINES IS SUFFICIENT.  
FOR EXAMPLE `-41 ms` (-1 frame) OR `-82 ms` (-2 frames).     

---
### Does not meet the requirements

![Does not meet the requirements](https://github.com/user-attachments/assets/5e963886-c763-4511-a35a-716d4dba95cb)

### Meets the requirements

(It is not necessary for the initial timestamp to perfectly align with the beginning of the audio peak of the speech, the important thing is that the beginning of the speech is included, the rest will be handled by the program):

![Meets the requirements](https://github.com/user-attachments/assets/faace722-7cc3-400f-944a-2be206f7c0e6)

---
## Before and After Examples – Auto Sub ReTimer

### Example 1 – Original Sub

![Original](https://github.com/user-attachments/assets/7953eb46-e2ed-49ff-b1b0-3c997a78c0f5)
![Original](https://github.com/user-attachments/assets/5e3d6209-8601-4ecd-a9e7-ebd7289b724a)

**Adjusted Sub with scene change:**

![Adjusted](https://github.com/user-attachments/assets/780d6aa0-d7bc-4ee8-865d-38849dd6d892)
![Adjusted](https://github.com/user-attachments/assets/516aff27-5ab5-4e00-a75c-7ac88594b317)

---
### Example 2 – Original Sub

![Original](https://github.com/user-attachments/assets/ed23556d-9766-44eb-a9cb-a20742c9e0ed)

**Adjusted Sub:**

![Adjusted](https://github.com/user-attachments/assets/30a422b8-e8f1-4351-a632-01f6c41efbad)

---
### Example 3 – Original Sub

![Original](https://github.com/user-attachments/assets/abcb7e51-974e-4cf8-8ba4-0310459c13ed)

**Adjusted Sub with scene change:**

![Adjusted](https://github.com/user-attachments/assets/b2fc1fa4-83c5-4b2e-9596-63e3d9408b57)

---
## Whisper

### Requirements

- Put your video `.mkv` and the folder `Faster-Whisper-XXL` inside the `Auto Sub ReTimer` folder.
- Run `AutoSubReTimer.exe` and select **"Whisper"**.

### Improving `whisper.srt`

- Use **Whisper ReTimer**.
- You will have two options:
  - Use only a basic timing improvement.
  - Ensure it also respects scene changes.
- Once you have made your choice and the process is complete, you will find everything you need on the Desktop.

> Keep in mind that the improvement with scene changes is not perfect, especially if used with the basic timing of Whisper.
