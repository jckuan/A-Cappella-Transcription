import os
import sys
import argparse
import torch
import torchaudio
import soundfile as sf
from huggingface_hub import hf_hub_download

# Needed to import from src.model inside ext/SepACap
_SEPACAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ext", "SepACap")
sys.path.insert(0, _SEPACAP_DIR)

# Temporarily remove the project root and '.' from sys.path to prevent namespace
# collision between A-Cappella-Transcription/src and ext/SepACap/src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
original_sys_path = sys.path.copy()
sys.path = [
    p for p in sys.path
    if os.path.abspath(p) != project_root and p not in ("", ".")
]

from src.model import Model
from src.utils import util_system

# Restore path
sys.path = original_sys_path


def main():
    parser = argparse.ArgumentParser(description="SepACap SATB Inference")
    parser.add_argument("--input", required=True, help="Path to input audio file")
    parser.add_argument("--output_dir", required=True, help="Directory to save separated stems")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(args.input))[0]

    # Device selection: prefer CUDA, fall back to CPU (skip MPS to avoid math artifacts)
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    print(f"Using device: {device}")

    # 1. Download checkpoint from HuggingFace (cached after first run)
    print("Downloading/Locating SepACap Checkpoint via huggingface_hub...")
    ckpt_path = hf_hub_download(repo_id="Tino3141/sepacap", filename="SepACap.pth")

    # 2. Load Config (relative to ext/SepACap)
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ext", "SepACap",
        "configs", "modelMusicSep.yaml"
    )
    config = util_system.parse_yaml(config_path)["config"]

    # 3. Model Init
    print(f"Initializing SepACap on {device}...")
    model = Model(**config["model"]).to(device)

    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
    if "model_state" in checkpoint:
        model.load_state_dict(checkpoint["model_state"], strict=False)
    else:
        model.load_state_dict(checkpoint, strict=False)
    model.eval()

    # 4. Load Audio
    print(f"Loading {args.input}...")
    audio, sr = torchaudio.load(args.input)

    # SepACap expects 24kHz mono
    if sr != 24000:
        resampler = torchaudio.transforms.Resample(sr, 24000)
        audio = resampler(audio)
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)
    audio = audio.squeeze(0)

    print(f"Running inference on {args.input} (chunked on {device.type} with overlap-add)...")
    with torch.no_grad():
        # SepACap scales quadratically with sequence length. A 10-second chunk uses ~12GB VRAM.
        chunk_sec = 10
        chunk_size = chunk_sec * 24000
        step_size = chunk_size // 2  # 50% overlap
        
        audio_len = audio.shape[-1]
        out_audio_stems = [torch.zeros(audio_len, device='cpu') for _ in range(7)]
        window_sum = torch.zeros(audio_len, device='cpu')
        
        # Hann window for smooth crossfading
        window = torch.hann_window(chunk_size, device='cpu')
        
        for start_idx in range(0, audio_len, step_size):
            end_idx = min(start_idx + chunk_size, audio_len)
            chunk = audio[start_idx:end_idx]
            
            actual_chunk_len = chunk.shape[-1]
            if actual_chunk_len == 0:
                break
                
            chunk_input = chunk.to(device).unsqueeze(0)
            
            # Pad if this is the final chunk that doesn't fit the window
            pad_len = 0
            if actual_chunk_len < chunk_size:
                pad_len = chunk_size - actual_chunk_len
                chunk_input = torch.nn.functional.pad(chunk_input, (0, pad_len))
                
            print(f"  Processing chunk {start_idx/24000:.1f}s - {(start_idx+actual_chunk_len)/24000:.1f}s...")
            sep_chunk, _ = model(chunk_input)
            
            for stem_idx in range(7):
                stem_out = sep_chunk[stem_idx].cpu().squeeze()
                if pad_len > 0:
                    stem_out = stem_out[:-pad_len]
                
                # Apply overlap-add windowing
                chunk_window = window[:actual_chunk_len]
                out_audio_stems[stem_idx][start_idx:end_idx] += stem_out * chunk_window
                
            window_sum[start_idx:end_idx] += window[:actual_chunk_len]
            
            # Clean VRAM to prevent fragmentation OOM
            del sep_chunk
            del chunk_input
            if device.type == "cuda":
                torch.cuda.empty_cache()
                
        # Normalize by the window sum to complete the crossfade
        # Add small epsilon to prevent division by zero at the very edges
        separated_sources = [
            (stem_buf / (window_sum + 1e-8)) for stem_buf in out_audio_stems
        ]

    # stem order from model: alto(0), bass(1), finger_snap(2), lead_vocal(3), soprano(4), tenor(5), vocal_percussion(6)
    target_stems = {
        "soprano": 4,
        "alto":    0,
        "tenor":   5,
        "bass":    1,
    }

    print("Saving separated SATB stems (resampling back to 44100 Hz)...")
    resampler_up = torchaudio.transforms.Resample(24000, 44100)
    for stem_name, idx in target_stems.items():
        out_audio = separated_sources[idx].cpu().squeeze()
        out_audio = out_audio.unsqueeze(0)        # (1, T)
        out_audio = resampler_up(out_audio)
        out_audio_stereo = out_audio.repeat(2, 1) # (2, T) — stereo to match pipeline expectations

        # soundfile expects (frames, channels) — avoids torchcodec dependency
        out_array = out_audio_stereo.transpose(0, 1).numpy()
        out_path  = os.path.join(args.output_dir, f"{base_name}_{stem_name}.wav")
        sf.write(out_path, out_array, 44100)
        print(f"  Saved {stem_name} → {out_path}")

    print("Done SATB split.")


if __name__ == "__main__":
    main()
