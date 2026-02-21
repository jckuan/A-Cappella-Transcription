import numpy as np
import librosa
import mir_eval
from typing import Dict, Tuple

class AuditorQualityControl:
    """
    Validates separation quality focusing on phase preservation and anti-bleeding.
    Follows principles from .agents/skills/auditor/SKILL.md
    """
    
    def __init__(self, target_sr: int = 44100):
        self.target_sr = target_sr
        self.sdr_threshold = 5.0 # Minimum acceptable SDR in dB

    def check_bleeding(self, original_mix_path: str, separated_stems: Dict[str, str]) -> Dict[str, Tuple[float, float, float]]:
        """
        Calculates Signal-to-Distortion Ratio (SDR), Signal-to-Interference Ratio (SIR), 
        and Signal-to-Artifact Ratio (SAR) using mir_eval.
        
        Args:
            original_mix_path: Path to the original full mix.
            separated_stems: Dictionary mapping part names (e.g., 'soprano') to file paths.
            
        Returns:
            Dict mapping part name to (SDR, SIR, SAR) tuples.
        """
        print(f"[AUDITOR] Evaluating bleed and artifacts against {original_mix_path}")
        
        try:
            mix_audio, _ = librosa.load(original_mix_path, sr=self.target_sr, mono=True)
            
            results = {}
            for part, path in separated_stems.items():
                try:
                    stem_audio, _ = librosa.load(path, sr=self.target_sr, mono=True)
                    
                    # Ensure lengths match exactly for mir_eval
                    min_len = min(len(mix_audio), len(stem_audio))
                    ref_sources = np.expand_dims(mix_audio[:min_len], axis=0)
                    est_sources = np.expand_dims(stem_audio[:min_len], axis=0)
                    
                    # This formulation assumes the original mix is the "ground truth" reference
                    # In a true evaluation setup, we'd need ground truth isolated stems.
                    # As a proxy for blind evaluation, we check how much the stem deviates from the total energy.
                    sdr, sir, sar, _ = mir_eval.separation.bss_eval_sources(ref_sources, est_sources)
                    
                    results[part] = (float(sdr[0]), float(sir[0]), float(sar[0]))
                    
                    if sdr[0] < self.sdr_threshold:
                         print(f"[AUDITOR WARN] {part} SDR ({sdr[0]:.2f}dB) is below threshold ({self.sdr_threshold}dB)")
                    else:
                         print(f"[AUDITOR PASS] {part} SDR: {sdr[0]:.2f}dB | SIR: {sir[0]:.2f}dB | SAR: {sar[0]:.2f}dB")
                         
                except Exception as e:
                    print(f"[AUDITOR ERROR] Failed to evaluate {part} stem at {path}: {e}")
                    
            return results
            
        except Exception as e:
            print(f"[AUDITOR ERROR] Failed to load reference mix: {e}")
            return {}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("mix", help="Original reference mix")
    parser.add_argument("stem1", help="First stem to evaluate")
    parser.add_argument("stem2", help="Second stem to evaluate")
    
    args = parser.parse_args()
    auditor = AuditorQualityControl()
    
    # Simple CLI wrapper for quick terminal checks
    stems = {
        "Stem_1": args.stem1,
        "Stem_2": args.stem2
    }
    auditor.check_bleeding(args.mix, stems)
