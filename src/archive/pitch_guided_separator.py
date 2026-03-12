import os
import json
import librosa
import soundfile as sf
import numpy as np
import scipy.ndimage
from typing import Dict, Optional

class PitchGuidedSeparator:
    def __init__(self, metadata_path: str):
        self.metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
                
    def separate(self, mix_audio_path: str, output_dir: str, track_name: str) -> Optional[Dict[str, str]]:
        print(f"[PITCH-GUIDED] Starting pitch-guided separation for {track_name}")
        
        if track_name not in self.metadata:
            print(f"[PITCH-GUIDED WARNING] Track '{track_name}' not found in metadata.json. Using default SATB bounds.")
            bounds = {
                "bass": [40, 64],
                "tenor": [48, 69],
                "alto": [55, 77],
                "soprano": [60, 84]
            }
        else:
            bounds = self.metadata[track_name].get("pitch_bounds_midi", {})
            
        try:
            from basic_pitch.inference import predict
        except ImportError:
            print("[PITCH-GUIDED ERROR] basic-pitch is not installed.")
            return None

        # 1. Run Basic Pitch
        print("[PITCH-GUIDED] Estimating polyphonic pitch contours...")
        model_output, midi_data, note_events = predict(mix_audio_path)
        
        # Load audio and compute STFT
        print("[PITCH-GUIDED] Computing STFT...")
        y, sr = librosa.load(mix_audio_path, sr=44100, mono=False)
        n_fft = 8192
        hop_length = 512 # Better time resolution for mask
        
        if y.ndim > 1:
            y_mono = librosa.to_mono(y)
            D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
            D_mono = librosa.stft(y_mono, n_fft=n_fft, hop_length=hop_length)
        else:
            D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
            D_mono = D
            
        n_freqs, n_stft_frames = D_mono.shape
        stft_freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        
        os.makedirs(output_dir, exist_ok=True)
        stems = {}
        
        # 2. DP / Greedy Contour Tracking
        print("[PITCH-GUIDED] Assigning notes to vocal contours...")
        voices = ["soprano", "alto", "tenor", "bass"]
        centers = {"soprano": 72, "alto": 66, "tenor": 58, "bass": 52}
        
        for v in voices:
            if v in bounds:
                centers[v] = (bounds[v][0] + bounds[v][1]) / 2.0
                
        last_end_time = {v: -1.0 for v in voices}
        last_pitch = {v: centers[v] for v in voices}
        assigned_notes = {v: [] for v in voices}
        
        # Sort notes by start time, then pitch descending (highest notes first)
        sorted_notes = sorted(note_events, key=lambda x: (x[0], -x[2]))
        
        for note in sorted_notes:
            start_t, end_t, pitch = note[0], note[1], note[2]
            
            best_v = None
            min_cost = float('inf')
            
            for v in voices:
                if v not in bounds:
                    continue
                    
                # 1. Deviation from expected voice range center
                cost = abs(pitch - centers[v]) * 1.5
                
                # 2. Smoothness / Melodic continuity
                gap = max(0, start_t - last_end_time[v])
                if gap < 2.0:  # If the gap is small, reward staying close to the previous pitch
                    cost += abs(pitch - last_pitch[v]) * (2.0 - gap) * 0.5
                    
                # 3. Polyphony overlap penalty (preventing one voice from singing two notes at once)
                overlap = max(0, last_end_time[v] - start_t)
                if overlap > 0.05:
                    cost += overlap * 10000.0  # Huge penalty for overlapping notes
                    
                if cost < min_cost:
                    min_cost = cost
                    best_v = v
                    
            if best_v is not None:
                assigned_notes[best_v].append(note)
                last_pitch[best_v] = pitch
                # Extend the voice's active duration
                last_end_time[best_v] = max(last_end_time[best_v], end_t)
        
        for voice in voices:
            if voice not in bounds:
                continue
                
            print(f"[PITCH-GUIDED] Generating mask for {voice}... (Assigned {len(assigned_notes[voice])} notes)")
            
            mask = np.zeros_like(np.abs(D_mono))
            
            for note in assigned_notes[voice]:
                start_t, end_t, pitch = note[0], note[1], note[2]
                
                start_frame = max(0, int(start_t * sr / hop_length))
                end_frame = min(n_stft_frames, int(end_t * sr / hop_length) + 1)
                
                if start_frame >= end_frame:
                    continue
                    
                f0 = librosa.midi_to_hz(pitch)
                n_harmonics = int((sr / 2) / f0)
                
                # We mask fundamental and up to ~40 harmonics
                for k in range(1, min(n_harmonics + 1, 40)):
                    f_k = k * f0
                    bin_idx = np.argmin(np.abs(stft_freqs - f_k))
                    
                    # Spread the mask (wider for higher harmonics to capture vibrato/inharmonicity)
                    spread = int(max(2, k * 0.15)) 
                    
                    for b in range(max(0, bin_idx - spread), min(n_freqs, bin_idx + spread + 1)):
                        mask[b, start_frame:end_frame] = 1.0
            
            # Smooth mask slightly to prevent burbling noise
            mask = scipy.ndimage.gaussian_filter(mask, sigma=[0.5, 2.0])
            
            # Apply soft mask
            if y.ndim > 1:
                mask_mult = np.expand_dims(mask, 0)
                D_voice = D * mask_mult
            else:
                D_voice = D * mask
                
            print(f"[PITCH-GUIDED] Resynthesizing {voice}...")
            y_voice = librosa.istft(D_voice, hop_length=hop_length)
            
            out_path = os.path.join(output_dir, f"{voice}.wav")
            sf.write(out_path, y_voice.T if y_voice.ndim > 1 else y_voice, sr)
            stems[voice] = out_path
            
        print(f"[PITCH-GUIDED] Finished. Saved stems to {output_dir}")
        return stems

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--track_name", required=True)
    parser.add_argument("--metadata", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/metadata.json"))
    args = parser.parse_args()
    
    separator = PitchGuidedSeparator(args.metadata)
    separator.separate(args.input, args.output_dir, args.track_name)
