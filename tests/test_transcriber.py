import os
import json
import unittest
import pretty_midi
from polyphonic_transcriber import PolyphonicTranscriber

class TestPolyphonicTranscriber(unittest.TestCase):
    
    def setUp(self):
        self.output_dir = "test_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # We need a dummy audio file for basic-pitch to swallow without crashing, 
        # but basic-pitch actually runs a full librosa load. 
        # For a true unit test without external mocking, we will just test the `_prune_polyphony` logic directly,
        # which is the core logic we wrote.
        self.transcriber = PolyphonicTranscriber()
        
    def test_polyphony_pruning(self):
        """
        Creates a dummy MIDI with 6 simultaneous notes and ensures it gets pruned down to 4.
        """
        midi = pretty_midi.PrettyMIDI()
        piano = pretty_midi.Instrument(program=0)
        
        # Create 6 overlapping notes from time 0.0 to 1.0
        # Velocities 10 to 60. The two lowest velocities (10, 20) should be dropped.
        for i, vel in enumerate([10, 20, 30, 40, 50, 60]):
            note = pretty_midi.Note(
                velocity=vel, 
                pitch=60 + i, 
                start=0.0, 
                end=1.0
            )
            piano.notes.append(note)
            
        midi.instruments.append(piano)
        
        # Prune to max 4 active notes
        pruned_midi = self.transcriber._prune_polyphony(midi, max_polyphony=4)
        
        # Verify only 4 notes remain
        self.assertEqual(len(pruned_midi.instruments[0].notes), 4)
        
        # Verify the surviving notes are the ones with highest velocities (30, 40, 50, 60)
        surviving_velocities = [n.velocity for n in pruned_midi.instruments[0].notes]
        self.assertNotIn(10, surviving_velocities)
        self.assertNotIn(20, surviving_velocities)
        self.assertIn(60, surviving_velocities)
        
    def test_polyphony_sequential(self):
         """
         Creates 6 notes, but only 2 overlap at any given time.
         Should NOT prune any notes.
         """
         midi = pretty_midi.PrettyMIDI()
         piano = pretty_midi.Instrument(program=0)
         
         # 3 pairs of 2 notes. None of the pairs overlap with other pairs.
         for i in range(3):
             start = i * 2.0
             end = start + 1.0
             
             note1 = pretty_midi.Note(velocity=50, pitch=60, start=start, end=end)
             note2 = pretty_midi.Note(velocity=50, pitch=64, start=start, end=end)
             
             piano.notes.extend([note1, note2])
             
         midi.instruments.append(piano)
         
         # Prune to max 4 active notes. Since max active is 2, none should be deleted.
         pruned_midi = self.transcriber._prune_polyphony(midi, max_polyphony=4)
         
         self.assertEqual(len(pruned_midi.instruments[0].notes), 6)

if __name__ == "__main__":
    unittest.main()
