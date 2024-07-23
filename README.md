# audio2vmd
Completely automatically convert audio to vmd lips data using python cmd/automatic batch-file, with automatic vocals extraction. Using this, you can make your MMD models lip-sync to any song or speech audio. **(wip, please check back in a few days)**

# Features
- **Automatic Audio to VMD conversion**
  - Automatically creates a lip-synced VMD for MikuMikuDance/MikuMikuMoving from a audio file
- **One-click installer**
  - One-click installer batch file to install audio2vmd on your computer (may need more development)
- **Optional GUI**
  - Simple GUI interface to select audio files, change the settings of the config file, and run conversions. 
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
 
# Installing audio2vmd
## Install automatically using 1-click installer batch file
1) Download and install [Python](https://www.python.org/downloads/windows/)
2) Download latest version of [audio2vmd](https://github.com/EliseWindbloom/audio2vmd/archive/refs/heads/main.zip)
3) Unzip audio2vmd and run "install.bat" to install automatically, this may take awhile to download all required files.

## Manually install
`wip`

# Usage
You have two choices on how to use it:
  - drag & drop audio files into the "Audio to VMD" bat file to convert them to lipsynced vmd files. Will also accept mp4/mkv video files.
  - double click on "Audio to VMD" bat file to launch the GUI where you can easily select audio files, run batch conversions and change settings. Will also accept mp4/mkv video files.
 
## Planned features
- Possibly a window binary exe file for ease of use (I will have to research how to do this first though)
 
## Credits
Nawota for the c# Lipsync plugin that this project is loosely based on.

This repository was first inspired by the original automatic lipsync guide by [Vayanis](https://www.youtube.com/watch?v=ozKBYGiyPJE)

[Parse VMD in python guide by crossous](https://www.jianshu.com/p/ae312fb53fc3)

[nuekaze](https://github.com/nuekaze/VMD-motion-extract/tree/master) for unpacking/repacking VMD python code (though as csv format)

[VMD file format wiki](https://mikumikudance.fandom.com/wiki/VMD_file_format)
