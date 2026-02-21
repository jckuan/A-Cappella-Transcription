import os
import ffmpeg
import librosa
import soundfile as sf
import numpy as np

def extract_audio_to_pcm(input_path: str, output_path: str, target_sr: int = 44100) -> bool:
    """
    Extracts audio from an input file and saves it as a lossless 24-bit PCM WAV.
    Enforces stereo configuration and the target sample rate.
    
    Args:
        input_path: Path to the input audio file.
        output_path: Path to save the extracted WAV file.
        target_sr: Desired sample rate (default 44100).
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if not os.path.exists(input_path):
        print(f"[ERROR] Input file '{input_path}' not found.")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        print(f"[LIBRARIAN] Standardizing {input_path} to {target_sr}Hz 24-bit stereo PCM...")
        # pcm_s24le is signed 24-bit little-endian PCM
        (
            ffmpeg
            .input(input_path)
            .output(output_path, acodec='pcm_s24le', ar=target_sr, ac=2)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"[LIBRARIAN] Successfully normalized and saved to {output_path}")
        return True
    except ffmpeg.Error as e:
        print(f"[ERROR] FFmpeg Error processing {input_path}:")
        print(e.stderr.decode('utf8'))
        return False

def verify_audio_requirements(file_path: str, expected_sr: int = 44100, expected_channels: int = 2) -> bool:
    """
    Verifies that the generated audio meets the strict downstream model requirements.
    
    Args:
        file_path: Path to the audio file to verify.
        expected_sr: The sample rate expected by the models (default 44100).
        expected_channels: The number of channels expected (default 2 for stereo).
        
    Returns:
        bool: True if it strictly meets requirements, False otherwise.
    """
    try:
        # soundfile is very efficient at just reading headers to grab metadata
        info = sf.info(file_path)
        
        if info.samplerate != expected_sr:
            print(f"[WARN] Sample rate mismatch: Expected {expected_sr}, got {info.samplerate}")
            return False
            
        if info.channels != expected_channels:
            print(f"[WARN] Channel mismatch: Expected {expected_channels}, got {info.channels}")
            return False
            
        if info.subtype != 'PCM_24':
            print(f"[WARN] Bit depth mismatch: Expected 24-bit PCM, got {info.subtype}")
            return False
            
        print(f"[PASS] {file_path} meets all model data requirements.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Could not read metadata for {file_path}: {e}")
        return False

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Librarian Data Preparation Tool")
    parser.add_argument("input_dir", help="Directory containing input raw audio files")
    parser.add_argument("output_dir", help="Directory to save the standardized audio files")
    parser.add_argument("--sr", type=int, default=44100, help="Target sample rate (default: 44100)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"Directory {args.input_dir} does not exist.")
        sys.exit(1)
        
    for filename in os.listdir(args.input_dir):
        if filename.startswith('.'):
            continue # skip hidden files
            
        in_path = os.path.join(args.input_dir, filename)
        
        if not os.path.isfile(in_path):
            continue
            
        # Standardize naming to output .wav
        name, _ = os.path.splitext(filename)
        out_path = os.path.join(args.output_dir, f"{name}_normalized.wav")
        
        success = extract_audio_to_pcm(in_path, out_path, target_sr=args.sr)
        if success:
            verify_audio_requirements(out_path, expected_sr=args.sr)
