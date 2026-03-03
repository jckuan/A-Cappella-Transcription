# SATB Vocal Separation Experiments

This document summarizes our attempts to perform "audio-to-audio" source separation for a cappella SATB (Soprano, Alto, Tenor, Bass) arrangements. 

Given a vocal mixture (with vocal percussion already removed), we attempted several state-of-the-art and algorithmic methods to isolate the 4 individual vocal stems. All methods were ultimately deemed unsuitable for pristine transcription due to severe artifacting, timber rejection, or extreme cross-stem bleeding.

## 1. SepACap (Conditioned AI Model)
**Hypothesis:** A specialized Deep Learning model trained specifically for a cappella SATB extraction using Snake activations.
**Result:** **Failed (Severe Artifacts & Poor SDR)**
- The public model weights produced extreme high-frequency radio noise even when correctly chunked and formatted identically to the research settings.
- SDR scores were deeply negative (e.g., `-14.95dB` for Soprano).
- The checkpoint appears to be fundamentally flawed or structurally mismatched with its own published inference scripts.

## 2. RoFormer (Multi-Stem Instrument AI)
**Hypothesis:** Use a highly performant MUSDB18-trained RoFormer model (Band-Split RoFormer) and map its outputs (`bass -> Bass`, `drums -> Alto`, `other -> Tenor`, `vocals -> Soprano`) assuming it might separate by pure frequency thresholds.
**Result:** **Failed (Timbre-Based Rejection)**
- RoFormer models learn *instrument timbres*, not just frequency bands.
- The model recognized all 4 singing voices as "vocals" and passed the entire polyphonic mix into the single `vocals` (Soprano) stem (SDR: `+3.17dB`).
- It aggressively rejected human formants from the other stems, treating them as silence/noise (SDR: `-15dB` to `-26dB` for Bass/Tenor/Alto).

## 3. Pitch-Guided Harmonic Masking (Algorithmic)
**Hypothesis:** Extract all notes via a polyphonic pitch tracker (`basic-pitch`), group them into SATB voices heuristically, and generate STFT harmonic masks to multiply against the mix spectrum.
**Result:** **Failed (Estimator Noise & Overlapping Bounds)**
- **Naive Bounding:** Fails because SATB pitch ranges overlap. A note in the overlapping region (e.g., MIDI 65) gets assigned to both Alto and Soprano masks, causing massive duplicates and bleed.
- **Dynamic Programming (DP) Contour Tracking:** Fails because modern polyphonic pitch estimators struggle heavily with dense, perfectly tuned a cappella chords. They hallucinate vocal formants/overtones as separate notes and drop inner harmony lines entirely. The poorly estimated contours corrupt the resulting STFT harmonic masks, yielding negative SDRs (`-4.28dB` to `-15.73dB`) and "burbling" musical noise.

---

## Conclusion & Pivot
"Blind" or semi-guided audio-to-audio separation for tightly voiced, homogeneous human singing is an unsolved problem without highly specific, supervised SATB models (which are not publicly available).

**New Workflow Strategy:**
Instead of separating the audio into 4 stems to transcribe them individually, we will skip stem separation. We will perform **Polyphonic Symbolic Transcription** directly on the VP-less vocal mix, predicting all active notes simultaneously, and assigning them to the 4 sheet music staves (SATB) via heuristic voicing rules.
