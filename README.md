# audio2vmd
Completely automatically convert audio to vmd lips data using python cmd/automatic batch-file, with automatic vocals extraction. Using this, you can make your MMD models lip-sync to any song or speech audio. **(wip, please check back in a few days)**

# Features
- **Automatic Audio to VMD conversion**
  - Automatically creates a lip-synced VMD for MikuMikuDance/MikuMikuMoving from a audio file
- **Audio file types**
  - Likely accepts all major audio file types for conversion. Will automatically convert them into wav files for this program and for MMD uses.
- **Audio extraction from videos**
  - Can also accept video files such as mp4 or mkv as input, and will automatically extract the audio from them for conversion. 
- **Voice detection and seperation**
  - Automatically detects vocals from songs/background sounds and seperates the vocals to a wav file before conversion
- **Spilting long audio**
  - Automatically splits audio if it's longer than 5 mintues, while also avoiding to cut audio in the middle of talking. This allows you to not worry about the 20,000 frames limit of MMD.
- **Optimized lips frames**
  - Automatically calulate and delete unneeded frames to make the filesize much smaller and allow you to load longer files into MMD.
- **Batch Processing**
  - Can accept multiple audio files at once and convert them all each to a different vmd file.
- **Config file**
  - Simple config file allows you to change settings. Currently you can change the effect of the amount for each vowel (A, I, O, U) to make talking much more pronounced.
- **Ready for MMD**
  - Will automatically convert audio to wav format if it isn't in wav already, this will be paired with the VMD, and ready to launch with MMD/MMM.(This won't move/delete your original audio)
 
## Planned features
- Drag-and-drop audio to batch file to automatically convert it to a lipsynced vmd (it will follow any settings in the config file). 
- One-click installer batch file to install on your computer (hopefully though, I'm still learning about python environments)
- Optional Simple GUI interface to select audio files and change the settings of the config file.
- Possibly a window binary exe file for ease of use (I will have to research how to do this first though)
 
