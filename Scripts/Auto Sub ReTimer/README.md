## Overview of the Phases

| Script     | Main Function | Editable Values |
|------------|---------------|-----------------|
| **Phase0.py** | Separates subtitles into categories (.ass and .srt) | No |
| **Phase1.py** | Extracts audio and separates voice using [Demucs](https://github.com/facebookresearch/demucs) | No |
| **Phase2.py** | Adjusts lead‑in/out based on audio peaks | Yes (4 values) |
| **Phase3.py** | Detects scene changes using [PySceneDetect](https://github.com/Breakthrough/PySceneDetect)/[TransNetV2](https://github.com/soCzech/TransNetV2) | No |
| **Phase4.py** | Aligns subtitles to scene changes | Yes (4 values) |
| **Phase5.py** | Rebuilds final file with original styles | No |
| **Phase6.py** | Cleans up and moves final files | No |

## What exactly do the "Phases.py" scripts do? 

## **Phase0.py**
Separates the loaded subtitles into different categories:

- **For .ass files**:
  - **Signs**: signs, opening, and ending.
  - **Comments**: commented and empty lines.
  - **On Top**: dialogues positioned at the top of the screen.
- **For .srt files**:
  - **On Top**: dialogues positioned at the top of the screen.

**Editable values:** None.

## **Phase1.py**
- Extracts audio from the `.mkv` file.
- Passes the audio to [Demucs](https://github.com/facebookresearch/demucs) to separate the voice track:
  - **CPU**: ~3–5 minutes
  - **GPU**: ~30–40 seconds (requires the correct CUDA version in the `main` folder).
- All processing is done locally — no external services are used.

**Editable values:** None.

## **Phase2.py**
- Analyzes audio peaks to remove and reapply lead‑in/out.
- Merges lines with a gap of `0.000s` to maintain continuity.

**Editable values:** 4

#### 1. Peak detection margin after initial timestamp (ms)

<img width="934" height="303" alt="1" src="https://github.com/user-attachments/assets/6016c38c-34bc-4f38-bd75-b2d9abb9d751" />

Sets a margin to detect the first audio peak of speech **after** the line’s initial timestamp.  
Mainly used to remove lead‑in from subtitles, then reapply it based on your personal settings.  
**Recommended value:** 400–500 ms. 

**Example with 200 milliseconds:**

![Phase2 1 200](https://github.com/user-attachments/assets/d690943a-c353-41cf-8462-16208599f29d)

Here, 200 ms is enough to detect the first audio peak after the line's initial timestamp.  
The distance from the first arrow (line's initial timestamp) to the second arrow (first audio peak) falls within the 200 ms range.  
If the audio peak is farther from the initial timestamp, increase this value.

#### 2. Peak detection margin before final timestamp (ms)

<img width="934" height="303" alt="2" src="https://github.com/user-attachments/assets/86c6d77f-959b-4b04-a4ac-686460ed1bef" />

Sets a margin to detect the first audio peak of speech **before** the line’s end timestamp.  
Mainly used to remove lead‑out from subtitles, then reapply it based on your personal settings.  
**Recommended value:** 700+ ms.

**Example with 600 milliseconds:**

![Phase2 2 600](https://github.com/user-attachments/assets/73264ebd-2543-4a74-885d-3c2208446b8a)

Here, 600 ms is enough to detect the first audio peak before the line's final timestamp.  
The distance from the first arrow (first audio peak) to the second arrow (line's final timestamp) falls within the 600 ms range.  
If the audio peak is farther from the final timestamp, increase this value.

#### 3–4. Add Lead‑in / Add Lead‑out

<img width="934" height="303" alt="3" src="https://github.com/user-attachments/assets/0bd6c8af-18a7-421c-83e5-2f0312084b73" />

Set your preferred lead‑in and lead‑out values here.  
**Recommended:** Lead‑in 170–180 ms, Lead‑out 400–450 ms.

If audio peaks in the two detection margins above are **not** detected because the values are too low, the lead‑in and lead‑out will still be added resulting in longer lines.  
To fix overly long lines, increase the peak detection values.

## **Phase3.py**
- Detects scene changes and saves them in a `.srt` file, which will then be used by **Phase4.py**.  
- Uses [PySceneDetect](https://github.com/Breakthrough/PySceneDetect)/[TransNetV2](https://github.com/soCzech/TransNetV2) (The first choice should always be PySceneDetect)

**Editable values:** None.

## **Phase4.py**
- Ensures that lines respect scene changes where possible.  
  *(May cut part of the spoken audio if Phase3 detected false scene changes.)*  
- Adds lead‑in to low‑CPM lines adjusted to a scene change, to prevent them from disappearing too quickly.  
- Joins lines with `0.000s` gap if the silence between them is within 0.300 seconds.

**Editable values:** 4

#### 1. Max range to detect a scene change from the final timestamp (ms)

<img width="934" height="309" alt="1" src="https://github.com/user-attachments/assets/ab172672-768f-408b-84d6-901d60b2cc2c" />

Detects a scene change (keyframe) **after** a line’s end timestamp.  
The margin checks for a scene change after applying the lead‑out set in Phase2.  
Example: Lead‑out 450 ms (Phase2) → max range 750 ms (450 ± 300 if a scene change is detected).

#### 2. Max gap 'empty' between two lines to attach (ms)

<img width="934" height="309" alt="2" src="https://github.com/user-attachments/assets/eaf61402-f050-4de4-85ab-562b960ff010" />

Controls the distance between two lines.  
If the next line starts within 250–300 ms (recommended), they will be merged for smoother reading.  
Indirectly depends on your lead‑in/lead‑out values in Phase2.

#### 3. Max range to detect scene change before the initial timestamp (ms)

<img width="934" height="307" alt="4" src="https://github.com/user-attachments/assets/ebbf4da1-d15b-439b-b393-dc9442a56ede" />

Checks for a scene change **before** the line’s start, within the set margin (200–250 ms recommended).  
Example: Lead‑in 180 ms (Phase2) + Max range 250 ms → up to 430 ms possible if a scene change is detected.

#### 4. Max range to detect scene change after the initial timestamp (ms)

<img width="934" height="307" alt="5" src="https://github.com/user-attachments/assets/6039a779-ca91-4b8d-889c-6cd99afb1263" />

Checks for a scene change **after** the line’s start, within the set margin (200 ms recommended).  
Less common than the previous case, but handled if needed.  
Indirectly depends on your lead‑in value in Phase2.

## **Phase5.py**
- If you uploaded an `.ass` file for adjustment, the final `.ass` will keep the original header and styles for every line, but with updated timing.

**Editable values:** None.


## **Phase6.py** 
- Deletes unnecessary temporary files after processing.  
- Saves the processed file in the input folder (where you selected the subtitles) or in a custom directory set via the GUI's `Options`.  
- Prompts you on how to save the final file, simply follow the on-screen instructions.

**Editable values:** None.

