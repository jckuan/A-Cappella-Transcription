# Vocal Source Separation Models: Findings and Constraints

This document summarizes our findings from evaluating various models for sub-stem (SATB) vocal source separation.

## 1. SepACap (ETH-DISCO)
*   **Architecture:** Power-set based source separation model designed specifically for a cappella music (Soprano, Alto, Tenor, Bass, Vocal Percussion). Based on the SepReformer architecture.
*   **Status:** **Abandoned**.
*   **Key Findings:**
    *   **VRAM Constraints:** The model's attention mechanisms scale quadratically with sequence length. The default inference chunks (e.g., 10 seconds) caused OOM exceptions on standard GPUs.
    *   **Receptive Field:** The model was trained with a `max_len` of 96,000 samples at 24kHz, equating to exactly 4-second chunks. Inference MUST match this chunk size.
    *   **Performance Issues:** Even when correctly chunked (4s) and given precisely scaled inputs (float32, `[1, 1, T]` shape) matching the evaluation scripts (`evalSepReformer.py`), the model outputs stems with severe high-frequency ringing and catastrophic Signal-to-Distortion Ratio (SDR) scores (e.g., -14.95dB). The public checkpoint `SepACap.pth` appears to be broken or highly overfitted to an internal dataset configuration not present in the open-source code.
    *   **Mixed Precision:** Using `torch.autocast/bfloat16` to save VRAM further degrades the output, compounding numerical instability.

## 2. BS-RoFormer / Mel-Band RoFormer (Music Source Separation Training)
*   **Architecture:** State-of-the-Art (SOTA) spectrogram and band-split based RoPE transformers.
*   **Status:** **Pending Migration**.
*   **Key Findings:**
    *   **Missing Checkpoints:** While the authors of SepACap provided a training script for Mel-Band RoFormer on the `ja_capella` dataset (`trainMelBandRoformer.py`), they **did not publish the pre-trained weights (checkpoints)** for SATB.
    *   **Public Constraints:** The ZFTurbo repository and HuggingFace only host pre-trained checkpoints for standard stems (Vocals, Drums, Bass, Other) or specific configurations like Guitar/Piano.
    *   **Next Steps:** To use RoFormer for SATB separation, we must either:
        1. Obtain the private checkpoint from the authors.
        2. Train the model from scratch on the `ja_capella` dataset using the provided script (computationally expensive but feasible).
        3. Attempt to hack an existing 4-stem model (e.g., Vocals/Bass/Drums/Other) and see if it generalizes to SATB (unlikely to yield clean stems).

## 3. htdemucs (Demucs)
*   **Architecture:** Hybrid transformer/domain-based architecture for general stem separation.
*   **Status:** **Functional for Extraction**.
*   **Key Findings:**
    *   Works exceptionally well for isolating Vocal Percussion (VP) as a "drums" stem from the rest of the a cappella mix.
    *   Provides clean inputs for downstream SATB separation.
    *   Cannot be used for SATB natively without fine-tuning, as it is hardcoded for instrumental stems.
