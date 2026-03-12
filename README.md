# A Cappella Transcription

Automated polyphonic symbolic transcription of a cappella vocal arrangements into MIDI.

## Goal

Given an a cappella recording (no instruments), produce a MIDI file that separates the four main vocal parts — **Soprano, Alto, Tenor, Bass (SATB)** — into individual tracks, one per voice. The output is intended to significantly reduce the manual effort of transcribing a cappella arrangements from scratch, even if the result requires cleanup in a notation editor.

### Original Approach (Archived)

The original design was a clean, modular **audio-to-sheet-music** pipeline with well-defined stages:

| Step | Tool(s) | Description |
|---|---|---|
| 1. VP Isolation | `htdemucs` | Remove vocal percussion from the mix as a "drums" stem, leaving a clean VP-less vocal mix |
| **2. SATB Separation** | **`SepACap`, `BS-RoFormer`** | **Split the VP-less mix into four isolated per-singer audio stems** |
| 3. Pitch Estimation | `STARS`, `RMVPE` | Run end-to-end pitch/phoneme analysis on each clean monophonic stem |
| 4. Pitch Correction | `ROSVOT` | Correct detuning and microtonal drift using surrounding harmonic context |
| 5. Rhythm Quantization | Audio-to-Score (A2S) | Hierarchical bar/beat decoding to align notes to a metrical grid without rhythmic drift |
| 6. Score Export | `pyAMPACT`, `music21` | Convert cleaned MIDI to MusicXML / PDF with professional SATB typesetting |

> [!CAUTION]
> **The pipeline failed at Step 2.** No working open-source SATB separation model exists. All three candidates tested — `SepACap`, `BS-RoFormer`, and a custom Pitch-Guided Harmonic Masking approach — produced catastrophically negative SDR scores. Steps 3–6 were never reached.

Because the clean per-singer audio stems required by Steps 3–6 could not be produced, the project pivoted to **Polyphonic Symbolic Transcription** directly from the VP-less mix. See [`research/archive/`](research/archive/) and [`scripts/archive/`](scripts/archive/) for the archived experiments.


---

## Tools Considered

### Phase 1 — Audio-to-Audio SATB Separation (Archived)

| Tool | Role | Decision |
|---|---|---|
| `htdemucs` (Meta) | VP / no-vocals stem separation | ✅ **Used** — extracts the VP stem and used for Bass recovery |
| `SepACap` (ETH Zurich / NeurIPS) | Dedicated a cappella SATB source separation model | ❌ Public checkpoint broken — severe high-frequency artifacts |
| `BS-RoFormer` / `Mel-RoFormer` | SOTA music source separation | ❌ Timbre-based — treats all four voices as "vocals", passes entire mix to one stem |
| Pitch-Guided Harmonic Masking (custom) | STFT mask generation from `basic-pitch` contours | ❌ Overlapping SATB ranges cause cross-stem bleeding; DP contour tracking produces negative SDR |
| `RMVPE` / `FCPE` | Monophonic pitch estimation (for Step 3 above) | ❌ Single-voice only — would have required clean per-singer stems as input |

### Phase 2 — Polyphonic Symbolic Transcription (Current)

| Tool | Role | Decision |
|---|---|---|
| `basic-pitch` (Spotify) | Polyphonic multi-pitch estimation | ✅ **Used** — the only viable open-source polyphonic MPE |
| `scipy.signal` | Bandpass filtering per vocal range | ✅ **Used** — isolates S/A/T frequency bands for per-part prediction |
| `music21` | Key detection / scale filtering | ✅ **Used** — optional harmonic filter Stage 1 |
| `librosa` | Chroma CQT + chord template matching | ✅ **Used** — optional harmonic filter Stage 2 |
| `ROSVOT` | Pitch correction | ❌ Requires single-voice input |
| `madmom` | Chord recognition | ❌ Python 3.12 incompatible (legacy library) |
| `autochord` | Chord recognition | ❌ Ships Linux-only VAMP binary — macOS incompatible |

---

## Final Architecture

### Step 1 — Stem Separation (external, one-time)
Run `htdemucs` on the original mix to extract a clean **vocal percussion (VP) / no-vocals stem**. This preserves the Bass singer's natural overtones which would otherwise be destroyed by frequency filtering.

```bash
python3 -m demucs --two-stems=vocals path/to/song.wav -o data/output/separation/htdemucs/
```

> The output `no_vocals.wav` is passed to the transcriber via `--vp_audio`.

### Step 2 — Polyphonic Transcription
`src/polyphonic_transcriber.py` runs the full pipeline:

