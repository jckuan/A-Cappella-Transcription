# A Cappella Separation Models: Hardware Requirements and CLI Parameters

## 1. SepACap (Research Agent Findings)
SepACap is a state-of-the-art power-set based source separation model specifically designed for a cappella music (separating multiple interacting singers).
- **Origin**: ETH Zurich / NeurIPS
- **Hardware Requirements**: As a deep-learning PyTorch architecture (based on SepReformer), it runs efficiently on CUDA-enabled GPUs. Exact VRAM specifications aren't published natively for consumers, but typically require 8GB+ VRAM for inference on high-sample-rate audio.
- **CLI Parameters**: SepACap is primarily a research repository without a public-facing, consumer-ready CLI. Integration is done via standard PyTorch script invocation (e.g., passing `--model_path` and `--input_dir`).

## 2. STARS / Popular Alternative Tools
While "STARS" likely refers to highly-starred Github repos in the domain, the leading alternatives for vocal separation feature robust CLI capabilities:

### Demucs (Facebook AI)
- **Hardware Parameters**: 
  - Minimum 3GB VRAM for GPU acceleration.
  - Recommended: 7GB+ VRAM for default models.
  - CPU-only mode available but significantly slower.
- **CLI Usage**:
  - Command: `demucs --mp3 --two-stems vocals -n mdx_extra "track.mp3"`
  - Memory mitigation flag: `--segment 8` (reduces batch split sizes for lower VRAM GPUs).

### Ultimate Vocal Remover (UVR / Python Audio Separator)
- **Hardware Parameters**:
  - Minimum Nvidia GTX 1060 6GB. Recommended 8GB+ VRAM.
  - 64-bit OS required.
- **CLI Usage**:
  - Provided via `pip install audio-separator`
  - Command: `audio-separator [audio_file] --model_name [model_name]`
