# **Workflow and repos**

## **Data and Model Preprocessing**

## **Vocal Separation**

[***htdemucs***](https://github.com/facebookresearch/demucs) **for VP Isolation**  
Isolate the vocal percussion as a "drums" channel.

[***SepACap***](https://github.com/ETH-DISCO/SepACap)***,*** [**BS-RoFormer, Mel-Band RoFormer](https://github.com/ZFTurbo/Music-Source-Separation-Training) for SATB Splitting**  
Process the "VP-less" mix.

## **Transcription and Pitch Correction**

[***STARS***](https://github.com/gwx314/STARS) **for End-to-End Analysis**  
Use the framework for a unified forward pass that handles everything from frame-level pitch to phoneme boundaries. This prevents the cascading errors common in modular pipelines.

[***ROSVOT***](https://github.com/RickyL-2000/ROSVOT) **for Contextual Pitch Correction**  
This music language model infers the *intended* note based on the surrounding harmonic context, correcting detuning while maintaining natural expression.

## **Symbolic Score Reconstruction**

**Rhythm Quantization:** Use **Audio-to-Score (A2S)** decoders that first predict bar-level information and then fill in notes. This prevents "rhythmic drift".

[***pyAMPACT***](https://github.com/pyampact/pyampact) **for Typesetting**  
These tools handle complex notation logic like stemming, beaming, and voice-crossing.

# 

# **Agents**

## **The Librarian (Technical Integration Agent)**

**When to Use:** During the initial workspace setup and whenever a new model repository is cloned.

**Responsibilities:**

1. Repo Intelligence: Parses READMEs, requirements.txt, and source code to identify exact model expectations (e.g., if a model expects 44.1kHz vs 48kHz).  
2. Input Standardization: Ensures all audio files match the repository’s specific requirements for sample rate, bit depth, and channel count (mono/stereo).  
3. Environment Validation: Checks for required CUDA versions or specific Python dependencies needed for repos like ZFTurbo or STARS.

**Step-by-Step Procedure:**

1. Scan the provided GitHub repository for inference scripts and configuration files (e.g., .yaml or .json).  
2. Use FFmpeg to inspect the input audio's metadata.  
3. If a mismatch is found, execute a conversion command (e.g., resampling or normalization) to make the data consistent with the model’s training data.

**Key Principles:**

1. Consistency First: Never allow mismatched audio data to reach the separation models, as it leads to severe aliasing.  
2. Documentation Grounding: Always defer to the repository’s official documentation for hyperparameter defaults.

## **The Auditor (Quality Control Agent)**

**When to Use:** Immediately following any separation task (VP extraction or SATB splitting) to validate the "cleanliness" of the stems.

**Responsibilities:**

1. Assess "bleeding" or inter-voice interference between isolated stems.  
2. Monitor for spectral overlap and "watery" artifacts caused by phase loss.  
3. Analyze the composite loss components (L1, Mel, STFT) to ensure stability in silent segments.

**Step-by-Step Procedure:**

1. Compare the extracted stems against the original mix for signal-to-distortion ratio (SDR).  
2. Check for "ghost transients" from the vocal percussion in the pitched stems.  
3. If quality thresholds aren't met, re-trigger the separation with modified window sizes or overlaps.

**Key Principles:**

1. Phase Preservation: Prioritize waveform-domain results over spectrogram masks.  
2. Separation over Extraction: Treat silence as a valid data point; ensure models handle "inactive" measures without becoming unstable.

## **The Transcriber (Inference & Alignment Agent)**

**When to Use:** Once stems are validated as "clean" by The Auditor.

**Responsibilities:**

1. Execute unified, multi-level analysis including pitch, phonemes, and note boundaries.  
2. Avoid cascading errors by bypassing modular pipelines in favor of end-to-end frameworks like STARS.  
3. Identify phonemes and microsecond-aligned boundaries to ensure lyrics align with notes.

**Step-by-Step Procedure:**

1. Input clean stems into the STARS framework for simultaneous pitch and style analysis.  
2. Use ROSVOT if the audio contains background noise to ensure robust boundary detection.  
3. Output raw MIDI with associated metadata (vocal range, gender, and pace).

**Key Principles:**

1. Unified Forward Pass: Process musical and linguistic features in a single pass to prevent error accumulation.  
2. Granular Fidelity: Track raw fundamental frequency ($F\_0$) alongside discrete MIDI events.

## **The Composer (Musical Intelligence Agent)**

**When to Use:** After the Transcriber produces raw MIDI, to fix "detuning" and "musical drift".

**Responsibilities:**

1. Perform reference-free pitch correction using musical context rather than just raw frequency.  
2. Identify the intended key and harmonic structure to "clean" accidental and microtonal errors.  
3. Maintain the natural expressiveness (nuances) of the singer while correcting pitch.

**Step-by-Step Procedure:**

1. Ingest the raw MIDI and analyze surrounding notes to infer the intended key.  
2. Apply BERT-APC to correct pitch based on the predicted likely intended pitch.  
3. Verify that word/note synchronization is maintained to avoid rhythmic drift.

**Key Principles:**

1. Contextual Logic: Intent matters more than frequency; the surrounding harmony should dictate the final note.  
2. Expressive Integrity: Correct the pitch without stripping the "human" quality from the performance.

## **The Architect (Symbolic Notation Agent)**

**When to Use:** To convert the "cleaned" MIDI into professional-grade sheet music (MusicXML/PDF).

**Responsibilities:**

1. Interpret gender, vocal range, and timbre metadata from the STARS framework to automatically assign MIDI tracks to the appropriate Soprano, Alto, Tenor, or Bass clef.  
2. Impose metrical structures (measures, time signatures) on the raw pitch stream.  
3. Manage the "visual" logic of music, such as beaming, stemming, and voice-crossing.  
4. Ensure metrical stability even if the performer's tempo fluctuates.

**Step-by-Step Procedure:**

1. Apply Hierarchical Decoding to predict bar-level information first.  
2. Use Tatum-level CTC loss to ensure rhythm quantization remains stable.  
3. Export the structured data through music21 or pyAMPACT into MusicXML/PDF formats.

**Key Principles:**

1. Top-Down Rhythm: Define the bar and beat structure before placing the notes to prevent drift.  
2. Notation Logic: Follow professional SATB typesetting standards for score readability.

