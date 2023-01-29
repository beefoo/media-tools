import mido

def printMidi(fn, verbose=True):
    mid = mido.MidiFile(fn)
    if mid.type != 2:
        print(f'Length: {mid.length} seconds')
    print(f'Ticks per beat: {mid.ticks_per_beat}')
    for i, track in enumerate(mid.tracks):
        print('Track {}: {}'.format(i, track.name))
        if verbose:
            for msg in track:
                print(msg)
            print('-----------------------------------')

def readMidiTracks(fn, newTempo=None, newTicksPerBeat=None):
    mid = mido.MidiFile(fn)
    if newTicksPerBeat is not None and newTicksPerBeat != mid.ticks_per_beat:
        mid.ticks_per_beat = newTicksPerBeat
    tracks = []
    for i, t in enumerate(mid.tracks):
        newTrack = mido.MidiTrack()
        for msg in t:
            if msg.type == 'set_tempo' and newTempo is not None:
                newTrack.append(msg.copy(tempo=newTempo))
            else:
                newTrack.append(msg.copy())
        tracks.append(newTrack)
    return (mid, tracks)