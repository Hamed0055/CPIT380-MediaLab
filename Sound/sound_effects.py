"""Read, edit and write uncompressed WAV audio in complete sample frames."""

from dataclasses import dataclass
from io import BytesIO
import math
import wave

import numpy as np


MAX_BYTES = 20 * 1024 * 1024
MAX_SECONDS = 60


@dataclass(frozen=True)
class Sound:
    samples: np.ndarray
    rate: int
    width: int

    @property
    def duration(self):
        return len(self.samples) / self.rate

    @property
    def channels(self):
        return self.samples.shape[1]


# Read WAV: Decode integer PCM samples into signed channel columns.
def read_wav(payload):
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Choose a WAV file up to 20 MB.")
    try:
        with wave.open(BytesIO(payload), "rb") as wav:
            channels, width, rate, frames, compression, _ = wav.getparams()
            if compression != "NONE" or width not in (1, 2, 3, 4):
                raise ValueError("Use an uncompressed integer PCM WAV file.")
            if channels not in (1, 2) or not 1000 <= rate <= 96000 or not 0 < frames <= rate * MAX_SECONDS:
                raise ValueError("Use mono or stereo PCM WAV up to 60 seconds at 1–96 kHz.")
            raw = wav.readframes(frames)
    except (wave.Error, EOFError, OverflowError) as exc:
        raise ValueError("The file is not a readable integer PCM WAV.") from exc
    if len(raw) != frames * channels * width:
        raise ValueError("The WAV file is incomplete.")

    if width == 1:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.int32) - 128
    elif width == 3:
        low, mid, high = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32).T
        unsigned = low | (mid << 8) | (high << 16)
        samples = (unsigned ^ 0x800000) - 0x800000
    else:
        samples = np.frombuffer(raw, dtype=f"<i{width}").astype(np.int32)
    return Sound(samples.reshape(frames, channels), rate, width)


# WAV bytes: Restore the original sample width and interleave matching channels.
def wav_bytes(sound):
    samples = sound.samples.ravel()
    if sound.width == 1:
        raw = (samples + 128).astype(np.uint8).tobytes()
    elif sound.width == 3:
        raw = np.column_stack([samples >> shift for shift in (0, 8, 16)]).astype(np.uint8).tobytes()
    else:
        raw = samples.astype(f"<i{sound.width}").tobytes()
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((sound.channels, sound.width, sound.rate, 0, "NONE", "not compressed"))
        wav.writeframes(raw)
    return output.getvalue()


# Quantize: Round once and clip to the integer range before encoding.
def _quantize(sound, samples):
    limit = 1 << (8 * sound.width - 1)
    return Sound(np.clip(np.rint(samples), -limit, limit - 1).astype(np.int32), sound.rate, sound.width)


# Match clips: Keep combined frames aligned by requiring identical PCM properties.
def _match(sound, other):
    if (sound.rate, sound.channels, sound.width) != (other.rate, other.channels, other.width):
        raise ValueError("Both clips must have the same sample rate, channel count and bit depth.")


def _check_extended_size(sound, frames):
    """Keep WAV exports within the same limits as files the editor can open."""
    if frames > sound.rate * MAX_SECONDS or 44 + frames * sound.channels * sound.width > MAX_BYTES:
        raise ValueError("The result would exceed 60 seconds or 20 MB. Trim the input first.")


# Volume: Scale the sample amplitudes and clip any overload before export.
def adjust_volume(sound, factor):
    if not 0 <= factor <= 2:
        raise ValueError("Choose a volume from 0 to 100.")
    return _quantize(sound, sound.samples * float(factor))


# Reverse: Reverse whole frames so stereo channels keep their positions.
def reverse_sound(sound):
    return Sound(sound.samples[::-1].copy(), sound.rate, sound.width)


# Echo: Mix a quieter copy after a delay and make room for the end of the echo.
def add_echo(sound, delay, strength):
    if not 0 <= delay <= 2 or not 0 <= strength <= 1:
        raise ValueError("Choose an echo delay up to two seconds and a strength from 0 to 100%.")
    if strength == 0:
        return sound
    offset = round(delay * sound.rate)
    frames = len(sound.samples)
    _check_extended_size(sound, frames + offset)
    samples = np.zeros((frames + offset, sound.channels))
    samples[:frames] = sound.samples
    samples[offset:] += strength * sound.samples
    return _quantize(sound, samples)


# Trim: Keep the frames in the chosen half-open time interval.
def trim_sound(sound, start, end):
    if not all(math.isfinite(point) for point in (start, end)) or not 0 <= start < end <= sound.duration:
        raise ValueError("Choose a start and end within the clip, with the end after the start.")
    first, last = round(start * sound.rate), round(end * sound.rate)
    if first == last:
        raise ValueError("The selection is shorter than one audio frame.")
    return Sound(sound.samples[first:last].copy(), sound.rate, sound.width)


# Join: Append the frames of a compatible second clip in order.
def splice_sounds(sound, other):
    _match(sound, other)
    _check_extended_size(sound, len(sound.samples) + len(other.samples))
    return Sound(np.concatenate((sound.samples, other.samples)), sound.rate, sound.width)


# Blend: Mix aligned frames and treat missing frames in either clip as silence.
def blend_sounds(sound, other, weight):
    _match(sound, other)
    if not 0 <= weight <= 1:
        raise ValueError("Choose a blend amount from 0 to 100%.")
    if weight == 0:
        return sound
    if weight == 1:
        return other
    samples = np.zeros((max(len(sound.samples), len(other.samples)), sound.channels))
    samples[:len(sound.samples)] = (1 - weight) * sound.samples
    samples[:len(other.samples)] += weight * other.samples
    return _quantize(sound, samples)
