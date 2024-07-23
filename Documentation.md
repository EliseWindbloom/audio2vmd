# audio2vmd Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [Functions](#functions)
7. [Classes](#classes)

## Introduction

audio2vmd is a Python-based tool that automatically converts audio files to VMD (Vocaloid Motion Data) lip sync data for use in MikuMikuDance (MMD) or MikuMikuMoving (MMM). It can process various audio formats, extract vocals, and generate optimized lip sync data for 3D character animations.

## Features

- **Automatic Audio to VMD conversion**: Creates lip-synced VMD files from audio input.
- **One-click installer**: Easy installation via a batch file.
- **Optional GUI**: Simple interface for file selection and configuration.
- **Multiple audio format support**: Accepts various audio and video file formats.
- **Audio extraction from videos**: Can extract audio from video files for processing.
- **Voice detection and separation**: Automatically detects and separates vocals from background sounds.
- **Long audio splitting**: Splits audio files longer than 5 minutes to work within MMD's frame limit.
- **Optimized lip sync**: Calculates and removes unnecessary frames to reduce file size.
- **Batch processing**: Can process multiple audio files in one go.
- **Configurable**: Adjust vowel intensities and other settings via a config file.
- **MMD-ready output**: Converts audio to WAV format for use with the generated VMD file.

## Installation

### Automatic Installation
1. Download and install [Python](https://www.python.org/downloads/windows/).
2. Download the latest version of [audio2vmd](https://github.com/EliseWindbloom/audio2vmd/archive/refs/heads/main.zip).
3. Unzip audio2vmd and run "install.bat" to install automatically.

### Manual Installation
If you prefer manual installation, use the following commands:

```
cd audio2vmd
python -m venv venv
call venv\Scripts\activate.bat
pip install pydub==0.25.1 PyYAML==6.0.1 tqdm==4.66.4 spleeter==2.4.0
pip install spleeter==2.3.2
cd..
```

## Usage

### GUI Method
1. Double-click on "Audio to VMD" batch file to launch the GUI.
2. Select audio files, adjust settings, and run conversions.

### Drag & Drop Method
Drag and drop audio or video files onto the "Audio to VMD" batch file to convert them to VMD files.

### Command Line Usage
Activate the virtual environment and use the following syntax:

```
python audio2vmd.py [input_files] [options]
```

Options:
- `--output`, `-o`: Output directory for VMD files (default: "output")
- `--model`, `-m`: Model name for VMD file (default: "Model")
- `--config`, `-c`: Path to configuration file (default: "config.yaml")

Examples:
```
python audio2vmd.py input.mp3
python audio2vmd.py input1.mp3 input2.wav --output my_output --model 'My Model'
python audio2vmd.py input_directory --output output_directory
```

You can also provide a text file containing a list of audio file paths:
```
python audio2vmd.py list_of_audio_files.txt --output "C:\files\vmd\"
```

## Configuration

The `config.yaml` file allows you to adjust various settings:

- `a_weight_multiplier`: Intensity of the 'あ' (A) sound
- `i_weight_multiplier`: Intensity of the 'い' (I) sound
- `o_weight_multiplier`: Intensity of the 'お' (O) sound
- `u_weight_multiplier`: Intensity of the 'う' (U) sound
- `max_duration`: Maximum duration for splitting audio in seconds (0 to disable splitting)
- `optimize_vmd`: Whether to optimize the VMD file (recommended to keep as true)

## Functions

### extract_vocals(audio_path, wav_path)
Extracts vocals from an audio file using the Spleeter library.

### get_audio_duration(audio_path, return_as_text=False)
Gets the duration of an audio file.

### analyze_audio_for_vocals(audio_path)
Analyzes an audio file to detect the presence of vocals and determine if it's a vocals-only file.

### detect_audio_format(audio_path)
Detects the format of an audio file.

### convert_audio_to_wav(audio_path, output_wav_path)
Converts an audio file to WAV format.

### load_config(config_file='config.yaml')
Loads configuration from a YAML file or creates a default configuration.

### print_config(config)
Prints the current configuration to the console.

### split_audio(audio_path, output_dir="", secondary_audio_path="", original_is_wav_filetype=True, max_duration=300, silence_threshold=-60, min_silence_length=300)
Splits an audio file into multiple parts, each not exceeding a specified maximum duration.

### detect_silence(audio_segment, min_silence_len=1000, silence_thresh=-40, seek_step=1)
Detects silent sections in an audio segment.

### db_to_float(db, using_amplitude=True)
Converts decibels to float values.

### process_single_file(input_file, output_dir, model_name, config)
Processes a single audio file to generate VMD data.

### batch_process(input_files, output_dir, model_name, config, global_start_time, item_start_time, audio_source_files_count=1)
Processes multiple audio files in batch.

### adjust_vowel_weights(weights, config)
Adjusts vowel weights for more natural mouth movements using config values.

### audio_to_vmd(input_audio, vmd_file, model_name, config)
Converts an audio file to VMD file format.

### get_file_extension(filepath)
Returns the file extension of the given filepath.

### sanitize_directory_path(path)
Sanitizes a directory path by removing invalid characters.

## Classes

### VMDMorphFrame
Represents a morph frame in the VMD file format.

#### Attributes:
- `name`: Name of the morph
- `frame`: Frame number
- `weight`: Weight of the morph

#### Methods:
- `to_bytes()`: Converts the frame data to bytes for file writing

### VMDFile
Represents a VMD (Vocaloid Motion Data) file.

#### Attributes:
- `model_name`: Name of the model
- `morph_frames`: List of VMDMorphFrame objects

#### Methods:
- `add_morph_frame(name, frame, weight)`: Adds a new morph frame to the file
- `save(filename)`: Saves the VMD data to a file

### CommentedConfig
A subclass of OrderedDict that allows adding comments to configuration items.

#### Methods:
- `__setitem__(key, value)`: Sets an item with an optional comment
- `items()`: Returns items with their comments

This documentation provides a comprehensive overview of the audio2vmd tool, its features, installation process, usage instructions, and detailed explanations of its functions and classes. Users can refer to this document for guidance on how to use and customize the tool for their lip-syncing needs in MMD or MMM projects.
