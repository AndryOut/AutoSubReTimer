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
- Extracts audio from "ep.mkv", passes it to demucs which extracts vocals with the CPU (3/5 minutes) or with GPU (30/40 seconds).
- Now there is no need to use the site anymore, it does everything automatically locally, make sure you have the right cuda version installed for you in the "main" folder to use GPU.

Values you can modify: None.

Fase2.py:  
- Based on the audio peaks of spoken audio, removes the lead-in-out and resets them according to values that can be changed as per your preference.  
- Joins close lines with a space of 0.000 seconds between them for better continuity.  

Values you can modify: 4.  

Value 1 "Peak detection margin after initial timestamp (ms)":  

![1](https://github.com/user-attachments/assets/4f44dde5-b04e-4318-b9c4-b7a7925b38dc)

"200" Changing this value ensures that the detection of the first audio peak of the spoken audio after the line start is identified with more margin.  

Example with 200 milliseconds:  

![Fase2 1 200](https://github.com/user-attachments/assets/d690943a-c353-41cf-8462-16208599f29d)

Here, the value 200 is more than enough to detect the first audio peak after the line's initial timestamp.  
The distance from the first arrow (line's initial timestamp) to the second arrow (first audio peak) falls within the 200-millisecond range.  
If the distance of the audio peak is farther from the line's initial timestamp, you can increase this value.  

What issues might arise if this value is set too high?  
In some cases, if the audio peak is not detected correctly, it may use the next audio peak (as it has more margin), resulting in a line with a part of the spoken audio cut off.

Value 2 "Peak detection margin before final timestamp (ms)":  

![1](https://github.com/user-attachments/assets/866a6f7b-59ec-4ed6-b28b-ba44c519c589)

"600" Changing these values ensures that the detection of the first audio peak of the spoken audio before the line end is identified with more margin.  

Example with 600 milliseconds:  

![Fase2 2 600](https://github.com/user-attachments/assets/73264ebd-2543-4a74-885d-3c2208446b8a)

Here, the value 600 is more than enough to detect the first audio peak before the line's final timestamp.  
The distance from the first arrow (first audio peak) to the second arrow (line's final timestamp) falls within the 600-millisecond range.  
If the distance of the audio peak is farther from the line's final timestamp, you can increase this value.  

What issues might arise if this value is set too high?  
In some cases, if the audio peak is not detected correctly, it may use the previous audio peak (as it has more margin), resulting in a line with a part of the spoken audio cut off.

Value 3-4 "Add Lead-in" - "Add Lead-out":  

![1](https://github.com/user-attachments/assets/11e89b62-b6a7-43ec-8663-eb7ae2ab9c7c)

You can modify the lead-in and lead-out values based on your personal preference.  

What issues might arise if this value is set too high?  
(A common issue is that audio peaks may not be detected correctly, so lead is added anyway. Keep these values not too high.)

Fase3.py:  
- Detects scene changes and saves them in a .srt file, which will then be used by "Fase4.py".  

Values you can modify: None.

Fase4.py:  
- Ensures that lines respect scene changes where possible.  
(It may cut a part of the spoken audio if "Fase3" has detected nonexistent scene changes.)  
- Adds lead-in to lines with low CPM adjusted to a scene change to prevent the line from lasting too short on-screen.  
- Joins lines with 0.000 seconds if there is a gap of silence between lines within a range of 0.300 seconds.  

Values you can modify: 4.  

Value 1 "Max range to detect a scene change from the final timestamp (ms)":  

![fase4](https://github.com/user-attachments/assets/e614e08e-89ee-4bec-85e0-7a082e41e708)

Changing this value gives more margin to detect a scene change occurring after the line's final timestamp.  
(If you set this value too high, it may result in lines being extended too much as lead-out to adjust to a scene change. )

(Keep in mind that this value is linked to the lead-out of "Fase2". So if you have set "500" in lead-out, the "300" range will check if there are scene changes after "500" of lead out, this means that if it finds a scene change, you will have a line that from the final audio peak will be a hypothetical 800 ms in lead-out until the detected scene change (500 ± 300).

Value 2 "Max gap 'empty' between two lines to attach (ms)":

![fase4](https://github.com/user-attachments/assets/6d424b8a-aad4-4856-8f07-d2cdf717e37e)

This setting allows you to configure the threshold for deciding how much "empty" space there must be to merge two subtitle lines. Merging the lines improves fluidity between them. If you leave it at 230, the lines won’t stretch too much to attach to the next line, but there will be a natural "break" based on the fluidity of the speech. (This is obviously a personal preference, but you can now adjust the threshold to your liking).

Value 3 "Max range to detect scene change before the initial timestamp (ms):

![fase4](https://github.com/user-attachments/assets/840ae9ef-b171-4fdb-b0d5-044ac1bef798)

Allows you to set the maximum distance to detect a scene change and link it before the initial timestamp of the line.

Value 4 "Max range to detect scene change after the initial timestamp (ms):

![fase4](https://github.com/user-attachments/assets/e1cd1def-68ae-4b99-a205-214ab6c6ed44)

Allows you to set the maximum distance to detect a scene change and link it after the initial timestamp of the line.

Fase5.py:  
- Ensures that if you initially uploaded an .ass file with subs to adjust, you will get a final .ass file with the original header of the uploaded subs, and every single line will retain its original styles but with adjusted timing.  

Values you can modify: None.


Fase6.py:  
- Delete files that are no longer needed after adjusting the sub timing.
- Move the files you need to the Desktop.
- You’ll be asked whether you want to merge "On top.ass/.srt," "Comments.ass" and "Signs.ass" into the final file. If you choose not to merge them, the separate files will also be moved to the desktop.

Values you can modify: None.

