![1](https://github.com/user-attachments/assets/abe9cbd1-610c-456b-a499-bc4a923d0a54)

What exactly do the scripts do? 

Do you want to change the values ​​to your preferences? 
[Read here](Scripts/Migliora%20il%20Timing%20Dei%20Sub/README.md)

If you have an NVIDIA GPU and plan to use it:
- Open "Auto Sub ReTimer GUI.bat" with Notepad (right-click > Edit).
- Locate the part of the file where it says "cu118".
- Change "cu118" to match the CUDA version supported by your GPU.

![2](https://github.com/user-attachments/assets/5140eb44-28cf-4d8a-8894-e9cad96fc4a7)

Tip: If you're unsure about your CUDA version, open a terminal (cmd) and type "nvidia-smi" to check it (you don’t necessarily have to use a recent CUDA version, you can also use an older one for better compatibility. The important thing is that it is compatible with your NVIDIA card).

- Save and you're done!

- Put your video .mkv inside the "Auto Sub ReTimer" folder.

Example:

![3](https://github.com/user-attachments/assets/b76a80e6-4d72-4d4f-84fb-6fb1c611fbf2)

- Run "Auto Sub ReTimer GUI.bat".

 - Now...                                         
    THE LINE OF SPOKEN AUDIO IN THE SUB MUST BE WITHIN THE LINES AND NOT PARTIALLY OUTSIDE THE LINE       
    (Audio Spectrum).                                                                           
    THERE MUST NOT BE THE START OF SPOKEN AUDIO THAT BEGINS BEFORE THE LINE, FOR EXAMPLE.       
    WHEN UPLOADING YOUR .ASS OR .SRT, MAKE SURE TO FOLLOW THE INSTRUCTIONS.                     
    EVEN A QUICK SYNC THAT'S THE SAME FOR ALL LINES IS SUFFICIENT.                              
    FOR EXAMPLE -0.050 OR -0.100. WITH VALUES TOO HIGH YOU WILL GET THE OPPOSITE EFFECT.               

Does not meet the requirements:

![Does not meet the requirements](https://github.com/user-attachments/assets/5e963886-c763-4511-a35a-716d4dba95cb)

Meets the requirements (It is not necessary for the initial timestamp to perfectly align with the beginning of the audio peak of the speech, the important thing is that the beginning of the speech is included, the rest will be handled by the program):

![Meets the requirements](https://github.com/user-attachments/assets/faace722-7cc3-400f-944a-2be206f7c0e6)

(If the process were to stop for any reason, delete the previously created files from the program to avoid conflicts)

Before and after examples Auto Sub ReTimer:

Example 1 Original Sub:

![Original](https://github.com/user-attachments/assets/7953eb46-e2ed-49ff-b1b0-3c997a78c0f5)
![Original](https://github.com/user-attachments/assets/5e3d6209-8601-4ecd-a9e7-ebd7289b724a)

Adjusted Sub with scene change:

![Adjusted](https://github.com/user-attachments/assets/780d6aa0-d7bc-4ee8-865d-38849dd6d892)
![Adjusted](https://github.com/user-attachments/assets/516aff27-5ab5-4e00-a75c-7ac88594b317)

Example 2 Original Sub:

![Original](https://github.com/user-attachments/assets/ed23556d-9766-44eb-a9cb-a20742c9e0ed)

Adjusted Sub:

![Adjusted](https://github.com/user-attachments/assets/30a422b8-e8f1-4351-a632-01f6c41efbad)

Example 3 Original Sub:

![Original](https://github.com/user-attachments/assets/abcb7e51-974e-4cf8-8ba4-0310459c13ed)

Adjusted Sub with scene change:

![Adjusted](https://github.com/user-attachments/assets/b2fc1fa4-83c5-4b2e-9596-63e3d9408b57)

-------------------------------------------------------------------------------------------------

To use whisper.

REQUIREMENTS

- Put your video .mkv inside the "Auto Sub ReTimer" folder.

- Run "Auto Sub ReTimer GUI.bat" and use "Whisper".

- To improve the timing of "whisper.srt" you will need to use "Whisper ReTimer".
 - You will have two options: use only a basic timing improvement or ensure it also respects scene changes.
  - Once you have made your choice and the process is complete, you will find everything you need on the desktop.
   (Keep in mind that the improvement with scene changes is not perfect, especially if used with the basic timing of whisper).
