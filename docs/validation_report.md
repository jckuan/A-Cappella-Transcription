# Validation Report

## Date: 2026-03-12
**Goal:** Run end-to-end synthesizations to confirm the originally stated goal (interpreting a cappella polyphony) is met by the `PolyphonicTranscriber` output.

### Result Validation
- **Input:** `Attention_normalized.wav` (A cappella arrangement, VP removed).
- **Process:** Executed `polyphonic_transcriber.py` using Spotify's `basic-pitch` for multi-pitch estimation and `_prune_polyphony` using heuristic bounds (`num_singers=4`). Synthesized to `.wav` via `fluidsynth`.
- **Output:** Transcribed multi-pitch `.mid` and audibly verifiable `.wav`.

### End-User Perspective / Verdict: `PARTIAL SUCCESS`
- **What Worked:**
  - The transcriber successfully avoids the "timbre-rejection" flaw of earlier audio-separation models (RoFormer, SepACap). It successfully identifies the core melodic lines and structural bass notes simultaneously.
  - The polyphony pruning logic correctly limits the "noise" or over-hallucinated overtones to a maximum of 4 concurrent staves representing SATB structure.
- **"Experimented but Failed" (Model Limitation):**
  - While it technically meets the Pipeline objective, the auditory validation of `basic-pitch` confirms our original hypothesis from `polyphonic_transcription_plan.md`: The model struggles significantly with perfectly tuned, tight vocal harmonies. 
  - Many "inner lines" (Alto/Tenor) are missed entirely or incorrectly bound to the lead vocal melody line due to the highly homogeneous timbre of human singing.
  - The rhythm is highly quantized out of algorithmic necessity, making the "groove" feel mechanical.

**Status:** Initial validation complete. Successive experimentation and score progression (currently 6/10) is documented in `iteration_log.md`. Holding for next user request.
