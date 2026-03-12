import os
import argparse
import subprocess
import shutil
import urllib.request
from pathlib import Path

CONFIG_URL = "https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download/v1.0.12/config_bs_roformer_384_8_2_485100.yaml"
WEIGHTS_URL = "https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download/v1.0.12/model_bs_roformer_ep_17_sdr_9.6568.ckpt"

def download_file(url, dest_path):
    if not os.path.exists(dest_path):
        print(f"Downloading {os.path.basename(dest_path)}...")
        urllib.request.urlretrieve(url, dest_path)
    return dest_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input wav file")
    parser.add_argument("--output_dir", required=True, help="Output directory for stems")
    args = parser.parse_args()

    # Define paths
    ext_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ext", "Music-Source-Separation-Training"))
    
    config_path = os.path.join(ext_dir, "configs", "config_bs_roformer_384_8_2_485100.yaml")
    weights_path = os.path.join(ext_dir, "model_bs_roformer_ep_17_sdr_9.6568.ckpt")

    # Download if missing
    download_file(CONFIG_URL, config_path)
    download_file(WEIGHTS_URL, weights_path)

    # Prepare temp dirs
    input_file = Path(args.input).resolve()
    base_name = input_file.stem
    temp_dir = Path(args.output_dir).resolve() / "temp_roformer"
    temp_in = temp_dir / "in"
    temp_out = temp_dir / "out"
    
    temp_in.mkdir(parents=True, exist_ok=True)
    temp_out.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(input_file, temp_in / input_file.name)

    print(f"[RoFormer] Running inference on {input_file.name}...")
    
    # Run ZFTurbo inference
    cmd = [
        "python", os.path.join(ext_dir, "inference.py"),
        "--model_type", "bs_roformer",
        "--config_path", config_path,
        "--start_check_point", weights_path,
        "--input_folder", str(temp_in),
        "--store_dir", str(temp_out),
        "--filename_template", "{file_name}/{instr}",
        "--extract_instrumental" # Just in case it's a 2-stem config accidentally
    ]
    
    env = os.environ.copy()
    env["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
    
    subprocess.run(cmd, check=True, env=env)
    
    # Output mappings. MUSDB outputs: vocals, bass, drums, other
    # We map this to: soprano (vocals), bass (bass), alto (drums), tenor (other)
    mapping = {
        "bass.wav": "bass.wav",
        "vocals.wav": "soprano.wav",
        "other.wav": "tenor.wav",
        "drums.wav": "alto.wav"
    }
    
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    track_out_dir = temp_out / base_name
    for source, target in mapping.items():
        src_path = track_out_dir / source
        dst_path = out_dir / target
        if src_path.exists():
            shutil.move(src_path, dst_path)
            print(f"[RoFormer] Mapped {source} -> {target}")
        else:
            print(f"[RoFormer] WARNING: {source} not produced by inference!")
    
    # Cleanup temp
    shutil.rmtree(temp_dir)
    print(f"[RoFormer] Done. Stems saved to {args.output_dir}")

if __name__ == "__main__":
    main()
