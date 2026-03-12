# RoFormer SATB Separation: Evaluation Results

After successfully clearing out broken dependencies, fixing the Numba locator caching bug, and fetching the full 527MB checkpoint, the `BS-RoFormer` multi-stem model successfully processed our validation suite. 

## The Hypothesis
We attempted to map the standard `bass`, `drums`, `other`, and `vocals` outputs of a MUSDB18-trained RoFormer model to SATB vocal sections (`bass->Bass`, `drums->Alto`, `other->Tenor`, `vocals->Soprano`). We hypothesized that RoFormer might isolate them based on their physical frequency ranges matching those instruments.

## The Results
The result was a conclusive **failure**. The Auditor output confirmed that RoFormer strictly isolates by *timbre*, completely rejecting human voice formants from the instrumental stems.

### 1. `Attention_normalized.wav`
- **Soprano (Vocals)**: `3.17dB` (Contains the entire vocal mix)
- **Alto (Drums)**: `-19.18dB`
- **Tenor (Other)**: `-26.62dB`
- **Bass (Bass)**: `-25.85dB`

### 2. `One Note Samba_normalized.wav`
- **Soprano (Vocals)**: `4.90dB` 
- **Alto (Drums)**: `-15.75dB`
- **Tenor (Other)**: `-18.12dB`
- **Bass (Bass)**: `-15.60dB`

### 3. `致姍姍來遲的你_normalized.wav`
- **Soprano (Vocals)**: `0.30dB` 
- **Alto (Drums)**: `-17.40dB`
- **Tenor (Other)**: `-17.40dB`
- **Bass (Bass)**: `-21.06dB`

## Analysis
The `vocals` stem simply passed the entire mix of human voices through, yielding low positive SDR scores. Meanwhile, the instrumental stems essentially evaluated as silent noise, scoring profoundly negative SDRs. 

> [!WARNING]
> While RoFormer is SOTA for instrumental stem extraction, we cannot rely on it to implicitly extract SATB parts without explicit vocal-range supervision.

## Next Steps
We must transition to a different model or technique intentionally designed for either sub-vocal source separation or purely frequency-band filtering.

---

# Phase 4: Pitch-Guided Harmonic Masking

We tested a rule-based separation algorithm using Spotify's `basic-pitch` for multi-pitch tracking combined with STFT harmonic soft-masking on a single test track ("Attention"), guided by generic SATB MIDI bounds.

## Feasibility Test Results
The initial test on `Attention_normalized.wav` produced the following SDR scores:
- **Soprano:** `-1.84dB`
- **Alto:** `-1.50dB`
- **Tenor:** `-2.38dB`
- **Bass:** `-6.31dB`

### Analysis
The negative SDR scores indicate that our naive harmonic masks severely leak or duplicate audio components. The primary reason is that the default vocal ranges for SATB significantly overlap:
- Alto: `[55, 77]`
- Soprano: `[60, 84]`

When a singer hits a note in the overlapping region (e.g., MIDI `65`), the tracker assigns that note and its harmonic mask to *both* voices. This causes all stems to pick up the same notes during overlapping passages, resulting in high bleed and low SDR numbers. 

### Proposed Fixes
To correct the multi-pitch clustering algorithm, we could:
1. Ensure the user provides **strictly non-overlapping** pitch bounds for each song per voice part.
2. Implement **Dynamic Programming** or Gaussian Mixture Models (GMM) to track contiguous vocal lines, allowing voices to dynamically cross paths based on melodic smoothness instead of rigid bounds.

### DP Contour Tracking Test
> Updated test using Dynamic Programming assignment to minimize pitch jumps and avoid rigid bounds.

**SDR Scores (`Attention_normalized.wav`):**
- **Soprano:** `-4.28dB` (Decrease from Naive)
- **Alto:** `-5.75dB` (Decrease from Naive)
- **Tenor:** `-6.11dB` (Decrease from Naive)
- **Bass:** `-15.73dB` (Decrease from Naive)

#### Conclusion
The DP-based tracking performed *worse*. Dense a cappella chords confuse polyphonic pitch estimators (like `basic-pitch`), causing them to miss notes or hallucinate partials. When the DP tracker assigns imperfect pitch contours to the 4 lines, the STFT masks it generates are completely misaligned with the actual voices, causing massive bleed and musical noise.

**Final Verdict:** Pitch-guided STFT masking is definitively not viable for pristine a cappella SATB extraction without a flawless, strictly ground-truth aligned symbolic score (MIDI). We cannot rely on blind multi-pitch estimation from the mix to construct accurate STFT masks.
