from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

vp_stem = "../data/output/separation/htdemucs/Attention_normalized/no_vocals.wav"
print(f"Predicting on {vp_stem}...")
try:
    model_output, midi_data, note_events = predict(
        vp_stem, 
        ICASSP_2022_MODEL_PATH, 
        onset_threshold=0.3, # using sane default
        frame_threshold=0.2
    )
    if midi_data.instruments:
        bass_notes = [n for n in midi_data.instruments[0].notes if 35 <= n.pitch <= 61]
        print(f"Found {len(bass_notes)} bass notes in VP stem.")
    else:
        print("No notes found in VP stem.")
except Exception as e:
    print(f"Error predicting VP stem: {e}")
