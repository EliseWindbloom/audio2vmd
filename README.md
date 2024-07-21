# audio2vmd
Completely automatically convert audio to vmd lips data using python cmd/automatic batch-file, with automatic vocals extraction **(wip, please check back in a few days)**

## Features
- Automatic Audio to VMD conversion
  - Automatically creates a lip-synced VMD for MikuMikuDance/MikuMikuMoving from a audio file
- Voice detection and seperation
  - Automatically detects vocals from songs/background sounds and seperates the vocals to a wav file before conversion
- Spilting long audio
  - Automatically splits audio if it's longer 5 mintues, while also avoiding to cut audio in the middle of talking. This allows you to not worry about the 20,000 frames limit of MMD.
- Optimized lips frames
  - Automatically calulate and delete unneeded frames to make filesize much smaller and allow you to load longer files into MMD.
- Batch Processing
  - Can accept multiple audio files at once and convert them all each to a vmd file.
- Config file
  - Simple config file allows you to change settings. Currently you can change the effect of the amount for each vowel (A, I, O, U) to make talking much more pronounced.
 
