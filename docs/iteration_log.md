# Transcription Iteration Log

This document tracks all iterative improvements, experiments, and end-user feedback loops applied to the Polyphonic Symbolic Transcription component block.

## Initial Build
- **Setup:** Ran `basic-pitch` on the full, VP-less a cappella mix. Extracted all notes natively and heuristically pruned the simultaneous active notes down to 4 (matching standard SATB polyphony limitations).
- **Result:** Software executed successfully. It exported the multi-track `.mid` file alongside a `fluidsynth` synthesized `.wav` file for auditory evaluation.

## Iteration 1: Audio Fixes & Onset Timings
- **User Feedback:** The `.wav` file did not output, and the notes that were transcribed to the MIDI were consistently lagging behind the beat.
- **Action Applied:** Fixed a generic `fluidsynth` 48kHz sampling generation issue. Dropped the `basic-pitch` sensitivity thresholds (`onset_threshold` and `frame_threshold`) significantly so it would capture softer attacks and log notes earlier.

## Iteration 2: Grid Quantization & Tool Cleanup
- **User Feedback:** The transcribed notes were still perceptually lagging. User requested snapping them directly to a 1/16th note grid, and requested the removal of the automated `fluidsynth` audio feature since outputs are verified manually in the Logic Pro DAW.
- **Action Applied:** Ripped out `fluidsynth` dependencies entirely. Inserted a mathematical MIDI quantization feature (grid-snapping) aligned mathematically to the track's BPM (parsed gracefully from project `metadata.json`).

## Iteration 3: Scenario B (Frequency Masking Isolation)
- **User Feedback:** The timing was much better, but some critical parts (especially the Bass) were entirely missing due to the louder melodies masking them in the mix.
- **Action Applied:** Built a digital `scipy.signal.butter` Bandpass Filter to mathematically isolate the Bass, Tenor, Alto, and Soprano tracking bounds completely based on standard `pitch_bounds_midi`. Re-ran `basic-pitch` over these 4 masked frequencies separately and merged the individual instrument tracks back into one grouped MIDI. 
- **Result (Failure):** The Bandpass filter successfully carved out the fundamentals, but unfortunately destroyed the upper human vocal harmonics in the process. `basic-pitch` requires those overtones to understand a note, resulting in a completely silent Bass output track holding zero notes.

## Iteration 4: Hybrid Frequency & Stem Extraction
- **User Feedback:** The S/A/T bandpass separation sounded musically coherent, but the Bass track disappearance was unacceptable. User insightfully proposed mining the Bass notes back from the misclassified VP stem.
- **Action Applied:** Engineered a Hybrid pipeline. The Soprano, Alto, and Tenor notes remain extracted via the Bandpass filter technique (to prevent different melodies from destructively jumping tracks). Correspondingly, the Bass notes are successfully extracted by targeting the `--vp_audio` (`no_vocals.wav`) stem generated natively by `htdemucs`, maintaining the bassline with all of its natural rich overtones.
- **Verdict:** `SCORE: 6/10`. Leveraging the VP stem fully restored the missing bass track. The isolated S/A/T stems are musically coherent again. While greatly improved, manual repair via notation software remains necessary for missing intertwined inner harmonies (Alto/Tenor) due to the sheer difficulty of differentiating heavily overlapping homogeneous vocal formants.

## Iteration 5: Two-Stage Harmonic Filter
- **User Feedback:** Each stem contained multiple simultaneous candidate notes. The intended goal is not a monophonic stem per singer but a clean polyphonic output close to ground truth. Harmonic context was needed to select correct pitches. ROSVOT ruled out (single-voice requirement). `autochord` ruled out (Linux-only VAMP binary, macOS incompatible).
- **Action Applied:**
  - **Stage 1 (Key Filter):** User provides `"key"` in `metadata.json` (e.g. `"E minor"`). `music21` resolves the 7 scale pitch classes and drops all out-of-key notes. Auto-detection fallback available.
  - **Stage 2 (Chord Filter):** `librosa` chroma CQT is used to compute a chromagram for the full audio. For each note, the dominant chord is estimated via dot-product against 24 major/minor chord templates. Notes whose pitch class is not a chord tone are dropped.
- **Note Reduction Results (Attention):**
  - Bass: 946 → 755 (-20%)
  - Tenor: 1153 → 796 (-31%)
  - Alto: 1345 → 889 (-34%)
  - Soprano: 1410 → 975 (-31%)
- **Verdict:** `SCORE: 6/10` — same as Iteration 4 without filtering. User prefers not filtering: the multiple candidate notes per stem serve as "options" the singers can choose from when manually editing. The harmonic filter code is retained and available via `--harmonic_filter`.

## Iteration 6: Note Merge & Opt-in Harmonic Filter
- **User Feedback:** The harmonic filter rated the same 6/10. Long notes were fragmenting into 1/16 unit runs due to quantization. Automatic note merging was added, but it incorrectly merged intentional rhythmic repeated notes.
- **Action Applied:**
  - `--harmonic_filter` flag added to CLI (default: off). Two-stage filter code preserved.
  - `_merge_sustained_notes()` (pre-quantization): merges overlapping same-pitch notes from `basic-pitch` detection. In practice, `basic-pitch` does not output overlapping notes, so this pass has zero effect.
  - `_merge_adjacent_notes()` (post-quantization): tunable via `--merge_gap_steps N` (default: off). Merges same-pitch notes with gap ≤ N grid steps, with a velocity re-onset guard (≥10% velocity increase = fresh attack, skip merge).
- **Limitation found:** `basic-pitch` fragmentation (artifacts) and intentional rhythmic repetitions both result in gap = 0 after quantization. The two cases are indistinguishable at the MIDI-only level without the original audio onset detection signal.
- **Verdict:** Note merge is exposed as a tunable opt-in. Users can dial `--merge_gap_steps 0.05` for conservative artifact-only cleanup. The note fragmentation problem is documented as a known open-source tool limitation.
