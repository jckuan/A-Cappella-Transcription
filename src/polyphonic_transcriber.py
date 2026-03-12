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
                   onset_threshold: float = 0.3, frame_threshold: float = 0.2, extra_polyphony: int = 2, 
                   quantize_unit: int = 16, apply_harmonic_filter: bool = False,
                   merge_gap_steps: float = 0.0) -> str:
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
                    song_key = song_meta.get("key", None)
            except Exception as e:
                print(f"[TRANSCRIBER WARNING] Failed to read metadata: {e}. Defaulting to 4 singers, 120.0 BPM.")
        else:
            print(f"[TRANSCRIBER] No metadata file found at {metadata_path}. Defaulting to 4 singers, 120.0 BPM.")

        pitch_bounds = song_meta.get("pitch_bounds_midi", {})

        export_midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

        # 2. Run basic-pitch once on the full mix - result always available for fallback
        print(f"[TRANSCRIBER] Running basic-pitch prediction (onset={onset_threshold}, frame={frame_threshold})...")
        try:
            _, midi_data, _ = predict(
                audio_path, 
                self.model_path, 
                onset_threshold=onset_threshold, 
                frame_threshold=frame_threshold
            )
        except Exception as e:
            print(f"[TRANSCRIBER ERROR] basic-pitch inference failed: {e}")
            return None

        if quantize_unit > 0:
            print(f"[TRANSCRIBER] Quantizing MIDI to 1/{quantize_unit} notes at {bpm} BPM...")
            midi_data = self._merge_sustained_notes(midi_data)  # merge overlaps BEFORE quantization
            midi_data = self._quantize_midi(midi_data, bpm, quantize_unit)
            if merge_gap_steps > 0:
                midi_data = self._merge_adjacent_notes(midi_data, bpm, quantize_unit, merge_gap_steps)

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
                        part_midi = self._merge_sustained_notes(part_midi)  # merge overlaps BEFORE quantization
                        part_midi = self._quantize_midi(part_midi, bpm, quantize_unit)
                        if merge_gap_steps > 0:
                            part_midi = self._merge_adjacent_notes(part_midi, bpm, quantize_unit, merge_gap_steps)
                        
                    part_max_polyphony = 1 + (extra_polyphony // 2)
                    part_midi = self._prune_polyphony(part_midi, part_max_polyphony)
                    
                    if part_midi.instruments:
                        inst = part_midi.instruments[0]
                        inst.name = part_name
                        valid_notes = [n for n in inst.notes if midi_min - 4 <= n.pitch <= midi_max + 4]
                        inst.notes = valid_notes
                        export_midi.instruments.append(inst)
            except Exception as e:
                print(f"[TRANSCRIBER ERROR] Hybrid masking failed: {e}. Falling back to simple polyphony pruning.")
                max_polyphony = num_singers + extra_polyphony
                pruned_midi = self._prune_polyphony(midi_data, max_polyphony)
                export_midi.instruments = pruned_midi.instruments
        else:
            max_polyphony = num_singers + extra_polyphony
            print(f"[TRANSCRIBER] Pruning notes to enforce maximum polyphony of {max_polyphony}...")
            pruned_midi = self._prune_polyphony(midi_data, max_polyphony)
            export_midi.instruments = pruned_midi.instruments
        
        # Apply the two-stage harmonic filter (opt-in only)
        if apply_harmonic_filter:
            print(f"[TRANSCRIBER] Applying harmonic filter (key={song_key})...")
            export_midi = self._apply_harmonic_filter(export_midi, audio_path, key=song_key)

        output_midi_path = os.path.join(output_dir, f"{base_name}_transcribed.mid")
        export_midi.write(output_midi_path)
        print(f"[TRANSCRIBER] Saved pruned MIDI to {output_midi_path}")

        return output_midi_path

    def _apply_harmonic_filter(self, midi_data: pretty_midi.PrettyMIDI, audio_path: str, key: str = None) -> pretty_midi.PrettyMIDI:
        """
        Two-stage harmonic filter:
        Stage 1: Drop notes outside the key's scale (uses metadata key or music21 auto-detect).
        Stage 2: Use autochord chord recognition to further retain only chord-tone notes per time window.
        """
        # --- Stage 1: Key-based scale filter ---
        allowed_pitch_classes = None
        try:
            import music21
            if key:
                print(f"[HARMONIC FILTER] Stage 1: Using provided key '{key}'.")
                # Normalize key string: 'E minor' -> 'e', 'C major' -> 'C', 'F# minor' -> 'f#'
                parts = key.strip().split()
                root = parts[0]
                mode = parts[1].lower() if len(parts) > 1 else 'major'
                if mode == 'minor':
                    normalized = root.lower()  # music21 uses lowercase for minor ('e' = E minor)
                else:
                    normalized = root[0].upper() + root[1:]  # 'C', 'F#' etc. for major
                k = music21.key.Key(normalized)
            else:
                print("[HARMONIC FILTER] Stage 1: Auto-detecting key from MIDI...")
                score = music21.converter.parse(midi_data)
                k = score.analyze('key')
                print(f"[HARMONIC FILTER] Stage 1: Detected key: {k}")
            allowed_pitch_classes = set(p.pitchClass for p in k.pitches)
            print(f"[HARMONIC FILTER] Stage 1: Allowed pitch classes: {sorted(allowed_pitch_classes)}")
        except Exception as e:
            print(f"[HARMONIC FILTER WARNING] Stage 1 failed: {e}. Skipping key filter.")

        for inst in midi_data.instruments:
            if allowed_pitch_classes is not None:
                before = len(inst.notes)
                inst.notes = [n for n in inst.notes if (n.pitch % 12) in allowed_pitch_classes]
                print(f"[HARMONIC FILTER] Stage 1: {inst.name or 'inst'}: {before} -> {len(inst.notes)} notes after key filter.")

        # --- Stage 2: Chord-tone filter using librosa chroma templates ---
        try:
            import librosa
            import numpy as np

            print(f"[HARMONIC FILTER] Stage 2: Computing chroma from {audio_path}...")
            y, sr = librosa.load(audio_path, sr=None, mono=True)
            hop_length = 512
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)  # shape: (12, T)
            times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=hop_length)

            # Build 96 chord templates per root: maj, min, dom7, maj7, min7, sus2, sus4
            CHORD_TEMPLATES = {}
            NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            CHORD_TYPES = {
                'maj':  [0, 4, 7],
                'min':  [0, 3, 7],
                'dom7': [0, 4, 7, 10],
                'maj7': [0, 4, 7, 11],
                'min7': [0, 3, 7, 10],
                'sus2': [0, 2, 7],
                'sus4': [0, 5, 7],
                'dim':  [0, 3, 6],
                'hdim7': [0, 3, 6, 10],
            }
            for root in range(12):
                for ctype, intervals in CHORD_TYPES.items():
                    pcs = frozenset((root + i) % 12 for i in intervals)
                    CHORD_TEMPLATES[f"{NOTE_NAMES[root]}:{ctype}"] = pcs

            def get_dominant_chord_pcs(t_start: float, t_end: float) -> set:
                """Find the dominant chord pitch classes for a time segment via chroma correlation."""
                idx_start = np.searchsorted(times, t_start)
                idx_end = np.searchsorted(times, t_end)
                if idx_start >= idx_end:
                    idx_end = idx_start + 1
                segment_chroma = chroma[:, idx_start:idx_end].mean(axis=1)  # mean chroma vector
                # Match against each template via dot product
                best_score, best_pcs = -1.0, None
                for label, pcs in CHORD_TEMPLATES.items():
                    template = np.array([1.0 if i in pcs else 0.0 for i in range(12)])
                    score = float(np.dot(segment_chroma, template))
                    if score > best_score:
                        best_score, best_pcs = score, pcs
                return best_pcs

            for inst in midi_data.instruments:
                filtered_notes = []
                for note in inst.notes:
                    chord_pcs = get_dominant_chord_pcs(note.start, note.end)
                    pc = note.pitch % 12
                    in_chord = chord_pcs is None or pc in chord_pcs
                    # In-scale fallback: only applies if Stage 1 was skipped (no key provided).
                    # When Stage 1 ran, out-of-key notes are already gone; we trust chord matching.
                    in_scale_fallback = (allowed_pitch_classes is None) and (pc in (allowed_pitch_classes or set()))
                    if in_chord or in_scale_fallback:
                        filtered_notes.append(note)
                before = len(inst.notes)
                inst.notes = filtered_notes
                print(f"[HARMONIC FILTER] Stage 2: {inst.name or 'inst'}: {before} -> {len(inst.notes)} notes after chord filter.")

        except Exception as e:
            print(f"[HARMONIC FILTER WARNING] Stage 2 failed: {e}. Skipping chord filter.")

        return midi_data

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

    def _merge_sustained_notes(self, midi_data: pretty_midi.PrettyMIDI) -> pretty_midi.PrettyMIDI:
        """
        Merges overlapping same-pitch note detections BEFORE quantization.
        
        Core principle:
        - basic-pitch fragmentation artifacts overlap in time (the model detects the same
          continuous pitch as multiple overlapping blobs). Merging these is safe.
        - Intentional rhythmic re-attacks NEVER overlap — there is always a real silence
          in between. These are preserved as separate notes.
        
        This approach is order-sensitive: must run BEFORE _quantize_midi(), because
        after quantization the overlap information is lost and gap-based merging
        cannot reliably distinguish rhythm from fragmentation.
        """
        if not midi_data.instruments:
            return midi_data

        for inst in midi_data.instruments:
            if not inst.notes:
                continue
            # Sort by pitch then start time
            sorted_notes = sorted(inst.notes, key=lambda n: (n.pitch, n.start))
            merged = []
            current = sorted_notes[0]
            for nxt in sorted_notes[1:]:
                same_pitch = nxt.pitch == current.pitch
                overlaps = nxt.start < current.end  # true overlap (not just adjacent)
                if same_pitch and overlaps:
                    # Absorb the overlapping fragment: extend end, keep original onset velocity
                    current = pretty_midi.Note(
                        velocity=current.velocity,
                        pitch=current.pitch,
                        start=current.start,
                        end=max(current.end, nxt.end)
                    )
                else:
                    merged.append(current)
                    current = nxt
            merged.append(current)
            print(f"[MERGE] {inst.name or 'inst'}: {len(inst.notes)} -> {len(merged)} notes after overlap merge.")
            inst.notes = merged

        return midi_data

    def _merge_adjacent_notes(self, midi_data: pretty_midi.PrettyMIDI, bpm: float, base_unit: int, gap_steps: float) -> pretty_midi.PrettyMIDI:
        """
        Post-quantization merge: merges same-pitch notes whose gap is <= gap_steps grid steps.
        Tunable via --merge_gap_steps: 0.05 = near-zero only, 0.5 = more aggressive.
        Velocity re-onset guard: skips merge if next note velocity is >=10% higher (fresh attack).
        """
        if not midi_data.instruments:
            return midi_data
        beat_duration = 60.0 / bpm
        step = beat_duration * (4.0 / base_unit)
        tolerance = step * gap_steps
        for inst in midi_data.instruments:
            if not inst.notes:
                continue
            sorted_notes = sorted(inst.notes, key=lambda n: (n.pitch, n.start))
            merged = []
            current = sorted_notes[0]
            for nxt in sorted_notes[1:]:
                gap = nxt.start - current.end
                is_adjacent = nxt.pitch == current.pitch and gap <= tolerance
                is_fresh_onset = nxt.velocity >= current.velocity * 1.10
                if is_adjacent and not is_fresh_onset:
                    current = pretty_midi.Note(
                        velocity=current.velocity,
                        pitch=current.pitch,
                        start=current.start,
                        end=max(current.end, nxt.end)
                    )
                else:
                    merged.append(current)
                    current = nxt
            merged.append(current)
            print(f"[MERGE_ADJ] {inst.name or 'inst'}: {len(inst.notes)} -> {len(merged)} notes (gap_steps={gap_steps}).")
            inst.notes = merged
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
    parser.add_argument("--harmonic_filter", action="store_true", default=False, help="Enable the two-stage harmonic filter (Stage 1: key-based, Stage 2: chord-based). Off by default.")
    parser.add_argument("--merge_gap_steps", type=float, default=0.0,
                        help="Post-quantization merge: merge same-pitch notes with a gap <= N grid steps. "
                             "0.0 = disabled (default). Try 0.05 to only catch floating-point artifacts, "
                             "or up to 0.5 for more aggressive merging.")
    
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
        quantize_unit=args.quantize_unit,
        apply_harmonic_filter=args.harmonic_filter,
        merge_gap_steps=args.merge_gap_steps
    )
