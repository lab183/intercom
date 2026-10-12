"""Audio playback through the default output device (Windows, Linux, macOS).

Wraps sounddevice (PortAudio). Playback is global: starting a clip replaces any clip
that is still playing, and `stop()` cuts it off.
"""


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
    return sounddevice


def play(pcm, sample_rate, block=False):
    """Play mono int16 samples. With block=True, return once playback has finished."""
    sd = _sounddevice()
    try:
        sd.play(pcm, sample_rate)
        if block:
            sd.wait()
    except sd.PortAudioError as e:
        raise PlaybackError(f"audio playback failed: {e}") from e


def stop():
    """Stop any clip that is playing."""
    _sounddevice().stop()