1. **Full-mix prediction** — `basic-pitch` inference runs once on the complete vocal mix.
2. **Hybrid per-part extraction** (when `pitch_bounds_midi` is in `metadata.json`):
   - **Soprano / Alto / Tenor**: `scipy.signal.butter` bandpass filter isolates each vocal range, then `basic-pitch` is run on each filtered signal separately.
   - **Bass**: `basic-pitch` runs directly on the `--vp_audio` stem (which retains the Bass's natural harmonic content).
3. **Pre-quantization overlap merge** — merges overlapping same-pitch `basic-pitch` detections (reserved for future use).
4. **Grid quantization** — notes are snapped to the nearest 1/N note grid using the song's BPM.
5. **Post-quantization adjacent merge** (opt-in) — merges same-pitch notes whose gap is within N grid steps.
6. **Polyphony pruning** — enforces a maximum of `num_singers + extra_polyphony` simultaneous notes.
7. **Harmonic filter** (opt-in) — two-stage filter using key-scale and chroma-based chord template matching.

---

## Metadata Format

Each song is described in `data/metadata.json`:

```json
{
  "SongName_normalized": {
    "key": "E minor",
    "bpm": 102,
    "time_signature": "4/4",
    "num_singers": 4,
    "pitch_bounds_midi": {
      "bass":    [37, 59],
      "tenor":   [52, 67],
      "alto":    [55, 72],
      "soprano": [59, 76]
    }
  }
}
```

- `key` — optional, used by `--harmonic_filter` Stage 1. If omitted, `music21` will attempt auto-detection.
- `pitch_bounds_midi` — optional. If omitted, falls back to a single pruned polyphonic track.

---

## Getting Started

### 1. Prerequisites

- Python 3.10–3.12
- `ffmpeg` installed system-wide (`brew install ffmpeg` on macOS)
- A Logic Pro DAW or other MIDI editor for review (optional)

### 2. Set Up the Environment

```bash
git clone <repo-url>
cd A-Cappella-Transcription
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export TF_USE_LEGACY_KERAS=1   # required for basic-pitch on TF2
```

### 3. Prepare Input Audio

Normalize your audio file to 44.1kHz 24-bit stereo PCM WAV format:

```bash
python3 src/librarian_prep.py
```

Or manually place your audio file in `data/input/` and run:

```python
from src.librarian_prep import extract_audio_to_pcm
extract_audio_to_pcm(
    "data/input/MySong.mp3",
    "data/output/prep/MySong_normalized.wav",
    target_sr=44100
)
```

The output filename (without `.wav`) must match the key in `metadata.json`.

### 4. Run Stem Separation (for Bass extraction)

Extract the vocal percussion (VP) stem using the provided script:

```bash
python3 src/extract_vp.py --run-all
```

This runs `htdemucs` on all files in `data/output/prep/` and produces:
- `data/output/separation/htdemucs/MySong_normalized/vocals.wav` (VP-less mix)
- `data/output/separation/htdemucs/MySong_normalized/no_vocals.wav` (VP stem for Bass recovery)

### 5. Run the Transcriber

**Basic (no stem info):**
```bash
python3 src/polyphonic_transcriber.py \
  --audio  data/output/prep/MySong_normalized.wav \
  --metadata data/metadata.json \
  --out_dir data/output/transcription \
  --quantize_unit 16
```

**Full pipeline with SATB separation and VP stem:**
```bash
python3 src/polyphonic_transcriber.py \
  --audio   data/output/prep/MySong_normalized.wav \
  --metadata data/metadata.json \
  --out_dir  data/output/transcription \
  --quantize_unit 16 \
  --vp_audio data/output/separation/htdemucs/MySong_normalized/no_vocals.wav
```

### CLI Options

| Flag | Default | Description |
|---|---|---|
| `--audio` | required | Path to the normalized vocal mix WAV |
| `--metadata` | required | Path to `metadata.json` |
| `--out_dir` | required | Output directory for MIDI files |
| `--vp_audio` | `None` | Path to `no_vocals.wav` VP stem (enables Bass hybrid extraction) |
| `--quantize_unit` | `16` | Grid quantization unit (16 = 1/16 notes, 8 = 1/8 notes) |
| `--onset_threshold` | `0.3` | `basic-pitch` onset sensitivity (lower = more notes) |
| `--frame_threshold` | `0.2` | `basic-pitch` frame sensitivity (lower = more notes) |
| `--extra_polyphony` | `2` | Extra simultaneous voices allowed beyond `num_singers` |
| `--harmonic_filter` | off | Enable two-stage harmonic filter (key + chord tone filtering) |
| `--merge_gap_steps` | `0.0` | Post-quantization note merge tolerance in grid steps (0 = disabled). Try `0.05` for conservative cleanup |

---

## Project Structure

```
A-Cappella-Transcription/
├── src/
│   ├── extract_vp.py                   # VP extraction pipeline runner
│   ├── librarian_prep.py               # Audio normalization utilities
│   ├── polyphonic_transcriber.py       # Main transcription pipeline
│   ├── vocal_separator.py              # Vocal separation wrapper (htdemucs)
│   └── archive/                        # Phase 1 audio-to-audio separation code
├── data/
│   └── metadata.json                   # Per-song BPM, key, SATB pitch bounds
├── tests/
│   ├── test_transcriber.py             # Core polyphony pruning tests
│   ├── test_bass.py
│   ├── test_tempo.py
│   ├── test_vp_bass.py
│   └── test_sdr_gains.py
├── docs/
│   ├── iteration_log.md                # Iterative improvement history
│   ├── research_log.md                 # Tool research and decisions
│   ├── implementation_log.md           # Module implementation notes
│   ├── test_report.md                  # Automated test outcomes
│   ├── validation_report.md            # End-to-end validation results
│   └── archive/                        # Outdated reports
├── polyphonic_transcription_plan.md    # Current approach design doc
├── README.md
└── requirements.txt
```

---

## Lessons Learned & Limitations

### Phase 1 Failure: Why Direct SATB Separation Didn't Work

The original approach assumed that state-of-the-art source separation models could isolate individual vocal parts from a polyphonic mix. All three candidate approaches failed:

1. **`SepACap` — Broken Public Checkpoint.** The only publicly available dedicated a cappella SATB separation model (ETH Zurich, NeurIPS). Even when inference exactly matched the training configuration (24 kHz mono, 4-second chunks, float32 input), the outputs contained severe high-frequency ringing artifacts and catastrophic SDR scores (e.g., −14.95 dB for Soprano). The published checkpoint `SepACap.pth` appears to be overfitted to a private internal dataset not reproducible from open-source code alone.

2. **`RoFormer` — Timbre-Based Rejection.** Band-Split RoFormer (state-of-the-art multi-stem separator) failed because it learns *instrument timbres*, not frequency ranges. All four singing voices were classified as "vocals" and collapsed into a single stem. The other three output stems were treated as silence or noise (SDR: −15 dB to −26 dB).

3. **Pitch-Guided Harmonic Masking — Overlapping Ranges & Estimator Noise.** A custom algorithmic pipeline used `basic-pitch` contours to generate per-voice STFT harmonic masks. This failed because SATB pitch ranges overlap significantly (especially Alto/Tenor and Soprano/Alto), causing notes in overlap zones to bleed into multiple stems. Additionally, polyphonic pitch estimators hallucinate vocal overtones and drop inner harmony lines, corrupting the masks (resulting SDR: −4 dB to −16 dB).

**Conclusion:** Blind audio-to-audio SATB separation for tightly-voiced, homogeneous human singing is an unsolved open-source problem. Supervised SATB models require proprietary training data and no working public checkpoints exist as of this project.

See [`research/archive/`](research/archive/) and [`scripts/archive/`](scripts/archive/) for preserved experiments.

---

### Phase 2: What Works Well
- **`basic-pitch`** is the only open-source model capable of polyphonic multi-pitch estimation from raw audio. It captures harmonic content of a cappella mixes well given the difficulty of the domain.
- **Bandpass filtering + VP stem hybrid** (Iteration 4) is effective at separating S/A/T from the mix while recovering the Bass from the `htdemucs` stem — the Bass's natural overtones survive because they are extracted from the VP stem rather than a bandpass-filtered signal.
- **BPM-aligned grid quantization** significantly improves rhythmic readability of the output MIDI in a DAW.

### Known Limitations

1. **Multiple simultaneous candidates per stem.** Each vocal stem contains 2–3 candidate pitches at any moment rather than a single clean melody. Singers should expect to select the correct note manually. This is treated as a feature — the options assist transcription rather than attempting to replace the human ear.

2. **Note fragmentation from quantization.** `basic-pitch` detection artifacts and intentional rhythmic re-attacks of the same pitch both result in gap = 0 after grid quantization, making them indistinguishable at the MIDI level alone. A tunable post-quantization merge is available via `--merge_gap_steps` but cannot perfectly resolve this without the original audio onset signal.

3. **Homogeneous timbre.** All four voices are the same instrument class (human voice). General source separation tools like `htdemucs` separate by instrument category, not by pitch range within a category.

4. **Key / chord aggressiveness trade-off.** The optional harmonic filter (`--harmonic_filter`) removes out-of-key and out-of-chord notes but is too aggressive for a cappella music which frequently uses chromatic passing tones, suspensions, and extended harmony.
