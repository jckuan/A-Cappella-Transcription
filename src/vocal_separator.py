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
        # Use python -m demucs.separate to avoid global PATH binary resolution issues
        cmd = [
            sys.executable, "-m", "demucs.separate",
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



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_audio", help="Standardized audio to separate")
    parser.add_argument("output_dir", help="Output directory for stems")
    
    args = parser.parse_args()
    separator = VocalSeparator()
    
    vp_res = separator.isolate_vp(args.input_audio, args.output_dir)
    if vp_res and os.path.exists(vp_res["vp_less_mix"]):
        print(f"[SUCCESS] VP isolated successfully. VP-less mix saved to {vp_res['vp_less_mix']}")
    else:
        print("[ERROR] Failed to isolate VP.")
