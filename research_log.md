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
