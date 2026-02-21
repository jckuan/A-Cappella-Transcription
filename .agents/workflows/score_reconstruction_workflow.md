---
description: Symbolic Score Reconstruction Workflow
---
# Symbolic Score Reconstruction Workflow

This workflow takes the cleaned transcription data and turns it into polished symbolic formats.

1. **Rhythm Quantization:** Use **Audio-to-Score (A2S)** decoders that first predict bar-level information and then fill in notes. This prevents "rhythmic drift".
2. Use **pyAMPACT** (https://github.com/pyampact/pyampact) for Typesetting: These tools handle complex notation logic like stemming, beaming, and voice-crossing.
