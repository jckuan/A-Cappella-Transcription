# Project Requirements Document (PRD)

## Overview
This document outlines the musical context, requirements, and configurations needed to perform **rule-based frequency clustering** for SATB (Soprano, Alto, Tenor, Bass) vocal source separation. Since deep learning models (like SepACap, RoFormer) fail due to either poor generalization or inappropriate timbre-based rejection, we are pivoting to algorithmic approaches guided by explicit musical knowledge.

## Proposed Approach: Rule-Based Pitch Clustering
Unlike "blind" source separation, polyphonic pitch tracking and clustering rely on estimating the fundamental frequencies (f0) present in the mixture and assigning them to specific voices. This requires us to know a lot about the source material. Possible algorithms/methods include:
- **Harmonic/Percussive Source Separation (HPSS) + Multi-pitch Estimation (MPE):** Extracting f0 tracks using tools like `crepe`, `pyin`, or `basic-pitch`, then clustering those pitch contours.
- **Non-negative Matrix Factorization (NMF):** If we know the notes (from a MIDI score) or the rough pitch ranges, we can guide an NMF algorithm to decompose the spectrogram into the specific notes sung by each voice.
- **Score-Informed Source Separation:** Using dynamic time warping (DTW) to align a MIDI score to the audio, and then using the score as a hard mask to separate the voices.
- **K-Means / GMM on Pitch Tracks:** Grouping extracted continuous pitch contours based on their average frequency range (assigning the highest contour to Soprano, lowest to Bass, etc.).

## Required Musical Parameters
To successfully apply rule-based separation, we need strict definitions for our audio files. Please review the following parameters and let us know what is available or feasible for your tracks:

| Parameter | Description | Is it available/feasible? |
| :--- | :--- | :--- |
| **Number of Tracks / Singers** | Total number of discrete vocal stems in the mix. Are there exactly 4 (SATB) in all tracks, or do some have divisibility/more voices? | Depends on song, could be manually provided, default to 4 |
| **Vocal Ranges (Pitch Bounds)** | The rough highest and lowest notes for each voice part. (e.g., Bass ranges from E2 to E4). | Could be provided, but the ranges for each song may vary |
| **Tempo (BPM)** | The beats per minute of the song. | Can be provided |
| **Time Signature** | The meter of the song (e.g., 4/4, 3/4). | Can be provided |
| **MIDI / Symbolic Score** | Is there an existing MIDI file, MusicXML, or sheet music for the arrangement that we could use for *score-informed* separation? | No, generation of the symbolic score is part of our later task phases. |
| **Vocal Percussion (VP)** | Is there VP in the tracks? (We currently split this out with htdemucs, but confirmation helps). | Can be provided per song. Handled by htdemucs. *Note: Bass track has overlapping frequencies with VP track. Future work may reconstruct Bass using the demucs-separated VP track (no_vocals) as well.* |

## Next Steps
Once we populate this PRD with the exact constraints from the user, we will implement the most viable rule-based pitch clustering algorithm tailored to those constraints.
