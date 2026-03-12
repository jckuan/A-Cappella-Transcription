import pretty_midi

# Create a sample midi data
original_midi = pretty_midi.PrettyMIDI()
inst = pretty_midi.Instrument(0)
inst.notes.append(pretty_midi.Note(100, 60, 0.0, 1.0))
original_midi.instruments.append(inst)

# Check default tempo
print(original_midi.get_tempo_changes())

# Remake it
new_midi = pretty_midi.PrettyMIDI(initial_tempo=102)
new_midi.instruments = original_midi.instruments
print(new_midi.get_tempo_changes())
new_midi.write('test_tempo.mid')
