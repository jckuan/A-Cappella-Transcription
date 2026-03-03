import os
import sys
import subprocess
import numpy as np
import soundfile as sf
from typing import Dict, Optional

class VocalSeparator:
    """
    Orchestrates the two-step a cappella separation process using external ML models.
    """
    def __init__(self, ext_dir: str = "ext"):
        self.ext_dir = os.path.abspath(ext_dir)
        self.demucs_path = os.path.join(self.ext_dir, "demucs")
        self.sepacap_path = os.path.join(self.ext_dir, "SepACap")

    def isolate_vp(self, input_audio: str, output_dir: str) -> Optional[Dict[str, str]]:
        """
        Step 1: Uses htdemucs to isolate Vocal Percussion (VP) as a 'drums' stem
        and outputs a 'VP-less' mix for further processing.
        """
        print(f"[SEPARATOR] Phase 1 - Isolating Vocal Percussion from {input_audio}")
        os.makedirs(output_dir, exist_ok=True)
        
        # NOTE: Demucs CLI can be invoked if installed via pip or run via python -m demucs
        # For this prototype we assume demucs is accessible in the environment. 
        # Command structure typical of demucs (mp3/wav output, 2-stems: vocals/drums)
        cmd = [
            "demucs",
            "--two-stems", "vocals", # separate vocals (VP-less) and drums (VP)
            "-o", output_dir,
            "-n", "htdemucs", # high-res demucs
            input_audio
        ]
        
        try:
            print(f"[SEPARATOR] Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                 print(f"[SEPARATOR ERROR] Demucs failed: {result.stderr}")
                 return None
            
            # Demucs typically outputs to output_dir/htdemucs/{track_name}/
            base_name = os.path.splitext(os.path.basename(input_audio))[0]
            track_dir = os.path.join(output_dir, "htdemucs", base_name)
            
            vp_stem = os.path.join(track_dir, "no_vocals.wav")
            vp_less_mix = os.path.join(track_dir, "vocals.wav")
            
            return {
                "vp_stem": vp_stem,
                "vp_less_mix": vp_less_mix 
            }
        except Exception as e:
            print(f"[SEPARATOR ERROR] Exception during VP isolation: {e}")
            return None

    def separate_satb(self, vp_less_audio: str, output_dir: str, track_name: str = None) -> Optional[Dict[str, str]]:
        """
        Step 2: Uses SepACap to split the VP-less mix into SATB parts.
        """
        print(f"[SEPARATOR] Phase 2 - Splitting SATB from {vp_less_audio}")
        
        if track_name is None:
            track_name = os.path.splitext(os.path.basename(vp_less_audio))[0]
            
        track_out_dir = os.path.join(output_dir, "SepACap", track_name)
        os.makedirs(track_out_dir, exist_ok=True)
        
        # Use inference wrapper from scripts/ (tracked by git, not inside ext/)
        infer_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts", "infer_satb.py"
        )
        cmd = [
            sys.executable, infer_script,
            "--input", vp_less_audio,
            "--output_dir", track_out_dir
        ]
        
        print(f"[SEPARATOR] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
             print(f"[SEPARATOR ERROR] SepACap failed: {result.stderr}")
             return None
        
        vocals_base = os.path.splitext(os.path.basename(vp_less_audio))[0]
        stems = {
            "soprano": os.path.join(track_out_dir, f"{vocals_base}_soprano.wav"),
            "alto": os.path.join(track_out_dir, f"{vocals_base}_alto.wav"),
            "tenor": os.path.join(track_out_dir, f"{vocals_base}_tenor.wav"),
            "bass": os.path.join(track_out_dir, f"{vocals_base}_bass.wav"),
        }
                
        return stems

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_audio", help="Standardized audio to separate")
    parser.add_argument("output_dir", help="Output directory for stems")
    
    args = parser.parse_args()
    separator = VocalSeparator()
    
    vp_res = separator.isolate_vp(args.input_audio, args.output_dir)
    if vp_res and os.path.exists(vp_res["vp_less_mix"]):
        separator.separate_satb(vp_res["vp_less_mix"], args.output_dir)
    else:
        print("[ERROR] Failed to isolate VP, skipping SATB separation.")
