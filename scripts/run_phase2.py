import os
import glob
from src.vocal_separator import VocalSeparator
from src.auditor_checks import AuditorQualityControl

def run_pipeline(skip_vp: bool = True):
    prep_dir = "data/output/prep"
    sep_dir  = "data/output/separation"
    
    separator = VocalSeparator()
    auditor = AuditorQualityControl()

    for mix_path in glob.glob(f"{prep_dir}/*.wav"):
        print(f"\n{'='*50}")
        print(f"Processing File: {mix_path}")
        print(f"{'='*50}")
        
        base_name = os.path.splitext(os.path.basename(mix_path))[0]
        stems = {}
        
        if skip_vp:
            # Skip isolated_vp, use existing to save time as requested by user
            track_dir = os.path.join(sep_dir, "htdemucs", base_name)
            vp_stem = os.path.join(track_dir, "no_vocals.wav")
            vp_less_mix = os.path.join(track_dir, "vocals.wav")
            stems = {"vp_stem": vp_stem, "vp_less_mix": vp_less_mix}
        else:
            stems = separator.isolate_vp(mix_path, output_dir=sep_dir)
            
        if stems and os.path.exists(stems["vp_less_mix"]):
            satb_stems = separator.separate_satb(stems["vp_less_mix"], output_dir=sep_dir, track_name=base_name)
            
            if satb_stems:
                # Combine all stems for full composite Auditor check
                all_stems = {
                    "vp_stem": stems["vp_stem"],
                    **satb_stems
                }
                auditor.check_bleeding(mix_path, all_stems)
            else:
                print(f"Failed to separate SATB for {mix_path}")
        else:
            print(f"Failed to extract VP stem for {mix_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-all", action="store_true", help="Run both Phase 1 (Demucs) and Phase 2 (SepACap)")
    args = parser.parse_args()
    
    # By default, skip VP since htdemucs is slow. Let user run-all if they want full tests.
    run_pipeline(skip_vp=not args.run_all)
