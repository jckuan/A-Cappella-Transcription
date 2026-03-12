# Research Log

## Date: 2026-03-12
**Goal:** Investigate the current state of Polyphonic Symbolic Transcription and search for open-source Multi-Pitch Estimation (MPE) models for a cappella vocals.

### Current State
- The project has pivoted away from audio-to-audio stem separation due to severe artifacting and timbre rejection by models like SepACap and RoFormer.
- The new goal is to transcribe the VP-less vocal mix directly into a polyphonic MIDI file.
- The existing `ACTIVE_polyphonic_transcription_plan.md` proposed using Spotify's `basic-pitch` or exploring `RMVPE`.

### Discovery & Open-Source Evaluation
I searched the internet to evaluate SOTA multi-pitch estimation models on GitHub, specifically comparing `basic-pitch`, `RMVPE`, and `FCPE`.

1. **RMVPE & FCPE ("Experimented but failed" / Ruled Out):** 
   - While RMVPE and its faster successor FCPE are highly accurate (up to ~87%) and robust to noise, they are designed strictly for **monophonic** pitch estimation. They extract only the single, dominant vocal line. Because a cappella music consists of 4 overlapping voices (SATB) singing simultaneously, these monophonic models physically cannot transcribe the full chordal structure from a single file. They are ruled out for this direct polyphonic approach.
   
2. **Spotify's `basic-pitch` (Viable Candidate):** 
   - `basic-pitch` is a lightweight neural network designed for polyphonic transcription across multiple instruments, including vocals. It natively outputs continuous polyphonic pitch contours and can export directly to MIDI. 
   - *Limitation:* It has lower overall accuracy on complex vocal nuances compared to monophonic models (~33% on some benchmarks), meaning it will likely hallucinate notes or miss inner harmony lines (Alto/Tenor). 

### Conclusion & Handoff
To perform Polyphonic Symbolic Transcription directly from a single VP-less mix, **Spotify's `basic-pitch`** is the only viable open-source multi-pitch estimator available off-the-shelf. The Planner should proceed with designing the implementation utilizing `basic-pitch`, keeping in mind that the output will need a heuristic pruning step to enforce a maximum of 4 polyphonic voices (`num_singers`).

---

## Date: 2026-03-12 — Iteration 5: Harmonic Note Selection Research
**Goal:** Find a post-processing technique to select harmonically plausible notes from the candidate-rich polyphonic MIDI output, addressing the "multiple options in one stem" problem.

### Context
The previous approach (ROSVOT) was ruled out. Per the user's investigation, ROSVOT expects single-voice audio as input — the same limitation as RMVPE/FCPE. "Harmonic context" in the original plan was loosely used and did not accurately describe polyphonic chord disambiguation.

**Actual Problem:** At each moment in time, each bandpass-filtered vocal stem contains multiple simultaneous candidate notes (typically 2). Only one is the correct intended pitch. Selecting the correct one requires external harmonic information (key, scale, or chord).

### Research Findings

1. **`music21` — Key Detection + Scale Projection (Viable)**
   - `music21` supports Krumhansl-Schmuckler key detection natively via `stream.analyze('key')`.
   - Once the key is detected, its `Key.pitches` attribute provides the exact set of in-scale pitches.
   - Out-of-scale notes can be dropped or snapped to the nearest scale degree.
   - *Limitation:* Key detection works best on longer excerpts. Short segments may guess incorrectly. Also, modulations in the song would not be captured with a single global key.
   - *Verdict:* **Viable as a first pass.** Easy to integrate on top of existing `pretty_midi` output.

2. **`madmom` — Chord Recognition (Potentially Viable, Compatibility Risk)**
   - `madmom` provides CNN + CRF-based chord recognition and DeepChroma features from raw audio.
   - Outputs a time-stamped series of chord labels (e.g., `C:maj`, `G:min7`) that could be used to further filter notes within each chord window.
   - *Limitation:* `madmom` is a legacy library; its last formal PyPI release is 2016. It is known to have `Python 3.12` compatibility issues (uses deprecated `pkg_resources` and `numpy` APIs). Would require a compatibility fork or pin to `Python 3.10`.
   - *Verdict:* **High integration risk. Deprioritized.**

3. **`autochord` — Bi-LSTM-CRF Chord Recognition (Viable, but requires audio)**
   - `autochord` provides chord labels from audio using NNLS-Chroma features with a Bi-LSTM-CRF model.
   - Outputs MIREX-style chord labels (e.g., `C:maj`, `A:min`) which can be mapped to allowed note sets per time window.
   - *Limitation:* Requires the raw audio file as input (not MIDI). Would add another audio analysis pass.
   - *Verdict:* **Viable.** Could be combined with `music21` key detection for a two-pass approach.

### Proposed Architecture for Iteration 5

**Two-stage harmonic filter:**
1. **Global Key Detection** (`music21`): Run on the full MIDI. Detect the primary key. Remove or snap all notes outside the key's pitch set.
2. **Local Chord Filtering** (`autochord`): Run on the original audio. Get time-windowed chord labels. Within each chord window, retain only notes that belong to the detected chord's note set.

- Both steps work on the existing MIDI output without requiring structural code changes.
- `music21` is already pip-installable and Python 3.12 compatible.

### Next Step
Hand off to Planner to design the implementation of the two-stage harmonic filter as `_apply_harmonic_filter()` in `polyphonic_transcriber.py`.
