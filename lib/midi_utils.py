import mido

def printMidi(fn, verbose=True):
    mid = mido.MidiFile(fn)
    for i, track in enumerate(mid.tracks):
        print('Track {}: {}'.format(i, track.name))
        if verbose:
            for msg in track:
                print(msg)
            print('-----------------------------------')

def readMidiTracks(fn, newTempo=None):
    mid = mido.MidiFile(fn)
    tracks = []
    for i, t in enumerate(mid.tracks):
        newTrack = mido.MidiTrack()
        for msg in t:
            if msg.type == 'set_tempo' and newTempo is not None:
                newTrack.append(msg.copy(tempo=newTempo))
            else:
                newTrack.append(msg.copy())
        tracks.append(newTrack)
    return tracks