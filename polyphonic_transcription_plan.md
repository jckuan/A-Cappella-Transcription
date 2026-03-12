# Polyphonic Symbolic Transcription

This plan outlines the approach to transcribe the VP-less vocal mix directly into a polyphonic symbolic format (MIDI) grouped by SATB voices, completely bypassing the failed intermediate step of audio stem separation.

## Goal Description
Since state-of-the-art audio separation models (SepACap, RoFormer) fail due to timbre rejection and artifacting, we will transition to **Symbolic Transcription**. 
1. We will extract polyphonic pitch data (all active notes and their durations) directly from the polyphonic vocal mixture.
2. We will enforce a polyphony limit (maximum 4 simultaneous notes) based on the `num_singers` metadata, discarding weaker overlapping predictions to clean up the output.
3. We will output a finalized `.midi` containing a single polyphonic track of the transcribed arrangement.
4. We will synthesize this MIDI file into an audio `.wav` file to allow for immediate, manual auditory validation.

## User Review Required
> [!IMPORTANT]
> Polyphonic transcription of highly blended, tuning-perfect a cappella chords is notoriously difficult for AI pitch estimators. There will likely be missing 'inner' notes (Alto/Tenor) and hallucinated rhythmic splits. Are you okay with the pipeline producing a "best effort" rough transcription MIDI that you will manually correct in notation software, or do you expect print-ready perfection?

## Proposed Changes

### [NEW] `src/polyphonic_transcriber.py`
A new module containing the core transcription logic:
1. **Multi-Pitch Estimation:** We will utilize Spotify's `basic-pitch` (or explore RMVPE if accuracy is too low) to predict a continuous polyphonic piano roll from the `vp_less_mix.wav`.
2. **Note Objectification & Pruning:** Convert the continuous probabilities into discrete Note objects. At any given moment, if there are more than `num_singers` (e.g., 4) active notes, we will retain only the 4 with the highest confidence scores, discarding the rest to reduce hallucinated overtones.
3. **MIDI Export:** The assigned notes will be written to a `.mid` file with a single polyphonic track using the `pretty_midi` library.
4. **Audio Synthesis:** We will use `FluidSynth` (or a similar lightweight synthesizer) to render the output `.mid` file back into a `.wav` file for manual validation.

### [MODIFY] `data/metadata.json`
We will continue to use the strict JSON constraints per-file to guide the DP assignment algorithm.

## Verification Plan
### Automated Tests
- The transcription script must successfully output a valid `.mid` file for `Attention_normalized.wav` and a corresponding synthesized `.wav` file.

### Manual Verification
- We will prompt the user to listen to the synthesized `.wav` file alongside the original `vp_less_mix.wav` to evaluate if the transcribed notes accurately represent the a cappella performance.
