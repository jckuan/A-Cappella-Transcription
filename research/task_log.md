# Task Checklist

## Phase 1: Preparation & Vocal Percussion Isolation
1. [x] Run `htdemucs` to split the Vocal Percussion (VP) from the vocal harmony mix.

## Phase 2: SATB Audio Source Separation (Archived/Failed)
1. [x] Evaluate `SepACap` (Failed due to model artifacts).
2. [x] Evaluate `RoFormer` MUSDB-18 stem mapping (Failed due to timbre rejection).
3. [x] Evaluate `Pitch-Guided Harmonic Masking` (Failed due to polyphonic estimation noise).

## Phase 3: Polyphonic Symbolic Transcription
1. [x] Refactor the pipeline orchestrator (`vocal_separator.py` & `extract_vp.py`) to skip Phase 2 SATB audio separation entirely.
2. [x] Create an `implementation_plan.md` outlining the polyphonic transcription approach.
3. [x] Identify a suitable Multi-Pitch Estimation (MPE) model or algorithm to extract note structures directly from the VP-less mix.
4. [ ] Build the transcription pipeline to output a single, polyphony-limited MIDI track.
5. [ ] Synthesize the output MIDI to an audio file for manual validation checking.
