"""Audio playback through the default output device (Windows, Linux, macOS).

Wraps sounddevice (PortAudio). Playback is global: starting a clip replaces any clip
that is still playing, and `stop()` cuts it off.
"""
from math import gcd

import numpy as np
from scipy.signal import resample_poly


class PlaybackError(RuntimeError):
    """Audio can't be played (no PortAudio library, no output device, ...)."""


def _sounddevice():
    # Imported late: it fails at import time if the PortAudio library is missing.
    try:
        import sounddevice
    except OSError as e:
        raise PlaybackError(
            "PortAudio library not found; on Linux install it, e.g. `apt install libportaudio2`"
        ) from e
    except Exception as e:
        # sounddevice also initialises PortAudio on import, which fails without an audio host.
        raise PlaybackError(f"audio unavailable: {e}") from e
    return sounddevice


def _resample(pcm, src_rate, dst_rate):
    g = gcd(src_rate, dst_rate)
    out = resample_poly(pcm.astype(np.float32), dst_rate // g, src_rate // g)
    return np.clip(out, -32768, 32767).astype(np.int16)


def play(pcm, sample_rate, block=False):
    """Play mono int16 samples. With block=True, return once playback has finished."""
    sd = _sounddevice()
    try:
        try:
            sd.play(pcm, sample_rate)
        except sd.PortAudioError:
            # Some devices (e.g. raw ALSA hw:) refuse the model's rate; retry at the device's own.
            rate = int(sd.query_devices(kind="output")["default_samplerate"])
            if rate == sample_rate:
                raise
            sd.play(_resample(pcm, sample_rate, rate), rate)
        if block:
            sd.wait()
    except sd.PortAudioError as e:
        raise PlaybackError(f"audio playback failed: {e}") from e


def stop():
    """Stop any clip that is playing."""
    sd = _sounddevice()
    try:
        sd.stop()
    except sd.PortAudioError as e:
        raise PlaybackError(f"audio playback failed: {e}") from e
