## Overview of the Phases

| Script     | Main Function | Editable Values |
|------------|---------------|-----------------|
| **Fase0.py** | Separates subtitles into categories (.ass and .srt) | No |
| **Fase1.py** | Extracts audio and separates voice using [Demucs](https://github.com/facebookresearch/demucs) – MIT License | No |
| **Fase2.py** | Adjusts lead‑in/out based on audio peaks | Yes (4 values) |
| **Fase3.py** | Detects scene changes using [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) – BSD 3‑Clause License | No |
| **Fase4.py** | Aligns subtitles to scene changes | Yes (4 values) |
| **Fase5.py** | Rebuilds final file with original styles | No |
| **Fase6.py** | Cleans up and moves final files | No |

## What exactly do the "Fasi.py" scripts do? 

## **Fase0.py**
Separates the loaded subtitles into different categories:

- **For .ass files**:
  - **Signs**: signs, opening, and ending.
  - **Comments**: commented and empty lines.
  - **On Top**: dialogues positioned at the top of the screen.
- **For .srt files**:
  - **On Top**: dialogues positioned at the top of the screen.

**Editable values:** None.

## **Fase1.py**
- Extracts audio from the `.mkv` file.
- Passes the audio to [Demucs](https://github.com/facebookresearch/demucs) to separate the voice track:
  - **CPU**: ~3–5 minutes
  - **GPU**: ~30–40 seconds (requires the correct CUDA version in the `main` folder).
- All processing is done locally — no external services are used.

**Editable values:** None.

## **Fase2.py**
- Analyzes audio peaks to remove and reapply lead‑in/out.
- Merges lines with a gap of `0.000s` to maintain continuity.

**Editable values:** 4

#### 1. Peak detection margin after initial timestamp (ms)

![1](https://github.com/user-attachments/assets/4f44dde5-b04e-4318-b9c4-b7a7925b38dc)

Sets a margin to detect the first audio peak of speech **after** the line’s initial timestamp.  
Mainly used to remove lead‑in from subtitles, then reapply it based on your personal settings.  
**Recommended value:** 400–500 ms. 

**Example with 200 milliseconds:**

![Fase2 1 200](https://github.com/user-attachments/assets/d690943a-c353-41cf-8462-16208599f29d)

Here, 200 ms is enough to detect the first audio peak after the line's initial timestamp.  
The distance from the first arrow (line's initial timestamp) to the second arrow (first audio peak) falls within the 200 ms range.  
If the audio peak is farther from the initial timestamp, increase this value.

#### 2. Peak detection margin before final timestamp (ms)

![1](https://github.com/user-attachments/assets/866a6f7b-59ec-4ed6-b28b-ba44c519c589)

Sets a margin to detect the first audio peak of speech **before** the line’s end timestamp.  
Mainly used to remove lead‑out from subtitles, then reapply it based on your personal settings.  
**Recommended value:** 700+ ms.

**Example with 600 milliseconds:**

![Fase2 2 600](https://github.com/user-attachments/assets/73264ebd-2543-4a74-885d-3c2208446b8a)

Here, 600 ms is enough to detect the first audio peak before the line's final timestamp.  
The distance from the first arrow (first audio peak) to the second arrow (line's final timestamp) falls within the 600 ms range.  
If the audio peak is farther from the final timestamp, increase this value.

#### 3–4. Add Lead‑in / Add Lead‑out

![1](https://github.com/user-attachments/assets/11e89b62-b6a7-43ec-8663-eb7ae2ab9c7c)

Set your preferred lead‑in and lead‑out values here.  
**Recommended:** Lead‑in 170–180 ms, Lead‑out 400–450 ms.

If audio peaks in the two detection margins above are **not** detected because the values are too low, the lead‑in and lead‑out will still be added resulting in longer lines.  
To fix overly long lines, increase the peak detection values.

## **Fase3.py**
- Detects scene changes and saves them in a `.srt` file, which will then be used by **Fase4.py**.  
- Uses [PySceneDetect](https://github.com/Breakthrough/PySceneDetect)

**Editable values:** None.

## **Fase4.py**
- Ensures that lines respect scene changes where possible.  
  *(May cut part of the spoken audio if Fase3 detected false scene changes.)*  
- Adds lead‑in to low‑CPM lines adjusted to a scene change, to prevent them from disappearing too quickly.  
- Joins lines with `0.000s` gap if the silence between them is within 0.300 seconds.

**Editable values:** 4

#### 1. Max range to detect a scene change from the final timestamp (ms)

![fase4](https://github.com/user-attachments/assets/e614e08e-89ee-4bec-85e0-7a082e41e708)

Detects a scene change (keyframe) **after** a line’s end timestamp.  
The margin checks for a scene change after applying the lead‑out set in Fase2.  
Example: Lead‑out 450 ms (Fase2) → max range 750 ms (450 ± 300 if a scene change is detected).

#### 2. Max gap 'empty' between two lines to attach (ms)

![fase4](https://github.com/user-attachments/assets/6d424b8a-aad4-4856-8f07-d2cdf717e37e)

Controls the distance between two lines.  
If the next line starts within 250–300 ms (recommended), they will be merged for smoother reading.  
Indirectly depends on your lead‑in/lead‑out values in Fase2.

#### 3. Max range to detect scene change before the initial timestamp (ms)

![fase4](https://github.com/user-attachments/assets/840ae9ef-b171-4fdb-b0d5-044ac1bef798)

Checks for a scene change **before** the line’s start, within the set margin (200–250 ms recommended).  
Example: Lead‑in 180 ms (Fase2) + Max range 250 ms → up to 430 ms possible if a scene change is detected.

#### 4. Max range to detect scene change after the initial timestamp (ms)

![fase4](https://github.com/user-attachments/assets/e1cd1def-68ae-4b99-a205-214ab6c6ed44)

Checks for a scene change **after** the line’s start, within the set margin (200 ms recommended).  
Less common than the previous case, but handled if needed.  
Indirectly depends on your lead‑in value in Fase2.

## **Fase5.py**
- If you uploaded an `.ass` file for adjustment, the final `.ass` will keep the original header and styles for every line, but with updated timing.

**Editable values:** None.


## **Fase6.py** 
- Deletes unnecessary files after timing adjustments.  
- Moves the required files to the Desktop.  
- Asks whether to merge `On top.ass/.srt`, `Comments.ass`, and `Signs.ass` into the final file.  
  If you choose not to merge, the separate files will also be moved to the Desktop.

**Editable values:** None.

