from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
import pretty_midi

model_output, midi_data, note_events = predict(
    "../data/output/prep/Attention_normalized.wav", 
    ICASSP_2022_MODEL_PATH, 
    onset_threshold=0.1, 
    frame_threshold=0.05
)

bass_notes = [n for n in midi_data.instruments[0].notes if 35 <= n.pitch <= 61]
print(f"Found {len(bass_notes)} bass notes in full mix with sensitive threshold.")
