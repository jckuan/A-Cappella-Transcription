import os
import subprocess
import pretty_midi
import json
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
from typing import Dict, List, Any

class PolyphonicTranscriber:
    """
    Handles the Polyphonic Symbolic Transcription of a VP-less vocal mix using basic-pitch.
    It extracts polyphonic pitch data, applies heuristic pruning to limit the maximum
    number of simultaneous voices, and exports the result to MIDI and synthesized WAV.
    """

    def __init__(self):
        self.model_path = ICASSP_2022_MODEL_PATH

    def transcribe(self, audio_path: str, metadata_path: str, output_dir: str, vp_audio: str = None, 
                   onset_threshold: float = 0.3, frame_threshold: float = 0.2, extra_polyphony: int = 2, quantize_unit: int = 16) -> str:
        """
        Transcribes audio to a polyphony-limited MIDI file.
        Adjusted onset_threshold and frame_threshold down to capture earlier onsets and weaker notes.
        """
        print(f"[TRANSCRIBER] Starting multi-pitch estimation on {audio_path}")
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # 1. Read metadata for polyphony limit
        num_singers = 4 # SATB default
        bpm = 120.0
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    meta = json.load(f)
                    song_meta = meta.get(base_name, {})
                    num_singers = song_meta.get("num_singers", 4)
                    bpm = song_meta.get("bpm", 120.0)
            except Exception as e:
                print(f"[TRANSCRIBER WARNING] Failed to read metadata: {e}. Defaulting to 4 singers, 120.0 BPM.")
        else:
            print(f"[TRANSCRIBER] No metadata file found at {metadata_path}. Defaulting to 4 singers, 120.0 BPM.")

        pitch_bounds = song_meta.get("pitch_bounds_midi", {})

        export_midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
        
        if pitch_bounds:
            print(f"[TRANSCRIBER] Found pitch bounds for {len(pitch_bounds)} parts. Running Hybrid Scenario B (Frequency Masking & VP Stem).")
            import librosa
            import soundfile as sf
            import scipy.signal
            import numpy as np
            
            try:
                audio_data, sr = librosa.load(audio_path, sr=None, mono=True)
                
                for part_name, bounds in pitch_bounds.items():
                    midi_min, midi_max = bounds
                    
                    if "bass" in part_name.lower() and vp_audio and os.path.exists(vp_audio):
                        print(f"[TRANSCRIBER] Processing part: {part_name} (Using extracted VP stem {vp_audio})")
                        target_audio = vp_audio
                        is_temp = False
                    else:
                        print(f"[TRANSCRIBER] Processing part: {part_name} (Using Bandpass Filter MIDI {midi_min}-{midi_max})")
                        freq_min = 440.0 * (2.0 ** ((midi_min - 2 - 69) / 12.0))
                        freq_max = 440.0 * (2.0 ** ((midi_max + 2 - 69) / 12.0))
                        
                        nyq = 0.5 * sr
                        low = max(0.01, freq_min / nyq)
                        high = min(0.99, freq_max / nyq)
                        
                        b, a = scipy.signal.butter(4, [low, high], btype='band')
                        filtered_audio = scipy.signal.filtfilt(b, a, audio_data)
                        
                        max_amp = np.max(np.abs(filtered_audio))
                        if max_amp > 0:
                            filtered_audio = filtered_audio / max_amp * 0.9
                            
                        target_audio = os.path.join(output_dir, f"tmp_{part_name}_{base_name}.wav")
                        sf.write(target_audio, filtered_audio, sr)
                        is_temp = True
                        
                    try:
                        _, part_midi, _ = predict(
                            target_audio, 
                            self.model_path, 
                            onset_threshold=onset_threshold, 
                            frame_threshold=frame_threshold
                        )
                    except Warning:
                        pass
                    except Exception as e:
                        print(f"[TRANSCRIBER WARNING] Failed to predict part {part_name}: {e}")
                        part_midi = pretty_midi.PrettyMIDI()
                        
                    if is_temp and os.path.exists(target_audio):
                        os.remove(target_audio)
                        
                    if quantize_unit > 0:
                        part_midi = self._quantize_midi(part_midi, bpm, quantize_unit)
                        
                    part_max_polyphony = 1 + (extra_polyphony // 2)
                    part_midi = self._prune_polyphony(part_midi, part_max_polyphony)
                    
                    if part_midi.instruments:
                        inst = part_midi.instruments[0]
                        inst.name = part_name
                        # Clamp notes firmly to boundaries to prevent crosstalk
                        valid_notes = [n for n in inst.notes if midi_min - 4 <= n.pitch <= midi_max + 4]
                        inst.notes = valid_notes
                        export_midi.instruments.append(inst)
            except Exception as e:
                print(f"[TRANSCRIBER ERROR] Hybrid masking failed: {e}")
                print("[TRANSCRIBER] Falling back to standard inference.")
                pitch_bounds = {} # trigger fallback
        else:
            max_polyphony = num_singers + extra_polyphony
            print(f"[TRANSCRIBER] Pruning notes to enforce maximum polyphony of {max_polyphony}...")
            pruned_midi = self._prune_polyphony(midi_data, max_polyphony)
            export_midi.instruments = pruned_midi.instruments
        
        output_midi_path = os.path.join(output_dir, f"{base_name}_transcribed.mid")
        export_midi.write(output_midi_path)
        print(f"[TRANSCRIBER] Saved pruned MIDI to {output_midi_path}")

        return output_midi_path

    def _prune_polyphony(self, midi_data: pretty_midi.PrettyMIDI, max_polyphony: int) -> pretty_midi.PrettyMIDI:
        """
        Takes a PrettyMIDI object and guarantees that at no single continuous point in time 
        are there more than `max_polyphony` active notes. Keeps the highest velocity notes.
        """
        # We only care about the single instrument track created by basic-pitch (usually Piano or similar)
        if not midi_data.instruments:
            return midi_data
            
        inst = midi_data.instruments[0]
        original_notes = inst.notes
        
        if not original_notes:
            return midi_data

        # We need to evaluate active notes over time.
        # Create a list of all start and end events to sweep through time.
        events = []
        for i, note in enumerate(original_notes):
            events.append((note.start, 'start', i, note.velocity))
            events.append((note.end, 'end', i, note.velocity))
            
        events.sort(key=lambda x: (x[0], x[1] == 'start')) # Sort by time, ends before starts if coincident
        
        active_notes = set()
        notes_to_keep = set()
        
        # Sweep line algorithm to track active notes
        for time, event_type, note_idx, velocity in events:
            if event_type == 'start':
                active_notes.add(note_idx)
                # Check polyphony
                if len(active_notes) > max_polyphony:
                    # Too many notes! Find the one with the lowest velocity and drop it
                    # Note: We keep the ones with the highest confidence (velocity in basic-pitch)
                    sorted_active = sorted(list(active_notes), key=lambda idx: original_notes[idx].velocity)
                    # The weakest note is at index 0
                    weakest_note_idx = sorted_active[0]
                    active_notes.remove(weakest_note_idx)
            else:
                if note_idx in active_notes:
                    notes_to_keep.add(note_idx)
                    active_notes.remove(note_idx)
                
        # Any notes still active at the end that survived pruning are kept
        for note_idx in active_notes:
            notes_to_keep.add(note_idx)
            
        # Create a new instrument with only the kept notes
        new_inst = pretty_midi.Instrument(program=inst.program, is_drum=inst.is_drum, name=inst.name)
        new_inst.notes = [original_notes[i] for i in sorted(list(notes_to_keep))]
        
        # Replace the instruments list
        midi_data.instruments = [new_inst]
        
        return midi_data

    def _quantize_midi(self, midi_data: pretty_midi.PrettyMIDI, bpm: float, base_unit: int) -> pretty_midi.PrettyMIDI:
        """
        Snaps note starts and ends to the closest grid division to fix lagging/humanization variations.
        """
        if base_unit <= 0 or not midi_data.instruments:
            return midi_data
            
        # Assuming 4/4 time signature for the quarter note beat
        beat_duration = 60.0 / bpm
        # If base_unit is 16, we want 1/16th notes. That means 4 steps per beat.
        step = beat_duration * (4.0 / base_unit)
        
        for inst in midi_data.instruments:
            for note in inst.notes:
                # Snap start and end to nearest grid step
                note.start = round(note.start / step) * step
                note.end = round(note.end / step) * step
                # Ensure minimum duration of 1 step
                if note.end <= note.start:
                    note.end = note.start + step
                    
        return midi_data

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to the VP-less vocal mix WAV.")
    parser.add_argument("--metadata", required=True, help="Path to metadata JSON.")
    parser.add_argument("--out_dir", required=True, help="Output directory for MIDI and WAV.")
    parser.add_argument("--vp_audio", default=None, help="Optional: Path to the clean isolated VP (Vocal Percussion) stem.")
    parser.add_argument("--onset_threshold", type=float, default=0.3, help="Basic-Pitch onset threshold (default 0.3).")
    parser.add_argument("--frame_threshold", type=float, default=0.2, help="Basic-Pitch frame threshold (default 0.2).")
    parser.add_argument("--extra_polyphony", type=int, default=2, help="Basic-Pitch extra allowed voices (default 2).")
    parser.add_argument("--quantize_unit", type=int, default=16, help="MIDI quantization base unit (default 16 for 1/16th notes).")
    
    args = parser.parse_args()
    
    transcriber = PolyphonicTranscriber()
    midi_out = transcriber.transcribe(
        args.audio, 
        args.metadata, 
        args.out_dir, 
        vp_audio=args.vp_audio,
        onset_threshold=args.onset_threshold,
        frame_threshold=args.frame_threshold,
        extra_polyphony=args.extra_polyphony,
        quantize_unit=args.quantize_unit
    )
