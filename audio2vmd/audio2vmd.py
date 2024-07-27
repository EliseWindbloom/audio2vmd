#=======================================
# audio2vmd version 12.1
# This script automatically converts a audio file to a vmd lips data file
#=======================================
# Created by Elise Windbloom
# Loosely based on original c# Lipsyncloid plugin for MMM by Nawota 
# Inspired by original lipsync video guide by Vayanis
import os
import sys
import time
import struct
import pathlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from spleeter.separator import Separator
from spleeter.audio.adapter import AudioAdapter
from pydub import AudioSegment
import yaml
from collections import OrderedDict
import argparse
from tqdm import tqdm
import string
import json
import subprocess
import logging
import tensorflow as tf
import traceback
import shlex
from pathlib import Path
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Set TensorFlow logging level to only show fatal errors
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# # Set up the logging configuration
logging.basicConfig(level=logging.FATAL)

# # Optional: further configuration to suppress warnings from other libraries
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Define VMD data structures
class VMDMorphFrame:
    def __init__(self, name, frame, weight):
        self.name = name
        self.frame = frame
        self.weight = weight

    def to_bytes(self):
        return (
            self.name.encode('shift-jis').ljust(15, b'\0') +
            struct.pack('<I', self.frame) +
            struct.pack('<f', self.weight)
        )


class VMDFile:
    def __init__(self, model_name=""):
        self.model_name = model_name
        self.header = b'Vocaloid Motion Data 0002\0\0\0\0\0'
        self.bone_frames = []
        self.morph_frames = []
        self.camera_frames = []
        self.light_frames = []
        self.shadow_frames = []

    def load(self, filename):
        #print(f"---load vmd filename = {filename}")
        with open(filename, 'rb') as f:
            data = f.read()

        # Read header
        self.header = data[:30]
        #if self.header != b'Vocaloid Motion Data 0002\0\0\0\0\0':
        if self.header.startswith(b"Vocaloid Motion Data 0002") == False and self.header.startswith(b"Vocaloid Motion Data file") == False:
            raise ValueError(f"Invalid VMD file header - <{self.header}>")
        
        # Read model name
        self.model_name = data[30:50].split(b'\0')[0].decode('shift-jis', errors='ignore')

        offset = 50
        # Read bone frames
        bone_count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        self.bone_frames = []
        for _ in range(bone_count):
            bone_frame = {
                'name': data[offset:offset+15].split(b'\0')[0].decode('shift-jis', errors='ignore'),
                'frame': struct.unpack('<I', data[offset+15:offset+19])[0],
                'position': struct.unpack('<fff', data[offset+19:offset+31]),
                'rotation': struct.unpack('<ffff', data[offset+31:offset+47]),
                'interpolation': data[offset+47:offset+111]
            }
            self.bone_frames.append(bone_frame)
            offset += 111

        # Read morph frames
        morph_count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        self.morph_frames = []
        for _ in range(morph_count):
            morph_frame = VMDMorphFrame(
                data[offset:offset+15].split(b'\0')[0].decode('shift-jis', errors='ignore'),
                struct.unpack('<I', data[offset+15:offset+19])[0],
                struct.unpack('<f', data[offset+19:offset+23])[0]
            )
            self.morph_frames.append(morph_frame)
            offset += 23

        # Read camera frames
        camera_count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        self.camera_frames = [data[offset+i*61:offset+(i+1)*61] for i in range(camera_count)]
        offset += camera_count * 61

        # Read light frames
        light_count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        self.light_frames = [data[offset+i*28:offset+(i+1)*28] for i in range(light_count)]
        offset += light_count * 28

        # Read shadow frames (if present)
        if offset < len(data):
            shadow_count = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            self.shadow_frames = [data[offset+i*9:offset+(i+1)*9] for i in range(shadow_count)]

    def save(self, filename):
        with open(filename, 'wb') as f:
            # Write header
            f.write(self.header)

            # Write model name
            f.write(self.model_name.encode('shift-jis').ljust(20, b'\0'))

            # Write bone frames
            f.write(struct.pack('<I', len(self.bone_frames)))
            for bone in self.bone_frames:
                f.write(bone['name'].encode('shift-jis').ljust(15, b'\0'))
                f.write(struct.pack('<I', bone['frame']))
                f.write(struct.pack('<fff', *bone['position']))
                f.write(struct.pack('<ffff', *bone['rotation']))
                f.write(bone['interpolation'])

            # Write morph frames
            f.write(struct.pack('<I', len(self.morph_frames)))
            for morph in self.morph_frames:
                f.write(morph.to_bytes())

            # Write camera frames
            f.write(struct.pack('<I', len(self.camera_frames)))
            for camera in self.camera_frames:
                f.write(camera)

            # Write light frames
            f.write(struct.pack('<I', len(self.light_frames)))
            for light in self.light_frames:
                f.write(light)

            # Write shadow frames
            f.write(struct.pack('<I', len(self.shadow_frames)))
            for shadow in self.shadow_frames:
                f.write(shadow)

    def add_morph_frame(self, name, frame, weight):
        self.morph_frames.append(VMDMorphFrame(name, frame, weight))

    def get_morph_frames(self):
        return self.morph_frames

