# audio2vmd Documentation/Wiki

## Table of Contents
1. [Introduction](#introduction)
2. [Usage](#usage)
3. [Usage (command-line)](#usage_cli)
#### Code Wiki
4. [Functions](#functions)
   - [extract_vocals](#extract_vocals)
   - [get_audio_duration](#get_audio_duration)
   - [analyze_audio_for_vocals](#analyze_audio_for_vocals)
   - [detect_audio_format](#detect_audio_format)
   - [convert_audio_to_wav](#convert_audio_to_wav)
   - [load_config](#load_config)
   - [print_config](#print_config)
   - [split_audio](#split_audio)
   - [detect_silence](#detect_silence)
   - [db_to_float](#db_to_float)
   - [batch_process](#batch_process)
   - [adjust_vowel_weights](#adjust_vowel_weights)
   - [audio_to_vmd](#audio_to_vmd)
   - [sanitize_directory_path](#sanitize_directory_path)
5. [Classes](#classes)
   - [VMDMorphFrame](#vmdmorphframe)
   - [VMDFile](#vmdfile)
   - [CommentedConfig](#commentedconfig)


## Introduction

The `audio2vmd.py` script is designed to convert audio files into VMD (Vocaloid Motion Data) files for lip-syncing in 3D animation software. It processes audio to detect vowel sounds and generates corresponding mouth movements.

## Usage

WIP

## Usage (command-line)

To use the script, run it from the command line with the following syntax:

```
python audio2vmd.py [input_files] [options]
```

**Options:**
- `--output`, `-o`: Output directory for VMD files (default: "output")
- `--model`, `-m`: Model name for VMD file (default: "Model")
- `--config`, `-c`: Path to configuration file (default: "config.yaml")

**Examples:**
```
python audio2vmd.py input.mp3
python audio2vmd.py input1.mp3 input2.wav --output my_output --model 'My Model'
python audio2vmd.py input_directory --output output_directory
```

For more detailed usage instructions, run:
```
python audio2vmd.py --help
```

## Functions

### extract_vocals

```python
def extract_vocals(audio_path, wav_path)
```

Extracts vocals from an audio file using the Spleeter library.

**Parameters:**
- `audio_path` (str): Path to the input audio file.
- `wav_path` (str): Path where the extracted vocals will be saved as a WAV file.

**Returns:**
- str: Path to the saved WAV file containing extracted vocals.

**Notes:**
- Uses the Spleeter library with a "2stems" separator.
- Creates necessary directories if they don't exist.

### get_audio_duration

```python
def get_audio_duration(audio_path, return_as_text=False)
```

Get the duration of an audio file.

**Parameters:**
- `audio_path` (str): Path to the audio file.
- `return_as_text` (bool): If True, returns the duration formatted as a readable string.

**Returns:**
- float or str: Duration of the audio file in seconds, or a formatted string if return_as_text is True.

**Notes:**
- Uses the pydub library to load and analyze the audio file.
- When `return_as_text` is True, it formats the duration as "X Hours, Y Minutes, Z Seconds".

### analyze_audio_for_vocals

```python
def analyze_audio_for_vocals(audio_path)
```

Analyzes an audio file to detect the presence of vocals and determine if it's a vocals-only file.

**Parameters:**
- `audio_path` (str): Path to the audio file to analyze.

**Returns:**
- tuple: (has_vocals, is_vocals_only)
  - `has_vocals` (bool): True if significant vocals are detected in the audio.
  - `is_vocals_only` (bool): True if the audio contains only vocals with minimal accompaniment.

**Notes:**
- Uses the Spleeter library to separate vocals and accompaniment.
- Adjusts thresholds for vocal detection and vocals-only classification.

### detect_audio_format

```python
def detect_audio_format(audio_path)
```

Detects the format of an audio file.

**Parameters:**
- `audio_path` (str): Path to the audio file.

**Returns:**
- str: The detected audio format (e.g., "mp3", "wav").

**Notes:**
- Uses pydub to detect the format.
- Falls back to checking file extension if pydub fails.

### convert_audio_to_wav

```python
def convert_audio_to_wav(audio_path, output_wav_path)
```

Converts an audio file to WAV format.

**Parameters:**
- `audio_path` (str): Path to the input audio file.
- `output_wav_path` (str): Path where the converted WAV file will be saved.

**Notes:**
- Ensures the output file has a ".wav" extension.
- Creates necessary directories if they don't exist.
- Uses pydub for audio conversion.

### load_config

```python
def load_config(config_file='config.yaml')
```

Loads configuration from a YAML file or creates a default configuration if the file doesn't exist.

**Parameters:**
- `config_file` (str): Path to the configuration file. Default is 'config.yaml'.

**Returns:**
- dict: Loaded configuration or default configuration.

**Notes:**
- Creates a default configuration file if it doesn't exist.
- Uses PyYAML for YAML parsing.

### print_config

```python
def print_config(config)
```

Prints the current configuration to the console.

**Parameters:**
- `config` (dict): Configuration dictionary to print.

### split_audio

```python
def split_audio(audio_path, output_dir="", max_duration=300, silence_threshold=-40, min_silence_length=300)
```

Split an audio file into multiple parts, each not exceeding a specified maximum duration.

**Parameters:**
- `audio_path` (str): Path to the input audio file.
- `output_dir` (str): Directory to save the split audio parts. If empty, uses the same directory as the input file.
- `max_duration` (int): Maximum duration of each part in seconds. Default is 300 (5 minutes).
- `silence_threshold` (int): The threshold (in dB) below which to consider as silence. Default is -40.
- `min_silence_length` (int): Minimum length of silence to be considered for splitting, in milliseconds. Default is 300 (0.3 seconds).

**Returns:**
- list: A list of file paths to the split audio parts.

**Notes:**
- Attempts to split the audio at silent points to avoid cutting during speech.
- Searches backwards from the max_duration point to find a suitable silence for splitting.
- If no silence is found, it will split at the max_duration point.
- The function will always keep the first 5 seconds of each segment intact and will not split within this period.
- Adjust silence_threshold and min_silence_length to fine-tune silence detection for your specific audio.
- Uses the pydub library to handle audio processing.

**Example usage:**
```python
split_audio("path/to/audio.mp3", output_dir="path/to/output", max_duration=300, silence_threshold=-45, min_silence_length=500)
```

### detect_silence

```python
def detect_silence(audio_segment, min_silence_len=1000, silence_thresh=-40, seek_step=1)
```

Detects silent sections in an audio segment.

**Parameters:**
- `audio_segment` (AudioSegment): The audio segment to analyze.
- `min_silence_len` (int): Minimum length of silence (in ms) to be detected. Default is 1000ms.
- `silence_thresh` (int): The threshold (in dB) below which to consider as silence. Default is -40dB.
- `seek_step` (int): Step size for seeking through the audio. Default is 1.

**Returns:**
- list: A list of [start, end] pairs in milliseconds indicating silent sections.

### db_to_float

```python
def db_to_float(db, using_amplitude=True)
```

Converts decibels to float values.

**Parameters:**
- `db` (float): The decibel value to convert.
- `using_amplitude` (bool): If True, converts amplitude dB. If False, converts power dB. Default is True.

**Returns:**
- float: The converted value.

### batch_process

```python
def batch_process(input_files, output_dir, model_name, config)
```

Processes multiple audio files and generates VMD files.

**Parameters:**
- `input_files` (list): List of input audio file paths.
- `output_dir` (str): Directory to save the output VMD files.
- `model_name` (str): Name of the model for the VMD file.
- `config` (dict): Configuration dictionary.

**Notes:**
- Uses tqdm for progress tracking.
- Splits audio files if necessary and processes each part.

### adjust_vowel_weights

```python
def adjust_vowel_weights(weights, config)
```

Adjusts vowel weights for more natural mouth movements using configuration values.

**Parameters:**
- `weights` (dict): Dictionary of vowel weights.
- `config` (dict): Configuration dictionary with weight multipliers.

**Returns:**
- dict: Adjusted vowel weights.

### audio_to_vmd

```python
def audio_to_vmd(input_audio, vmd_file, model_name, config)
```

Converts an audio file to a VMD (Vocaloid Motion Data) file for lip-syncing.

**Parameters:**
- `input_audio` (str): Path to the input audio file.
- `vmd_file` (str): Path where the output VMD file will be saved.
- `model_name` (str): Name of the model for the VMD file.
- `config` (dict): Configuration dictionary.

**Notes:**
- Extracts vocals if necessary.
- Converts audio to WAV format if needed.
- Processes audio to detect vowel sounds and generate corresponding mouth movements.
- Optimizes VMD data before saving.

### sanitize_directory_path

```python
def sanitize_directory_path(path)
```

Sanitizes a directory path by removing invalid characters.

**Parameters:**
- `path` (str): The directory path to sanitize.

**Returns:**
- str: The sanitized directory path.

## Classes

### VMDMorphFrame

Represents a morph frame in the VMD file format.

**Attributes:**
- `name` (str): Name of the morph.
- `frame` (int): Frame number.
- `weight` (float): Weight of the morph.

**Methods:**
- `to_bytes()`: Converts the frame data to bytes for file writing.

### VMDFile

Represents a VMD (Vocaloid Motion Data) file.

**Attributes:**
- `model_name` (str): Name of the model.
- `morph_frames` (list): List of VMDMorphFrame objects.

**Methods:**
- `add_morph_frame(name, frame, weight)`: Adds a new morph frame to the file.
- `save(filename)`: Saves the VMD data to a file.

### CommentedConfig

A subclass of OrderedDict that allows adding comments to configuration items.

**Methods:**
- `__setitem__(key, value)`: Sets an item with an optional comment.
- `items()`: Returns items with their comments.


