import audioread
import librosa
import numpy as np
import os
import resampy
import scipy.signal
import scipy.fftpack as fft
import sys

filename = "D:/landscapes/downloads/ia_fedflixnara/gov.archives.arc.54752_512kb.mp4"

# print("loading...")
# y, sr = librosa.load(filename, sr=None)
# print("here")
# sys.exit()

y = []
offset=0.0
# sr=22050
sr=None
mono=True
offset=0.0
duration=None
dtype=np.float32
res_type='kaiser_best'
# res_type='scipy'

def buf_to_float(x, n_bytes=2, dtype=np.float32):
    # Invert the scale of the data
    scale = 1./float(1 << ((8 * n_bytes) - 1))

    # Construct the format string
    fmt = '<i{:d}'.format(n_bytes)

    # Rescale and format the data buffer
    return scale * np.frombuffer(x, fmt).astype(dtype)

def fix_length(data, size, axis=-1, **kwargs):
    kwargs.setdefault('mode', 'constant')

    n = data.shape[axis]

    if n > size:
        slices = [slice(None)] * data.ndim
        slices[axis] = slice(0, size)
        return data[tuple(slices)]

    elif n < size:
        lengths = [(0, 0)] * data.ndim
        lengths[axis] = (0, size - n)
        return np.pad(data, lengths, **kwargs)

    return data

def to_mono(y):
    # Validate the buffer.  Stereo is ok here.
    valid_audio(y, mono=False)

    if y.ndim > 1:
        y = np.mean(y, axis=0)

    return y

def valid_audio(y, mono=True):
    if not isinstance(y, np.ndarray):
        raise ParameterError('data must be of type numpy.ndarray')

    if not np.issubdtype(y.dtype, np.floating):
        raise ParameterError('data must be floating-point')

    if mono and y.ndim != 1:
        raise ParameterError('Invalid shape for monophonic audio: '
                             'ndim={:d}, shape={}'.format(y.ndim, y.shape))

    elif y.ndim > 2 or y.ndim == 0:
        raise ParameterError('Audio must have shape (samples,) or (channels, samples). '
                             'Received shape={}'.format(y.shape))

    if not np.isfinite(y).all():
        raise ParameterError('Audio buffer is not finite everywhere')

    return True

def resample(y, orig_sr, target_sr, res_type='kaiser_best', fix=True, scale=False, **kwargs):
    # First, validate the audio buffer
    valid_audio(y, mono=False)

    if orig_sr == target_sr:
        return y

    print("Ratio...")
    ratio = float(target_sr) / orig_sr

    n_samples = int(np.ceil(y.shape[-1] * ratio))

    print("Resample..")
    if res_type == 'scipy':
        y_hat = scipy.signal.resample(y, n_samples, axis=-1)
    else:
        y_hat = resampy.resample(y, orig_sr, target_sr, filter=res_type, axis=-1)

    if fix:
        print("Fix...")
        y_hat = fix_length(y_hat, n_samples, **kwargs)

    if scale:
        print("Scale..")
        y_hat /= np.sqrt(ratio)

    print("Contiguous...")
    return np.ascontiguousarray(y_hat, dtype=y.dtype)

print("Opening file...")
with audioread.audio_open(os.path.realpath(filename)) as input_file:
    print("Opened file")
    sr_native = input_file.samplerate
    n_channels = input_file.channels

    s_start = int(np.round(sr_native * offset)) * n_channels

    if duration is None:
        s_end = np.inf
    else:
        s_end = s_start + (int(np.round(sr_native * duration)) * n_channels)

    n = 0

    for frame in input_file:
        frame = buf_to_float(frame, dtype=dtype)
        n_prev = n
        n = n + len(frame)

        if n < s_start:
            # offset is after the current frame
            # keep reading
            continue

        if s_end < n_prev:
            # we're off the end.  stop reading
            break

        if s_end < n:
            # the end is in this frame.  crop.
            frame = frame[:s_end - n_prev]

        if n_prev <= s_start <= n:
            # beginning is in this frame
            frame = frame[(s_start - n_prev):]

        # tack on the current frame
        y.append(frame)

if y:
    print("Concat...")
    y = np.concatenate(y)

    if n_channels > 1:
        print("Reshape...")
        y = y.reshape((-1, n_channels)).T
        if mono:
            print("Mono...")
            y = to_mono(y)

    if sr is not None:
        print("resample...")
        y = resample(y, sr_native, sr, res_type=res_type)

    else:
        sr = sr_native

print("Contiguous...")
# Final cleanup for dtype and contiguity
y = np.ascontiguousarray(y, dtype=dtype)

print(sr)

print("Done.")