# this is use to help set up a yaml that is easy to add comments to from this python script
class CommentedConfig(OrderedDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.comments = {}

    def __setitem__(self, key, value):
        if isinstance(value, tuple) and len(value) == 2:
            super().__setitem__(key, value[0])
            self.comments[key] = value[1]
        else:
            super().__setitem__(key, value)

    def items(self):
        for key in self:
            yield key, (self[key], self.comments.get(key, ''))

def optimize_vmd_data(vmd):
    """Optimize VMD data by removing unnecessary frames"""
    def is_keyframe(v1, v2, v3):
        return (v1 > v2 and v1 > v3) or (v1 < v2 and v1 < v3) or \
               (v1 == 0 and (v2 != 0 or v3 != 0)) or (v1 == 1 and (v2 != 1 or v3 != 1)) or \
               (v1 < 0.0099 and ((v2 > 0.0099 and v2 > v1) or (v3 > 0.0099 and v3 > v1)))

    optimized_frames = []
    vowel_frames = {vowel: [] for vowel in 'あいうお'}

    for frame in vmd.morph_frames:
        if frame.name in vowel_frames:
            vowel_frames[frame.name].append(frame)
        else:
            optimized_frames.append(frame)

    for frames in vowel_frames.values():
        optimized_frames.extend(frames[:2])
        optimized_frames.extend(frames[-2:])
        for i in range(2, len(frames) - 2):
            if not all(f.weight == 0 for f in frames[i-1:i+2]) and \
               is_keyframe(frames[i].weight, frames[i-1].weight, frames[i+1].weight):
                optimized_frames.append(frames[i])

    vmd.morph_frames = sorted(optimized_frames, key=lambda f: f.frame)

def optimize_vmd_bones_and_morphs(vmd, position_tolerance=0.01, rotation_tolerance=0.01):
    # Safe Range for bone position/rotation tolerance: 0.001 to 0.01
    # Explanation: A tolerance of 0.001 ensures very high fidelity, but it might not reduce the file size significantly. Increasing it to 0.01 can still maintain acceptable visual quality while allowing more keyframes to be removed.

    def is_keyframe(v1, v2, v3):
        return (v1 > v2 and v1 > v3) or (v1 < v2 and v1 < v3) or \
               (v1 == 0 and (v2 != 0 or v3 != 0)) or (v1 == 1 and (v2 != 1 or v3 != 1)) or \
               (v1 < 0.0099 and ((v2 > 0.0099 and v2 > v1) or (v3 > 0.0099 and v3 > v1)))

    def interpolate(v1, v2, t):
        return v1 * (1 - t) + v2 * t

    def is_interpolated_keyframe(frame1, frame2, frame3):
        t = (frame2['frame'] - frame1['frame']) / (frame3['frame'] - frame1['frame'])
        interpolated_pos = [interpolate(frame1['position'][i], frame3['position'][i], t) for i in range(3)]
        interpolated_rot = [interpolate(frame1['rotation'][i], frame3['rotation'][i], t) for i in range(4)]
        return not (all(abs(frame2['position'][i] - interpolated_pos[i]) < position_tolerance for i in range(3)) and
                    all(abs(frame2['rotation'][i] - interpolated_rot[i]) < rotation_tolerance for i in range(4)))

    optimized_bone_frames = []
    optimized_morph_frames = []

    # Optimize bone frames
    for bone_name in set(frame['name'] for frame in vmd.bone_frames):
        bone_frames = sorted([f for f in vmd.bone_frames if f['name'] == bone_name], key=lambda x: x['frame'])
        optimized_bone_frames.extend(bone_frames[:2])
        optimized_bone_frames.extend(bone_frames[-2:])
        for i in range(2, len(bone_frames) - 2):
            if is_keyframe(bone_frames[i]['position'][0], bone_frames[i-1]['position'][0], bone_frames[i+1]['position'][0]) or \
               is_keyframe(bone_frames[i]['position'][1], bone_frames[i-1]['position'][1], bone_frames[i+1]['position'][1]) or \
               is_keyframe(bone_frames[i]['position'][2], bone_frames[i-1]['position'][2], bone_frames[i+1]['position'][2]) or \
               is_keyframe(bone_frames[i]['rotation'][0], bone_frames[i-1]['rotation'][0], bone_frames[i+1]['rotation'][0]) or \
               is_keyframe(bone_frames[i]['rotation'][1], bone_frames[i-1]['rotation'][1], bone_frames[i+1]['rotation'][1]) or \
               is_keyframe(bone_frames[i]['rotation'][2], bone_frames[i-1]['rotation'][2], bone_frames[i+1]['rotation'][2]) or \
               is_keyframe(bone_frames[i]['rotation'][3], bone_frames[i-1]['rotation'][3], bone_frames[i+1]['rotation'][3]) or \
               is_interpolated_keyframe(bone_frames[i-1], bone_frames[i], bone_frames[i+1]):
                optimized_bone_frames.append(bone_frames[i])

    # Optimize morph frames
    for morph_name in set(frame.name for frame in vmd.morph_frames):
        morph_frames = sorted([f for f in vmd.morph_frames if f.name == morph_name], key=lambda x: x.frame)
        optimized_morph_frames.extend(morph_frames[:2])
        optimized_morph_frames.extend(morph_frames[-2:])
        for i in range(2, len(morph_frames) - 2):
            if is_keyframe(morph_frames[i].weight, morph_frames[i-1].weight, morph_frames[i+1].weight):
                optimized_morph_frames.append(morph_frames[i])

    vmd.bone_frames = sorted(optimized_bone_frames, key=lambda x: x['frame'])
    vmd.morph_frames = sorted(optimized_morph_frames, key=lambda x: x.frame)

def replace_mouth_frames(source_vmd_path, target_vmd_path, new_vmd_save_path, replace_mode="AIOU"):
    #print(f"-prepaing to save mouth source_vmd_path=<{source_vmd_path}>")
    #print(f"-target_vmd_path=<{target_vmd_path}> new_vmd_save_path=<{new_vmd_save_path}> replace_all={replace_all}")

    # Read the VMD files
    target_vmd = VMDFile()
    target_vmd.load(target_vmd_path)
    source_vmd = VMDFile()
    source_vmd.load(source_vmd_path)
    # List of all mouth morphs
    mouth_morphs = [
        'あ', 'い', 'う', 'え', 'お', 'あ２', 'ん', '▲', '∧', '□', 'ワ', 'ω', 'ω□',
        'にやり', 'にやり２', 'にっこり', 'ぺろっ', 'てへぺろ', 'てへぺろ２', '口角上げ',
        '口角下げ', '口横広げ', '歯無し上', '歯無し下'
    ] # All the general mouth morphs
    specific_mouth_morphs = ['あ', 'い', 'う', 'お'] # A, I, O, U mouths only
    
    if replace_mode == "ALL_MOUTHS":
        # Filter only mouth morphs from source_vmd
        source_morph_frames = [f for f in source_vmd.morph_frames if f.name in mouth_morphs]
    elif replace_mode == "AIOU":
        # Default specific A, I, O, U mouth morphs
        source_morph_frames = [f for f in source_vmd.morph_frames if f.name in specific_mouth_morphs]
    elif replace_mode == "ALL_FACE":
        # Replace all face morphs (eyes, mouth, brow, other)
        source_morph_frames = source_vmd.morph_frames
    else:
        raise ValueError(f"Invalid replace_mode option: {replace_mode}")
    
    if replace_mode in ["ALL_MOUTHS", "AIOU"]:
        # Remove existing mouth morphs from target_vmd
        target_morph_frames = [f for f in target_vmd.morph_frames if f.name not in mouth_morphs]
    else:
        # Remove all morphs from target_vmd
        target_morph_frames = []

    # Combine and sort the frames
    target_vmd.morph_frames = sorted(target_morph_frames + source_morph_frames, key=lambda x: x.frame)

    # Save the modified target VMD file
    target_vmd.save(new_vmd_save_path)

def format_time(seconds):
    """Format time in seconds to a human-readable string"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    else:
        minutes, secs = divmod(seconds, 60)
        return f"{int(minutes)} minutes and {secs:.2f} seconds"

def extract_vocals(audio_path, wav_path):
    audio_path = os.path.normpath(audio_path)
    wav_path = os.path.normpath(wav_path)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Specified audio file does not exist: {audio_path}")

    try:
        base_dir = str(pathlib.Path(wav_path).parent)
        process_audio_dir = base_dir

        if not os.path.exists(process_audio_dir):
            os.makedirs(process_audio_dir)

        audio_adapter = AudioAdapter.default()
        waveform, sample_rate = audio_adapter.load(audio_path)

        separator = Separator("spleeter:2stems")
        prediction = separator.separate(waveform)

        vocals = prediction["vocals"]

        # Save as WAV using Spleeter's default settings
        audio_adapter.save(wav_path, vocals, sample_rate)

        #del separator  # Clear the separator object
        #del prediction  # Clear the prediction dictionary
        #del vocals  # Clear the vocals array

        print(f"Vocals separated and saved to: {wav_path}")
        return wav_path
    except TypeError as e:
        print(f"TypeError occurred: {e}")
        raise
    except ValueError as e:
        print(f"ValueError occurred: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

def get_audio_duration(audio_path, return_as_text=False):
    """
    Get the duration of an audio file.

    Parameters:
    audio_path (str): Path to the audio file.
    return_as_text (bool): If True, returns the duration formatted as a readable string.

    Returns:
    float or str: Duration of the audio file in seconds, or a formatted string if return_as_text is True.
    """
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)
    
    # Get the duration in milliseconds
    duration_ms = len(audio)
    
    # Convert to seconds
    duration_s = duration_ms / 1000.0
    
    if return_as_text:
        # Calculate hours, minutes, and seconds
        hours = int(duration_s // 3600)
        minutes = int((duration_s % 3600) // 60)
        seconds = int(duration_s % 60)
        
        # Format the duration as a readable string
        parts = []
        if hours > 0:
            parts.append(f"{hours} Hour" + ("s" if hours > 1 else ""))
        if minutes > 0:
            parts.append(f"{minutes} Minute" + ("s" if minutes > 1 else ""))
        if seconds > 0 or not parts:  # Include seconds if no other parts
            parts.append(f"{seconds} Second" + ("s" if seconds > 1 else ""))
        
        return ", ".join(parts)
    
    return duration_s #return duration in seconds

def analyze_audio_for_vocals(audio_path):
    #check if audio has voice in it, and also if it's a vocals-only file
    separator = Separator('spleeter:2stems')
    audio_loader = AudioAdapter.default()
    waveform, _ = audio_loader.load(audio_path)
    prediction = separator.separate(waveform)
    vocals = prediction['vocals']
    accompaniment = prediction['accompaniment']
    
    vocal_energy = np.mean(np.abs(vocals))
    accompaniment_energy = np.mean(np.abs(accompaniment))
    
    # Check if there are significant vocals
    has_vocals = vocal_energy > 0.01  # Adjust this threshold as needed
    
    # Check if it's vocals-only (very low accompaniment energy compared to vocals)
    is_vocals_only = has_vocals and (accompaniment_energy < 0.1 * vocal_energy)  # Adjust this ratio as needed
    
    #del separator  # Clear the separator object reference 
    #del prediction  # Clear the prediction dictionary reference 
    #del vocals  # Clear the vocals array reference 
    #del accompaniment  # Clear the accompaniment array reference 
    return has_vocals, is_vocals_only

def detect_audio_format(audio_path):
    #get audio file format (like "mp3", "wav"...)
    try:
        audio = AudioSegment.from_file(audio_path)
        return audio.format_info
    except:
        # If pydub fails, fallback to checking file extension
        return os.path.splitext(audio_path)[1][1:].lower()

def convert_audio_to_wav(audio_path, output_wav_path):
    # --Simple fast audio convert to wav format for main script
    # --This is used when vocals don't need to be seperated but audio is not a wav
    # Ensure the output file name ends with ".wav"
    if not output_wav_path.lower().endswith(".wav"):
        output_wav_path += ".wav"
    
    # Extract the directory from the output file path, if it exists
    output_dir = os.path.dirname(output_wav_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Load the audio file
    audio = AudioSegment.from_file(audio_path)
    
    # Set the frame rate to 48kHz and sample width to 16-bit
    #audio = audio.set_frame_rate(48000).set_sample_width(2)

    # Export the audio to a WAV file
    audio.export(output_wav_path, format="wav")

    # Print confirmation message
    print(f"-Audio converted to wav format. Saved at: {output_wav_path}")

def represent_commented_config(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

yaml.add_representer(CommentedConfig, represent_commented_config)

def load_config(config_file='config.yaml'):
    """Load configuration from a YAML file."""
    print(f"Attempting to load configuration from: {config_file}")
    
    default_config = CommentedConfig()
    default_config['a_weight_multiplier'] = (1.2, "Intensity of the 'あ' (A) sound. Increase to make mouth generally open bigger.")
    default_config['i_weight_multiplier'] = (0.8, "Intensity of the 'い' (I) sound. Increase to get general extra width mouth when talking.")
    default_config['o_weight_multiplier'] = (1.1, "Intensity of the 'お' (O) sound. Increase to get more of a general wide medium circle shape.")
    default_config['u_weight_multiplier'] = (0.9, "Intensity of the 'う' (U) sound. Increase to get more general small circle-shaped mouth.")
    default_config['max_duration'] = (300, "Maximum duration for splitting audio in seconds. Set to 0 to disable splitting.")
    default_config['optimize_vmd'] = (True, "Automatically optimize the VMD file True, highly recommended to keep this true.")
    default_config['extras_optimize_vmd_bone_position_tolerance'] = (0.005, "For Optimizing a VMD (in Extras) with bone position data. Use a tolerance of 0.001 for very high fidelity, but it might not reduce the file size much.")
    default_config['extras_optimize_vmd_bone_rotation_tolerance'] = (0.005, "For Optimizing a VMD (in Extras) with bone rotation data. Use a tolerance of 0.001 for very high fidelity, but it might not reduce the file size much.")

    if os.path.exists(config_file):
        print(f"Configuration file found. Loading...")
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded_config = yaml.safe_load(f)
        if loaded_config is None:
            print("Warning: Configuration file is empty or invalid. Using default configuration.")
            loaded_config = {k: default_config[k] for k in default_config}
        print(f"Loaded configuration: {loaded_config}")
        return loaded_config
    else:
        print(f"Configuration file not found. Creating default configuration...")
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write("# Configuration file for audio2vmd\n")
            f.write("# Adjust these values to fine-tune the lip sync:\n\n")
            for key, (value, comment) in default_config.items():
                f.write(f"{key}: {value}  # {comment}\n")

        print(f"Default configuration created and saved to: {config_file}")
        return {k: default_config[k] for k in default_config}

# Add this function to your main script
def print_config(config):
    print("Current configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

def split_audio(audio_path, output_dir="", secondary_audio_path="", original_is_wav_filetype=True, max_duration=300, silence_threshold=-60, min_silence_length=300):
    """
    Split an audio file into multiple parts, each not exceeding a specified maximum duration.

    This function attempts to split the audio at silent points to avoid cutting during speech.
    It searches backwards from the max_duration point to find a suitable silence for splitting.
    If no silence is found, it will split at the max_duration point.

    Parameters:
    audio_path (str): Path to the input audio file.
    output_dir (str): Directory to save the split audio parts. If empty, uses the same directory as the input file.
    secondary_audio_path (str): Split an additional audio file.
                            However this audio file will split the exact same way as the one in audio_path.
                            This is useful for when you have full audio you want to split the same timestamps as a vocals-only audio. 
    max_duration (int): Maximum duration of each part in seconds. Default is 300 (5 minutes).
    silence_threshold (int): The threshold (in dB) below which to consider as silence. Default is -40.
                             More negative values (e.g., -50) will detect only quieter sounds as silence.
                             Less negative values (e.g., -30) will consider more sounds as silence.
    min_silence_length (int): Minimum length of silence to be considered for splitting, in milliseconds.
                              Default is 300 (0.3 seconds).
                              Increase this value if you want to split only at longer silences.


    Returns:
    list: A list of file paths to the split audio parts.

    Notes:
    - The function will always keep the first 5 seconds of each segment intact and will not split within this period.
    - If no suitable silence is found, the audio will be split at exactly the max_duration point.
    - Adjust silence_threshold and min_silence_length to fine-tune silence detection for your specific audio.
    - The function uses the pydub library to handle audio processing.

    Example usage:
    split_audio("path/to/audio.mp3", output_dir="path/to/output", max_duration=300, silence_threshold=-45, min_silence_length=500)
    """
    audio = AudioSegment.from_file(audio_path)
    if not output_dir:
        output_dir = os.path.dirname(audio_path)
    os.makedirs(output_dir, exist_ok=True)

    short_audio_needs_wav_conversion = False
    total_duration = len(audio) / 1000  # Convert to seconds
    if total_duration <= max_duration or max_duration == 0:
        if original_is_wav_filetype == False:#audio is in wrong filetype, will still run to convert to wav
            short_audio_needs_wav_conversion = True # will original audio to wav
        else:
            return [audio_path], [] #no need to split audio, already short enough

    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_files = []
    secondary_output_files = []
    start = 0
    part_num = 1

    if secondary_audio_path != "":
        secondary_audio = AudioSegment.from_file(secondary_audio_path)
        secondary_base_name = os.path.splitext(os.path.basename(secondary_audio_path))[0]

    while start < len(audio):
        end = min(start + max_duration * 1000, len(audio))
        
        if end - start < max_duration * 1000:
            # This is the last segment, just export it
            part = audio[start:end]
            if short_audio_needs_wav_conversion == False:
                output_file = os.path.join(output_dir, f"{base_name}_part{part_num}.wav")
            else:
                output_file = os.path.join(output_dir, f"{base_name}.wav")
            part.export(output_file, format="wav")
            output_files.append(output_file)

            if secondary_audio_path != "":
                secondary_part = secondary_audio[start:end]
                if short_audio_needs_wav_conversion == False:
                    secondary_output_file = os.path.join(output_dir, f"{secondary_base_name}_original_part{part_num}.wav")
                else:
                    secondary_output_file = os.path.join(output_dir, f"{secondary_base_name}_original.wav")
                secondary_part.export(secondary_output_file, format="wav")
                secondary_output_files.append(secondary_output_file)
            break

        # Search for silence in the entire segment
        segment_to_search = audio[start:end]
        silence_ranges = detect_silence(segment_to_search, 
                                        min_silence_len=min_silence_length, 
                                        silence_thresh=silence_threshold)
        
        if silence_ranges:
            # Find the silence range closest to the max_duration point
            target_time = max_duration * 1000
            closest_silence = min(silence_ranges, key=lambda x: abs(x[0] - target_time))
            split_point = start + closest_silence[0]
        else:
            # If no silence found, split at max_duration
            split_point = end

        part = audio[start:split_point]
        if short_audio_needs_wav_conversion == False:
            output_file = os.path.join(output_dir, f"{base_name}_part{part_num}.wav")
        else:
            output_file = os.path.join(output_dir, f"{base_name}.wav")
        part.export(output_file, format="wav")
        output_files.append(output_file)

        #del audio  # Clear the full audio reference after processing
        if secondary_audio_path != "":
            secondary_part = secondary_audio[start:split_point]
            if short_audio_needs_wav_conversion == False:
                secondary_output_file = os.path.join(output_dir, f"{secondary_base_name}_original_part{part_num}.wav")
            else:
                secondary_output_file = os.path.join(output_dir, f"{secondary_base_name}_original.wav")
            secondary_part.export(secondary_output_file, format="wav")
            secondary_output_files.append(secondary_output_file)
            # try:
            #     del secondary_audio # Clear the secondary audio reference after processing
            # except NameError as e:
            #     pass  # Do nothing and move on
            

        start = split_point
        part_num += 1

    return output_files, secondary_output_files

def detect_silence(audio_segment, min_silence_len=1000, silence_thresh=-40, seek_step=1):
    """
    Returns a list of all silent sections [start, end] in milliseconds of audio_segment.
    """
    seg_len = len(audio_segment)
    
    # you can't have a silent portion of a sound that is longer than the sound
    if seg_len < min_silence_len:
        return []

    # convert silence threshold to a float value (so we can compare it to rms)
    silence_thresh = db_to_float(silence_thresh) * audio_segment.max_possible_amplitude

    # find silence and add start and end indices to the to_cut list
    silence_ranges = []

    # check successive chunks of sound for silence
    # try a chunk at every "seek step" (or every chunk for a seek step == 1)
    last_slice_start = seg_len - min_silence_len
    slice_starts = range(last_slice_start, -1, -seek_step)  # Reversed range for backwards search

    for i in slice_starts:
        audio_slice = audio_segment[i:i + min_silence_len]
        if audio_slice.rms <= silence_thresh:
            silence_ranges.append([i, i + min_silence_len])

    return silence_ranges

def db_to_float(db, using_amplitude=True):
    """
    Converts the input db to a float, which represents the equivalent
    ratio in power.
    """
    db = float(db)
    if using_amplitude:
        return 10 ** (db / 20)
    else:  # using power
        return 10 ** (db / 10)

def save_progress(remaining_files, output_dir, global_start_time, audio_source_files_count):
    progress_file = os.path.join(output_dir, "batch_progress.json")
    time_and_remain = [global_start_time] + [audio_source_files_count] + remaining_files
    with open(progress_file, 'w') as f:
        json.dump(time_and_remain, f)

def load_progress(output_dir):
    progress_file = os.path.join(output_dir, "batch_progress.json")
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return None

def process_single_file(input_file, output_dir, model_name, config, send_lips_data_to):
    # This function contains the logic previously in the batch_process function,
    # but for a single file
    file_extension = get_file_extension(input_file)
    if file_extension.lower() == '.vmd':
        # Handle VMD file optimization
        output_file = os.path.join(output_dir, f"_optimized_{os.path.basename(input_file)}")
        vmd_optimized = VMDFile()
        vmd_optimized.load(input_file)# Load the VMD file
        optimize_vmd_bones_and_morphs(input_file) # Optimize the VMD file
        vmd_optimized.save(output_file)# Save the modified VMD file
        print(f"Optimized VMD file saved as: {output_file}")
        return
    input_is_wav_filetype = False
    dependent_audio_to_split = ""
    input_audio_has_vocals, input_audio_is_vocals_only = analyze_audio_for_vocals(input_file)
    if not input_audio_is_vocals_only and input_audio_has_vocals:
        vocals_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}_vocals_only.wav")
        dependent_audio_to_split = input_file
        if not os.path.exists(vocals_file):
            print(f"Extracting vocals from: {input_file}")
            extract_vocals(input_file, vocals_file)
        else:
            print(f"Using existing vocals file: {vocals_file}")
    else:
        vocals_file = input_file
    if get_file_extension(input_file).lower() == "wav":
        input_is_wav_filetype = True

    vocal_parts, full_audio_parts = split_audio(vocals_file, output_dir, dependent_audio_to_split, input_is_wav_filetype, config.get('max_duration', 300))

    for i, vocal_part in enumerate(vocal_parts):
        if len(vocal_parts)>1:
            output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}_part{i+1}.vmd")
        else:
            # only one part, file was not splitted
            output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}.vmd")
        audio_to_vmd(vocal_part, output_file, model_name, config)
        print(f"Processed part {i+1}:")
        print(f"  Vocals file: {vocal_part}")
        
        if i < len(full_audio_parts):
            full_audio_part = full_audio_parts[i]
            print(f"  Full audio file: {full_audio_part}")
        
        print(f"  VMD file: {output_file}")
    # After processing all parts
    if send_lips_data_to:
        #print(f"--send_lips_data_to = <{send_lips_data_to}>")
        if len(vocal_parts)>1:
            # Process the original unsplit audio file if the vmd file was in parts
            unsplit_vmd_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}_unsplit.vmd")
            audio_to_vmd(input_file, unsplit_vmd_file, model_name, config)
        else:
            unsplit_vmd_file = output_file
        
        # Replace mouth frames in the target VMD file
        lips_output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(send_lips_data_to))[0]}_With_Lips_From_{os.path.splitext(os.path.basename(input_file))[0]}.vmd")
        lips_output_file = trim_filename_if_needed(lips_output_file) #keeps filename from getting too long
        print(f"Sending lips data to a copy of: {send_lips_data_to}")
        replace_mouth_frames(unsplit_vmd_file, send_lips_data_to, lips_output_file, "AIOU")
        print(f"Lips data sent to: {lips_output_file}")
        if os.path.exists(unsplit_vmd_file) and unsplit_vmd_file != output_file:
            os.remove(unsplit_vmd_file) # delete unneeded vmd file

#def batch_process(input_files, output_dir, model_name, config, args):
def batch_process(input_files, output_dir, model_name, config, global_start_time, item_start_time, audio_source_files_count=1, send_lips_data_to="", show_final_complete_message=True):
    total_files = len(input_files)
    processed_files = 0
    start_time = time.time()

    for input_file in input_files:
        processed_files += 1
        print(f"\nProcessing file {processed_files} of {total_files}: {input_file}")
        
        try:
            process_single_file(input_file, output_dir, model_name, config, send_lips_data_to)
        except Exception as e:
            print(f"Error processing {input_file}: {str(e)}")
            logging.error(f"Error processing {input_file}: {str(e)}")
            continue

        elapsed_time = time.time() - start_time
        avg_time_per_file = elapsed_time / processed_files
        estimated_time_left = (total_files - processed_files) * avg_time_per_file
        
        if show_final_complete_message == True:
            print(f"Processed {processed_files}/{total_files} files")
            print(f"Elapsed time: {format_time(elapsed_time)}")
            print(f"Estimated time left: {format_time(estimated_time_left)}")

    
        if send_lips_data_to:
            print("Batch processing complete. Lips data has been sent to the specified VMD file.")
        elif show_final_complete_message == True:
            print("Batch processing complete.")

    print(f"Total time taken: {format_time(time.time() - start_time)}")

    # Restart the script if there are more files to process
    if processed_files < total_files:
        print("Restarting script to process remaining files...")
        python = sys.executable
        os.execl(python, python, *sys.argv)
    


def adjust_vowel_weights(weights, config):
    """Adjust vowel weights for more natural mouth movements using config values."""
    adjusted = weights.copy()
    adjusted['あ'] *= config['a_weight_multiplier'] if adjusted['あ'] > 0.3 else 1 # あ A
    adjusted['お'] *= config['o_weight_multiplier'] if adjusted['お'] > 0.3 else 1 # お O
    adjusted['い'] *= config['i_weight_multiplier'] # い I #GET extra width by adding to this number
    adjusted['う'] *= config['u_weight_multiplier'] # う U

    total = sum(adjusted.values())
    return {v: w / total for v, w in adjusted.items()}

def audio_to_vmd(input_audio, vmd_file, model_name, config):
    """Convert any audio file to VMD file"""
    # Extract vocals and save as a temporary WAV file
    # Create the new filename by appending "_vocals_only" before the extension
    temp_base_name, ext = os.path.splitext(os.path.basename(input_audio))
    temp_dironly = os.path.dirname(os.path.abspath(input_audio))
    temp_dironly_output = os.path.dirname(os.path.abspath(vmd_file))
    temp_wav = input_audio
    temp_vocals_only_file = ""
    
    #check if audio is already voice only
    input_audio_has_vocals, input_audio_is_vocals_only = analyze_audio_for_vocals(os.path.abspath(input_audio))
    #Prints audio duration information
    temp_duration = get_audio_duration(input_audio, True)
    print(f"Audio filename: {os.path.basename(input_audio)}")
    print(f"Audio duration: {temp_duration}")
    if not input_audio_has_vocals:
        # Didn't detect any vocals, but will still attempt to convert
        print("Warning: No vocals detected input audio file!!")
    if not input_audio_is_vocals_only and input_audio_has_vocals:
        # extracts vocals from audio file, this also converts the audio to a wav
        temp_wav = f"{temp_base_name}_vocals_only.wav"
        temp_wav_basename = temp_wav
        temp_wav = os.path.join(temp_dironly_output, temp_wav) # full path
        if not os.path.exists(temp_wav):
            print(f"-Non-vocal elements detected along with vocals in audio file, will extract vocals to wav named: {temp_wav_basename}")
            extract_vocals(input_audio, temp_wav) # saves as a vocals-only wav file
        else:
            print(f"-Non-vocal elements detected along with vocals in audio file, will use the name-matching already existing wav file instead: {temp_wav_basename}")
        temp_vocals_only_file = temp_wav # used to tell it to use voicals-only if non-wav audio is detected
    elif input_audio_has_vocals and input_audio_is_vocals_only:
        print(f"-Audio file detected as containing only vocals, so no vocal separation needed for {os.path.basename(input_audio)}")

    if detect_audio_format(os.path.abspath(input_audio)) != "wav":
        # Audio was not given as a wav, will convert to wav format needed by wav2vmd script(this is faster than vocals extraction)
        # This will create a wav even if you already a vocals-only wav. This is so you'll have a full wav file that you can load in MMD.
        temp_wav = f"{temp_base_name}.wav"
        temp_wav_basename = temp_wav
        
        temp_wav = os.path.join(temp_dironly_output, temp_wav)
        if not os.path.exists(temp_wav):
            print(f"-Audio file not in required wav format for MMD, will convert to wav named: {temp_wav_basename}")
            convert_audio_to_wav(input_audio, temp_wav)
        else:
            print(f"-Audio file not in required wav format for MMD, will use the name-matching already existing wav file instead: {temp_wav_basename}")
        if temp_vocals_only_file:
            temp_wav = temp_vocals_only_file
    else:
        print(f"-Audio file already in wav format, no conversion needed.")

    print("Converting Audio to VMD...")

    # Now process the temporary WAV file as before
    sample_rate, audio = wavfile.read(temp_wav)
    audio = np.mean(audio, axis=1) if len(audio.shape) > 1 else audio
    audio = audio / np.max(np.abs(audio))

    # Compute spectrogram
    frame_rate = 30
    window_size = int(sample_rate / frame_rate)
    f, t, Sxx = spectrogram(audio, fs=sample_rate, nperseg=window_size, noverlap=0)

    # Define vowel frequency ranges
    vowel_ranges = {
        'あ': (800, 1200),
        'い': (2300, 2700),
        'う': (300, 700),
        'お': (500, 900)
    }

    vmd = VMDFile(model_name)
    smoothing_window = 5
    vowel_weights_history = []

    # Process each frame
    for frame in range(Sxx.shape[1]):
        # Calculate vowel weights
        vowel_weights = {v: np.mean(Sxx[np.argmin(np.abs(f - low)):np.argmin(np.abs(f - high)), frame])
                         for v, (low, high) in vowel_ranges.items()}

        # Normalize weights
        total_weight = sum(vowel_weights.values())
        if total_weight > 0:
            vowel_weights = {v: w / total_weight for v, w in vowel_weights.items()}

        # Apply smoothing
        vowel_weights_history.append(vowel_weights)
        if len(vowel_weights_history) > smoothing_window:
            vowel_weights_history.pop(0)
        smoothed_weights = {v: np.mean([w[v] for w in vowel_weights_history]) for v in vowel_weights}

        energy = np.sum(Sxx[:, frame])
        is_speech = energy > 0.01 * np.max(Sxx)

        # Use the config in the vowel weight adjustment
        # Detect speech and adjust weights
        if is_speech:
            energy_scale = np.clip(energy / np.max(Sxx), 0, 1) ** 0.5
            adjusted_weights = adjust_vowel_weights(smoothed_weights, config)

            for vowel, weight in adjusted_weights.items():
                scaled_weight = min(weight * energy_scale, 1.0) #change this to increase/decrease weight effect
                vmd.add_morph_frame(vowel, frame, scaled_weight)
        else:
            for vowel in vowel_weights:
                vmd.add_morph_frame(vowel, frame, 0)

    if config.get('optimize_vmd', True):
        optimize_vmd_data(vmd)
    vmd.save(vmd_file)
    print(f"VMD saved at: {os.path.abspath(vmd_file)}")

def get_file_extension(filepath):
    # Returns the file extension of the given filepath string without the leading period.
    _, extension = os.path.splitext(filepath)
    return extension[1:] if extension else ''

def filename_fix_remove_extra_text(file_path, substring_to_remove = " --model Model"):
    # Bug fix for when cmd gives model name too
    #print(f"----- if needs fix testing {file_path}")
    if file_path.endswith(substring_to_remove):
        print(f"-----fixing file path extra for {file_path}")
        file_path = file_path[:-len(substring_to_remove)]
    return file_path

def trim_filename_if_needed(file_path, max_length=260):
    """
    Trims the filename if the file path exceeds the maximum allowed length.

    Parameters:
    - file_path (str): The full path to the file.
    - max_length (int): The maximum allowed length of the file path.

    Returns:
    - str: The modified file path if trimming was needed, otherwise the original file path.
    """
    if len(file_path) <= max_length:
        return file_path
    
    # Get the directory path and filename
    dir_path, filename = os.path.split(file_path)
    
    # Calculate how much to trim from the filename
    excess_length = len(file_path) - max_length
    
    if excess_length >= len(filename):
        raise ValueError("The directory path alone exceeds the maximum length limit.")
    
    # Trim the filename
    trimmed_filename = filename[:-excess_length]

    # Ensure there's still a valid file extension if applicable
    base, ext = os.path.splitext(filename)
    if ext:
        trimmed_filename = base[:len(trimmed_filename) - len(ext)] + ext
    
    # Reassemble the trimmed file path
    trimmed_file_path = os.path.join(dir_path, trimmed_filename)
    
    return trimmed_file_path

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert audio to VMD lip sync data.")
    parser.add_argument("input", nargs='*', type=Path, help="Input audio file(s) or directory")
    parser.add_argument("--output", "-o", type=Path, default="output", help="Output directory for VMD files")
    parser.add_argument('--send-lips-data-to', type=Path,  default="", help='Path to the VMD file to receive the lips data')
    parser.add_argument("--model", "-m", default="Model", help="Model name for VMD file")
    parser.add_argument("--config", "-c", type=Path, default="config.yaml", help="Path to configuration file")
    parser.add_argument("--extras-mode", choices=["OPTIMIZE_VMD", "REPLACE_LIPS", ""], default="", help="Extra processing mode")
    parser.add_argument('--show-final-complete-message', type=str2bool, default="True", help='Tells to show the final complete message (used for looping).')
     
    
    args = parser.parse_args()
    #print(f"---args_before=<{args}>")
    
    if not args.input:
        parser.print_help()
        print("\nExamples:")
        print("  python audio2vmd.py input.mp3")
        print("  python audio2vmd.py input1.mp3 input2.wav --output my_output --model 'My Model'")
        print("  python audio2vmd.py input_directory --output output_directory")
        sys.exit(1)

    audio_source_files_count = 1 # number of audio files to convert
    start_time = time.time() #global start time for the whole process
    item_start_time = time.time() #start time for the current audio file
    
    #print(f"-args before ={str(args)}")
    args.input = [str(path) for path in args.input] # convert all items to string
    args.output = str(args.output) 
    #args.model = str(args.model)
    args.config = str(args.config)
    args.send_lips_data_to = str(args.send_lips_data_to) # converts Path back to strings for now
    if args.send_lips_data_to == '.': #remove . set by Path when empty directory is given
        args.send_lips_data_to = ''
    #print(f"-args after ={str(args)}")

    # remove extra model name if it's connected to end of output directory (bug fix)
    # if args.output.endswith(substring_to_remove):
    #     args.output = args.output[:-len(substring_to_remove)]
    # if args.send_lips_data_to.endswith(substring_to_remove):
    #     args.send_lips_data_to = args.send_lips_data_to[:-len(substring_to_remove)]
    m_command = " --model " + args.model
    args.output = filename_fix_remove_extra_text(args.output, m_command)
    args.send_lips_data_to = filename_fix_remove_extra_text(args.send_lips_data_to, m_command)

    # Starts output folder in the parent directory unless a full directory was given
    if not os.path.isabs(args.output):
        # Local path, append the provided output directory to the parent directory
        parent_dir = os.path.dirname(os.getcwd())
        args.output = os.path.join(parent_dir, args.output)

    #print(f"===test args = <{str(args)}>")
    #print("Full output directory:", args.output)
    #print(f"===test input args = <{args.input}>")

    config = load_config(args.config)
    print_config(config)

    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Check if we're resuming a previous batch
    remaining_files = load_progress(args.output)#this temporary holds audio file count and start time too in the array
    
    audio_formats = ".mp3, .wav, .mp4, .mkv, .aac, .flac, .ogg, .wma, .m4a, .alac, .aiff, .pcm, .aa3, .aax, .ac3, .dts, .amr, .opus"

    if remaining_files is None:
        # This is a new batch, so process all input files
        input_files = []
        for input_path in args.input:
            input_path = filename_fix_remove_extra_text(input_path, m_command)
            if os.path.isdir(input_path):
                input_files.extend([os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(('.mp4','.mkv','.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.m4a', '.alac', '.aiff', '.pcm', '.aa3', '.aax', '.ac3', '.dts', '.amr', '.opus'))])
            elif os.path.isfile(input_path) and input_path.endswith('.txt'):
                print(f"Reading audio file paths from: {input_path}")
                with open(input_path, 'r') as f:
                    file_paths = [line.strip() for line in f if line.strip()]
                    input_files.extend(file_paths)
                print(f"Found {len(file_paths)} audio file(s) in the text file:")
                for file_path in file_paths:
                    print(f"  - {file_path}")
            else:
                input_files.append(input_path)
    else:
        # We're resuming a previous batch
        start_time = float(remaining_files.pop(0)) #loads the start time(which was the first item)
        audio_source_files_count = int(remaining_files.pop(0)) #keeps count of original source files for printing results at end
        input_files = remaining_files
        print(f"Resuming batch processing with {len(input_files)} remaining files.")
    audio_source_files_count = len(input_files)
    
    extras_base_name = os.path.splitext(os.path.basename(args.input[0]))[0]
    
    #print(f"===test output args = <{args.output}>")

    if args.extras_mode == "OPTIMIZE_VMD":
        vmd = VMDFile()
        vmd.load(args.input[0])
        extras_output_path = os.path.join(args.output, f"{extras_base_name}_optimized.vmd")
        bone_pos = config.get('extras_optimize_vmd_bone_position_tolerance', 0.005)
        bone_rot = config.get('extras_optimize_vmd_bone_rotation_tolerance', 0.005)
        #print(f"-Bone Position Tolerance = {bone_pos}")
        #print(f"-Bone Rotation Tolerance = {bone_rot}")
        optimize_vmd_bones_and_morphs(vmd, bone_pos, bone_rot)
        vmd.save(extras_output_path)
        print(f"Optimized VMD saved to: {extras_output_path}")
    elif args.extras_mode == "REPLACE_LIPS":
        if not args.send_lips_data_to:
            print("Error: --send-lips-data-to argument is required for REPLACE_LIPS mode")
            exit(1)
        extras_output_path = os.path.join(args.output, f"{os.path.splitext(os.path.basename(args.send_lips_data_to))[0]}_With_Lips_From_{os.path.splitext(os.path.basename(args.input[0]))[0]}.vmd")
        replace_mouth_frames(args.input[0], args.send_lips_data_to, extras_output_path)
        print(f"VMD with replaced lips data saved to: {extras_output_path}")
    else:
        # Existing batch processing logic
        batch_process(input_files, args.output, args.model, config, start_time, item_start_time, audio_source_files_count, args.send_lips_data_to, args.show_final_complete_message)


    #batch_process(input_files, args.output, args.model, config, start_time, item_start_time, audio_source_files_count, args.send_lips_data_to)
    

    if args.show_final_complete_message == True:
        end_time = time.time()
        processing_time = end_time - start_time
        if audio_source_files_count>1:
            print(f"Complete! All Audio to VMD conversion completed for {audio_source_files_count} audio files in {format_time(processing_time)}.")
        else:
            print(f"Complete! All Audio to VMD conversion completed in {format_time(processing_time)}.")
    

