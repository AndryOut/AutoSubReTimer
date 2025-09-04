What exactly do the "Fasi.py" scripts do?  

Fase0.py:  
Separate from uploaded .ass sub (No need to manually sort everything anymore, the program does it all for you):

- "Signs": Contains all signs, opening and ending subtitles (necessary separation to adjust dialogue timing).

- "Comments": Contains commented lines and empty lines (necessary separation to adjust dialogue timing).

- "On Top": Contains all dialogues positioned at the top of the screen (necessary separation to adjust dialogue timing).

Separate from uploaded .srt sub:

- "On Top": Contains all dialogues positioned at the top of the screen (necessary separation to adjust dialogue timing). 

Values you can modify: None.

Fase1.py:
- Extracts audio from the video .mkv, passes it to demucs which extracts vocals with the CPU (3/5 minutes) or with GPU (30/40 seconds).
- Now there is no need to use the site anymore, it does everything automatically locally, make sure you have the right cuda version installed for you in the "main" folder to use GPU.

[Demucs](https://github.com/facebookresearch/demucs) — MIT License

Values you can modify: None.

Fase2.py:  
- Based on the audio peaks of spoken audio, removes the lead-in-out and resets them according to values that can be changed as per your preference.  
- Joins close lines with a space of 0.000 seconds between them for better continuity.  

Values you can modify: 4.  

Value 1 "Peak detection margin after initial timestamp (ms)":  

![1](https://github.com/user-attachments/assets/4f44dde5-b04e-4318-b9c4-b7a7925b38dc)

This sets a margin to detect the first audio peak of speech after the line’s initial timestamp.
It’s mainly used to remove lead-in from subtitles and then reapply it based on your personal settings. (Recommended value: 400-500)  

Example with 200 milliseconds:  

![Fase2 1 200](https://github.com/user-attachments/assets/d690943a-c353-41cf-8462-16208599f29d)

Here, the value 200 is more than enough to detect the first audio peak after the line's initial timestamp.  
The distance from the first arrow (line's initial timestamp) to the second arrow (first audio peak) falls within the 200-millisecond range.  
If the distance of the audio peak is farther from the line's initial timestamp, you can increase this value.  

Value 2 "Peak detection margin before final timestamp (ms)":  

![1](https://github.com/user-attachments/assets/866a6f7b-59ec-4ed6-b28b-ba44c519c589)

This sets a margin to detect the first audio peak of speech before the line’s end timestamp.
It’s mainly used to remove lead-out from subtitles and then reapply it based on your personal settings. (Recommended value: 700+)  

Example with 600 milliseconds:  

![Fase2 2 600](https://github.com/user-attachments/assets/73264ebd-2543-4a74-885d-3c2208446b8a)

Here, the value 600 is more than enough to detect the first audio peak before the line's final timestamp.  
The distance from the first arrow (first audio peak) to the second arrow (line's final timestamp) falls within the 600-millisecond range.  
If the distance of the audio peak is farther from the line's final timestamp, you can increase this value.  

Value 3-4 "Add Lead-in" - "Add Lead-out":  

![1](https://github.com/user-attachments/assets/11e89b62-b6a7-43ec-8663-eb7ae2ab9c7c)

You can set your preferred lead-in and lead-out values here. (Recommended: Lead-in 170-180, Lead-out 400-450)

If audio peaks in "Peak detection margin after initial timestamp (ms)" and "Peak detection margin before final timestamp (ms)" are not detected because the value was set too low, then the lead-in and lead-out will still be added, resulting in longer lines. Simply increase the peak detection values to address these overly long lines.

Fase3.py:  
- Detects scene changes and saves them in a .srt file, which will then be used by "Fase4.py".  

[PySceneDetect](https://github.com/Breakthrough/PySceneDetect) — BSD 3-Clause License

Values you can modify: None.

Fase4.py:  
- Ensures that lines respect scene changes where possible.  
(It may cut a part of the spoken audio if "Fase3" has detected nonexistent scene changes.)  
- Adds lead-in to lines with low CPM adjusted to a scene change to prevent the line from lasting too short on-screen.  
- Joins lines with 0.000 seconds if there is a gap of silence between lines within a range of 0.300 seconds.  

Values you can modify: 4.  

Value 1 "Max range to detect a scene change from the final timestamp (ms)":  

![fase4](https://github.com/user-attachments/assets/e614e08e-89ee-4bec-85e0-7a082e41e708)

This value detects a scene change (keyframe) after a line’s end timestamp.
The margin checks if there’s a scene change after applying the lead-out set in "Fase2 Configuration".
For example, if you set the lead-out to 450 (Fase2), the maximum range would be 750ms (450±300 if a scene change is detected).

Value 2 "Max gap 'empty' between two lines to attach (ms)":

![fase4](https://github.com/user-attachments/assets/6d424b8a-aad4-4856-8f07-d2cdf717e37e)

This controls the distance between two lines. If the next line is within 250-300 (recommended), they’ll be merged for smoother reading. If the gap is larger, they won’t be joined.
This indirectly depends on your lead-in/lead-out values in "Fase2 Configuration".

Value 3 "Max range to detect scene change before the initial timestamp (ms):"

![fase4](https://github.com/user-attachments/assets/840ae9ef-b171-4fdb-b0d5-044ac1bef798)

This determines whether to link a scene change (keyframe) found before the line’s initial timestamp, based on the set margin (200-250 recommended).
For example, if a scene change is detected within 250 before the line starts, it will be linked. If it’s beyond this margin, it won’t.
This indirectly depends on your lead-in value in "Fase2 Configuration".
For example: Lead-in 180 (Fase2), Max range 250. That is, 180±250, so a maximum of 430ms is possible if a scene change is detected.

Value 4 "Max range to detect scene change after the initial timestamp (ms):"

![fase4](https://github.com/user-attachments/assets/e1cd1def-68ae-4b99-a205-214ab6c6ed44)

This determines whether to link a scene change (keyframe) found after the line’s initial timestamp, based on the set margin.
For example, if a scene change is detected within 200 (recommended) after the line starts, it will be linked. If it’s beyond this margin, it won’t (this is rarer than the previous case, but the program will handle it if needed).
This indirectly depends on your lead-in value in "Fase2 Configuration".

Fase5.py:  
- Ensures that if you initially uploaded an .ass file with subs to adjust, you will get a final .ass file with the original header of the uploaded subs, and every single line will retain its original styles but with adjusted timing.  

Values you can modify: None.


Fase6.py:  
- Delete files that are no longer needed after adjusting the sub timing.
- Move the files you need to the Desktop.
- You’ll be asked whether you want to merge "On top.ass/.srt," "Comments.ass" and "Signs.ass" into the final file. If you choose not to merge them, the separate files will also be moved to the desktop.

Values you can modify: None.

