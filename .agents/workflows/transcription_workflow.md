---
description: Transcription and Pitch Correction Workflow
---
# Transcription and Pitch Correction Workflow

This workflow takes cleanly separated vocal stems and translates them into context-aware note data.

1. Use **STARS** (https://github.com/gwx314/STARS) for End-to-End Analysis: Use the framework for a unified forward pass that handles everything from frame-level pitch to phoneme boundaries. This prevents the cascading errors common in modular pipelines.
2. Use **ROSVOT** (https://github.com/RickyL-2000/ROSVOT) for Contextual Pitch Correction: This music language model infers the *intended* note based on the surrounding harmonic context, correcting detuning while maintaining natural expression.
